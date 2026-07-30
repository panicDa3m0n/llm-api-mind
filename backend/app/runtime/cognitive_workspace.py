"""Shadow-first coordination of cognitive signals, candidates, and wake ignition."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Any, Callable

from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.factory import (
    auxiliary_provider_model,
    auxiliary_provider_settings,
)
from app.llm.provider import (
    LLMConfigurationError,
    LLMProvider,
    LLMRequestError,
    LLMTextResult,
)
from app.mind.context_families import CONTEXT_FAMILIES
from app.mind.wake_registry import (
    WAKE_SOURCE_REGISTRY_VERSION,
    WakeSourceSpec,
    classify_wake_source,
)
from app.mind.workspace_contracts import (
    APPRAISAL_SCHEMA_VERSION,
    IGNITION_SCHEMA_VERSION,
    APPRAISER_SYSTEM_PROMPT,
    IGNITION_SYSTEM_PROMPT,
    JSON_REPAIR_SYSTEM_PROMPT,
    CognitiveAppraisalBatch,
    CognitiveIgnitionDecision,
    CognitiveSignalEnvelope,
    IgnitionCoalition,
    appraisal_prompt,
    ignition_prompt,
)
from app.runtime.auxiliary_structured import run_auxiliary_structured_call
from app.runtime.autonomy_schedule import coalesce_autonomous_activation
from app.runtime.cognitive_candidates import (
    candidate_source,
    persist_cognitive_candidate,
)
from app.runtime.endogenous_cognition import run_endogenous_cognition_window
from app.runtime.events import record_event
from app.runtime.preferences import load_runtime_preferences
from app.runtime.time import aware_utc
from app.storage import repositories
from app.storage.models import (
    AutonomousActivation,
    ChatSession,
    CognitiveCandidate,
    CognitiveEvent,
    CognitiveSignalReceipt,
    IntentionRecord,
    PerceptionEvent,
    utc_now,
)


ProviderFactory = Callable[[Settings], LLMProvider]
KNOWN_CONTEXT_FAMILIES = {item.id for item in CONTEXT_FAMILIES}
WORKSPACE_TRACE_KIND = "cognition.workspace"


def run_cognitive_workspace_tick(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    now: datetime | None = None,
    replay_existing: bool = False,
) -> dict[str, Any]:
    """Process new evidence and optionally schedule Scarlet without running her."""

    mode = settings.cognitive_workspace_mode
    if mode == "off":
        return {"mode": mode, "status": "disabled"}
    if replay_existing and mode != "shadow":
        return {
            "mode": mode,
            "status": "replay_requires_shadow",
            "replay_existing": True,
        }

    current = now or utc_now()
    with Session(engine) as db:
        preferences = load_runtime_preferences(db, settings)
        profile_id = preferences.profile_id
        autonomous_session = repositories.get_or_create_autonomous_session(
            db,
            profile_id=profile_id,
        )
        autonomous_session_id = autonomous_session.id
        bootstrapped = _bootstrap_live_cursors(
            db,
            profile_id=profile_id,
            replay_existing=replay_existing,
        )
        envelopes = _ingest_event_signals(
            db,
            profile_id=profile_id,
            autonomous_session=autonomous_session,
            settings=settings,
        )
        envelopes.extend(
            _ingest_perception_signals(
                db,
                profile_id=profile_id,
                settings=settings,
            )
        )
        envelopes.extend(
            _ingest_due_volition_signals(
                db,
                profile_id=profile_id,
                now=current,
                settings=settings,
            )
        )
        wake_conditions = _evaluate_wake_conditions(
            db,
            profile_id=profile_id,
            autonomous_session=autonomous_session,
            now=current,
        )

    endogenous = run_endogenous_cognition_window(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        profile_id=profile_id,
        session_id=autonomous_session_id,
        now=current,
    )
    with Session(engine) as db:
        envelopes = _pending_appraisal_envelopes(
            db,
            profile_id=profile_id,
            limit=settings.cognitive_workspace_appraisal_batch_size,
            now=current,
        )

    appraisal = _appraise_signals(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        profile_id=profile_id,
        session_id=autonomous_session_id,
        envelopes=envelopes,
    )
    ignition = _arbitrate_candidates(
        engine,
        settings=settings,
        provider_factory=provider_factory,
        profile_id=profile_id,
        session_id=autonomous_session_id,
        now=current,
    )
    watchdog = _ensure_watchdog_activation(
        engine,
        settings=settings,
        profile_id=profile_id,
        session_id=autonomous_session_id,
        now=current,
    )
    return {
        "mode": mode,
        "status": "completed",
        "bootstrapped": bootstrapped,
        "new_signal_count": len(envelopes),
        "wake_conditions": wake_conditions,
        "endogenous": endogenous,
        "appraisal": appraisal,
        "ignition": ignition,
        "watchdog": watchdog,
    }


def _evaluate_wake_conditions(
    db: Session,
    *,
    profile_id: str,
    autonomous_session: ChatSession,
    now: datetime,
) -> dict[str, Any]:
    """Match only explicit deterministic predicates; semantic checks become signals."""

    conditions = repositories.list_pending_wake_conditions(
        db,
        profile_id=profile_id,
        now=now,
        limit=100,
    )
    matched_ids: list[str] = []
    for condition in conditions:
        matched_event: CognitiveEvent | None = None
        should_match = False
        if condition.kind in {"at_time", "semantic_recheck"}:
            should_match = (
                condition.not_before is None
                or aware_utc(condition.not_before) <= aware_utc(now)
            )
        elif condition.kind == "max_silence":
            should_match = (
                condition.deadline is not None
                and aware_utc(condition.deadline) <= aware_utc(now)
            )
        elif condition.kind == "on_event":
            predicate = condition.predicate_json
            expected_type = predicate.get("event_type")
            if not isinstance(expected_type, str) or not expected_type:
                repositories.update_wake_condition(
                    db,
                    condition_id=condition.id,
                    status="invalid",
                )
                continue
            events = repositories.list_events_for_profile_since(
                db,
                profile_id=profile_id,
                observed_after=condition.created_at,
                limit=500,
            )
            for event in events:
                if event.type != expected_type:
                    continue
                expected_source = predicate.get("source")
                if expected_source is not None and event.source != expected_source:
                    continue
                expected_actor = predicate.get("actor")
                if expected_actor is not None and event.actor != expected_actor:
                    continue
                payload_equals = predicate.get("payload_equals") or {}
                if not isinstance(payload_equals, dict):
                    continue
                if any(
                    event.payload_json.get(key) != value
                    for key, value in payload_equals.items()
                ):
                    continue
                matched_event = event
                should_match = True
                break
        if not should_match:
            continue
        repositories.update_wake_condition(
            db,
            condition_id=condition.id,
            status="matched",
            matched_event_id=matched_event.id if matched_event is not None else None,
            matched_at=now,
        )
        event = record_event(
            db,
            session_id=autonomous_session.id,
            event_type="cognition.wake.condition_matched",
            payload={
                "condition_id": condition.id,
                "condition_kind": condition.kind,
                "episode_id": condition.episode_id,
                "candidate_id": condition.candidate_id,
                "predicate": condition.predicate_json,
                "matched_source_event_id": (
                    matched_event.id if matched_event is not None else None
                ),
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
        )
        envelope = CognitiveSignalEnvelope(
            receipt_id="pending",
            source_ref=f"event:{event.id}",
            source_type=event.type,
            policy="required_wake",
            context_family="agent_posture",
            observed_at=event.created_at.isoformat(),
            summary=(
                "A wake condition previously registered by Scarlet is now true."
            ),
            details={
                "condition_id": condition.id,
                "condition_kind": condition.kind,
                "episode_id": condition.episode_id,
                "predicate": condition.predicate_json,
            },
        )
        receipt = repositories.create_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind="event",
            source_key=event.id,
            source_type=event.type,
            policy="required_wake",
            disposition="required_wake",
            registry_version=WAKE_SOURCE_REGISTRY_VERSION,
            observed_at=event.created_at,
            details={"envelope": envelope.model_dump(mode="json")},
            episode_id=condition.episode_id,
        )
        candidate = _create_required_candidate(
            db,
            profile_id=profile_id,
            receipt=receipt,
            envelope=envelope.model_copy(update={"receipt_id": receipt.id}),
        )
        if condition.episode_id is not None:
            repositories.update_candidate(
                db,
                candidate_id=candidate.id,
                selected_episode_id=condition.episode_id,
            )
        matched_ids.append(condition.id)
    return {
        "evaluated": len(conditions),
        "matched_ids": matched_ids,
    }


def _bootstrap_live_cursors(
    db: Session,
    *,
    profile_id: str,
    replay_existing: bool,
) -> dict[str, Any]:
    if replay_existing:
        return {"event": False, "perception": False, "replay_existing": True}
    result: dict[str, Any] = {
        "event": False,
        "perception": False,
        "replay_existing": False,
    }
    if repositories.get_signal_cursor(
        db,
        profile_id=profile_id,
        source_kind="event",
    ) is None:
        latest_event = repositories.latest_event_for_profile(
            db,
            profile_id=profile_id,
        )
        repositories.advance_signal_cursor(
            db,
            profile_id=profile_id,
            source_kind="event",
            observed_at=(
                latest_event.created_at
                if latest_event is not None
                else datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            source_id=latest_event.id if latest_event is not None else "",
        )
        result["event"] = True
    if repositories.get_signal_cursor(
        db,
        profile_id=profile_id,
        source_kind="perception",
    ) is None:
        latest_perception = repositories.latest_perception_event_for_profile(
            db,
            profile_id=profile_id,
        )
        repositories.advance_signal_cursor(
            db,
            profile_id=profile_id,
            source_kind="perception",
            observed_at=(
                latest_perception.received_at
                if latest_perception is not None
                else datetime(1970, 1, 1, tzinfo=timezone.utc)
            ),
            source_id=latest_perception.id if latest_perception is not None else "",
        )
        result["perception"] = True
    return result


def _ingest_event_signals(
    db: Session,
    *,
    profile_id: str,
    autonomous_session: ChatSession,
    settings: Settings,
) -> list[CognitiveSignalEnvelope]:
    envelopes: list[CognitiveSignalEnvelope] = []
    rows = repositories.list_unprocessed_events(
        db,
        profile_id=profile_id,
        registry_version=WAKE_SOURCE_REGISTRY_VERSION,
        limit=settings.cognitive_workspace_signal_batch_size,
    )
    for event, chat_session in rows:
        spec = classify_wake_source(event.type)
        if event.type == "turn.completed" and chat_session.kind != "human_dialogue":
            spec = WakeSourceSpec(
                pattern=event.type,
                policy="trace_only",
                context_family="session_continuity",
                appraisal_required=False,
                coalescing_key="autonomous-turn:{turn_id}",
                purpose="Autonomous completion is already part of internal chronology.",
            )
        episode_id = _episode_for_event(db, event)
        disposition = _initial_disposition(spec, episode_id=episode_id)
        details = _event_details(db, event=event, chat_session=chat_session)
        envelope = CognitiveSignalEnvelope(
            receipt_id="pending",
            source_ref=f"event:{event.id}",
            source_type=event.type,
            policy=spec.policy,
            context_family=spec.context_family,
            observed_at=event.created_at.isoformat(),
            summary=_event_summary(event, details=details),
            details=details,
        )
        receipt = repositories.create_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind="event",
            source_key=event.id,
            source_type=event.type,
            policy=spec.policy,
            disposition=disposition,
            registry_version=WAKE_SOURCE_REGISTRY_VERSION,
            observed_at=event.created_at,
            details={
                "envelope": envelope.model_dump(mode="json"),
                "registry_purpose": spec.purpose,
                "interrupt_policy": spec.interrupt_policy,
            },
            episode_id=episode_id,
        )
        repositories.advance_signal_cursor(
            db,
            profile_id=profile_id,
            source_kind="event",
            observed_at=event.created_at,
            source_id=event.id,
        )
        if disposition == "pending_appraisal":
            envelopes.append(
                envelope.model_copy(update={"receipt_id": receipt.id})
            )
        elif spec.policy == "required_wake":
            _create_required_candidate(
                db,
                profile_id=profile_id,
                receipt=receipt,
                envelope=envelope.model_copy(update={"receipt_id": receipt.id}),
            )
        _record_signal_receipt_event(
            db,
            session_id=autonomous_session.id,
            receipt=receipt,
        )
    return envelopes


def _ingest_perception_signals(
    db: Session,
    *,
    profile_id: str,
    settings: Settings,
) -> list[CognitiveSignalEnvelope]:
    envelopes: list[CognitiveSignalEnvelope] = []
    events = repositories.list_unprocessed_perception_events(
        db,
        profile_id=profile_id,
        registry_version=WAKE_SOURCE_REGISTRY_VERSION,
        limit=settings.cognitive_workspace_signal_batch_size,
    )
    for event in events:
        summary = (
            f"New external observation on channel={event.channel}, "
            f"event_type={event.event_type}, source={event.source}."
        )
        envelope = CognitiveSignalEnvelope(
            receipt_id="pending",
            source_ref=f"perception:{event.id}",
            source_type=event.event_type,
            policy="candidate",
            context_family=_perception_context_family(event),
            observed_at=event.observed_at.isoformat(),
            summary=summary,
            details={
                "channel": event.channel,
                "source": event.source,
                "payload": _compact_value(event.payload_json),
                "navigation": event.navigation_json,
            },
        )
        receipt = repositories.create_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind="perception",
            source_key=event.id,
            source_type=event.event_type,
            policy="candidate",
            disposition="pending_appraisal",
            registry_version=WAKE_SOURCE_REGISTRY_VERSION,
            observed_at=event.received_at,
            details={"envelope": envelope.model_dump(mode="json")},
        )
        repositories.advance_signal_cursor(
            db,
            profile_id=profile_id,
            source_kind="perception",
            observed_at=event.received_at,
            source_id=event.id,
        )
        envelopes.append(envelope.model_copy(update={"receipt_id": receipt.id}))
    return envelopes


def _ingest_due_volition_signals(
    db: Session,
    *,
    profile_id: str,
    now: datetime,
    settings: Settings,
) -> list[CognitiveSignalEnvelope]:
    envelopes: list[CognitiveSignalEnvelope] = []
    due = repositories.list_due_intention_records(
        db,
        owner_profile_id=profile_id,
        now=now,
        limit=settings.cognitive_workspace_appraisal_batch_size,
    )
    for intention in due:
        due_key = _volition_due_key(intention)
        if repositories.get_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind="volition_due",
            source_key=due_key,
            registry_version=WAKE_SOURCE_REGISTRY_VERSION,
        ) is not None:
            continue
        envelope = CognitiveSignalEnvelope(
            receipt_id="pending",
            source_ref=f"intention:{intention.id}",
            source_type="organ.volition.review_due",
            policy="candidate",
            context_family="agent_posture",
            observed_at=(intention.next_review_at or now).isoformat(),
            summary=(
                "The review time has arrived for an open Scarlet volition: "
                f"{intention.desire}"
            ),
            details={
                "intention_id": intention.id,
                "status": intention.status,
                "reason": intention.reason,
                "next_possible_reflection": intention.next_possible_reflection,
                "last_reviewed_at": _iso(intention.last_reviewed_at),
                "next_review_at": _iso(intention.next_review_at),
            },
        )
        receipt = repositories.create_signal_receipt(
            db,
            profile_id=profile_id,
            source_kind="volition_due",
            source_key=due_key,
            source_type="organ.volition.review_due",
            policy="candidate",
            disposition="pending_appraisal",
            registry_version=WAKE_SOURCE_REGISTRY_VERSION,
            observed_at=intention.next_review_at or now,
            details={"envelope": envelope.model_dump(mode="json")},
        )
        envelopes.append(envelope.model_copy(update={"receipt_id": receipt.id}))
    return envelopes


def _pending_appraisal_envelopes(
    db: Session,
    *,
    profile_id: str,
    limit: int,
    now: datetime,
) -> list[CognitiveSignalEnvelope]:
    receipts = repositories.list_signal_receipts(
        db,
        profile_id=profile_id,
        disposition="pending_appraisal",
        limit=limit,
    )
    envelopes: list[CognitiveSignalEnvelope] = []
    for receipt in receipts:
        retry_after = receipt.details_json.get("retry_after")
        if isinstance(retry_after, str):
            try:
                if _parse_datetime(retry_after) > now:
                    continue
            except ValueError:
                pass
        raw = receipt.details_json.get("envelope")
        if not isinstance(raw, dict):
            repositories.update_signal_receipt(
                db,
                receipt_id=receipt.id,
                disposition="invalid",
                details={
                    **receipt.details_json,
                    "error": "missing persisted signal envelope",
                },
            )
            continue
        try:
            envelopes.append(
                CognitiveSignalEnvelope.model_validate(
                    {**raw, "receipt_id": receipt.id}
                )
            )
        except ValidationError as exc:
            repositories.update_signal_receipt(
                db,
                receipt_id=receipt.id,
                disposition="invalid",
                details={
                    **receipt.details_json,
                    "validation_error": str(exc),
                },
            )
    return envelopes


def _appraise_signals(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    profile_id: str,
    session_id: str,
    envelopes: list[CognitiveSignalEnvelope],
) -> dict[str, Any]:
    if not envelopes:
        return {"status": "not_required", "candidate_ids": []}
    with Session(engine) as db:
        parked_candidates = repositories.list_candidates(
            db,
            profile_id=profile_id,
            status="parked",
            limit=settings.cognitive_workspace_parked_candidate_context_limit,
        )
        parked_payloads = [
            _parked_candidate_payload(db, candidate)
            for candidate in parked_candidates
        ]
    aux_settings = auxiliary_provider_settings(settings)
    prompt = appraisal_prompt(envelopes, parked_candidates=parked_payloads)
    try:
        provider = provider_factory(aux_settings)
        result, parsed, repaired = run_auxiliary_structured_call(
            provider=provider,
            prompt=prompt,
            system=APPRAISER_SYSTEM_PROMPT,
            max_tokens=settings.cognitive_workspace_appraisal_max_tokens,
            schema_name=APPRAISAL_SCHEMA_VERSION,
            parser=CognitiveAppraisalBatch.model_validate,
            repair_system=JSON_REPAIR_SYSTEM_PROMPT,
        )
    except (LLMConfigurationError, LLMRequestError) as exc:
        with Session(engine) as db:
            trace = repositories.add_trace(
                db,
                session_id=session_id,
                kind=WORKSPACE_TRACE_KIND,
                payload={
                    "operation": "cognition.appraisal",
                    "status": "provider_error",
                    "model": auxiliary_provider_model(settings),
                    "source_refs": [item.source_ref for item in envelopes],
                    "error": str(exc),
                },
            )
            retry_after = utc_now() + timedelta(seconds=60)
            for envelope in envelopes:
                receipt = db.get(CognitiveSignalReceipt, envelope.receipt_id)
                if receipt is None:
                    continue
                repositories.update_signal_receipt(
                    db,
                    receipt_id=receipt.id,
                    disposition="pending_appraisal",
                    details={
                        **receipt.details_json,
                        "appraisal_attempt_count": int(
                            receipt.details_json.get("appraisal_attempt_count", 0)
                        )
                        + 1,
                        "retry_after": retry_after.isoformat(),
                        "last_provider_error": str(exc),
                        "appraisal_trace_id": trace.id,
                    },
                )
        return {
            "status": "provider_error",
            "trace_id": trace.id,
            "error": str(exc),
        }

    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            kind=WORKSPACE_TRACE_KIND,
            payload={
                "operation": "cognition.appraisal",
                "status": "completed" if parsed is not None else "invalid_output",
                "model": result.model,
                "input": [item.model_dump(mode="json") for item in envelopes],
                "parked_candidates": parked_payloads,
                "provider": _provider_payload(result),
                "repair_provider": _provider_payload(repaired)
                if repaired is not None
                else None,
                "parsed": parsed.model_dump(mode="json")
                if parsed is not None
                else None,
            },
        )
        if parsed is None:
            for envelope in envelopes:
                repositories.update_signal_receipt(
                    db,
                    receipt_id=envelope.receipt_id,
                    disposition="insufficient_evidence",
                    details={
                        "envelope": envelope.model_dump(mode="json"),
                        "appraisal_trace_id": trace.id,
                        "reason": (
                            "The appraiser and one repair attempt did not return "
                            "a valid structured disposition."
                        ),
                    },
                )
            return {
                "status": "invalid_output",
                "trace_id": trace.id,
                "candidate_ids": [],
            }
        by_ref = {item.source_ref: item for item in envelopes}
        parked_by_id = {
            item.id: item
            for item in repositories.list_candidates(
                db,
                profile_id=profile_id,
                status="parked",
                limit=settings.cognitive_workspace_parked_candidate_context_limit,
            )
        }
        mentioned: set[str] = set()
        candidate_ids: list[str] = []
        for item in parsed.appraisals:
            valid_refs = sorted({ref for ref in item.source_refs if ref in by_ref})
            if len(valid_refs) != len(set(item.source_refs)):
                continue
            mentioned.update(valid_refs)
            related = [by_ref[ref] for ref in valid_refs]
            if item.disposition == "reconsider":
                candidate = parked_by_id.get(item.candidate_id or "")
                if candidate is None:
                    for envelope in related:
                        repositories.update_signal_receipt(
                            db,
                            receipt_id=envelope.receipt_id,
                            disposition="insufficient_evidence",
                            details={
                                "envelope": envelope.model_dump(mode="json"),
                                "appraisal_reason": item.reason,
                                "appraisal_trace_id": trace.id,
                                "reason": "The referenced parked candidate is unavailable.",
                            },
                        )
                    continue
                existing_refs = {
                    f"{source.source_kind}:{source.source_id}"
                    for source in repositories.list_candidate_sources(
                        db,
                        candidate_id=candidate.id,
                    )
                }
                novel_refs = [ref for ref in valid_refs if ref not in existing_refs]
                if not novel_refs:
                    for envelope in related:
                        repositories.update_signal_receipt(
                            db,
                            receipt_id=envelope.receipt_id,
                            disposition="insufficient_evidence",
                            details={
                                "envelope": envelope.model_dump(mode="json"),
                                "appraisal_reason": item.reason,
                                "appraisal_trace_id": trace.id,
                                "reason": (
                                    "Reconsidering a parked candidate requires newly "
                                    "admitted source evidence."
                                ),
                            },
                        )
                    continue
                reconsidered = repositories.reconsider_candidate(
                    db,
                    candidate_id=candidate.id,
                    sources=[
                        candidate_source(
                            ref,
                            observed_at=_parse_datetime(by_ref[ref].observed_at),
                        )
                        for ref in novel_refs
                    ],
                    appraisal_model=result.model,
                    appraisal_trace_id=trace.id,
                    metadata={
                        "reason": item.reason,
                        "new_source_refs": novel_refs,
                    },
                )
                candidate_ids.append(reconsidered.id)
                for envelope in related:
                    repositories.update_signal_receipt(
                        db,
                        receipt_id=envelope.receipt_id,
                        disposition="candidate_reconsidered",
                        candidate_id=reconsidered.id,
                        details={
                            "envelope": envelope.model_dump(mode="json"),
                            "appraisal_reason": item.reason,
                            "appraisal_trace_id": trace.id,
                        },
                    )
                continue
            if item.disposition != "candidate":
                for envelope in related:
                    repositories.update_signal_receipt(
                        db,
                        receipt_id=envelope.receipt_id,
                        disposition=item.disposition,
                        details={
                            "envelope": envelope.model_dump(mode="json"),
                            "appraisal_reason": item.reason,
                            "appraisal_trace_id": trace.id,
                        },
                    )
                continue
            assert item.candidate_kind is not None
            assert item.context_family is not None
            assert item.claim is not None
            assert item.why_now is not None
            assert item.cognitive_question is not None
            assert item.expected_transformation is not None
            context_family = (
                item.context_family
                if item.context_family in KNOWN_CONTEXT_FAMILIES
                else related[0].context_family
            )
            candidate, created = persist_cognitive_candidate(
                db,
                profile_id=profile_id,
                candidate_kind=item.candidate_kind,
                context_family=context_family,
                claim=item.claim,
                why_now=item.why_now,
                cognitive_question=item.cognitive_question,
                expected_transformation=item.expected_transformation,
                uncertainty=item.uncertainty,
                source_refs=valid_refs,
                sources=[
                    candidate_source(
                        ref,
                        observed_at=_parse_datetime(by_ref[ref].observed_at),
                    )
                    for ref in valid_refs
                ],
                appraisal_model=result.model,
                appraisal_trace_id=trace.id,
                metadata={
                    "wake_recommendation": item.wake_recommendation,
                    "appraisal_reason": item.reason,
                },
            )
            should_offer_candidate = created or candidate.status != "parked"
            if should_offer_candidate:
                candidate_ids.append(candidate.id)
            for envelope in related:
                repositories.update_signal_receipt(
                    db,
                    receipt_id=envelope.receipt_id,
                    disposition=(
                        "candidate_created"
                        if should_offer_candidate
                        else "candidate_already_parked"
                    ),
                    candidate_id=candidate.id,
                    details={
                        "envelope": envelope.model_dump(mode="json"),
                        "appraisal_reason": item.reason,
                        "appraisal_trace_id": trace.id,
                    },
                )
        for envelope in envelopes:
            if envelope.source_ref in mentioned:
                continue
            repositories.update_signal_receipt(
                db,
                receipt_id=envelope.receipt_id,
                disposition="insufficient_evidence",
                details={
                    "envelope": envelope.model_dump(mode="json"),
                    "appraisal_trace_id": trace.id,
                    "reason": "The appraiser returned no disposition for this signal.",
                },
            )
        record_event(
            db,
            session_id=session_id,
            event_type="cognition.appraisal.completed",
            payload={
                "trace_id": trace.id,
                "model": result.model,
                "source_count": len(envelopes),
                "candidate_ids": candidate_ids,
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
            trace_id=trace.id,
        )
        return {
            "status": "completed",
            "trace_id": trace.id,
            "candidate_ids": candidate_ids,
        }


def _arbitrate_candidates(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    profile_id: str,
    session_id: str,
    now: datetime,
) -> dict[str, Any]:
    with Session(engine) as db:
        candidates = repositories.list_eligible_candidates(
            db,
            profile_id=profile_id,
            now=now,
            limit=settings.cognitive_workspace_candidate_pool_limit,
        )
        if not candidates:
            return {"status": "not_required", "selected_ids": []}
        episodes = repositories.list_episodes(
            db,
            profile_id=profile_id,
            status="active",
            limit=10,
        )
        pool_fingerprint = _pool_fingerprint(candidates, episodes)
        existing = repositories.get_arbitration_by_pool(
            db,
            profile_id=profile_id,
            mode=settings.cognitive_workspace_mode,
            pool_fingerprint=pool_fingerprint,
        )
        if existing is not None:
            activation = _apply_ignition(
                db,
                settings=settings,
                profile_id=profile_id,
                session_id=session_id,
                arbitration=existing,
                candidates=candidates,
                now=now,
            )
            return {
                "status": "reused",
                "arbitration_id": existing.id,
                "selected_ids": existing.selected_ids_json,
                "activation_id": activation.id if activation is not None else None,
            }
        required = [
            item
            for item in candidates
            if bool(item.metadata_json.get("required_wake"))
        ]
        candidate_payloads = [
            _candidate_payload(db, candidate) for candidate in candidates
        ]
        episode_payloads = [
            _episode_payload(db, episode) for episode in episodes
        ]

    decision: CognitiveIgnitionDecision | None
    if required:
        decision = CognitiveIgnitionDecision(
            ignite="now",
            coalitions=[
                IgnitionCoalition(
                    candidate_ids=[item.id for item in required],
                    reason="Deterministic wake contract matched.",
                    proposed_episode_question=required[0].cognitive_question,
                    expected_transformation=required[
                        0
                    ].expected_transformation,
                )
            ],
            rationale=(
                "One or more source contracts require a Scarlet activation; "
                "semantic arbitration may still reject the proposed work."
            ),
        )
        provider_result = None
        repaired = None
        model = "deterministic_required_wake"
    else:
        aux_settings = auxiliary_provider_settings(settings)
        try:
            provider = provider_factory(aux_settings)
            provider_result, decision, repaired = run_auxiliary_structured_call(
                provider=provider,
                prompt=ignition_prompt(
                    candidates=candidate_payloads,
                    active_episodes=episode_payloads,
                    max_deferrals=settings.cognitive_workspace_max_deferrals,
                ),
                system=IGNITION_SYSTEM_PROMPT,
                max_tokens=settings.cognitive_workspace_arbitration_max_tokens,
                schema_name=IGNITION_SCHEMA_VERSION,
                parser=CognitiveIgnitionDecision.model_validate,
                repair_system=JSON_REPAIR_SYSTEM_PROMPT,
            )
        except (LLMConfigurationError, LLMRequestError) as exc:
            return {"status": "provider_error", "error": str(exc)}
        if decision is None:
            return {"status": "invalid_output", "selected_ids": []}
        model = provider_result.model

    allowed_ids = {item.id for item in candidates}
    selected_ids = _selected_candidate_ids(decision, allowed_ids=allowed_ids)
    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            kind=WORKSPACE_TRACE_KIND,
            payload={
                "operation": "cognition.ignition",
                "mode": settings.cognitive_workspace_mode,
                "model": model,
                "pool_fingerprint": pool_fingerprint,
                "candidates": candidate_payloads,
                "active_episodes": episode_payloads,
                "provider": _provider_payload(provider_result)
                if provider_result is not None
                else None,
                "repair_provider": _provider_payload(repaired)
                if repaired is not None
                else None,
                "decision": decision.model_dump(mode="json"),
                "selected_ids": selected_ids,
            },
        )
        arbitration = repositories.create_arbitration(
            db,
            profile_id=profile_id,
            mode=settings.cognitive_workspace_mode,
            status="completed",
            model=model,
            pool_fingerprint=pool_fingerprint,
            candidate_ids=[item.id for item in candidates],
            selected_ids=selected_ids,
            decision=decision.model_dump(mode="json"),
            trace_id=trace.id,
        )
        activation = _apply_ignition(
            db,
            settings=settings,
            profile_id=profile_id,
            session_id=session_id,
            arbitration=arbitration,
            candidates=candidates,
            now=now,
        )
        _apply_gate_deferrals(
            db,
            decision=decision,
            allowed_ids=allowed_ids,
            selected_ids=set(selected_ids),
            now=now,
            default_delay_seconds=settings.autonomous_activation_interval_seconds,
        )
        record_event(
            db,
            session_id=session_id,
            event_type="cognition.arbitration.completed",
            payload={
                "arbitration_id": arbitration.id,
                "mode": settings.cognitive_workspace_mode,
                "model": model,
                "ignite": decision.ignite,
                "selected_ids": selected_ids,
                "activation_id": activation.id if activation is not None else None,
            },
            source="cognitive_workspace",
            actor="backend",
            visibility="private",
            trace_id=trace.id,
        )
        return {
            "status": "completed",
            "arbitration_id": arbitration.id,
            "selected_ids": selected_ids,
            "activation_id": activation.id if activation is not None else None,
        }


def _apply_gate_deferrals(
    db: Session,
    *,
    decision: CognitiveIgnitionDecision,
    allowed_ids: set[str],
    selected_ids: set[str],
    now: datetime,
    default_delay_seconds: int,
) -> None:
    """Persist reconsideration timing without turning M2.7 into final authority."""

    for item in decision.deferred:
        if item.candidate_id not in allowed_ids or item.candidate_id in selected_ids:
            continue
        revisit_at: datetime | None = None
        if item.revisit_kind == "at_time" and item.revisit_at:
            try:
                revisit_at = _parse_datetime(item.revisit_at)
            except ValueError:
                revisit_at = None
        if revisit_at is None:
            revisit_at = now + timedelta(seconds=default_delay_seconds)
        repositories.update_candidate(
            db,
            candidate_id=item.candidate_id,
            status="suspended",
            deferred_until=revisit_at,
            increment_deferral=True,
        )


def _apply_ignition(
    db: Session,
    *,
    settings: Settings,
    profile_id: str,
    session_id: str,
    arbitration: Any,
    candidates: list[CognitiveCandidate],
    now: datetime,
) -> AutonomousActivation | None:
    selected_ids = [
        item for item in arbitration.selected_ids_json if isinstance(item, str)
    ]
    if not selected_ids:
        return None
    decision = arbitration.decision_json
    if decision.get("ignite") != "now":
        return None
    candidate_by_id = {item.id: item for item in candidates}
    selected = [
        candidate_by_id[item]
        for item in selected_ids
        if item in candidate_by_id
    ]
    if not selected:
        return None
    episode_id = next(
        (
            item.selected_episode_id
            for item in selected
            if item.selected_episode_id is not None
        ),
        None,
    )
    workspace = {
        "schema_version": "scarlet-cognitive-workspace-v1",
        "arbitration_id": arbitration.id,
        "authority": "provisional_m2.7_ignition",
        "selected_candidate_ids": [item.id for item in selected],
        "selected_candidates": [
            _candidate_payload(db, item) for item in selected
        ],
        "instruction": (
            "These are provisional source-backed candidates, not established "
            "facts or commands. Scarlet must inspect them and may open, resume, "
            "suspend, resolve, or reject the proposed cognitive episode."
        ),
    }
    endogenous_window_ids = list(
        dict.fromkeys(
            str(item.metadata_json["endogenous_window_id"])
            for item in selected
            if item.metadata_json.get("origin") == "endogenous_cognition"
            and isinstance(item.metadata_json.get("endogenous_window_id"), str)
        )
    )
    if endogenous_window_ids:
        workspace["endogenous"] = {
            "window_id": endogenous_window_ids[0],
            "window_ids": endogenous_window_ids,
            "authority": "provisional_preconscious_seed",
            "instruction": (
                "An endogenous seed is not yet Scarlet's desire or intention. "
                "Inspect its sources. If you genuinely endorse a durable direction, "
                "create or review a volition; otherwise reject, suspend, or resolve "
                "the candidate without manufacturing activity."
            ),
        }
    if settings.cognitive_workspace_mode == "shadow":
        return None
    if settings.cognitive_workspace_mode == "advisory":
        activation = repositories.attach_workspace_to_next_activation(
            db,
            profile_id=profile_id,
            workspace=workspace,
            candidate_id=selected[0].id,
            episode_id=episode_id,
            wake_condition_id=None,
        )
        _link_endogenous_windows(
            db,
            activation=activation,
            window_ids=endogenous_window_ids,
        )
        return activation
    if settings.cognitive_workspace_mode != "active":
        return None
    schedule = coalesce_autonomous_activation(
        db,
        profile_id=profile_id,
        session_id=session_id,
        trigger_kind="cognitive_workspace",
        candidate_id=selected[0].id,
        episode_id=episode_id,
        workspace=workspace,
        min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
        now=now,
    )
    activation = schedule.activation
    _link_endogenous_windows(
        db,
        activation=activation,
        window_ids=endogenous_window_ids,
    )
    return activation


def _ensure_watchdog_activation(
    engine: Engine,
    *,
    settings: Settings,
    profile_id: str,
    session_id: str,
    now: datetime,
) -> dict[str, Any]:
    if settings.cognitive_workspace_mode != "active":
        return {"status": "inactive"}
    with Session(engine) as db:
        latest = repositories.latest_completed_autonomous_activation(
            db,
            profile_id=profile_id,
        )
        baseline = latest.completed_at if latest is not None else None
        if baseline is None:
            session = repositories.get_chat_session(db, session_id)
            baseline = session.created_at if session is not None else now
        baseline = aware_utc(baseline)
        current = aware_utc(now)
        due_at = baseline + timedelta(
            seconds=settings.autonomous_activation_max_silence_seconds
        )
        if due_at > current:
            return {"status": "waiting", "due_at": due_at.isoformat()}
        schedule = coalesce_autonomous_activation(
            db,
            profile_id=profile_id,
            session_id=session_id,
            trigger_kind="max_silence",
            min_gap_seconds=settings.autonomous_activation_min_gap_seconds,
            now=current,
            workspace={
                "schema_version": "scarlet-cognitive-workspace-v1",
                "authority": "deterministic_max_silence",
                "selected_candidates": [],
                "instruction": (
                    "A bounded orientation cycle is due. No source is a fact or "
                    "command; inspect available continuity and suspend again when "
                    "no transformation is available."
                ),
            },
        )
        if schedule.disposition == "scheduled":
            record_event(
                db,
                session_id=session_id,
                event_type="cognition.max_silence.due",
                payload={
                    "activation_id": schedule.activation.id,
                    "baseline": baseline.isoformat(),
                    "due_at": due_at.isoformat(),
                    "eligible_at": schedule.eligible_at.isoformat(),
                },
                source="cognitive_workspace",
                actor="backend",
                visibility="private",
            )
        return {
            "status": schedule.disposition,
            "activation_id": schedule.activation.id,
            "eligible_at": schedule.eligible_at.isoformat(),
        }


def _create_required_candidate(
    db: Session,
    *,
    profile_id: str,
    receipt: CognitiveSignalReceipt,
    envelope: CognitiveSignalEnvelope,
) -> CognitiveCandidate:
    candidate, _ = persist_cognitive_candidate(
        db,
        profile_id=profile_id,
        candidate_kind="required_wake",
        context_family=envelope.context_family,
        claim=envelope.summary,
        why_now="A validated deterministic wake contract matched.",
        cognitive_question=(
            "What does this source require Scarlet to inspect or decide now?"
        ),
        expected_transformation=(
            "Verify the source and produce a traceable decision or suspension."
        ),
        uncertainty="low",
        source_refs=[envelope.source_ref],
        sources=[
            candidate_source(
                envelope.source_ref,
                observed_at=_parse_datetime(envelope.observed_at),
            )
        ],
        metadata={"required_wake": True},
    )
    repositories.update_signal_receipt(
        db,
        receipt_id=receipt.id,
        disposition="candidate_created",
        candidate_id=candidate.id,
        details=receipt.details_json,
    )
    return candidate


def _link_endogenous_windows(
    db: Session,
    *,
    activation: AutonomousActivation | None,
    window_ids: list[str],
) -> None:
    if activation is None:
        return
    for window_id in window_ids:
        repositories.link_endogenous_activation(
            db,
            window_id=window_id,
            activation_id=activation.id,
        )


def _event_details(
    db: Session,
    *,
    event: CognitiveEvent,
    chat_session: ChatSession,
) -> dict[str, Any]:
    details: dict[str, Any] = {
        "session_id": event.session_id,
        "session_kind": chat_session.kind,
        "turn_id": event.turn_id,
        "source": event.source,
        "actor": event.actor,
        "status": event.status,
        "payload": _compact_value(event.payload_json),
    }
    if event.type == "turn.completed" and event.turn_id is not None:
        details["messages"] = [
            {
                "id": item.id,
                "role": item.role,
                "content": item.content[:1600],
            }
            for item in repositories.list_messages_for_turn(
                db,
                turn_id=event.turn_id,
            )
            if item.role in {"user", "assistant"}
        ]
    return details


def _event_summary(
    event: CognitiveEvent,
    *,
    details: dict[str, Any],
) -> str:
    messages = details.get("messages")
    if isinstance(messages, list) and messages:
        rendered = " | ".join(
            f"{item.get('role')}: {item.get('content')}"
            for item in messages
            if isinstance(item, dict)
        )
        return f"{event.type}: {rendered}"[:3600]
    payload = json.dumps(
        details.get("payload") or {},
        ensure_ascii=False,
        sort_keys=True,
    )
    return f"{event.type} from {event.source}: {payload}"[:3600]


def _initial_disposition(
    spec: WakeSourceSpec,
    *,
    episode_id: str | None,
) -> str:
    if spec.policy == "trace_only":
        return "trace_only"
    if spec.policy == "invalid":
        return "invalid"
    if spec.policy == "episode_evidence":
        return "episode_evidence" if episode_id is not None else "trace_only"
    if spec.policy == "required_wake":
        return "required_wake"
    return "pending_appraisal"


def _episode_for_event(
    db: Session,
    event: CognitiveEvent,
) -> str | None:
    if event.turn_id is None:
        return None
    activation = repositories.get_autonomous_activation_by_turn(
        db,
        turn_id=event.turn_id,
    )
    return activation.episode_id if activation is not None else None


def _record_signal_receipt_event(
    db: Session,
    *,
    session_id: str,
    receipt: CognitiveSignalReceipt,
) -> None:
    record_event(
        db,
        session_id=session_id,
        event_type="cognition.signal.dispositioned",
        payload={
            "receipt_id": receipt.id,
            "source_kind": receipt.source_kind,
            "source_key": receipt.source_key,
            "source_type": receipt.source_type,
            "policy": receipt.policy,
            "disposition": receipt.disposition,
            "candidate_id": receipt.candidate_id,
            "episode_id": receipt.episode_id,
            "registry_version": receipt.registry_version,
        },
        source="cognitive_workspace",
        actor="backend",
        visibility="private",
    )


def _candidate_payload(
    db: Session,
    candidate: CognitiveCandidate,
) -> dict[str, Any]:
    return {
        "id": candidate.id,
        "kind": candidate.candidate_kind,
        "status": candidate.status,
        "context_family": candidate.context_family,
        "claim": candidate.claim,
        "why_now": candidate.why_now,
        "cognitive_question": candidate.cognitive_question,
        "expected_transformation": candidate.expected_transformation,
        "uncertainty": candidate.uncertainty,
        "deferral_count": candidate.deferral_count,
        "created_at": candidate.created_at.isoformat(),
        "source_refs": [
            f"{item.source_kind}:{item.source_id}"
            for item in repositories.list_candidate_sources(
                db,
                candidate_id=candidate.id,
            )
        ],
        "linked_episode_id": candidate.selected_episode_id,
    }


def _parked_candidate_payload(
    db: Session,
    candidate: CognitiveCandidate,
) -> dict[str, Any]:
    """Keep re-appraisal compact while preserving navigable source identity."""

    payload = _candidate_payload(db, candidate)
    return {
        "id": payload["id"],
        "kind": payload["kind"],
        "context_family": payload["context_family"],
        "cognitive_question": payload["cognitive_question"],
        "expected_transformation": payload["expected_transformation"],
        "source_refs": payload["source_refs"],
    }


def _episode_payload(db: Session, episode: Any) -> dict[str, Any]:
    steps = repositories.list_episode_steps(
        db,
        episode_id=episode.id,
        limit=3,
    )
    return {
        "id": episode.id,
        "status": episode.status,
        "question": episode.question,
        "expected_transformation": episode.expected_transformation,
        "last_progress_at": _iso(episode.last_progress_at),
        "resume_condition": episode.resume_condition,
        "recent_steps": [
            {
                "progress": item.progress_summary,
                "next_step": item.next_step,
                "no_progress": item.no_progress,
                "created_at": item.created_at.isoformat(),
            }
            for item in steps
        ],
    }


def _selected_candidate_ids(
    decision: CognitiveIgnitionDecision,
    *,
    allowed_ids: set[str],
) -> list[str]:
    selected: list[str] = []
    for coalition in decision.coalitions:
        for candidate_id in coalition.candidate_ids:
            if candidate_id in allowed_ids and candidate_id not in selected:
                selected.append(candidate_id)
    return selected


def _pool_fingerprint(
    candidates: list[CognitiveCandidate],
    episodes: list[Any],
) -> str:
    payload = {
        "candidates": [
            {
                "id": item.id,
                "status": item.status,
                "updated_at": item.updated_at.isoformat(),
                "deferrals": item.deferral_count,
            }
            for item in candidates
        ],
        "episodes": [
            {
                "id": item.id,
                "status": item.status,
                "updated_at": item.updated_at.isoformat(),
            }
            for item in episodes
        ],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _volition_due_key(intention: IntentionRecord) -> str:
    return ":".join(
        [
            intention.id,
            _iso(intention.next_review_at) or "unscheduled",
            intention.updated_at.isoformat(),
        ]
    )


def _perception_context_family(event: PerceptionEvent) -> str:
    channel = event.channel.lower()
    if channel in {"notifications", "calendar", "messages", "email"}:
        return "human_personal_events"
    if channel in {"health", "activity", "movement"}:
        return "human_wellbeing"
    if channel in {"camera", "microphone", "audio", "video"}:
        return "human_device_observation"
    return "human_device_state"


def _compact_value(value: Any, *, limit: int = 4000) -> Any:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if len(encoded) <= limit:
        return value
    return {"truncated_json": encoded[:limit], "truncated": True}


def _provider_payload(result: LLMTextResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "model": result.model,
        "usage": result.usage,
        "provider_message_id": result.provider_message_id,
        "stop_reason": result.stop_reason,
        "text": result.text,
    }


def _parse_datetime(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

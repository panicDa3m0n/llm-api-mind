"""Adaptive, source-backed endogenous cognition over the shared workspace."""

from __future__ import annotations

from datetime import datetime, timedelta
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
from app.mind.endogenous_contracts import (
    ENDOGENOUS_SCHEMA_VERSION,
    ENDOGENOUS_SUBSTRATE_SUMMARY_MAX_CHARS,
    ENDOGENOUS_SYSTEM_PROMPT,
    EndogenousImpulseBatch,
    EndogenousSubstrateItem,
    endogenous_prompt,
)
from app.mind.workspace_contracts import (
    JSON_REPAIR_SYSTEM_PROMPT,
    repair_prompt,
)
from app.runtime.events import record_event
from app.runtime.time import aware_utc
from app.storage import repositories
from app.storage.models import (
    EndogenousCognitiveWindow,
    MemoryGraphNode,
    utc_now,
)


ProviderFactory = Callable[[Settings], LLMProvider]
ENDOGENOUS_TRACE_KIND = "cognition.endogenous"
KNOWN_CONTEXT_FAMILIES = {item.id for item in CONTEXT_FAMILIES}
FAMILY_FALLBACKS = {
    "personal_continuity": "session_continuity",
    "curiosity": "memory_continuity",
    "growth": "metacognitive_guidance",
    "relationship": "relationship_continuity",
    "responsibility": "agent_posture",
    "exploration": "memory_continuity",
    "creativity": "memory_continuity",
    "regulation": "agent_posture",
}


def run_endogenous_cognition_window(
    engine: Engine,
    *,
    settings: Settings,
    provider_factory: ProviderFactory,
    profile_id: str,
    session_id: str,
    now: datetime,
) -> dict[str, Any]:
    """Open one due free window and propose source-backed impulse seeds."""

    if not settings.endogenous_cognition_enabled:
        return {"status": "disabled"}

    current = aware_utc(now)
    with Session(engine) as db:
        latest = repositories.latest_endogenous_window(
            db,
            profile_id=profile_id,
        )
        latest = _window_snapshot(latest)
        if latest is not None:
            due_at = aware_utc(latest.next_window_at)
            if due_at > current:
                return {
                    "status": "waiting",
                    "window_id": latest.id,
                    "next_window_at": due_at.isoformat(),
                    "cadence_seconds": latest.cadence_seconds,
                }
            if latest.status == "opened":
                stale_after = aware_utc(latest.opened_at) + timedelta(
                    seconds=settings.endogenous_cognition_min_interval_seconds
                )
                if stale_after > current:
                    return {
                        "status": "in_progress",
                        "window_id": latest.id,
                        "next_window_at": due_at.isoformat(),
                    }
                repositories.complete_endogenous_window(
                    db,
                    window_id=latest.id,
                    status="failed",
                    cadence_seconds=settings.endogenous_cognition_min_interval_seconds,
                    next_window_at=current,
                    consecutive_empty_windows=latest.consecutive_empty_windows,
                    candidate_ids=latest.candidate_ids_json,
                    trace_id=latest.trace_id,
                    outcome={
                        **latest.outcome_json,
                        "failure": "stale_open_window_recovered",
                    },
                )
        substrate = _collect_substrate(
            db,
            profile_id=profile_id,
            session_id=session_id,
        )
        initial_cadence = _initial_cadence(settings, latest=latest)
        schedule_key = (
            f"{profile_id}:after:{latest.id}"
            if latest is not None
            else f"{profile_id}:initial"
        )
        window, created = repositories.create_endogenous_window(
            db,
            schedule_key=schedule_key,
            profile_id=profile_id,
            opened_at=current,
            cadence_seconds=initial_cadence,
            next_window_at=current + timedelta(seconds=initial_cadence),
            consecutive_empty_windows=(
                latest.consecutive_empty_windows if latest is not None else 0
            ),
            substrate=[item.model_dump(mode="json") for item in substrate],
            source_refs=[item.source_ref for item in substrate],
        )
        window = _window_snapshot(window)
        if window is None:
            raise RuntimeError("Failed to snapshot the endogenous cognitive window")
        if not created:
            return {
                "status": "in_progress",
                "window_id": window.id,
                "next_window_at": window.next_window_at.isoformat(),
                "cadence_seconds": window.cadence_seconds,
            }
        record_event(
            db,
            session_id=session_id,
            event_type="cognition.free_window.opened",
            payload={
                "window_id": window.id,
                "opened_at": current.isoformat(),
                "source_count": len(substrate),
                "meaning": "available_internal_cognitive_time",
                "not_evidence_of": ["boredom", "need", "mood", "urgency"],
            },
            source="endogenous_cognition",
            actor="backend",
            visibility="private",
        )

    if not substrate:
        return _complete_without_seed(
            engine,
            settings=settings,
            session_id=session_id,
            window=window,
            current=current,
            previous=latest,
            reason="No source-backed substrate was available.",
        )

    aux_settings = auxiliary_provider_settings(settings)
    prompt = endogenous_prompt(
        window_id=window.id,
        opened_at=current.isoformat(),
        substrate=substrate,
        max_seeds=settings.endogenous_cognition_max_seeds,
    )
    try:
        provider = provider_factory(aux_settings)
        result, parsed, repaired = _structured_call(
            provider=provider,
            prompt=prompt,
            max_tokens=settings.endogenous_cognition_max_tokens,
        )
    except (LLMConfigurationError, LLMRequestError) as exc:
        return _complete_provider_failure(
            engine,
            settings=settings,
            session_id=session_id,
            window=window,
            current=current,
            previous=latest,
            error=str(exc),
        )

    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            kind=ENDOGENOUS_TRACE_KIND,
            payload={
                "operation": "cognition.endogenous.synthesize",
                "window_id": window.id,
                "status": "completed" if parsed is not None else "invalid_output",
                "model": result.model,
                "substrate": [item.model_dump(mode="json") for item in substrate],
                "provider": _provider_payload(result),
                "repair_provider": (
                    _provider_payload(repaired) if repaired is not None else None
                ),
                "parsed": (
                    parsed.model_dump(mode="json") if parsed is not None else None
                ),
            },
        )
        if parsed is None:
            cadence, empty_count = _empty_cadence(
                settings,
                previous=latest,
            )
            completed = repositories.complete_endogenous_window(
                db,
                window_id=window.id,
                status="invalid_output",
                cadence_seconds=cadence,
                next_window_at=current + timedelta(seconds=cadence),
                consecutive_empty_windows=empty_count,
                candidate_ids=[],
                trace_id=trace.id,
                outcome={
                    "seed_count": 0,
                    "reason": "invalid_auxiliary_output_after_one_repair",
                    "model": result.model,
                },
            )
            _record_window_completed(
                db,
                session_id=session_id,
                window=completed,
            )
            return _window_result(completed)

        candidate_ids = _persist_seeds(
            db,
            settings=settings,
            profile_id=profile_id,
            window=window,
            substrate=substrate,
            parsed=parsed,
            model=result.model,
            trace_id=trace.id,
        )
        if candidate_ids:
            cadence = settings.endogenous_cognition_productive_followup_seconds
            empty_count = 0
            status = "seeds_proposed"
        else:
            cadence, empty_count = _empty_cadence(
                settings,
                previous=latest,
            )
            status = "empty"
        completed = repositories.complete_endogenous_window(
            db,
            window_id=window.id,
            status=status,
            cadence_seconds=cadence,
            next_window_at=current + timedelta(seconds=cadence),
            consecutive_empty_windows=empty_count,
            candidate_ids=candidate_ids,
            trace_id=trace.id,
            outcome={
                "seed_count": len(candidate_ids),
                "no_seed_reason": parsed.no_seed_reason,
                "model": result.model,
                "authority": "provisional_m2.7",
            },
        )
        _record_window_completed(
            db,
            session_id=session_id,
            window=completed,
        )
        return _window_result(completed)


def record_endogenous_activation_feedback(
    db: Session,
    *,
    activation: Any,
) -> None:
    """Attach lifecycle evidence without semantically judging Scarlet's choice."""

    endogenous = activation.workspace_json.get("endogenous")
    if not isinstance(endogenous, dict):
        return
    window_id = endogenous.get("window_id")
    if not isinstance(window_id, str) or not window_id:
        return
    candidate_states: list[dict[str, Any]] = []
    for candidate_id in activation.workspace_json.get("selected_candidate_ids", []):
        if not isinstance(candidate_id, str):
            continue
        candidate = repositories.get_candidate(db, candidate_id)
        if candidate is None:
            continue
        candidate_states.append(
            {
                "candidate_id": candidate.id,
                "status": candidate.status,
                "selected_episode_id": candidate.selected_episode_id,
                "resolution": candidate.resolution,
            }
        )
    transformation_observed = any(
        item["status"] in {"selected", "resolved", "rejected"}
        or item["selected_episode_id"] is not None
        for item in candidate_states
    )
    repositories.record_endogenous_activation_outcome(
        db,
        window_id=window_id,
        activation_id=activation.id,
        outcome={
            "status": activation.status,
            "turn_id": activation.turn_id,
            "candidate_states": candidate_states,
            "transformation_observed": transformation_observed,
            "recorded_at": utc_now().isoformat(),
        },
    )
    record_event(
        db,
        session_id=activation.session_id,
        turn_id=activation.turn_id,
        event_type="cognition.endogenous.activation_observed",
        payload={
            "window_id": window_id,
            "activation_id": activation.id,
            "activation_status": activation.status,
            "transformation_observed": transformation_observed,
            "candidate_states": candidate_states,
        },
        source="endogenous_cognition",
        actor="backend",
        visibility="private",
    )


def _collect_substrate(
    db: Session,
    *,
    profile_id: str,
    session_id: str,
) -> list[EndogenousSubstrateItem]:
    items: list[EndogenousSubstrateItem] = []

    for state in repositories.list_session_summary_states(
        db,
        exclude_session_id=session_id,
        limit=3,
        kind="human_dialogue",
        profile_id=profile_id,
    ):
        summary = (
            state.summary.summary
            if state.summary is not None and state.summary_state == "current"
            else "Sessione con riassunto mancante o non aggiornato; ispezionare per i dettagli."
        )
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"session:{state.chat_session.id}",
                source_kind="session",
                context_family="session_continuity",
                observed_at=(
                    state.last_message_at or state.chat_session.updated_at
                ).isoformat(),
                summary=_substrate_summary(summary),
                details={
                    "updated_at": state.chat_session.updated_at.isoformat(),
                    "turn_count": state.turn_count,
                    "summary_state": state.summary_state,
                },
            )
        )

    memories = repositories.list_recent_memories_by_activity(db, limit=6)
    for memory in memories:
        graph_nodes = repositories.list_memory_graph_nodes(
            db,
            source_memory_id=memory.id,
            limit=8,
        )
        graph_edges = repositories.list_memory_graph_edges(
            db,
            source_memory_id=memory.id,
            limit=8,
        )
        node_by_id: dict[str, MemoryGraphNode] = {
            item.id: item for item in graph_nodes
        }
        for edge in graph_edges:
            for node_id in (edge.source_node_id, edge.target_node_id):
                if node_id in node_by_id:
                    continue
                node = db.get(MemoryGraphNode, node_id)
                if node is not None:
                    node_by_id[node.id] = node
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"memory:{memory.id}",
                source_kind="memory",
                context_family="memory_continuity",
                observed_at=(memory.last_used_at or memory.updated_at).isoformat(),
                summary=_substrate_summary(memory.content),
                details={
                    "type": memory.memory_type,
                    "scope": memory.scope,
                    "created_at": memory.created_at.isoformat(),
                    "updated_at": memory.updated_at.isoformat(),
                    "source_session_id": memory.source_session_id,
                    "source_turn_id": memory.source_turn_id,
                    "source_message_id": memory.source_message_id,
                    "associative_neighborhood": {
                        "nodes": [
                            {
                                "id": node.id,
                                "type": node.node_type,
                                "label": node.label,
                            }
                            for node in node_by_id.values()
                        ],
                        "edges": [
                            {
                                "id": edge.id,
                                "source_node_id": edge.source_node_id,
                                "target_node_id": edge.target_node_id,
                                "relation": edge.relation,
                            }
                            for edge in graph_edges
                        ],
                        "navigation": f"memory graph {memory.id}",
                    },
                },
            )
        )

    for focus in repositories.list_active_focus_records(
        db,
        owner_profile_id=profile_id,
    )[:2]:
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"focus:{focus.id}",
                source_kind="focus",
                context_family="foreground_attention",
                observed_at=focus.updated_at.isoformat(),
                summary=_substrate_summary(focus.focus_object),
                details={
                    "status": focus.status,
                    "type": focus.focus_type,
                    "reason": focus.reason,
                    "duration_policy": focus.duration_policy,
                },
            )
        )

    for intention in repositories.list_open_intention_records(
        db,
        owner_profile_id=profile_id,
        limit=8,
    ):
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"intention:{intention.id}",
                source_kind="intention",
                context_family="agent_posture",
                observed_at=intention.updated_at.isoformat(),
                summary=_substrate_summary(intention.desire),
                details={
                    "status": intention.status,
                    "reason": intention.reason,
                    "horizon": intention.horizon,
                    "next_possible_reflection": intention.next_possible_reflection,
                    "next_review_at": _iso(intention.next_review_at),
                },
            )
        )

    episodes = [
        *repositories.list_episodes(
            db,
            profile_id=profile_id,
            status="active",
            limit=6,
        ),
        *repositories.list_episodes(
            db,
            profile_id=profile_id,
            status="suspended",
            limit=6,
        ),
    ]
    for episode in episodes:
        expectations = repositories.list_expectations(
            db,
            episode_id=episode.id,
        )
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"episode:{episode.id}",
                source_kind="episode",
                context_family="agent_posture",
                observed_at=episode.updated_at.isoformat(),
                summary=_substrate_summary(episode.question),
                details={
                    "status": episode.status,
                    "expected_transformation": episode.expected_transformation,
                    "resume_condition": episode.resume_condition,
                    "suspended_until": _iso(episode.suspended_until),
                    "expectations": [
                        {
                            "id": item.id,
                            "status": item.status,
                            "claim": item.claim,
                            "observable_outcome": item.observable_outcome,
                            "due_at": _iso(item.due_at),
                        }
                        for item in expectations
                    ],
                },
            )
        )

    affect = repositories.get_latest_affect_state(
        db,
        owner_profile_id=profile_id,
    )
    if affect is not None:
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"affect:{affect.id}",
                source_kind="affect",
                context_family="affective_posture",
                observed_at=affect.updated_at.isoformat(),
                summary=(
                    f"Current appraised affective posture: {affect.emotion} "
                    f"({affect.intensity_label})."
                ),
                details={
                    "mode": affect.mode,
                    "emotion": affect.emotion,
                    "intensity_label": affect.intensity_label,
                    "tendencies": affect.tendencies_json,
                },
            )
        )

    for event in repositories.list_perception_events(
        db,
        profile_id=profile_id,
        limit=12,
    ):
        if not event.source.startswith("device_exploration_adapter"):
            continue
        items.append(
            EndogenousSubstrateItem(
                source_ref=f"perception:{event.id}",
                source_kind="perception",
                context_family=_device_context_family(event.channel),
                observed_at=event.observed_at.isoformat(),
                summary=(
                    f"Device-sourced transition on {event.channel}: "
                    f"{event.event_type}."
                ),
                details={
                    "source": event.source,
                    "payload": event.payload_json,
                    "navigation": event.navigation_json,
                    "perspective": "human_device_not_scarlet_sensor",
                },
            )
        )

    deduplicated: dict[str, EndogenousSubstrateItem] = {}
    for item in items:
        deduplicated.setdefault(item.source_ref, item)
    return list(deduplicated.values())[:40]


def _substrate_summary(value: str) -> str:
    normalized = value.strip()
    if len(normalized) <= ENDOGENOUS_SUBSTRATE_SUMMARY_MAX_CHARS:
        return normalized
    return (
        normalized[: ENDOGENOUS_SUBSTRATE_SUMMARY_MAX_CHARS - 3].rstrip()
        + "..."
    )


def _persist_seeds(
    db: Session,
    *,
    settings: Settings,
    profile_id: str,
    window: EndogenousCognitiveWindow,
    substrate: list[EndogenousSubstrateItem],
    parsed: EndogenousImpulseBatch,
    model: str,
    trace_id: str,
) -> list[str]:
    by_ref = {item.source_ref: item for item in substrate}
    candidate_ids: list[str] = []
    for seed in parsed.seeds[: settings.endogenous_cognition_max_seeds]:
        refs = sorted(set(seed.source_refs))
        if not refs or any(ref not in by_ref for ref in refs):
            continue
        context_family = (
            seed.context_family
            if seed.context_family in KNOWN_CONTEXT_FAMILIES
            else FAMILY_FALLBACKS[seed.impulse_family]
        )
        fingerprint = _candidate_fingerprint(
            profile_id=profile_id,
            candidate_kind=f"endogenous_{seed.impulse_family}",
            claim=seed.claim,
            source_refs=refs,
        )
        candidate, _ = repositories.create_candidate(
            db,
            profile_id=profile_id,
            candidate_kind=f"endogenous_{seed.impulse_family}",
            context_family=context_family,
            claim=seed.claim,
            why_now=seed.why_now,
            cognitive_question=seed.cognitive_question,
            expected_transformation=seed.expected_transformation,
            uncertainty=seed.uncertainty,
            exact_fingerprint=fingerprint,
            sources=[
                {
                    "source_kind": ref.split(":", 1)[0],
                    "source_id": ref.split(":", 1)[1],
                    "observed_at": _parse_datetime(by_ref[ref].observed_at),
                    "metadata": {
                        "endogenous_window_id": window.id,
                        "impulse_family": seed.impulse_family,
                    },
                }
                for ref in refs
            ],
            appraisal_model=model,
            appraisal_trace_id=trace_id,
            metadata={
                "origin": "endogenous_cognition",
                "endogenous_window_id": window.id,
                "impulse_family": seed.impulse_family,
                "wake_recommendation": seed.wake_recommendation,
                "appraisal_reason": seed.reason,
                "authority": "provisional_m2.7",
                "m3_endorsement_required": True,
            },
        )
        if candidate.status in {"proposed", "suspended"}:
            candidate_ids.append(candidate.id)
    return list(dict.fromkeys(candidate_ids))


def _complete_without_seed(
    engine: Engine,
    *,
    settings: Settings,
    session_id: str,
    window: EndogenousCognitiveWindow,
    current: datetime,
    previous: EndogenousCognitiveWindow | None,
    reason: str,
) -> dict[str, Any]:
    with Session(engine) as db:
        cadence, empty_count = _empty_cadence(settings, previous=previous)
        completed = repositories.complete_endogenous_window(
            db,
            window_id=window.id,
            status="empty",
            cadence_seconds=cadence,
            next_window_at=current + timedelta(seconds=cadence),
            consecutive_empty_windows=empty_count,
            candidate_ids=[],
            trace_id=None,
            outcome={"seed_count": 0, "no_seed_reason": reason},
        )
        _record_window_completed(db, session_id=session_id, window=completed)
        return _window_result(completed)


def _complete_provider_failure(
    engine: Engine,
    *,
    settings: Settings,
    session_id: str,
    window: EndogenousCognitiveWindow,
    current: datetime,
    previous: EndogenousCognitiveWindow | None,
    error: str,
) -> dict[str, Any]:
    with Session(engine) as db:
        trace = repositories.add_trace(
            db,
            session_id=session_id,
            kind=ENDOGENOUS_TRACE_KIND,
            payload={
                "operation": "cognition.endogenous.synthesize",
                "window_id": window.id,
                "status": "provider_error",
                "model": auxiliary_provider_model(settings),
                "error": error,
            },
        )
        cadence = settings.endogenous_cognition_min_interval_seconds
        completed = repositories.complete_endogenous_window(
            db,
            window_id=window.id,
            status="provider_error",
            cadence_seconds=cadence,
            next_window_at=current + timedelta(seconds=cadence),
            consecutive_empty_windows=(
                previous.consecutive_empty_windows if previous is not None else 0
            ),
            candidate_ids=[],
            trace_id=trace.id,
            outcome={"seed_count": 0, "provider_error": error},
        )
        _record_window_completed(db, session_id=session_id, window=completed)
        return _window_result(completed)


def _record_window_completed(
    db: Session,
    *,
    session_id: str,
    window: EndogenousCognitiveWindow,
) -> None:
    record_event(
        db,
        session_id=session_id,
        event_type=(
            "cognition.endogenous.seeds_proposed"
            if window.candidate_ids_json
            else "cognition.endogenous.window_empty"
        ),
        payload={
            "window_id": window.id,
            "status": window.status,
            "candidate_ids": window.candidate_ids_json,
            "source_refs": window.source_refs_json,
            "next_window_at": window.next_window_at.isoformat(),
            "cadence_seconds": window.cadence_seconds,
            "consecutive_empty_windows": window.consecutive_empty_windows,
            "trace_id": window.trace_id,
        },
        source="endogenous_cognition",
        actor="backend",
        visibility="private",
        trace_id=window.trace_id,
    )


def _initial_cadence(
    settings: Settings,
    *,
    latest: EndogenousCognitiveWindow | None,
) -> int:
    if latest is None:
        return settings.endogenous_cognition_base_interval_seconds
    return max(
        settings.endogenous_cognition_min_interval_seconds,
        min(
            latest.cadence_seconds,
            settings.endogenous_cognition_max_interval_seconds,
        ),
    )


def _empty_cadence(
    settings: Settings,
    *,
    previous: EndogenousCognitiveWindow | None,
) -> tuple[int, int]:
    empty_count = (
        (previous.consecutive_empty_windows + 1) if previous is not None else 1
    )
    previous_cadence = (
        previous.cadence_seconds
        if previous is not None
        else settings.endogenous_cognition_base_interval_seconds
    )
    cadence = min(
        settings.endogenous_cognition_max_interval_seconds,
        max(
            settings.endogenous_cognition_base_interval_seconds,
            previous_cadence * 2,
        ),
    )
    return cadence, empty_count


def _structured_call(
    *,
    provider: LLMProvider,
    prompt: str,
    max_tokens: int,
) -> tuple[
    LLMTextResult,
    EndogenousImpulseBatch | None,
    LLMTextResult | None,
]:
    result = provider.generate_text(
        prompt=prompt,
        system=ENDOGENOUS_SYSTEM_PROMPT,
        max_tokens=max_tokens,
    )
    parsed = _parse_batch(result.text)
    repaired: LLMTextResult | None = None
    if parsed is None:
        repaired = provider.generate_text(
            prompt=repair_prompt(
                malformed=result.text,
                schema_name=ENDOGENOUS_SCHEMA_VERSION,
            ),
            system=JSON_REPAIR_SYSTEM_PROMPT,
            max_tokens=max_tokens,
        )
        parsed = _parse_batch(repaired.text)
    return result, parsed, repaired


def _parse_batch(text: str) -> EndogenousImpulseBatch | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        return EndogenousImpulseBatch.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return None


def _candidate_fingerprint(
    *,
    profile_id: str,
    candidate_kind: str,
    claim: str,
    source_refs: list[str],
) -> str:
    payload = {
        "profile_id": profile_id,
        "candidate_kind": candidate_kind,
        "claim": " ".join(claim.lower().split()),
        "source_refs": sorted(set(source_refs)),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _window_result(window: EndogenousCognitiveWindow) -> dict[str, Any]:
    return {
        "status": window.status,
        "window_id": window.id,
        "candidate_ids": window.candidate_ids_json,
        "source_count": len(window.source_refs_json),
        "trace_id": window.trace_id,
        "next_window_at": window.next_window_at.isoformat(),
        "cadence_seconds": window.cadence_seconds,
        "consecutive_empty_windows": window.consecutive_empty_windows,
        "outcome": window.outcome_json,
    }


def _window_snapshot(
    window: EndogenousCognitiveWindow | None,
) -> EndogenousCognitiveWindow | None:
    """Detach loaded window state from commit-driven ORM expiration."""

    if window is None:
        return None
    return EndogenousCognitiveWindow.model_validate(window.model_dump())


def _device_context_family(channel: str) -> str:
    if channel == "notifications":
        return "human_personal_events"
    return "human_device_state"


def _provider_payload(result: LLMTextResult) -> dict[str, Any]:
    return {
        "model": result.model,
        "text": result.text,
        "usage": result.usage,
        "provider_message_id": result.provider_message_id,
        "stop_reason": result.stop_reason,
    }


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return aware_utc(parsed)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None

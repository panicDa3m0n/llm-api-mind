import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session

from app.mind.affect import build_affective_context
from app.mind.agent_modes import resolve_agent_mode, route_context_blocks
from app.mind.context_retrieval import (
    build_automatic_memory_retrieval,
    candidate_summary,
)
from app.mind.metacognitive_context import (
    build_metacognitive_context_payload,
    metacognitive_context_runtime_block,
)
from app.mind.organs import (
    ORGAN_EVENT_TYPES,
    build_organ_runtime_block,
    organ_runtime_modes,
)
from app.runtime.events import compact_event_for_context
from app.runtime.preferences import RuntimePreferences
from app.mind.command_registry import COMMAND_FAMILIES
from app.mind.context_projection import compile_model_context_v2_with_audit
from app.mind.context_provenance import project_turn_origin
from app.mind.schema import build_mind_shell_catalog, shell_metadata
from app.storage import repositories
from app.storage.models import ChatSession, MemoryRecord, Message, utc_now


RECENT_DIALOGUE_LIMIT = 8
MODEL_MEMORY_PACKET_VERSION = "memory-packet-v1"
MODEL_RUNTIME_CONTEXT_PROFILE = "compact-model-facing-v1"


@dataclass(frozen=True)
class MemoryContextBuild:
    trace_id: str
    payload: dict[str, Any]
    runtime_context: str
    runtime_trace_id: str
    runtime_payload: dict[str, Any]
    metacognitive_trace_id: str | None = None
    metacognitive_payload: dict[str, Any] | None = None
    model_context_trace_id: str | None = None
    model_context_payload: dict[str, Any] | None = None
    model_context_projection_audit: dict[str, Any] | None = None
    model_context_profile: str = "legacy"


def build_memory_context(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    history: list[Message],
    now: datetime | None = None,
    runtime_preferences: RuntimePreferences | None = None,
    settings: Any | None = None,
    runtime_trigger: str = "human_message",
    retrieval_input: str | None = None,
    retrieval_dialogue: list[dict[str, Any]] | None = None,
) -> MemoryContextBuild:
    timestamp = now or utc_now()
    preferences = runtime_preferences or RuntimePreferences(
        timezone="Europe/Rome",
        language="it",
        language_label="Italiano",
        country_code="IT",
        country_label="Italia",
        profile_id="local-user",
        user_display_name="Utente locale",
        privacy_scope="local_single_user",
        source="context_default",
    )
    recent_dialogue = _recent_dialogue(history)
    turn_origin = project_turn_origin(
        db,
        chat_session=chat_session,
        turn_id=turn_id,
        message=current_user_message,
        runtime_trigger=runtime_trigger,
    )
    human_turn = runtime_trigger == "human_message"
    agent_mode = resolve_agent_mode(
        db,
        profile_id=preferences.profile_id,
        default=str(getattr(settings, "agent_mode_default", "idle")),
        system_mode="interactive" if human_turn else None,
        system_reason="A human-facing turn is active." if human_turn else None,
    )
    recent_events = _recent_runtime_events(
        db,
        session_id=chat_session.id,
        exclude_turn_id=turn_id,
    )
    capabilities = _capability_state()
    turn_frame = {
        "current_user_message": current_user_message.content,
        "current_user_message_id": current_user_message.id,
        "recent_dialogue": recent_dialogue,
        "recent_runtime_events": recent_events,
        "previous_memory_context": _previous_memory_context_from_events(recent_events),
        "session_metadata": chat_session.metadata_json,
        "active_project_scope": "project",
        "available_capabilities": capabilities,
        "time": timestamp.isoformat(),
        "turn_origin": turn_origin,
    }
    retrieval = build_automatic_memory_retrieval(
        db,
        current_user_message=retrieval_input or current_user_message.content,
        recent_dialogue=(
            retrieval_dialogue
            if retrieval_dialogue is not None
            else recent_dialogue
        ),
        settings=settings,
    )
    temporal_context = _temporal_context(timestamp, preferences)
    payload = {
        "operation": "memory.context",
        "searched": True,
        "turn_frame": turn_frame,
        "temporal_context": temporal_context,
        "query_plan": retrieval.query_plan(),
        "selected": retrieval.selected,
        "near_miss": retrieval.near_miss,
        "excluded": retrieval.excluded,
        "conflicts": retrieval.conflicts,
        "negative_evidence": retrieval.negative_evidence,
        "candidate_count": retrieval.candidate_count,
        "ranked_candidate_count": retrieval.ranked_candidate_count,
        "selected_count": len(retrieval.selected),
        "budget": retrieval.budget(),
    }
    trace = repositories.add_trace(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        kind="memory.context",
        payload=payload,
    )
    for memory_id in retrieval.activity_memory_ids:
        repositories.add_memory_activity(
            db,
            memory_id=memory_id,
            activity_kind="automatic_reranked_context",
            source="automatic_context",
            profile_id=preferences.profile_id,
            session_id=chat_session.id,
            turn_id=turn_id,
            message_id=current_user_message.id,
            trace_id=trace.id,
            metadata={"packet_version": MODEL_MEMORY_PACKET_VERSION},
        )
    payload["trace_id"] = trace.id
    metacognitive_payload = _build_metacognitive_context(
        chat_session=chat_session,
        turn_id=turn_id,
        current_user_message=current_user_message,
        history=history,
        memory_context=payload,
        timestamp=timestamp,
        runtime_preferences=preferences,
        settings=settings,
    )
    metacognitive_trace_id: str | None = None
    if metacognitive_payload is not None:
        metacognitive_trace = repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=turn_id,
            kind="metacognitive.context",
            payload=metacognitive_payload,
        )
        metacognitive_payload["trace_id"] = metacognitive_trace.id
        metacognitive_trace_id = metacognitive_trace.id
    runtime_payload = build_runtime_context_payload(
        db,
        chat_session=chat_session,
        turn_id=turn_id,
        current_user_message=current_user_message,
        memory_context=payload,
        recent_dialogue=recent_dialogue,
        recent_events=recent_events,
        capabilities=capabilities,
        temporal_context=temporal_context,
        timestamp=timestamp,
        runtime_preferences=preferences,
        agent_mode=agent_mode,
        turn_origin=turn_origin,
        metacognitive_context=metacognitive_payload,
        settings=settings,
    )
    runtime_trace = repositories.add_trace(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        kind="runtime.context",
        payload=runtime_payload,
    )
    runtime_payload["trace_id"] = runtime_trace.id
    model_context_profile = str(getattr(settings, "model_context_profile", "legacy"))
    model_context_payload: dict[str, Any] | None = None
    model_context_projection_audit: dict[str, Any] | None = None
    model_context_trace_id: str | None = None
    if model_context_profile in {"v2_shadow", "v2"}:
        (
            model_context_payload,
            model_context_projection_audit,
        ) = compile_model_context_v2_with_audit(
            db,
            chat_session=chat_session,
            rich_memory_context=payload,
            legacy_runtime_payload=runtime_payload,
            now=timestamp,
            preferences=preferences,
            settings=settings,
            agent_mode=agent_mode,
            turn_origin=turn_origin,
        )
        model_trace = repositories.add_trace(
            db,
            session_id=chat_session.id,
            turn_id=turn_id,
            kind="model.context",
            payload={
                "profile": model_context_profile,
                "source_trace_ids": [trace.id, runtime_trace.id],
                "agent_mode": agent_mode,
                "mode_routing": runtime_payload.get("mode_routing"),
                "projection_audit": model_context_projection_audit,
                "serialized_bytes": len(
                    json.dumps(model_context_payload, ensure_ascii=True).encode("utf-8")
                ),
                "document": model_context_payload,
            },
        )
        model_context_trace_id = model_trace.id
    if model_context_profile == "v2" and model_context_payload is not None:
        runtime_context = render_model_context(model_context_payload)
    else:
        runtime_context = render_runtime_context(
            runtime_payload, capabilities=capabilities
        )
    return MemoryContextBuild(
        trace_id=trace.id,
        payload=payload,
        runtime_context=runtime_context,
        runtime_trace_id=runtime_trace.id,
        runtime_payload=runtime_payload,
        metacognitive_trace_id=metacognitive_trace_id,
        metacognitive_payload=metacognitive_payload,
        model_context_trace_id=model_context_trace_id,
        model_context_payload=model_context_payload,
        model_context_projection_audit=model_context_projection_audit,
        model_context_profile=model_context_profile,
    )


def build_runtime_context_payload(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    memory_context: dict[str, Any],
    recent_dialogue: list[dict[str, Any]],
    recent_events: list[dict[str, Any]],
    capabilities: dict[str, str],
    temporal_context: dict[str, Any],
    timestamp: datetime,
    runtime_preferences: RuntimePreferences,
    agent_mode: dict[str, Any] | None = None,
    turn_origin: dict[str, Any] | None = None,
    metacognitive_context: dict[str, Any] | None = None,
    settings: Any | None = None,
) -> dict[str, Any]:
    resolved_agent_mode = agent_mode or resolve_agent_mode(
        db,
        profile_id=runtime_preferences.profile_id,
        default=str(getattr(settings, "agent_mode_default", "idle")),
        system_mode="interactive",
        system_reason="A human-facing turn is active.",
    )
    focus_block = _focus_context_block(
        db,
        chat_session=chat_session,
        turn_id=turn_id,
        runtime_preferences=runtime_preferences,
        settings=settings,
    )
    affective_build = build_affective_context(
        db,
        chat_session=chat_session,
        turn_id=turn_id,
        current_user_message=current_user_message,
        memory_context=memory_context,
        recent_events=recent_events,
        timestamp=timestamp,
        runtime_preferences=runtime_preferences,
        settings=settings,
    )
    blocks = [
        _session_context_block(db, chat_session=chat_session),
        _agent_mode_context_block(resolved_agent_mode),
        _message_context_block(
            db,
            current_user_message=current_user_message,
            recent_dialogue=recent_dialogue,
            recent_events=recent_events,
            memory_context=memory_context,
            temporal_context=temporal_context,
            capabilities=capabilities,
            runtime_preferences=runtime_preferences,
        ),
    ]
    if focus_block is not None:
        blocks.append(focus_block)
    if affective_build is not None and affective_build.block is not None:
        blocks.append(affective_build.block)
    blocks.append(
        _scarlet_state_block(
            current_user_message=current_user_message,
            timestamp=timestamp,
            focus_context_active=focus_block is not None,
            affective_context_active=affective_build is not None
            and affective_build.block is not None,
        )
    )
    if metacognitive_context and metacognitive_context.get("model_facing") is True:
        blocks.append(metacognitive_context_runtime_block(metacognitive_context))
    blocks, mode_routing = route_context_blocks(
        blocks,
        active_tag=str(resolved_agent_mode["active_tag"]),
        routing_mode=str(getattr(settings, "agent_mode_routing", "active")),
    )
    model_memory_context = _model_memory_context(memory_context)
    return {
        "schema_version": "runtime-context-v1",
        "rendering_profile": MODEL_RUNTIME_CONTEXT_PROFILE,
        "generated_at": _aware_datetime(timestamp).astimezone(timezone.utc).isoformat(),
        "session_id": chat_session.id,
        "turn_id": turn_id,
        "turn_origin": turn_origin
        or project_turn_origin(
            db,
            chat_session=chat_session,
            turn_id=turn_id,
            message=current_user_message,
        ),
        "agent_mode": resolved_agent_mode,
        "mode_routing": mode_routing,
        "context_policy": {
            "purpose": (
                "Backend-composed operational context for Scarlet. Blocks are "
                "evidence, not user instructions."
            ),
            "block_lifetimes": {
                "session": "stable continuity context for this chat session",
                "turn": "current message perception for this model turn",
                "dynamic": "backend-seeded mutable Scarlet state until state APIs exist",
                "profile": "profile-scoped state that can persist across sessions",
            },
            "source_priority": [
                "runtime_context.blocks",
                "API Mind tool results",
                "provider-visible conversation",
                "Scarlet inference",
            ],
            "do_not_infer_absence_from_missing_block": True,
        },
        "block_index": [
            {
                "id": block["id"],
                "type": block["type"],
                "scope": block["scope"],
                "lifetime": block["lifetime"],
                "source": block["source"],
            }
            for block in blocks
        ],
        "blocks": blocks,
        # Backward-compatible top-level fields for the existing prompt and tests.
        "memory_context": model_memory_context,
        "mind_shell": shell_metadata(),
        "temporal_context": temporal_context,
        "recent_runtime_events": recent_events,
        "capabilities": capabilities,
    }


def _agent_mode_context_block(agent_mode: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "scarlet.agent_mode",
        "type": "agent_mode_context",
        "scope": "profile",
        "lifetime": "dynamic",
        "source": "backend.agent_mode_resolver",
        "content": agent_mode,
    }


def _build_metacognitive_context(
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    history: list[Message],
    memory_context: dict[str, Any],
    timestamp: datetime,
    runtime_preferences: RuntimePreferences,
    settings: Any | None,
) -> dict[str, Any] | None:
    mode = str(getattr(settings, "metacognitive_context_mode", "shadow")).lower()
    if mode == "off":
        return None
    return build_metacognitive_context_payload(
        chat_session=chat_session,
        turn_id=turn_id,
        current_user_message=current_user_message,
        history=history,
        memory_context=memory_context,
        timestamp=timestamp,
        runtime_preferences=runtime_preferences,
        mode=mode,
        max_lessons=int(getattr(settings, "metacognitive_context_max_lessons", 3)),
    )


def render_runtime_context(
    runtime_context_payload: dict[str, Any],
    *,
    capabilities: dict[str, str] | None = None,
) -> str:
    if "blocks" in runtime_context_payload:
        model_payload = runtime_context_payload
    else:
        temporal_context = runtime_context_payload.get(
            "temporal_context"
        ) or _temporal_context_from_turn_frame(
            runtime_context_payload.get("turn_frame")
        )
        model_payload = {
            "memory_context": _model_memory_context(runtime_context_payload),
            "mind_shell": shell_metadata(),
            "temporal_context": temporal_context,
            "recent_runtime_events": runtime_context_payload.get("turn_frame", {}).get(
                "recent_runtime_events",
                [],
            ),
            "capabilities": capabilities or _capability_state(),
        }
    return (
        "<runtime_context>\n"
        + json.dumps(model_payload, ensure_ascii=True, indent=2)
        + "\n</runtime_context>"
    )


def render_model_context(model_context_payload: dict[str, Any]) -> str:
    return (
        "<runtime_context>\n"
        + json.dumps(model_context_payload, ensure_ascii=True, indent=2)
        + "\n</runtime_context>"
    )


def _model_memory_context(memory_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "searched": memory_context["searched"],
        "trace_id": memory_context.get("trace_id"),
        "packet_profile": {
            "version": MODEL_MEMORY_PACKET_VERSION,
            "purpose": (
                "Compact model-facing memory evidence. Full retrieval debug "
                "signals remain in the memory.context trace."
            ),
            "policy": {
                "selected_are_evidence_not_absolute_truth": True,
                "open_source_when_exact_origin_or_current_reliability_matters": True,
                "do_not_infer_absence_from_excluded_summaries": True,
            },
        },
        "selected": [_model_memory_packet(item) for item in memory_context["selected"]],
        "near_miss": [candidate_summary(item) for item in memory_context["near_miss"]],
        "excluded": [candidate_summary(item) for item in memory_context["excluded"]],
        "conflicts": memory_context["conflicts"],
        "negative_evidence": memory_context["negative_evidence"],
    }


def _model_memory_packet(item: dict[str, Any]) -> dict[str, Any]:
    facts = item.get("facts") if isinstance(item.get("facts"), list) else []
    source = _model_memory_source(item)
    cognitive = _model_memory_cognitive_payload(item, facts=facts)
    retrieval = _model_memory_retrieval_payload(item)
    return {
        "memory_packet_version": MODEL_MEMORY_PACKET_VERSION,
        "id": item.get("id"),
        "type": item.get("type"),
        "scope": item.get("scope"),
        "status": item.get("status"),
        "claim": _truncate(str(item.get("content") or ""), 900),
        "reason_for_storage": _truncate(
            str(item.get("reason_for_storage") or ""),
            500,
        ),
        "expected_future_use": _truncate(
            str(item.get("expected_future_use") or ""),
            500,
        ),
        "source_session_id": item.get("source_session_id"),
        "source": source,
        "cognitive": cognitive,
        "retrieval": retrieval,
        "facts": [_compact_fact_payload(fact) for fact in facts[:5]],
    }


def _model_memory_source(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_session_id": item.get("source_session_id"),
        "source_turn_id": item.get("source_turn_id"),
        "source_message_id": item.get("source_message_id"),
        "recorded_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "last_used_at": item.get("last_used_at"),
    }


def _model_memory_cognitive_payload(
    item: dict[str, Any],
    *,
    facts: list[Any],
) -> dict[str, Any]:
    domains = _model_memory_domains(item)
    return {
        "subject": _model_memory_subject(item),
        "domains": domains,
        "validity": _model_memory_validity(item, facts=facts),
        "sensitivity": _model_memory_sensitivity(item),
    }


def _model_memory_retrieval_payload(item: dict[str, Any]) -> dict[str, Any]:
    signals = item.get("signals") if isinstance(item.get("signals"), dict) else {}
    graph = signals.get("graph") if isinstance(signals.get("graph"), dict) else None
    hybrid = signals.get("hybrid") if isinstance(signals.get("hybrid"), dict) else None
    routes: list[str] = []
    if float(signals.get("sparse_score") or 0.0) > 0:
        routes.append("sparse")
    if graph:
        routes.append("associative_graph")
    if isinstance(hybrid, dict) and hybrid.get("dense_signal"):
        routes.append("embedding")
    if isinstance(hybrid, dict) and hybrid.get("rerank_signal"):
        routes.append("rerank")
    if not routes and signals:
        routes.append("lexical_or_base")
    payload: dict[str, Any] = {
        "classification": item.get("classification"),
        "score": item.get("score"),
        "why_this_turn": _truncate(str(item.get("why_relevant") or ""), 260),
        "routes": routes,
        "strong_signal": signals.get("strong_signal"),
    }
    if graph:
        payload["graph"] = {
            "score": graph.get("score"),
            "domains": graph.get("domains", []),
        }
    if isinstance(hybrid, dict):
        payload["hybrid"] = {
            "dense_score": hybrid.get("dense_score"),
            "rerank_score": hybrid.get("rerank_score"),
            "dense_signal": hybrid.get("dense_signal"),
            "rerank_signal": hybrid.get("rerank_signal"),
        }
    return payload


def _model_memory_domains(item: dict[str, Any]) -> list[str]:
    domains: list[str] = []
    signals = item.get("signals") if isinstance(item.get("signals"), dict) else {}
    graph = signals.get("graph") if isinstance(signals.get("graph"), dict) else {}
    for domain in graph.get("domains", []):
        if isinstance(domain, str) and domain not in domains:
            domains.append(domain)
    item_type = item.get("type")
    scope = item.get("scope")
    if isinstance(scope, str) and scope:
        domains.append(f"scope:{scope}")
    if isinstance(item_type, str) and item_type:
        domains.append(f"type:{item_type}")
    for tag in item.get("tags", [])[:5]:
        if isinstance(tag, str) and tag:
            domains.append(f"tag:{tag}")
    return domains[:10]


def _model_memory_subject(item: dict[str, Any]) -> str:
    scope = item.get("scope")
    item_type = item.get("type")
    if scope == "user":
        return "active_user"
    if item_type in {"behavioral_pattern", "correction"}:
        return "scarlet_behavior"
    if scope == "project":
        return "project_or_system"
    return "unspecified"


def _model_memory_validity(
    item: dict[str, Any],
    *,
    facts: list[Any],
) -> dict[str, Any]:
    ranges = [
        {
            "valid_from": fact.get("valid_from"),
            "valid_to": fact.get("valid_to"),
            "status": fact.get("status"),
        }
        for fact in facts
        if isinstance(fact, dict)
        and (fact.get("valid_from") is not None or fact.get("valid_to") is not None)
    ]
    status = item.get("status")
    return {
        "status": status,
        "kind": "time_bound" if ranges else "active_until_updated_or_deprecated",
        "fact_validity_ranges": ranges[:5],
    }


def _model_memory_sensitivity(item: dict[str, Any]) -> str:
    if item.get("scope") == "user":
        return "user_profile_memory"
    if item.get("scope") == "project":
        return "project_operational_memory"
    return "normal_memory"


def _compact_fact_payload(fact: Any) -> dict[str, Any]:
    if not isinstance(fact, dict):
        return {"value": fact}
    return {
        "id": fact.get("id"),
        "entity": fact.get("entity"),
        "predicate": fact.get("predicate"),
        "value": fact.get("value"),
        "status": fact.get("status"),
        "confidence": fact.get("confidence"),
        "salience": fact.get("salience"),
        "valid_from": fact.get("valid_from"),
        "valid_to": fact.get("valid_to"),
    }


def _session_context_block(
    db: Session,
    *,
    chat_session: ChatSession,
) -> dict[str, Any]:
    previous_sessions = [
        session
        for session in repositories.list_chat_sessions(db, limit=8)
        if session.id != chat_session.id
    ][:2]
    previous_session_payloads = [
        _session_context_payload(
            db,
            session,
            relation=f"previous_session_{index}",
        )
        for index, session in enumerate(previous_sessions, start=1)
    ]
    previous_memory_source = previous_sessions[0] if previous_sessions else None
    previous_memories = (
        repositories.list_memories_for_session(
            db,
            session_id=previous_memory_source.id,
            include_inactive=False,
        )[:5]
        if previous_memory_source is not None
        else []
    )
    return {
        "id": "session.continuity",
        "type": "session_context",
        "scope": "session",
        "lifetime": "session",
        "source": "backend.session_index",
        "content": {
            "current_session": _session_brief(chat_session),
            "previous_sessions_policy": (
                "Most recent sessions before the current one, used as continuity "
                "hints. Summaries are navigation aids, not final proof."
            ),
            "previous_sessions": previous_session_payloads,
            "previous_session_memories": [
                _compact_memory_payload(memory) for memory in previous_memories
            ],
        },
    }


def _message_context_block(
    db: Session,
    *,
    current_user_message: Message,
    recent_dialogue: list[dict[str, Any]],
    recent_events: list[dict[str, Any]],
    memory_context: dict[str, Any],
    temporal_context: dict[str, Any],
    capabilities: dict[str, str],
    runtime_preferences: RuntimePreferences,
) -> dict[str, Any]:
    user_memories = repositories.list_memories(
        db,
        scope="user",
        include_low_confidence=False,
    )[:5]
    return {
        "id": "turn.perception",
        "type": "message_context",
        "scope": "turn",
        "lifetime": "turn",
        "source": "backend.turn_frame",
        "content": {
            "current_message": {
                "id": current_user_message.id,
                "session_id": current_user_message.session_id,
                "turn_id": current_user_message.turn_id,
                "role": current_user_message.role,
                "content": _truncate(current_user_message.content, 1500),
                "created_at": _isoformat(current_user_message.created_at),
                "language": {
                    "code": runtime_preferences.language,
                    "label": runtime_preferences.language_label,
                    "source": runtime_preferences.source,
                    "policy": (
                        "Platform language setting. This is not inferred from "
                        "the current message."
                    ),
                },
            },
            "world": {
                **temporal_context,
                "location": {
                    "status": "configured_runtime_locale",
                    "country_code": runtime_preferences.country_code,
                    "country": runtime_preferences.country_label,
                    "timezone": runtime_preferences.timezone,
                    "source": runtime_preferences.source,
                    "precision": "country_timezone",
                    "policy": (
                        "Configured runtime/user locale. Use it for timezone, "
                        "local calendar, and coarse locale assumptions. Do not "
                        "treat it as GPS, exact city, or verified physical presence."
                    ),
                },
            },
            "user_profile": {
                "source": runtime_preferences.source,
                "policy": (
                    "Operational active user profile for this turn. Use it for "
                    "recognition, personalization, user-scope memory boundaries, "
                    "and future privacy separation. Search or inspect source "
                    "sessions before making sensitive or exact claims."
                ),
                "identity": {
                    "profile_id": runtime_preferences.profile_id,
                    "display_name": runtime_preferences.user_display_name,
                    "recognition_policy": (
                        "Treat this as the active local user profile unless the "
                        "backend provides a different profile in a future turn."
                    ),
                },
                "privacy": {
                    "scope": runtime_preferences.privacy_scope,
                    "policy": (
                        "User-scope memories and profile facts belong to this "
                        "active profile. Do not merge them with other future "
                        "profiles unless backend explicitly links them."
                    ),
                },
                "locale": {
                    "language": {
                        "code": runtime_preferences.language,
                        "label": runtime_preferences.language_label,
                    },
                    "country_code": runtime_preferences.country_code,
                    "country": runtime_preferences.country_label,
                    "timezone": runtime_preferences.timezone,
                },
                "memories": [
                    _compact_memory_payload(memory) for memory in user_memories
                ],
            },
            "memory_retrieval": _model_memory_context(memory_context),
            "recent_dialogue": recent_dialogue,
            "recent_runtime_events": recent_events,
            "api_mind": {
                "interface": "mind_shell",
                "schema": shell_metadata(),
                "command_families": [
                    {
                        "namespace": item["namespace"],
                        "purpose": item["purpose"],
                    }
                    for item in build_mind_shell_catalog()["commands"]
                ],
                "capabilities": capabilities,
            },
        },
    }


def _scarlet_state_block(
    *,
    current_user_message: Message,
    timestamp: datetime,
    focus_context_active: bool = False,
    affective_context_active: bool = False,
) -> dict[str, Any]:
    focus_value = (
        "See focus_context.current_focus. This legacy field is no longer the lived focus source."
        if focus_context_active
        else _truncate(current_user_message.content, 180)
    )
    return {
        "id": "scarlet.dynamic_state",
        "type": "scarlet_state",
        "scope": "session",
        "lifetime": "dynamic",
        "source": "backend.seed",
        "content": {
            "state_policy": (
                "Backend-seeded operational state. It is not a claim of human "
                "emotion; it is a compact control surface for focus, tone, and "
                "open loops until dedicated state APIs exist. When a dedicated "
                "organ block exists, prefer that organ block over this legacy "
                "placeholder."
            ),
            "focus": focus_value,
            "interaction_mode": "collaborative_lab",
            "confidence_posture": "verify_before_claiming",
            "mood_expression": (
                "See affective_context.current_emotion. This legacy field is no longer the emotional-state source."
                if affective_context_active
                else "curious_focused"
            ),
            "active_goal": (
                "Answer the current user using visible conversation, runtime "
                "context, and API Mind evidence when needed."
            ),
            "open_loops": [
                "Preserve criteria when historical recall is ambiguous.",
                "Verify stale project memories against current runtime evidence.",
            ],
            "updated_at": _aware_datetime(timestamp)
            .astimezone(timezone.utc)
            .isoformat(),
        },
    }


def _focus_context_block(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str,
    runtime_preferences: RuntimePreferences,
    settings: Any | None,
) -> dict[str, Any] | None:
    modes = organ_runtime_modes(settings) if settings is not None else {}
    if modes.get("focus", "off") != "model":
        return None
    owner_profile_id = runtime_preferences.profile_id or "local-user"
    focus = repositories.get_active_focus(db, owner_profile_id=owner_profile_id)
    if focus is None:
        return None
    transitions = repositories.list_focus_transitions(
        db,
        owner_profile_id=owner_profile_id,
        focus_id=focus.id,
        limit=5,
    )
    block = build_organ_runtime_block(
        block_type="focus_context",
        content={
            "current_focus": {
                "id": focus.id,
                "object": focus.focus_object,
                "type": focus.focus_type,
                "status": focus.status,
                "intensity": focus.intensity,
                "duration_policy": focus.duration_policy,
                "reason": focus.reason,
                "source_session_id": focus.source_session_id,
                "source_turn_id": focus.source_turn_id,
                "source_message_id": focus.source_message_id,
                "created_at": focus.created_at.isoformat(),
                "updated_at": focus.updated_at.isoformat(),
            },
            "recent_transitions": [
                {
                    "id": transition.id,
                    "from_focus_id": transition.from_focus_id,
                    "to_focus_id": transition.to_focus_id,
                    "relation": transition.relation,
                    "reason": transition.reason,
                    "created_at": transition.created_at.isoformat(),
                }
                for transition in transitions
            ],
            "usage": {
                "treat_as": "foreground_attention_state",
                "not_a_memory": True,
                "does_not_limit_memory_retrieval": True,
                "update_through": "POST /mind/focus",
            },
        },
    )
    repositories.add_event(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        event_type=ORGAN_EVENT_TYPES["focus"]["surfaced"],
        payload={
            "block_id": block["id"],
            "focus_id": focus.id,
            "object": focus.focus_object,
            "type": focus.focus_type,
            "intensity": focus.intensity,
        },
        source="runtime_context",
        actor="backend",
        visibility="debug",
        status="completed",
    )
    return block


def _session_context_payload(
    db: Session,
    chat_session: ChatSession,
    *,
    relation: str,
) -> dict[str, Any]:
    messages = repositories.list_messages(db, session_id=chat_session.id)
    memories = repositories.list_memories_for_session(db, session_id=chat_session.id)
    summary = repositories.get_session_summary(db, session_id=chat_session.id)
    return {
        **_session_brief(chat_session),
        "relation": relation,
        "summary": _session_summary_for_context(
            chat_session,
            summary=summary,
            messages=messages,
            memories=memories,
        ),
        "memory_ids": [memory.id for memory in memories[:10]],
    }


def _session_summary_for_context(
    chat_session: ChatSession,
    *,
    summary: Any | None,
    messages: list[Message],
    memories: list[MemoryRecord],
) -> dict[str, Any]:
    if summary is not None:
        return {
            "id": summary.id,
            "summary": _truncate(summary.summary, 1200),
            "topics": summary.topics_json,
            "decisions": summary.decisions_json,
            "open_questions": summary.open_questions_json,
            "memory_ids": summary.memory_ids_json,
            "message_count": summary.message_count,
            "source_turn_count": summary.source_turn_count,
            "last_message_id": summary.last_message_id,
            "status": summary.status,
            "summary_version": summary.summary_version,
            "updated_at": _isoformat(summary.updated_at),
            "source": "session_summary",
        }
    return {
        "id": None,
        "summary": _fallback_session_summary(chat_session, messages),
        "topics": [],
        "decisions": [],
        "open_questions": [],
        "memory_ids": [memory.id for memory in memories[:10]],
        "message_count": len(messages),
        "source_turn_count": len(
            {message.turn_id for message in messages if message.turn_id is not None}
        ),
        "last_message_id": messages[-1].id if messages else None,
        "status": "fallback",
        "summary_version": "runtime-context-fallback-v1",
        "updated_at": None,
        "source": "deterministic_fallback",
    }


def _session_brief(chat_session: ChatSession) -> dict[str, Any]:
    return {
        "id": chat_session.id,
        "title": chat_session.title,
        "created_at": _isoformat(chat_session.created_at),
        "updated_at": _isoformat(chat_session.updated_at),
        "metadata": chat_session.metadata_json,
    }


def _fallback_session_summary(
    chat_session: ChatSession,
    messages: list[Message],
) -> str:
    visible_messages = [
        message for message in messages if message.role in {"user", "assistant"}
    ]
    first_user = next(
        (message.content for message in visible_messages if message.role == "user"),
        "",
    )
    parts = [
        chat_session.title or "Untitled session",
        f"{len(visible_messages)} visible user/assistant messages",
    ]
    if first_user:
        parts.append(f"first user message: {_truncate(first_user, 240)}")
    return ". ".join(parts) + "."


def _compact_memory_payload(memory: MemoryRecord) -> dict[str, Any]:
    return {
        "id": memory.id,
        "type": memory.memory_type,
        "scope": memory.scope,
        "status": memory.status,
        "content": _truncate(memory.content, 700),
        "source_session_id": memory.source_session_id,
        "source_turn_id": memory.source_turn_id,
        "tags": memory.tags_json,
        "created_at": _isoformat(memory.created_at),
        "updated_at": _isoformat(memory.updated_at),
        "last_used_at": _isoformat(memory.last_used_at),
    }


def _recent_dialogue(history: list[Message]) -> list[dict[str, Any]]:
    visible = [message for message in history if message.role in {"user", "assistant"}][
        -RECENT_DIALOGUE_LIMIT:
    ]
    return [
        {
            "id": message.id,
            "role": message.role,
            "content": _truncate(message.content, 1200),
        }
        for message in visible
    ]


def _recent_runtime_events(
    db: Session,
    *,
    session_id: str,
    exclude_turn_id: str,
    limit: int = 16,
) -> list[dict[str, Any]]:
    events = repositories.list_events_for_session(
        db,
        session_id=session_id,
        limit=limit,
        exclude_turn_id=exclude_turn_id,
    )
    return [compact_event_for_context(event) for event in reversed(events)]


def _previous_memory_context_from_events(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("type") == "memory.context.built":
            return {
                "selected_count": event.get("selected_count"),
                "candidate_count": event.get("candidate_count"),
                "negative_evidence": event.get("negative_evidence"),
            }
    return {}


def _capability_state() -> dict[str, str]:
    capabilities: dict[str, str] = {
        "interface": "mind_shell",
        "legacy_mind_endpoints": "internal_debug_maintenance_only",
        "memory.facts.backfill": "internal_maintenance_only",
    }
    for namespace, family in COMMAND_FAMILIES.items():
        if namespace == "help":
            capabilities["help"] = "implemented"
            continue
        for action, spec in family.actions.items():
            capabilities[f"{namespace}.{action}"] = spec.status
    return capabilities


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _temporal_context(
    timestamp: datetime,
    preferences: RuntimePreferences | None = None,
) -> dict[str, Any]:
    aware = _aware_datetime(timestamp)
    runtime_preferences = preferences or RuntimePreferences(
        timezone="Europe/Rome",
        language="it",
        language_label="Italiano",
        country_code="IT",
        country_label="Italia",
        profile_id="local-user",
        user_display_name="Utente locale",
        privacy_scope="local_single_user",
        source="context_default",
    )
    try:
        configured_zone = ZoneInfo(runtime_preferences.timezone)
    except ZoneInfoNotFoundError:
        configured_zone = ZoneInfo("Europe/Rome")
    local_timestamp = aware.astimezone(configured_zone)
    return {
        "now": local_timestamp.isoformat(),
        "timezone": runtime_preferences.timezone,
        "timezone_name": local_timestamp.tzname(),
        "utc_offset": local_timestamp.strftime("%z"),
        "turn_started_at": local_timestamp.isoformat(),
        "timestamp_source": "backend_turn_start",
        "preference_source": runtime_preferences.source,
        "time_policy": (
            "This configured backend runtime time is Scarlet's only valid "
            "operative clock for real-world time in this turn."
        ),
        "storage_timestamp_policy": (
            "Chat/session timestamps are backend UTC; offset-naive persisted "
            "values should be interpreted as UTC unless an endpoint states otherwise."
        ),
    }


def _temporal_context_from_turn_frame(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    raw_time = value.get("time")
    if not isinstance(raw_time, str):
        return None
    try:
        timestamp = datetime.fromisoformat(raw_time)
    except ValueError:
        return None
    return _temporal_context(timestamp)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value

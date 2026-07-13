import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlmodel import Session

from app.mind.affect import build_affective_context
from app.mind.agent_modes import resolve_agent_mode, route_context_blocks
from app.mind.facts import fact_payload, fact_search_text
from app.mind.graph_retrieval import (
    build_memory_graph_expansion,
    graph_signals_by_memory,
)
from app.mind.hybrid_retrieval import (
    HybridBaseScore,
    hybrid_rank_status_payload,
    rank_hybrid_memories,
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
from app.mind.context_projection import compile_model_context_v2
from app.mind.schema import build_mind_shell_catalog, shell_metadata
from app.mind.search import (
    entity_token_groups,
    query_tokens,
    retrieval_stage_manifest,
    search_documents,
    sparse_results_by_source,
    sync_memory_documents,
)
from app.mind.shadow_retrieval import run_memory_surface_shadow_search
from app.storage import repositories
from app.storage.models import ChatSession, MemoryFact, MemoryRecord, Message, utc_now


RECENT_DIALOGUE_LIMIT = 8
INTERNAL_CANDIDATE_LIMIT = 20
MODEL_SELECTED_LIMIT = 5
NEAR_MISS_MIN_SCORE = 1.5
MODEL_MEMORY_PACKET_VERSION = "memory-packet-v1"
MODEL_RUNTIME_CONTEXT_PROFILE = "compact-model-facing-v1"

@dataclass(frozen=True)
class MemoryCandidateScore:
    memory: MemoryRecord
    score: float
    why_relevant: str
    sparse_score: float
    current_overlap: list[str]
    context_overlap: list[str]
    generic_overlap: list[str]
    tag_overlap: list[str]
    strong_signal: bool
    graph_score: float = 0.0
    graph_signal: dict[str, Any] | None = None
    hybrid_score: float | None = None
    hybrid_signals: dict[str, Any] | None = None


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
    agent_mode = resolve_agent_mode(
        db,
        profile_id=preferences.profile_id,
        default=str(getattr(settings, "agent_mode_default", "idle")),
        system_mode="interactive",
        system_reason="A human-facing turn is active.",
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
    }
    lexical_queries = _lexical_queries(
        current_user_message=current_user_message.content,
        recent_dialogue=recent_dialogue,
    )
    candidates = repositories.list_memories(
        db,
        scope=None,
        include_low_confidence=False,
    )
    facts_by_memory = {
        memory.id: repositories.list_memory_facts(db, memory_id=memory.id)
        for memory in candidates
    }
    sync_memory_documents(db, candidates, facts_by_memory=facts_by_memory)
    sparse_query = " ".join(lexical_queries)
    sparse_matches = sparse_results_by_source(
        search_documents(
            db,
            query=sparse_query,
            kind="memory",
            limit=INTERNAL_CANDIDATE_LIMIT * 4,
        )
    )
    graph_expansion = build_memory_graph_expansion(
        db,
        query=sparse_query,
        memories=candidates,
        facts_by_memory=facts_by_memory,
        limit=INTERNAL_CANDIDATE_LIMIT,
    )
    graph_signals = graph_signals_by_memory(graph_expansion)
    retrieval_shadow = run_memory_surface_shadow_search(
        db,
        query=sparse_query,
        candidate_memory_ids=[memory.id for memory in candidates],
        settings=settings,
        limit=MODEL_SELECTED_LIMIT,
    )
    ranked_base = _rank_candidates(
        candidates,
        current_user_message=current_user_message.content,
        recent_dialogue=recent_dialogue,
        facts_by_memory=facts_by_memory,
        sparse_matches=sparse_matches,
        graph_signals=graph_signals,
    )
    hybrid_plan = rank_hybrid_memories(
        candidates,
        base_scores=_hybrid_base_scores_from_context(ranked_base),
        retrieval_shadow=retrieval_shadow,
        settings=settings,
        limit=INTERNAL_CANDIDATE_LIMIT,
    )
    if hybrid_plan.active:
        ranked = _context_candidates_from_hybrid(
            hybrid_plan.entries,
            base_ranked=ranked_base,
        )
    else:
        ranked = ranked_base[:INTERNAL_CANDIDATE_LIMIT]
    selected_ranked, near_miss_ranked, excluded_ranked = _classify_candidates(ranked)

    near_miss = [
        _candidate_payload(item, classification="near_miss")
        | {"facts": [fact_payload(fact) for fact in facts_by_memory.get(item.memory.id, [])]}
        for item in near_miss_ranked
    ]
    excluded = [
        _candidate_payload(item, classification="excluded")
        | {"facts": [fact_payload(fact) for fact in facts_by_memory.get(item.memory.id, [])]}
        for item in excluded_ranked
    ]

    selected: list[dict[str, Any]] = []
    for item in selected_ranked[:MODEL_SELECTED_LIMIT]:
        selected.append(
            _candidate_payload(
                item,
                memory=item.memory,
                classification="selected",
                facts=facts_by_memory.get(item.memory.id, []),
            )
        )

    conflicts = _detect_conflicts(selected)
    temporal_context = _temporal_context(timestamp, preferences)
    payload = {
        "operation": "memory.context",
        "searched": True,
        "turn_frame": turn_frame,
        "temporal_context": temporal_context,
        "query_plan": {
            "lexical_queries": lexical_queries,
            "semantic_queries": [],
            "sparse_query": _truncate(sparse_query, 1500),
            "retrieval_stages": ["fts5_sparse_v1", "lexical_guard_v1"],
            "retrieval_readiness": retrieval_stage_manifest(),
            "retrieval_graph": graph_expansion,
            "retrieval_shadow": retrieval_shadow,
            "retrieval_hybrid": hybrid_rank_status_payload(hybrid_plan),
        },
        "selected": selected,
        "near_miss": near_miss,
        "excluded": excluded,
        "conflicts": conflicts,
        "negative_evidence": "none" if selected else "no_relevant_memory_selected",
        "candidate_count": len(candidates),
        "ranked_candidate_count": len(ranked),
        "selected_count": len(selected),
        "budget": {
            "internal_candidates": INTERNAL_CANDIDATE_LIMIT,
            "model_selected": MODEL_SELECTED_LIMIT,
        },
    }
    trace = repositories.add_trace(
        db,
        session_id=chat_session.id,
        turn_id=turn_id,
        kind="memory.context",
        payload=payload,
    )
    for item in selected_ranked[:MODEL_SELECTED_LIMIT]:
        if not (item.hybrid_signals or {}).get("rerank_signal"):
            continue
        repositories.add_memory_activity(
            db,
            memory_id=item.memory.id,
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
    model_context_trace_id: str | None = None
    if model_context_profile in {"v2_shadow", "v2"}:
        model_context_payload = compile_model_context_v2(
            db,
            chat_session=chat_session,
            rich_memory_context=payload,
            legacy_runtime_payload=runtime_payload,
            now=timestamp,
            preferences=preferences,
            settings=settings,
            agent_mode=agent_mode,
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
        runtime_context = render_runtime_context(runtime_payload, capabilities=capabilities)
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
        "selected": [
            _model_memory_packet(item)
            for item in memory_context["selected"]
        ],
        "near_miss": [
            _candidate_summary(item)
            for item in memory_context["near_miss"]
        ],
        "excluded": [
            _candidate_summary(item)
            for item in memory_context["excluded"]
        ],
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
                _compact_memory_payload(memory)
                for memory in previous_memories
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
                    _compact_memory_payload(memory)
                    for memory in user_memories
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
            "updated_at": _aware_datetime(timestamp).astimezone(timezone.utc).isoformat(),
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
            {
                message.turn_id
                for message in messages
                if message.turn_id is not None
            }
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
        message
        for message in messages
        if message.role in {"user", "assistant"}
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
    visible = [
        message
        for message in history
        if message.role in {"user", "assistant"}
    ][-RECENT_DIALOGUE_LIMIT:]
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


def _lexical_queries(
    *,
    current_user_message: str,
    recent_dialogue: list[dict[str, Any]],
) -> list[str]:
    queries = [current_user_message]
    recent_context = " ".join(
        str(item["content"])
        for item in recent_dialogue[-4:]
        if item["content"] != current_user_message
    )
    if recent_context:
        queries.append(f"{current_user_message} {recent_context}")
    return [_truncate(query, 1500) for query in queries]


def _rank_candidates(
    memories: list[MemoryRecord],
    *,
    current_user_message: str,
    recent_dialogue: list[dict[str, Any]],
    facts_by_memory: dict[str, list[MemoryFact]],
    sparse_matches: dict[str, Any] | None = None,
    graph_signals: dict[str, Any] | None = None,
) -> list[MemoryCandidateScore]:
    current_text = _normalize_text(current_user_message)
    current_tokens = set(_tokens(current_user_message))
    entity_groups = entity_token_groups(current_user_message)
    entity_tokens = set().union(*entity_groups) if entity_groups else set()
    low_signal_tokens = _low_signal_query_tokens(
        memories,
        facts_by_memory=facts_by_memory,
        query_tokens=current_tokens,
    )
    signal_tokens = (current_tokens - low_signal_tokens) | entity_tokens
    context_text = " ".join(
        str(item["content"])
        for item in recent_dialogue
        if item["content"] != current_user_message
    )
    context_tokens = set(_tokens(context_text))
    scores: list[MemoryCandidateScore] = []
    sparse_matches = sparse_matches or {}
    graph_signals = graph_signals or {}

    for memory in memories:
        haystack = _memory_search_text(memory, facts=facts_by_memory.get(memory.id, []))
        haystack_tokens = set(_tokens(haystack))
        current_overlap = sorted(signal_tokens & haystack_tokens)
        context_overlap = sorted(
            (context_tokens & haystack_tokens) - set(current_overlap) - low_signal_tokens
        )
        generic_overlap = sorted((current_tokens & haystack_tokens) - set(current_overlap))
        entity_supported = _supports_entity_group(
            haystack_tokens,
            memory.tags_json,
            entity_groups=entity_groups,
        )
        tag_overlap = sorted(
            tag
            for tag in set(memory.tags_json)
            if _tag_matches(tag, current_text)
            and _tag_has_signal(
                tag,
                signal_tokens=signal_tokens,
                entity_groups=entity_groups,
            )
        )

        score = 0.0
        reasons: list[str] = []
        sparse_match = sparse_matches.get(memory.id)
        sparse_score = sparse_match.score if sparse_match is not None else 0.0
        graph_signal = graph_signals.get(memory.id)
        graph_score = float(getattr(graph_signal, "score", 0.0) or 0.0)
        if sparse_match is not None:
            score += sparse_score * 2.0
            reasons.append(sparse_match.why_relevant)
        if graph_signal is not None and graph_score > 0:
            score += graph_score
            reasons.append(getattr(graph_signal, "why_relevant", "graph expansion"))
        if entity_supported:
            score += 3.0
            reasons.append("query entity support")
        if current_overlap:
            score += len(current_overlap) * 2.0
            reasons.append(f"current token overlap: {', '.join(current_overlap)}")
        if tag_overlap:
            score += len(tag_overlap) * 2.5
            reasons.append(f"tag match: {', '.join(tag_overlap)}")
        if context_overlap:
            score += len(context_overlap) * 0.4
            reasons.append(f"recent dialogue overlap: {', '.join(context_overlap[:6])}")
        if generic_overlap:
            score += len(generic_overlap) * 0.2
            reasons.append(f"generic overlap: {', '.join(generic_overlap)}")

        if score <= 0:
            continue

        if entity_groups:
            strong_signal = entity_supported
        else:
            strong_signal = (
                len(current_overlap) >= 2
                or bool(tag_overlap)
                or graph_score >= 2.0
                or (len(signal_tokens) <= 2 and bool(current_overlap))
            )
        scores.append(
            MemoryCandidateScore(
                memory=memory,
                score=score,
                why_relevant="; ".join(reasons),
                sparse_score=sparse_score,
                current_overlap=current_overlap,
                context_overlap=context_overlap,
                generic_overlap=generic_overlap,
                tag_overlap=tag_overlap,
                strong_signal=strong_signal,
                graph_score=graph_score,
                graph_signal=(
                    {
                        "score": round(graph_score, 6),
                        "why_relevant": getattr(graph_signal, "why_relevant", ""),
                        "domains": getattr(graph_signal, "domains", []),
                        "paths": getattr(graph_signal, "paths", [])[:5],
                    }
                    if graph_signal is not None
                    else None
                ),
            )
        )

    return sorted(
        scores,
        key=lambda item: (item.score, item.memory.created_at),
        reverse=True,
    )


def _classify_candidates(
    ranked: list[MemoryCandidateScore],
) -> tuple[
    list[MemoryCandidateScore],
    list[MemoryCandidateScore],
    list[MemoryCandidateScore],
]:
    selected: list[MemoryCandidateScore] = []
    near_miss: list[MemoryCandidateScore] = []
    excluded: list[MemoryCandidateScore] = []
    has_user_associative_context = any(
        item.memory.scope == "user" and item.graph_score >= 2.0
        for item in ranked
    )

    for item in ranked:
        if (
            has_user_associative_context
            and item.graph_score <= 0
            and not _has_confirmed_hybrid_signal(item)
            and (item.memory.scope == "project" or item.score < 0.3)
        ):
            if item.score >= NEAR_MISS_MIN_SCORE:
                near_miss.append(item)
            else:
                excluded.append(item)
            continue
        if item.strong_signal:
            selected.append(item)
        elif item.score >= NEAR_MISS_MIN_SCORE:
            near_miss.append(item)
        else:
            excluded.append(item)
    return selected, near_miss, excluded


def _has_confirmed_hybrid_signal(item: MemoryCandidateScore) -> bool:
    signals = item.hybrid_signals or {}
    return bool(signals.get("dense_signal") or signals.get("rerank_signal"))


def _hybrid_base_scores_from_context(
    ranked: list[MemoryCandidateScore],
) -> dict[str, HybridBaseScore]:
    return {
        item.memory.id: HybridBaseScore(
            score=item.score,
            reason=item.why_relevant,
            sparse_score=item.sparse_score,
            strong_signal=item.strong_signal,
        )
        for item in ranked
    }


def _context_candidates_from_hybrid(
    entries: list[Any],
    *,
    base_ranked: list[MemoryCandidateScore],
) -> list[MemoryCandidateScore]:
    base_by_id = {item.memory.id: item for item in base_ranked}
    candidates: list[MemoryCandidateScore] = []
    for entry in entries:
        base = base_by_id.get(entry.memory_id)
        if base is not None:
            candidates.append(
                MemoryCandidateScore(
                    memory=entry.memory,
                    score=entry.score,
                    why_relevant=entry.why_relevant,
                    sparse_score=base.sparse_score,
                    current_overlap=base.current_overlap,
                    context_overlap=base.context_overlap,
                    generic_overlap=base.generic_overlap,
                    tag_overlap=base.tag_overlap,
                    graph_score=base.graph_score,
                    graph_signal=base.graph_signal,
                    strong_signal=entry.strong_signal,
                    hybrid_score=entry.score,
                    hybrid_signals=entry.signals,
                )
            )
            continue
        candidates.append(
            MemoryCandidateScore(
                memory=entry.memory,
                score=entry.score,
                why_relevant=entry.why_relevant,
                sparse_score=float(entry.signals.get("sparse_score", 0.0)),
                current_overlap=[],
                context_overlap=[],
                generic_overlap=[],
                tag_overlap=[],
                graph_score=0.0,
                graph_signal=None,
                strong_signal=entry.strong_signal,
                hybrid_score=entry.score,
                hybrid_signals=entry.signals,
            )
        )
    return candidates


def _candidate_payload(
    item: MemoryCandidateScore,
    *,
    classification: str,
    memory: MemoryRecord | None = None,
    facts: list[MemoryFact] | None = None,
) -> dict[str, Any]:
    record = memory or item.memory
    payload = {
        "id": record.id,
        "type": record.memory_type,
        "scope": record.scope,
        "status": record.status,
        "content": record.content,
        "reason_for_storage": record.reason_for_storage,
        "expected_future_use": record.expected_future_use,
        "source_session_id": record.source_session_id,
        "source_turn_id": record.source_turn_id,
        "source_message_id": record.source_message_id,
        "tags": record.tags_json,
        "metadata": record.metadata_json,
        "usage_count": record.usage_count,
        "created_at": _isoformat(record.created_at),
        "updated_at": _isoformat(record.updated_at),
        "last_used_at": _isoformat(record.last_used_at),
        "score": round(item.score, 4),
        "classification": classification,
        "why_relevant": item.why_relevant,
        "signals": {
            "sparse_score": round(item.sparse_score, 4),
            "graph_score": round(item.graph_score, 4),
            "current_overlap": item.current_overlap,
            "context_overlap": item.context_overlap,
            "generic_overlap": item.generic_overlap,
            "tag_overlap": item.tag_overlap,
            "strong_signal": item.strong_signal,
        },
    }
    if item.graph_signal is not None:
        payload["signals"]["graph"] = item.graph_signal
    if item.hybrid_signals is not None:
        payload["signals"]["hybrid"] = item.hybrid_signals
        payload["hybrid_score"] = round(item.hybrid_score or item.score, 4)
    if facts is not None:
        payload["facts"] = [fact_payload(fact) for fact in facts]
    return payload


def _candidate_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "type": item["type"],
        "scope": item["scope"],
        "score": item["score"],
        "classification": item["classification"],
        "why_relevant": item["why_relevant"],
    }


def _detect_conflicts(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    facts_by_key: dict[tuple[str, str], list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for memory in selected:
        facts = memory.get("facts") if isinstance(memory.get("facts"), list) else []
        for fact in facts:
            if not isinstance(fact, dict) or fact.get("status") != "active":
                continue
            entity = str(fact.get("entity") or "")
            predicate = str(fact.get("predicate") or "")
            if not entity or not predicate:
                continue
            facts_by_key.setdefault((entity, predicate), []).append((memory, fact))

    for (entity, predicate), items in facts_by_key.items():
        memory_ids = sorted({str(memory.get("id")) for memory, _ in items})
        values = {
            repr(sorted((fact.get("value") or {}).items()))
            for _, fact in items
            if isinstance(fact.get("value"), dict)
        }
        if len(memory_ids) < 2 or len(values) < 2:
            continue
        conflicts.append(
            {
                "classification": "atomic_fact_conflict",
                "basis": "atomic_fact",
                "confidence": 0.95,
                "entity": entity,
                "predicate": predicate,
                "memory_ids": memory_ids,
                "reason": (
                    "selected memories contain active facts with same entity "
                    "and predicate but different values"
                ),
            }
        )
    return conflicts


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


def _memory_search_text(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact] | None = None,
) -> str:
    return " ".join(
        item
        for item in [
            memory.content,
            memory.memory_type,
            memory.scope,
            " ".join(memory.tags_json),
            fact_search_text(facts or []),
        ]
        if item
    )


def _low_signal_query_tokens(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]],
    query_tokens: set[str],
) -> set[str]:
    if not memories or not query_tokens:
        return set()
    document_frequency = {token: 0 for token in query_tokens}
    for memory in memories:
        tokens = set(
            _tokens(
                _memory_search_text(
                    memory,
                    facts=facts_by_memory.get(memory.id, []),
                )
            )
        )
        for token in query_tokens:
            if token in tokens:
                document_frequency[token] += 1
    threshold = max(3, int(len(memories) * 0.35))
    return {
        token
        for token, count in document_frequency.items()
        if count >= threshold
    }


def _supports_entity_group(
    haystack_tokens: set[str],
    tags: list[str],
    *,
    entity_groups: list[set[str]],
) -> bool:
    if not entity_groups:
        return False
    tag_token_sets = [
        set(query_tokens(tag.replace("-", " ").replace("_", " ")))
        for tag in tags
    ]
    for group in entity_groups:
        if group <= haystack_tokens:
            return True
        if any(group <= tag_tokens for tag_tokens in tag_token_sets):
            return True
    return False


def _tag_has_signal(
    tag: str,
    *,
    signal_tokens: set[str],
    entity_groups: list[set[str]],
) -> bool:
    tag_tokens = set(query_tokens(tag.replace("-", " ").replace("_", " ")))
    if not tag_tokens:
        return False
    if tag_tokens & signal_tokens:
        return True
    return any(group <= tag_tokens for group in entity_groups)


def _subject_tokens(value: str) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if len(token) > 2
    }


def _tag_matches(tag: str, current_text: str) -> bool:
    normalized_tag = _normalize_text(tag)
    if normalized_tag in current_text:
        return True
    return normalized_tag.replace("-", " ") in current_text


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


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

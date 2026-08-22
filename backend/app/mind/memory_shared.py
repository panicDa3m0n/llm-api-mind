"""Shared semantic-memory contracts used by read and mutation handlers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.facts import fact_payload, fact_search_text
from app.mind.search import entity_token_groups, query_tokens
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord

MemoryType = str


MemoryScope = str


MEMORY_TYPE_VALUES = {
    "project_fact",
    "user_preference",
    "decision",
    "correction",
    "task_context",
    "behavioral_pattern",
    "episodic",
}


MEMORY_SCOPE_VALUES = {"project", "user", "session"}


DEFAULT_MEMORY_SCOPE = "general"


TYPE_ALIASES = {
    "pref": "user_preference",
    "preference": "user_preference",
    "preferenza": "user_preference",
    "operational-preference": "user_preference",
    "operational_preference": "user_preference",
    "standard-preference": "user_preference",
    "standard_preference": "user_preference",
    "user_pref": "user_preference",
    "nota-operativa": "task_context",
    "nota_operativa": "task_context",
    "operational-note": "task_context",
    "operational_note": "task_context",
    "fact": "project_fact",
    "project": "project_fact",
    "decisione": "decision",
    "correzione": "correction",
    "context": "task_context",
}


def _context_required(operation: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code="memory.context_required",
        error_message=(
            f"Memory {operation} requires a session context so the operation "
            "can be traced."
        ),
        suggested_next_actions=[
            "Call memory routes during a chat turn",
            "Provide session_id when using POST /mind/call",
        ],
        confidence=1.0,
    )


def _memory_not_found(memory_id: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code="memory.not_found",
        error_message=f"Memory {memory_id} was not found.",
        suggested_next_actions=[
            "Call GET /mind/memory/conflicts",
            "Search memory before lifecycle operations",
        ],
        confidence=1.0,
    )


def _memory_payload(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact] | None = None,
) -> dict[str, Any]:
    payload = {
        "id": memory.id,
        "type": memory.memory_type,
        "scope": memory.scope,
        "status": memory.status,
        "content": memory.content,
        "reason_for_storage": memory.reason_for_storage,
        "expected_future_use": memory.expected_future_use,
        "created_by": memory.created_by,
        "source_session_id": memory.source_session_id,
        "source_turn_id": memory.source_turn_id,
        "source_message_id": memory.source_message_id,
        "tags": memory.tags_json,
        "metadata": memory.metadata_json,
        "usage_count": memory.usage_count,
        "created_at": _isoformat(memory.created_at),
        "updated_at": _isoformat(memory.updated_at),
        "last_used_at": _isoformat(memory.last_used_at),
    }
    if facts is not None:
        payload["facts"] = [fact_payload(fact) for fact in facts]
    return payload


def _normalize_freeform_label(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿ_ -]+", " ", value.strip().casefold())
    cleaned = re.sub(r"[\s-]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:80] or DEFAULT_MEMORY_SCOPE


def _normalize_memory_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _record_memory_activity(
    db: Session,
    *,
    context: MindAPIContext,
    memory_id: str,
    activity_kind: str,
    source: str,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    repositories.add_memory_activity(
        db,
        memory_id=memory_id,
        activity_kind=activity_kind,
        source=source,
        profile_id=getattr(context.settings, "user_profile_id", None),
        session_id=context.session_id,
        turn_id=context.turn_id,
        message_id=context.source_message_id,
        trace_id=trace_id,
        metadata=metadata,
    )


def score_memory_candidates(
    memories: list[MemoryRecord],
    query: str,
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
    sparse_matches: dict[str, Any] | None = None,
    graph_signals: dict[str, Any] | None = None,
) -> list[tuple[MemoryRecord, float, str]]:
    """Build the shared non-final candidate order for manual memory consumers."""

    query_text = query.lower()
    tokens = set(query_tokens(query))
    entity_groups = entity_token_groups(query)
    scored: list[tuple[MemoryRecord, float, str]] = []
    facts_by_memory = facts_by_memory or {}
    sparse_matches = sparse_matches or {}
    graph_signals = graph_signals or {}

    for memory in memories:
        haystack = " ".join(
            item
            for item in [
                memory.content,
                memory.memory_type,
                " ".join(memory.tags_json),
                fact_search_text(facts_by_memory.get(memory.id, [])),
            ]
            if item
        ).lower()
        haystack_tokens = set(_tokenize_memory_text(haystack))
        overlap = tokens & haystack_tokens
        tag_overlap = tokens & set(memory.tags_json)
        entity_supported = _supports_query_entity(
            haystack_tokens,
            memory.tags_json,
            entity_groups=entity_groups,
        )
        score = 0.0
        reasons: list[str] = []
        sparse_match = sparse_matches.get(memory.id)
        graph_signal = graph_signals.get(memory.id)
        graph_score = float(getattr(graph_signal, "score", 0.0) or 0.0)
        if sparse_match is not None:
            score += sparse_match.score * 2.5
            reasons.append(sparse_match.why_relevant)
        if graph_signal is not None and graph_score > 0:
            score += graph_score
            reasons.append(getattr(graph_signal, "why_relevant", "graph expansion"))
        if entity_supported:
            score += 3.0
            reasons.append("query entity support")
        if query_text in haystack:
            score += 3.0
            reasons.append("query substring match")
        if overlap:
            if entity_groups and not entity_supported:
                continue
            if (
                sparse_match is None
                and len(tokens) >= 2
                and len(overlap) < min(2, len(tokens))
                and not tag_overlap
            ):
                continue
            token_score = len(overlap) / max(len(tokens), 1)
            score += token_score
            reasons.append(f"token overlap: {', '.join(sorted(overlap))}")
        if tag_overlap:
            score += 0.5
            reasons.append(f"tag overlap: {', '.join(sorted(tag_overlap))}")
        if score <= 0:
            continue

        scored.append((memory, score, "; ".join(reasons)))

    return sorted(
        scored,
        key=lambda item: (item[1], item[0].created_at),
        reverse=True,
    )


def memory_facts_by_id(
    db: Session,
    memories: list[MemoryRecord],
    *,
    include_inactive: bool = False,
) -> dict[str, list[MemoryFact]]:
    """Load audit facts once per supplied memory without semantic inference."""

    return {
        memory.id: repositories.list_memory_facts(
            db,
            memory_id=memory.id,
            include_inactive=include_inactive,
        )
        for memory in memories
    }


def load_memory_facts(
    db: Session,
    memory: MemoryRecord,
    *,
    source_trace_id: str | None = None,
) -> tuple[list[MemoryFact], list[MemoryFact]]:
    """Return audit facts and preserve the no-derived-facts mutation contract."""

    _ = source_trace_id
    return (
        repositories.list_memory_facts(
            db,
            memory_id=memory.id,
            include_inactive=True,
        ),
        [],
    )


def _supports_query_entity(
    haystack_tokens: set[str],
    tags: list[str],
    *,
    entity_groups: list[set[str]],
) -> bool:
    if not entity_groups:
        return False
    tag_token_sets = [
        set(query_tokens(tag.replace("-", " ").replace("_", " "))) for tag in tags
    ]
    for group in entity_groups:
        if group <= haystack_tokens:
            return True
        if any(group <= tag_tokens for tag_tokens in tag_token_sets):
            return True
    return False


def _tokenize_memory_text(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()

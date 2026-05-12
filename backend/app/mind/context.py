import json
import re
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Any

from sqlmodel import Session

from app.mind.schema import MIND_API_ROUTES
from app.storage import repositories
from app.storage.models import ChatSession, MemoryRecord, Message, utc_now


RECENT_DIALOGUE_LIMIT = 8
INTERNAL_CANDIDATE_LIMIT = 20
MODEL_SELECTED_LIMIT = 5
NEAR_MISS_MIN_SCORE = 1.5

GENERIC_TOKENS = {
    "a",
    "about",
    "ancora",
    "and",
    "che",
    "context",
    "contesto",
    "cosa",
    "del",
    "della",
    "di",
    "dimmi",
    "do",
    "e",
    "for",
    "il",
    "in",
    "invece",
    "know",
    "la",
    "memoria",
    "memory",
    "of",
    "per",
    "preference",
    "preferenza",
    "project",
    "progetto",
    "protocol",
    "protocollo",
    "ricorda",
    "ricordi",
    "sai",
    "the",
    "what",
}


@dataclass(frozen=True)
class MemoryCandidateScore:
    memory: MemoryRecord
    score: float
    why_relevant: str
    current_overlap: list[str]
    context_overlap: list[str]
    generic_overlap: list[str]
    tag_overlap: list[str]
    strong_signal: bool


@dataclass(frozen=True)
class MemoryContextBuild:
    trace_id: str
    payload: dict[str, Any]
    runtime_context: str


def build_memory_context(
    db: Session,
    *,
    chat_session: ChatSession,
    turn_id: str,
    current_user_message: Message,
    history: list[Message],
    now: datetime | None = None,
) -> MemoryContextBuild:
    timestamp = now or utc_now()
    recent_dialogue = _recent_dialogue(history)
    capabilities = _capability_state()
    turn_frame = {
        "current_user_message": current_user_message.content,
        "current_user_message_id": current_user_message.id,
        "recent_dialogue": recent_dialogue,
        "previous_memory_context": {},
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
    ranked = _rank_candidates(
        candidates,
        current_user_message=current_user_message.content,
        recent_dialogue=recent_dialogue,
    )[:INTERNAL_CANDIDATE_LIMIT]
    selected_ranked, near_miss_ranked, excluded_ranked = _classify_candidates(ranked)

    near_miss = [
        _candidate_payload(item, classification="near_miss")
        for item in near_miss_ranked
    ]
    excluded = [
        _candidate_payload(item, classification="excluded")
        for item in excluded_ranked
    ]

    selected: list[dict[str, Any]] = []
    for item in selected_ranked[:MODEL_SELECTED_LIMIT]:
        updated = (
            repositories.mark_memory_used(db, memory_id=item.memory.id) or item.memory
        )
        selected.append(
            _candidate_payload(
                item,
                memory=updated,
                classification="selected",
            )
        )

    conflicts = _detect_conflicts(selected)
    payload = {
        "operation": "memory.context",
        "searched": True,
        "turn_frame": turn_frame,
        "query_plan": {
            "lexical_queries": lexical_queries,
            "semantic_queries": [],
            "retrieval_stages": ["lexical_v0"],
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
    payload["trace_id"] = trace.id
    runtime_context = render_runtime_context(payload, capabilities=capabilities)
    return MemoryContextBuild(
        trace_id=trace.id,
        payload=payload,
        runtime_context=runtime_context,
    )


def render_runtime_context(
    memory_context: dict[str, Any],
    *,
    capabilities: dict[str, str] | None = None,
) -> str:
    model_payload = {
        "memory_context": {
            "searched": memory_context["searched"],
            "trace_id": memory_context.get("trace_id"),
            "selected": memory_context["selected"],
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
        },
        "capabilities": capabilities or _capability_state(),
    }
    return (
        "<runtime_context>\n"
        + json.dumps(model_payload, ensure_ascii=True, indent=2)
        + "\n</runtime_context>"
    )


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
) -> list[MemoryCandidateScore]:
    current_text = _normalize_text(current_user_message)
    current_tokens = set(_tokens(current_user_message))
    context_text = " ".join(
        str(item["content"])
        for item in recent_dialogue
        if item["content"] != current_user_message
    )
    context_tokens = set(_tokens(context_text))
    scores: list[MemoryCandidateScore] = []

    for memory in memories:
        haystack = _memory_search_text(memory)
        haystack_tokens = set(_tokens(haystack))
        current_overlap = sorted((current_tokens & haystack_tokens) - GENERIC_TOKENS)
        context_overlap = sorted(
            (context_tokens & haystack_tokens) - set(current_overlap) - GENERIC_TOKENS
        )
        generic_overlap = sorted((current_tokens & haystack_tokens) & GENERIC_TOKENS)
        tag_overlap = sorted(
            tag
            for tag in set(memory.tags_json)
            if _tag_matches(tag, current_text)
        )

        score = 0.0
        reasons: list[str] = []
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

        score *= 1.0 + memory.confidence + memory.salience
        strong_signal = len(current_overlap) >= 2 or bool(tag_overlap)
        scores.append(
            MemoryCandidateScore(
                memory=memory,
                score=score,
                why_relevant="; ".join(reasons),
                current_overlap=current_overlap,
                context_overlap=context_overlap,
                generic_overlap=generic_overlap,
                tag_overlap=tag_overlap,
                strong_signal=strong_signal,
            )
        )

    return sorted(
        scores,
        key=lambda item: (item.score, item.memory.salience, item.memory.created_at),
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

    for item in ranked:
        if item.strong_signal:
            selected.append(item)
        elif item.score >= NEAR_MISS_MIN_SCORE:
            near_miss.append(item)
        else:
            excluded.append(item)
    return selected, near_miss, excluded


def _candidate_payload(
    item: MemoryCandidateScore,
    *,
    classification: str,
    memory: MemoryRecord | None = None,
) -> dict[str, Any]:
    record = memory or item.memory
    return {
        "id": record.id,
        "type": record.memory_type,
        "scope": record.scope,
        "status": record.status,
        "content": record.content,
        "reason_for_storage": record.reason_for_storage,
        "expected_future_use": record.expected_future_use,
        "confidence": record.confidence,
        "salience": record.salience,
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
            "current_overlap": item.current_overlap,
            "context_overlap": item.context_overlap,
            "generic_overlap": item.generic_overlap,
            "tag_overlap": item.tag_overlap,
            "strong_signal": item.strong_signal,
        },
    }


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
    for left, right in combinations(selected, 2):
        if _normalize_text(left["content"]) == _normalize_text(right["content"]):
            continue
        shared_tags = sorted(set(left["tags"]) & set(right["tags"]))
        shared_tokens = sorted(
            (_subject_tokens(left["content"]) & _subject_tokens(right["content"]))
            - GENERIC_TOKENS
        )
        if not shared_tags and len(shared_tokens) < 2:
            continue
        conflicts.append(
            {
                "memory_ids": [left["id"], right["id"]],
                "shared_tags": shared_tags,
                "shared_tokens": shared_tokens[:8],
                "reason": "selected memories appear to describe the same subject",
            }
        )
    return conflicts


def _capability_state() -> dict[str, str]:
    capabilities: dict[str, str] = {}
    for route in MIND_API_ROUTES:
        capabilities[_capability_key(route["path"])] = route["status"]
    capabilities.setdefault("memory.update", "unavailable")
    capabilities.setdefault("memory.deprecate", "unavailable")
    capabilities.setdefault("memory.delete", "unavailable")
    return capabilities


def _capability_key(path: str) -> str:
    parts = [part for part in path.strip("/").split("/") if part and part != "mind"]
    return ".".join(parts)


def _memory_search_text(memory: MemoryRecord) -> str:
    return " ".join(
        item
        for item in [
            memory.content,
            memory.reason_for_storage,
            memory.expected_future_use or "",
            memory.memory_type,
            memory.scope,
            " ".join(memory.tags_json),
        ]
        if item
    )


def _subject_tokens(value: str) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if token not in GENERIC_TOKENS and len(token) > 2
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

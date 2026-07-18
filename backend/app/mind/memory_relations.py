import re
from itertools import combinations
from typing import Any

from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.memory_read import _facts_by_memory
from app.mind.memory_shared import (
    _context_required,
    _memory_payload,
    _normalize_memory_text,
)
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord


def handle_memory_conflicts(
    context: MindAPIContext | None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("conflicts")

    with Session(context.engine) as db:
        memories = repositories.list_memories(
            db, scope=None, include_low_confidence=False
        )
        facts_by_memory = _facts_by_memory(db, memories)
        relations = _detect_active_memory_relations(
            memories,
            facts_by_memory=facts_by_memory,
        )
        conflicts = relations["conflicts"]
        related_overlaps = relations["related_overlaps"]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="memory.conflicts",
            payload={
                "operation": "memory.conflicts",
                "count": len(conflicts),
                "conflict_counts": _conflict_counts(conflicts),
                "related_overlap_count": len(related_overlaps),
                "active_memory_count": len(memories),
                "active_fact_count": sum(
                    len(facts) for facts in facts_by_memory.values()
                ),
                "conflicts": conflicts,
                "related_overlaps": related_overlaps,
            },
        )
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.conflicts",
            "count": len(conflicts),
            "conflict_counts": _conflict_counts(conflicts),
            "conflicts": conflicts,
            "related_overlap_count": len(related_overlaps),
            "related_overlaps": related_overlaps[:20],
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Unresolved atomic memory conflicts should be named before using "
            "any conflicting memory as active evidence. Related overlaps are "
            "maintenance signals, not contradictions."
        )
        if conflicts
        else "No active atomic memory conflicts were detected.",
        suggested_next_actions=[
            "Supersede or deprecate obsolete memories",
            "Continue with active memory context",
        ]
        if conflicts
        else ["Continue with active memories"],
        confidence=0.95,
    )


def _detect_active_memory_relations(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    facts_by_memory = facts_by_memory or {}
    conflicts = _detect_fact_conflicts(memories, facts_by_memory)

    conflict_memory_sets = {frozenset(conflict["memory_ids"]) for conflict in conflicts}
    payloads = [
        _memory_payload(memory, facts=facts_by_memory.get(memory.id, []))
        for memory in memories
    ]
    related_overlaps: list[dict[str, Any]] = []
    corpus_token_sets = {
        payload["id"]: _subject_tokens(payload["content"]) for payload in payloads
    }
    document_frequency = _token_document_frequency(corpus_token_sets.values())
    for left, right in combinations(payloads, 2):
        if frozenset([left["id"], right["id"]]) in conflict_memory_sets:
            continue
        duplicate_candidate = _normalize_memory_text(
            left["content"]
        ) == _normalize_memory_text(right["content"])
        shared_tags = sorted(set(left["tags"]) & set(right["tags"]))
        shared_tokens = sorted(
            corpus_token_sets[left["id"]] & corpus_token_sets[right["id"]]
        )
        overlap_score = _weighted_overlap_score(
            shared_tokens,
            document_frequency=document_frequency,
        )
        if not duplicate_candidate and not shared_tags and overlap_score < 1.5:
            continue
        related_overlaps.append(
            {
                "classification": "duplicate_candidate"
                if duplicate_candidate
                else "related_overlap",
                "basis": "exact_content"
                if duplicate_candidate
                else "tag_token_similarity",
                "confidence": 0.9
                if duplicate_candidate
                else min(0.75, overlap_score / 4),
                "memory_ids": [left["id"], right["id"]],
                "memory_claims": _memory_claims(left, right),
                "shared_tags": shared_tags,
                "shared_tokens": shared_tokens[:12],
                "overlap_score": round(overlap_score, 4),
                "reason": (
                    "active memories may describe the same stored subject"
                    if duplicate_candidate
                    else "active memories share maintenance-level semantic overlap"
                ),
            }
        )
    return {
        "conflicts": conflicts,
        "related_overlaps": related_overlaps,
    }


def _conflict_counts(conflicts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for conflict in conflicts:
        key = str(conflict.get("classification") or conflict.get("basis") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _detect_fact_conflicts(
    memories: list[MemoryRecord],
    facts_by_memory: dict[str, list[MemoryFact]],
) -> list[dict[str, Any]]:
    memories_by_id = {memory.id: memory for memory in memories}
    active_facts = [
        fact
        for facts in facts_by_memory.values()
        for fact in facts
        if fact.status == "active"
    ]
    conflicts: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[MemoryFact]] = {}
    for fact in active_facts:
        grouped.setdefault((fact.entity, fact.predicate), []).append(fact)

    for (entity, predicate), facts in grouped.items():
        memory_ids = sorted({fact.memory_id for fact in facts})
        values = {_normalize_fact_value(fact.value_json) for fact in facts}
        if len(memory_ids) < 2 or len(values) < 2:
            continue
        memory_payloads = [
            _memory_payload(
                memories_by_id[memory_id],
                facts=facts_by_memory.get(memory_id, []),
            )
            for memory_id in memory_ids
            if memory_id in memories_by_id
        ]
        conflicts.append(
            {
                "classification": "atomic_fact_conflict",
                "basis": "atomic_fact",
                "confidence": 0.95,
                "entity": entity,
                "predicate": predicate,
                "fact_ids": [fact.id for fact in facts],
                "memory_ids": memory_ids,
                "memory_claims": [
                    {
                        "id": memory.get("id"),
                        "content": memory.get("content"),
                        "source_session_id": memory.get("source_session_id"),
                        "source_turn_id": memory.get("source_turn_id"),
                    }
                    for memory in memory_payloads
                ],
                "values": [fact.value_json for fact in facts],
                "reason": (
                    "active facts share entity and predicate but have different values"
                ),
            }
        )
    return conflicts


def _memory_claims(*payloads: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": payload.get("id"),
            "content": payload.get("content"),
            "source_session_id": payload.get("source_session_id"),
            "source_turn_id": payload.get("source_turn_id"),
        }
        for payload in payloads
    ]


def _token_document_frequency(token_sets: Any) -> dict[str, int]:
    frequency: dict[str, int] = {}
    for tokens in token_sets:
        for token in tokens:
            frequency[token] = frequency.get(token, 0) + 1
    return frequency


def _weighted_overlap_score(
    shared_tokens: list[str],
    *,
    document_frequency: dict[str, int],
) -> float:
    score = 0.0
    for token in shared_tokens:
        frequency = max(document_frequency.get(token, 1), 1)
        score += 1 / frequency
    return score


def _normalize_fact_value(value: dict[str, Any]) -> str:
    return repr(sorted(value.items()))


def _subject_tokens(value: str) -> set[str]:
    return {
        token
        for token in _tokens(value)
        if token not in _generic_conflict_tokens() and len(token) > 2
    }


def _generic_conflict_tokens() -> set[str]:
    return {
        "a",
        "and",
        "che",
        "con",
        "di",
        "e",
        "il",
        "in",
        "la",
        "memoria",
        "memory",
        "protocol",
        "protocollo",
        "the",
    }


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())

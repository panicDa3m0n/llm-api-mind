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
        review_candidates = relations["review_candidates"]
        related_overlaps = relations["related_overlaps"]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="memory.conflicts",
            payload={
                "operation": "memory.conflicts",
                "count": 0,
                "conflict_counts": {},
                "review_candidate_count": len(review_candidates),
                "related_overlap_count": len(related_overlaps),
                "active_memory_count": len(memories),
                "active_fact_count": sum(
                    len(facts) for facts in facts_by_memory.values()
                ),
                "conflicts": [],
                "review_candidates": review_candidates,
                "related_overlaps": related_overlaps,
            },
        )
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.conflicts",
            "count": 0,
            "conflict_counts": {},
            "conflicts": [],
            "review_candidate_count": len(review_candidates),
            "review_candidates": review_candidates,
            "related_overlap_count": len(related_overlaps),
            "related_overlaps": related_overlaps[:20],
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "No conflict was asserted deterministically. Review candidates are "
            "non-authoritative leads; inspect their memories and provenance "
            "before deciding whether they conflict."
        ),
        suggested_next_actions=[
            "Open candidate memories and source sessions when relevant",
            "Use Scarlet's semantic judgment before lifecycle changes",
        ],
        confidence=1.0,
    )


def _detect_active_memory_relations(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    facts_by_memory = facts_by_memory or {}
    review_candidates = _detect_fact_relation_candidates(memories, facts_by_memory)
    payloads = {
        memory.id: _memory_payload(
            memory,
            facts=facts_by_memory.get(memory.id, []),
        )
        for memory in memories
    }
    duplicate_groups: dict[str, list[str]] = {}
    for memory in memories:
        duplicate_groups.setdefault(
            _normalize_memory_text(memory.content),
            [],
        ).append(memory.id)
    related_overlaps = [
        {
            "classification": "exact_duplicate_candidate",
            "basis": "exact_normalized_content",
            "authoritative": False,
            "memory_ids": memory_ids,
            "memory_claims": [
                {
                    "id": payloads[memory_id]["id"],
                    "content": payloads[memory_id]["content"],
                    "source_session_id": payloads[memory_id][
                        "source_session_id"
                    ],
                    "source_turn_id": payloads[memory_id]["source_turn_id"],
                }
                for memory_id in memory_ids
            ],
            "reason": (
                "active memories have identical normalized content; Scarlet "
                "must inspect provenance before applying lifecycle changes"
            ),
        }
        for memory_ids in duplicate_groups.values()
        if len(memory_ids) > 1
    ]
    return {
        "conflicts": [],
        "review_candidates": review_candidates,
        "related_overlaps": related_overlaps,
    }


def _conflict_counts(conflicts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for conflict in conflicts:
        key = str(conflict.get("classification") or conflict.get("basis") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _detect_fact_relation_candidates(
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
    candidates: list[dict[str, Any]] = []
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
        candidates.append(
            {
                "classification": "legacy_fact_divergence_candidate",
                "basis": "legacy_heuristic_fact",
                "authoritative": False,
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
                    "legacy heuristic propositions share an entity/predicate "
                    "label and have different values; semantic review is required"
                ),
            }
        )
    return candidates


def _normalize_fact_value(value: dict[str, Any]) -> str:
    return repr(sorted(value.items()))

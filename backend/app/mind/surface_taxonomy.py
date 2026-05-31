from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.mind.facts import fact_search_text
from app.storage.models import MemoryFact, MemoryGraphNode, MemoryRecord


SURFACE_TAXONOMY_VERSION = "memory-surface-taxonomy-v1"

AGENT_SUPPLIED_MEMORY_FIELDS = [
    "type",
    "content",
    "reason_for_storage",
    "expected_future_use",
    "confidence",
    "salience",
    "scope",
    "tags",
    "semantic_metadata",
]
BACKEND_OWNED_MEMORY_FIELDS = [
    "id",
    "status",
    "created_at",
    "updated_at",
    "source_session_id",
    "source_turn_id",
    "source_message_id",
    "source_trace_id",
    "content_hash",
    "surface_key",
    "embedding_status",
    "graph_keys",
]

TYPE_SURFACE_KIND = {
    "behavioral_pattern": ("behavioral_pattern_text", "behavioral"),
    "correction": ("correction_text", "correction"),
    "decision": ("decision_text", "decision"),
    "episodic": ("episodic_anchor_text", "episodic"),
    "project_fact": ("project_fact_text", "project_fact"),
    "task_context": ("task_context_text", "task"),
    "user_preference": ("preference_text", "preference"),
}


@dataclass(frozen=True)
class SurfaceDraft:
    target_type: str
    target_id: str
    surface_kind: str
    content: str
    scope: str | None
    status: str
    metadata: dict[str, Any]
    source_session_id: str | None = None
    source_turn_id: str | None = None
    source_message_id: str | None = None
    source_trace_id: str | None = None


def surface_taxonomy_manifest() -> dict[str, Any]:
    return {
        "taxonomy_version": SURFACE_TAXONOMY_VERSION,
        "compiler": "deterministic_backend_surface_compiler",
        "policy": {
            "canonical_truth": [
                "memories",
                "memory_facts",
                "session_summaries",
                "messages",
                "memory_proposals",
            ],
            "surfaces_are": "derived_rebuildable_indexes",
            "agent_does_not_write_surfaces_directly": True,
        },
        "agent_supplied_memory_fields": AGENT_SUPPLIED_MEMORY_FIELDS,
        "backend_owned_memory_fields": BACKEND_OWNED_MEMORY_FIELDS,
        "memory_surface_kinds": [
            {
                "kind": "memory_text",
                "dimensions": ["semantic", "canonical_summary"],
                "purpose": "General semantic recall of the whole memory.",
            },
            {
                "kind": "future_use_text",
                "dimensions": ["future_use", "retrieval_instruction"],
                "purpose": "When Scarlet should reuse this memory later.",
            },
            {
                "kind": "temporal_text",
                "dimensions": ["temporal", "provenance"],
                "purpose": "Recorded/source/validity anchors for temporal recall.",
            },
            {
                "kind": "fact_bundle_text",
                "dimensions": ["facts", "entity_predicate_value"],
                "purpose": "Canonical fact bundle linked to the memory.",
            },
            {
                "kind": "conflict_guard_text",
                "dimensions": ["conflict", "lifecycle"],
                "purpose": "Future conflict/update/deprecation cues.",
            },
            *[
                {
                    "kind": surface_kind,
                    "dimensions": ["semantic", dimension],
                    "purpose": f"Type-specific retrieval surface for {memory_type}.",
                }
                for memory_type, (surface_kind, dimension) in sorted(
                    TYPE_SURFACE_KIND.items()
                )
            ],
        ],
    }


def compile_memory_surface_drafts(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact],
) -> list[SurfaceDraft]:
    drafts = [
        _memory_surface(
            memory,
            surface_kind="memory_text",
            content=_memory_text(memory, facts=facts),
            dimensions=["semantic", "canonical_summary"],
            embedding_role="dense_sparse_primary",
        )
    ]
    type_spec = TYPE_SURFACE_KIND.get(memory.memory_type)
    if type_spec is not None:
        surface_kind, dimension = type_spec
        drafts.append(
            _memory_surface(
                memory,
                surface_kind=surface_kind,
                content=_type_specific_text(memory, dimension=dimension),
                dimensions=["semantic", dimension],
                embedding_role="dense_sparse_type_specific",
            )
        )
    if memory.expected_future_use or memory.reason_for_storage:
        drafts.append(
            _memory_surface(
                memory,
                surface_kind="future_use_text",
                content=_future_use_text(memory),
                dimensions=["future_use", "retrieval_instruction"],
                embedding_role="dense_sparse_intent",
            )
        )
    drafts.append(
        _memory_surface(
            memory,
            surface_kind="temporal_text",
            content=_temporal_text(memory, facts=facts),
            dimensions=["temporal", "provenance"],
            embedding_role="sparse_temporal_filter_support",
        )
    )
    if facts:
        drafts.append(
            _memory_surface(
                memory,
                surface_kind="fact_bundle_text",
                content=_fact_bundle_text(memory, facts=facts),
                dimensions=["facts", "entity_predicate_value"],
                embedding_role="dense_sparse_fact_bridge",
            )
        )
    if _needs_conflict_guard(memory):
        drafts.append(
            _memory_surface(
                memory,
                surface_kind="conflict_guard_text",
                content=_conflict_guard_text(memory),
                dimensions=["conflict", "lifecycle"],
                embedding_role="dense_sparse_conflict_detection",
            )
        )
    return drafts


def compile_fact_surface_drafts(
    fact: MemoryFact,
    *,
    memory: MemoryRecord,
) -> list[SurfaceDraft]:
    return [
        SurfaceDraft(
            target_type="fact",
            target_id=fact.id,
            surface_kind="fact_text",
            content=_fact_text(fact, memory=memory),
            scope=memory.scope,
            status=fact.status,
            source_session_id=fact.source_session_id,
            source_turn_id=fact.source_turn_id,
            source_trace_id=fact.source_trace_id,
            metadata=_surface_metadata(
                dimensions=["fact", "entity_predicate_value"],
                embedding_role="dense_sparse_fact",
                extra={
                    "memory_id": memory.id,
                    "entity": fact.entity,
                    "predicate": fact.predicate,
                    "confidence": fact.confidence,
                    "salience": fact.salience,
                    "surface_origin": "memory_fact",
                },
            ),
        )
    ]


def compile_graph_node_surface_draft(node: MemoryGraphNode) -> SurfaceDraft:
    return SurfaceDraft(
        target_type="graph_node",
        target_id=node.id,
        surface_kind="graph_node_profile",
        content=_node_text(node),
        scope=node.scope,
        status=node.status,
        source_session_id=node.source_session_id,
        metadata=_surface_metadata(
            dimensions=["graph_node", node.node_type],
            embedding_role="graph_expansion_profile",
            extra={
                "node_key": node.node_key,
                "node_type": node.node_type,
                "surface_origin": "memory_graph_node",
            },
        ),
    )


def _memory_surface(
    memory: MemoryRecord,
    *,
    surface_kind: str,
    content: str,
    dimensions: list[str],
    embedding_role: str,
) -> SurfaceDraft:
    return SurfaceDraft(
        target_type="memory",
        target_id=memory.id,
        surface_kind=surface_kind,
        content=content,
        scope=memory.scope,
        status=memory.status,
        source_session_id=memory.source_session_id,
        source_turn_id=memory.source_turn_id,
        source_message_id=memory.source_message_id,
        metadata=_surface_metadata(
            dimensions=dimensions,
            embedding_role=embedding_role,
            extra={
                "memory_type": memory.memory_type,
                "confidence": memory.confidence,
                "salience": memory.salience,
                "surface_origin": "memory_record",
            },
        ),
    )


def _surface_metadata(
    *,
    dimensions: list[str],
    embedding_role: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        **(extra or {}),
        "taxonomy_version": SURFACE_TAXONOMY_VERSION,
        "compiler": "deterministic_backend_surface_compiler",
        "cognitive_dimensions": dimensions,
        "embedding_role": embedding_role,
        "agent_supplied_fields": AGENT_SUPPLIED_MEMORY_FIELDS,
        "backend_owned_fields": BACKEND_OWNED_MEMORY_FIELDS,
    }


def _memory_text(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
    return "\n".join(
        item
        for item in [
            f"Memory {memory.id}",
            f"Type: {memory.memory_type}",
            f"Scope: {memory.scope}",
            f"Status: {memory.status}",
            f"Content: {memory.content}",
            f"Reason: {memory.reason_for_storage}",
            f"Future use: {memory.expected_future_use or ''}",
            f"Tags: {', '.join(memory.tags_json)}" if memory.tags_json else "",
            fact_search_text(facts),
        ]
        if item
    )


def _type_specific_text(memory: MemoryRecord, *, dimension: str) -> str:
    return "\n".join(
        item
        for item in [
            f"{dimension.replace('_', ' ').title()} memory",
            f"Content: {memory.content}",
            f"Why it matters: {memory.reason_for_storage}",
            f"Expected future use: {memory.expected_future_use or ''}",
            f"Tags: {', '.join(memory.tags_json)}" if memory.tags_json else "",
        ]
        if item
    )


def _future_use_text(memory: MemoryRecord) -> str:
    return "\n".join(
        item
        for item in [
            "Future use surface for Scarlet memory retrieval.",
            f"Use later when: {memory.expected_future_use or memory.reason_for_storage}",
            f"Original content: {memory.content}",
            f"Memory type: {memory.memory_type}",
            f"Scope: {memory.scope}",
        ]
        if item
    )


def _temporal_text(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
    valid_ranges = [
        f"{_isoformat(fact.valid_from) or 'unknown'} -> {_isoformat(fact.valid_to) or 'open'}"
        for fact in facts
        if fact.valid_from is not None or fact.valid_to is not None
    ]
    return "\n".join(
        item
        for item in [
            "Temporal and provenance surface.",
            f"Recorded at: {_isoformat(memory.created_at)}",
            f"Updated at: {_isoformat(memory.updated_at)}",
            f"Source session: {memory.source_session_id or ''}",
            f"Source turn: {memory.source_turn_id or ''}",
            f"Source message: {memory.source_message_id or ''}",
            f"Status: {memory.status}",
            f"Fact validity ranges: {'; '.join(valid_ranges)}" if valid_ranges else "",
            f"Content anchor: {memory.content}",
        ]
        if item
    )


def _fact_bundle_text(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
    fact_lines = [
        " ".join(
            [
                f"Entity: {fact.entity}",
                f"Predicate: {fact.predicate}",
                f"Value: {json.dumps(fact.value_json, ensure_ascii=False, sort_keys=True)}",
                f"Status: {fact.status}",
            ]
        )
        for fact in facts
    ]
    return "\n".join(
        [
            f"Canonical facts for memory {memory.id}",
            f"Memory content: {memory.content}",
            *fact_lines,
        ]
    )


def _conflict_guard_text(memory: MemoryRecord) -> str:
    return "\n".join(
        item
        for item in [
            "Conflict/update/deprecation guard surface.",
            f"Active claim or constraint: {memory.content}",
            f"Reason stored: {memory.reason_for_storage}",
            f"Future use: {memory.expected_future_use or ''}",
            "Use this surface to notice future statements that update, contradict, deprecate, or supersede this memory.",
        ]
        if item
    )


def _fact_text(fact: MemoryFact, *, memory: MemoryRecord) -> str:
    return "\n".join(
        [
            f"Fact {fact.id}",
            f"Memory: {memory.id}",
            f"Entity: {fact.entity}",
            f"Predicate: {fact.predicate}",
            f"Value: {json.dumps(fact.value_json, ensure_ascii=False)}",
            f"Status: {fact.status}",
            f"Scope: {memory.scope}",
            f"Memory content: {memory.content}",
        ]
    )


def _node_text(node: MemoryGraphNode) -> str:
    return "\n".join(
        item
        for item in [
            f"Node {node.node_key}",
            f"Type: {node.node_type}",
            f"Label: {node.label}",
            f"Scope: {node.scope or ''}",
            f"Status: {node.status}",
            f"Aliases: {', '.join(node.aliases_json)}" if node.aliases_json else "",
            f"Metadata: {json.dumps(node.metadata_json, ensure_ascii=False)}",
        ]
        if item
    )


def _needs_conflict_guard(memory: MemoryRecord) -> bool:
    if memory.status != "active":
        return True
    if memory.memory_type in {
        "correction",
        "decision",
        "project_fact",
        "task_context",
        "behavioral_pattern",
    }:
        return True
    lifecycle = memory.metadata_json.get("lifecycle")
    return isinstance(lifecycle, dict) and bool(lifecycle)


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None

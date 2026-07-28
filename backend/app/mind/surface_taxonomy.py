from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.storage.models import MemoryFact, MemoryGraphNode, MemoryRecord


SURFACE_TAXONOMY_VERSION = "memory-surface-taxonomy-v1"

AGENT_SUPPLIED_MEMORY_FIELDS = [
    "type",
    "content",
    "reason_for_storage",
    "expected_future_use",
    "scope",
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
    "tags_json",
    "metadata_json",
    "usage_count",
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

PRIMARY_CONTENT_SURFACE_KINDS = {
    "content_chunk_text",
    "memory_text",
    *(surface_kind for surface_kind, _ in TYPE_SURFACE_KIND.values()),
}
CANONICAL_FACT_SURFACE_KINDS = {"fact_bundle_text", "fact_text"}
ASSOCIATIVE_SURFACE_KINDS = {"graph_node_profile", "session_summary"}
SUPPORT_SURFACE_KINDS = {
    "future_use_text",
    "temporal_text",
    "conflict_guard_text",
}
PROMOTABLE_SURFACE_ROLES = {
    "primary_content",
    "associative_graph",
    "episodic_context",
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
    surface_key_suffix: str | None = None


def surface_taxonomy_manifest() -> dict[str, Any]:
    return {
        "taxonomy_version": SURFACE_TAXONOMY_VERSION,
        "compiler": "deterministic_backend_surface_compiler",
        "policy": {
            "canonical_truth": [
                "memories",
                "memory_facts (legacy audit only)",
                "session_summaries",
                "messages",
                "memory_proposals",
            ],
            "surfaces_are": "derived_rebuildable_indexes",
            "agent_does_not_write_surfaces_directly": True,
            "active_retrieval_policy": (
                "Content surfaces may promote a memory. Legacy-fact, "
                "future-use, temporal, and conflict/lifecycle surfaces are "
                "supporting evidence and must not select a memory by themselves."
            ),
        },
        "agent_supplied_memory_fields": AGENT_SUPPLIED_MEMORY_FIELDS,
        "backend_owned_memory_fields": BACKEND_OWNED_MEMORY_FIELDS,
        "retrieval_roles": [
            {
                "role": "primary_content",
                "surface_kinds": sorted(PRIMARY_CONTENT_SURFACE_KINDS),
                "active_rank_eligible": True,
                "purpose": "Direct recall from the actual memory claim/content.",
            },
            {
                "role": "legacy_fact_audit",
                "surface_kinds": sorted(CANONICAL_FACT_SURFACE_KINDS),
                "active_rank_eligible": False,
                "purpose": "Historical compatibility only; excluded from active recall.",
            },
            {
                "role": "associative_graph",
                "surface_kinds": sorted(ASSOCIATIVE_SURFACE_KINDS),
                "active_rank_eligible": True,
                "purpose": "Associative recall through graph/session nodes.",
            },
            {
                "role": "supporting_context",
                "surface_kinds": sorted(SUPPORT_SURFACE_KINDS),
                "active_rank_eligible": False,
                "purpose": (
                    "Corroborate, explain, or time/lifecycle-anchor a memory "
                    "already retrieved through a promotable route."
                ),
            },
        ],
        "memory_surface_kinds": [
            {
                "kind": "memory_text",
                "dimensions": ["semantic", "canonical_summary"],
                "purpose": "General semantic recall of the whole memory.",
            },
            {
                "kind": "content_chunk_text",
                "dimensions": ["semantic", "content_chunk"],
                "purpose": (
                    "Sentence/paragraph-level recall for longer memories. "
                    "Multiple chunk surfaces can point to the same memory; the "
                    "backend deduplicates by memory id before Scarlet sees the "
                    "memory packet."
                ),
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
                "purpose": "Deprecated legacy fact bundle; not generated in V1.64.",
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
            embedding_role="primary_content",
        )
    ]
    for index, chunk in enumerate(_content_chunks(memory.content), start=1):
        drafts.append(
            _memory_surface(
                memory,
                surface_kind="content_chunk_text",
                content=_content_chunk_text(memory, chunk=chunk, index=index),
                dimensions=["semantic", "content_chunk"],
                embedding_role="primary_content_chunk",
                surface_key_suffix=f"chunk:{index}",
            )
        )
    type_spec = TYPE_SURFACE_KIND.get(memory.memory_type)
    if type_spec is not None:
        surface_kind, dimension = type_spec
        drafts.append(
            _memory_surface(
                memory,
                surface_kind=surface_kind,
                content=_type_specific_text(memory, dimension=dimension),
                dimensions=["semantic", dimension],
                embedding_role="primary_type_content",
            )
        )
    if memory.expected_future_use or memory.reason_for_storage:
        drafts.append(
            _memory_surface(
                memory,
                surface_kind="future_use_text",
                content=_future_use_text(memory),
                dimensions=["future_use", "retrieval_instruction"],
                embedding_role="support_future_use",
            )
        )
    drafts.append(
        _memory_surface(
            memory,
            surface_kind="temporal_text",
            content=_temporal_text(memory, facts=facts),
            dimensions=["temporal", "provenance"],
            embedding_role="support_temporal",
        )
    )
    return drafts


def compile_fact_surface_drafts(
    fact: MemoryFact,
    *,
    memory: MemoryRecord,
) -> list[SurfaceDraft]:
    del fact, memory
    return []


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
                "active_rank_eligible": True,
            },
        ),
    )


def surface_retrieval_role(surface_kind: str) -> str:
    if surface_kind in PRIMARY_CONTENT_SURFACE_KINDS:
        return "primary_content"
    if surface_kind in CANONICAL_FACT_SURFACE_KINDS:
        return "legacy_fact_audit"
    if surface_kind == "session_summary":
        return "episodic_context"
    if surface_kind in ASSOCIATIVE_SURFACE_KINDS:
        return "associative_graph"
    if surface_kind in SUPPORT_SURFACE_KINDS:
        return "supporting_context"
    return "unknown"


def surface_can_promote_active(surface_kind: str) -> bool:
    return surface_retrieval_role(surface_kind) in PROMOTABLE_SURFACE_ROLES


def _memory_surface(
    memory: MemoryRecord,
    *,
    surface_kind: str,
    content: str,
    dimensions: list[str],
    embedding_role: str,
    surface_key_suffix: str | None = None,
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
        surface_key_suffix=surface_key_suffix,
        metadata=_surface_metadata(
            dimensions=dimensions,
            embedding_role=embedding_role,
            extra={
                "memory_type": memory.memory_type,
                "memory_scope": memory.scope,
                "surface_origin": "memory_record",
                "surface_key_suffix": surface_key_suffix,
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
        ]
        if item
    )


def _type_specific_text(memory: MemoryRecord, *, dimension: str) -> str:
    return "\n".join(
        item
        for item in [
            f"{dimension.replace('_', ' ').title()} memory",
            f"Content: {memory.content}",
        ]
        if item
    )


def _content_chunks(content: str) -> list[str]:
    normalized = " ".join(content.split())
    if len(normalized) < 220:
        return []
    raw_parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?;:])\s+|\n+", normalized)
        if part.strip()
    ]
    chunks: list[str] = []
    buffer = ""
    for part in raw_parts:
        candidate = f"{buffer} {part}".strip() if buffer else part
        if len(candidate) <= 420:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
        buffer = part
    if buffer:
        chunks.append(buffer)
    return chunks[:12]


def _content_chunk_text(memory: MemoryRecord, *, chunk: str, index: int) -> str:
    return "\n".join(
        [
            f"Memory {memory.id} content chunk {index}",
            f"Type: {memory.memory_type}",
            f"Scope: {memory.scope}",
            f"Content chunk: {chunk}",
        ]
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


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None

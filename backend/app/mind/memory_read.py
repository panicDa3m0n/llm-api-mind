"""Read-only semantic-memory commands and retrieval helpers."""

from __future__ import annotations

import re
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from sqlmodel import Session

from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.mind.facts import (
    canonicalize_entity,
    canonicalize_predicate,
    fact_payload,
    fact_search_text,
)
from app.mind.memory_recall import (
    collect_memory_recall_evidence,
    run_memory_recall_pipeline,
)
from app.mind.memory_shared import (
    TYPE_ALIASES,
    MemoryScope,
    MemoryType,
    _context_required,
    _memory_not_found,
    _memory_payload,
    _normalize_freeform_label,
    _record_memory_activity,
)
from app.mind.relevance_rerank import (
    FINAL_RERANK_POLICY,
    MemoryRerankEntry,
    rerank_status_payload,
)
from app.mind.search import (
    entity_token_groups,
    query_tokens,
    retrieval_stage_manifest,
    sync_memory_retrieval_artifacts,
)
from app.mind.time_filters import (
    TimeFilter,
    interval_contains,
    resolve_interval,
    time_filter_payload,
)
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.models import (
    MemoryFact,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemoryRecord,
)


class MemorySearchBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str = Field(min_length=1, max_length=1000)
    memory_types: list[MemoryType] = Field(default_factory=list, alias="types")
    scope: MemoryScope | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    include_low_confidence: bool = False
    time: TimeFilter | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "top_k" not in normalized and "limit" in normalized:
            normalized["top_k"] = normalized.pop("limit")
        else:
            normalized.pop("limit", None)
        memory_types = normalized.get("types")
        if isinstance(memory_types, str):
            normalized["types"] = [
                _normalize_freeform_label(
                    TYPE_ALIASES.get(memory_types.casefold(), memory_types)
                )
            ]
        elif isinstance(memory_types, list):
            normalized["types"] = [
                _normalize_freeform_label(TYPE_ALIASES.get(item.casefold(), item))
                if isinstance(item, str)
                else item
                for item in memory_types
            ]
        scope = normalized.get("scope")
        if isinstance(scope, str):
            if scope.strip().casefold() in {"", "all", "any", "*", "null", "none"}:
                normalized["scope"] = None
            else:
                normalized["scope"] = _normalize_freeform_label(scope)
        if "time" not in normalized:
            for alias in ("when", "period", "date_range"):
                if alias in normalized:
                    normalized["time"] = normalized.pop(alias)
                    break
        return normalized

    @model_validator(mode="after")
    def validate_time_basis(self) -> "MemorySearchBody":
        if self.time is not None:
            basis = self.time.basis or "source_conversation"
            if basis not in {"source_conversation", "recorded", "valid"}:
                raise ValueError(
                    "time.basis must be source_conversation, recorded, or valid"
                )
            self.time.basis = basis
        return self

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        return " ".join(value.split())


class MemoryFactsQueryBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_id: str | None = Field(default=None, max_length=80)
    entity: str | None = Field(default=None, max_length=120)
    predicate: str | None = Field(default=None, max_length=80)
    query: str | None = Field(default=None, max_length=1000)
    status: str = Field(default="active", max_length=40)
    include_inactive: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "memory_id" not in normalized:
            for alias in ("id", "target_id"):
                if alias in normalized:
                    normalized["memory_id"] = normalized.pop(alias)
                    break
        if "query" not in normalized:
            for alias in ("q", "text", "subject"):
                if alias in normalized:
                    normalized["query"] = normalized.pop(alias)
                    break
        return normalized

    @model_validator(mode="after")
    def canonicalize_filters(self) -> "MemoryFactsQueryBody":
        if self.entity is None and self.query is not None:
            self.entity = canonicalize_entity(self.query)
        elif self.entity is not None:
            self.entity = canonicalize_entity(self.entity)
        if self.predicate is not None:
            self.predicate = canonicalize_predicate(self.predicate)
        return self


class MemoryGraphExploreBody(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    memory_id: str = Field(min_length=1, max_length=80)
    depth: int = Field(default=1, ge=1, le=3)
    limit: int = Field(default=30, ge=1, le=100)
    include_inactive: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        if "memory_id" not in normalized:
            for alias in ("id", "target_id", "source_memory_id"):
                if alias in normalized:
                    normalized["memory_id"] = normalized.pop(alias)
                    break
        if "depth" not in normalized and "max_hops" in normalized:
            normalized["depth"] = normalized.pop("max_hops")
        if "limit" not in normalized and "top_k" in normalized:
            normalized["limit"] = normalized.pop("top_k")
        return normalized


def handle_memory_search(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("search")

    body_with_intent = dict(body)
    if "query" not in body_with_intent and intent:
        body_with_intent["query"] = intent

    try:
        request = MemorySearchBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_search",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with a valid memory search body",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        candidates = repositories.list_memories(
            db,
            scope=request.scope,
            include_low_confidence=request.include_low_confidence,
        )
        # Legacy heuristic facts are available through the dedicated audit
        # command, not as active evidence for search, ranking, or time filters.
        facts_by_memory: dict[str, list[MemoryFact]] = {}
        runtime_timezone = (
            load_runtime_preferences(db, context.settings).timezone
            if context.settings is not None
            else "Europe/Rome"
        )
        resolved_time = resolve_interval(
            request.time,
            timezone_name=runtime_timezone,
        )
        candidates = _filter_memories_by_time(
            db,
            candidates,
            facts_by_memory=facts_by_memory,
            time_filter=request.time,
            resolved_time=resolved_time,
            context=context,
        )
        facts_by_memory = {
            memory.id: facts_by_memory.get(memory.id, []) for memory in candidates
        }
        retrieval_query = _expanded_retrieval_query(
            request.query,
            memory_types=list(request.memory_types),
        )
        evidence = collect_memory_recall_evidence(
            db,
            query=retrieval_query,
            memories=candidates,
            facts_by_memory=facts_by_memory,
            settings=context.settings,
            sparse_limit=max(50, request.top_k * 8),
            graph_limit=max(request.top_k, 20),
        )
        scored = _score_memories(
            candidates,
            retrieval_query,
            facts_by_memory=facts_by_memory,
            sparse_matches=evidence.sparse_matches,
            graph_signals=evidence.graph_signals,
        )
        pipeline = run_memory_recall_pipeline(
            evidence,
            lexical_memory_ids=[memory.id for memory, _, _ in scored],
            settings=context.settings,
            selected_limit=request.top_k,
            off_mode_stage="lexical_fallback_v1",
        )
        rerank_plan = pipeline.rerank_plan
        retrieval_stages = pipeline.retrieval_stages
        if rerank_plan.active:
            scored = _memory_scores_from_final_rerank(rerank_plan.entries)
        hybrid_signals_by_id = {
            entry.memory_id: _final_rerank_signals(entry)
            for entry in rerank_plan.entries
        }
        graph_signal_payload_by_id = {
            memory_id: {
                "score": round(signal.score, 6),
                "why_relevant": signal.why_relevant,
                "domains": signal.domains,
                "paths": signal.paths[:5],
            }
            for memory_id, signal in evidence.graph_signals.items()
        }
        selected = scored[: request.top_k]

        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.search",
            payload={
                "operation": "memory.search",
                "query": request.query,
                "retrieval_query": retrieval_query,
                "types": list(request.memory_types),
                "scope": request.scope,
                "top_k": request.top_k,
                "time": time_filter_payload(request.time, resolved_time),
                "returned_memory_ids": [memory.id for memory, _, _ in selected],
                "candidate_count": len(candidates),
                "fact_candidate_count": sum(
                    len(facts) for facts in facts_by_memory.values()
                ),
                "retrieval_stages": retrieval_stages,
                "retrieval_readiness": retrieval_stage_manifest(),
                "retrieval_graph": evidence.graph_expansion,
                "retrieval_shadow": evidence.retrieval_shadow,
                "retrieval_rerank": rerank_status_payload(rerank_plan),
                "retrieval_hybrid": rerank_status_payload(rerank_plan),
            },
        )
        trace_id = trace.id
        for memory, _, _ in selected:
            _record_memory_activity(
                db,
                context=context,
                memory_id=memory.id,
                activity_kind="manual_search",
                source="memory.search",
                trace_id=trace_id,
                metadata={"query": request.query},
            )

        memories = [
            {
                **_memory_payload(memory),
                "facts": [
                    fact_payload(fact) for fact in facts_by_memory.get(memory.id, [])
                ],
                "score": round(score, 4),
                "why_relevant": reason,
                "retrieval_signals": {
                    "graph": graph_signal_payload_by_id.get(memory.id),
                    "hybrid": hybrid_signals_by_id.get(memory.id),
                },
            }
            for memory, score, reason in selected
        ]

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.search",
            "query": request.query,
            "retrieval_query": retrieval_query,
            "time": time_filter_payload(request.time, resolved_time),
            "retrieval_stages": retrieval_stages,
            "retrieval_readiness": retrieval_stage_manifest(),
            "retrieval_graph": evidence.graph_expansion,
            "retrieval_shadow": evidence.retrieval_shadow,
            "retrieval_rerank": rerank_status_payload(rerank_plan),
            "retrieval_hybrid": rerank_status_payload(rerank_plan),
            "memories": memories,
            "count": len(memories),
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Use returned memories as sourceable context, not as hidden truth. "
            "If no memories are returned, answer from current conversation only."
        ),
        suggested_next_actions=[
            "Use relevant memories with their provenance",
            "Do not invent memory content when search returns no result",
        ],
        confidence=0.95 if memories else 0.8,
    )


def handle_memory_facts(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("facts")

    try:
        request = MemoryFactsQueryBody.model_validate(body)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_facts_query",
            error_message=str(exc),
            suggested_next_actions=[
                "Call GET /mind/schema",
                "Retry with entity, predicate, memory_id, or query",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        facts = repositories.list_memory_facts(
            db,
            memory_id=request.memory_id,
            entity=request.entity,
            predicate=request.predicate,
            status=request.status,
            include_inactive=request.include_inactive,
        )
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.facts",
            payload={
                "operation": "memory.facts",
                "memory_id": request.memory_id,
                "entity": request.entity,
                "predicate": request.predicate,
                "status": request.status,
                "include_inactive": request.include_inactive,
                "count": len(facts),
            },
        )
        if request.memory_id is not None:
            _record_memory_activity(
                db,
                context=context,
                memory_id=request.memory_id,
                activity_kind="manual_facts",
                source="memory.facts",
                trace_id=trace.id,
            )
        fact_payloads = [fact_payload(fact) for fact in facts]
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.facts",
            "facts": fact_payloads,
            "count": len(fact_payloads),
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Use facts as canonical memory state. Natural-language memories "
            "remain source text, while facts provide entity/predicate/value."
        ),
        suggested_next_actions=[
            "Use fact entity and predicate for conflict reasoning",
            "Treat deprecated facts as history, not active evidence",
        ],
        confidence=0.95,
    )


def handle_memory_graph(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str | None = None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("graph")

    body_with_intent = dict(body)
    if "memory_id" not in body_with_intent and intent and "mem_" in intent:
        match = re.search(r"mem_[a-f0-9]+", intent)
        if match:
            body_with_intent["memory_id"] = match.group(0)

    try:
        request = MemoryGraphExploreBody.model_validate(body_with_intent)
    except ValidationError as exc:
        return MemoryOperationResult(
            ok=False,
            error_code="memory.invalid_graph_request",
            error_message=str(exc),
            suggested_next_actions=[
                "Retry with memory_id and optional depth/limit",
            ],
            confidence=1.0,
        )

    with Session(context.engine) as db:
        memory = repositories.get_memory(db, request.memory_id)
        if memory is None:
            return _memory_not_found(request.memory_id)
        facts = repositories.list_memory_facts(
            db,
            memory_id=memory.id,
            include_inactive=True,
        )
        sync_memory_retrieval_artifacts(
            db,
            [memory],
            facts_by_memory={memory.id: facts},
        )
        root = repositories.get_memory_graph_node_by_key(
            db,
            node_key=f"memory:{memory.id}",
        )
        if root is None:
            return MemoryOperationResult(
                ok=False,
                error_code="memory.graph_root_missing",
                error_message=f"No graph root was available for memory {memory.id}.",
                suggested_next_actions=[
                    "Call POST /mind/memory/facts/backfill for this memory",
                    "Retry graph navigation after retrieval artifacts sync",
                ],
                confidence=0.7,
            )
        nodes, edges = _graph_neighborhood(
            db,
            root=root,
            depth=request.depth,
            limit=request.limit,
            include_inactive=request.include_inactive,
        )
        related_memory_ids = sorted(
            {
                node.source_memory_id
                for node in nodes
                if node.source_memory_id
                and node.source_memory_id != memory.id
                and (request.include_inactive or node.status == "active")
            }
        )
        related_memories = [
            _memory_payload(related)
            for memory_id in related_memory_ids[: request.limit]
            if (related := repositories.get_memory(db, memory_id)) is not None
        ]
        root_memory_payload = _memory_payload(memory, facts=facts)
        node_payloads = [_graph_node_payload(node) for node in nodes]
        edge_payloads = [_graph_edge_payload(edge) for edge in edges]
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.graph",
            payload={
                "operation": "memory.graph",
                "memory_id": memory.id,
                "depth": request.depth,
                "limit": request.limit,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "related_memory_ids": related_memory_ids,
            },
        )
        _record_memory_activity(
            db,
            context=context,
            memory_id=memory.id,
            activity_kind="manual_graph",
            source="memory.graph",
            trace_id=trace.id,
        )
        trace_id = trace.id

    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "memory.graph",
            "memory_id": request.memory_id,
            "root_memory": root_memory_payload,
            "depth": request.depth,
            "nodes": node_payloads,
            "edges": edge_payloads,
            "related_memories": related_memories,
            "count": {
                "nodes": len(node_payloads),
                "edges": len(edge_payloads),
                "related_memories": len(related_memories),
            },
            "trace_ids": [trace_id],
        },
        cognitive_hint=(
            "Use graph neighbors to reconstruct associative context around a "
            "memory. If exact conversation wording matters, open the source "
            "session as well."
        ),
        suggested_next_actions=[
            "Use related memories only when their relation is relevant",
            "Open source sessions for exact provenance-sensitive claims",
        ],
        confidence=0.95,
    )


def handle_memory_read(
    memory_id: str,
    context: MindAPIContext | None,
) -> MemoryOperationResult:
    if context is None or context.session_id is None:
        return _context_required("read")

    with Session(context.engine) as db:
        memory = repositories.get_memory(db, memory_id)
        if memory is None:
            return _memory_not_found(memory_id)
        facts = repositories.list_memory_facts(
            db,
            memory_id=memory.id,
            include_inactive=True,
        )
        trace_ids: list[str] = []
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="mind.memory.read",
            payload={
                "operation": "memory.read",
                "memory_id": memory.id,
                "status": memory.status,
            },
        )
        _record_memory_activity(
            db,
            context=context,
            memory_id=memory.id,
            activity_kind="manual_read",
            source="memory.read",
            trace_id=trace.id,
        )
        trace_ids.append(trace.id)
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "memory.read",
                "memory": _memory_payload(memory, facts=facts),
                "trace_ids": trace_ids,
            },
            cognitive_hint=(
                "Use this memory with its status and provenance. Deprecated "
                "records are inspectable history, not active evidence."
            ),
            suggested_next_actions=["Use active memories for answers"],
            confidence=1.0,
        )


def _score_memories(
    memories: list[MemoryRecord],
    query: str,
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
    sparse_matches: dict[str, Any] | None = None,
    graph_signals: dict[str, Any] | None = None,
) -> list[tuple[MemoryRecord, float, str]]:
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
        haystack_tokens = set(_tokens(haystack))
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


def _memory_scores_from_final_rerank(
    entries: list[MemoryRerankEntry],
) -> list[tuple[MemoryRecord, float, str]]:
    return [
        (
            entry.memory,
            entry.score,
            "Final memory-level reranker accepted this candidate.",
        )
        for entry in entries
        if entry.accepted
    ]


def _final_rerank_signals(entry: MemoryRerankEntry) -> dict[str, Any]:
    return {
        "ranking_policy": FINAL_RERANK_POLICY,
        "mode": "active",
        "final_arbiter": True,
        "rerank_score": round(entry.score, 6),
        "rerank_rank": entry.rank,
        "rerank_signal": entry.accepted,
        "rerank_evaluated": entry.evaluated,
        "dense_signal": "dense" in entry.routes,
        "recall_routes": list(entry.routes),
        "route_ranks": entry.route_ranks,
    }


def _expanded_retrieval_query(query: str, *, memory_types: list[str]) -> str:
    # `types` are model-supplied retrieval hints, not evidence that a memory is
    # semantically relevant. Folding them into the query makes broad labels such
    # as "user_preference" match unrelated memories. Keep the natural-language
    # query as the active retrieval surface; type hints remain visible in traces
    # and can be used by dedicated typed/embedded retrieval stages later.
    _ = memory_types
    return query


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


def _filter_memories_by_time(
    db: Session,
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]],
    time_filter: TimeFilter | None,
    resolved_time: dict[str, Any] | None,
    context: MindAPIContext,
) -> list[MemoryRecord]:
    if time_filter is None:
        return memories
    if time_filter.preset == "this_session":
        return [
            memory
            for memory in memories
            if memory.source_session_id == context.session_id
        ]
    basis = time_filter.basis or "source_conversation"
    return [
        memory
        for memory in memories
        if _memory_matches_time(
            db,
            memory,
            facts=facts_by_memory.get(memory.id, []),
            basis=basis,
            resolved_time=resolved_time,
        )
    ]


def _memory_matches_time(
    db: Session,
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact],
    basis: str,
    resolved_time: dict[str, Any] | None,
) -> bool:
    if basis == "recorded":
        return interval_contains(memory.created_at, resolved=resolved_time)
    if basis == "valid":
        if not facts:
            return interval_contains(memory.created_at, resolved=resolved_time)
        return any(
            interval_contains(
                fact.valid_from or fact.recorded_at, resolved=resolved_time
            )
            or interval_contains(fact.valid_to, resolved=resolved_time)
            for fact in facts
        )
    if memory.source_session_id is None:
        return interval_contains(memory.created_at, resolved=resolved_time)
    messages = repositories.list_messages(db, session_id=memory.source_session_id)
    conversation_messages = [
        message for message in messages if message.role in {"user", "assistant"}
    ]
    if not conversation_messages:
        return interval_contains(memory.created_at, resolved=resolved_time)
    return any(
        interval_contains(message.created_at, resolved=resolved_time)
        for message in conversation_messages
    )


def _graph_neighborhood(
    db: Session,
    *,
    root: MemoryGraphNode,
    depth: int,
    limit: int,
    include_inactive: bool,
) -> tuple[list[MemoryGraphNode], list[MemoryGraphEdge]]:
    all_edges = repositories.list_memory_graph_edges(limit=2000, db=db)
    all_nodes = {
        node.id: node for node in repositories.list_memory_graph_nodes(db, limit=2000)
    }
    node_ids: set[str] = {root.id}
    frontier: set[str] = {root.id}
    selected_edges: dict[str, MemoryGraphEdge] = {}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in all_edges:
            if not include_inactive and edge.status != "active":
                continue
            if (
                edge.source_node_id not in frontier
                and edge.target_node_id not in frontier
            ):
                continue
            selected_edges.setdefault(edge.id, edge)
            other_id = (
                edge.target_node_id
                if edge.source_node_id in frontier
                else edge.source_node_id
            )
            if other_id not in node_ids:
                next_frontier.add(other_id)
        node_ids.update(next_frontier)
        frontier = next_frontier
        if not frontier or len(node_ids) >= limit:
            break
    nodes = [
        node
        for node_id in list(node_ids)[:limit]
        if (node := all_nodes.get(node_id)) is not None
        and (include_inactive or node.status == "active")
    ]
    allowed = {node.id for node in nodes}
    edges = [
        edge
        for edge in selected_edges.values()
        if edge.source_node_id in allowed and edge.target_node_id in allowed
    ][:limit]
    return nodes, edges


def _graph_node_payload(node: MemoryGraphNode) -> dict[str, Any]:
    return {
        "id": node.id,
        "node_key": node.node_key,
        "type": node.node_type,
        "label": node.label,
        "scope": node.scope,
        "status": node.status,
        "aliases": node.aliases_json,
        "source_memory_id": node.source_memory_id,
        "source_fact_id": node.source_fact_id,
        "source_session_id": node.source_session_id,
        "metadata": node.metadata_json,
    }


def _graph_edge_payload(edge: MemoryGraphEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "relation": edge.relation,
        "status": edge.status,
        "source_node_id": edge.source_node_id,
        "target_node_id": edge.target_node_id,
        "source_memory_id": edge.source_memory_id,
        "source_fact_id": edge.source_fact_id,
        "source_session_id": edge.source_session_id,
        "metadata": edge.metadata_json,
    }


def _facts_by_memory(
    db: Session,
    memories: list[MemoryRecord],
    *,
    include_inactive: bool = False,
) -> dict[str, list[MemoryFact]]:
    return {
        memory.id: repositories.list_memory_facts(
            db,
            memory_id=memory.id,
            include_inactive=include_inactive,
        )
        for memory in memories
    }


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())

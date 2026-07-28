"""Shared evidence collection and final-rerank pipeline for memory recall."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.mind.graph_retrieval import (
    build_memory_graph_expansion,
    graph_signals_by_memory,
)
from app.mind.relevance_rerank import (
    FINAL_RERANK_POLICY,
    MemoryRecallCandidate,
    MemoryRerankPlan,
    build_memory_recall_pool,
    run_memory_relevance_rerank,
)
from app.mind.search import (
    search_documents,
    sparse_results_by_source,
    sync_memory_documents,
)
from app.mind.shadow_retrieval import run_memory_surface_shadow_search
from app.storage.models import MemoryFact, MemoryRecord


@dataclass(frozen=True)
class MemoryRecallEvidence:
    """Route evidence collected before either caller applies its local ranking."""

    query: str
    memories: list[MemoryRecord]
    facts_by_memory: dict[str, list[MemoryFact]]
    sparse_matches: dict[str, Any]
    graph_expansion: dict[str, Any]
    graph_signals: dict[str, Any]
    retrieval_shadow: dict[str, Any]
    rerank_candidate_limit: int


@dataclass(frozen=True)
class MemoryRecallPipeline:
    """Shared recall pool and final rerank result, independent of presentation."""

    evidence: MemoryRecallEvidence
    recall_pool: list[MemoryRecallCandidate]
    rerank_plan: MemoryRerankPlan
    retrieval_stages: list[str]


def collect_memory_recall_evidence(
    db: Session,
    *,
    query: str,
    memories: list[MemoryRecord],
    facts_by_memory: dict[str, list[MemoryFact]],
    settings: Any | None,
    sparse_limit: int,
    graph_limit: int,
) -> MemoryRecallEvidence:
    """Collect shared retrieval routes without deciding semantic relevance.

    Callers deliberately retain their own query construction, candidate filters,
    deterministic fallback ranking, output packet, and activity semantics. The
    final reranker receives the same evidence pool for automatic and manual
    recall.
    """

    sync_memory_documents(db, memories, facts_by_memory=facts_by_memory)
    sparse_matches = sparse_results_by_source(
        search_documents(
            db,
            query=query,
            kind="memory",
            limit=sparse_limit,
        )
    )
    graph_expansion = build_memory_graph_expansion(
        db,
        query=query,
        memories=memories,
        facts_by_memory=facts_by_memory,
        limit=graph_limit,
    )
    graph_signals = graph_signals_by_memory(graph_expansion)
    rerank_candidate_limit = int(
        getattr(settings, "retrieval_shadow_rerank_candidate_limit", 20) or 20
    )
    final_rerank_enabled = str(
        getattr(settings, "retrieval_hybrid_mode", "off") or "off"
    ).lower() in {"shadow", "active"}
    retrieval_shadow = run_memory_surface_shadow_search(
        db,
        query=query,
        candidate_memory_ids=[memory.id for memory in memories],
        settings=settings,
        limit=rerank_candidate_limit,
        include_surface_rerank=not final_rerank_enabled,
    )
    return MemoryRecallEvidence(
        query=query,
        memories=memories,
        facts_by_memory=facts_by_memory,
        sparse_matches=sparse_matches,
        graph_expansion=graph_expansion,
        graph_signals=graph_signals,
        retrieval_shadow=retrieval_shadow,
        rerank_candidate_limit=rerank_candidate_limit,
    )


def run_memory_recall_pipeline(
    evidence: MemoryRecallEvidence,
    *,
    lexical_memory_ids: list[str],
    settings: Any | None,
    selected_limit: int,
    off_mode_stage: str,
) -> MemoryRecallPipeline:
    """Build route-balanced candidates and invoke the configured final reranker."""

    recall_pool = build_memory_recall_pool(
        evidence.memories,
        facts_by_memory=evidence.facts_by_memory,
        routes={
            "sparse": list(evidence.sparse_matches),
            "dense": [
                str(item["target_id"])
                for item in evidence.retrieval_shadow.get("grouped_results", [])
                if item.get("active_rank_eligible") is True
                and isinstance(item.get("target_id"), str)
            ],
            "graph": list(evidence.graph_signals),
            "lexical": lexical_memory_ids,
        },
        limit=evidence.rerank_candidate_limit,
    )
    rerank_plan = run_memory_relevance_rerank(
        query=evidence.query,
        candidates=recall_pool,
        settings=settings,
        selected_limit=selected_limit,
    )
    retrieval_stages = (
        [
            "fts5_sparse_v1",
            "dense_memory_surfaces_v1",
            "networkx_graph_recall_v1",
            "round_robin_recall_pool_v1",
            FINAL_RERANK_POLICY,
        ]
        if rerank_plan.status.get("mode") != "off"
        else ["fts5_sparse_v1", off_mode_stage]
    )
    return MemoryRecallPipeline(
        evidence=evidence,
        recall_pool=recall_pool,
        rerank_plan=rerank_plan,
        retrieval_stages=retrieval_stages,
    )

"""Memory-level recall pooling and final relevance arbitration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.mind.facts import fact_search_text
from app.mind import shadow_retrieval
from app.mind.openrouter_retrieval import OpenRouterRetrievalError
from app.storage.models import MemoryFact, MemoryRecord


FINAL_RERANK_POLICY = "memory_level_rerank_final_arbiter_v1"
RECALL_POOL_POLICY = "round_robin_sparse_dense_graph_lexical_v1"


@dataclass(frozen=True)
class MemoryRecallCandidate:
    memory: MemoryRecord
    document: str
    routes: tuple[str, ...]
    route_ranks: dict[str, int]


@dataclass(frozen=True)
class MemoryRerankEntry:
    memory: MemoryRecord
    memory_id: str
    score: float
    rank: int | None
    accepted: bool
    evaluated: bool
    routes: tuple[str, ...]
    route_ranks: dict[str, int]


@dataclass(frozen=True)
class MemoryRerankPlan:
    status: dict[str, Any]
    entries: list[MemoryRerankEntry]

    @property
    def active(self) -> bool:
        return self.status.get("mode") == "active"

    @property
    def completed(self) -> bool:
        return self.status.get("status") in {"completed", "no_candidates"}


def build_memory_recall_pool(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]],
    routes: dict[str, list[str]],
    limit: int,
) -> list[MemoryRecallCandidate]:
    """Interleave independent recall routes without fusing arbitrary scores."""

    if limit <= 0:
        return []
    memory_by_id = {memory.id: memory for memory in memories}
    normalized_routes = {
        route: [memory_id for memory_id in memory_ids if memory_id in memory_by_id]
        for route, memory_ids in routes.items()
    }
    route_ranks = {
        route: {
            memory_id: rank
            for rank, memory_id in enumerate(memory_ids, start=1)
        }
        for route, memory_ids in normalized_routes.items()
    }
    ordered_ids: list[str] = []
    seen: set[str] = set()
    depth = 0
    while len(ordered_ids) < limit:
        added = False
        for memory_ids in normalized_routes.values():
            if depth >= len(memory_ids):
                continue
            memory_id = memory_ids[depth]
            added = True
            if memory_id in seen:
                continue
            seen.add(memory_id)
            ordered_ids.append(memory_id)
            if len(ordered_ids) >= limit:
                break
        if not added:
            break
        depth += 1

    return [
        MemoryRecallCandidate(
            memory=memory_by_id[memory_id],
            document=_memory_rerank_document(
                memory_by_id[memory_id],
                facts=facts_by_memory.get(memory_id, []),
            ),
            routes=tuple(
                route
                for route, memory_ids in normalized_routes.items()
                if memory_id in memory_ids
            ),
            route_ranks={
                route: ranks[memory_id]
                for route, ranks in route_ranks.items()
                if memory_id in ranks
            },
        )
        for memory_id in ordered_ids
    ]


def run_memory_relevance_rerank(
    *,
    query: str,
    candidates: list[MemoryRecallCandidate],
    settings: Any | None,
    selected_limit: int,
) -> MemoryRerankPlan:
    """Let the configured reranker alone accept and order active results."""

    mode = str(getattr(settings, "retrieval_hybrid_mode", "off") or "off").lower()
    configured_threshold = getattr(
        settings,
        "retrieval_hybrid_min_rerank_score",
        0.01,
    )
    threshold = float(0.01 if configured_threshold is None else configured_threshold)
    candidate_limit = int(
        getattr(settings, "retrieval_shadow_rerank_candidate_limit", 20) or 20
    )
    bounded_candidates = candidates[:candidate_limit]
    base_status: dict[str, Any] = {
        "mode": mode,
        "active": mode == "active",
        "ranking_policy": FINAL_RERANK_POLICY,
        "recall_pool_policy": RECALL_POOL_POLICY,
        "candidate_count": len(bounded_candidates),
        "candidate_limit": candidate_limit,
        "selected_limit": selected_limit,
        "acceptance_threshold": threshold,
        "legacy_weighted_fusion": False,
        "fail_closed": mode == "active",
        "entry_count": 0,
    }
    if mode == "off":
        return MemoryRerankPlan(
            status={**base_status, "ok": False, "status": "disabled"},
            entries=[],
        )
    if not bounded_candidates:
        return MemoryRerankPlan(
            status={**base_status, "ok": True, "status": "no_candidates"},
            entries=[],
        )

    configuration_error = _configuration_error(settings)
    if configuration_error is not None:
        return MemoryRerankPlan(
            status={
                **base_status,
                "ok": False,
                "status": "configuration_error",
                **configuration_error,
            },
            entries=_unevaluated_entries(bounded_candidates),
        )

    model = str(getattr(settings, "retrieval_shadow_rerank_model", "") or "")
    top_n_setting = int(
        getattr(settings, "retrieval_shadow_rerank_top_n", 10) or 10
    )
    top_n = min(
        len(bounded_candidates),
        max(top_n_setting, max(selected_limit, 1)),
    )
    client = shadow_retrieval.OpenRouterRetrievalClient(
        api_key=str(getattr(settings, "openrouter_api_key", "") or "").strip(),
        base_url=str(
            getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")
            or "https://openrouter.ai/api/v1"
        ),
        timeout_seconds=float(
            getattr(settings, "retrieval_shadow_http_timeout_seconds", 30.0) or 30.0
        ),
    )
    try:
        response = client.rerank(
            model=model,
            query=query,
            documents=[candidate.document for candidate in bounded_candidates],
            top_n=top_n,
        )
    except OpenRouterRetrievalError as exc:
        return MemoryRerankPlan(
            status={
                **base_status,
                "ok": False,
                "status": "backend_error",
                "error_code": "retrieval_rerank.backend_error",
                "error_message": str(exc),
                "error_type": type(exc).__name__,
            },
            entries=_unevaluated_entries(bounded_candidates),
        )

    result_by_index: dict[int, tuple[int, float]] = {}
    for rank, item in enumerate(_rerank_items(response), start=1):
        index = item.get("index")
        if not isinstance(index, int) or not 0 <= index < len(bounded_candidates):
            continue
        score = float(item.get("relevance_score") or 0.0)
        result_by_index[index] = (rank, score)

    entries: list[MemoryRerankEntry] = []
    for index, candidate in enumerate(bounded_candidates):
        result = result_by_index.get(index)
        entries.append(
            MemoryRerankEntry(
                memory=candidate.memory,
                memory_id=candidate.memory.id,
                score=result[1] if result is not None else 0.0,
                rank=result[0] if result is not None else None,
                accepted=result is not None and result[1] >= threshold,
                evaluated=result is not None,
                routes=candidate.routes,
                route_ranks=candidate.route_ranks,
            )
        )
    entries.sort(
        key=lambda entry: (
            entry.accepted,
            entry.evaluated,
            entry.score,
            -(entry.rank or 10_000),
        ),
        reverse=True,
    )
    accepted_count = sum(entry.accepted for entry in entries)
    return MemoryRerankPlan(
        status={
            **base_status,
            "ok": True,
            "status": "completed",
            "model": model,
            "top_n": top_n,
            "evaluated_count": len(result_by_index),
            "accepted_count": accepted_count,
            "entry_count": accepted_count,
            "response_id": response.get("id"),
            "provider": response.get("provider"),
            "usage": response.get("usage")
            if isinstance(response.get("usage"), dict)
            else {},
        },
        entries=entries,
    )


def rerank_status_payload(plan: MemoryRerankPlan) -> dict[str, Any]:
    return {
        **plan.status,
        "entries": [
            {
                "memory_id": entry.memory_id,
                "rank": entry.rank,
                "score": round(entry.score, 6),
                "accepted": entry.accepted,
                "evaluated": entry.evaluated,
                "recall_routes": list(entry.routes),
                "route_ranks": entry.route_ranks,
            }
            for entry in plan.entries
        ],
    }


def _memory_rerank_document(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact],
) -> str:
    return "\n".join(
        item
        for item in [
            f"Memory id: {memory.id}",
            f"Type: {memory.memory_type}",
            f"Scope: {memory.scope}",
            f"Content: {memory.content}",
            f"Canonical facts: {fact_search_text(facts)}" if facts else "",
        ]
        if item
    )


def _configuration_error(settings: Any | None) -> dict[str, str] | None:
    if not bool(getattr(settings, "retrieval_shadow_enabled", False)):
        return {
            "error_code": "retrieval_rerank.disabled",
            "error_message": "Final rerank requires retrieval_shadow_enabled=true.",
        }
    backend = str(getattr(settings, "retrieval_shadow_backend", "none") or "none")
    if backend != "openrouter":
        return {
            "error_code": "retrieval_rerank.unsupported_backend",
            "error_message": "Final rerank currently requires the OpenRouter backend.",
        }
    if not bool(getattr(settings, "retrieval_shadow_rerank_enabled", False)):
        return {
            "error_code": "retrieval_rerank.disabled",
            "error_message": "Final rerank requires rerank_enabled=true.",
        }
    if not str(getattr(settings, "openrouter_api_key", "") or "").strip():
        return {
            "error_code": "retrieval_rerank.missing_key",
            "error_message": "Final rerank requires an OpenRouter API key.",
        }
    return None


def _unevaluated_entries(
    candidates: list[MemoryRecallCandidate],
) -> list[MemoryRerankEntry]:
    return [
        MemoryRerankEntry(
            memory=candidate.memory,
            memory_id=candidate.memory.id,
            score=0.0,
            rank=None,
            accepted=False,
            evaluated=False,
            routes=candidate.routes,
            route_ranks=candidate.route_ranks,
        )
        for candidate in candidates
    ]


def _rerank_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    results = response.get("results")
    if isinstance(results, list):
        return [item for item in results if isinstance(item, dict)]
    data = response.get("data")
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []

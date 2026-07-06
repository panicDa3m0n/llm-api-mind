from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any, Iterable

from sqlmodel import Session

from app.mind.openrouter_retrieval import (
    OpenRouterRetrievalClient,
    OpenRouterRetrievalError,
)
from app.mind.surface_taxonomy import (
    surface_can_promote_active,
    surface_retrieval_role,
)
from app.storage import repositories
from app.storage.models import MemorySurface


SHADOW_RANKING_POLICY = "trace_only_no_active_ranking"
GROUPING_POLICY = "memory_target_role_aware_surface_score_v2"
SUPPORTED_BACKENDS = {"none", "local", "milvus_lite", "openrouter"}
TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ_]+")


def retrieval_shadow_status(settings: Any | None) -> dict[str, Any]:
    enabled = bool(getattr(settings, "retrieval_shadow_enabled", False))
    backend = _shadow_backend(settings)
    return {
        "enabled": enabled,
        "backend": backend,
        "embedding_model": _embedding_model(settings),
        "vector_dim": _vector_dim(settings),
        "ranking_policy": SHADOW_RANKING_POLICY,
        "rerank": _rerank_status(settings),
    }


def run_memory_surface_shadow_search(
    db: Session,
    *,
    query: str,
    candidate_memory_ids: Iterable[str],
    settings: Any | None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run optional vector-shadow retrieval over derived memory surfaces.

    V1.3.1 intentionally keeps this path trace-only. Results are diagnostic
    evidence for future hybrid retrieval and must not affect active memory
    ordering until real embeddings and scoring policies are validated.
    """

    status = retrieval_shadow_status(settings)
    requested_limit = limit or int(getattr(settings, "retrieval_shadow_top_k", 10))
    target_ids = list(dict.fromkeys(candidate_memory_ids))
    payload: dict[str, Any] = {
        **status,
        "operation": "memory.surface_shadow_search",
        "limit": requested_limit,
        "candidate_memory_count": len(target_ids),
        "candidate_surface_count": 0,
        "results": [],
        "grouped_results": [],
        "ok": False,
        "status": "disabled",
    }
    if not status["enabled"]:
        return payload

    backend = status["backend"]
    if backend not in SUPPORTED_BACKENDS:
        payload.update(
            {
                "status": "configuration_error",
                "error_code": "retrieval_shadow.unsupported_backend",
                "error_message": (
                    "retrieval_shadow_backend must be one of "
                    f"{sorted(SUPPORTED_BACKENDS)}."
                ),
            }
        )
        return payload
    if backend == "none":
        payload.update(
            {
                "status": "disabled_backend",
                "error_code": "retrieval_shadow.backend_none",
                "error_message": "Shadow retrieval is enabled but backend is none.",
            }
        )
        return payload

    cloud_surface_limit = int(
        getattr(settings, "retrieval_shadow_cloud_surface_limit", 50) or 50
    )
    surface_fetch_limit = max(
        requested_limit * 8,
        len(target_ids) * 6,
        cloud_surface_limit,
        1,
    )
    surfaces = repositories.list_memory_surfaces_by_targets(
        db,
        target_type="memory",
        target_ids=target_ids,
        surface_kind=None,
        status="active",
        limit=surface_fetch_limit,
    )
    payload["candidate_surface_count"] = len(surfaces)
    payload["candidate_surface_fetch_limit"] = surface_fetch_limit
    if not surfaces:
        payload.update({"ok": True, "status": "no_candidate_surfaces"})
        return payload

    if backend == "local":
        payload.update(_run_local_shadow(query, surfaces, settings, requested_limit))
        return payload
    if backend == "milvus_lite":
        payload.update(
            _run_milvus_lite_shadow(query, surfaces, settings, requested_limit)
        )
        return payload
    if backend == "openrouter":
        payload.update(
            _run_openrouter_shadow(db, query, surfaces, settings, requested_limit)
        )
        return payload
    return payload


def embed_text_for_shadow(text: str, *, dim: int) -> list[float]:
    """Small deterministic embedding used only to validate retrieval plumbing.

    This is not a semantic model. It hashes normalized lexical units into a
    stable vector so traces can prove index/search flow before V1.4 introduces
    real embeddings.
    """

    vector = [0.0] * dim
    tokens = TOKEN_RE.findall(text.casefold())
    if not tokens:
        tokens = [text.casefold()] if text else ["empty"]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 20) / 20.0
        vector[index] += sign * weight
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 0:
        return vector
    return [value / length for value in vector]


def _run_local_shadow(
    query: str,
    surfaces: list[MemorySurface],
    settings: Any | None,
    limit: int,
) -> dict[str, Any]:
    dim = _vector_dim(settings)
    query_vector = embed_text_for_shadow(query, dim=dim)
    scored = []
    for surface in surfaces:
        surface_vector = embed_text_for_shadow(surface.content, dim=dim)
        scored.append((_dot(query_vector, surface_vector), surface))
    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    all_results = [
        _surface_result_payload(
            surface,
            score=score,
            backend="local",
            embedding_model=_embedding_model(settings),
            why_relevant=(
                "Deterministic local vector shadow over memory_surfaces; "
                "trace-only and not used for active ranking."
            ),
        )
        for score, surface in scored
    ]
    return {
        "ok": True,
        "status": "completed",
        "results": all_results[:limit],
        "grouped_results": _group_surface_results(all_results, limit=limit),
    }


def _run_milvus_lite_shadow(
    query: str,
    surfaces: list[MemorySurface],
    settings: Any | None,
    limit: int,
) -> dict[str, Any]:
    try:
        from pymilvus import MilvusClient
    except Exception as exc:
        return {
            "ok": False,
            "status": "backend_unavailable",
            "error_code": "retrieval_shadow.milvus_unavailable",
            "error_message": (
                "Install the optional backend dependency with "
                "`pip install -e 'backend[retrieval]'` or "
                "`pip install 'pymilvus[milvus-lite]'`."
            ),
            "error_type": type(exc).__name__,
        }

    dim = _vector_dim(settings)
    uri = str(getattr(settings, "milvus_lite_uri", "./data/milvus_lite_shadow.db"))
    collection = str(
        getattr(settings, "milvus_collection", "memory_surfaces_shadow")
    )
    try:
        directory = os.path.dirname(uri)
        if directory:
            os.makedirs(directory, exist_ok=True)
        client = MilvusClient(uri=uri)
        if not client.has_collection(collection_name=collection):
            client.create_collection(
                collection_name=collection,
                dimension=dim,
                primary_field_name="id",
                id_type="string",
                vector_field_name="vector",
                metric_type="COSINE",
                auto_id=False,
            )
        data = [
            {
                "id": surface.id,
                "vector": embed_text_for_shadow(surface.content, dim=dim),
                "target_id": surface.target_id,
                "target_type": surface.target_type,
                "surface_kind": surface.surface_kind,
                "content_hash": surface.content_hash,
            }
            for surface in surfaces
        ]
        client.upsert(collection_name=collection, data=data)
        raw_results = client.search(
            collection_name=collection,
            data=[embed_text_for_shadow(query, dim=dim)],
            limit=limit,
            output_fields=[
                "target_id",
                "target_type",
                "surface_kind",
                "content_hash",
            ],
        )
        surface_by_id = {surface.id: surface for surface in surfaces}
        results = []
        for hit in _flatten_milvus_hits(raw_results):
            surface_id = str(hit.get("id") or hit.get("pk") or "")
            surface = surface_by_id.get(surface_id)
            if surface is None:
                continue
            results.append(
                _surface_result_payload(
                    surface,
                    score=_milvus_score(hit),
                    backend="milvus_lite",
                    embedding_model=_embedding_model(settings),
                    why_relevant=(
                        "Milvus Lite vector shadow over memory_surfaces; "
                        "trace-only and not used for active ranking."
                    ),
                )
            )
        return {
            "ok": True,
            "status": "completed",
            "uri": uri,
            "collection": collection,
            "results": results,
            "grouped_results": _group_surface_results(results, limit=limit),
        }
    except Exception as exc:
        return {
            "ok": False,
            "status": "backend_error",
            "uri": uri,
            "collection": collection,
            "error_code": "retrieval_shadow.milvus_error",
            "error_message": str(exc),
            "error_type": type(exc).__name__,
        }
    finally:
        close = locals().get("client")
        if close is not None and hasattr(close, "close"):
            close.close()


def _run_openrouter_shadow(
    db: Session,
    query: str,
    surfaces: list[MemorySurface],
    settings: Any | None,
    limit: int,
) -> dict[str, Any]:
    api_key = str(getattr(settings, "openrouter_api_key", "") or "").strip()
    if not api_key:
        return {
            "ok": False,
            "status": "configuration_error",
            "error_code": "retrieval_shadow.openrouter_missing_key",
            "error_message": (
                "Set OPENROUTER_API_KEY before using "
                "RETRIEVAL_SHADOW_BACKEND=openrouter."
            ),
        }

    cloud_surface_limit = int(
        getattr(settings, "retrieval_shadow_cloud_surface_limit", 50) or 50
    )
    limited_surfaces = surfaces[:cloud_surface_limit]
    base_url = str(
        getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")
        or "https://openrouter.ai/api/v1"
    )
    timeout_seconds = float(
        getattr(settings, "retrieval_shadow_http_timeout_seconds", 30.0) or 30.0
    )
    model = _embedding_model(settings)
    client = OpenRouterRetrievalClient(
        api_key=api_key,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
    )
    try:
        query_vector, surface_vectors, cache_stats = _embed_query_and_surfaces(
            db,
            client=client,
            query=query,
            surfaces=limited_surfaces,
            model=model,
        )
    except OpenRouterRetrievalError as exc:
        return _openrouter_error_payload(exc, status="backend_error", stage="embedding")

    scored: list[tuple[float, MemorySurface]] = []
    for surface in limited_surfaces:
        vector = surface_vectors.get(surface.id)
        if vector is None:
            continue
        scored.append((_cosine(query_vector, vector), surface))
    scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
    all_dense_results = [
        _surface_result_payload(
            surface,
            score=score,
            backend="openrouter",
            embedding_model=model,
            why_relevant=(
                "OpenRouter cloud embedding shadow over memory_surfaces; "
                "trace-only and not used for active ranking."
            ),
        )
        for score, surface in scored
    ]
    grouped_candidates = _group_scored_surfaces(
        scored,
        backend="openrouter",
        embedding_model=model,
        why_relevant=(
            "OpenRouter cloud embedding shadow grouped by target memory; "
            "trace-only unless retrieval_hybrid_mode promotes it."
        ),
        limit=max(
            limit,
            int(getattr(settings, "retrieval_shadow_rerank_candidate_limit", 20) or 20),
        ),
    )

    return {
        "ok": True,
        "status": "completed",
        "results": all_dense_results[:limit],
        "grouped_results": _public_grouped_results(grouped_candidates[:limit]),
        "base_url": base_url,
        "cloud_surface_limit": cloud_surface_limit,
        "candidate_surface_count_after_limit": len(limited_surfaces),
        "truncated_surface_count": max(len(surfaces) - len(limited_surfaces), 0),
        "vector_dim": len(query_vector),
        "embedding_cache": cache_stats,
        "rerank": _run_openrouter_rerank_shadow(
            client,
            query=query,
            scored_surfaces=scored,
            grouped_candidates=grouped_candidates,
            settings=settings,
            limit=limit,
        ),
    }


def _embed_query_and_surfaces(
    db: Session,
    *,
    client: OpenRouterRetrievalClient,
    query: str,
    surfaces: list[MemorySurface],
    model: str,
) -> tuple[list[float], dict[str, list[float]], dict[str, Any]]:
    provider = "openrouter"
    surface_vectors: dict[str, list[float]] = {}
    missing_surfaces: list[MemorySurface] = []
    for surface in surfaces:
        cache_key = _embedding_cache_key(
            provider=provider,
            model=model,
            input_hash=surface.content_hash,
        )
        cached = repositories.get_embedding_vector_by_key(db, object_key=cache_key)
        vector = _coerce_vector(cached.vector_json if cached is not None else None)
        if vector is None:
            missing_surfaces.append(surface)
        else:
            surface_vectors[surface.id] = vector
            repositories.mark_memory_surface_embedded(
                db,
                surface_id=surface.id,
                embedding_model=model,
                embedding_vector_id=cached.id,
            )

    vectors = client.embed_texts(
        model=model,
        texts=[query] + [surface.content for surface in missing_surfaces],
    )
    query_vector = vectors[0]
    inserted = 0
    for surface, vector in zip(missing_surfaces, vectors[1:]):
        cache_key = _embedding_cache_key(
            provider=provider,
            model=model,
            input_hash=surface.content_hash,
        )
        embedding_record, _ = repositories.upsert_embedding_vector(
            db,
            object_key=cache_key,
            provider=provider,
            model=model,
            input_hash=surface.content_hash,
            vector=vector,
            source_surface_id=surface.id,
            target_type=surface.target_type,
            target_id=surface.target_id,
            surface_kind=surface.surface_kind,
            metadata={
                "source": "retrieval_shadow.openrouter",
                "content_hash": surface.content_hash,
            },
        )
        repositories.mark_memory_surface_embedded(
            db,
            surface_id=surface.id,
            embedding_model=model,
            embedding_vector_id=embedding_record.id,
        )
        surface_vectors[surface.id] = vector
        inserted += 1

    return query_vector, surface_vectors, {
        "surface_count": len(surfaces),
        "hits": len(surfaces) - len(missing_surfaces),
        "misses": len(missing_surfaces),
        "inserted": inserted,
        "query_embedded": True,
    }


def _run_openrouter_rerank_shadow(
    client: OpenRouterRetrievalClient,
    *,
    query: str,
    scored_surfaces: list[tuple[float, MemorySurface]],
    grouped_candidates: list[dict[str, Any]] | None = None,
    settings: Any | None,
    limit: int,
) -> dict[str, Any]:
    rerank_enabled = bool(getattr(settings, "retrieval_shadow_rerank_enabled", False))
    model = str(
        getattr(
            settings,
            "retrieval_shadow_rerank_model",
            "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
        )
        or "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
    )
    candidate_limit = int(
        getattr(settings, "retrieval_shadow_rerank_candidate_limit", 20) or 20
    )
    top_n = int(getattr(settings, "retrieval_shadow_rerank_top_n", 10) or 10)
    status = {
        "enabled": rerank_enabled,
        "model": model,
        "candidate_limit": candidate_limit,
        "top_n": min(top_n, limit),
        "ranking_policy": SHADOW_RANKING_POLICY,
    }
    if not rerank_enabled:
        return {
            **status,
            "ok": False,
            "status": "disabled",
            "results": [],
            "grouped_results": [],
        }

    candidates = scored_surfaces[:candidate_limit]
    if not candidates:
        return {
            **status,
            "ok": True,
            "status": "no_candidates",
            "results": [],
            "grouped_results": [],
        }

    try:
        response = client.rerank(
            model=model,
            query=query,
            documents=[_rerank_document(surface) for _, surface in candidates],
            top_n=min(top_n, len(candidates), limit),
        )
    except OpenRouterRetrievalError as exc:
        return {
            **status,
            **_openrouter_error_payload(
                exc,
                status="backend_error",
                stage="rerank",
            ),
        }

    dense_by_index = {
        index: (score, surface)
        for index, (score, surface) in enumerate(candidates)
    }
    results = []
    for rank, item in enumerate(_rerank_items(response), start=1):
        index = item.get("index")
        if not isinstance(index, int) or index not in dense_by_index:
            continue
        dense_score, surface = dense_by_index[index]
        result = _surface_result_payload(
            surface,
            score=float(item.get("relevance_score") or 0.0),
            backend="openrouter_rerank",
            embedding_model=model,
            why_relevant=(
                "OpenRouter rerank shadow over dense candidates; trace-only "
                "and not used for active ranking unless hybrid mode is active."
            ),
        )
        result["rerank_rank"] = rank
        result["rerank_score"] = result["score"]
        result["dense_score"] = round(float(dense_score), 6)
        results.append(result)
    grouped_rerank = _run_openrouter_grouped_rerank_shadow(
        client,
        query=query,
        grouped_candidates=grouped_candidates or [],
        model=model,
        limit=limit,
    )
    return {
        **status,
        "ok": True,
        "status": "completed",
        "candidate_count": len(candidates),
        "response_id": response.get("id"),
        "provider": response.get("provider"),
        "usage": response.get("usage") if isinstance(response.get("usage"), dict) else {},
        "results": results,
        "grouped_status": grouped_rerank["status"],
        "grouped_results": grouped_rerank["results"],
    }


def _run_openrouter_grouped_rerank_shadow(
    client: OpenRouterRetrievalClient,
    *,
    query: str,
    grouped_candidates: list[dict[str, Any]],
    model: str,
    limit: int,
) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in grouped_candidates
        if candidate.get("active_rank_eligible") is True
    ][:limit]
    if not candidates:
        return {"status": "no_grouped_candidates", "results": []}
    try:
        response = client.rerank(
            model=model,
            query=query,
            documents=[
                str(candidate.get("_rerank_document") or "")
                for candidate in candidates
            ],
            top_n=min(len(candidates), limit),
        )
    except OpenRouterRetrievalError as exc:
        return {
            "status": "backend_error",
            "results": [],
            "error": _openrouter_error_payload(
                exc,
                status="backend_error",
                stage="grouped_rerank",
            ),
        }

    by_index = {index: candidate for index, candidate in enumerate(candidates)}
    results: list[dict[str, Any]] = []
    for rank, item in enumerate(_rerank_items(response), start=1):
        index = item.get("index")
        if not isinstance(index, int) or index not in by_index:
            continue
        candidate = dict(by_index[index])
        score = float(item.get("relevance_score") or 0.0)
        candidate["score"] = round(score, 6)
        candidate["rerank_score"] = round(score, 6)
        candidate["rerank_rank"] = rank
        candidate["backend"] = "openrouter_grouped_rerank"
        candidate["embedding_model"] = model
        candidate["why_relevant"] = (
            "OpenRouter rerank over memory-level dense candidates; trace-only "
            "unless retrieval_hybrid_mode promotes it."
        )
        results.append(_public_grouped_result(candidate))
    return {
        "status": "completed",
        "response_id": response.get("id"),
        "provider": response.get("provider"),
        "usage": response.get("usage") if isinstance(response.get("usage"), dict) else {},
        "results": results,
    }


def _group_scored_surfaces(
    scored_surfaces: list[tuple[float, MemorySurface]],
    *,
    backend: str,
    embedding_model: str,
    why_relevant: str,
    limit: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for score, surface in scored_surfaces:
        result = _surface_result_payload(
            surface,
            score=score,
            backend=backend,
            embedding_model=embedding_model,
            why_relevant=why_relevant,
        )
        result["_content"] = surface.content
        promotable = result["active_rank_eligible"] is True
        target = grouped.setdefault(
            surface.target_id,
            {
                "target_type": surface.target_type,
                "target_id": surface.target_id,
                "score": 0.0,
                "raw_score": result["score"],
                "promotable_score": 0.0,
                "support_score": 0.0,
                "active_rank_eligible": False,
                "backend": backend,
                "embedding_model": embedding_model,
                "source_session_id": surface.source_session_id,
                "surface_count": 0,
                "surface_kinds": [],
                "surface_roles": [],
                "promotable_surface_kinds": [],
                "support_surface_kinds": [],
                "top_surface_id": surface.id,
                "top_surface_kind": surface.surface_kind,
                "top_surface_role": result["surface_role"],
                "top_surface_score": 0.0,
                "top_promotable_surface_id": None,
                "top_promotable_surface_kind": None,
                "top_promotable_surface_score": 0.0,
                "top_support_surface_id": None,
                "top_support_surface_kind": None,
                "top_support_surface_score": 0.0,
                "why_relevant": why_relevant,
                "ranking_policy": GROUPING_POLICY,
                "contributing_surfaces": [],
                "_rerank_surface_docs": [],
            },
        )
        target["surface_count"] += 1
        if surface.surface_kind not in target["surface_kinds"]:
            target["surface_kinds"].append(surface.surface_kind)
        if result["surface_role"] not in target["surface_roles"]:
            target["surface_roles"].append(result["surface_role"])
        if promotable:
            if surface.surface_kind not in target["promotable_surface_kinds"]:
                target["promotable_surface_kinds"].append(surface.surface_kind)
        elif surface.surface_kind not in target["support_surface_kinds"]:
            target["support_surface_kinds"].append(surface.surface_kind)
        if result["score"] > float(target["raw_score"]):
            target["raw_score"] = result["score"]
        if promotable and result["score"] > float(target["promotable_score"]):
            target["active_rank_eligible"] = True
            target["score"] = result["score"]
            target["promotable_score"] = result["score"]
            target["source_session_id"] = surface.source_session_id
            target["top_surface_id"] = surface.id
            target["top_surface_kind"] = surface.surface_kind
            target["top_surface_role"] = result["surface_role"]
            target["top_surface_score"] = result["score"]
            target["top_promotable_surface_id"] = surface.id
            target["top_promotable_surface_kind"] = surface.surface_kind
            target["top_promotable_surface_score"] = result["score"]
        if not promotable and result["score"] > float(target["support_score"]):
            target["support_score"] = result["score"]
            target["top_support_surface_id"] = surface.id
            target["top_support_surface_kind"] = surface.surface_kind
            target["top_support_surface_score"] = result["score"]
            if target["active_rank_eligible"] is False:
                target["score"] = result["score"]
                target["top_surface_id"] = surface.id
                target["top_surface_kind"] = surface.surface_kind
                target["top_surface_role"] = result["surface_role"]
                target["top_surface_score"] = result["score"]
        if len(target["contributing_surfaces"]) < 5:
            target["contributing_surfaces"].append(result)
        if promotable:
            target["_rerank_surface_docs"].append(_rerank_document(surface))

    candidates = sorted(
        grouped.values(),
        key=lambda item: (
            bool(item.get("active_rank_eligible")),
            float(item.get("promotable_score") or 0.0),
            float(item.get("support_score") or 0.0),
            float(item.get("raw_score") or 0.0),
            str(item.get("target_id") or ""),
        ),
        reverse=True,
    )
    for candidate in candidates:
        candidate["_rerank_document"] = "\n\n".join(
            [
                f"target_type: {candidate['target_type']}",
                f"target_id: {candidate['target_id']}",
                f"surface_kinds: {', '.join(candidate['surface_kinds'])}",
                f"promotable_surface_kinds: {', '.join(candidate['promotable_surface_kinds'])}",
                f"support_surface_kinds: {', '.join(candidate['support_surface_kinds'])}",
                *candidate.pop("_rerank_surface_docs", []),
            ]
        )
    return candidates[:limit]


def _group_surface_results(
    results: list[dict[str, Any]],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for result in results:
        target_id = result.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            continue
        target = grouped.setdefault(
            target_id,
            {
                "target_type": result.get("target_type"),
                "target_id": target_id,
                "score": 0.0,
                "raw_score": result.get("score", 0.0),
                "promotable_score": 0.0,
                "support_score": 0.0,
                "active_rank_eligible": False,
                "backend": result.get("backend"),
                "embedding_model": result.get("embedding_model"),
                "source_session_id": result.get("source_session_id"),
                "surface_count": 0,
                "surface_kinds": [],
                "surface_roles": [],
                "promotable_surface_kinds": [],
                "support_surface_kinds": [],
                "top_surface_id": result.get("surface_id"),
                "top_surface_kind": result.get("surface_kind"),
                "top_surface_role": result.get("surface_role"),
                "top_surface_score": 0.0,
                "top_promotable_surface_id": None,
                "top_promotable_surface_kind": None,
                "top_promotable_surface_score": 0.0,
                "top_support_surface_id": None,
                "top_support_surface_kind": None,
                "top_support_surface_score": 0.0,
                "why_relevant": (
                    "Memory-level grouping over raw retrieval_shadow surfaces."
                ),
                "ranking_policy": GROUPING_POLICY,
                "contributing_surfaces": [],
            },
        )
        target["surface_count"] += 1
        surface_kind = result.get("surface_kind")
        if isinstance(surface_kind, str) and surface_kind not in target["surface_kinds"]:
            target["surface_kinds"].append(surface_kind)
        surface_role = result.get("surface_role")
        if isinstance(surface_role, str) and surface_role not in target["surface_roles"]:
            target["surface_roles"].append(surface_role)
        promotable = result.get("active_rank_eligible") is True
        if promotable and isinstance(surface_kind, str):
            if surface_kind not in target["promotable_surface_kinds"]:
                target["promotable_surface_kinds"].append(surface_kind)
        if not promotable and isinstance(surface_kind, str):
            if surface_kind not in target["support_surface_kinds"]:
                target["support_surface_kinds"].append(surface_kind)
        result_score = _result_score(result)
        if result_score > float(target["raw_score"]):
            target["raw_score"] = result_score
        if promotable and result_score > float(target["promotable_score"]):
            target["active_rank_eligible"] = True
            target["score"] = result.get("score", 0.0)
            target["promotable_score"] = result.get("score", 0.0)
            target["source_session_id"] = result.get("source_session_id")
            target["top_surface_id"] = result.get("surface_id")
            target["top_surface_kind"] = result.get("surface_kind")
            target["top_surface_role"] = result.get("surface_role")
            target["top_surface_score"] = result.get("score", 0.0)
            target["top_promotable_surface_id"] = result.get("surface_id")
            target["top_promotable_surface_kind"] = result.get("surface_kind")
            target["top_promotable_surface_score"] = result.get("score", 0.0)
        if not promotable and result_score > float(target["support_score"]):
            target["support_score"] = result.get("score", 0.0)
            target["top_support_surface_id"] = result.get("surface_id")
            target["top_support_surface_kind"] = result.get("surface_kind")
            target["top_support_surface_score"] = result.get("score", 0.0)
            if target["active_rank_eligible"] is False:
                target["score"] = result.get("score", 0.0)
                target["top_surface_id"] = result.get("surface_id")
                target["top_surface_kind"] = result.get("surface_kind")
                target["top_surface_role"] = result.get("surface_role")
                target["top_surface_score"] = result.get("score", 0.0)
        if len(target["contributing_surfaces"]) < 5:
            target["contributing_surfaces"].append(result)
    return sorted(
        (_public_grouped_result(item) for item in grouped.values()),
        key=lambda item: (
            bool(item.get("active_rank_eligible")),
            float(item.get("promotable_score") or 0.0),
            float(item.get("support_score") or 0.0),
            float(item.get("raw_score") or 0.0),
            str(item.get("target_id") or ""),
        ),
        reverse=True,
    )[:limit]


def _public_grouped_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_public_grouped_result(item) for item in results]


def _public_grouped_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if not key.startswith("_")
    }


def _result_score(value: dict[str, Any]) -> float:
    raw = value.get("score")
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def _surface_result_payload(
    surface: MemorySurface,
    *,
    score: float,
    backend: str,
    embedding_model: str,
    why_relevant: str,
) -> dict[str, Any]:
    surface_role = surface_retrieval_role(surface.surface_kind)
    active_rank_eligible = surface_can_promote_active(surface.surface_kind)
    return {
        "surface_id": surface.id,
        "target_type": surface.target_type,
        "target_id": surface.target_id,
        "surface_kind": surface.surface_kind,
        "surface_role": surface_role,
        "active_rank_eligible": active_rank_eligible,
        "score": round(float(score), 6),
        "backend": backend,
        "embedding_model": embedding_model,
        "content_hash": surface.content_hash,
        "source_session_id": surface.source_session_id,
        "why_relevant": why_relevant,
    }


def _shadow_backend(settings: Any | None) -> str:
    backend = str(getattr(settings, "retrieval_shadow_backend", "none") or "none")
    return backend.strip().casefold()


def _embedding_model(settings: Any | None) -> str:
    return str(
        getattr(settings, "retrieval_shadow_embedding_model", "local_hash_embedding_v1")
        or "local_hash_embedding_v1"
    )


def _vector_dim(settings: Any | None) -> int:
    return int(getattr(settings, "retrieval_shadow_vector_dim", 2048) or 2048)


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0.0
    left_length = math.sqrt(sum(value * value for value in left))
    right_length = math.sqrt(sum(value * value for value in right))
    if left_length <= 0 or right_length <= 0:
        return 0.0
    return _dot(left, right) / (left_length * right_length)


def _embedding_cache_key(
    *,
    provider: str,
    model: str,
    input_hash: str,
) -> str:
    digest = hashlib.sha256(
        f"{provider}\n{model}\n{input_hash}".encode("utf-8")
    ).hexdigest()
    return f"embedding:{digest}"


def _coerce_vector(value: Any) -> list[float] | None:
    if not isinstance(value, list):
        return None
    vector: list[float] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        vector.append(float(item))
    return vector


def _rerank_status(settings: Any | None) -> dict[str, Any]:
    return {
        "enabled": bool(getattr(settings, "retrieval_shadow_rerank_enabled", False)),
        "model": str(
            getattr(
                settings,
                "retrieval_shadow_rerank_model",
                "nvidia/llama-nemotron-rerank-vl-1b-v2:free",
            )
            or "nvidia/llama-nemotron-rerank-vl-1b-v2:free"
        ),
    }


def _openrouter_error_payload(
    exc: OpenRouterRetrievalError,
    *,
    status: str,
    stage: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": status,
        "error_code": f"retrieval_shadow.{exc.code}",
        "error_message": exc.message,
        "error_stage": stage,
        "status_code": exc.status_code,
        "error_payload": exc.payload,
    }


def _rerank_document(surface: MemorySurface) -> str:
    return "\n".join(
        [
            f"surface_kind: {surface.surface_kind}",
            f"target_type: {surface.target_type}",
            f"target_id: {surface.target_id}",
            f"content: {surface.content}",
        ]
    )


def _rerank_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = response.get("results")
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _flatten_milvus_hits(raw_results: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_results, list):
        return []
    hits = (
        raw_results[0]
        if raw_results and isinstance(raw_results[0], list)
        else raw_results
    )
    return [hit for hit in hits if isinstance(hit, dict)]


def _milvus_score(hit: dict[str, Any]) -> float:
    for key in ("distance", "score"):
        value = hit.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0

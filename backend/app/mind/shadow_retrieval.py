from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any, Iterable

from sqlmodel import Session

from app.storage import repositories
from app.storage.models import MemorySurface


SHADOW_RANKING_POLICY = "trace_only_no_active_ranking"
SUPPORTED_BACKENDS = {"none", "local", "milvus_lite"}
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

    surfaces = repositories.list_memory_surfaces_by_targets(
        db,
        target_type="memory",
        target_ids=target_ids,
        surface_kind="memory_text",
        status="active",
        limit=max(requested_limit * 8, len(target_ids), 1),
    )
    payload["candidate_surface_count"] = len(surfaces)
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
    return {
        "ok": True,
        "status": "completed",
        "results": [
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
            for score, surface in scored[:limit]
        ],
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


def _surface_result_payload(
    surface: MemorySurface,
    *,
    score: float,
    backend: str,
    embedding_model: str,
    why_relevant: str,
) -> dict[str, Any]:
    return {
        "surface_id": surface.id,
        "target_type": surface.target_type,
        "target_id": surface.target_id,
        "surface_kind": surface.surface_kind,
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
    return int(getattr(settings, "retrieval_shadow_vector_dim", 128) or 128)


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


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

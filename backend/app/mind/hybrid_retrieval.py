from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.storage.models import MemoryRecord


HYBRID_RANKING_POLICY = "sparse_dense_memory_group_hybrid_v1"
VALID_HYBRID_MODES = {"off", "shadow", "active"}


@dataclass(frozen=True)
class HybridBaseScore:
    score: float = 0.0
    reason: str = ""
    sparse_score: float = 0.0
    strong_signal: bool = False


@dataclass(frozen=True)
class HybridRankEntry:
    memory: MemoryRecord
    memory_id: str
    memory_salience: float
    memory_created_at: Any
    score: float
    why_relevant: str
    strong_signal: bool
    signals: dict[str, Any]


@dataclass(frozen=True)
class HybridRankPlan:
    status: dict[str, Any]
    entries: list[HybridRankEntry]

    @property
    def active(self) -> bool:
        return self.status.get("mode") == "active" and self.status.get("ok") is True


def retrieval_hybrid_status(settings: Any | None) -> dict[str, Any]:
    mode = str(getattr(settings, "retrieval_hybrid_mode", "off") or "off").lower()
    if mode not in VALID_HYBRID_MODES:
        return {
            "enabled": False,
            "ok": False,
            "mode": mode,
            "ranking_policy": HYBRID_RANKING_POLICY,
            "error_code": "retrieval_hybrid.unsupported_mode",
            "error_message": (
                "retrieval_hybrid_mode must be one of "
                f"{sorted(VALID_HYBRID_MODES)}."
            ),
        }
    return {
        "enabled": mode != "off",
        "ok": mode != "off",
        "mode": mode,
        "ranking_policy": HYBRID_RANKING_POLICY,
        "thresholds": {
            "min_dense_score": _setting_float(
                settings,
                "retrieval_hybrid_min_dense_score",
                0.38,
            ),
            "min_rerank_score": _setting_float(
                settings,
                "retrieval_hybrid_min_rerank_score",
                0.55,
            ),
        },
        "weights": {
            "base": _setting_float(settings, "retrieval_hybrid_base_weight", 0.35),
            "sparse": _setting_float(settings, "retrieval_hybrid_sparse_weight", 0.15),
            "dense": _setting_float(settings, "retrieval_hybrid_dense_weight", 0.35),
            "rerank": _setting_float(settings, "retrieval_hybrid_rerank_weight", 0.20),
            "support": _setting_float(settings, "retrieval_hybrid_support_weight", 0.05),
            "salience": 0.0,
            "confidence": 0.0,
        },
        "deprecated_weights": {
            "salience": _setting_float(
                settings,
                "retrieval_hybrid_salience_weight",
                0.0,
            ),
            "confidence": _setting_float(
                settings,
                "retrieval_hybrid_confidence_weight",
                0.0,
            ),
            "policy": (
                "Stored memory confidence/salience are retained for legacy "
                "audit only and do not affect active hybrid ranking."
            ),
        },
    }


def rank_hybrid_memories(
    memories: list[MemoryRecord],
    *,
    base_scores: dict[str, HybridBaseScore],
    retrieval_shadow: dict[str, Any] | None,
    settings: Any | None,
    limit: int | None = None,
) -> HybridRankPlan:
    status = retrieval_hybrid_status(settings)
    if not status.get("enabled"):
        return HybridRankPlan(
            status={
                **status,
                "ok": False,
                "status": "disabled",
                "active": False,
                "entry_count": 0,
            },
            entries=[],
        )
    if status.get("ok") is not True:
        return HybridRankPlan(
            status={**status, "status": "configuration_error", "active": False},
            entries=[],
        )

    dense_by_memory = _grouped_results_by_memory(
        (retrieval_shadow or {}).get("grouped_results")
    )
    rerank_by_memory = _grouped_results_by_memory(
        ((retrieval_shadow or {}).get("rerank") or {}).get("grouped_results")
    )
    if not dense_by_memory and not rerank_by_memory:
        return HybridRankPlan(
            status={
                **status,
                "status": "no_grouped_dense_evidence",
                "active": False,
                "entry_count": 0,
            },
            entries=[],
        )

    max_base = max((item.score for item in base_scores.values()), default=0.0)
    max_sparse = max((item.sparse_score for item in base_scores.values()), default=0.0)
    thresholds = status["thresholds"]
    weights = status["weights"]
    entries: list[HybridRankEntry] = []

    for memory in memories:
        base = base_scores.get(memory.id, HybridBaseScore())
        dense = dense_by_memory.get(memory.id)
        rerank = rerank_by_memory.get(memory.id)
        dense_score = _promotable_score(dense)
        dense_support_score = _support_score(dense)
        rerank_score = _rerank_score(rerank)
        rerank_support_score = _support_score(rerank)
        support_score = max(dense_support_score, rerank_support_score)
        dense_signal = dense_score >= thresholds["min_dense_score"]
        rerank_signal = rerank_score >= thresholds["min_rerank_score"]
        base_signal = base.strong_signal and base.score > 0

        if not base_signal and not dense_signal and not rerank_signal:
            continue

        base_norm = _normalize(base.score, max_base)
        sparse_norm = _normalize(base.sparse_score, max_sparse)
        if not base.strong_signal:
            base_norm = min(base_norm, 0.25)
            sparse_norm = 0.0
        support_norm = max(support_score, 0.0)
        hybrid_score = (
            (weights["base"] * base_norm)
            + (weights["sparse"] * sparse_norm)
            + (weights["dense"] * max(dense_score, 0.0))
            + (weights["rerank"] * max(rerank_score, 0.0))
            + (weights["support"] * support_norm)
        )
        reasons = _hybrid_reasons(
            base=base,
            dense=dense,
            rerank=rerank,
            dense_signal=dense_signal,
            rerank_signal=rerank_signal,
        )
        signals = {
            "ranking_policy": HYBRID_RANKING_POLICY,
            "mode": status["mode"],
            "base_score": round(base.score, 6),
            "base_score_normalized": round(base_norm, 6),
            "sparse_score": round(base.sparse_score, 6),
            "sparse_score_normalized": round(sparse_norm, 6),
            "dense_score": round(dense_score, 6),
            "rerank_score": round(rerank_score, 6),
            "support_score": round(support_score, 6),
            "dense_signal": dense_signal,
            "rerank_signal": rerank_signal,
            "base_signal": base_signal,
            "hybrid_strong_signal": rerank_signal or dense_signal,
            "surface_kinds": _surface_kinds(dense),
            "surface_roles": _surface_roles(dense),
            "promotable_surface_kinds": _promotable_surface_kinds(dense),
            "support_surface_kinds": _support_surface_kinds(dense),
            "top_surface_id": _top_surface_id(dense),
            "top_surface_kind": _top_surface_kind(dense),
            "top_surface_role": _top_surface_role(dense),
            "active_rank_eligible": _active_rank_eligible(dense),
            "thresholds": thresholds,
            "weights": weights,
        }
        entries.append(
            HybridRankEntry(
                memory=memory,
                memory_id=memory.id,
                memory_salience=memory.salience,
                memory_created_at=memory.created_at,
                score=hybrid_score,
                why_relevant="; ".join(reasons),
                strong_signal=base.strong_signal or rerank_signal or dense_signal,
                signals=signals,
            )
        )

    entries.sort(
        key=lambda item: (
            item.score,
            item.signals["rerank_score"],
            item.signals["dense_score"],
            item.memory_created_at,
        ),
        reverse=True,
    )
    if limit is not None:
        entries = entries[:limit]
    return HybridRankPlan(
        status={
            **status,
            "status": "completed",
            "active": status["mode"] == "active",
            "entry_count": len(entries),
            "dense_group_count": len(dense_by_memory),
            "rerank_group_count": len(rerank_by_memory),
            "uses_rerank": bool(rerank_by_memory),
        },
        entries=entries,
    )


def hybrid_rank_status_payload(plan: HybridRankPlan) -> dict[str, Any]:
    return {
        **plan.status,
        "entries": [
            {
                "memory_id": entry.memory_id,
                "score": round(entry.score, 6),
                "strong_signal": entry.strong_signal,
                "why_relevant": entry.why_relevant,
                "signals": entry.signals,
            }
            for entry in plan.entries
        ],
    }


def _grouped_results_by_memory(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        return {}
    results: dict[str, dict[str, Any]] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        target_id = item.get("target_id")
        if not isinstance(target_id, str) or not target_id:
            continue
        existing = results.get(target_id)
        if existing is None or _promotable_score(item) > _promotable_score(existing):
            results[target_id] = item
    return results


def _hybrid_reasons(
    *,
    base: HybridBaseScore,
    dense: dict[str, Any] | None,
    rerank: dict[str, Any] | None,
    dense_signal: bool,
    rerank_signal: bool,
) -> list[str]:
    reasons: list[str] = []
    if base.reason:
        reasons.append(base.reason)
    if dense is not None:
        surface = dense.get("top_surface_kind") or dense.get("surface_kind")
        reasons.append(
            "dense memory-level match"
            f" score={_promotable_score(dense):.3f}"
            f" support={_support_score(dense):.3f}"
            f" surface={surface}"
            f" signal={str(dense_signal).lower()}"
        )
    if rerank is not None:
        reasons.append(
            "rerank memory-level match"
            f" score={_rerank_score(rerank):.3f}"
            f" signal={str(rerank_signal).lower()}"
        )
    return reasons or ["hybrid memory candidate"]


def _promotable_score(value: dict[str, Any] | None) -> float:
    if not isinstance(value, dict):
        return 0.0
    if value.get("active_rank_eligible") is False:
        return 0.0
    raw = value.get("promotable_score", value.get("score"))
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def _score(value: dict[str, Any] | None) -> float:
    if not isinstance(value, dict):
        return 0.0
    raw = value.get("score")
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def _rerank_score(value: dict[str, Any] | None) -> float:
    if not isinstance(value, dict):
        return 0.0
    raw = value.get("rerank_score", value.get("score"))
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def _support_score(value: dict[str, Any] | None) -> float:
    if not isinstance(value, dict):
        return 0.0
    raw = value.get("support_score")
    return float(raw) if isinstance(raw, (int, float)) else 0.0


def _surface_kinds(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    kinds = value.get("surface_kinds")
    if isinstance(kinds, list):
        return [str(item) for item in kinds if isinstance(item, str)]
    kind = value.get("surface_kind")
    return [kind] if isinstance(kind, str) else []


def _top_surface_id(value: dict[str, Any] | None) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("top_surface_id") or value.get("surface_id")
    return raw if isinstance(raw, str) else None


def _surface_roles(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    roles = value.get("surface_roles")
    if isinstance(roles, list):
        return [str(item) for item in roles if isinstance(item, str)]
    role = value.get("surface_role")
    return [role] if isinstance(role, str) else []


def _promotable_surface_kinds(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    kinds = value.get("promotable_surface_kinds")
    if isinstance(kinds, list):
        return [str(item) for item in kinds if isinstance(item, str)]
    return []


def _support_surface_kinds(value: dict[str, Any] | None) -> list[str]:
    if not isinstance(value, dict):
        return []
    kinds = value.get("support_surface_kinds")
    if isinstance(kinds, list):
        return [str(item) for item in kinds if isinstance(item, str)]
    return []


def _top_surface_kind(value: dict[str, Any] | None) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("top_surface_kind") or value.get("surface_kind")
    return raw if isinstance(raw, str) else None


def _top_surface_role(value: dict[str, Any] | None) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("top_surface_role") or value.get("surface_role")
    return raw if isinstance(raw, str) else None


def _active_rank_eligible(value: dict[str, Any] | None) -> bool:
    if not isinstance(value, dict):
        return False
    return value.get("active_rank_eligible") is not False


def _normalize(score: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(min(score / maximum, 1.0), 0.0)


def _setting_float(settings: Any | None, key: str, default: float) -> float:
    value = getattr(settings, key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

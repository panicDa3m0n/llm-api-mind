"""Automatic semantic-memory retrieval for Scarlet's turn context."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import Session

from app.mind.facts import fact_payload, fact_search_text
from app.mind.memory_recall import (
    collect_memory_recall_evidence,
    run_memory_recall_pipeline,
)
from app.mind.relevance_rerank import (
    FINAL_RERANK_POLICY,
    MemoryRerankEntry,
    MemoryRerankPlan,
    rerank_status_payload,
)
from app.mind.search import (
    entity_token_groups,
    query_tokens,
    retrieval_stage_manifest,
)
from app.storage import repositories
from app.storage.models import MemoryFact, MemoryRecord


INTERNAL_CANDIDATE_LIMIT = 20
MODEL_SELECTED_LIMIT = 5
NEAR_MISS_MIN_SCORE = 1.5


@dataclass(frozen=True)
class MemoryCandidateScore:
    memory: MemoryRecord
    score: float
    why_relevant: str
    sparse_score: float
    current_overlap: list[str]
    context_overlap: list[str]
    generic_overlap: list[str]
    tag_overlap: list[str]
    strong_signal: bool
    graph_score: float = 0.0
    graph_signal: dict[str, Any] | None = None
    hybrid_score: float | None = None
    hybrid_signals: dict[str, Any] | None = None


@dataclass(frozen=True)
class AutomaticMemoryRetrieval:
    lexical_queries: list[str]
    sparse_query: str
    retrieval_stages: list[str]
    retrieval_graph: dict[str, Any]
    retrieval_shadow: dict[str, Any]
    retrieval_rerank: dict[str, Any]
    selected: list[dict[str, Any]]
    near_miss: list[dict[str, Any]]
    excluded: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    negative_evidence: str
    candidate_count: int
    ranked_candidate_count: int
    activity_memory_ids: list[str]

    def query_plan(self) -> dict[str, Any]:
        return {
            "lexical_queries": self.lexical_queries,
            "semantic_queries": [],
            "sparse_query": _truncate(self.sparse_query, 1500),
            "retrieval_stages": self.retrieval_stages,
            "retrieval_readiness": retrieval_stage_manifest(),
            "retrieval_graph": self.retrieval_graph,
            "retrieval_shadow": self.retrieval_shadow,
            "retrieval_rerank": self.retrieval_rerank,
            # Compatibility key for evaluator clients written before V1.31.0.
            "retrieval_hybrid": self.retrieval_rerank,
        }

    def budget(self) -> dict[str, int]:
        return {
            "internal_candidates": INTERNAL_CANDIDATE_LIMIT,
            "model_selected": MODEL_SELECTED_LIMIT,
        }


def build_automatic_memory_retrieval(
    db: Session,
    *,
    current_user_message: str,
    recent_dialogue: list[dict[str, Any]],
    settings: Any | None = None,
) -> AutomaticMemoryRetrieval:
    """Build one complete automatic-memory selection without runtime assembly."""

    lexical_queries = _lexical_queries(
        current_user_message=current_user_message,
        recent_dialogue=recent_dialogue,
    )
    candidates = repositories.list_memories(
        db,
        scope=None,
        include_low_confidence=False,
    )
    # Legacy heuristic facts remain auditable through ``memory facts`` but do
    # not participate in automatic recall, ranking, or conflict claims.
    facts_by_memory: dict[str, list[MemoryFact]] = {}
    # This query already contains the current message plus recent context.
    # Joining every diagnostic variant would duplicate the current message.
    sparse_query = lexical_queries[-1]
    evidence = collect_memory_recall_evidence(
        db,
        query=sparse_query,
        memories=candidates,
        facts_by_memory=facts_by_memory,
        settings=settings,
        sparse_limit=INTERNAL_CANDIDATE_LIMIT * 4,
        graph_limit=INTERNAL_CANDIDATE_LIMIT,
    )
    ranked_base = _rank_candidates(
        candidates,
        current_user_message=current_user_message,
        recent_dialogue=recent_dialogue,
        facts_by_memory=facts_by_memory,
        sparse_matches=evidence.sparse_matches,
        graph_signals=evidence.graph_signals,
    )
    pipeline = run_memory_recall_pipeline(
        evidence,
        lexical_memory_ids=[item.memory.id for item in ranked_base],
        settings=settings,
        selected_limit=MODEL_SELECTED_LIMIT,
        off_mode_stage="lexical_guard_v1",
    )
    rerank_plan = pipeline.rerank_plan
    retrieval_stages = pipeline.retrieval_stages
    if rerank_plan.active:
        ranked = _context_candidates_from_final_rerank(
            rerank_plan.entries,
            base_ranked=ranked_base,
        )
    else:
        ranked = ranked_base[:INTERNAL_CANDIDATE_LIMIT]
    selected_ranked, near_miss_ranked, excluded_ranked = _classify_candidates(ranked)

    near_miss = [
        _candidate_payload(item, classification="near_miss")
        | {
            "facts": [
                fact_payload(fact) for fact in facts_by_memory.get(item.memory.id, [])
            ]
        }
        for item in near_miss_ranked
    ]
    excluded = [
        _candidate_payload(item, classification="excluded")
        | {
            "facts": [
                fact_payload(fact) for fact in facts_by_memory.get(item.memory.id, [])
            ]
        }
        for item in excluded_ranked
    ]
    selected = [
        _candidate_payload(
            item,
            memory=item.memory,
            classification="selected",
            facts=facts_by_memory.get(item.memory.id, []),
        )
        for item in selected_ranked[:MODEL_SELECTED_LIMIT]
    ]
    rerank_payload = rerank_status_payload(rerank_plan)

    return AutomaticMemoryRetrieval(
        lexical_queries=lexical_queries,
        sparse_query=sparse_query,
        retrieval_stages=retrieval_stages,
        retrieval_graph=evidence.graph_expansion,
        retrieval_shadow=evidence.retrieval_shadow,
        retrieval_rerank=rerank_payload,
        selected=selected,
        near_miss=near_miss,
        excluded=excluded,
        conflicts=[],
        negative_evidence=_memory_negative_evidence(
            selected=selected,
            rerank_plan=rerank_plan,
        ),
        candidate_count=len(candidates),
        ranked_candidate_count=len(ranked),
        activity_memory_ids=[
            item.memory.id
            for item in selected_ranked[:MODEL_SELECTED_LIMIT]
            if (item.hybrid_signals or {}).get("rerank_signal")
        ],
    )


def candidate_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item["id"],
        "type": item["type"],
        "scope": item["scope"],
        "score": item["score"],
        "classification": item["classification"],
        "why_relevant": item["why_relevant"],
    }


def _lexical_queries(
    *,
    current_user_message: str,
    recent_dialogue: list[dict[str, Any]],
) -> list[str]:
    queries = [current_user_message]
    recent_context = " ".join(
        str(item["content"])
        for item in recent_dialogue[-4:]
        if item["content"] != current_user_message
    )
    if recent_context:
        queries.append(f"{current_user_message} {recent_context}")
    return [_truncate(query, 1500) for query in queries]


def _rank_candidates(
    memories: list[MemoryRecord],
    *,
    current_user_message: str,
    recent_dialogue: list[dict[str, Any]],
    facts_by_memory: dict[str, list[MemoryFact]],
    sparse_matches: dict[str, Any] | None = None,
    graph_signals: dict[str, Any] | None = None,
) -> list[MemoryCandidateScore]:
    current_text = _normalize_text(current_user_message)
    current_tokens = set(_tokens(current_user_message))
    entity_groups = entity_token_groups(current_user_message)
    entity_tokens = set().union(*entity_groups) if entity_groups else set()
    low_signal_tokens = _low_signal_query_tokens(
        memories,
        facts_by_memory=facts_by_memory,
        query_tokens=current_tokens,
    )
    signal_tokens = (current_tokens - low_signal_tokens) | entity_tokens
    context_text = " ".join(
        str(item["content"])
        for item in recent_dialogue
        if item["content"] != current_user_message
    )
    context_tokens = set(_tokens(context_text))
    scores: list[MemoryCandidateScore] = []
    sparse_matches = sparse_matches or {}
    graph_signals = graph_signals or {}

    for memory in memories:
        haystack = _memory_search_text(memory, facts=facts_by_memory.get(memory.id, []))
        haystack_tokens = set(_tokens(haystack))
        current_overlap = sorted(signal_tokens & haystack_tokens)
        context_overlap = sorted(
            (context_tokens & haystack_tokens)
            - set(current_overlap)
            - low_signal_tokens
        )
        generic_overlap = sorted(
            (current_tokens & haystack_tokens) - set(current_overlap)
        )
        entity_supported = _supports_entity_group(
            haystack_tokens,
            memory.tags_json,
            entity_groups=entity_groups,
        )
        tag_overlap = sorted(
            tag
            for tag in set(memory.tags_json)
            if _tag_matches(tag, current_text)
            and _tag_has_signal(
                tag,
                signal_tokens=signal_tokens,
                entity_groups=entity_groups,
            )
        )

        score = 0.0
        reasons: list[str] = []
        sparse_match = sparse_matches.get(memory.id)
        sparse_score = sparse_match.score if sparse_match is not None else 0.0
        graph_signal = graph_signals.get(memory.id)
        graph_score = float(getattr(graph_signal, "score", 0.0) or 0.0)
        if sparse_match is not None:
            score += sparse_score * 2.0
            reasons.append(sparse_match.why_relevant)
        if graph_signal is not None and graph_score > 0:
            score += graph_score
            reasons.append(getattr(graph_signal, "why_relevant", "graph expansion"))
        if entity_supported:
            score += 3.0
            reasons.append("query entity support")
        if current_overlap:
            score += len(current_overlap) * 2.0
            reasons.append(f"current token overlap: {', '.join(current_overlap)}")
        if tag_overlap:
            score += len(tag_overlap) * 2.5
            reasons.append(f"tag match: {', '.join(tag_overlap)}")
        if context_overlap:
            score += len(context_overlap) * 0.4
            reasons.append(f"recent dialogue overlap: {', '.join(context_overlap[:6])}")
        if generic_overlap:
            score += len(generic_overlap) * 0.2
            reasons.append(f"generic overlap: {', '.join(generic_overlap)}")

        if score <= 0:
            continue
        if entity_groups:
            strong_signal = entity_supported
        else:
            strong_signal = (
                len(current_overlap) >= 2
                or bool(tag_overlap)
                or graph_score >= 2.0
                or (len(signal_tokens) <= 2 and bool(current_overlap))
            )
        scores.append(
            MemoryCandidateScore(
                memory=memory,
                score=score,
                why_relevant="; ".join(reasons),
                sparse_score=sparse_score,
                current_overlap=current_overlap,
                context_overlap=context_overlap,
                generic_overlap=generic_overlap,
                tag_overlap=tag_overlap,
                strong_signal=strong_signal,
                graph_score=graph_score,
                graph_signal=(
                    {
                        "score": round(graph_score, 6),
                        "why_relevant": getattr(graph_signal, "why_relevant", ""),
                        "domains": getattr(graph_signal, "domains", []),
                        "paths": getattr(graph_signal, "paths", [])[:5],
                    }
                    if graph_signal is not None
                    else None
                ),
            )
        )

    return sorted(
        scores,
        key=lambda item: (item.score, item.memory.created_at),
        reverse=True,
    )


def _classify_candidates(
    ranked: list[MemoryCandidateScore],
) -> tuple[
    list[MemoryCandidateScore],
    list[MemoryCandidateScore],
    list[MemoryCandidateScore],
]:
    selected: list[MemoryCandidateScore] = []
    near_miss: list[MemoryCandidateScore] = []
    excluded: list[MemoryCandidateScore] = []
    has_user_associative_context = any(
        item.memory.scope == "user" and item.graph_score >= 2.0 for item in ranked
    )

    for item in ranked:
        final_signals = item.hybrid_signals or {}
        if final_signals.get("final_arbiter") is True:
            if final_signals.get("rerank_signal") is True:
                selected.append(item)
            elif final_signals.get("rerank_evaluated") is True:
                near_miss.append(item)
            else:
                excluded.append(item)
            continue
        if (
            has_user_associative_context
            and item.graph_score <= 0
            and not _has_confirmed_hybrid_signal(item)
            and (item.memory.scope == "project" or item.score < 0.3)
        ):
            if item.score >= NEAR_MISS_MIN_SCORE:
                near_miss.append(item)
            else:
                excluded.append(item)
            continue
        if item.strong_signal:
            selected.append(item)
        elif item.score >= NEAR_MISS_MIN_SCORE:
            near_miss.append(item)
        else:
            excluded.append(item)
    return selected, near_miss, excluded


def _has_confirmed_hybrid_signal(item: MemoryCandidateScore) -> bool:
    signals = item.hybrid_signals or {}
    return bool(signals.get("dense_signal") or signals.get("rerank_signal"))


def _context_candidates_from_final_rerank(
    entries: list[MemoryRerankEntry],
    *,
    base_ranked: list[MemoryCandidateScore],
) -> list[MemoryCandidateScore]:
    base_by_id = {item.memory.id: item for item in base_ranked}
    candidates: list[MemoryCandidateScore] = []
    for entry in entries:
        base = base_by_id.get(entry.memory_id)
        signals = {
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
        reason = (
            "Final memory-level reranker accepted this candidate."
            if entry.accepted
            else "Final memory-level reranker did not accept this candidate."
        )
        if base is not None:
            candidates.append(
                MemoryCandidateScore(
                    memory=entry.memory,
                    score=entry.score,
                    why_relevant=reason,
                    sparse_score=base.sparse_score,
                    current_overlap=base.current_overlap,
                    context_overlap=base.context_overlap,
                    generic_overlap=base.generic_overlap,
                    tag_overlap=base.tag_overlap,
                    graph_score=base.graph_score,
                    graph_signal=base.graph_signal,
                    strong_signal=entry.accepted,
                    hybrid_score=entry.score,
                    hybrid_signals=signals,
                )
            )
            continue
        candidates.append(
            MemoryCandidateScore(
                memory=entry.memory,
                score=entry.score,
                why_relevant=reason,
                sparse_score=0.0,
                current_overlap=[],
                context_overlap=[],
                generic_overlap=[],
                tag_overlap=[],
                graph_score=0.0,
                graph_signal=None,
                strong_signal=entry.accepted,
                hybrid_score=entry.score,
                hybrid_signals=signals,
            )
        )
    return candidates


def _memory_negative_evidence(
    *,
    selected: list[dict[str, Any]],
    rerank_plan: MemoryRerankPlan,
) -> str:
    if selected:
        return "none"
    if rerank_plan.active and not rerank_plan.completed:
        return "final_rerank_unavailable"
    return "no_relevant_memory_selected"


def _candidate_payload(
    item: MemoryCandidateScore,
    *,
    classification: str,
    memory: MemoryRecord | None = None,
    facts: list[MemoryFact] | None = None,
) -> dict[str, Any]:
    record = memory or item.memory
    payload = {
        "id": record.id,
        "type": record.memory_type,
        "scope": record.scope,
        "status": record.status,
        "content": record.content,
        "reason_for_storage": record.reason_for_storage,
        "expected_future_use": record.expected_future_use,
        "source_session_id": record.source_session_id,
        "source_turn_id": record.source_turn_id,
        "source_message_id": record.source_message_id,
        "tags": record.tags_json,
        "metadata": record.metadata_json,
        "usage_count": record.usage_count,
        "created_at": _isoformat(record.created_at),
        "updated_at": _isoformat(record.updated_at),
        "last_used_at": _isoformat(record.last_used_at),
        "score": round(item.score, 4),
        "classification": classification,
        "why_relevant": item.why_relevant,
        "signals": {
            "sparse_score": round(item.sparse_score, 4),
            "graph_score": round(item.graph_score, 4),
            "current_overlap": item.current_overlap,
            "context_overlap": item.context_overlap,
            "generic_overlap": item.generic_overlap,
            "tag_overlap": item.tag_overlap,
            "strong_signal": item.strong_signal,
        },
    }
    if item.graph_signal is not None:
        payload["signals"]["graph"] = item.graph_signal
    if item.hybrid_signals is not None:
        payload["signals"]["hybrid"] = item.hybrid_signals
        payload["hybrid_score"] = round(item.hybrid_score or item.score, 4)
    if facts is not None:
        payload["facts"] = [fact_payload(fact) for fact in facts]
    return payload


def _memory_search_text(
    memory: MemoryRecord,
    *,
    facts: list[MemoryFact] | None = None,
) -> str:
    return " ".join(
        item
        for item in [
            memory.content,
            memory.memory_type,
            memory.scope,
            " ".join(memory.tags_json),
            fact_search_text(facts or []),
        ]
        if item
    )


def _low_signal_query_tokens(
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]],
    query_tokens: set[str],
) -> set[str]:
    if not memories or not query_tokens:
        return set()
    document_frequency = {token: 0 for token in query_tokens}
    for memory in memories:
        tokens = set(
            _tokens(
                _memory_search_text(
                    memory,
                    facts=facts_by_memory.get(memory.id, []),
                )
            )
        )
        for token in query_tokens:
            if token in tokens:
                document_frequency[token] += 1
    threshold = max(3, int(len(memories) * 0.35))
    return {token for token, count in document_frequency.items() if count >= threshold}


def _supports_entity_group(
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


def _tag_has_signal(
    tag: str,
    *,
    signal_tokens: set[str],
    entity_groups: list[set[str]],
) -> bool:
    tag_tokens = set(query_tokens(tag.replace("-", " ").replace("_", " ")))
    if not tag_tokens:
        return False
    if tag_tokens & signal_tokens:
        return True
    return any(group <= tag_tokens for group in entity_groups)


def _tag_matches(tag: str, current_text: str) -> bool:
    normalized_tag = _normalize_text(tag)
    if normalized_tag in current_text:
        return True
    return normalized_tag.replace("-", " ") in current_text


def _tokens(value: str) -> list[str]:
    return re.findall(r"\w+", value.casefold())


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()

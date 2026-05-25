from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import text
from sqlmodel import Session

from app.mind.facts import fact_search_text
from app.storage import repositories
from app.storage.models import ChatSession, MemoryFact, MemoryRecord


@dataclass(frozen=True)
class SparseSearchResult:
    source_id: str
    doc_id: str
    kind: str
    score: float
    raw_rank: float
    why_relevant: str


def sync_memory_documents(
    db: Session,
    memories: Iterable[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
) -> None:
    facts_by_memory = facts_by_memory or {}
    for memory in memories:
        facts = facts_by_memory.get(memory.id)
        if facts is None:
            facts = repositories.list_memory_facts(db, memory_id=memory.id)
        _replace_document(
            db,
            doc_id=f"memory:{memory.id}",
            kind="memory",
            source_id=memory.id,
            title=_truncate(memory.content, 240),
            body=_memory_body(memory, facts=facts),
            tags_text=" ".join(memory.tags_json),
            entities_text=" ".join(sorted({fact.entity for fact in facts})),
            predicates_text=" ".join(sorted({fact.predicate for fact in facts})),
            scope=memory.scope,
            status=memory.status,
            source_session_id=memory.source_session_id,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
            metadata={
                "memory_type": memory.memory_type,
                "confidence": memory.confidence,
                "salience": memory.salience,
            },
        )
    db.commit()


def sync_session_documents(db: Session, sessions: Iterable[ChatSession]) -> None:
    for chat_session in sessions:
        summary = repositories.get_session_summary(db, session_id=chat_session.id)
        messages = repositories.list_messages(db, session_id=chat_session.id)
        memories = repositories.list_memories_for_session(
            db,
            session_id=chat_session.id,
        )
        topics = summary.topics_json if summary is not None else []
        decisions = summary.decisions_json if summary is not None else []
        open_questions = summary.open_questions_json if summary is not None else []
        summary_text = summary.summary if summary is not None else ""
        transcript_text = _truncate(
            "\n".join(
                f"{message.role}: {message.content}"
                for message in messages
                if message.role in {"user", "assistant"}
            ),
            24000,
        )
        _replace_document(
            db,
            doc_id=f"session:{chat_session.id}",
            kind="session",
            source_id=chat_session.id,
            title=chat_session.title or "Untitled session",
            body="\n".join(
                item
                for item in [
                    summary_text,
                    " ".join(topics),
                    " ".join(decisions),
                    " ".join(open_questions),
                    transcript_text,
                ]
                if item
            ),
            tags_text=" ".join(topics),
            entities_text=" ".join(memory.id for memory in memories),
            predicates_text=" ".join(decisions),
            scope="session",
            status=summary.status if summary is not None else "fallback",
            source_session_id=chat_session.id,
            created_at=chat_session.created_at,
            updated_at=chat_session.updated_at,
            metadata={
                "summary_id": summary.id if summary is not None else None,
                "summary_version": summary.summary_version if summary is not None else None,
                "message_count": len(messages),
                "memory_count": len(memories),
            },
        )
    db.commit()


def search_documents(
    db: Session,
    *,
    query: str,
    kind: str,
    limit: int = 50,
) -> list[SparseSearchResult]:
    match_query = _fts_match_query(db, query=query, kind=kind)
    if match_query is None:
        return []
    try:
        rows = db.execute(
            text(
                """
                SELECT
                  doc_id,
                  kind,
                  source_id,
                  bm25(search_documents_fts, 5.0, 2.5, 1.2, 1.5, 1.5) AS rank
                FROM search_documents_fts
                WHERE search_documents_fts MATCH :match_query
                  AND kind = :kind
                ORDER BY rank
                LIMIT :limit
                """
            ),
            {"match_query": match_query, "kind": kind, "limit": limit},
        ).mappings()
    except Exception:
        return []

    results: list[SparseSearchResult] = []
    for row in rows:
        raw_rank = float(row["rank"])
        score = _bm25_to_score(raw_rank)
        results.append(
            SparseSearchResult(
                source_id=str(row["source_id"]),
                doc_id=str(row["doc_id"]),
                kind=str(row["kind"]),
                score=score,
                raw_rank=raw_rank,
                why_relevant=f"FTS5/BM25 sparse match ({match_query})",
            )
        )
    return results


def sparse_results_by_source(
    results: Iterable[SparseSearchResult],
) -> dict[str, SparseSearchResult]:
    grouped: dict[str, SparseSearchResult] = {}
    for result in results:
        current = grouped.get(result.source_id)
        if current is None or result.score > current.score:
            grouped[result.source_id] = result
    return grouped


def _replace_document(
    db: Session,
    *,
    doc_id: str,
    kind: str,
    source_id: str,
    title: str,
    body: str,
    tags_text: str,
    entities_text: str,
    predicates_text: str,
    scope: str | None,
    status: str,
    source_session_id: str | None,
    created_at: datetime | None,
    updated_at: datetime | None,
    metadata: dict[str, Any],
) -> None:
    db.execute(
        text("DELETE FROM search_documents_fts WHERE doc_id = :doc_id"),
        {"doc_id": doc_id},
    )
    db.execute(
        text(
            """
            INSERT INTO search_documents_fts (
              doc_id, kind, source_id, title, body, tags_text, entities_text,
              predicates_text, scope, status, source_session_id, created_at,
              updated_at, metadata_json
            )
            VALUES (
              :doc_id, :kind, :source_id, :title, :body, :tags_text,
              :entities_text, :predicates_text, :scope, :status,
              :source_session_id, :created_at, :updated_at, :metadata_json
            )
            """
        ),
        {
            "doc_id": doc_id,
            "kind": kind,
            "source_id": source_id,
            "title": title,
            "body": body,
            "tags_text": tags_text,
            "entities_text": entities_text,
            "predicates_text": predicates_text,
            "scope": scope,
            "status": status,
            "source_session_id": source_session_id,
            "created_at": created_at.isoformat() if created_at is not None else None,
            "updated_at": updated_at.isoformat() if updated_at is not None else None,
            "metadata_json": json.dumps(metadata, ensure_ascii=True),
        },
    )


def _memory_body(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
    return "\n".join(
        item
        for item in [
            memory.content,
            memory.reason_for_storage,
            memory.expected_future_use or "",
            memory.memory_type,
            memory.scope,
            fact_search_text(facts),
        ]
        if item
    )


def query_tokens(query: str) -> list[str]:
    seen: set[str] = set()
    tokens: list[str] = []
    for token in re.findall(r"\w+", query.casefold()):
        if len(token) <= 1 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def entity_token_groups(query: str) -> list[set[str]]:
    groups: list[set[str]] = []
    for raw in re.findall(r"\b[\w]+(?:[-_][\w]+)+\b", query, flags=re.UNICODE):
        tokens = set(query_tokens(raw.replace("-", " ").replace("_", " ")))
        if len(tokens) >= 2:
            groups.append(tokens)
    for raw in re.findall(
        r"\b(?:[A-ZÀ-Ý][\wÀ-ÿ]+(?:\s+|[-_]))+[A-ZÀ-Ý][\wÀ-ÿ]+\b",
        query,
        flags=re.UNICODE,
    ):
        tokens = set(query_tokens(raw.replace("-", " ").replace("_", " ")))
        if len(tokens) >= 2:
            groups.append(tokens)
    for raw in re.findall(r'"([^"]{3,120})"', query):
        tokens = set(query_tokens(raw))
        if len(tokens) >= 1:
            groups.append(tokens)
    return _dedupe_groups(groups)


def _fts_match_query(db: Session, *, query: str, kind: str) -> str | None:
    groups = entity_token_groups(query)
    if groups:
        return " OR ".join(_and_terms(group) for group in groups[:4])

    tokens = query_tokens(query)
    if not tokens:
        return None
    document_counts = _document_counts(db, tokens=tokens, kind=kind)
    present_tokens = [token for token in tokens if document_counts.get(token, 0) > 0]
    if not present_tokens:
        return None
    present_tokens.sort(key=lambda token: (document_counts[token], -len(token), token))
    return _and_terms(present_tokens[: min(4, len(present_tokens))])


def _document_counts(
    db: Session,
    *,
    tokens: list[str],
    kind: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for token in tokens:
        try:
            count = db.execute(
                text(
                    """
                    SELECT count(*) AS count
                    FROM search_documents_fts
                    WHERE search_documents_fts MATCH :match_query
                      AND kind = :kind
                    """
                ),
                {"match_query": _quote_term(token), "kind": kind},
            ).scalar_one()
        except Exception:
            count = 0
        counts[token] = int(count or 0)
    return counts


def _and_terms(tokens: Iterable[str]) -> str:
    return " AND ".join(_quote_term(token) for token in sorted(set(tokens)))


def _quote_term(token: str) -> str:
    return f'"{token.replace(chr(34), chr(34) + chr(34))}"'


def _dedupe_groups(groups: list[set[str]]) -> list[set[str]]:
    deduped: list[set[str]] = []
    for group in groups:
        if any(group == existing for existing in deduped):
            continue
        deduped.append(group)
    return deduped


def _bm25_to_score(raw_rank: float) -> float:
    if raw_rank < 0:
        return min(4.0, abs(raw_rank) * 1000000)
    return 1.0 / (1.0 + raw_rank)


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."

from __future__ import annotations

import json
import re
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import text
from sqlmodel import Session

from app.mind.facts import fact_search_text
from app.storage import repositories
from app.storage.models import ChatSession, MemoryFact, MemoryGraphNode, MemoryRecord


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
    synced_memories = list(memories)
    for memory in synced_memories:
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
    _sync_memory_surfaces_and_graph(
        db,
        synced_memories,
        facts_by_memory=facts_by_memory,
    )
    db.commit()


def sync_session_documents(db: Session, sessions: Iterable[ChatSession]) -> None:
    synced_sessions = list(sessions)
    for chat_session in synced_sessions:
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
        _sync_session_surface_and_node(
            db,
            chat_session=chat_session,
            summary_text=summary_text,
            topics=topics,
            decisions=decisions,
            open_questions=open_questions,
            transcript_text=transcript_text,
            status=summary.status if summary is not None else "fallback",
        )
    db.commit()


def sync_memory_retrieval_artifacts(
    db: Session,
    memories: Iterable[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]] | None = None,
) -> None:
    """Synchronize all current derived retrieval artifacts for memories.

    This is the V1.3.0 readiness seam: FTS5 remains the active sparse retrieval
    path, while surfaces and graph rows are durable indexes that can later feed
    Milvus/Qdrant/GraphRAG-style retrieval without changing the source tables.
    """

    sync_memory_documents(db, memories, facts_by_memory=facts_by_memory)


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


def retrieval_stage_manifest() -> dict[str, Any]:
    return {
        "active_stages": ["fts5_sparse_v1", "lexical_fallback_v1"],
        "readiness_stages": [
            "memory_surfaces_v1",
            "memory_graph_v1",
            "embedding_index_shadow_ready_v1",
        ],
        "source_of_truth": [
            "memories",
            "memory_facts",
            "session_summaries",
            "messages",
        ],
        "derived_indexes": [
            "search_documents_fts",
            "memory_surfaces",
            "memory_graph_nodes",
            "memory_graph_edges",
        ],
        "notes": [
            "Surface and graph indexes are derived and can be rebuilt.",
            "No vector database is required for V1.3.0.",
            "Milvus/Qdrant adapters should consume memory_surfaces later.",
        ],
    }


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


def _sync_memory_surfaces_and_graph(
    db: Session,
    memories: list[MemoryRecord],
    *,
    facts_by_memory: dict[str, list[MemoryFact]],
) -> None:
    for memory in memories:
        facts = facts_by_memory.get(memory.id)
        if facts is None:
            facts = repositories.list_memory_facts(
                db,
                memory_id=memory.id,
                include_inactive=True,
            )
        memory_node = _upsert_memory_node(db, memory)
        _upsert_surface(
            db,
            target_type="memory",
            target_id=memory.id,
            surface_kind="memory_text",
            content=_memory_surface_text(memory, facts=facts),
            scope=memory.scope,
            status=memory.status,
            source_session_id=memory.source_session_id,
            source_turn_id=memory.source_turn_id,
            source_message_id=memory.source_message_id,
            metadata={
                "memory_type": memory.memory_type,
                "confidence": memory.confidence,
                "salience": memory.salience,
                "surface_origin": "memory_record",
            },
        )
        _upsert_surface(
            db,
            target_type="graph_node",
            target_id=memory_node.id,
            surface_kind="graph_node_profile",
            content=_node_surface_text(memory_node),
            scope=memory_node.scope,
            status=memory_node.status,
            source_session_id=memory_node.source_session_id,
            metadata={
                "node_key": memory_node.node_key,
                "node_type": memory_node.node_type,
                "surface_origin": "memory_graph_node",
            },
        )
        if memory.source_session_id:
            session_node = _upsert_session_node(
                db,
                session_id=memory.source_session_id,
                scope=memory.scope,
                status="active",
                source_memory_id=None,
            )
            _upsert_edge(
                db,
                source_node=memory_node,
                target_node=session_node,
                relation="evidenced_by_session",
                source_memory_id=memory.id,
                source_session_id=memory.source_session_id,
                confidence=memory.confidence,
                salience=memory.salience,
            )
        for fact in facts:
            fact_node = _upsert_fact_node(db, fact, memory=memory)
            entity_node = _upsert_entity_node(db, fact, memory=memory)
            _upsert_edge(
                db,
                source_node=memory_node,
                target_node=fact_node,
                relation="has_fact",
                source_memory_id=memory.id,
                source_fact_id=fact.id,
                source_session_id=memory.source_session_id,
                confidence=fact.confidence,
                salience=fact.salience,
            )
            _upsert_edge(
                db,
                source_node=fact_node,
                target_node=entity_node,
                relation="about_entity",
                source_memory_id=memory.id,
                source_fact_id=fact.id,
                source_session_id=memory.source_session_id,
                confidence=fact.confidence,
                salience=fact.salience,
            )
            _upsert_surface(
                db,
                target_type="fact",
                target_id=fact.id,
                surface_kind="fact_text",
                content=_fact_surface_text(fact, memory=memory),
                scope=memory.scope,
                status=fact.status,
                source_session_id=fact.source_session_id,
                source_turn_id=fact.source_turn_id,
                source_trace_id=fact.source_trace_id,
                metadata={
                    "memory_id": memory.id,
                    "entity": fact.entity,
                    "predicate": fact.predicate,
                    "confidence": fact.confidence,
                    "salience": fact.salience,
                    "surface_origin": "memory_fact",
                },
            )
            for node in (fact_node, entity_node):
                _upsert_surface(
                    db,
                    target_type="graph_node",
                    target_id=node.id,
                    surface_kind="graph_node_profile",
                    content=_node_surface_text(node),
                    scope=node.scope,
                    status=node.status,
                    source_session_id=node.source_session_id,
                    metadata={
                        "node_key": node.node_key,
                        "node_type": node.node_type,
                        "surface_origin": "memory_graph_node",
                    },
                )
            _sync_fact_lifecycle_edges(
                db,
                fact=fact,
                fact_node=fact_node,
                memory=memory,
            )
        _sync_memory_lifecycle_edges(db, memory=memory, memory_node=memory_node)


def _sync_session_surface_and_node(
    db: Session,
    *,
    chat_session: ChatSession,
    summary_text: str,
    topics: list[str],
    decisions: list[str],
    open_questions: list[str],
    transcript_text: str,
    status: str,
) -> None:
    session_node = _upsert_session_node(
        db,
        session_id=chat_session.id,
        scope="session",
        status=status,
        source_memory_id=None,
        label=chat_session.title or chat_session.id,
        aliases=topics,
    )
    content = "\n".join(
        item
        for item in [
            f"Session: {chat_session.title or chat_session.id}",
            f"Summary: {summary_text}" if summary_text else "",
            f"Topics: {', '.join(topics)}" if topics else "",
            f"Decisions: {', '.join(decisions)}" if decisions else "",
            f"Open questions: {', '.join(open_questions)}" if open_questions else "",
            transcript_text,
        ]
        if item
    )
    _upsert_surface(
        db,
        target_type="session",
        target_id=chat_session.id,
        surface_kind="session_summary",
        content=content,
        scope="session",
        status=status,
        source_session_id=chat_session.id,
        metadata={
            "node_id": session_node.id,
            "topic_count": len(topics),
            "decision_count": len(decisions),
            "surface_origin": "session_summary",
        },
    )
    _upsert_surface(
        db,
        target_type="graph_node",
        target_id=session_node.id,
        surface_kind="graph_node_profile",
        content=_node_surface_text(session_node),
        scope=session_node.scope,
        status=session_node.status,
        source_session_id=session_node.source_session_id,
        metadata={
            "node_key": session_node.node_key,
            "node_type": session_node.node_type,
            "surface_origin": "memory_graph_node",
        },
    )


def _upsert_memory_node(db: Session, memory: MemoryRecord) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"memory:{memory.id}",
        node_type="memory",
        label=_truncate(memory.content, 160),
        scope=memory.scope,
        status=memory.status,
        aliases=memory.tags_json,
        source_memory_id=memory.id,
        source_session_id=memory.source_session_id,
        confidence=memory.confidence,
        salience=memory.salience,
        metadata={
            "memory_type": memory.memory_type,
            "created_by": memory.created_by,
        },
    )
    return node


def _upsert_session_node(
    db: Session,
    *,
    session_id: str,
    scope: str | None,
    status: str,
    source_memory_id: str | None,
    label: str | None = None,
    aliases: list[str] | None = None,
) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"session:{session_id}",
        node_type="session",
        label=label or session_id,
        scope=scope or "session",
        status=status,
        aliases=aliases or [],
        source_memory_id=source_memory_id,
        source_session_id=session_id,
        confidence=1.0,
        salience=0.7,
        metadata={"session_id": session_id},
    )
    return node


def _upsert_fact_node(
    db: Session,
    fact: MemoryFact,
    *,
    memory: MemoryRecord,
) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"fact:{fact.id}",
        node_type="fact",
        label=f"{fact.entity} {fact.predicate}",
        scope=memory.scope,
        status=fact.status,
        aliases=_fact_aliases(fact),
        source_memory_id=memory.id,
        source_fact_id=fact.id,
        source_session_id=fact.source_session_id or memory.source_session_id,
        confidence=fact.confidence,
        salience=fact.salience,
        metadata={
            "entity": fact.entity,
            "predicate": fact.predicate,
            "value": fact.value_json,
        },
    )
    return node


def _upsert_entity_node(
    db: Session,
    fact: MemoryFact,
    *,
    memory: MemoryRecord,
) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"entity:{fact.entity}",
        node_type="entity",
        label=fact.entity,
        scope=memory.scope,
        status="active",
        aliases=_fact_aliases(fact),
        source_memory_id=memory.id,
        source_fact_id=fact.id,
        source_session_id=fact.source_session_id or memory.source_session_id,
        confidence=fact.confidence,
        salience=max(fact.salience, memory.salience),
        metadata={
            "entity": fact.entity,
            "latest_fact_id": fact.id,
            "latest_memory_id": memory.id,
        },
    )
    return node


def _sync_memory_lifecycle_edges(
    db: Session,
    *,
    memory: MemoryRecord,
    memory_node: MemoryGraphNode,
) -> None:
    lifecycle = memory.metadata_json.get("lifecycle")
    if not isinstance(lifecycle, dict):
        return
    superseded_by = lifecycle.get("superseded_by")
    if isinstance(superseded_by, str):
        target_node = _upsert_external_memory_node(
            db,
            memory_id=superseded_by,
            scope=memory.scope,
        )
        _upsert_edge(
            db,
            source_node=memory_node,
            target_node=target_node,
            relation="superseded_by",
            source_memory_id=memory.id,
            source_session_id=memory.source_session_id,
            confidence=memory.confidence,
            salience=memory.salience,
        )
    for old_memory_id in lifecycle.get("supersedes") or []:
        if not isinstance(old_memory_id, str):
            continue
        target_node = _upsert_external_memory_node(
            db,
            memory_id=old_memory_id,
            scope=memory.scope,
        )
        _upsert_edge(
            db,
            source_node=memory_node,
            target_node=target_node,
            relation="supersedes",
            source_memory_id=memory.id,
            source_session_id=memory.source_session_id,
            confidence=memory.confidence,
            salience=memory.salience,
        )


def _sync_fact_lifecycle_edges(
    db: Session,
    *,
    fact: MemoryFact,
    fact_node: MemoryGraphNode,
    memory: MemoryRecord,
) -> None:
    if fact.supersedes_fact_id:
        target_node = _upsert_external_fact_node(
            db,
            fact_id=fact.supersedes_fact_id,
            memory=memory,
        )
        _upsert_edge(
            db,
            source_node=fact_node,
            target_node=target_node,
            relation="supersedes_fact",
            source_memory_id=memory.id,
            source_fact_id=fact.id,
            source_session_id=memory.source_session_id,
            confidence=fact.confidence,
            salience=fact.salience,
        )
    if fact.superseded_by_fact_id:
        target_node = _upsert_external_fact_node(
            db,
            fact_id=fact.superseded_by_fact_id,
            memory=memory,
        )
        _upsert_edge(
            db,
            source_node=fact_node,
            target_node=target_node,
            relation="superseded_by_fact",
            source_memory_id=memory.id,
            source_fact_id=fact.id,
            source_session_id=memory.source_session_id,
            confidence=fact.confidence,
            salience=fact.salience,
        )


def _upsert_external_memory_node(
    db: Session,
    *,
    memory_id: str,
    scope: str | None,
) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"memory:{memory_id}",
        node_type="memory",
        label=memory_id,
        scope=scope,
        status="referenced",
        aliases=[],
        source_memory_id=memory_id,
        confidence=0.7,
        salience=0.7,
        metadata={"external_reference": True},
    )
    return node


def _upsert_external_fact_node(
    db: Session,
    *,
    fact_id: str,
    memory: MemoryRecord,
) -> MemoryGraphNode:
    node, _ = repositories.upsert_memory_graph_node(
        db,
        node_key=f"fact:{fact_id}",
        node_type="fact",
        label=fact_id,
        scope=memory.scope,
        status="referenced",
        aliases=[],
        source_memory_id=memory.id,
        source_fact_id=fact_id,
        source_session_id=memory.source_session_id,
        confidence=0.7,
        salience=0.7,
        metadata={"external_reference": True},
    )
    return node


def _upsert_edge(
    db: Session,
    *,
    source_node: MemoryGraphNode,
    target_node: MemoryGraphNode,
    relation: str,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
) -> None:
    edge_key = "|".join(
        [
            relation,
            source_node.node_key,
            target_node.node_key,
            source_memory_id or "",
            source_fact_id or "",
        ]
    )
    repositories.upsert_memory_graph_edge(
        db,
        edge_key=edge_key,
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        relation=relation,
        source_memory_id=source_memory_id,
        source_fact_id=source_fact_id,
        source_session_id=source_session_id,
        confidence=confidence,
        salience=salience,
        metadata={
            "source_node_key": source_node.node_key,
            "target_node_key": target_node.node_key,
        },
    )


def _upsert_surface(
    db: Session,
    *,
    target_type: str,
    target_id: str,
    surface_kind: str,
    content: str,
    scope: str | None,
    status: str,
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    source_trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    surface_key = f"{target_type}:{target_id}:{surface_kind}"
    repositories.upsert_memory_surface(
        db,
        surface_key=surface_key,
        target_type=target_type,
        target_id=target_id,
        surface_kind=surface_kind,
        content=content,
        content_hash=_content_hash(content),
        scope=scope,
        status=status,
        source_session_id=source_session_id,
        source_turn_id=source_turn_id,
        source_message_id=source_message_id,
        source_trace_id=source_trace_id,
        metadata=metadata,
    )


def _memory_surface_text(memory: MemoryRecord, *, facts: list[MemoryFact]) -> str:
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


def _fact_surface_text(fact: MemoryFact, *, memory: MemoryRecord) -> str:
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


def _node_surface_text(node: MemoryGraphNode) -> str:
    return "\n".join(
        item
        for item in [
            f"Node {node.node_key}",
            f"Type: {node.node_type}",
            f"Label: {node.label}",
            f"Scope: {node.scope or ''}",
            f"Status: {node.status}",
            f"Aliases: {', '.join(node.aliases_json)}"
            if node.aliases_json
            else "",
            f"Metadata: {json.dumps(node.metadata_json, ensure_ascii=False)}",
        ]
        if item
    )


def _fact_aliases(fact: MemoryFact) -> list[str]:
    aliases = fact.metadata_json.get("aliases")
    if isinstance(aliases, list):
        return [item for item in aliases if isinstance(item, str)]
    return []


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


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

"""Persistence operations for derived retrieval surfaces, vectors, and graph state."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.storage.models import (
    EmbeddingVector,
    MemoryGraphEdge,
    MemoryGraphNode,
    MemorySurface,
    utc_now,
)

def upsert_memory_surface(
    db: Session,
    *,
    surface_key: str,
    target_type: str,
    target_id: str,
    surface_kind: str,
    content: str,
    content_hash: str,
    scope: str | None = None,
    status: str = "active",
    source_session_id: str | None = None,
    source_turn_id: str | None = None,
    source_message_id: str | None = None,
    source_trace_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemorySurface, bool]:
    existing = get_memory_surface_by_key(db, surface_key=surface_key)
    if existing is None:
        surface = MemorySurface(
            surface_key=surface_key,
            target_type=target_type,
            target_id=target_id,
            surface_kind=surface_kind,
            content=content,
            content_hash=content_hash,
            scope=scope,
            status=status,
            source_session_id=source_session_id,
            source_turn_id=source_turn_id,
            source_message_id=source_message_id,
            source_trace_id=source_trace_id,
            metadata_json=metadata or {},
        )
        db.add(surface)
        db.commit()
        db.refresh(surface)
        return surface, True

    changed_content = existing.content_hash != content_hash
    changed = changed_content or any(
        [
            existing.content != content,
            existing.target_type != target_type,
            existing.target_id != target_id,
            existing.surface_kind != surface_kind,
            existing.scope != scope,
            existing.status != status,
            existing.source_session_id != source_session_id,
            existing.source_turn_id != source_turn_id,
            existing.source_message_id != source_message_id,
            existing.source_trace_id != source_trace_id,
            existing.metadata_json != (metadata or {}),
        ]
    )
    if changed:
        existing.target_type = target_type
        existing.target_id = target_id
        existing.surface_kind = surface_kind
        existing.content = content
        existing.content_hash = content_hash
        existing.scope = scope
        existing.status = status
        existing.source_session_id = source_session_id
        existing.source_turn_id = source_turn_id
        existing.source_message_id = source_message_id
        existing.source_trace_id = source_trace_id
        existing.metadata_json = metadata or {}
        existing.updated_at = utc_now()
        if changed_content:
            existing.embedding_status = "pending"
            existing.embedding_model = None
            existing.embedding_vector_id = None
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_surface_by_key(
    db: Session,
    *,
    surface_key: str,
) -> MemorySurface | None:
    statement = select(MemorySurface).where(MemorySurface.surface_key == surface_key)
    return db.exec(statement).first()


def list_memory_surfaces(
    db: Session,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    surface_kind: str | None = None,
    embedding_status: str | None = None,
    limit: int = 100,
) -> list[MemorySurface]:
    statement = select(MemorySurface)
    if target_type is not None:
        statement = statement.where(MemorySurface.target_type == target_type)
    if target_id is not None:
        statement = statement.where(MemorySurface.target_id == target_id)
    if surface_kind is not None:
        statement = statement.where(MemorySurface.surface_kind == surface_kind)
    if embedding_status is not None:
        statement = statement.where(MemorySurface.embedding_status == embedding_status)
    statement = statement.order_by(
        MemorySurface.updated_at.desc(),
        MemorySurface.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def list_memory_surfaces_by_targets(
    db: Session,
    *,
    target_type: str,
    target_ids: list[str],
    surface_kind: str | None = None,
    status: str | None = "active",
    limit: int = 500,
) -> list[MemorySurface]:
    if not target_ids:
        return []
    statement = select(MemorySurface).where(
        MemorySurface.target_type == target_type,
        MemorySurface.target_id.in_(target_ids),
    )
    if surface_kind is not None:
        statement = statement.where(MemorySurface.surface_kind == surface_kind)
    if status is not None:
        statement = statement.where(MemorySurface.status == status)
    statement = statement.order_by(
        MemorySurface.updated_at.desc(),
        MemorySurface.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def get_embedding_vector_by_key(
    db: Session,
    *,
    object_key: str,
) -> EmbeddingVector | None:
    statement = select(EmbeddingVector).where(EmbeddingVector.object_key == object_key)
    return db.exec(statement).first()


def upsert_embedding_vector(
    db: Session,
    *,
    object_key: str,
    provider: str,
    model: str,
    input_hash: str,
    vector: list[float],
    input_kind: str = "memory_surface",
    source_surface_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    surface_kind: str | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> tuple[EmbeddingVector, bool]:
    existing = get_embedding_vector_by_key(db, object_key=object_key)
    normalized_metadata = metadata or {}
    vector_dim = len(vector)
    if existing is None:
        record = EmbeddingVector(
            object_key=object_key,
            provider=provider,
            model=model,
            input_hash=input_hash,
            input_kind=input_kind,
            vector_dim=vector_dim,
            vector_json=vector,
            source_surface_id=source_surface_id,
            target_type=target_type,
            target_id=target_id,
            surface_kind=surface_kind,
            status=status,
            metadata_json=normalized_metadata,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record, True

    changed = any(
        [
            existing.provider != provider,
            existing.model != model,
            existing.input_hash != input_hash,
            existing.input_kind != input_kind,
            existing.vector_dim != vector_dim,
            existing.vector_json != vector,
            existing.source_surface_id != source_surface_id,
            existing.target_type != target_type,
            existing.target_id != target_id,
            existing.surface_kind != surface_kind,
            existing.status != status,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.provider = provider
        existing.model = model
        existing.input_hash = input_hash
        existing.input_kind = input_kind
        existing.vector_dim = vector_dim
        existing.vector_json = vector
        existing.source_surface_id = source_surface_id
        existing.target_type = target_type
        existing.target_id = target_id
        existing.surface_kind = surface_kind
        existing.status = status
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def mark_memory_surface_embedded(
    db: Session,
    *,
    surface_id: str,
    embedding_model: str,
    embedding_vector_id: str,
) -> MemorySurface | None:
    surface = db.get(MemorySurface, surface_id)
    if surface is None:
        return None

    changed = any(
        [
            surface.embedding_status != "embedded",
            surface.embedding_model != embedding_model,
            surface.embedding_vector_id != embedding_vector_id,
        ]
    )
    if changed:
        surface.embedding_status = "embedded"
        surface.embedding_model = embedding_model
        surface.embedding_vector_id = embedding_vector_id
        surface.updated_at = utc_now()
        db.add(surface)
        db.commit()
        db.refresh(surface)
    return surface


def upsert_memory_graph_node(
    db: Session,
    *,
    node_key: str,
    node_type: str,
    label: str,
    scope: str | None = None,
    status: str = "active",
    aliases: list[str] | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    confidence: float = 0.7,
    salience: float = 0.7,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemoryGraphNode, bool]:
    existing = get_memory_graph_node_by_key(db, node_key=node_key)
    normalized_aliases = aliases or []
    normalized_metadata = metadata or {}
    if existing is None:
        node = MemoryGraphNode(
            node_key=node_key,
            node_type=node_type,
            label=label,
            scope=scope,
            status=status,
            aliases_json=normalized_aliases,
            source_memory_id=source_memory_id,
            source_fact_id=source_fact_id,
            source_session_id=source_session_id,
            confidence=confidence,
            salience=salience,
            metadata_json=normalized_metadata,
        )
        db.add(node)
        db.commit()
        db.refresh(node)
        return node, True

    changed = any(
        [
            existing.node_type != node_type,
            existing.label != label,
            existing.scope != scope,
            existing.status != status,
            existing.aliases_json != normalized_aliases,
            existing.source_memory_id != source_memory_id,
            existing.source_fact_id != source_fact_id,
            existing.source_session_id != source_session_id,
            existing.confidence != confidence,
            existing.salience != salience,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.node_type = node_type
        existing.label = label
        existing.scope = scope
        existing.status = status
        existing.aliases_json = normalized_aliases
        existing.source_memory_id = source_memory_id
        existing.source_fact_id = source_fact_id
        existing.source_session_id = source_session_id
        existing.confidence = confidence
        existing.salience = salience
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_graph_node_by_key(
    db: Session,
    *,
    node_key: str,
) -> MemoryGraphNode | None:
    statement = select(MemoryGraphNode).where(MemoryGraphNode.node_key == node_key)
    return db.exec(statement).first()


def list_memory_graph_nodes(
    db: Session,
    *,
    node_type: str | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    limit: int = 100,
) -> list[MemoryGraphNode]:
    statement = select(MemoryGraphNode)
    if node_type is not None:
        statement = statement.where(MemoryGraphNode.node_type == node_type)
    if source_memory_id is not None:
        statement = statement.where(MemoryGraphNode.source_memory_id == source_memory_id)
    if source_fact_id is not None:
        statement = statement.where(MemoryGraphNode.source_fact_id == source_fact_id)
    if source_session_id is not None:
        statement = statement.where(
            MemoryGraphNode.source_session_id == source_session_id
        )
    statement = statement.order_by(
        MemoryGraphNode.updated_at.desc(),
        MemoryGraphNode.id,
    ).limit(limit)
    return list(db.exec(statement).all())


def upsert_memory_graph_edge(
    db: Session,
    *,
    edge_key: str,
    source_node_id: str,
    target_node_id: str,
    relation: str,
    status: str = "active",
    confidence: float = 0.7,
    salience: float = 0.7,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> tuple[MemoryGraphEdge, bool]:
    existing = get_memory_graph_edge_by_key(db, edge_key=edge_key)
    normalized_metadata = metadata or {}
    if existing is None:
        edge = MemoryGraphEdge(
            edge_key=edge_key,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            status=status,
            confidence=confidence,
            salience=salience,
            source_memory_id=source_memory_id,
            source_fact_id=source_fact_id,
            source_session_id=source_session_id,
            metadata_json=normalized_metadata,
        )
        db.add(edge)
        db.commit()
        db.refresh(edge)
        return edge, True

    changed = any(
        [
            existing.source_node_id != source_node_id,
            existing.target_node_id != target_node_id,
            existing.relation != relation,
            existing.status != status,
            existing.confidence != confidence,
            existing.salience != salience,
            existing.source_memory_id != source_memory_id,
            existing.source_fact_id != source_fact_id,
            existing.source_session_id != source_session_id,
            existing.metadata_json != normalized_metadata,
        ]
    )
    if changed:
        existing.source_node_id = source_node_id
        existing.target_node_id = target_node_id
        existing.relation = relation
        existing.status = status
        existing.confidence = confidence
        existing.salience = salience
        existing.source_memory_id = source_memory_id
        existing.source_fact_id = source_fact_id
        existing.source_session_id = source_session_id
        existing.metadata_json = normalized_metadata
        existing.updated_at = utc_now()
        db.add(existing)
        db.commit()
        db.refresh(existing)
    return existing, False


def get_memory_graph_edge_by_key(
    db: Session,
    *,
    edge_key: str,
) -> MemoryGraphEdge | None:
    statement = select(MemoryGraphEdge).where(MemoryGraphEdge.edge_key == edge_key)
    return db.exec(statement).first()


def list_memory_graph_edges(
    db: Session,
    *,
    source_node_id: str | None = None,
    target_node_id: str | None = None,
    relation: str | None = None,
    source_memory_id: str | None = None,
    source_fact_id: str | None = None,
    source_session_id: str | None = None,
    limit: int = 100,
) -> list[MemoryGraphEdge]:
    statement = select(MemoryGraphEdge)
    if source_node_id is not None:
        statement = statement.where(MemoryGraphEdge.source_node_id == source_node_id)
    if target_node_id is not None:
        statement = statement.where(MemoryGraphEdge.target_node_id == target_node_id)
    if relation is not None:
        statement = statement.where(MemoryGraphEdge.relation == relation)
    if source_memory_id is not None:
        statement = statement.where(MemoryGraphEdge.source_memory_id == source_memory_id)
    if source_fact_id is not None:
        statement = statement.where(MemoryGraphEdge.source_fact_id == source_fact_id)
    if source_session_id is not None:
        statement = statement.where(
            MemoryGraphEdge.source_session_id == source_session_id
        )
    statement = statement.order_by(
        MemoryGraphEdge.updated_at.desc(),
        MemoryGraphEdge.id,
    ).limit(limit)
    return list(db.exec(statement).all())



"""Persistence for source-labelled chronological compaction artifacts."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session, select

from app.storage.models import HistoryCompaction, utc_now


def get_history_compaction(
    db: Session,
    compaction_id: str,
) -> HistoryCompaction | None:
    return db.get(HistoryCompaction, compaction_id)


def get_latest_history_compaction(
    db: Session,
    *,
    session_id: str,
    status: str | None = "active",
) -> HistoryCompaction | None:
    statement = select(HistoryCompaction).where(
        HistoryCompaction.session_id == session_id
    )
    if status is not None:
        statement = statement.where(HistoryCompaction.status == status)
    statement = statement.order_by(
        HistoryCompaction.generation.desc(),
        HistoryCompaction.created_at.desc(),
        HistoryCompaction.id,
    )
    return db.exec(statement).first()


def list_history_compactions(
    db: Session,
    *,
    session_id: str,
    status: str | None = None,
) -> list[HistoryCompaction]:
    statement = select(HistoryCompaction).where(
        HistoryCompaction.session_id == session_id
    )
    if status is not None:
        statement = statement.where(HistoryCompaction.status == status)
    statement = statement.order_by(
        HistoryCompaction.generation,
        HistoryCompaction.created_at,
        HistoryCompaction.id,
    )
    return list(db.exec(statement).all())


def create_history_compaction(
    db: Session,
    *,
    session_id: str,
    summary: str,
    summary_sha256: str,
    source_history_sha256: str,
    covered_through_turn_id: str,
    covered_turn_ids: list[str],
    covered_sources: list[dict[str, Any]],
    source_estimated_tokens: int,
    summary_estimated_tokens: int,
    trigger_turn_id: str | None,
    model: str | None,
    provider_message_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> HistoryCompaction:
    previous = get_latest_history_compaction(
        db,
        session_id=session_id,
        status=None,
    )
    generation = (previous.generation + 1) if previous is not None else 1
    now = utc_now()
    if previous is not None and previous.status == "active":
        previous.status = "superseded"
        previous.updated_at = now
        db.add(previous)

    artifact = HistoryCompaction(
        session_id=session_id,
        generation=generation,
        status="active",
        summary=summary,
        summary_sha256=summary_sha256,
        source_history_sha256=source_history_sha256,
        covered_through_turn_id=covered_through_turn_id,
        trigger_turn_id=trigger_turn_id,
        previous_compaction_id=previous.id if previous is not None else None,
        covered_turn_ids_json=covered_turn_ids,
        covered_sources_json=covered_sources,
        source_estimated_tokens=source_estimated_tokens,
        summary_estimated_tokens=summary_estimated_tokens,
        model=model,
        provider_message_id=provider_message_id,
        metadata_json=metadata or {},
        updated_at=now,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    if previous is not None:
        db.refresh(previous)
    return artifact

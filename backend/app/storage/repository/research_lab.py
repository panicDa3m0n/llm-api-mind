"""Persistence for the bounded, non-cognitive Research Lab evidence ledger."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.storage.models import (
    ResearchLabArtifact,
    ResearchLabRun,
    ResearchLabSource,
    utc_now,
)


def create_research_lab_run(
    db: Session,
    *,
    profile_id: str,
    session_id: str | None,
    turn_id: str | None,
    action: str,
    intent: str,
    request: dict[str, Any],
    source_ids: list[str] | None = None,
    runner_identity: str | None = None,
) -> ResearchLabRun:
    run = ResearchLabRun(
        profile_id=profile_id,
        session_id=session_id,
        turn_id=turn_id,
        action=action,
        intent=intent,
        request_json=request,
        source_ids_json=source_ids or [],
        runner_identity=runner_identity,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def complete_research_lab_run(
    db: Session,
    *,
    run: ResearchLabRun,
    result: dict[str, Any],
    status: str = "completed",
) -> ResearchLabRun:
    run.status = status
    run.result_json = result
    run.error_json = None
    run.completed_at = utc_now()
    run.updated_at = utc_now()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def fail_research_lab_run(
    db: Session,
    *,
    run: ResearchLabRun,
    error: dict[str, Any],
) -> ResearchLabRun:
    run.status = "failed"
    run.error_json = error
    run.completed_at = utc_now()
    run.updated_at = utc_now()
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_research_lab_run(db: Session, run_id: str) -> ResearchLabRun | None:
    return db.get(ResearchLabRun, run_id)


def list_research_lab_runs(
    db: Session,
    *,
    profile_id: str,
    session_id: str | None = None,
    limit: int = 10,
) -> list[ResearchLabRun]:
    statement = select(ResearchLabRun).where(ResearchLabRun.profile_id == profile_id)
    if session_id is not None:
        statement = statement.where(ResearchLabRun.session_id == session_id)
    statement = statement.order_by(
        ResearchLabRun.started_at.desc(),
        ResearchLabRun.id.desc(),
    ).limit(limit)
    return list(db.exec(statement).all())


def create_research_lab_source(
    db: Session,
    *,
    run_id: str,
    profile_id: str,
    url: str | None,
    title: str | None,
    content: str,
    content_sha256: str,
    content_type: str | None,
    retrieved_at: datetime,
    metadata: dict[str, Any] | None = None,
) -> ResearchLabSource:
    source = ResearchLabSource(
        run_id=run_id,
        profile_id=profile_id,
        url=url,
        title=title,
        content=content,
        content_sha256=content_sha256,
        content_type=content_type,
        retrieved_at=retrieved_at,
        metadata_json=metadata or {},
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_research_lab_source(db: Session, source_id: str) -> ResearchLabSource | None:
    return db.get(ResearchLabSource, source_id)


def create_research_lab_artifact(
    db: Session,
    *,
    run_id: str,
    profile_id: str,
    name: str,
    media_type: str,
    content_bytes: bytes,
    sha256: str,
) -> ResearchLabArtifact:
    artifact = ResearchLabArtifact(
        run_id=run_id,
        profile_id=profile_id,
        name=name,
        media_type=media_type,
        byte_size=len(content_bytes),
        sha256=sha256,
        content_bytes=content_bytes,
    )
    db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def get_research_lab_artifact(
    db: Session,
    artifact_id: str,
) -> ResearchLabArtifact | None:
    return db.get(ResearchLabArtifact, artifact_id)


def list_research_lab_artifacts(
    db: Session,
    *,
    run_id: str,
) -> list[ResearchLabArtifact]:
    statement = (
        select(ResearchLabArtifact)
        .where(ResearchLabArtifact.run_id == run_id)
        .order_by(ResearchLabArtifact.created_at, ResearchLabArtifact.id)
    )
    return list(db.exec(statement).all())


def delete_research_lab_artifact(
    db: Session,
    artifact: ResearchLabArtifact,
) -> None:
    """Remove one user-visible artifact while preserving its run receipt."""

    db.delete(artifact)
    db.commit()

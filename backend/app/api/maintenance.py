from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.config import Settings
from app.llm.factory import build_llm_provider
from app.mind.memory import memory_proposal_payload
from app.runtime.maintenance import (
    run_maintenance_job,
    schedule_summary_repairs,
    session_summary_audit,
)
from app.runtime.memory_provenance import (
    MemoryProvenanceMutationError,
    deprecate_explicit_test_fixtures,
    memory_provenance_audit,
    repair_exact_source_messages,
)
from app.storage import repositories
from app.storage.models import MaintenanceJob, MemoryProposal, MemoryRecord, utc_now


ProviderFactory = Callable[[Settings], Any]


class MaintenanceProposalArchiveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)
    result: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def merge_reason_into_result(self) -> "MaintenanceProposalArchiveBody":
        if self.reason is not None and "reason" not in self.result:
            self.result = {**self.result, "reason": self.reason}
        return self


class MemoryProvenanceRepairBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    expected_candidate_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    backup_reference: str | None = Field(default=None, min_length=1, max_length=1000)
    approval: Literal["repair-exact-source-messages"] | None = None

    @model_validator(mode="after")
    def require_apply_guards(self) -> "MemoryProvenanceRepairBody":
        if not self.dry_run and self.approval != "repair-exact-source-messages":
            raise ValueError("Apply requires approval='repair-exact-source-messages'.")
        return self


class ExplicitTestFixtureDeprecationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    reason: str = Field(min_length=1, max_length=1000)
    expected_candidate_digest: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    backup_reference: str | None = Field(default=None, min_length=1, max_length=1000)
    approval: Literal["deprecate-explicit-codex-test-fixtures"] | None = None

    @model_validator(mode="after")
    def require_apply_guards(self) -> "ExplicitTestFixtureDeprecationBody":
        if (
            not self.dry_run
            and self.approval != "deprecate-explicit-codex-test-fixtures"
        ):
            raise ValueError(
                "Apply requires approval='deprecate-explicit-codex-test-fixtures'."
            )
        return self


def build_maintenance_router(
    engine: Engine,
    settings: Settings,
    provider_factory: ProviderFactory = build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

    @router.get("/overview")
    def get_maintenance_overview(
        recent_limit: int = Query(default=8, ge=1, le=30),
    ) -> dict[str, Any]:
        now = utc_now()
        with Session(engine) as db:
            recent_jobs = repositories.list_maintenance_jobs(
                db,
                limit=recent_limit,
            )
            recent_proposals = repositories.list_memory_proposals(
                db,
                status=None,
                limit=recent_limit,
            )
            due_pending_jobs = repositories.list_due_maintenance_jobs(
                db,
                now=now,
                limit=recent_limit + 1,
            )
            maintenance_memories = db.exec(
                select(func.count(MemoryRecord.id)).where(
                    MemoryRecord.created_by == "maintenance"
                )
            ).one()

            return {
                "operation": "maintenance.overview",
                "generated_at": now.isoformat(),
                "settings": {
                    "enabled": settings.maintenance_enabled,
                    "idle_seconds": settings.maintenance_idle_seconds,
                    "worker_interval_seconds": settings.maintenance_worker_interval_seconds,
                    "job_batch_size": settings.maintenance_job_batch_size,
                },
                "jobs": {
                    "counts_by_status": _counts_by_column(
                        db,
                        MaintenanceJob.status,
                    ),
                    "counts_by_kind": _counts_by_column(db, MaintenanceJob.kind),
                    "due_pending_count": len(due_pending_jobs[:recent_limit]),
                    "due_pending_has_more": len(due_pending_jobs) > recent_limit,
                    "recent": [_maintenance_job_payload(job) for job in recent_jobs],
                },
                "memory_proposals": {
                    "counts_by_status": _counts_by_column(
                        db,
                        MemoryProposal.status,
                    ),
                    "counts_by_action": _counts_by_column(
                        db,
                        MemoryProposal.proposed_action,
                    ),
                    "counts_by_risk": _counts_by_column(db, MemoryProposal.risk),
                    "recent": [
                        memory_proposal_payload(proposal)
                        for proposal in recent_proposals
                    ],
                },
                "memories": {
                    "created_by_maintenance": maintenance_memories,
                },
                "lab_guidance": [
                    "Inspect pending proposals before adding new maintenance processes.",
                    "Use GET /api/maintenance/jobs to inspect idle jobs and skipped/failed runs.",
                    "Use POST /api/maintenance/jobs/{job_id}/run only for a pending lab job you want to execute now.",
                    "Keep merge/update/deprecate automation pending until embedding/KG evidence improves similarity and stale-memory detection.",
                ],
            }

    @router.get("/jobs")
    def list_maintenance_jobs(
        status_filter: str | None = Query(
            default=None,
            alias="status",
            max_length=40,
            description="Optional job status filter. Omit to list all statuses.",
        ),
        kind: str | None = Query(default=None, max_length=80),
        session_id: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        with Session(engine) as db:
            jobs = repositories.list_maintenance_jobs(
                db,
                status=status_filter,
                kind=kind,
                session_id=session_id,
                limit=limit + 1,
                offset=offset,
            )
            has_more = len(jobs) > limit
            visible = jobs[:limit]

        return {
            "operation": "maintenance.jobs.list",
            "status": status_filter,
            "kind": kind,
            "session_id": session_id,
            "limit": limit,
            "offset": offset,
            "returned": len(visible),
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
            "jobs": [_maintenance_job_payload(job) for job in visible],
        }

    @router.get("/summary/audit")
    def audit_session_summaries() -> dict[str, Any]:
        with Session(engine) as db:
            return {
                "operation": "maintenance.summary.audit",
                **session_summary_audit(db),
            }

    @router.post("/summary/reconcile")
    def reconcile_session_summaries(
        dry_run: bool = Query(default=True),
        limit: int = Query(default=2, ge=1, le=100),
    ) -> dict[str, Any]:
        with Session(engine) as db:
            audit = session_summary_audit(db)
            scheduled = (
                []
                if dry_run
                else schedule_summary_repairs(db, settings=settings, limit=limit)
            )
        return {
            "operation": "maintenance.summary.reconcile",
            "dry_run": dry_run,
            "limit": limit,
            "audit": audit,
            "scheduled_job_ids": [job.id for job in scheduled],
        }

    @router.get("/memory/provenance")
    def audit_memory_provenance(
        limit: int | None = Query(default=None, ge=1, le=10000),
    ) -> dict[str, Any]:
        with Session(engine) as db:
            report = memory_provenance_audit(db, limit=limit)
        return {
            "operation": "maintenance.memory.provenance",
            **report,
        }

    @router.post("/memory/provenance/repair")
    def repair_memory_provenance(
        body: MemoryProvenanceRepairBody,
    ) -> dict[str, Any]:
        try:
            with Session(engine) as db:
                return repair_exact_source_messages(
                    db,
                    dry_run=body.dry_run,
                    expected_candidate_digest=body.expected_candidate_digest,
                    backup_reference=body.backup_reference,
                )
        except MemoryProvenanceMutationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "memory_provenance.mutation_guard_failed",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc

    @router.post("/memory/provenance/deprecate-explicit-test-fixtures")
    def deprecate_memory_test_fixtures(
        body: ExplicitTestFixtureDeprecationBody,
    ) -> dict[str, Any]:
        try:
            with Session(engine) as db:
                return deprecate_explicit_test_fixtures(
                    db,
                    reason=body.reason,
                    dry_run=body.dry_run,
                    expected_candidate_digest=body.expected_candidate_digest,
                    backup_reference=body.backup_reference,
                )
        except MemoryProvenanceMutationError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "memory_provenance.mutation_guard_failed",
                    "message": str(exc),
                    "recoverable": True,
                },
            ) from exc

    @router.post("/jobs/{job_id}/run")
    def run_pending_maintenance_job(job_id: str) -> dict[str, Any]:
        with Session(engine) as db:
            job = repositories.get_maintenance_job(db, job_id)
            if job is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "maintenance_job.not_found",
                        "message": f"Maintenance job {job_id} was not found.",
                        "recoverable": True,
                    },
                )
        result = run_maintenance_job(
            engine,
            settings=settings,
            provider_factory=provider_factory,
            job_id=job_id,
        )
        return {
            "operation": "maintenance.jobs.run",
            "job_id": job_id,
            "result": result,
        }

    @router.get("/memory/proposals")
    def list_memory_proposals(
        status_filter: str | None = Query(
            default="open",
            alias="status",
            max_length=40,
            description=(
                "Proposal status filter. Use open for pending and pending_review; "
                "resolved for terminal states; all, any, or * disables the filter."
            ),
        ),
        source_session_id: str | None = Query(default=None, max_length=80),
        created_from: datetime | None = Query(default=None),
        created_to: datetime | None = Query(default=None),
        resolved_from: datetime | None = Query(default=None),
        resolved_to: datetime | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        normalized_status = None if status_filter in {"all", "any", "*"} else status_filter
        statuses = (
            sorted(repositories.RESOLVED_MEMORY_PROPOSAL_STATUSES)
            if normalized_status == "resolved"
            else (
                sorted(repositories.OPEN_MEMORY_PROPOSAL_STATUSES)
                if normalized_status == "open"
                else None
            )
        )
        exact_status = None if statuses is not None else normalized_status
        with Session(engine) as db:
            proposals = repositories.list_memory_proposals(
                db,
                status=exact_status,
                statuses=statuses,
                source_session_id=source_session_id,
                created_from=created_from,
                created_to=created_to,
                resolved_from=resolved_from,
                resolved_to=resolved_to,
                limit=limit + 1,
                offset=offset,
            )
            has_more = len(proposals) > limit
            visible = proposals[:limit]
            payloads = [memory_proposal_payload(proposal) for proposal in visible]

        return {
            "operation": "maintenance.memory.proposals.list",
            "status": normalized_status,
            "statuses": statuses,
            "source_session_id": source_session_id,
            "created_from": created_from.isoformat() if created_from else None,
            "created_to": created_to.isoformat() if created_to else None,
            "resolved_from": resolved_from.isoformat() if resolved_from else None,
            "resolved_to": resolved_to.isoformat() if resolved_to else None,
            "limit": limit,
            "offset": offset,
            "returned": len(payloads),
            "has_more": has_more,
            "next_offset": offset + limit if has_more else None,
            "proposals": payloads,
        }

    @router.post("/memory/proposals/{proposal_id}/archive")
    def archive_memory_proposal(
        proposal_id: str,
        body: MaintenanceProposalArchiveBody,
    ) -> dict[str, Any]:
        with Session(engine) as db:
            proposal = repositories.archive_memory_proposal(
                db,
                proposal_id=proposal_id,
                result=body.result,
            )
            if proposal is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "memory_proposal.not_found",
                        "message": f"Memory proposal {proposal_id} was not found.",
                        "recoverable": True,
                    },
                )
            payload = memory_proposal_payload(proposal)

        return {
            "operation": "maintenance.memory.proposals.archive",
            "proposal": payload,
        }

    return router


def _counts_by_column(db: Session, column: Any) -> dict[str, int]:
    statement = select(column, func.count()).group_by(column)
    return {
        str(key): int(count)
        for key, count in db.exec(statement).all()
        if key is not None
    }


def _maintenance_job_payload(job: MaintenanceJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "kind": job.kind,
        "status": job.status,
        "session_id": job.session_id,
        "trigger_turn_id": job.trigger_turn_id,
        "trigger_event_id": job.trigger_event_id,
        "due_at": job.due_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": (
            job.completed_at.isoformat() if job.completed_at else None
        ),
        "superseded_by_job_id": job.superseded_by_job_id,
        "idempotency_key": job.idempotency_key,
        "input": job.input_json,
        "result": job.result_json,
        "error": job.error_json,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }

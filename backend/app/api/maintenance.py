from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.mind.memory import memory_proposal_payload
from app.storage import repositories


class MaintenanceProposalArchiveBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)
    result: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def merge_reason_into_result(self) -> "MaintenanceProposalArchiveBody":
        if self.reason is not None and "reason" not in self.result:
            self.result = {**self.result, "reason": self.reason}
        return self


def build_maintenance_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

    @router.get("/memory/proposals")
    def list_memory_proposals(
        status_filter: str | None = Query(
            default="pending",
            alias="status",
            max_length=40,
            description=(
                "Proposal status filter. Use pending for open maintenance work; "
                "all, any, or * disables the status filter."
            ),
        ),
        source_session_id: str | None = Query(default=None, max_length=80),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> dict[str, Any]:
        normalized_status = None if status_filter in {"all", "any", "*"} else status_filter
        with Session(engine) as db:
            proposals = repositories.list_memory_proposals(
                db,
                status=normalized_status,
                source_session_id=source_session_id,
                limit=limit + 1,
                offset=offset,
            )
            has_more = len(proposals) > limit
            visible = proposals[:limit]
            payloads = [memory_proposal_payload(proposal) for proposal in visible]

        return {
            "operation": "maintenance.memory.proposals.list",
            "status": normalized_status,
            "source_session_id": source_session_id,
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

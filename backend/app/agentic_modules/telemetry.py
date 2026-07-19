"""Traceable receipts for Agentic Module host activity."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from scarlet_agentic_module_sdk.contracts import ContractModel
from app.runtime.events import record_event
from app.storage import repositories
from app.storage.models import new_id, utc_now


class ModuleReceipt(ContractModel):
    receipt_id: str
    module_id: str
    operation: str
    status: Literal["started", "succeeded", "failed", "skipped"]
    occurred_at: datetime
    duration_ms: int | None = None
    active_mode_tag: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    turn_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    event_id: str | None = None


class ModuleTelemetry(Protocol):
    async def emit(self, receipt: ModuleReceipt) -> ModuleReceipt: ...


class InMemoryModuleTelemetry:
    def __init__(self) -> None:
        self.receipts: list[ModuleReceipt] = []

    async def emit(self, receipt: ModuleReceipt) -> ModuleReceipt:
        self.receipts.append(receipt)
        return receipt


class RepositoryModuleTelemetry:
    """Persist module receipts in the existing Core trace/event stores."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    async def emit(self, receipt: ModuleReceipt) -> ModuleReceipt:
        if receipt.session_id is None:
            return receipt
        payload = receipt.model_dump(mode="json", exclude={"trace_id", "event_id"})
        with Session(self._engine) as db:
            trace = repositories.add_trace(
                db,
                session_id=receipt.session_id,
                turn_id=receipt.turn_id,
                kind=f"agentic_module.{receipt.operation}",
                payload=payload,
            )
            trace_id = trace.id
            event = record_event(
                db,
                session_id=receipt.session_id,
                turn_id=receipt.turn_id,
                event_type=(f"agentic_module.{receipt.operation}.{receipt.status}"),
                source=receipt.module_id,
                actor="module_host",
                visibility="debug",
                status=_event_status(receipt.status),
                trace_id=trace_id,
                payload={
                    "receipt_id": receipt.receipt_id,
                    "module_id": receipt.module_id,
                    "operation": receipt.operation,
                    "duration_ms": receipt.duration_ms,
                    "details": receipt.details,
                },
            )
            event_id = event.id
        return receipt.model_copy(update={"trace_id": trace_id, "event_id": event_id})


def new_receipt(
    *,
    module_id: str,
    operation: str,
    status: Literal["started", "succeeded", "failed", "skipped"],
    active_mode_tag: str | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
    turn_id: str | None = None,
    duration_ms: int | None = None,
    details: dict[str, Any] | None = None,
) -> ModuleReceipt:
    return ModuleReceipt(
        receipt_id=new_id("modrcpt"),
        module_id=module_id,
        operation=operation,
        status=status,
        occurred_at=utc_now(),
        duration_ms=duration_ms,
        active_mode_tag=active_mode_tag,
        request_id=request_id,
        session_id=session_id,
        turn_id=turn_id,
        details=details or {},
    )


def _event_status(status: str) -> str:
    if status == "started":
        return "active"
    if status == "failed":
        return "failed"
    return "completed"

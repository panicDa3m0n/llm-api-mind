import time
from collections.abc import Callable

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMProvider
from app.llm.factory import build_llm_provider
from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIRequest,
    MindAPIResponse,
    dispatch_mind_api,
)
from app.mind.schema import build_mind_schema
from app.runtime.events import record_event
from app.storage import repositories

ProviderFactory = Callable[[Settings], LLMProvider]


class MindAPICallRequest(MindAPIRequest):
    session_id: str | None = None
    turn_id: str | None = None


class MindAPICallResponse(MindAPIResponse):
    tool_call_id: str


def build_mind_router(
    engine: Engine,
    settings: Settings,
    provider_factory: ProviderFactory = build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/mind", tags=["mind"])

    @router.get("/schema", response_model=MindAPIResponse)
    def get_schema() -> MindAPIResponse:
        return MindAPIResponse(
            ok=True,
            result=build_mind_schema(),
            cognitive_hint="This is the currently available Mind API surface.",
            suggested_next_actions=["Use POST /mind/call to exercise mind_api"],
            confidence=1.0,
        )

    @router.post("/call", response_model=MindAPICallResponse)
    def call_mind_api(request: MindAPICallRequest) -> MindAPICallResponse:
        started = time.perf_counter()
        mind_request = MindAPIRequest(
            method=request.method,
            path=request.path,
            body=request.body,
            intent=request.intent,
        )
        with Session(engine) as db:
            if request.session_id is not None:
                chat_session = repositories.get_chat_session(db, request.session_id)
                if chat_session is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={
                            "code": "session.not_found",
                            "message": f"Session {request.session_id} was not found.",
                            "recoverable": True,
                        },
                    )

        source_message_id: str | None = None
        if request.turn_id is not None:
            with Session(engine) as db:
                source_message = repositories.latest_message_for_turn(
                    db,
                    turn_id=request.turn_id,
                    role="user",
                )
                source_message_id = (
                    source_message.id if source_message is not None else None
                )
        context = (
            MindAPIContext(
                engine=engine,
                session_id=request.session_id,
                turn_id=request.turn_id,
                source_message_id=source_message_id,
                settings=settings,
                provider_factory=provider_factory,
            )
            if request.session_id is not None
            else None
        )
        started_event_id: str | None = None
        if request.session_id is not None:
            with Session(engine) as db:
                started_event = record_event(
                    db,
                    session_id=request.session_id,
                    turn_id=request.turn_id,
                    event_type="mind.tool_call.started",
                    payload={
                        "tool_name": "mind_api",
                        "arguments": mind_request.model_dump(mode="json"),
                        "operation": {
                            "method": mind_request.method,
                            "path": mind_request.path,
                            "intent": mind_request.intent,
                        },
                    },
                    source="mind_api",
                    actor="scarlet",
                    visibility="debug",
                    status="active",
                )
                started_event_id = started_event.id

        response = dispatch_mind_api(mind_request, context=context)
        latency_ms = int((time.perf_counter() - started) * 1000)

        with Session(engine) as db:
            result_payload = response.model_dump(mode="json")
            tool_call = repositories.add_tool_call(
                db,
                session_id=request.session_id,
                turn_id=request.turn_id,
                tool_name="mind_api",
                arguments=mind_request.model_dump(mode="json"),
                result=result_payload,
                status="completed" if response.ok else "error",
                latency_ms=latency_ms,
            )
            tool_call_id = tool_call.id
            tool_call_status = tool_call.status

            trace_id: str | None = None
            if request.session_id is not None:
                trace = repositories.add_trace(
                    db,
                    session_id=request.session_id,
                    turn_id=request.turn_id,
                    kind="mind.tool_call",
                    payload={
                        "tool_call_id": tool_call_id,
                        "tool_name": "mind_api",
                        "arguments": mind_request.model_dump(mode="json"),
                        "result": result_payload,
                        "status": tool_call_status,
                        "latency_ms": latency_ms,
                    },
                )
                trace_id = trace.id
                record_event(
                    db,
                    session_id=request.session_id,
                    turn_id=request.turn_id,
                    event_type="mind.tool_call.completed"
                    if response.ok
                    else "mind.tool_call.failed",
                    payload={
                        "tool_name": "mind_api",
                        "operation": {
                            "method": mind_request.method,
                            "path": mind_request.path,
                            "intent": mind_request.intent,
                        },
                        "arguments": mind_request.model_dump(mode="json"),
                        "result_summary": _mind_call_result_summary(result_payload),
                        "latency_ms": latency_ms,
                    },
                    source="mind_api",
                    actor="backend",
                    visibility="debug",
                    status=tool_call_status,
                    parent_event_id=started_event_id,
                    trace_id=trace_id,
                    tool_call_id=tool_call_id,
                )

        response.trace_id = trace_id
        return MindAPICallResponse(
            **response.model_dump(mode="json"),
            tool_call_id=tool_call_id,
        )

    return router


def _mind_call_result_summary(result_payload: dict) -> dict:
    result = result_payload.get("result")
    if not isinstance(result, dict):
        result = {}
    error = result_payload.get("error")
    summary = {
        "ok": result_payload.get("ok"),
        "operation": result.get("operation"),
        "confidence": result_payload.get("confidence"),
    }
    for key in (
        "stored",
        "policy_decision",
        "memory_id",
        "count",
        "up_to_date",
        "json_repair_applied",
    ):
        if key in result:
            summary[key] = result[key]
    if isinstance(error, dict):
        summary["error"] = {
            "code": error.get("code"),
            "message": error.get("message"),
            "recoverable": error.get("recoverable"),
        }
    return summary

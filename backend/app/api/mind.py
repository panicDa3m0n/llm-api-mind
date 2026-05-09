import time

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIRequest,
    MindAPIResponse,
    dispatch_mind_api,
)
from app.mind.schema import build_mind_schema
from app.storage import repositories


class MindAPICallRequest(MindAPIRequest):
    session_id: str | None = None
    turn_id: str | None = None


class MindAPICallResponse(MindAPIResponse):
    tool_call_id: str


def build_mind_router(engine: Engine) -> APIRouter:
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

        context = (
            MindAPIContext(
                engine=engine,
                session_id=request.session_id,
                turn_id=request.turn_id,
            )
            if request.session_id is not None
            else None
        )
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

        response.trace_id = trace_id
        return MindAPICallResponse(
            **response.model_dump(mode="json"),
            tool_call_id=tool_call_id,
        )

    return router

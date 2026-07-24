from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_serialization import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
    EventResponse,
    TraceResponse,
    event_response as _event_response,
    message_response as _message_response,
    session_response as _session_response,
    trace_response as _trace_response,
)
from app.api.chat_native_turn import (
    NativeTurnFailure,
    execute_native_turn,
    prepare_native_turn,
    stream_native_turn,
)
from app.api.chat_stream_v2 import (
    StreamReplayResponse,
    replay_session_events,
    stream_persisted_turn_events,
)
from app.api.chat_turn_runner import start_native_turn_runner
from app.config import Settings
from app.llm.factory import (
    build_llm_provider,
)
from app.llm.provider import (
    LLMProvider,
)
from app.runtime.maintenance import (
    schedule_summary_repairs,
)
from app.storage import repositories
from app.storage.models import ChatSession


ProviderFactory = Callable[[Settings], LLMProvider]


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatTurnRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    system: str | None = Field(default=None, max_length=20000)
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


def build_chat_router(
    settings: Settings,
    engine: Engine,
    provider_factory: ProviderFactory = build_llm_provider,
) -> APIRouter:
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("/sessions", response_model=ChatSessionResponse)
    def create_session(request: ChatSessionCreate) -> ChatSessionResponse:
        with Session(engine) as db:
            chat_session = repositories.create_chat_session(
                db,
                title=request.title,
                metadata=request.metadata,
            )
            schedule_summary_repairs(
                db,
                settings=settings,
                limit=1,
                exclude_session_id=chat_session.id,
            )
            return _session_response(chat_session)

    @router.get("/sessions", response_model=list[ChatSessionResponse])
    def list_sessions(
        limit: int = Query(default=30, ge=1, le=100),
    ) -> list[ChatSessionResponse]:
        with Session(engine) as db:
            sessions = repositories.list_chat_sessions(db, limit=limit)
            return [_session_response(chat_session) for chat_session in sessions]

    @router.get(
        "/sessions/{session_id}/messages",
        response_model=list[ChatMessageResponse],
    )
    def get_messages(session_id: str) -> list[ChatMessageResponse]:
        with Session(engine) as db:
            _require_session(db, session_id)
            messages = repositories.list_messages(db, session_id=session_id)
            return [_message_response(message) for message in messages]

    @router.post(
        "/sessions/{session_id}/turn",
        response_model=ChatTurnResponse,
    )
    def create_turn(session_id: str, request: ChatTurnRequest) -> ChatTurnResponse:
        try:
            prepared = prepare_native_turn(
                settings=settings,
                engine=engine,
                session_id=session_id,
                message=request.message,
                system_override=request.system,
                requested_max_tokens=request.max_tokens,
                stream=False,
            )
            return execute_native_turn(
                settings=settings,
                engine=engine,
                provider_factory=provider_factory,
                prepared=prepared,
            )
        except NativeTurnFailure as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc

    @router.post("/sessions/{session_id}/turn/stream")
    def create_streaming_turn(
        session_id: str,
        request: ChatTurnRequest,
    ) -> StreamingResponse:
        try:
            prepared = prepare_native_turn(
                settings=settings,
                engine=engine,
                session_id=session_id,
                message=request.message,
                system_override=request.system,
                requested_max_tokens=request.max_tokens,
                stream=True,
            )
        except NativeTurnFailure as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc
        return StreamingResponse(
            stream_native_turn(
                settings=settings,
                engine=engine,
                provider_factory=provider_factory,
                prepared=prepared,
            ),
            media_type="application/x-ndjson",
        )

    @router.post("/sessions/{session_id}/turn/stream-v2")
    def create_streaming_turn_v2(
        session_id: str,
        request: ChatTurnRequest,
    ) -> StreamingResponse:
        try:
            prepared = prepare_native_turn(
                settings=settings,
                engine=engine,
                session_id=session_id,
                message=request.message,
                system_override=request.system,
                requested_max_tokens=request.max_tokens,
                stream=True,
            )
        except NativeTurnFailure as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc
        start_native_turn_runner(
            settings=settings,
            engine=engine,
            provider_factory=provider_factory,
            prepared=prepared,
        )
        return StreamingResponse(
            stream_persisted_turn_events(
                engine=engine,
                session_id=session_id,
                turn_id=prepared.turn_id,
            ),
            media_type="application/x-ndjson",
            headers={
                "X-Scarlet-Stream-Schema": "scarlet-stream-v2",
                "X-Scarlet-Turn-ID": prepared.turn_id,
            },
        )

    @router.get("/sessions/{session_id}/turns/{turn_id}/stream-v2")
    def resume_streaming_turn_v2(
        session_id: str,
        turn_id: str,
        after_seq: int = Query(default=0, ge=0),
    ) -> StreamingResponse:
        with Session(engine) as db:
            _require_session(db, session_id)
            turn = repositories.get_turn(db, turn_id)
            if turn is None or turn.session_id != session_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "turn.not_found",
                        "message": f"Turn {turn_id} was not found in this session.",
                        "recoverable": False,
                    },
                )
        return StreamingResponse(
            stream_persisted_turn_events(
                engine=engine,
                session_id=session_id,
                turn_id=turn_id,
                after_seq=after_seq,
            ),
            media_type="application/x-ndjson",
            headers={
                "X-Scarlet-Stream-Schema": "scarlet-stream-v2",
                "X-Scarlet-Turn-ID": turn_id,
            },
        )

    @router.get(
        "/sessions/{session_id}/events",
        response_model=StreamReplayResponse,
    )
    def replay_events(
        session_id: str,
        after_seq: int = Query(default=0, ge=0),
        limit: int = Query(default=500, ge=1, le=1000),
    ) -> StreamReplayResponse:
        with Session(engine) as db:
            _require_session(db, session_id)
            return replay_session_events(
                db,
                session_id=session_id,
                after_seq=after_seq,
                limit=limit,
            )

    return router


def build_trace_router(engine: Engine) -> APIRouter:
    router = APIRouter(prefix="/api/debug", tags=["debug"])

    @router.get("/traces/{turn_id}", response_model=list[TraceResponse])
    def get_traces(turn_id: str) -> list[TraceResponse]:
        with Session(engine) as db:
            traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
            if not traces:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "trace.not_found",
                        "message": f"No traces found for turn {turn_id}.",
                        "recoverable": True,
                    },
                )
            return [_trace_response(trace) for trace in traces]

    @router.get("/events", response_model=list[EventResponse])
    def get_events(
        session_id: str | None = Query(default=None),
        turn_id: str | None = Query(default=None),
        limit: int = Query(default=200, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[EventResponse]:
        if session_id is None and turn_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "events.scope_required",
                    "message": "Pass session_id or turn_id to inspect runtime events.",
                    "recoverable": True,
                },
            )
        with Session(engine) as db:
            if turn_id is not None:
                events = repositories.list_events_for_turn(db, turn_id=turn_id)
            else:
                assert session_id is not None
                events = repositories.list_events_for_session(
                    db,
                    session_id=session_id,
                    limit=limit,
                    offset=offset,
                )
                events = list(reversed(events))
            return [_event_response(event) for event in events]

    return router


def _require_session(db: Session, session_id: str) -> ChatSession:
    chat_session = repositories.get_chat_session(db, session_id)
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "session.not_found",
                "message": f"Session {session_id} was not found.",
                "recoverable": True,
            },
        )
    return chat_session

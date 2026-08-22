"""Experimental Android/Tapo interactive videocall transport."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.api.chat_live_stream import LiveTurnFeed, stream_live_turn_items
from app.api.chat_native_turn import NativeTurnFailure, prepare_native_turn
from app.api.chat_turn_runner import start_native_turn_runner
from app.config import Settings
from app.llm.factory import build_multimodal_llm_provider
from app.llm.provider import LLMProvider
from app.plugins.camera_perception.live import SpeechAlignedCameraCapture
from app.plugins.camera_perception.service import package_camera_observation
from app.plugins.camera_perception.service import capture_camera_observation
from app.runtime.events import record_event
from app.storage import repositories


ProviderFactory = Callable[[Settings], LLMProvider]
LIVE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "X-Scarlet-Stream-Schema": "scarlet-live-v1",
}


class VideoCallStartRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    client: str = Field(default="android_app", max_length=80)


class SpeechStartRequest(BaseModel):
    utterance_id: str = Field(min_length=1, max_length=120)


class VideoCallTurnRequest(BaseModel):
    utterance_id: str = Field(min_length=1, max_length=120)
    transcript: str = Field(min_length=1, max_length=20000)
    max_tokens: int | None = Field(default=None, ge=1, le=131072)


class VideoCallStateResponse(BaseModel):
    call_id: str
    session_id: str
    state: str
    source_id: str
    speech_input: str = "android_speech_recognizer"
    visual_input: str = "configured_camera_source"
    speech_output: str = "android_text_to_speech"
    half_duplex: bool = True
    started_at: str
    utterance_id: str | None = None


@dataclass
class _VideoCall:
    id: str
    session_id: str
    source_id: str
    started_at: datetime
    state: str = "LISTENING"
    utterance_id: str | None = None
    capture: SpeechAlignedCameraCapture | None = None


class _VideoCallRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._lock = threading.RLock()
        self._calls: dict[str, _VideoCall] = {}

    def start(self, session_id: str) -> _VideoCall:
        call = _VideoCall(
            id=f"videocall_{uuid4().hex}",
            session_id=session_id,
            source_id=self._settings.camera_perception_source_id,
            started_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._calls[call.id] = call
        return call

    def speech_started(self, call_id: str, utterance_id: str) -> _VideoCall:
        with self._lock:
            call = self.require(call_id)
            if call.state != "LISTENING":
                raise RuntimeError(
                    f"Videocall is {call.state}; a new utterance cannot start."
                )
            capture = SpeechAlignedCameraCapture(self._settings)
            call.capture = capture
            call.utterance_id = utterance_id
            call.state = "USER_SPEAKING"
            return call

    def finish_speech(self, call_id: str, utterance_id: str):
        with self._lock:
            call = self.require(call_id)
            if call.state != "USER_SPEAKING":
                raise RuntimeError(
                    f"Videocall is {call.state}; no speech window can be closed."
                )
            if call.utterance_id != utterance_id or call.capture is None:
                raise RuntimeError("The utterance does not match the active camera window.")
            capture = call.capture
            call.capture = None
            call.state = "WAITING_FOR_SCARLET"
        return call, capture.finish()

    def turn_completed(self, call_id: str) -> None:
        with self._lock:
            call = self._calls.get(call_id)
            if call is None:
                return
            call.state = "LISTENING"
            call.utterance_id = None

    def stop(self, call_id: str) -> _VideoCall:
        with self._lock:
            call = self.require(call_id)
            self._calls.pop(call_id, None)
            call.state = "STOPPED"
            capture = call.capture
            call.capture = None
        if capture is not None:
            capture.abort()
        return call

    def require(self, call_id: str) -> _VideoCall:
        call = self._calls.get(call_id)
        if call is None:
            raise KeyError(call_id)
        return call


def build_videocall_router(
    settings: Settings,
    engine: Engine,
    *,
    provider_factory: ProviderFactory = build_multimodal_llm_provider,
) -> APIRouter:
    """Expose the app-scope videocall process without creating a second Core."""

    router = APIRouter(prefix="/api/perception/videocall", tags=["perception"])
    registry = _VideoCallRegistry(settings)

    @router.post("/start", response_model=VideoCallStateResponse)
    def start_call(request: VideoCallStartRequest) -> VideoCallStateResponse:
        _require_enabled(settings)
        with Session(engine) as db:
            chat_session = repositories.get_chat_session(db, request.session_id)
            if chat_session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "session.not_found",
                        "message": f"Session {request.session_id} was not found.",
                    },
                )
            if chat_session.kind != "human_dialogue":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "videocall.session_kind_invalid",
                        "message": "Videocalls require a human dialogue session.",
                    },
                )
        return _state_response(registry.start(request.session_id))

    @router.post(
        "/{call_id}/speech-start",
        response_model=VideoCallStateResponse,
    )
    def speech_started(
        call_id: str,
        request: SpeechStartRequest,
    ) -> VideoCallStateResponse:
        try:
            call = registry.speech_started(call_id, request.utterance_id)
        except KeyError as exc:
            raise _call_not_found(call_id) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "videocall.state_conflict",
                    "message": str(exc),
                },
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "videocall.camera_start_failed",
                    "message": str(exc),
                },
            ) from exc
        return _state_response(call)

    @router.post("/{call_id}/turn/stream-live")
    def create_videocall_turn(
        call_id: str,
        request: VideoCallTurnRequest,
    ) -> StreamingResponse:
        try:
            call, observation = registry.finish_speech(
                call_id,
                request.utterance_id,
            )
        except KeyError as exc:
            raise _call_not_found(call_id) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "videocall.state_conflict",
                    "message": str(exc),
                },
            ) from exc
        except Exception as exc:
            registry.turn_completed(call_id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "videocall.camera_finalize_failed",
                    "message": str(exc),
                },
            ) from exc

        receipt, provider_parts = package_camera_observation(observation)
        try:
            prepared = prepare_native_turn(
                settings=settings,
                engine=engine,
                session_id=call.session_id,
                message=request.transcript,
                system_override=None,
                requested_max_tokens=request.max_tokens,
                stream=True,
                transient_user_content_parts=provider_parts,
                request_metadata={
                    "interaction_channel": "android_tapo_videocall",
                    "provider_transport": "minimax_responses",
                    "perception_receipt": receipt,
                    "transient_media": True,
                },
                live_perception_capture=(
                    lambda runtime_settings, seconds: capture_camera_observation(
                        runtime_settings,
                        seconds=seconds,
                    )
                ),
            )
        except NativeTurnFailure as exc:
            registry.turn_completed(call_id)
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc

        with Session(engine) as db:
            record_event(
                db,
                session_id=call.session_id,
                turn_id=prepared.turn_id,
                event_type="perception.videocall.observation.attached",
                payload={
                    "call_id": call_id,
                    "utterance_id": request.utterance_id,
                    "observation": receipt,
                    "raw_media_persisted": False,
                },
                source="camera_perception",
                actor="backend",
                visibility="debug",
            )

        feed = LiveTurnFeed()

        def complete() -> None:
            registry.turn_completed(call_id)
            feed.finish()

        start_native_turn_runner(
            settings=settings,
            engine=engine,
            provider_factory=provider_factory,
            prepared=prepared,
            line_sink=feed.publish,
            completion_sink=complete,
        )
        return StreamingResponse(
            stream_live_turn_items(
                feed=feed,
                engine=engine,
                session_id=call.session_id,
                turn_id=prepared.turn_id,
            ),
            media_type="application/x-ndjson",
            headers={
                **LIVE_HEADERS,
                "X-Scarlet-Turn-ID": prepared.turn_id,
                "X-Scarlet-VideoCall-ID": call_id,
            },
        )

    @router.post("/{call_id}/stop", response_model=VideoCallStateResponse)
    def stop_call(call_id: str) -> VideoCallStateResponse:
        try:
            return _state_response(registry.stop(call_id))
        except KeyError as exc:
            raise _call_not_found(call_id) from exc

    return router


def _require_enabled(settings: Settings) -> None:
    if not settings.interactive_videocall_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "videocall.disabled",
                "message": "Interactive videocall experimentation is disabled.",
            },
        )
    if not settings.camera_perception_enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "videocall.camera_disabled",
                "message": "The camera perception source is disabled.",
            },
        )


def _state_response(call: _VideoCall) -> VideoCallStateResponse:
    return VideoCallStateResponse(
        call_id=call.id,
        session_id=call.session_id,
        state=call.state,
        source_id=call.source_id,
        started_at=call.started_at.isoformat(),
        utterance_id=call.utterance_id,
    )


def _call_not_found(call_id: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "videocall.not_found",
            "message": f"Videocall {call_id} was not found or already stopped.",
        },
    )

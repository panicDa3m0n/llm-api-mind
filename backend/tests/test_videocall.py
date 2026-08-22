import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMMessage, LLMStreamEvent, LLMTextResult
from app.main import create_app
from app.storage import repositories


class VideoCallProvider:
    seen_messages: list[list[LLMMessage]] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(self, *, prompt, system=None, max_tokens=None):
        return LLMTextResult(model="MiniMax-M3", text=prompt, stop_reason="end_turn")

    def generate_chat(self, *, messages, system=None, max_tokens=None):
        return LLMTextResult(
            model="MiniMax-M3",
            text="Ti vedo.",
            stop_reason="end_turn",
            raw_content=[{"type": "text", "text": "Ti vedo."}],
        )

    def generate_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner,
        max_tool_calls=None,
    ):
        return self.generate_chat(messages=messages, system=system, max_tokens=max_tokens)

    def stream_chat_with_tools(
        self,
        *,
        messages,
        system=None,
        max_tokens=None,
        tools,
        tool_runner,
        max_tool_calls=None,
    ):
        self.__class__.seen_messages.append(messages)
        result = self.generate_chat(messages=messages, system=system, max_tokens=max_tokens)
        yield LLMStreamEvent(
            type="text_delta",
            data={"model_step": 1, "index": 0, "text": "Ti vedo."},
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={"model_step": 1, "index": 0, "text": "Ti vedo."},
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def test_videocall_aligns_speech_and_video_without_persisting_media(
    db_engine: Engine,
    tmp_path: Path,
) -> None:
    VideoCallProvider.seen_messages = []
    fixture = tmp_path / "camera.mp4"
    fixture.write_bytes(b"transient-video-fixture")
    settings = Settings(
        agent_system_prompt="You are Scarlet.",
        camera_perception_enabled=True,
        camera_perception_source="file",
        camera_perception_file_path=str(fixture),
        interactive_videocall_enabled=True,
        maintenance_enabled=False,
        autonomous_activation_enabled=False,
    )
    client = TestClient(
        create_app(
            settings=settings,
            llm_provider_factory=VideoCallProvider,
            multimodal_provider_factory=VideoCallProvider,
            db_engine=db_engine,
        )
    )
    session = client.post("/api/chat/sessions", json={}).json()
    started = client.post(
        "/api/perception/videocall/start",
        json={"session_id": session["id"]},
    ).json()
    call_id = started["call_id"]
    utterance_id = "utterance-test-1"

    speech = client.post(
        f"/api/perception/videocall/{call_id}/speech-start",
        json={"utterance_id": utterance_id},
    )
    assert speech.status_code == 200
    assert speech.json()["state"] == "USER_SPEAKING"

    with client.stream(
        "POST",
        f"/api/perception/videocall/{call_id}/turn/stream-live",
        json={
            "utterance_id": utterance_id,
            "transcript": "Scarlet, cosa vedi davanti a te?",
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["x-scarlet-stream-schema"] == "scarlet-live-v1"
        items = [json.loads(line) for line in response.iter_lines() if line]

    assert any(
        item.get("event", {}).get("event_type") == "turn.completed"
        for item in items
        if item["kind"] == "event"
    )
    provider_message = VideoCallProvider.seen_messages[0][-1]
    assert isinstance(provider_message.content, list)
    assert [part["type"] for part in provider_message.content] == [
        "input_text",
        "input_text",
        "input_video",
    ]
    media_url = provider_message.content[-1]["video_url"]["url"]
    assert media_url.startswith("data:video/mp4;base64,")

    messages = client.get(
        f"/api/chat/sessions/{session['id']}/messages"
    ).json()
    assert [message["content"] for message in messages] == [
        "Scarlet, cosa vedi davanti a te?",
        "Ti vedo.",
    ]
    traces = client.get(
        f"/api/debug/traces/{response.headers['x-scarlet-turn-id']}"
    ).json()
    serialized_traces = json.dumps(traces)
    assert media_url not in serialized_traces
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    receipt = request_trace["payload"]["perception_receipt"]
    assert receipt["media_bytes"] == len(b"transient-video-fixture")
    assert len(receipt["sha256"]) == 64

    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        assert media_url not in json.dumps(stored_session.provider_history_json)

    stopped = client.post(
        f"/api/perception/videocall/{call_id}/stop"
    )
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "STOPPED"


def test_videocall_rejects_turn_without_speech_window(
    db_engine: Engine,
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "camera.mp4"
    fixture.write_bytes(b"fixture")
    settings = Settings(
        agent_system_prompt="You are Scarlet.",
        camera_perception_enabled=True,
        camera_perception_source="file",
        camera_perception_file_path=str(fixture),
        interactive_videocall_enabled=True,
        maintenance_enabled=False,
        autonomous_activation_enabled=False,
    )
    client = TestClient(
        create_app(
            settings=settings,
            llm_provider_factory=VideoCallProvider,
            db_engine=db_engine,
        )
    )
    session = client.post("/api/chat/sessions", json={}).json()
    call_id = client.post(
        "/api/perception/videocall/start",
        json={"session_id": session["id"]},
    ).json()["call_id"]

    response = client.post(
        f"/api/perception/videocall/{call_id}/turn/stream-live",
        json={"utterance_id": "missing", "transcript": "Ciao"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "videocall.state_conflict"

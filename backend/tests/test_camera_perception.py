from pathlib import Path

from sqlalchemy import create_engine

from app.config import Settings
from app.mind.contracts import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.plugins.camera_perception import capture_camera_observation
from app.plugins.camera_perception.sources import _sanitize_capture_error


def _context(settings: Settings) -> MindAPIContext:
    return MindAPIContext(
        engine=create_engine("sqlite://"),
        session_id="ses_camera_test",
        turn_id="turn_camera_test",
        source_message_id="msg_camera_test",
        settings=settings,
        live_perception_capture=(
            lambda runtime_settings, seconds: capture_camera_observation(
                runtime_settings,
                seconds=seconds,
            )
        ),
    )


def test_perception_look_attaches_media_without_serializing_it(tmp_path: Path) -> None:
    fixture = tmp_path / "camera.mp4"
    fixture.write_bytes(b"bounded-camera-fixture")
    settings = Settings(
        camera_perception_enabled=True,
        camera_perception_source="file",
        camera_perception_file_path=str(fixture),
    )

    response = dispatch_mind_shell(
        MindShellRequest(
            command="perception look --source camera --seconds 2",
            intent="Inspect the current camera window.",
        ),
        context=_context(settings),
    )

    assert response.ok is True
    data = response.result["data"]
    assert data["operation"] == "perception.look"
    assert data["observation"]["source_kind"] == "bounded_file_fixture"
    assert data["observation"]["persistence"] == {
        "memory_written": False,
        "automatic_context_written": False,
        "perception_event_written": False,
    }
    assert [part["type"] for part in response.provider_content_parts] == [
        "input_text",
        "input_video",
    ]
    media_url = response.provider_content_parts[1]["video_url"]["url"]
    assert media_url.startswith("data:video/mp4;base64,")
    assert "provider_content_parts" not in response.model_dump(mode="json")
    assert media_url not in str(response.model_dump(mode="json"))


def test_perception_look_fails_closed_when_experiment_is_disabled() -> None:
    response = dispatch_mind_shell(
        MindShellRequest(command="perception look --source camera --seconds 2"),
        context=_context(Settings(camera_perception_enabled=False)),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "perception.camera_capture_failed"
    assert response.provider_content_parts == []


def test_perception_look_requires_a_compatible_provider_composition() -> None:
    settings = Settings(camera_perception_enabled=True)
    context = MindAPIContext(
        engine=create_engine("sqlite://"),
        session_id="ses_camera_test",
        turn_id="turn_camera_test",
        source_message_id="msg_camera_test",
        settings=settings,
    )

    response = dispatch_mind_shell(
        MindShellRequest(command="perception look --source camera --seconds 2"),
        context=context,
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == "perception.live_source_unavailable"
    assert response.provider_content_parts == []


def test_rtsp_capture_errors_redact_credentials() -> None:
    url = "rtsp://camera-user:camera-secret@192.0.2.2:554/stream2"
    sanitized = _sanitize_capture_error(
        f"Unable to open {url}; fallback rtsp://other:secret@192.0.2.2/stream1",
        url,
    )

    assert "camera-user" not in sanitized
    assert "camera-secret" not in sanitized
    assert "other:secret" not in sanitized
    assert "redacted" in sanitized

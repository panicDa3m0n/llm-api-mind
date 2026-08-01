"""Bounded file and RTSP sources for the camera perception experiment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

from app.config import Settings
from app.mind.contracts import LivePerceptionError
from app.plugins.camera_perception.contracts import CameraObservation


class CameraCaptureError(LivePerceptionError):
    """Raised when a bounded camera observation cannot be captured."""


def capture_from_settings(
    settings: Settings,
    *,
    seconds: float,
) -> CameraObservation:
    if not settings.camera_perception_enabled:
        raise CameraCaptureError("Interactive camera perception is disabled.")
    bounded_seconds = min(seconds, settings.camera_perception_max_window_seconds)
    if bounded_seconds < 0.5:
        raise CameraCaptureError("Camera observation windows must be at least 0.5s.")
    if settings.camera_perception_source == "file":
        return _capture_file(settings, seconds=bounded_seconds)
    return _capture_rtsp(settings, seconds=bounded_seconds)


def _capture_file(settings: Settings, *, seconds: float) -> CameraObservation:
    raw_path = settings.camera_perception_file_path
    if not raw_path:
        raise CameraCaptureError("CAMERA_PERCEPTION_FILE_PATH is not configured.")
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        raise CameraCaptureError(f"Configured camera fixture does not exist: {path}")
    observed_to = datetime.now(timezone.utc)
    return CameraObservation(
        source_id="camera-fixture",
        source_kind="bounded_file_fixture",
        observed_from=observed_to - timedelta(seconds=seconds),
        observed_to=observed_to,
        mime_type=_video_mime_type(path),
        media_bytes=_read_bounded(path, settings.camera_perception_max_media_bytes),
        capture_metadata={
            "fixture_name": path.name,
            "requested_window_seconds": seconds,
        },
    )


def _capture_rtsp(settings: Settings, *, seconds: float) -> CameraObservation:
    host = (settings.camera_perception_host or "").strip()
    username = settings.camera_perception_username or ""
    password = settings.camera_perception_password or ""
    if not host or not username or not password:
        raise CameraCaptureError(
            "RTSP camera host and camera-account credentials are not configured."
        )
    stream_url = (
        f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@"
        f"{host}:{settings.camera_perception_port}/{settings.camera_perception_stream}"
    )
    observed_from = datetime.now(timezone.utc)
    output_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="scarlet-camera-",
            suffix=".mp4",
            delete=False,
        ) as handle:
            output_path = Path(handle.name)
        command = [
            settings.camera_perception_ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-i",
            stream_url,
            "-t",
            f"{seconds:.3f}",
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-y",
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=seconds + 15.0,
            check=False,
        )
        if completed.returncode != 0:
            detail = _sanitize_capture_error(completed.stderr, stream_url)
            raise CameraCaptureError(f"RTSP capture failed: {detail}")
        media_bytes = _read_bounded(
            output_path,
            settings.camera_perception_max_media_bytes,
        )
        observed_to = datetime.now(timezone.utc)
        return CameraObservation(
            source_id=settings.camera_perception_source_id,
            source_kind="rtsp_live_window",
            observed_from=observed_from,
            observed_to=observed_to,
            mime_type="video/mp4",
            media_bytes=media_bytes,
            capture_metadata={
                "host": host,
                "port": settings.camera_perception_port,
                "stream": settings.camera_perception_stream,
                "requested_window_seconds": seconds,
            },
        )
    except FileNotFoundError as exc:
        raise CameraCaptureError(
            f"Camera capture executable not found: {settings.camera_perception_ffmpeg_path}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise CameraCaptureError("RTSP capture timed out.") from exc
    finally:
        if output_path is not None:
            output_path.unlink(missing_ok=True)


def _read_bounded(path: Path, maximum_bytes: int) -> bytes:
    size = path.stat().st_size
    if size <= 0:
        raise CameraCaptureError("Camera capture produced an empty media file.")
    if size > maximum_bytes:
        raise CameraCaptureError(
            f"Camera media exceeds the configured limit ({size} > {maximum_bytes})."
        )
    return path.read_bytes()


def _video_mime_type(path: Path) -> str:
    return {
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".mov": "video/quicktime",
        ".mp4": "video/mp4",
    }.get(path.suffix.casefold(), "application/octet-stream")


def _sanitize_capture_error(message: str, stream_url: str) -> str:
    compact = " ".join(message.strip().split())
    sanitized = (compact or "unknown ffmpeg error").replace(
        stream_url,
        "<redacted-rtsp-url>",
    )
    sanitized = re.sub(
        r"rtsp://[^@\s]+@",
        "rtsp://<redacted>@",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized[:500]

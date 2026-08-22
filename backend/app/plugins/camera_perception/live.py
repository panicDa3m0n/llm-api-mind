"""Speech-aligned camera windows for the interactive videocall experiment."""

from __future__ import annotations

import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from app.config import Settings
from app.plugins.camera_perception.contracts import CameraObservation
from app.plugins.camera_perception.sources import (
    CameraCaptureError,
    _read_bounded,
    _sanitize_capture_error,
    capture_from_settings,
)


class SpeechAlignedCameraCapture:
    """Capture the visual interval that overlaps one recognized utterance."""

    def __init__(self, settings: Settings) -> None:
        if not settings.camera_perception_enabled:
            raise CameraCaptureError("Interactive camera perception is disabled.")
        self._settings = settings
        self._started_at = datetime.now(timezone.utc)
        self._started_monotonic = time.monotonic()
        self._process: subprocess.Popen[str] | None = None
        self._output_path: Path | None = None
        self._stream_url: str | None = None
        self._closed = False
        if settings.camera_perception_source == "rtsp":
            self._start_rtsp()

    @property
    def started_at(self) -> datetime:
        return self._started_at

    def finish(self) -> CameraObservation:
        if self._closed:
            raise CameraCaptureError("The camera window is already closed.")
        elapsed = time.monotonic() - self._started_monotonic
        maximum = self._settings.camera_perception_max_window_seconds
        if elapsed > maximum:
            self.abort()
            raise CameraCaptureError(
                f"Speech window exceeded the configured {maximum:.1f}s limit."
            )
        if elapsed < 0.5:
            time.sleep(0.5 - elapsed)
            elapsed = 0.5
        if self._settings.camera_perception_source == "file":
            self._closed = True
            return capture_from_settings(self._settings, seconds=elapsed)
        return self._finish_rtsp(elapsed)

    def abort(self) -> None:
        if self._closed:
            return
        self._closed = True
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3.0)
        if self._output_path is not None:
            self._output_path.unlink(missing_ok=True)

    def _start_rtsp(self) -> None:
        settings = self._settings
        host = (settings.camera_perception_host or "").strip()
        username = settings.camera_perception_username or ""
        password = settings.camera_perception_password or ""
        if not host or not username or not password:
            raise CameraCaptureError(
                "RTSP camera host and camera-account credentials are not configured."
            )
        stream_url = (
            f"rtsp://{quote(username, safe='')}:{quote(password, safe='')}@"
            f"{host}:{settings.camera_perception_port}/"
            f"{settings.camera_perception_stream}"
        )
        self._stream_url = stream_url
        with tempfile.NamedTemporaryFile(
            prefix="scarlet-videocall-",
            suffix=".mp4",
            delete=False,
        ) as handle:
            self._output_path = Path(handle.name)
        command = [
            settings.camera_perception_ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostats",
            "-rtsp_transport",
            "tcp",
            "-i",
            stream_url,
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
            str(self._output_path),
        ]
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            self._cleanup_output()
            raise CameraCaptureError(
                f"Camera capture executable not found: "
                f"{settings.camera_perception_ffmpeg_path}"
            ) from exc
        time.sleep(0.15)
        if self._process.poll() is not None:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            self._cleanup_output()
            raise CameraCaptureError(
                "RTSP capture failed: "
                + _sanitize_capture_error(stderr, stream_url)
            )

    def _finish_rtsp(self, elapsed: float) -> CameraObservation:
        process = self._process
        output_path = self._output_path
        if process is None or output_path is None:
            raise CameraCaptureError("RTSP capture process is unavailable.")
        try:
            _, stderr = process.communicate(input="q\n", timeout=15.0)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.communicate()
            self._cleanup_output()
            self._closed = True
            raise CameraCaptureError("RTSP capture finalization timed out.") from exc
        self._closed = True
        if process.returncode != 0:
            detail = _sanitize_capture_error(stderr, self._stream_url or "<rtsp>")
            self._cleanup_output()
            raise CameraCaptureError(f"RTSP capture failed: {detail}")
        try:
            media_bytes = _read_bounded(
                output_path,
                self._settings.camera_perception_max_media_bytes,
            )
        finally:
            self._cleanup_output()
        observed_to = datetime.now(timezone.utc)
        return CameraObservation(
            source_id=self._settings.camera_perception_source_id,
            source_kind="rtsp_speech_aligned_window",
            observed_from=self._started_at,
            observed_to=observed_to,
            mime_type="video/mp4",
            media_bytes=media_bytes,
            capture_metadata={
                "host": self._settings.camera_perception_host,
                "port": self._settings.camera_perception_port,
                "stream": self._settings.camera_perception_stream,
                "alignment": "android_speech_started_to_final_transcript",
                "measured_window_seconds": elapsed,
            },
        )

    def _cleanup_output(self) -> None:
        if self._output_path is not None:
            self._output_path.unlink(missing_ok=True)
            self._output_path = None

"""Prepare one camera observation for a multimodal provider continuation."""

from __future__ import annotations

import base64
from typing import Any

from app.config import Settings
from app.plugins.camera_perception.sources import capture_from_settings


def capture_camera_observation(
    settings: Settings,
    *,
    seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observation = capture_from_settings(settings, seconds=seconds)
    metadata = {
        "source_id": observation.source_id,
        "source_kind": observation.source_kind,
        "observed_from": observation.observed_from.isoformat(),
        "observed_to": observation.observed_to.isoformat(),
        "duration_seconds": observation.duration_seconds,
        "freshness": "current_bounded_observation",
        "mime_type": observation.mime_type,
        "media_bytes": len(observation.media_bytes),
        "capture": observation.capture_metadata,
        "persistence": {
            "memory_written": False,
            "automatic_context_written": False,
            "perception_event_written": False,
        },
    }
    data_url = (
        f"data:{observation.mime_type};base64,"
        + base64.b64encode(observation.media_bytes).decode("ascii")
    )
    provider_parts: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": (
                "Direct bounded camera observation. It is current perceptual "
                "evidence, not memory. System interval: "
                f"{metadata['observed_from']} to {metadata['observed_to']}."
            ),
        },
        {
            "type": "input_video",
            "video_url": {
                "url": data_url,
                "fps": 2,
                "detail": "high",
                "max_long_side_pixel": 672,
            },
        },
    ]
    return metadata, provider_parts

"""Transport-neutral contracts for one bounded camera observation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CameraObservation:
    source_id: str
    source_kind: str
    observed_from: datetime
    observed_to: datetime
    mime_type: str
    media_bytes: bytes
    capture_metadata: dict[str, Any]

    @property
    def duration_seconds(self) -> float:
        return max(0.0, (self.observed_to - self.observed_from).total_seconds())

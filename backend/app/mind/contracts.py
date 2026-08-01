"""Shared internal contracts for API Mind handlers.

These types intentionally live outside a specific organ. Memory, episodic
recall, focus, volition, affect, and metacognition all need the same traced
runtime context and normalized operation result, but none should depend on the
memory implementation merely to import them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import json
from typing import Any

from sqlalchemy.engine import Engine


LivePerceptionCapture = Callable[
    [Any, float],
    tuple[dict[str, Any], list[dict[str, Any]]],
]


class LivePerceptionError(RuntimeError):
    """A bounded external perception source could not supply evidence."""


@dataclass(frozen=True)
class MindAPIContext:
    """Traceable backend state available to one cognitive operation."""

    engine: Engine
    session_id: str | None = None
    turn_id: str | None = None
    source_message_id: str | None = None
    runtime_trigger: str = "human_message"
    settings: Any | None = None
    provider_factory: Callable[[Any], Any] | None = None
    live_perception_capture: LivePerceptionCapture | None = None


@dataclass(frozen=True)
class MemoryOperationResult:
    """Handler-level result normalized by the endpoint or shell dispatcher."""

    ok: bool
    result: dict[str, Any] = field(default_factory=dict)
    cognitive_hint: str | None = None
    suggested_next_actions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    error_code: str | None = None
    error_message: str | None = None
    error_recoverable: bool = True
    provider_content_parts: list[dict[str, Any]] = field(default_factory=list)


def serializable_validation_errors(exc: Any) -> list[dict[str, Any]]:
    """Return Pydantic validation details without live exception objects."""

    return json.loads(
        exc.json(
            include_url=False,
            include_context=False,
            include_input=True,
        )
    )

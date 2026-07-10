"""Shared internal contracts for API Mind handlers.

These types intentionally live outside a specific organ. Memory, episodic
recall, focus, volition, affect, and metacognition all need the same traced
runtime context and normalized operation result, but none should depend on the
memory implementation merely to import them.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.engine import Engine


@dataclass(frozen=True)
class MindAPIContext:
    """Traceable backend state available to one cognitive operation."""

    engine: Engine
    session_id: str | None = None
    turn_id: str | None = None
    settings: Any | None = None
    provider_factory: Callable[[Any], Any] | None = None


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

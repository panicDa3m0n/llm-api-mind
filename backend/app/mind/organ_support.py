"""Small shared transport helpers for profile-scoped cognitive organs."""

from __future__ import annotations

from typing import Any

from app.mind.contracts import MindAPIContext, MemoryOperationResult


def active_owner_profile_id(context: MindAPIContext) -> str:
    """Resolve the active profile consistently across profile-scoped organs."""

    return str(getattr(context.settings, "user_profile_id", None) or "local-user")


def recoverable_organ_error(
    operation: str,
    *,
    code: str,
    message: str,
    hint: str,
    actions: list[str],
    result: dict[str, Any] | None = None,
) -> MemoryOperationResult:
    """Build the shared model-facing error envelope for cognitive organs."""

    return MemoryOperationResult(
        ok=False,
        result=result or {"operation": operation},
        cognitive_hint=hint,
        suggested_next_actions=actions,
        confidence=1.0,
        error_code=code,
        error_message=message,
        error_recoverable=True,
    )

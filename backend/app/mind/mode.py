"""Mind handler for Scarlet's agent-only operating mode."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from app.mind.agent_modes import (
    AGENT_MODE_VALUES,
    agent_mode_registry,
    resolve_agent_mode,
    set_preferred_agent_mode,
)
from app.mind.contracts import MindAPIContext, MemoryOperationResult
from app.runtime.events import record_event
from app.storage import repositories


class AgentModeRequest(BaseModel):
    action: Literal["read", "list", "set"] = "read"
    mode: str | None = None
    reason: str | None = Field(default=None, max_length=1000)


def handle_agent_mode(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if (
        context is None
        or context.settings is None
        or context.session_id is None
    ):
        return _error(
            "mode.context_required",
            "Agent mode needs an active API Mind context.",
            ["Use mode read inside a Scarlet turn."],
        )
    try:
        request = AgentModeRequest.model_validate(body)
    except ValidationError as exc:
        return _error(
            "mode.invalid_request",
            "Agent mode request is invalid.",
            ["mode read", 'mode set scouting --reason "..."'],
            details={"validation": exc.errors(include_url=False)},
        )
    profile_id = str(context.settings.user_profile_id)
    default = str(context.settings.agent_mode_default)
    with Session(context.engine) as db:
        if request.action == "list":
            return MemoryOperationResult(
                ok=True,
                result={"operation": "mode.list", "registry": agent_mode_registry()},
                cognitive_hint="Modes are Scarlet agent postures, not backend process states.",
            )
        if request.action == "read":
            state = resolve_agent_mode(
                db,
                profile_id=profile_id,
                default=default,
                system_mode="interactive" if context.turn_id else None,
                system_reason="A human-facing turn is active." if context.turn_id else None,
            )
            return MemoryOperationResult(
                ok=True,
                result={"operation": "mode.read", "agent_mode": state},
                cognitive_hint="The system-enforced interactive mode applies only to the active human turn.",
            )
        if request.mode not in AGENT_MODE_VALUES or not request.reason:
            return _error(
                "mode.set_missing_fields",
                "mode set requires a supported mode and a reason.",
                ['mode set idle --reason "..."', 'mode set scouting --reason "..."'],
                details={"supported_modes": list(AGENT_MODE_VALUES)},
            )
        changed = set_preferred_agent_mode(
            db,
            profile_id=profile_id,
            mode=request.mode,
            reason=request.reason,
        )
        trace = repositories.add_trace(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            kind="agent.mode",
            payload={
                "operation": "mode.set",
                "profile_id": profile_id,
                "change": changed,
                "intent": intent,
            },
        )
        record_event(
            db,
            session_id=context.session_id,
            turn_id=context.turn_id,
            event_type="agent.mode.changed",
            payload={"change": changed, "intent": intent},
            source="agent_mode",
            actor="scarlet",
            visibility="debug",
            trace_id=trace.id,
        )
        active = resolve_agent_mode(
            db,
            profile_id=profile_id,
            default=default,
            system_mode="interactive" if context.turn_id else None,
            system_reason="A human-facing turn is active." if context.turn_id else None,
        )
        return MemoryOperationResult(
            ok=True,
            result={
                "operation": "mode.set",
                "change": changed,
                "agent_mode": active,
                "execution_started": False,
                "runtime_effect": "persistent_posture_only_no_autonomous_cycle",
                "trace_id": trace.id,
            },
            cognitive_hint=(
                "The selected mode is persistent. During this human turn, interactive "
                "remains active and the selected mode resumes afterward. This changes "
                "posture state only; it does not start an autonomous cycle. Scouting is "
                "currently registered without autonomous sensor runtime."
                if request.mode == "scouting"
                else "The selected mode is persistent. During this human turn, interactive "
                "remains active and the selected mode resumes afterward. This changes "
                "posture state only; it does not start an autonomous cycle."
            ),
        )


def _error(
    code: str,
    message: str,
    actions: list[str],
    *,
    details: dict[str, Any] | None = None,
) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        result={"operation": "mode.error", "details": details or {}},
        cognitive_hint="Correct the mode command only if changing Scarlet's operating posture is useful.",
        suggested_next_actions=actions,
        error_code=code,
        error_message=message,
    )

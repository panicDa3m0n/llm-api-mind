"""Agent-only operating modes and capability tagging.

Modes describe Scarlet's foreground operating posture. They do not represent
backend maintenance, Dream, or other background processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.storage import repositories


AGENT_MODE_REGISTRY_VERSION = "2026-07-13.agent-modes-v1"
AGENT_MODE_SETTING_PREFIX = "agent_mode"
AGENT_MODE_VALUES = ("idle", "interactive", "scouting")


@dataclass(frozen=True)
class AgentModeSpec:
    tag: str
    purpose: str
    implemented_runtime: bool


@dataclass(frozen=True)
class ModeCapabilitySpec:
    capability: str
    kind: str
    mode_tags: tuple[str, ...]
    status: str
    context_block_type: str | None = None
    notes: str = ""


AGENT_MODES: tuple[AgentModeSpec, ...] = (
    AgentModeSpec(
        tag="idle",
        purpose="Scarlet is available and active but not currently engaged in a task or human exchange.",
        implemented_runtime=True,
    ),
    AgentModeSpec(
        tag="interactive",
        purpose="Scarlet is communicating with one or more humans and prioritizes that exchange.",
        implemented_runtime=True,
    ),
    AgentModeSpec(
        tag="scouting",
        purpose="Scarlet studies an environment or information field with exploratory attention.",
        implemented_runtime=False,
    ),
)


MODE_CAPABILITIES: tuple[ModeCapabilitySpec, ...] = (
    ModeCapabilitySpec(
        capability="context.agent_mode",
        kind="context",
        mode_tags=AGENT_MODE_VALUES,
        status="implemented",
        context_block_type="agent_mode_context",
    ),
    ModeCapabilitySpec(
        capability="context.session_spine",
        kind="context",
        mode_tags=AGENT_MODE_VALUES,
        status="implemented",
        context_block_type="session_context",
    ),
    ModeCapabilitySpec(
        capability="context.turn_perception",
        kind="context",
        mode_tags=("interactive", "scouting"),
        status="implemented",
        context_block_type="message_context",
    ),
    ModeCapabilitySpec(
        capability="context.scarlet_state",
        kind="context",
        mode_tags=AGENT_MODE_VALUES,
        status="implemented",
        context_block_type="scarlet_state",
    ),
    ModeCapabilitySpec(
        capability="continuity.provider_history",
        kind="continuity",
        mode_tags=("interactive",),
        status="implemented",
    ),
    ModeCapabilitySpec(
        capability="cognition.mind_shell",
        kind="capability",
        mode_tags=AGENT_MODE_VALUES,
        status="implemented",
    ),
    ModeCapabilitySpec(
        capability="organ.focus",
        kind="organ",
        mode_tags=AGENT_MODE_VALUES,
        status="implemented_config_gated",
        context_block_type="focus_context",
    ),
    ModeCapabilitySpec(
        capability="organ.volition",
        kind="organ",
        mode_tags=("idle", "scouting"),
        status="implemented_manual_only",
        context_block_type="volition_context",
    ),
    ModeCapabilitySpec(
        capability="organ.affect",
        kind="organ",
        mode_tags=("interactive", "scouting"),
        status="implemented_config_gated",
        context_block_type="affective_context",
    ),
    ModeCapabilitySpec(
        capability="organ.metacognition",
        kind="organ",
        mode_tags=("interactive", "scouting"),
        status="implemented_on_demand",
        context_block_type="metacognitive_context",
    ),
    ModeCapabilitySpec(
        capability="future.environment_scouting",
        kind="capability",
        mode_tags=("scouting",),
        status="future_no_sensor_runtime",
    ),
)


def agent_mode_registry() -> dict[str, Any]:
    return {
        "registry_version": AGENT_MODE_REGISTRY_VERSION,
        "routing_scope": "automatic_model_context_v1",
        "on_demand_shell_commands_remain_available": True,
        "modes": [
            {
                "tag": mode.tag,
                "purpose": mode.purpose,
                "implemented_runtime": mode.implemented_runtime,
            }
            for mode in AGENT_MODES
        ],
        "capabilities": [
            {
                "capability": spec.capability,
                "kind": spec.kind,
                "mode_tags": list(spec.mode_tags),
                "status": spec.status,
                "context_block_type": spec.context_block_type,
                "notes": spec.notes,
            }
            for spec in MODE_CAPABILITIES
        ],
        "background_processes_are_agent_modes": False,
    }


def preferred_agent_mode(
    db: Session,
    *,
    profile_id: str,
    default: str = "idle",
) -> dict[str, Any]:
    fallback = default if default in AGENT_MODE_VALUES else "idle"
    setting = repositories.get_app_setting(db, _setting_key(profile_id))
    if setting is None:
        return {
            "mode": fallback,
            "source": "configured_default",
            "reason": None,
            "updated_at": None,
        }
    stored = setting.value_json.get("value")
    payload = stored if isinstance(stored, dict) else {"mode": stored}
    mode = payload.get("mode")
    if mode not in AGENT_MODE_VALUES:
        mode = fallback
    return {
        "mode": mode,
        "source": payload.get("source") or "persistent_setting",
        "reason": payload.get("reason"),
        "updated_at": setting.updated_at.isoformat(),
    }


def resolve_agent_mode(
    db: Session,
    *,
    profile_id: str,
    default: str = "idle",
    system_mode: str | None = None,
    system_reason: str | None = None,
) -> dict[str, Any]:
    preferred = preferred_agent_mode(db, profile_id=profile_id, default=default)
    active = system_mode if system_mode in AGENT_MODE_VALUES else preferred["mode"]
    source = "system_condition" if system_mode in AGENT_MODE_VALUES else preferred["source"]
    active_runtime = _mode_runtime_implemented(active)
    resume_mode = preferred["mode"] if system_mode in AGENT_MODE_VALUES else None
    return {
        "registry_version": AGENT_MODE_REGISTRY_VERSION,
        "active_tag": active,
        "source": source,
        "reason": system_reason if system_mode in AGENT_MODE_VALUES else preferred["reason"],
        "active_runtime_implemented": active_runtime,
        "resume_tag": resume_mode,
        "resume_runtime_implemented": (
            _mode_runtime_implemented(resume_mode) if resume_mode is not None else None
        ),
        "available_tags": list(AGENT_MODE_VALUES),
    }


def set_preferred_agent_mode(
    db: Session,
    *,
    profile_id: str,
    mode: str,
    reason: str,
) -> dict[str, Any]:
    if mode not in AGENT_MODE_VALUES:
        raise ValueError(f"Unsupported agent mode: {mode}")
    previous = preferred_agent_mode(db, profile_id=profile_id)
    setting = repositories.upsert_app_setting(
        db,
        key=_setting_key(profile_id),
        value={"mode": mode, "reason": reason, "source": "scarlet_manual"},
    )
    return {
        "previous_tag": previous["mode"],
        "preferred_tag": mode,
        "reason": reason,
        "source": "scarlet_manual",
        "updated_at": setting.updated_at.isoformat(),
    }


def mode_routing_decision(
    *,
    active_tag: str,
    routing_mode: str,
    block_types: list[str] | None = None,
) -> dict[str, Any]:
    eligible = [
        spec
        for spec in MODE_CAPABILITIES
        if active_tag in spec.mode_tags
    ]
    eligibility_by_block = {
        spec.context_block_type: spec
        for spec in MODE_CAPABILITIES
        if spec.context_block_type is not None
    }
    included_blocks: list[str] = []
    ineligible_blocks: list[str] = []
    for block_type in block_types or []:
        spec = eligibility_by_block.get(block_type)
        if spec is None or active_tag in spec.mode_tags:
            included_blocks.append(block_type)
        else:
            ineligible_blocks.append(block_type)
    return {
        "registry_version": AGENT_MODE_REGISTRY_VERSION,
        "active_tag": active_tag,
        "routing_mode": routing_mode,
        "eligible_capabilities": [spec.capability for spec in eligible],
        "included_block_types": included_blocks,
        "ineligible_block_types": ineligible_blocks,
        "background_processes_excluded": True,
    }


def route_context_blocks(
    blocks: list[dict[str, Any]],
    *,
    active_tag: str,
    routing_mode: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    decision = mode_routing_decision(
        active_tag=active_tag,
        routing_mode=routing_mode,
        block_types=[str(block.get("type") or "") for block in blocks],
    )
    if routing_mode != "active":
        return blocks, decision
    excluded = set(decision["ineligible_block_types"])
    return [block for block in blocks if block.get("type") not in excluded], decision


def _setting_key(profile_id: str) -> str:
    return f"{AGENT_MODE_SETTING_PREFIX}:{profile_id}"


def _mode_runtime_implemented(mode: str) -> bool:
    return next(
        (spec.implemented_runtime for spec in AGENT_MODES if spec.tag == mode),
        False,
    )

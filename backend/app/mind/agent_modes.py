"""Agent-only operating modes and capability tagging.

Modes describe Scarlet's foreground operating posture. They do not represent
backend maintenance, Dream, or other background processes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlmodel import Session

from app.storage import repositories


AGENT_MODE_REGISTRY_VERSION = "2026-07-27.agent-modes-routing-v3"
AGENT_MODE_SETTING_PREFIX = "agent_mode"
AGENT_MODE_VALUES = ("idle", "interactive", "scouting")
AGENT_MODE_RESUMABLE_VALUES = ("idle", "scouting")


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
        purpose=(
            "Scarlet is available but has no current task, human exchange, or "
            "exploratory direction to resume."
        ),
        implemented_runtime=True,
    ),
    AgentModeSpec(
        tag="interactive",
        purpose="Scarlet is communicating with one or more humans and prioritizes that exchange.",
        implemented_runtime=True,
    ),
    AgentModeSpec(
        tag="scouting",
        purpose=(
            "Scarlet keeps an exploratory orientation toward available "
            "environmental or information channels during autonomous cognition."
        ),
        implemented_runtime=True,
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
        mode_tags=AGENT_MODE_VALUES,
        status="implemented",
    ),
    ModeCapabilitySpec(
        capability="context.autonomous_activation",
        kind="context",
        mode_tags=("idle", "scouting"),
        status="implemented",
        context_block_type="autonomous_activation_context",
    ),
    ModeCapabilitySpec(
        capability="perception.availability_index",
        kind="context",
        mode_tags=("idle", "scouting"),
        status="implemented",
        context_block_type="perception_context",
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
        status="implemented_available_channels_only",
        notes=(
            "Scouting can inspect registered perception channels; continuous "
            "robotic sensors remain future work."
        ),
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
                "manually_resumable": mode.tag in AGENT_MODE_RESUMABLE_VALUES,
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
        "manually_resumable_tags": list(AGENT_MODE_RESUMABLE_VALUES),
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
    if mode not in AGENT_MODE_RESUMABLE_VALUES:
        raise ValueError(f"Agent mode is not resumable: {mode}")
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
    blocks: list[dict[str, Any]] | None = None,
    block_types: list[str] | None = None,
) -> dict[str, Any]:
    if active_tag not in AGENT_MODE_VALUES:
        raise ValueError(f"Unsupported active agent mode: {active_tag}")
    if routing_mode not in {"off", "shadow", "active"}:
        raise ValueError(f"Unsupported agent mode routing: {routing_mode}")

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
    routing_inputs = blocks or [
        {"id": None, "type": block_type}
        for block_type in block_types or []
    ]
    block_decisions = [
        _block_routing_decision(
            block=block,
            input_index=index,
            active_tag=active_tag,
            routing_mode=routing_mode,
            spec=eligibility_by_block.get(str(block.get("type") or "")),
        )
        for index, block in enumerate(routing_inputs)
    ]
    return {
        "registry_version": AGENT_MODE_REGISTRY_VERSION,
        "active_tag": active_tag,
        "routing_mode": routing_mode,
        "routing_applied": routing_mode == "active",
        "eligible_capabilities": [spec.capability for spec in eligible],
        "included_block_ids": [
            item["block_id"]
            for item in block_decisions
            if item["delivered"] and item["block_id"] is not None
        ],
        "included_block_types": [
            item["block_type"] for item in block_decisions if item["delivered"]
        ],
        "excluded_block_ids": [
            item["block_id"]
            for item in block_decisions
            if not item["delivered"] and item["block_id"] is not None
        ],
        "excluded_block_types": [
            item["block_type"] for item in block_decisions if not item["delivered"]
        ],
        "ineligible_block_types": [
            item["block_type"]
            for item in block_decisions
            if item["eligibility"] == "ineligible"
        ],
        "would_exclude_block_types": [
            item["block_type"]
            for item in block_decisions
            if item["delivery_disposition"] == "shadow_included"
        ],
        "unregistered_block_types": [
            item["block_type"]
            for item in block_decisions
            if item["eligibility"] == "unregistered"
        ],
        "block_decisions": block_decisions,
        "on_demand_shell_commands_remain_available": True,
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
        blocks=blocks,
    )
    routed = [
        block
        for block, block_decision in zip(
            blocks, decision["block_decisions"], strict=True
        )
        if block_decision["delivered"]
    ]
    return routed, decision


def _block_routing_decision(
    *,
    block: dict[str, Any],
    input_index: int,
    active_tag: str,
    routing_mode: str,
    spec: ModeCapabilitySpec | None,
) -> dict[str, Any]:
    block_id = block.get("id") if isinstance(block.get("id"), str) else None
    block_type = str(block.get("type") or "")

    if spec is None:
        eligibility = "unregistered"
        delivered = True
        delivery_disposition = "included_unregistered"
        reason = (
            "No registered mode capability owns this block type; it is delivered "
            "fail-open and reported for registry review."
        )
    else:
        eligible_for_mode = active_tag in spec.mode_tags
        eligibility = "eligible" if eligible_for_mode else "ineligible"
        if routing_mode == "active" and not eligible_for_mode:
            delivered = False
            delivery_disposition = "excluded"
            reason = (
                f"Active tag {active_tag!r} is not in the capability tags; active "
                "routing excludes this automatic block."
            )
        elif routing_mode == "shadow" and not eligible_for_mode:
            delivered = True
            delivery_disposition = "shadow_included"
            reason = (
                f"Active tag {active_tag!r} is not in the capability tags; shadow "
                "routing records the exclusion but still delivers the block."
            )
        elif routing_mode == "off":
            delivered = True
            delivery_disposition = "included_routing_off"
            reason = "Mode routing is disabled, so the block is delivered unchanged."
        else:
            delivered = True
            delivery_disposition = "included"
            reason = (
                f"Active tag {active_tag!r} matches the capability tags, so the "
                "automatic block is eligible and delivered."
            )

    return {
        "input_index": input_index,
        "block_id": block_id,
        "block_type": block_type,
        "capability": spec.capability if spec is not None else None,
        "capability_status": spec.status if spec is not None else None,
        "required_mode_tags": list(spec.mode_tags) if spec is not None else [],
        "eligibility": eligibility,
        "delivery_disposition": delivery_disposition,
        "delivered": delivered,
        "reason": reason,
    }


def _setting_key(profile_id: str) -> str:
    return f"{AGENT_MODE_SETTING_PREFIX}:{profile_id}"


def _mode_runtime_implemented(mode: str) -> bool:
    return next(
        (spec.implemented_runtime for spec in AGENT_MODES if spec.tag == mode),
        False,
    )

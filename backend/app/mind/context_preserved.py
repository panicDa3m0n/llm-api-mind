"""Field-level projection for dynamic context families preserved by V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.mind.context_time import render_user_time


PRESERVED_PROJECTION_VERSION = "preserved-context-projection-v1"


@dataclass(frozen=True)
class PreservedContextProjection:
    blocks: list[dict[str, Any]]
    audit: dict[str, Any]


@dataclass(frozen=True)
class _ModelFamily:
    family: str
    source_block_type: str
    cognitive_function: str
    on_demand: tuple[str, ...]
    projector: Callable[[dict[str, Any], str], dict[str, Any] | None]


_MODEL_FAMILIES = (
    _ModelFamily(
        family="focus_context",
        source_block_type="focus_context",
        cognitive_function="Current foreground attention with source navigation.",
        on_demand=("focus read", "focus timeline"),
        projector=lambda block, timezone_id: _project_focus(block, timezone_id),
    ),
    _ModelFamily(
        family="affective_context",
        source_block_type="affective_context",
        cognitive_function="Current appraised posture that may shape response style.",
        on_demand=("affect read", "affect list"),
        projector=lambda block, timezone_id: _project_affect(block),
    ),
    _ModelFamily(
        family="metacognitive_context",
        source_block_type="metacognitive_context",
        cognitive_function="Few trigger-matched operating lessons for this turn.",
        on_demand=("metacognition step",),
        projector=lambda block, timezone_id: _project_metacognition(block),
    ),
)


def project_preserved_context(
    legacy_runtime_payload: dict[str, Any],
    *,
    timezone_id: str,
) -> PreservedContextProjection:
    source_blocks = [
        block
        for block in legacy_runtime_payload.get("blocks", [])
        if isinstance(block, dict)
    ]
    blocks_by_type = {
        str(block.get("type")): block
        for block in source_blocks
        if isinstance(block.get("type"), str)
    }
    projected_blocks: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for spec in _MODEL_FAMILIES:
        source = blocks_by_type.get(spec.source_block_type)
        projected = spec.projector(source, timezone_id) if source is not None else None
        if projected is not None:
            projected_blocks.append(projected)
        decisions.append(
            _decision(
                family=spec.family,
                source_block_type=spec.source_block_type,
                source=source,
                projected=projected,
                disposition="automatic_model_conditional",
                cognitive_function=spec.cognitive_function,
                on_demand=spec.on_demand,
                reason=(
                    "Included through an explicit model-facing field allowlist."
                    if projected is not None
                    else "Source organ block was absent, inactive, or removed by mode routing."
                ),
            )
        )

    scarlet_state = blocks_by_type.get("scarlet_state")
    decisions.append(
        _decision(
            family="scarlet_state",
            source_block_type="scarlet_state",
            source=scarlet_state,
            projected=None,
            disposition="trace_ui_only",
            cognitive_function=(
                "Legacy seeded placeholders superseded by the current turn and dedicated organs."
            ),
            on_demand=("focus read", "affect read", "mode read"),
            reason="Excluded because it duplicates current input, policy, focus, and affect.",
        )
    )

    message_block = blocks_by_type.get("message_context")
    message_content = _content(message_block)
    decisions.extend(
        (
            _subfield_decision(
                family="recent_dialogue",
                message_block=message_block,
                message_content=message_content,
                source_key="recent_dialogue",
                disposition="trace_ui_only",
                cognitive_function="Same-session conversational continuity.",
                on_demand=("session open", "session message", "session turn"),
                reason="Excluded because provider-native history is the continuity source.",
            ),
            _subfield_decision(
                family="recent_runtime_events",
                message_block=message_block,
                message_content=message_content,
                source_key="recent_runtime_events",
                disposition="trace_ui_only",
                cognitive_function="Operational event diagnostics and recovery evidence.",
                on_demand=("session turn",),
                reason=(
                    "Excluded because generic event summaries are not a targeted, navigable "
                    "cognitive packet."
                ),
            ),
            _subfield_decision(
                family="api_mind",
                message_block=message_block,
                message_content=message_content,
                source_key="api_mind",
                disposition="on_demand",
                cognitive_function="Current cognitive command catalog and capability detail.",
                on_demand=("help", "help <family>"),
                reason=(
                    "Excluded from automatic context because the tool schema and help command "
                    "are the authoritative capability surfaces."
                ),
            ),
        )
    )

    included_types = [str(block["type"]) for block in projected_blocks]
    return PreservedContextProjection(
        blocks=projected_blocks,
        audit={
            "schema_version": PRESERVED_PROJECTION_VERSION,
            "policy": (
                "Only allowlisted fields with an immediate cognitive or navigation use reach "
                "the model; rich source data remains in runtime.context."
            ),
            "included_block_types": included_types,
            "families": decisions,
        },
    )


def _project_focus(block: dict[str, Any], timezone_id: str) -> dict[str, Any] | None:
    content = _content(block)
    current = content.get("current_focus")
    if not isinstance(current, dict):
        return None
    projected_focus = _copy_fields(
        current,
        (
            "id",
            "object",
            "type",
            "status",
            "intensity",
            "duration_policy",
            "reason",
            "source_session_id",
            "source_turn_id",
            "source_message_id",
        ),
    )
    for field in ("created_at", "updated_at"):
        value = current.get(field)
        if isinstance(value, str) and value:
            projected_focus[field] = _safe_user_time(value, timezone_id=timezone_id)
    return _project_block(block, {"current_focus": projected_focus})


def _project_affect(block: dict[str, Any]) -> dict[str, Any] | None:
    content = _content(block)
    if not isinstance(content.get("current_emotion"), str):
        return None
    projected = _copy_fields(
        content,
        (
            "state_id",
            "current_emotion",
            "intensity",
            "felt_quality",
            "activation",
            "valence",
            "persistence",
            "attention_tendency",
            "action_tendency",
            "relational_posture",
            "causes",
        ),
    )
    return _project_block(block, projected)


def _project_metacognition(block: dict[str, Any]) -> dict[str, Any] | None:
    content = _content(block)
    lessons = content.get("lessons")
    if not isinstance(lessons, list) or not lessons:
        return None
    projected_lessons = [
        _copy_fields(
            lesson,
            ("id", "title", "lesson", "recommended_action", "risk_if_overused"),
        )
        for lesson in lessons
        if isinstance(lesson, dict)
    ]
    if not projected_lessons:
        return None
    triggers = content.get("triggers")
    projected_triggers = (
        [
            _copy_fields(trigger, ("id",))
            for trigger in triggers
            if isinstance(trigger, dict)
        ]
        if isinstance(triggers, list)
        else []
    )
    return _project_block(
        block,
        {
            "triggers": projected_triggers,
            "lessons": projected_lessons,
        },
    )


def _project_block(
    source: dict[str, Any],
    content: dict[str, Any],
) -> dict[str, Any]:
    return {
        key: source[key]
        for key in ("id", "type", "scope", "lifetime", "source")
        if key in source
    } | {"content": content}


def _decision(
    *,
    family: str,
    source_block_type: str,
    source: dict[str, Any] | None,
    projected: dict[str, Any] | None,
    disposition: str,
    cognitive_function: str,
    on_demand: tuple[str, ...],
    reason: str,
) -> dict[str, Any]:
    source_fields = _field_paths(source) if source is not None else []
    model_fields = _field_paths(projected) if projected is not None else []
    return {
        "family": family,
        "source_block_type": source_block_type,
        "source_block_id": source.get("id") if source is not None else None,
        "source_present": source is not None,
        "disposition": disposition,
        "included_in_model": projected is not None,
        "cognitive_function": cognitive_function,
        "on_demand_commands": list(on_demand),
        "model_fields": model_fields,
        "excluded_source_fields": sorted(set(source_fields) - set(model_fields)),
        "reason": reason,
    }


def _subfield_decision(
    *,
    family: str,
    message_block: dict[str, Any] | None,
    message_content: dict[str, Any],
    source_key: str,
    disposition: str,
    cognitive_function: str,
    on_demand: tuple[str, ...],
    reason: str,
) -> dict[str, Any]:
    source_present = source_key in message_content
    source_value = message_content.get(source_key)
    source_fields = (
        _field_paths(source_value, prefix=f"content.{source_key}")
        if source_present
        else []
    )
    return {
        "family": family,
        "source_block_type": "message_context",
        "source_block_id": message_block.get("id") if message_block else None,
        "source_present": source_present,
        "disposition": disposition,
        "included_in_model": False,
        "cognitive_function": cognitive_function,
        "on_demand_commands": list(on_demand),
        "model_fields": [],
        "excluded_source_fields": source_fields,
        "reason": reason,
    }


def _content(block: dict[str, Any] | None) -> dict[str, Any]:
    if block is None:
        return {}
    content = block.get("content")
    return content if isinstance(content, dict) else {}


def _copy_fields(source: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: source[field] for field in fields if field in source}


def _safe_user_time(value: str, *, timezone_id: str) -> str:
    try:
        return render_user_time(value, timezone_id=timezone_id)
    except (TypeError, ValueError):
        return value


def _field_paths(value: Any, *, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        paths: set[str] = set()
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            paths.update(_field_paths(item, prefix=child))
        return sorted(paths)
    if isinstance(value, list):
        paths = {prefix}
        for item in value:
            if isinstance(item, dict):
                paths.update(_field_paths(item, prefix=f"{prefix}[]"))
        return sorted(path for path in paths if path)
    return [prefix] if prefix else []

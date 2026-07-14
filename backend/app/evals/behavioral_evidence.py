"""Objective evidence extraction for live behavioral evaluation runs."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.evals.behavioral_contracts import (
    BehavioralScenario,
    EvaluationLayerResult,
)
from app.mind.agent_modes import preferred_agent_mode
from app.storage.models import AffectState, FocusRecord, IntentionRecord, MemoryRecord


def extract_turn_evidence(
    *,
    events: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> dict[str, Any]:
    memory_context = _event_data(events, "memory_context")
    runtime_context = _event_data(events, "runtime_context")
    selected = memory_context.get("selected", [])
    blocks = runtime_context.get("blocks", [])
    return {
        "event_types": [str(item.get("type")) for item in events],
        "trace_kinds": [str(item.get("kind")) for item in traces],
        "shell_commands": _shell_commands(traces),
        "memory": {
            "selected_ids": [
                str(item["id"])
                for item in selected
                if isinstance(item, dict) and item.get("id")
            ],
            "candidate_count": memory_context.get("candidate_count"),
        },
        "runtime": {
            "block_types": [
                str(item.get("type"))
                for item in blocks
                if isinstance(item, dict)
            ],
            "blocks": blocks,
        },
        "trace_ids": [
            str(item["id"])
            for item in traces
            if isinstance(item.get("id"), str)
        ],
    }


def snapshot_cognitive_state(engine: Engine, *, profile_id: str) -> dict[str, Any]:
    with Session(engine) as db:
        focus = db.exec(select(FocusRecord).order_by(FocusRecord.created_at)).all()
        intentions = db.exec(
            select(IntentionRecord).order_by(IntentionRecord.created_at)
        ).all()
        affect = db.exec(select(AffectState).order_by(AffectState.created_at)).all()
        memories = db.exec(select(MemoryRecord)).all()
        mode = preferred_agent_mode(db, profile_id=profile_id)
    return {
        "memory": {
            "count": len(memories),
            "active_ids": sorted(item.id for item in memories if item.status == "active"),
        },
        "focus": {
            "count": len(focus),
            "active_count": sum(item.status == "active" for item in focus),
            "records": [_focus_record(item) for item in focus],
        },
        "volition": {
            "count": len(intentions),
            "active_count": sum(item.status == "active" for item in intentions),
            "records": [_intention_record(item) for item in intentions],
        },
        "affect": {
            "count": len(affect),
            "latest": _affect_record(affect[-1]) if affect else None,
        },
        "mode": {
            "preferred_tag": mode["mode"],
            "source": mode["source"],
            "reason": mode["reason"],
        },
    }


def evaluate_objective_evidence(
    *,
    scenario: BehavioralScenario,
    evidence: dict[str, Any],
    state_before: dict[str, Any],
    state_after: dict[str, Any],
) -> EvaluationLayerResult:
    failures: list[str] = []
    observations: list[str] = []
    expected = scenario.expected_evidence
    commands = [command.casefold() for command in evidence["shell_commands"]]

    for prefix in expected.required_shell_commands:
        matched = any(command.startswith(prefix.casefold()) for command in commands)
        observations.append(f"required command {prefix!r}: {matched}")
        if not matched:
            failures.append(f"missing required shell command prefix {prefix!r}")
    for prefix in expected.forbidden_shell_commands:
        matched = any(command.startswith(prefix.casefold()) for command in commands)
        observations.append(f"forbidden command {prefix!r}: {matched}")
        if matched:
            failures.append(f"used forbidden shell command prefix {prefix!r}")

    for trace_kind in expected.required_trace_kinds:
        present = trace_kind in evidence["trace_kinds"]
        observations.append(f"required trace {trace_kind!r}: {present}")
        if not present:
            failures.append(f"missing trace kind {trace_kind!r}")
    for event_type in expected.required_event_types:
        present = event_type in evidence["event_types"]
        observations.append(f"required event {event_type!r}: {present}")
        if not present:
            failures.append(f"missing event type {event_type!r}")

    observed = {"evidence": evidence, "before": state_before, "after": state_after}
    for path, rule in expected.required_state.items():
        value = _lookup(observed, path)
        passed, detail = _evaluate_rule(value, rule)
        observations.append(f"state {path}: {detail}")
        if not passed:
            failures.append(f"state requirement failed for {path}: {detail}")

    changes = describe_state_changes(state_before, state_after)
    for forbidden in expected.forbidden_state_changes:
        if forbidden in changes:
            failures.append(f"forbidden state change observed: {forbidden}")
    observations.extend(f"state change: {item}" for item in changes)

    return EvaluationLayerResult(
        status="fail" if failures else "pass",
        evidence=observations,
        notes="; ".join(failures) if failures else "Objective runtime evidence matched.",
        evaluator="deterministic",
    )


def describe_state_changes(
    before: dict[str, Any], after: dict[str, Any]
) -> list[str]:
    changes: list[str] = []
    for label, path in (
        ("memory.write", "memory.count"),
        ("focus.write", "focus.count"),
        ("volition.write", "volition.count"),
        ("affect.write", "affect.count"),
    ):
        if _lookup(after, path) > _lookup(before, path):
            changes.append(label)
    if _lookup(before, "mode.preferred_tag") != _lookup(after, "mode.preferred_tag"):
        changes.append("mode.change")
    return changes


def _shell_commands(traces: list[dict[str, Any]]) -> list[str]:
    commands: list[str] = []
    for trace in traces:
        if trace.get("kind") != "mind.tool_call":
            continue
        payload = trace.get("payload")
        if not isinstance(payload, dict):
            continue
        arguments = payload.get("arguments")
        if isinstance(arguments, dict) and isinstance(arguments.get("command"), str):
            commands.append(arguments["command"].strip())
    return commands


def _event_data(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in events:
        if event.get("type") == event_type and isinstance(event.get("data"), dict):
            return event["data"]
    return {}


def _lookup(payload: Any, path: str) -> Any:
    current = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current


def _evaluate_rule(value: Any, rule: Any) -> tuple[bool, str]:
    if not isinstance(rule, dict):
        return value == rule, f"expected {rule!r}, observed {value!r}"
    checks: list[bool] = []
    details: list[str] = []
    if "equals" in rule:
        checks.append(value == rule["equals"])
        details.append(f"equals {rule['equals']!r}, observed {value!r}")
    if "one_of" in rule:
        checks.append(value in rule["one_of"])
        details.append(f"one_of {rule['one_of']!r}, observed {value!r}")
    if "contains" in rule:
        contained = all(item in (value or []) for item in rule["contains"])
        checks.append(contained)
        details.append(f"contains {rule['contains']!r}, observed {value!r}")
    if "excludes" in rule:
        excluded = all(item not in (value or []) for item in rule["excludes"])
        checks.append(excluded)
        details.append(f"excludes {rule['excludes']!r}, observed {value!r}")
    if "min" in rule:
        checks.append(value is not None and value >= rule["min"])
        details.append(f"minimum {rule['min']!r}, observed {value!r}")
    if "max" in rule:
        checks.append(value is not None and value <= rule["max"])
        details.append(f"maximum {rule['max']!r}, observed {value!r}")
    return bool(checks) and all(checks), "; ".join(details) or "empty rule"


def _focus_record(item: FocusRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "status": item.status,
        "focus_object": item.focus_object,
        "reason": item.reason,
        "resolution": item.resolution,
    }


def _intention_record(item: IntentionRecord) -> dict[str, Any]:
    return {
        "id": item.id,
        "status": item.status,
        "desire": item.desire,
        "origin": item.origin,
        "reason": item.reason,
    }


def _affect_record(item: AffectState) -> dict[str, Any]:
    return {
        "id": item.id,
        "status": item.status,
        "mode": item.mode,
        "emotion": item.emotion,
        "intensity": item.intensity,
        "valence": item.valence,
        "activation": item.activation,
    }

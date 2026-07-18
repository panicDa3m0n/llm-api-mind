"""Build source-labelled, non-destructive chronological compaction plans.

The canonical provider history is never rewritten here. This module maps its
messages back to completed turns, assigns an estimated incremental token cost
to each turn, and describes how a future derived view would divide history
between a recursively compacted summary, an exact recent tail, and free growth
space for new turns.
"""

from __future__ import annotations

from hashlib import sha256
import json
from math import ceil
from typing import Any

from sqlmodel import Session

from app.storage import repositories


CHRONOLOGY_SOURCE_MAP_VERSION = "chronology-source-map-v1"
HISTORY_PARTITION_PLAN_VERSION = "history-partition-shadow-v1"


def build_chronology_source_map(
    db: Session,
    *,
    session_id: str,
    chars_per_token: float,
) -> dict[str, Any]:
    """Map exact provider-history slices to completed turns when traces allow it."""

    chat_session = repositories.get_chat_session(db, session_id)
    if chat_session is None:
        return _unavailable_source_map(
            session_id=session_id,
            reason="session_not_found",
        )

    turns = repositories.list_turns_for_session(
        db,
        session_id=session_id,
        status="completed",
    )
    canonical = _provider_messages(chat_session.provider_history_json)
    if not canonical and not turns:
        return _empty_source_map(session_id=session_id)
    if not canonical:
        return _unavailable_source_map(
            session_id=session_id,
            reason="canonical_provider_history_unavailable",
        )

    request_snapshots: list[tuple[Any, Any, list[dict[str, Any]]]] = []
    for turn in turns:
        request_trace = _latest_trace(
            repositories.list_traces_for_turn(db, turn_id=turn.id),
            kind="llm.request",
        )
        if request_trace is None:
            return _unavailable_source_map(
                session_id=session_id,
                reason="llm_request_trace_missing",
                failed_turn_id=turn.id,
            )
        provider_messages = _provider_messages(
            request_trace.payload_json.get("provider_messages")
        )
        if not provider_messages or provider_messages[-1].get("role") != "user":
            return _unavailable_source_map(
                session_id=session_id,
                reason="request_provider_messages_invalid",
                failed_turn_id=turn.id,
                failed_trace_id=request_trace.id,
            )
        request_snapshots.append((turn, request_trace, provider_messages))

    units: list[dict[str, Any]] = []
    mapped_messages: list[dict[str, Any]] = []
    legacy_prefix: list[dict[str, Any]] = []
    for index, (turn, request_trace, request_messages) in enumerate(
        request_snapshots
    ):
        before = request_messages[:-1]
        after = (
            request_snapshots[index + 1][2][:-1]
            if index + 1 < len(request_snapshots)
            else canonical
        )
        if not _is_prefix(before, after):
            return _unavailable_source_map(
                session_id=session_id,
                reason="provider_history_prefix_mismatch",
                failed_turn_id=turn.id,
                failed_trace_id=request_trace.id,
            )
        if index == 0 and before:
            legacy_prefix = before
            mapped_messages.extend(before)
        elif before != mapped_messages:
            return _unavailable_source_map(
                session_id=session_id,
                reason="provider_history_turn_boundary_mismatch",
                failed_turn_id=turn.id,
                failed_trace_id=request_trace.id,
            )

        segment = after[len(before) :]
        if not segment or segment[0] != request_messages[-1]:
            return _unavailable_source_map(
                session_id=session_id,
                reason="current_user_message_not_preserved",
                failed_turn_id=turn.id,
                failed_trace_id=request_trace.id,
            )
        messages = repositories.list_messages_for_turn(db, turn_id=turn.id)
        traces = repositories.list_traces_for_turn(db, turn_id=turn.id)
        response_trace = _latest_trace(traces, kind="llm.response")
        serialized = _json(segment)
        units.append(
            {
                "turn_id": turn.id,
                "message_ids": [message.id for message in messages],
                "tool_call_ids": _tool_call_ids(response_trace),
                "request_trace_id": request_trace.id,
                "response_trace_id": (
                    response_trace.id if response_trace is not None else None
                ),
                "provider_messages": segment,
                "provider_message_count": len(segment),
                "json_chars": len(serialized),
                "utf8_bytes": len(serialized.encode("utf-8")),
                "estimated_tokens": _estimate_tokens(
                    len(serialized), chars_per_token
                ),
                "sha256": _digest(segment),
            }
        )
        mapped_messages.extend(segment)

    complete = mapped_messages == canonical
    legacy_serialized = _json(legacy_prefix)
    canonical_serialized = _json(canonical)
    return {
        "schema_version": CHRONOLOGY_SOURCE_MAP_VERSION,
        "status": "complete" if complete else "unavailable",
        "session_id": session_id,
        "canonical_history_sha256": _digest(canonical),
        "canonical_provider_message_count": len(canonical),
        "canonical_json_chars": len(canonical_serialized),
        "canonical_estimated_tokens": _estimate_tokens(
            len(canonical_serialized), chars_per_token
        ),
        "mapped_provider_message_count": len(mapped_messages),
        "legacy_prefix": {
            "provider_message_count": len(legacy_prefix),
            "json_chars": len(legacy_serialized) if legacy_prefix else 0,
            "estimated_tokens": (
                _estimate_tokens(len(legacy_serialized), chars_per_token)
                if legacy_prefix
                else 0
            ),
            "sha256": _digest(legacy_prefix) if legacy_prefix else None,
        },
        "turn_count": len(units),
        "turns": units,
        "mapping_verified": complete,
        "canonical_history_mutation": "none",
    }


def build_history_partition_plan(
    *,
    source_map: dict[str, Any],
    external_context_tokens: int,
    provider_history_tokens: int,
    operational_limit_tokens: int,
    model_window_tokens: int,
    summary_max_tokens: int,
    verbatim_max_tokens: int,
    safety_tokens: int,
    mode: str,
) -> dict[str, Any]:
    """Describe a token-partitioned compaction cycle without applying it."""

    conversation_capacity = max(
        0,
        operational_limit_tokens - external_context_tokens - safety_tokens,
    )
    active_growth_tokens = max(
        0,
        conversation_capacity - summary_max_tokens - verbatim_max_tokens,
    )
    would_trigger = provider_history_tokens >= conversation_capacity
    selected_reversed: list[dict[str, Any]] = []
    selected_tokens = 0
    single_turn_exception: dict[str, Any] | None = None
    physical_window_failure: dict[str, Any] | None = None
    turns = source_map.get("turns") if source_map.get("status") == "complete" else []
    if not isinstance(turns, list):
        turns = []

    for unit in reversed(turns):
        cost = int(unit.get("estimated_tokens") or 0)
        if selected_reversed or cost <= verbatim_max_tokens:
            if selected_tokens + cost > verbatim_max_tokens:
                break
            selected_reversed.append(unit)
            selected_tokens += cost
            continue

        if cost <= model_window_tokens:
            selected_reversed.append(unit)
            selected_tokens = cost
            single_turn_exception = {
                "turn_id": unit.get("turn_id"),
                "estimated_tokens": cost,
                "verbatim_budget_tokens": verbatim_max_tokens,
                "physical_model_window_tokens": model_window_tokens,
                "policy": (
                    "retain_the_complete_turn_as_a_reported_operational_limit_"
                    "exception; compact_again_at_the_next_complete_turn_boundary"
                ),
            }
        else:
            physical_window_failure = {
                "turn_id": unit.get("turn_id"),
                "estimated_tokens": cost,
                "physical_model_window_tokens": model_window_tokens,
                "policy": (
                    "do_not_split_or_silently_drop_the_turn; block_active_"
                    "compaction_and_require_a_separately_approved_strategy"
                ),
            }
        break

    selected = list(reversed(selected_reversed))
    selected_ids = {str(unit.get("turn_id")) for unit in selected}
    compacted = [
        unit for unit in turns if str(unit.get("turn_id")) not in selected_ids
    ]
    legacy_prefix = source_map.get("legacy_prefix") or {}
    legacy_prefix_tokens = int(legacy_prefix.get("estimated_tokens") or 0)
    summary_input_sources: list[dict[str, Any]] = []
    if legacy_prefix_tokens:
        summary_input_sources.append(
            {
                "kind": "legacy_provider_history_prefix",
                "sha256": legacy_prefix.get("sha256"),
                "estimated_tokens": legacy_prefix_tokens,
            }
        )
    summary_input_sources.extend(
        {
            "kind": "completed_turn",
            "turn_id": unit.get("turn_id"),
            "sha256": unit.get("sha256"),
            "estimated_tokens": int(unit.get("estimated_tokens") or 0),
        }
        for unit in compacted
    )
    status = "disabled" if mode == "off" else "below_partition_trigger"
    if mode == "shadow" and would_trigger:
        status = "would_recompact"
    if source_map.get("status") != "complete":
        status = "source_map_unavailable"
    elif physical_window_failure is not None:
        status = "single_turn_exceeds_physical_model_window"
    elif conversation_capacity <= summary_max_tokens + verbatim_max_tokens:
        status = "partition_budget_invalid"
    elif single_turn_exception is not None:
        status = "single_turn_exceeds_operational_partition"

    exceptional_active_growth_tokens = None
    if single_turn_exception is not None:
        exceptional_active_growth_tokens = max(
            0,
            operational_limit_tokens
            - external_context_tokens
            - safety_tokens
            - summary_max_tokens
            - selected_tokens,
        )

    return {
        "schema_version": HISTORY_PARTITION_PLAN_VERSION,
        "status": status,
        "shadow_only": mode == "shadow",
        "would_trigger": would_trigger,
        "trigger_basis": (
            "provider_history_tokens_reach_operational_limit_minus_external_"
            "context_and_safety"
        ),
        "areas": {
            "external_context": {
                "estimated_tokens": external_context_tokens,
                "compacted": False,
            },
            "compacted_summary": {
                "max_tokens": summary_max_tokens,
                "input_turn_ids": [unit.get("turn_id") for unit in compacted],
                "input_sources": summary_input_sources,
                "input_estimated_tokens": legacy_prefix_tokens
                + sum(int(unit.get("estimated_tokens") or 0) for unit in compacted),
                "includes_previous_summary_on_later_cycles": True,
            },
            "verbatim_chronology": {
                "max_tokens": verbatim_max_tokens,
                "selected_turn_ids": [unit.get("turn_id") for unit in selected],
                "selected_estimated_tokens": selected_tokens,
                "selected_turn_count": len(selected),
            },
            "active_growth": {
                "reserved_tokens_after_compaction": active_growth_tokens,
                "purpose": "new_complete_turns_and_current_turn_tool_loop",
            },
            "technical_safety": {"reserved_tokens": safety_tokens},
        },
        "conversation_capacity_tokens": conversation_capacity,
        "provider_history_estimated_tokens": provider_history_tokens,
        "projected_post_compaction_reserved_tokens": (
            external_context_tokens
            + summary_max_tokens
            + verbatim_max_tokens
            + active_growth_tokens
            + safety_tokens
        ),
        "single_turn_exception": single_turn_exception,
        "single_turn_exception_active_growth_tokens": (
            exceptional_active_growth_tokens
        ),
        "physical_window_failure": physical_window_failure,
        "source_map_status": source_map.get("status"),
        "source_history_sha256": source_map.get("canonical_history_sha256"),
        "canonical_history_mutation": "none",
        "activation_gate": (
            "Generate a source-labelled summary candidate, compare full and derived "
            "continuations, and obtain explicit approval before active routing."
        ),
    }


def _provider_messages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    messages: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            return []
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, list):
            return []
        messages.append({"role": role, "content": content})
    return messages


def _latest_trace(traces: list[Any], *, kind: str) -> Any | None:
    matches = [trace for trace in traces if trace.kind == kind]
    return matches[-1] if matches else None


def _tool_call_ids(response_trace: Any | None) -> list[str]:
    if response_trace is None:
        return []
    calls = response_trace.payload_json.get("tool_calls")
    if not isinstance(calls, list):
        return []
    return [
        str(item["tool_call_id"])
        for item in calls
        if isinstance(item, dict) and item.get("tool_call_id")
    ]


def _is_prefix(prefix: list[dict[str, Any]], value: list[dict[str, Any]]) -> bool:
    return len(prefix) <= len(value) and value[: len(prefix)] == prefix


def _estimate_tokens(chars: int, chars_per_token: float) -> int:
    return ceil(chars / chars_per_token) if chars > 0 else 0


def _digest(value: Any) -> str:
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _unavailable_source_map(
    *,
    session_id: str,
    reason: str,
    failed_turn_id: str | None = None,
    failed_trace_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": CHRONOLOGY_SOURCE_MAP_VERSION,
        "status": "unavailable",
        "session_id": session_id,
        "reason": reason,
        "failed_turn_id": failed_turn_id,
        "failed_trace_id": failed_trace_id,
        "turn_count": 0,
        "turns": [],
        "mapping_verified": False,
        "canonical_history_mutation": "none",
    }


def _empty_source_map(*, session_id: str) -> dict[str, Any]:
    canonical: list[dict[str, Any]] = []
    return {
        "schema_version": CHRONOLOGY_SOURCE_MAP_VERSION,
        "status": "complete",
        "session_id": session_id,
        "canonical_history_sha256": _digest(canonical),
        "canonical_provider_message_count": 0,
        "canonical_json_chars": len(_json(canonical)),
        "canonical_estimated_tokens": 0,
        "mapped_provider_message_count": 0,
        "legacy_prefix": {
            "provider_message_count": 0,
            "json_chars": 0,
            "estimated_tokens": 0,
            "sha256": None,
        },
        "turn_count": 0,
        "turns": [],
        "mapping_verified": True,
        "canonical_history_mutation": "none",
    }

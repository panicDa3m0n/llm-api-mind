"""Measure model input and prepare non-destructive history compaction plans.

Provider token usage is authoritative only after a model call. Preflight
measurements therefore keep exact character/byte counts separate from token
estimates, then an observed trace records the provider-reported total.
"""

from __future__ import annotations

from copy import deepcopy
from math import ceil
import json
from statistics import median
from typing import Any

from sqlmodel import Session

from app.llm.provider import LLMMessage, LLMTextResult
from app.storage import repositories


CONTEXT_ACCOUNTING_VERSION = "context-accounting-v1"
HISTORY_COMPACTION_PLAN_VERSION = "history-compaction-shadow-v1"


def build_context_accounting_preflight(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    model: str,
    transport: str,
    base_system: str,
    runtime_context: str,
    messages: list[LLMMessage],
    tools: list[dict[str, Any]],
    settings: Any,
    external_unobserved_context: list[str] | None = None,
) -> dict[str, Any]:
    fallback_ratio = float(settings.context_estimated_chars_per_token)
    ratio, calibration = _calibrated_chars_per_token(
        db,
        session_id=session_id,
        model=model,
        fallback=fallback_ratio,
    )
    message_payloads = [message.model_dump(mode="json") for message in messages]
    history_payloads = message_payloads[:-1] if message_payloads else []
    current_payloads = message_payloads[-1:] if message_payloads else []
    effective_system = f"{base_system}\n\n{runtime_context}"
    wire_payload = {
        "system": effective_system,
        "messages": message_payloads,
        "tools": tools,
    }
    total_json = _json(wire_payload)
    raw_channels = {
        "static_system": base_system,
        "dynamic_runtime_context": runtime_context,
        "provider_history": history_payloads,
        "current_user_message": current_payloads,
        "tool_schema": tools,
    }
    channels = {
        name: _measurement(value, chars_per_token=ratio)
        for name, value in raw_channels.items()
    }
    accounted_chars = sum(item["json_chars"] for item in channels.values())
    channels["request_structure"] = _measurement_from_chars(
        max(0, len(total_json) - accounted_chars),
        chars_per_token=ratio,
    )
    total_estimated_tokens = _estimate_tokens(len(total_json), ratio)
    recent_window = _recent_turn_window(
        db,
        session_id=session_id,
        limit=int(settings.history_compaction_recent_turns),
        chars_per_token=ratio,
    )
    policy = _policy(settings)
    compaction_plan = _compaction_plan(
        channels=channels,
        total_estimated_tokens=total_estimated_tokens,
        recent_window=recent_window,
        policy=policy,
    )
    return {
        "schema_version": CONTEXT_ACCOUNTING_VERSION,
        "stage": "preflight",
        "session_id": session_id,
        "turn_id": turn_id,
        "model": model,
        "transport": transport,
        "measurement_boundary": {
            "exact": ["json_chars", "utf8_bytes", "message_count", "turn_count"],
            "estimated": ["tokens_by_channel", "preflight_input_tokens"],
            "provider_reported_after_call": ["first_step_input_tokens", "tool_loop_totals"],
            "external_unobserved_context": external_unobserved_context or [],
        },
        "calibration": calibration | {"chars_per_token_used": ratio},
        "channels": channels,
        "total": {
            "json_chars": len(total_json),
            "utf8_bytes": len(total_json.encode("utf-8")),
            "estimated_input_tokens": total_estimated_tokens,
        },
        "policy": policy,
        "recent_turn_window": recent_window,
        "compaction_plan": compaction_plan,
    }


def build_context_accounting_observation(
    *,
    preflight_trace_id: str,
    preflight: dict[str, Any],
    result: LLMTextResult,
) -> dict[str, Any]:
    first_step_usage: dict[str, Any] = {}
    if result.raw_provider_messages:
        candidate = result.raw_provider_messages[0].get("usage")
        if isinstance(candidate, dict):
            first_step_usage = candidate
    first_step_input = _int_or_none(first_step_usage.get("input_tokens"))
    if first_step_input is None and len(result.raw_provider_messages) <= 1:
        first_step_input = _int_or_none(result.usage.get("input_tokens"))
    request_chars = int((preflight.get("total") or {}).get("json_chars") or 0)
    observed_ratio = (
        round(request_chars / first_step_input, 6)
        if first_step_input and request_chars > 0
        else None
    )
    return {
        "schema_version": CONTEXT_ACCOUNTING_VERSION,
        "stage": "observed",
        "preflight_trace_id": preflight_trace_id,
        "session_id": preflight.get("session_id"),
        "turn_id": preflight.get("turn_id"),
        "model": result.model,
        "provider_reported": {
            "first_step_input_tokens": first_step_input,
            "first_step_usage": first_step_usage,
            "tool_loop_totals": result.usage,
            "model_step_count": max(1, len(result.raw_provider_messages)),
        },
        "calibration_observation": {
            "request_json_chars": request_chars,
            "chars_per_first_step_input_token": observed_ratio,
            "usable_for_future_preflight": observed_ratio is not None,
        },
        "compaction_plan_was_shadow_only": True,
        "canonical_history_mutated": False,
    }


def build_external_context_accounting_preflight(
    *,
    session_id: str,
    turn_id: str,
    transport: str,
    payload: dict[str, Any],
    settings: Any,
) -> dict[str, Any]:
    """Measure only the backend packet visible at the GPT bridge boundary.

    ChatGPT's manual system prompt, native conversation history, action schema
    serialization, and provider tokenization are not observable by this
    backend. The result must therefore never be presented as total model input.
    """

    ratio = float(settings.context_estimated_chars_per_token)
    measured_payload = deepcopy(payload)
    diagnostics = measured_payload.get("full_diagnostics")
    if isinstance(diagnostics, dict):
        # Persisting this measurement and the request creates the final trace
        # ids. Measuring that list would therefore be circular; all other
        # bootstrap fields remain byte-for-byte accounted.
        diagnostics["available_in_trace_ids"] = []
    channels = {
        key: _measurement(value, chars_per_token=ratio)
        for key, value in measured_payload.items()
    }
    serialized = _json(measured_payload)
    return {
        "schema_version": CONTEXT_ACCOUNTING_VERSION,
        "stage": "preflight",
        "session_id": session_id,
        "turn_id": turn_id,
        "model": "external-gpt-unobserved",
        "transport": transport,
        "measurement_boundary": {
            "exact": [
                "backend_bootstrap_json_chars_excluding_assigned_trace_ids",
                "backend_bootstrap_utf8_bytes_excluding_assigned_trace_ids",
            ],
            "estimated": ["backend_bootstrap_tokens_by_channel"],
            "normalization": [
                "full_diagnostics.available_in_trace_ids is measured as an empty "
                "array because those ids are assigned after accounting"
            ],
            "external_unobserved_context": [
                "manual_gpt_system_prompt",
                "chatgpt_native_conversation_history",
                "chatgpt_action_schema_serialization",
                "chatgpt_provider_request_structure",
                "chatgpt_provider_token_usage",
            ],
            "is_total_model_input": False,
        },
        "calibration": {
            "source": "configured_fallback_no_external_provider_usage",
            "sample_count": 0,
            "chars_per_token_used": ratio,
        },
        "channels": channels,
        "total": {
            "json_chars": len(serialized),
            "utf8_bytes": len(serialized.encode("utf-8")),
            "estimated_backend_packet_tokens": _estimate_tokens(
                len(serialized), ratio
            ),
            "total_model_input_tokens": None,
        },
        "policy": {
            "native_policy_reference": _policy(settings),
            "enforceable_for_external_gpt": False,
        },
        "compaction_plan": {
            "status": "not_computable_external_provider_history_unobserved",
            "shadow_only": True,
            "canonical_history_mutation": "none",
        },
    }


def _policy(settings: Any) -> dict[str, Any]:
    return {
        "model_context_window_tokens": int(settings.context_window_tokens),
        "operational_input_limit_tokens": int(
            settings.context_operational_input_limit_tokens
        ),
        "compaction_trigger_tokens": int(settings.context_compaction_trigger_tokens),
        "summary_target_tokens": int(settings.history_compaction_target_tokens),
        "recent_complete_turns": int(settings.history_compaction_recent_turns),
        "compaction_mode": str(settings.history_compaction_mode),
        "canonical_history_policy": "append_only_never_overwrite",
    }


def _compaction_plan(
    *,
    channels: dict[str, dict[str, Any]],
    total_estimated_tokens: int,
    recent_window: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    trigger = int(policy["compaction_trigger_tokens"])
    limit = int(policy["operational_input_limit_tokens"])
    summary_target = int(policy["summary_target_tokens"])
    mode = str(policy["compaction_mode"])
    would_trigger = total_estimated_tokens >= trigger
    fixed_tokens = total_estimated_tokens - int(
        channels["provider_history"]["estimated_tokens"]
    )
    projected = fixed_tokens + summary_target + int(recent_window["estimated_tokens"])
    status = "disabled" if mode == "off" else "below_trigger"
    if mode == "shadow" and would_trigger:
        status = "would_compact"
        if projected >= limit:
            status = "would_compact_insufficient_headroom"
    return {
        "schema_version": HISTORY_COMPACTION_PLAN_VERSION,
        "status": status,
        "shadow_only": mode == "shadow",
        "would_trigger": would_trigger,
        "trigger_basis": "estimated_preflight_input_tokens",
        "summary_target_tokens": summary_target,
        "retained_recent_turn_count": recent_window["turn_count"],
        "retained_recent_turn_ids": recent_window["turn_ids"],
        "retained_recent_turns_estimated_tokens": recent_window["estimated_tokens"],
        "projected_active_input_tokens": projected,
        "projected_free_tokens_below_operational_limit": limit - projected,
        "canonical_history_mutation": "none",
        "activation_gate": (
            "Calibrate on a long varied real session, validate summary quality and "
            "recent-turn sizing, then approve an active strategy separately."
        ),
    }


def _recent_turn_window(
    db: Session,
    *,
    session_id: str,
    limit: int,
    chars_per_token: float,
) -> dict[str, Any]:
    turns = repositories.list_turns_for_session(
        db,
        session_id=session_id,
        status="completed",
    )[-limit:]
    payloads: list[dict[str, Any]] = []
    for turn in turns:
        messages = repositories.list_messages_for_turn(db, turn_id=turn.id)
        traces = repositories.list_traces_for_turn(db, turn_id=turn.id)
        response = next((trace for trace in traces if trace.kind == "llm.response"), None)
        response_payload = response.payload_json if response is not None else {}
        payloads.append(
            {
                "turn_id": turn.id,
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                    if message.role in {"user", "assistant"}
                ],
                "provider_response_blocks": response_payload.get(
                    "raw_provider_messages",
                    response_payload.get("raw_content", []),
                ),
                "tool_calls": response_payload.get("tool_calls", []),
            }
        )
    serialized = _json(payloads)
    return {
        "basis": "completed_turn_public_messages_provider_blocks_and_tool_receipts",
        "turn_count": len(turns),
        "turn_ids": [turn.id for turn in turns],
        "json_chars": len(serialized),
        "utf8_bytes": len(serialized.encode("utf-8")),
        "estimated_tokens": _estimate_tokens(len(serialized), chars_per_token),
    }


def _calibrated_chars_per_token(
    db: Session,
    *,
    session_id: str,
    model: str,
    fallback: float,
) -> tuple[float, dict[str, Any]]:
    traces = repositories.list_traces_for_session(
        db,
        session_id=session_id,
        kinds=["context.accounting.observed"],
        limit=20,
    )
    values: list[float] = []
    for trace in traces:
        payload = trace.payload_json
        if payload.get("model") != model:
            continue
        value = (payload.get("calibration_observation") or {}).get(
            "chars_per_first_step_input_token"
        )
        if isinstance(value, (int, float)) and 1.0 <= float(value) <= 12.0:
            values.append(float(value))
    if not values:
        return fallback, {"source": "configured_fallback", "sample_count": 0}
    return float(median(values)), {
        "source": "provider_observation_median",
        "sample_count": len(values),
    }


def _measurement(value: Any, *, chars_per_token: float) -> dict[str, Any]:
    serialized = value if isinstance(value, str) else _json(value)
    return _measurement_from_chars(
        len(serialized),
        chars_per_token=chars_per_token,
        utf8_bytes=len(serialized.encode("utf-8")),
    )


def _measurement_from_chars(
    chars: int,
    *,
    chars_per_token: float,
    utf8_bytes: int | None = None,
) -> dict[str, Any]:
    return {
        "json_chars": chars,
        "utf8_bytes": chars if utf8_bytes is None else utf8_bytes,
        "estimated_tokens": _estimate_tokens(chars, chars_per_token),
        "token_status": "estimated_not_provider_exact",
    }


def _estimate_tokens(chars: int, chars_per_token: float) -> int:
    return ceil(chars / chars_per_token) if chars > 0 else 0


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None

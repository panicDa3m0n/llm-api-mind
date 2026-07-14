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
from app.runtime.history_compaction import (
    build_chronology_source_map,
    build_history_partition_plan,
)
from app.storage import repositories


CONTEXT_ACCOUNTING_VERSION = "context-accounting-v2"


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
        "static_system_policy": base_system,
        "model_context_packet": runtime_context,
        "provider_history": history_payloads,
        "current_user_message": current_payloads,
        "mind_shell_tool_schema": tools,
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
    chronology_source_map = build_chronology_source_map(
        db,
        session_id=session_id,
        chars_per_token=ratio,
    )
    policy = _policy(settings)
    provider_history_tokens = int(channels["provider_history"]["estimated_tokens"])
    external_context_tokens = max(
        0,
        total_estimated_tokens - provider_history_tokens,
    )
    compaction_plan = build_history_partition_plan(
        source_map=chronology_source_map,
        external_context_tokens=external_context_tokens,
        provider_history_tokens=provider_history_tokens,
        operational_limit_tokens=int(
            settings.context_operational_input_limit_tokens
        ),
        model_window_tokens=int(settings.context_window_tokens),
        summary_max_tokens=int(settings.history_compaction_target_tokens),
        verbatim_max_tokens=int(settings.history_compaction_verbatim_tokens),
        safety_tokens=int(settings.history_compaction_safety_tokens),
        mode=str(settings.history_compaction_mode),
    )
    return {
        "schema_version": CONTEXT_ACCOUNTING_VERSION,
        "stage": "preflight",
        "session_id": session_id,
        "turn_id": turn_id,
        "model": model,
        "transport": transport,
        "accounting_surface": "native_model_request",
        "measurement_boundary": {
            "exact": ["json_chars", "utf8_bytes", "message_count", "turn_count"],
            "estimated": ["tokens_by_channel", "preflight_input_tokens"],
            "provider_reported_after_call": [
                "per_step_effective_input_tokens",
                "maximum_step_effective_input_tokens",
                "tool_loop_cumulative_usage",
            ],
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
        "chronology_source_map": chronology_source_map,
        "compaction_plan": compaction_plan,
    }


def build_context_accounting_observation(
    *,
    preflight_trace_id: str,
    preflight: dict[str, Any],
    result: LLMTextResult,
) -> dict[str, Any]:
    step_observations = _step_usage_observations(result)
    first_step = step_observations[0] if step_observations else {}
    first_step_usage = first_step.get("usage") or {}
    first_step_input = _int_or_none(first_step.get("effective_input_tokens"))
    maximum_step_input = max(
        (
            int(step["effective_input_tokens"])
            for step in step_observations
            if _int_or_none(step.get("effective_input_tokens")) is not None
        ),
        default=None,
    )
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
            # Compatibility alias: from v2 this is the effective provider input,
            # including cache-read and cache-creation tokens when reported.
            "first_step_input_tokens": first_step_input,
            "first_step_effective_input_tokens": first_step_input,
            "first_step_usage": first_step_usage,
            "steps": step_observations,
            "maximum_step_effective_input_tokens": maximum_step_input,
            "tool_loop_totals": result.usage,
            "tool_loop_cumulative_usage": result.usage,
            "model_step_count": len(step_observations),
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
        "accounting_surface": "gpt_bridge_backend_packet_only",
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
        "compatibility_warning_threshold_tokens": int(
            settings.context_compaction_trigger_tokens
        ),
        "compacted_summary_max_tokens": int(
            settings.history_compaction_target_tokens
        ),
        "verbatim_chronology_max_tokens": int(
            settings.history_compaction_verbatim_tokens
        ),
        "technical_safety_tokens": int(settings.history_compaction_safety_tokens),
        "verbatim_selection": "newest_complete_turns_by_incremental_token_cost",
        "compaction_mode": str(settings.history_compaction_mode),
        "canonical_history_policy": "append_only_never_overwrite",
    }


def _step_usage_observations(result: LLMTextResult) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for index, provider_message in enumerate(result.raw_provider_messages, start=1):
        candidate = provider_message.get("usage")
        usage = candidate if isinstance(candidate, dict) else {}
        observations.append(
            {
                "step": index,
                "provider_message_id": provider_message.get("id"),
                "usage": usage,
                "effective_input_tokens": _effective_input_tokens(usage),
            }
        )
    if not observations and result.usage:
        observations.append(
            {
                "step": 1,
                "provider_message_id": result.provider_message_id,
                "usage": result.usage,
                "effective_input_tokens": _effective_input_tokens(result.usage),
                "source": "aggregate_single_step_fallback",
            }
        )
    return observations


def _effective_input_tokens(usage: dict[str, Any]) -> int | None:
    components = [
        _int_or_none(usage.get("input_tokens")),
        _int_or_none(usage.get("cache_read_input_tokens")),
        _int_or_none(usage.get("cache_creation_input_tokens")),
    ]
    present = [value for value in components if value is not None]
    return sum(present) if present else None


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
        if (
            payload.get("schema_version") != CONTEXT_ACCOUNTING_VERSION
            or payload.get("model") != model
        ):
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

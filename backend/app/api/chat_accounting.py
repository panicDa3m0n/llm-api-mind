"""Context-accounting persistence and compact request statistics for chat."""

import json
from typing import Any

from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMMessage, LLMTextResult
from app.mind.shell import MIND_SHELL_TOOL_SCHEMA
from app.runtime.context_accounting import (
    build_context_accounting_observation,
    build_context_accounting_preflight,
)
from app.storage import repositories
from app.storage.models import Trace


def post_turn_model_history_tokens(
    source_map: dict[str, Any],
    history_routing_payload: dict[str, Any],
) -> int:
    canonical_tokens = int(source_map.get("canonical_estimated_tokens") or 0)
    if history_routing_payload.get("status") != "derived_history_active":
        return canonical_tokens
    turns = source_map.get("turns")
    covered_count = int(history_routing_payload.get("covered_turn_count") or 0)
    if not isinstance(turns, list) or covered_count < 0 or covered_count > len(turns):
        return canonical_tokens
    return sum(
        int(unit.get("estimated_tokens") or 0)
        for unit in turns[covered_count:]
        if isinstance(unit, dict)
    )


def record_context_accounting_preflight(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    model: str,
    transport: str,
    base_system: str,
    runtime_context: str,
    messages: list[LLMMessage],
    settings: Settings,
    compacted_chronology: str = "",
    answer_obligations: str = "",
    external_unobserved_context: list[str] | None = None,
) -> tuple[Trace, dict[str, Any]]:
    payload = build_context_accounting_preflight(
        db,
        session_id=session_id,
        turn_id=turn_id,
        model=model,
        transport=transport,
        base_system=base_system,
        runtime_context=runtime_context,
        messages=messages,
        tools=[MIND_SHELL_TOOL_SCHEMA],
        settings=settings,
        compacted_chronology=compacted_chronology,
        answer_obligations=answer_obligations,
        external_unobserved_context=external_unobserved_context,
    )
    trace = repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn_id,
        kind="context.accounting.preflight",
        payload=payload,
    )
    return trace, payload


def record_context_accounting_observed(
    db: Session,
    *,
    session_id: str,
    turn_id: str,
    preflight_trace_id: str,
    preflight: dict[str, Any],
    result: LLMTextResult,
) -> Trace:
    return repositories.add_trace(
        db,
        session_id=session_id,
        turn_id=turn_id,
        kind="context.accounting.observed",
        payload=build_context_accounting_observation(
            preflight_trace_id=preflight_trace_id,
            preflight=preflight,
            result=result,
        ),
    )


def context_accounting_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "transport": payload.get("transport"),
        "total": payload.get("total"),
        "policy": payload.get("policy"),
        "compaction_plan": payload.get("compaction_plan"),
    }


def provider_message_stats(messages: list[LLMMessage]) -> dict[str, Any]:
    serializable = [message.model_dump(mode="json") for message in messages]
    serialized = json.dumps(serializable, ensure_ascii=False)
    block_count = 0
    for message in messages:
        if isinstance(message.content, list):
            block_count += len(message.content)
        else:
            block_count += 1
    return {
        "message_count": len(messages),
        "content_block_count": block_count,
        "json_chars": len(serialized),
        "approx_tokens": max(1, len(serialized) // 4) if serialized else 0,
    }

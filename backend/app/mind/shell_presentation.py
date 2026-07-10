"""Model-facing presentation for Mind shell command results.

Command handlers stay concerned with translating shell grammar to internal
operations. This module owns response sanitization, compact model packets,
help/error envelopes, and endpoint-language removal so presentation policy can
evolve without changing the command grammar or handlers.
"""

from __future__ import annotations

import re
from typing import Any

from app.mind.command_registry import COMMAND_REGISTRY_VERSION, validate_shell_command
from app.mind.contracts import MindAPIContext
from app.mind.dispatcher import (
    MindAPIError,
    MindAPIRequest,
    MindAPIResponse,
    dispatch_mind_api,
)
from app.mind.schema import (
    build_mind_shell_catalog,
    shell_command_catalog,
    shell_command_usage_guide,
    shell_metadata,
)
from app.mind.shell_parsing import ParsedCommand


def dispatch_api_as_shell(
    parsed: ParsedCommand,
    *,
    target: str,
    api_request: MindAPIRequest,
    context: MindAPIContext | None,
) -> MindAPIResponse:
    """Execute an internal operation and return its stable shell envelope."""

    api_response = dispatch_mind_api(api_request, context=context)
    sanitized_result = sanitize_for_shell(api_response.result)
    model_data = model_facing_data(target, sanitized_result)
    return MindAPIResponse(
        ok=api_response.ok,
        result={
            "operation": "mind_shell.command",
            "command": parsed.raw,
            "parsed": parsed.model_payload(),
            "target": target,
            "data": model_data,
        },
        cognitive_hint=sanitize_text(api_response.cognitive_hint)
        if api_response.cognitive_hint
        else hint_for_target(target),
        suggested_next_actions=shell_next_actions(
            target,
            [sanitize_text(action) for action in api_response.suggested_next_actions],
            ok=api_response.ok,
        ),
        confidence=api_response.confidence,
        usage_guide=None if api_response.ok else usage_for_target(target, parsed.namespace),
        error=MindAPIError(
            code=api_response.error.code,
            message=sanitize_text(api_response.error.message),
            recoverable=api_response.error.recoverable,
        )
        if api_response.error is not None
        else None,
    )


def help_response(parsed: ParsedCommand) -> MindAPIResponse:
    namespace = parsed.action
    if parsed.namespace in {"schema", "capabilities"}:
        namespace = None
    commands = shell_command_catalog(namespace)
    if namespace and not commands:
        return shell_error(
            code="shell.help_unknown_namespace",
            message=f"No help namespace found for: {namespace}",
            parsed=parsed,
            namespace=None,
            actions=["help"],
        )
    return MindAPIResponse(
        ok=True,
        result={
            "operation": "mind_shell.help",
            "command": parsed.raw,
            "schema": shell_metadata(),
            "command_registry": {"version": COMMAND_REGISTRY_VERSION},
            "catalog": build_mind_shell_catalog()
            if namespace is None
            else {"commands": commands},
        },
        cognitive_hint=(
            "Use these commands as Scarlet's internal cognitive shell. "
            "Prefer precise commands over endpoint paths."
        ),
        suggested_next_actions=[
            "Use a namespace command for the cognitive need",
            "Use help <namespace> before unfamiliar state-changing commands",
        ],
        confidence=1.0,
    )


def shell_error(
    *,
    code: str,
    message: str,
    parsed: ParsedCommand | None,
    namespace: str | None,
    actions: list[str],
    details: dict[str, Any] | None = None,
) -> MindAPIResponse:
    return MindAPIResponse(
        ok=False,
        result={
            "operation": "mind_shell.command",
            "parsed": parsed.model_payload() if parsed is not None else None,
            "details": details or {},
            "command_validation": validate_shell_command(parsed.raw)
            if parsed is not None
            else None,
            "schema": shell_metadata(),
        },
        cognitive_hint="Correct the command syntax and retry if the cognitive operation is still useful.",
        suggested_next_actions=actions,
        confidence=1.0,
        usage_guide=shell_command_usage_guide(namespace),
        error=MindAPIError(code=code, message=message, recoverable=True),
    )


def usage_for_target(target: str, namespace: str | None) -> dict[str, Any]:
    guide = shell_command_usage_guide(namespace)
    guide["target"] = target
    return guide


def shell_next_actions(target: str, actions: list[str], *, ok: bool) -> list[str]:
    defaults = {
        "memory.search": ["memory open mem_...", "memory graph mem_... --depth 2"],
        "memory.write": ["memory open mem_..."],
        "session.list": ["session open ses_..."],
        "session.open": ['memory search "related fact" --top 5'],
        "focus.read": ['focus set "object" --reason "..."'],
        "volition.list_active": ["volition read int_..."],
        "affect.read": ["affect prototypes"],
    }
    translated = [
        item
        for item in actions
        if item and "endpoint" not in item.casefold() and "/mind/" not in item
    ]
    if ok:
        return translated or defaults.get(target, [])
    return translated or ["help", f"help {target.split('.', 1)[0]}"]


def model_facing_data(target: str, data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    if target == "memory.search":
        return compact_memory_search(data)
    if target == "memory.conflicts":
        return compact_memory_conflicts(data)
    if target == "session.open":
        return annotate_session_window(data)
    return data


def compact_memory_search(data: dict[str, Any]) -> dict[str, Any]:
    omitted = [
        key
        for key in ("retrieval_shadow", "retrieval_graph", "retrieval_hybrid")
        if key in data
    ]
    return {
        "operation": data.get("operation"),
        "model_output_profile": "mind-shell-memory-search-compact-v1",
        "query": data.get("query"),
        "retrieval_query": data.get("retrieval_query"),
        "time": data.get("time"),
        "count": data.get("count"),
        "memories": [
            compact_memory_payload(item)
            for item in data.get("memories", [])
            if isinstance(item, dict)
        ],
        "retrieval_summary": retrieval_summary(data),
        "trace_ids": data.get("trace_ids", []),
        "debug": {
            "full_result_in_trace": True,
            "omitted_model_fields": omitted,
        },
    }


def compact_memory_payload(memory: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "id": memory.get("id"),
        "type": memory.get("type"),
        "scope": memory.get("scope"),
        "status": memory.get("status"),
        "content": memory.get("content"),
        "reason_for_storage": memory.get("reason_for_storage"),
        "expected_future_use": memory.get("expected_future_use"),
        "source": {
            "source_session_id": memory.get("source_session_id"),
            "source_turn_id": memory.get("source_turn_id"),
            "source_message_id": memory.get("source_message_id"),
        },
        "score": memory.get("score"),
        "why_relevant": memory.get("why_relevant"),
        "facts": compact_facts(memory.get("facts")),
        "retrieval": compact_retrieval_signals(memory.get("retrieval_signals")),
        "created_at": memory.get("created_at"),
        "updated_at": memory.get("updated_at"),
        "last_used_at": memory.get("last_used_at"),
    }
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


def compact_facts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    facts: list[dict[str, Any]] = []
    for fact in value[:8]:
        if isinstance(fact, dict):
            facts.append(
                {
                    "id": fact.get("id"),
                    "entity": fact.get("entity"),
                    "predicate": fact.get("predicate"),
                    "value": fact.get("value"),
                    "status": fact.get("status"),
                }
            )
    return facts


def compact_retrieval_signals(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    graph = value.get("graph") if isinstance(value.get("graph"), dict) else None
    hybrid = value.get("hybrid") if isinstance(value.get("hybrid"), dict) else None
    payload: dict[str, Any] = {}
    if graph:
        paths = graph.get("paths") if isinstance(graph.get("paths"), list) else []
        payload["graph"] = {
            "score": graph.get("score"),
            "why_relevant": graph.get("why_relevant"),
            "domains": graph.get("domains", []),
            "path_count": len(paths),
            "sample_paths": paths[:2],
        }
    if hybrid:
        payload["hybrid"] = {
            "score": hybrid.get("score"),
            "base_score": hybrid.get("base_score"),
            "dense_score": hybrid.get("dense_score"),
            "rerank_score": hybrid.get("rerank_score"),
            "base_signal": hybrid.get("base_signal"),
            "dense_signal": hybrid.get("dense_signal"),
            "rerank_signal": hybrid.get("rerank_signal"),
            "active_rank_eligible": hybrid.get("active_rank_eligible"),
            "surface_kinds": hybrid.get("surface_kinds", []),
            "promotable_surface_kinds": hybrid.get("promotable_surface_kinds", []),
            "support_surface_kinds": hybrid.get("support_surface_kinds", []),
        }
    return payload


def retrieval_summary(data: dict[str, Any]) -> dict[str, Any]:
    graph = data.get("retrieval_graph") if isinstance(data.get("retrieval_graph"), dict) else {}
    shadow = data.get("retrieval_shadow") if isinstance(data.get("retrieval_shadow"), dict) else {}
    hybrid = data.get("retrieval_hybrid") if isinstance(data.get("retrieval_hybrid"), dict) else {}
    return {
        "stages": data.get("retrieval_stages", []),
        "graph": {
            "backend": graph.get("backend"),
            "status": graph.get("status"),
            "result_count": len(graph.get("results", []))
            if isinstance(graph.get("results"), list)
            else 0,
        },
        "embedding_shadow": {
            "backend": shadow.get("backend"),
            "status": shadow.get("status"),
            "grouped_count": len(shadow.get("grouped_results", []))
            if isinstance(shadow.get("grouped_results"), list)
            else 0,
            "rerank_status": (shadow.get("rerank") or {}).get("status")
            if isinstance(shadow.get("rerank"), dict)
            else None,
        },
        "hybrid": {
            "active": hybrid.get("active"),
            "status": hybrid.get("status"),
            "entry_count": hybrid.get("entry_count"),
            "uses_rerank": hybrid.get("uses_rerank"),
        },
    }


def compact_memory_conflicts(data: dict[str, Any]) -> dict[str, Any]:
    conflicts = data.get("conflicts") if isinstance(data.get("conflicts"), list) else []
    related = data.get("related_overlaps") if isinstance(data.get("related_overlaps"), list) else []
    return {
        "operation": data.get("operation"),
        "model_output_profile": "mind-shell-memory-conflicts-compact-v1",
        "count": data.get("count"),
        "conflict_counts": data.get("conflict_counts", {}),
        "conflicts": [
            compact_conflict(item) for item in conflicts[:20] if isinstance(item, dict)
        ],
        "related_overlap_count": data.get("related_overlap_count", len(related)),
        "related_overlap_examples": [
            compact_conflict(item) for item in related[:5] if isinstance(item, dict)
        ],
        "trace_ids": data.get("trace_ids", []),
        "debug": {
            "full_result_in_trace": True,
            "related_overlaps_are_not_memory_conflicts": True,
        },
    }


def compact_conflict(item: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "classification": item.get("classification"),
        "basis": item.get("basis"),
        "confidence": item.get("confidence"),
        "memory_ids": item.get("memory_ids"),
        "entity": item.get("entity"),
        "predicate": item.get("predicate"),
        "values": item.get("values"),
        "shared_tags": item.get("shared_tags", []),
        "shared_tokens": item.get("shared_tokens", []),
        "reason": item.get("reason"),
    }
    claims = item.get("memory_claims")
    if claims is None and isinstance(item.get("memories"), list):
        claims = [
            {"id": memory.get("id"), "content": memory.get("content")}
            for memory in item["memories"][:2]
            if isinstance(memory, dict)
        ]
    if claims:
        payload["memory_claims"] = claims
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


def annotate_session_window(data: dict[str, Any]) -> dict[str, Any]:
    if "messages" not in data or not isinstance(data.get("messages"), list):
        return data
    updated = dict(data)
    message_count = data.get("message_count")
    returned_count = len(data["messages"])
    has_more = bool(data.get("messages_truncated"))
    updated["transcript_window"] = {
        "returned_count": returned_count,
        "total_message_count": message_count,
        "messages_truncated": has_more,
        "has_more_before_window": has_more,
        "window_position": "latest",
    }
    return updated


def sanitize_for_shell(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: sanitize_for_shell(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_for_shell(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_text(value: str | None) -> str:
    if value is None:
        return ""
    replacements = {
        "GET /mind/schema": "help",
        "POST /mind/memory/write": "memory write",
        "POST /mind/memory/search": "memory search",
        "GET /mind/memory/facts": "memory facts",
        "POST /mind/memory/facts/backfill": "backend fact-backfill maintenance",
        "POST /mind/memory/graph": "memory graph",
        "GET /mind/memory/conflicts": "memory conflicts",
        "POST /mind/memory/deprecate": "memory deprecate",
        "POST /mind/memory/supersede": "memory supersede",
        "GET /mind/sessions/{session_id}": "session open <session_id>",
        "GET /mind/sessions": "session list",
        "POST /mind/sessions/{session_id}/summarize": "session summarize <session_id>",
        "POST /mind/metacognition/step": "metacognition step",
        "POST /mind/focus": "focus",
        "POST /mind/volition": "volition",
        "POST /mind/affect": "affect",
        "mind_api": "mind_shell",
    }
    sanitized = value
    for old, new in replacements.items():
        sanitized = sanitized.replace(old, new)
    sanitized = re.sub(
        r"\b(GET|POST)\s+/mind/[A-Za-z0-9_./{}-]+",
        "mind shell command",
        sanitized,
    )
    return re.sub(r"/mind/[A-Za-z0-9_./{}-]+", "mind shell command", sanitized)


def hint_for_target(target: str) -> str:
    return f"Mind shell executed {target}."

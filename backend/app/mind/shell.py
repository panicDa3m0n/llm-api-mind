import json
import re
import shlex
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.mind.dispatcher import (
    MindAPIContext,
    MindAPIError,
    MindAPIRequest,
    MindAPIResponse,
    dispatch_mind_api,
)
from app.mind.command_registry import (
    COMMAND_REGISTRY_VERSION,
    validate_shell_command,
)
from app.mind.schema import (
    MIND_SHELL_TOOL_SCHEMA,
    build_mind_shell_catalog,
    shell_command_catalog,
    shell_command_usage_guide,
    shell_metadata,
)


class MindShellRequest(BaseModel):
    command: str = Field(min_length=1, max_length=4000)
    intent: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="before")
    @classmethod
    def normalize_model_tool_input(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return {"command": value}
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        raw_input = normalized.get("raw_input")
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                raw_input = {"command": raw_input}
        if isinstance(raw_input, dict):
            unwrapped = dict(raw_input)
            for key, item in normalized.items():
                if key != "raw_input" and key not in unwrapped:
                    unwrapped[key] = item
            normalized = unwrapped

        if "command" not in normalized:
            for alias in ("cmd", "input", "query"):
                if alias in normalized:
                    normalized["command"] = normalized.pop(alias)
                    break
        return normalized


@dataclass(frozen=True)
class ParsedCommand:
    raw: str
    namespace: str
    action: str | None = None
    args: list[str] = field(default_factory=list)
    flags: dict[str, list[str | bool]] = field(default_factory=dict)

    def model_payload(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "action": self.action,
            "args": self.args,
            "flags": self.flags,
        }


def dispatch_mind_shell(
    request: MindShellRequest,
    context: MindAPIContext | None = None,
) -> MindAPIResponse:
    parsed_or_error = _parse_command(request.command)
    if isinstance(parsed_or_error, MindAPIResponse):
        return parsed_or_error
    parsed = parsed_or_error
    intent = request.intent or _default_intent(parsed)

    if parsed.namespace in {"help", "?", "schema", "capabilities"}:
        return _help_response(parsed)

    if parsed.namespace in {"memory", "mem", "remember"}:
        return _memory_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"session", "sessions", "episodic"}:
        return _session_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"focus", "attention"}:
        return _focus_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"volition", "intention", "intentions"}:
        return _volition_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"affect", "emotion", "emotions"}:
        return _affect_command(parsed, context=context, intent=intent)
    if parsed.namespace in {"metacognition", "meta", "reflect"}:
        return _metacognition_command(parsed, context=context, intent=intent)

    return _shell_error(
        code="shell.unknown_namespace",
        message=f"Unknown mind shell namespace: {parsed.namespace}",
        parsed=parsed,
        namespace=None,
        actions=["help", "help memory", "help session", "help focus"],
    )


def _parse_command(command: str) -> ParsedCommand | MindAPIResponse:
    raw = command.strip()
    try:
        tokens = shlex.split(raw)
    except ValueError as exc:
        return _shell_error(
            code="shell.parse_error",
            message=str(exc),
            parsed=None,
            namespace=None,
            actions=["help", "Retry with quoted text closed correctly"],
        )
    if not tokens:
        return _shell_error(
            code="shell.empty_command",
            message="Mind shell command cannot be empty.",
            parsed=None,
            namespace=None,
            actions=["help"],
        )

    namespace = _normalize_token(tokens[0])
    if namespace in {"help", "?", "schema", "capabilities"}:
        action = _normalize_token(tokens[1]) if len(tokens) > 1 else None
        args, flags = _parse_args_and_flags(tokens[2:])
        return ParsedCommand(raw=raw, namespace=namespace, action=action, args=args, flags=flags)

    action = _normalize_token(tokens[1]) if len(tokens) > 1 else None
    args, flags = _parse_args_and_flags(tokens[2:])
    return ParsedCommand(raw=raw, namespace=namespace, action=action, args=args, flags=flags)


def _parse_args_and_flags(tokens: list[str]) -> tuple[list[str], dict[str, list[str | bool]]]:
    args: list[str] = []
    flags: dict[str, list[str | bool]] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and len(token) > 2:
            name, sep, inline_value = token[2:].partition("=")
            normalized = _normalize_flag(name)
            if sep:
                value: str | bool = inline_value
            elif index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                index += 1
                value = tokens[index]
            else:
                value = True
            flags.setdefault(normalized, []).append(value)
        else:
            args.append(token)
        index += 1
    return args, flags


def _memory_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "search"
    if action in {"search", "find"}:
        query = _joined_args(parsed) or _flag_string(parsed, "query", "q")
        if not query:
            return _shell_error(
                code="shell.memory_search_missing_query",
                message="memory search requires a natural-language query.",
                parsed=parsed,
                namespace="memory",
                actions=['memory search "what to find" --top 5'],
            )
        body: dict[str, Any] = {
            "query": query,
            "top_k": _flag_int(parsed, 5, "top", "top-k", "limit"),
        }
        scope = _flag_string(parsed, "scope")
        if scope is not None:
            body["scope"] = scope
        memory_type = _flag_values(parsed, "type", "types")
        if memory_type:
            body["types"] = memory_type
        time_filter = _time_filter(parsed, default_basis="source_conversation")
        if time_filter is not None:
            body["time"] = time_filter
        if _flag_bool(parsed, False, "include-low-confidence", "low-confidence"):
            body["include_low_confidence"] = True
        return _dispatch_api_as_shell(
            parsed,
            target="memory.search",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/search",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"write", "save", "store"}:
        content = _flag_string(parsed, "content") or _joined_args(parsed)
        memory_type = _flag_string(parsed, "type")
        reason = _flag_string(parsed, "reason", "why")
        missing = [
            name
            for name, value in {
                "--type": memory_type,
                "--content": content,
                "--reason": reason,
            }.items()
            if not value
        ]
        if missing:
            return _shell_error(
                code="shell.memory_write_missing_fields",
                message="memory write needs type, content, and reason.",
                parsed=parsed,
                namespace="memory",
                actions=[
                    'memory write --type user_preference --scope user --content "..." --reason "..."',
                    "help memory",
                ],
                details={"missing": missing},
            )
        body = {
            "type": memory_type,
            "content": content,
            "reason_for_storage": reason,
        }
        future_use = _flag_string(parsed, "future-use", "future", "expected-future-use")
        if future_use is not None:
            body["expected_future_use"] = future_use
        scope = _flag_string(parsed, "scope")
        if scope is not None:
            body["scope"] = scope
        return _dispatch_api_as_shell(
            parsed,
            target="memory.write",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/write",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"open", "read", "inspect"}:
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        if not memory_id:
            return _shell_error(
                code="shell.memory_open_missing_id",
                message="memory open requires a memory id.",
                parsed=parsed,
                namespace="memory",
                actions=["memory open mem_..."],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.open",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/memory/{memory_id}",
                body={},
                intent=intent,
            ),
            context=context,
        )
    if action == "graph":
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        if not memory_id:
            return _shell_error(
                code="shell.memory_graph_missing_id",
                message="memory graph requires a memory id.",
                parsed=parsed,
                namespace="memory",
                actions=["memory graph mem_... --depth 2"],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.graph",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/graph",
                body={
                    "memory_id": memory_id,
                    "depth": _flag_int(parsed, 1, "depth", "hops"),
                    "limit": _flag_int(parsed, 30, "limit", "top"),
                    "include_inactive": _flag_bool(parsed, False, "include-inactive"),
                },
                intent=intent,
            ),
            context=context,
        )
    if action == "facts":
        body: dict[str, Any] = {
            "include_inactive": _flag_bool(parsed, False, "include-inactive"),
        }
        for key, flag_names in {
            "memory_id": ("memory-id", "id"),
            "entity": ("entity",),
            "predicate": ("predicate",),
            "query": ("query", "q"),
            "status": ("status",),
        }.items():
            value = _flag_string(parsed, *flag_names)
            if value is not None:
                body[key] = value
        if "query" not in body and parsed.args:
            body["query"] = _joined_args(parsed)
        return _dispatch_api_as_shell(
            parsed,
            target="memory.facts",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/memory/facts",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action == "conflicts":
        return _dispatch_api_as_shell(
            parsed,
            target="memory.conflicts",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/memory/conflicts",
                body={},
                intent=intent,
            ),
            context=context,
        )
    if action == "deprecate":
        memory_id = _first_arg_or_flag(parsed, "id", "memory-id")
        reason = _flag_string(parsed, "reason", "why")
        if not memory_id or not reason:
            return _shell_error(
                code="shell.memory_deprecate_missing_fields",
                message="memory deprecate requires memory id and reason.",
                parsed=parsed,
                namespace="memory",
                actions=['memory deprecate mem_... --reason "..."'],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.deprecate",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/deprecate",
                body={"memory_id": memory_id, "reason": reason},
                intent=intent,
            ),
            context=context,
        )
    if action == "supersede":
        old_memory_id = parsed.args[0] if len(parsed.args) >= 1 else _flag_string(parsed, "old")
        new_memory_id = parsed.args[1] if len(parsed.args) >= 2 else _flag_string(parsed, "new")
        reason = _flag_string(parsed, "reason", "why")
        if not old_memory_id or not new_memory_id or not reason:
            return _shell_error(
                code="shell.memory_supersede_missing_fields",
                message="memory supersede requires old id, new id, and reason.",
                parsed=parsed,
                namespace="memory",
                actions=['memory supersede mem_old mem_new --reason "..."'],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="memory.supersede",
            api_request=MindAPIRequest(
                method="POST",
                path="/mind/memory/supersede",
                body={
                    "old_memory_id": old_memory_id,
                    "new_memory_id": new_memory_id,
                    "reason": reason,
                    "deprecate_old": not _flag_bool(parsed, False, "keep-old-active"),
                },
                intent=intent,
            ),
            context=context,
        )
    validation = validate_shell_command(parsed.raw)
    if validation.get("schema_status") in {"unavailable_by_design", "planned"}:
        suggested = validation.get("suggested_action") or "help memory"
        return _shell_error(
            code="shell.memory_action_unavailable",
            message=(
                f"Memory action '{action}' is "
                f"{validation.get('schema_status')} in the current Mind shell."
            ),
            parsed=parsed,
            namespace="memory",
            actions=[str(suggested), "help memory"],
            details={"command_validation": validation},
        )
    return _shell_error(
        code="shell.memory_unknown_action",
        message=f"Unknown memory action: {action}",
        parsed=parsed,
        namespace="memory",
        actions=["help memory"],
    )


def _session_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "list"
    if action in {"list", "search", "find"}:
        body: dict[str, Any] = {
            "limit": _flag_int(parsed, 10, "limit", "top"),
            "offset": _flag_int(parsed, 0, "offset"),
        }
        query = _flag_string(parsed, "query", "q") or _joined_args(parsed)
        if query:
            body["query"] = query
        time_filter = _time_filter(parsed, default_basis="conversation")
        if time_filter is not None:
            body["time"] = time_filter
        return _dispatch_api_as_shell(
            parsed,
            target="session.list",
            api_request=MindAPIRequest(
                method="GET",
                path="/mind/sessions",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action in {"open", "read", "inspect", "show", "get"}:
        session_id = _first_arg_or_flag(parsed, "id", "session-id")
        if not session_id:
            return _shell_error(
                code="shell.session_open_missing_id",
                message="session open requires a session id.",
                parsed=parsed,
                namespace="session",
                actions=["session open ses_... --limit 200"],
            )
        body = {
            "include_messages": not _flag_bool(parsed, False, "summary-only"),
            "include_memories": not _flag_bool(parsed, False, "no-memories"),
        }
        limit = _flag_int(parsed, 0, "limit", "message-limit")
        if limit > 0:
            body["message_limit"] = limit
        return _dispatch_api_as_shell(
            parsed,
            target="session.open",
            api_request=MindAPIRequest(
                method="GET",
                path=f"/mind/sessions/{session_id}",
                body=body,
                intent=intent,
            ),
            context=context,
        )
    if action == "summarize":
        session_id = _first_arg_or_flag(parsed, "id", "session-id")
        if not session_id:
            return _shell_error(
                code="shell.session_summarize_missing_id",
                message="session summarize requires a session id.",
                parsed=parsed,
                namespace="session",
                actions=["session summarize ses_... --force"],
            )
        return _dispatch_api_as_shell(
            parsed,
            target="session.summarize",
            api_request=MindAPIRequest(
                method="POST",
                path=f"/mind/sessions/{session_id}/summarize",
                body={
                    "force": _flag_bool(parsed, False, "force"),
                    "focus": _flag_string(parsed, "focus"),
                },
                intent=intent,
            ),
            context=context,
        )
    return _shell_error(
        code="shell.session_unknown_action",
        message=f"Unknown session action: {action}",
        parsed=parsed,
        namespace="session",
        actions=["help session"],
    )


def _focus_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "read"
    action = {"open": "read", "inspect": "read", "show": "read", "get": "read", "current": "read"}.get(action, action)
    if action in {"set", "shift"}:
        focus_object = _joined_args(parsed) or _flag_string(parsed, "object")
        if not focus_object:
            return _shell_error(
                code="shell.focus_missing_object",
                message=f"focus {action} requires an object.",
                parsed=parsed,
                namespace="focus",
                actions=[f'focus {action} "what Scarlet is holding" --reason "..."'],
            )
        body: dict[str, Any] = {
            "action": action,
            "object": focus_object,
            "reason": _flag_string(parsed, "reason", "why") or intent,
        }
    else:
        body = {"action": action}
    _copy_flags(
        parsed,
        body,
        {
            "focus_id": ("id", "focus-id"),
            "object": ("object",),
            "type": ("type",),
            "duration_policy": ("duration", "duration-policy"),
            "reason": ("reason", "why"),
            "resolution": ("resolution",),
            "impossible_reason": ("impossible-reason", "reason"),
            "status": ("status",),
            "query": ("query", "q"),
        },
    )
    if parsed.args and action in {"update", "hold", "defer", "resolve", "impossible"}:
        body.setdefault("focus_id", parsed.args[0])
    if action in {"list", "search", "timeline"}:
        body["limit"] = _flag_int(parsed, 10, "limit", "top")
        body["offset"] = _flag_int(parsed, 0, "offset")
        if action == "search" and "query" not in body:
            body["query"] = _joined_args(parsed)
    intensity = _flag_float(parsed, None, "intensity")
    if intensity is not None:
        body["intensity"] = intensity
    return _dispatch_api_as_shell(
        parsed,
        target=f"focus.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/focus",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _volition_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "list_active"
    if action == "list" and parsed.args:
        list_kind = _normalize_token(parsed.args[0])
        if list_kind in {"active", "open"}:
            action = "list_active"
            parsed = ParsedCommand(parsed.raw, parsed.namespace, parsed.action, parsed.args[1:], parsed.flags)
        elif list_kind in {"due", "review"}:
            action = "list_due"
            parsed = ParsedCommand(parsed.raw, parsed.namespace, parsed.action, parsed.args[1:], parsed.flags)
    action = {
        "list-active": "list_active",
        "list_active": "list_active",
        "list-due": "list_due",
        "list_due": "list_due",
        "open": "read",
        "show": "read",
        "get": "read",
        "promote": "promote_to_focus_candidate",
        "promote-to-focus-candidate": "promote_to_focus_candidate",
        "impossible": "mark_impossible",
        "mark-impossible": "mark_impossible",
    }.get(action, action)
    body: dict[str, Any] = {"action": action}
    if action == "create":
        desire = _joined_args(parsed) or _flag_string(parsed, "desire")
        reason = _flag_string(parsed, "reason", "why")
        if not desire or not reason:
            return _shell_error(
                code="shell.volition_create_missing_fields",
                message="volition create requires desire and reason.",
                parsed=parsed,
                namespace="volition",
                actions=['volition create "what I want to keep exploring" --reason "..."'],
            )
        body["desire"] = desire
        body["reason"] = reason
    elif action in {
        "read",
        "update",
        "defer",
        "review",
        "promote_to_focus_candidate",
        "resolve",
        "mark_impossible",
        "deprecate",
    }:
        intention_id = _first_arg_or_flag(parsed, "id", "intention-id")
        if not intention_id:
            return _shell_error(
                code="shell.volition_missing_id",
                message=f"volition {action} requires an intention id.",
                parsed=parsed,
                namespace="volition",
                actions=["volition read int_..."],
            )
        body["intention_id"] = intention_id
    elif action in {"search", "list_active", "list_due"}:
        body["limit"] = _flag_int(parsed, 10, "limit", "top")
        body["offset"] = _flag_int(parsed, 0, "offset")
        if action == "search":
            body["query"] = _joined_args(parsed) or _flag_string(parsed, "query", "q")
        if action == "list_due":
            body["include_unscheduled"] = _flag_bool(parsed, False, "include-unscheduled")
    _copy_flags(
        parsed,
        body,
        {
            "origin": ("origin",),
            "horizon": ("horizon",),
            "autonomy_level": ("autonomy", "autonomy-level"),
            "reason": ("reason", "why"),
            "next_possible_reflection": ("next-reflection",),
            "resolution": ("resolution",),
            "impossible_reason": ("impossible-reason", "reason"),
            "status": ("status",),
            "query": ("query", "q"),
        },
    )
    intensity = _flag_float(parsed, None, "intensity")
    if intensity is not None:
        body["intensity"] = intensity
    return _dispatch_api_as_shell(
        parsed,
        target=f"volition.{action}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/volition",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _affect_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "read"
    body: dict[str, Any] = {
        "action": {
            "history": "list",
            "states": "list",
            "show": "read",
            "get": "read",
            "current": "read",
        }.get(action, action)
    }
    _copy_flags(
        parsed,
        body,
        {
            "affect_id": ("id", "affect-id"),
            "emotion": ("emotion",),
            "mode": ("mode",),
            "status": ("status",),
        },
    )
    body["limit"] = _flag_int(parsed, 10, "limit", "top")
    body["offset"] = _flag_int(parsed, 0, "offset")
    return _dispatch_api_as_shell(
        parsed,
        target=f"affect.{body['action']}",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/affect",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _metacognition_command(
    parsed: ParsedCommand,
    *,
    context: MindAPIContext | None,
    intent: str,
) -> MindAPIResponse:
    action = parsed.action or "step"
    if action != "step":
        return _shell_error(
            code="shell.metacognition_unknown_action",
            message="metacognition currently supports only step.",
            parsed=parsed,
            namespace="metacognition",
            actions=["help metacognition"],
        )
    objective = _flag_string(parsed, "objective") or _joined_args(parsed)
    if not objective:
        return _shell_error(
            code="shell.metacognition_missing_objective",
            message="metacognition step requires an objective.",
            parsed=parsed,
            namespace="metacognition",
            actions=['metacognition step --objective "what to review" --mode critic'],
        )
    body: dict[str, Any] = {
        "objective": objective,
        "mode": _flag_string(parsed, "mode") or "critic",
        "known_evidence": _flag_values(parsed, "evidence", "known-evidence"),
        "uncertainties": _flag_values(parsed, "uncertainty", "uncertainties"),
        "max_findings": _flag_int(parsed, 6, "max-findings", "limit"),
    }
    _copy_flags(
        parsed,
        body,
        {
            "focus_question": ("question", "focus-question"),
            "internal_prompt": ("prompt", "internal-prompt"),
            "draft_answer": ("draft", "draft-answer"),
        },
    )
    return _dispatch_api_as_shell(
        parsed,
        target="metacognition.step",
        api_request=MindAPIRequest(
            method="POST",
            path="/mind/metacognition/step",
            body=body,
            intent=intent,
        ),
        context=context,
    )


def _dispatch_api_as_shell(
    parsed: ParsedCommand,
    *,
    target: str,
    api_request: MindAPIRequest,
    context: MindAPIContext | None,
) -> MindAPIResponse:
    api_response = dispatch_mind_api(api_request, context=context)
    sanitized_result = _sanitize_for_shell(api_response.result)
    model_data = _model_facing_data(target, sanitized_result)
    response = MindAPIResponse(
        ok=api_response.ok,
        result={
            "operation": "mind_shell.command",
            "command": parsed.raw,
            "parsed": parsed.model_payload(),
            "target": target,
            "data": model_data,
        },
        cognitive_hint=_sanitize_text(api_response.cognitive_hint)
        if api_response.cognitive_hint
        else _hint_for_target(target),
        suggested_next_actions=_shell_next_actions(
            target,
            [_sanitize_text(action) for action in api_response.suggested_next_actions],
            ok=api_response.ok,
        ),
        confidence=api_response.confidence,
        usage_guide=None if api_response.ok else _usage_for_target(target, parsed.namespace),
        error=MindAPIError(
            code=api_response.error.code,
            message=_sanitize_text(api_response.error.message),
            recoverable=api_response.error.recoverable,
        )
        if api_response.error is not None
        else None,
    )
    return response


def _help_response(parsed: ParsedCommand) -> MindAPIResponse:
    namespace = parsed.action
    if parsed.namespace in {"schema", "capabilities"}:
        namespace = None
    commands = shell_command_catalog(namespace)
    if namespace and not commands:
        return _shell_error(
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
            "catalog": build_mind_shell_catalog() if namespace is None else {"commands": commands},
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


def _shell_error(
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
            "command_validation": validate_shell_command(parsed.raw) if parsed is not None else None,
            "schema": shell_metadata(),
        },
        cognitive_hint="Correct the command syntax and retry if the cognitive operation is still useful.",
        suggested_next_actions=actions,
        confidence=1.0,
        usage_guide=shell_command_usage_guide(namespace),
        error=MindAPIError(code=code, message=message, recoverable=True),
    )


def _usage_for_target(target: str, namespace: str | None) -> dict[str, Any]:
    guide = shell_command_usage_guide(namespace)
    guide["target"] = target
    return guide


def _shell_next_actions(target: str, actions: list[str], *, ok: bool) -> list[str]:
    defaults = {
        "memory.search": ['memory open mem_...', "memory graph mem_... --depth 2"],
        "memory.write": ['memory open mem_...'],
        "session.list": ["session open ses_..."],
        "session.open": ["memory search \"related fact\" --top 5"],
        "focus.read": ["focus set \"object\" --reason \"...\""],
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


def _model_facing_data(target: str, data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    if target == "memory.search":
        return _compact_memory_search(data)
    if target == "memory.conflicts":
        return _compact_memory_conflicts(data)
    if target == "session.open":
        return _annotate_session_window(data)
    return data


def _compact_memory_search(data: dict[str, Any]) -> dict[str, Any]:
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
            _compact_memory_payload(item)
            for item in data.get("memories", [])
            if isinstance(item, dict)
        ],
        "retrieval_summary": _retrieval_summary(data),
        "trace_ids": data.get("trace_ids", []),
        "debug": {
            "full_result_in_trace": True,
            "omitted_model_fields": omitted,
        },
    }


def _compact_memory_payload(memory: dict[str, Any]) -> dict[str, Any]:
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
        "facts": _compact_facts(memory.get("facts")),
        "retrieval": _compact_retrieval_signals(memory.get("retrieval_signals")),
        "created_at": memory.get("created_at"),
        "updated_at": memory.get("updated_at"),
        "last_used_at": memory.get("last_used_at"),
    }
    return {key: value for key, value in payload.items() if value not in (None, [], {})}


def _compact_facts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    facts: list[dict[str, Any]] = []
    for fact in value[:8]:
        if not isinstance(fact, dict):
            continue
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


def _compact_retrieval_signals(value: Any) -> dict[str, Any]:
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


def _retrieval_summary(data: dict[str, Any]) -> dict[str, Any]:
    graph = data.get("retrieval_graph") if isinstance(data.get("retrieval_graph"), dict) else {}
    shadow = data.get("retrieval_shadow") if isinstance(data.get("retrieval_shadow"), dict) else {}
    hybrid = data.get("retrieval_hybrid") if isinstance(data.get("retrieval_hybrid"), dict) else {}
    return {
        "stages": data.get("retrieval_stages", []),
        "graph": {
            "backend": graph.get("backend"),
            "status": graph.get("status"),
            "result_count": len(graph.get("results", [])) if isinstance(graph.get("results"), list) else 0,
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


def _compact_memory_conflicts(data: dict[str, Any]) -> dict[str, Any]:
    conflicts = data.get("conflicts") if isinstance(data.get("conflicts"), list) else []
    related = data.get("related_overlaps") if isinstance(data.get("related_overlaps"), list) else []
    return {
        "operation": data.get("operation"),
        "model_output_profile": "mind-shell-memory-conflicts-compact-v1",
        "count": data.get("count"),
        "conflict_counts": data.get("conflict_counts", {}),
        "conflicts": [_compact_conflict(item) for item in conflicts[:20] if isinstance(item, dict)],
        "related_overlap_count": data.get("related_overlap_count", len(related)),
        "related_overlap_examples": [
            _compact_conflict(item) for item in related[:5] if isinstance(item, dict)
        ],
        "trace_ids": data.get("trace_ids", []),
        "debug": {
            "full_result_in_trace": True,
            "related_overlaps_are_not_memory_conflicts": True,
        },
    }


def _compact_conflict(item: dict[str, Any]) -> dict[str, Any]:
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


def _annotate_session_window(data: dict[str, Any]) -> dict[str, Any]:
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


def _sanitize_for_shell(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_shell(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_shell(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(value: str | None) -> str:
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
    sanitized = re.sub(r"\b(GET|POST)\s+/mind/[A-Za-z0-9_./{}-]+", "mind shell command", sanitized)
    sanitized = re.sub(r"/mind/[A-Za-z0-9_./{}-]+", "mind shell command", sanitized)
    return sanitized


def _hint_for_target(target: str) -> str:
    return f"Mind shell executed {target}."


def _default_intent(parsed: ParsedCommand) -> str:
    if parsed.namespace in {"help", "schema", "capabilities"}:
        return "Inspect current Mind shell capabilities."
    return f"Use Mind shell command {parsed.namespace} {parsed.action or ''}".strip()


def _normalize_token(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def _normalize_flag(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def _flag_values(parsed: ParsedCommand, *names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        for item in parsed.flags.get(_normalize_flag(name), []):
            if isinstance(item, str):
                values.append(item)
    return values


def _flag_string(parsed: ParsedCommand, *names: str) -> str | None:
    values = _flag_values(parsed, *names)
    return values[-1] if values else None


def _flag_int(parsed: ParsedCommand, default: int, *names: str) -> int:
    value = _flag_string(parsed, *names)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _flag_float(
    parsed: ParsedCommand,
    default: float | None,
    *names: str,
) -> float | None:
    value = _flag_string(parsed, *names)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _flag_bool(parsed: ParsedCommand, default: bool, *names: str) -> bool:
    for name in names:
        values = parsed.flags.get(_normalize_flag(name), [])
        if not values:
            continue
        value = values[-1]
        if isinstance(value, bool):
            return value
        return value.strip().casefold() not in {"0", "false", "no", "off"}
    return default


def _joined_args(parsed: ParsedCommand) -> str | None:
    text = " ".join(parsed.args).strip()
    return text or None


def _first_arg_or_flag(parsed: ParsedCommand, *flag_names: str) -> str | None:
    return parsed.args[0] if parsed.args else _flag_string(parsed, *flag_names)


def _copy_flags(
    parsed: ParsedCommand,
    body: dict[str, Any],
    mapping: dict[str, tuple[str, ...]],
) -> None:
    for target, names in mapping.items():
        value = _flag_string(parsed, *names)
        if value is not None:
            body[target] = value


def _time_filter(
    parsed: ParsedCommand,
    *,
    default_basis: str,
) -> dict[str, Any] | None:
    preset = None
    for candidate in ("today", "yesterday", "last-7-days", "this-session"):
        if _flag_bool(parsed, False, candidate):
            preset = candidate.replace("-", "_")
            break
    explicit_preset = _flag_string(parsed, "time", "preset", "period", "when")
    if explicit_preset:
        preset = explicit_preset.replace("-", "_")
    from_value = _flag_string(parsed, "from", "since")
    to_value = _flag_string(parsed, "to", "until")
    if not preset and not from_value and not to_value:
        return None
    return {
        "preset": preset,
        "from": from_value,
        "to": to_value,
        "basis": _flag_string(parsed, "basis") or default_basis,
    }


__all__ = [
    "MIND_SHELL_TOOL_SCHEMA",
    "MindShellRequest",
    "dispatch_mind_shell",
]

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any


COMMAND_REGISTRY_VERSION = "2026-07-08.mind-shell-command-registry-v1"


@dataclass(frozen=True)
class CommandAction:
    status: str
    canonical: str | None = None
    aliases: tuple[str, ...] = ()
    requires_all: tuple[str, ...] = ()
    requires_any: tuple[str, ...] = ()
    missing_status: str = "missing_required_argument"
    suggested_command: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class CommandFamily:
    aliases: tuple[str, ...]
    default_action: str | None
    actions: dict[str, CommandAction]


COMMAND_FAMILIES: dict[str, CommandFamily] = {
    "help": CommandFamily(
        aliases=("?", "schema", "capabilities"),
        default_action=None,
        actions={"": CommandAction(status="implemented", canonical="")},
    ),
    "memory": CommandFamily(
        aliases=("mem", "remember"),
        default_action="search",
        actions={
            "search": CommandAction(
                status="implemented",
                aliases=("find",),
                requires_any=("arg", "query", "q"),
                suggested_command='memory search "query" --top 5',
            ),
            "write": CommandAction(
                status="implemented",
                aliases=("save", "store"),
                requires_all=("type", "content", "reason|why"),
                suggested_command=(
                    'memory write --type user_preference --scope user '
                    '--content "..." --reason "..."'
                ),
            ),
            "open": CommandAction(
                status="implemented",
                aliases=("read", "inspect", "show", "get"),
                requires_any=("arg", "id", "memory-id"),
                suggested_command="memory open mem_...",
            ),
            "graph": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "memory-id"),
                suggested_command="memory graph mem_... --depth 2",
            ),
            "facts": CommandAction(status="implemented", suggested_command="memory facts --query \"...\""),
            "conflicts": CommandAction(status="implemented", suggested_command="memory conflicts"),
            "deprecate": CommandAction(
                status="implemented",
                requires_all=("arg|id|memory-id", "reason|why"),
                suggested_command='memory deprecate mem_... --reason "..."',
            ),
            "supersede": CommandAction(
                status="implemented",
                requires_all=("arg2|old+new", "reason|why"),
                suggested_command='memory supersede mem_old mem_new --reason "..."',
            ),
            "update": CommandAction(
                status="unavailable_by_design",
                suggested_command=(
                    "Use memory supersede for updated facts or memory deprecate "
                    "when old information is no longer valid."
                ),
                reason="Memories are append-only/versioned for provenance.",
            ),
            "delete": CommandAction(
                status="unavailable_by_design",
                aliases=("remove",),
                suggested_command="Use memory deprecate mem_... --reason \"...\".",
                reason="Hard delete is not exposed to Scarlet; lifecycle changes are traceable.",
            ),
            "merge": CommandAction(
                status="planned",
                suggested_command="Use memory supersede or leave a maintenance note.",
                reason="Automatic merge waits for stronger embedding/KG maintenance.",
            ),
        },
    ),
    "session": CommandFamily(
        aliases=("sessions", "episodic"),
        default_action="list",
        actions={
            "list": CommandAction(status="implemented", aliases=("search", "find")),
            "open": CommandAction(
                status="implemented",
                aliases=("read", "inspect", "show", "get"),
                requires_any=("arg", "id", "session-id"),
                suggested_command="session open ses_... --limit 200",
            ),
            "summarize": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "session-id"),
                suggested_command="session summarize ses_... --force",
            ),
        },
    ),
    "focus": CommandFamily(
        aliases=("attention",),
        default_action="read",
        actions={
            "read": CommandAction(status="implemented", aliases=("open", "inspect", "show", "get", "current")),
            "list": CommandAction(status="implemented"),
            "search": CommandAction(status="implemented"),
            "set": CommandAction(status="implemented", requires_any=("arg", "object")),
            "shift": CommandAction(status="implemented", requires_any=("arg", "object")),
            "update": CommandAction(status="implemented"),
            "hold": CommandAction(status="implemented"),
            "defer": CommandAction(status="implemented"),
            "resolve": CommandAction(
                status="implemented",
                requires_any=("resolution", "reason", "why"),
            ),
            "impossible": CommandAction(
                status="implemented",
                requires_any=("impossible-reason", "reason", "why"),
            ),
            "timeline": CommandAction(status="implemented"),
        },
    ),
    "volition": CommandFamily(
        aliases=("intention", "intentions"),
        default_action="list_active",
        actions={
            "list": CommandAction(status="implemented", aliases=("list-active", "list_active", "list-due", "list_due")),
            "list_active": CommandAction(status="implemented"),
            "list_due": CommandAction(status="implemented"),
            "search": CommandAction(status="implemented"),
            "create": CommandAction(
                status="implemented",
                requires_all=("arg|desire", "reason|why"),
            ),
            "read": CommandAction(status="implemented", aliases=("open", "show", "get"), requires_any=("arg", "id", "intention-id")),
            "update": CommandAction(status="implemented", requires_any=("arg", "id", "intention-id")),
            "defer": CommandAction(status="implemented", requires_any=("arg", "id", "intention-id")),
            "review": CommandAction(status="implemented", requires_any=("arg", "id", "intention-id")),
            "promote_to_focus_candidate": CommandAction(status="implemented", aliases=("promote",), requires_any=("arg", "id", "intention-id")),
            "resolve": CommandAction(
                status="implemented",
                requires_all=("arg|id|intention-id", "resolution|reason|why"),
            ),
            "mark_impossible": CommandAction(
                status="implemented",
                aliases=("impossible",),
                requires_all=("arg|id|intention-id", "impossible-reason|reason|why"),
            ),
            "deprecate": CommandAction(
                status="implemented",
                requires_all=("arg|id|intention-id", "reason|why"),
            ),
        },
    ),
    "affect": CommandFamily(
        aliases=("emotion", "emotions"),
        default_action="read",
        actions={
            "read": CommandAction(status="implemented", aliases=("show", "get", "current")),
            "list": CommandAction(status="implemented", aliases=("history", "states")),
            "prototypes": CommandAction(status="implemented"),
        },
    ),
    "metacognition": CommandFamily(
        aliases=("meta", "reflect"),
        default_action="step",
        actions={
            "step": CommandAction(
                status="implemented",
                requires_any=("arg", "objective"),
                suggested_command='metacognition step --objective "what to review" --mode critic',
            )
        },
    ),
}


def validate_shell_command(command: str | None) -> dict[str, Any]:
    if command is None or not command.strip():
        return _validation(
            command=command or "",
            schema_status="empty_command",
            call_is_available=False,
            suggested_action="Use help to inspect available commands.",
        )
    if "/mind/" in command:
        return _validation(
            command=command,
            schema_status="obsolete_endpoint_language",
            call_is_available=False,
            suggested_action="Use a mind_shell command from help instead.",
        )

    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return _validation(
            command=command,
            schema_status="parse_error",
            call_is_available=False,
            suggested_action="Retry with quoted text closed correctly.",
            details={"error": str(exc)},
        )
    if not tokens:
        return _validation(
            command=command,
            schema_status="empty_command",
            call_is_available=False,
            suggested_action="Use help to inspect available commands.",
        )

    namespace = _normalize_token(tokens[0])
    canonical_namespace = _canonical_namespace(namespace)
    if canonical_namespace is None:
        return _validation(
            command=command,
            namespace=namespace,
            schema_status="unknown_command_family",
            call_is_available=False,
            suggested_action="Use help to inspect available commands.",
        )

    if canonical_namespace == "help":
        action = _normalize_token(tokens[1]) if len(tokens) > 1 else ""
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=action or None,
            canonical_action=action or None,
            schema_status="implemented_command",
            call_is_available=True,
            suggested_command="help",
        )

    family = COMMAND_FAMILIES[canonical_namespace]
    raw_action = _normalize_token(tokens[1]) if len(tokens) > 1 else family.default_action
    canonical_action = _canonical_action(family, raw_action)
    if canonical_action is None:
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=raw_action,
            schema_status="unknown_command_action",
            call_is_available=False,
            suggested_action=f"Use help {canonical_namespace} to inspect supported actions.",
        )

    spec = family.actions[canonical_action]
    has_alias = raw_action != canonical_action
    if spec.status != "implemented":
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=raw_action,
            canonical_action=canonical_action,
            schema_status=spec.status,
            call_is_available=False,
            suggested_action=spec.suggested_command or f"Use help {canonical_namespace}.",
            details={"reason": spec.reason} if spec.reason else {},
        )

    positional_args, flags = _parse_args_and_flags(tokens[2:])
    missing_all = _missing_required_all(spec.requires_all, positional_args, flags)
    if missing_all:
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=raw_action,
            canonical_action=canonical_action,
            schema_status=spec.missing_status,
            call_is_available=False,
            suggested_action=spec.suggested_command or f"Use help {canonical_namespace}.",
            details={"missing": missing_all},
        )
    if spec.requires_any and not _has_required_input(spec.requires_any, positional_args, flags):
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=raw_action,
            canonical_action=canonical_action,
            schema_status=spec.missing_status,
            call_is_available=False,
            suggested_action=spec.suggested_command or f"Use help {canonical_namespace}.",
            details={"required_any": list(spec.requires_any)},
        )

    return _validation(
        command=command,
        namespace=namespace,
        canonical_namespace=canonical_namespace,
        action=raw_action,
        canonical_action=canonical_action,
        schema_status="implemented_command_alias" if has_alias else "implemented_command",
        call_is_available=True,
        suggested_command=(
            _canonical_command(canonical_namespace, canonical_action)
            if has_alias
            else None
        ),
    )


def command_family_summaries() -> list[dict[str, str]]:
    return [
        {
            "namespace": namespace,
            "status": "implemented",
            "default_action": family.default_action or "",
        }
        for namespace, family in COMMAND_FAMILIES.items()
    ]


def _canonical_namespace(namespace: str) -> str | None:
    for canonical, family in COMMAND_FAMILIES.items():
        if namespace == canonical or namespace in family.aliases:
            return canonical
    return None


def _canonical_action(family: CommandFamily, action: str | None) -> str | None:
    normalized = _normalize_token(action or family.default_action or "")
    for canonical, spec in family.actions.items():
        if normalized == _normalize_token(canonical):
            return canonical
        if any(normalized == _normalize_token(alias) for alias in spec.aliases):
            return canonical
    return None


def _parse_args_and_flags(tokens: list[str]) -> tuple[list[str], set[str]]:
    args: list[str] = []
    flags: set[str] = set()
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and len(token) > 2:
            flags.add(_normalize_token(token[2:].split("=", 1)[0]))
            if "=" not in token and index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                index += 1
        else:
            args.append(token)
        index += 1
    return args, flags


def _has_required_input(
    required_any: tuple[str, ...],
    positional_args: list[str],
    flags: set[str],
) -> bool:
    for key in required_any:
        if _requirement_met(key, positional_args, flags):
            return True
    return False


def _missing_required_all(
    required_all: tuple[str, ...],
    positional_args: list[str],
    flags: set[str],
) -> list[str]:
    missing: list[str] = []
    for raw_key in required_all:
        alternatives = tuple(_normalize_token(item) for item in raw_key.split("|"))
        if any(_requirement_met(item, positional_args, flags) for item in alternatives):
            continue
        missing.append(raw_key)
    return missing


def _requirement_met(
    requirement: str,
    positional_args: list[str],
    flags: set[str],
) -> bool:
    normalized = _normalize_token(requirement)
    parts = normalized.split("+")
    if len(parts) > 1:
        return all(_requirement_met(part, positional_args, flags) for part in parts)
    if normalized == "arg":
        return bool(positional_args)
    if normalized.startswith("arg") and normalized[3:].isdigit():
        return len(positional_args) >= int(normalized[3:])
    return normalized in flags


def _canonical_command(namespace: str, action: str | None) -> str:
    if namespace == "help":
        return "help"
    if action:
        return f"{namespace} {action.replace('_', '-')}"
    return namespace


def _normalize_token(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def _validation(
    *,
    command: str,
    schema_status: str,
    call_is_available: bool,
    namespace: str | None = None,
    canonical_namespace: str | None = None,
    action: str | None = None,
    canonical_action: str | None = None,
    suggested_command: str | None = None,
    suggested_action: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "schema_status": schema_status,
        "call_is_available": call_is_available,
    }
    if namespace is not None:
        payload["namespace"] = namespace
    if canonical_namespace is not None:
        payload["canonical_namespace"] = canonical_namespace
    if action is not None:
        payload["action"] = action
    if canonical_action is not None:
        payload["canonical_action"] = canonical_action
    if suggested_command is not None:
        payload["suggested_command"] = suggested_command
    if suggested_action is not None:
        payload["suggested_action"] = suggested_action
    if details:
        payload["details"] = details
    return payload

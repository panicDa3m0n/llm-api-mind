from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.mind.shell_parsing import ShellParseError, normalize_token, parse_command


COMMAND_REGISTRY_VERSION = "2026-08-01.mind-shell-command-registry-v7"


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
            "proposals": CommandAction(
                status="implemented",
                suggested_command="memory proposals --status open --limit 10",
            ),
            "proposal": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "proposal-id"),
                suggested_command="memory proposal prop_...",
            ),
            "proposal-accept": CommandAction(
                status="implemented",
                requires_all=("arg", "reason|why"),
                suggested_command=(
                    'memory proposal-accept prop_... --reason "..."'
                ),
            ),
            "proposal-reject": CommandAction(
                status="implemented",
                requires_all=("arg", "reason|why"),
                suggested_command=(
                    'memory proposal-reject prop_... --reason "..."'
                ),
            ),
            "proposal-duplicate": CommandAction(
                status="implemented",
                requires_all=("arg2", "reason|why"),
                suggested_command=(
                    'memory proposal-duplicate prop_... mem_... --reason "..."'
                ),
            ),
            "proposal-supersede": CommandAction(
                status="implemented",
                requires_all=("arg2", "reason|why"),
                suggested_command=(
                    'memory proposal-supersede prop_... mem_old --reason "..."'
                ),
            ),
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
            "message": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "message-id"),
                suggested_command="session message msg_...",
            ),
            "turn": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "turn-id"),
                suggested_command="session turn turn_...",
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
            "search": CommandAction(
                status="implemented",
                requires_any=("arg", "query", "q"),
                suggested_command='focus search "query" --limit 10',
            ),
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
            "list_active": CommandAction(
                status="implemented",
                aliases=("list", "list-active"),
            ),
            "list_due": CommandAction(status="implemented", aliases=("list-due",)),
            "search": CommandAction(
                status="implemented",
                requires_any=("arg", "query", "q"),
                suggested_command='volition search "query" --limit 10',
            ),
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
    "mode": CommandFamily(
        aliases=("operating-mode",),
        default_action="read",
        actions={
            "read": CommandAction(
                status="implemented",
                aliases=("show", "get", "current"),
            ),
            "list": CommandAction(status="implemented"),
            "set": CommandAction(
                status="implemented",
                requires_all=("arg|mode|tag", "reason|why"),
                suggested_command='mode set scouting --reason "..."',
            ),
        },
    ),
    "perception": CommandFamily(
        aliases=("sense", "senses", "sensor"),
        default_action="status",
        actions={
            "status": CommandAction(
                status="implemented",
                aliases=("list", "available"),
            ),
            "open": CommandAction(
                status="implemented",
                requires_any=("arg", "channel"),
                suggested_command="perception open notifications --limit 10",
            ),
            "read": CommandAction(
                status="implemented",
                aliases=("show", "get", "inspect"),
                requires_any=("arg", "id", "event-id"),
                suggested_command="perception read per_...",
            ),
            "look": CommandAction(
                status="implemented",
                suggested_command="perception look --source camera --seconds 3",
                reason=(
                    "Returns one bounded, current camera observation without "
                    "writing memory or automatic context."
                ),
            ),
        },
    ),
    "episode": CommandFamily(
        aliases=("episodes", "inquiry", "inquiries"),
        default_action="list",
        actions={
            "list": CommandAction(status="implemented"),
            "read": CommandAction(
                status="implemented",
                aliases=("inspect", "show", "get"),
                requires_any=("arg", "id", "episode-id"),
                suggested_command="episode read episode_...",
            ),
            "open": CommandAction(
                status="implemented",
                requires_any=("arg", "candidate", "candidate-id"),
                suggested_command=(
                    'episode open cand_... --question "..." '
                    '--expected-transformation "..."'
                ),
            ),
            "checkpoint": CommandAction(
                status="implemented",
                requires_all=("arg|id|episode-id", "progress"),
                suggested_command=(
                    'episode checkpoint episode_... --progress "..." --next "..."'
                ),
            ),
            "suspend": CommandAction(
                status="implemented",
                requires_all=("arg|id|episode-id", "reason|why"),
                suggested_command=(
                    'episode suspend episode_... --reason "..." --resume-at "..."'
                ),
            ),
            "resume": CommandAction(
                status="implemented",
                requires_any=("arg", "id", "episode-id"),
            ),
            "resolve": CommandAction(
                status="implemented",
                requires_all=("arg|id|episode-id", "resolution"),
            ),
            "abandon": CommandAction(
                status="implemented",
                requires_all=("arg|id|episode-id", "resolution|reason|why"),
            ),
            "reject": CommandAction(
                status="implemented",
                requires_all=("arg|candidate|candidate-id", "reason|why"),
            ),
            "expectation-add": CommandAction(
                status="implemented",
                requires_all=(
                    "arg|id|episode-id",
                    "claim",
                    "observable-outcome",
                ),
            ),
            "expectation-resolve": CommandAction(
                status="implemented",
                requires_all=("arg|expectation|expectation-id", "evaluation"),
            ),
            "wake-list": CommandAction(status="implemented"),
            "wake-add": CommandAction(
                status="implemented",
                requires_any=("at", "event-type"),
            ),
            "wake-cancel": CommandAction(
                status="implemented",
                requires_any=("arg", "condition", "condition-id"),
            ),
        },
    ),
    "lab": CommandFamily(
        aliases=("research", "research-lab"),
        default_action="status",
        actions={
            "status": CommandAction(status="implemented", aliases=("info",)),
            "python": CommandAction(
                status="implemented",
                aliases=("code", "compute"),
                requires_any=("code",),
                suggested_command='lab python --code "from sympy import symbols; print(symbols(\'x\'))"',
            ),
            "web": CommandAction(
                status="implemented",
                suggested_command='lab web open "https://example.org"',
            ),
            "run": CommandAction(
                status="implemented",
                aliases=("open", "inspect"),
                requires_any=("arg", "id", "run-id"),
                suggested_command="lab run labrun_...",
            ),
            "source": CommandAction(
                status="implemented",
                aliases=("read",),
                requires_any=("arg", "id", "source-id"),
                suggested_command="lab source labsrc_...",
            ),
            "artifact": CommandAction(
                status="implemented",
                aliases=("file",),
                requires_any=("arg", "id", "artifact-id"),
                suggested_command="lab artifact labart_...",
            ),
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


# This is deliberately co-located with COMMAND_FAMILIES.  It is the one
# model-facing presentation of commands that the validator below accepts;
# schema/help consumers must never maintain a second catalog elsewhere.
COMMAND_CATALOG_METADATA: dict[str, dict[str, Any]] = {
    "help": {
        "purpose": "Inspect available cognitive command families and examples.",
        "commands": [
            "help",
            "help memory",
            "help session",
            "help focus",
            "help volition",
            "help affect",
            "help mode",
            "help perception",
            "help episode",
            "help lab",
            "help metacognition",
        ],
    },
    "memory": {
        "purpose": "Search, write, inspect, and maintain semantic memories.",
        "commands": [
            'memory search "query" --top 5',
            'memory write --type user_preference --scope user --content "..." --reason "..." --future-use "..."',
            "memory open mem_...",
            "memory graph mem_... --depth 2 --limit 30",
            'memory facts --query "entity or question"',
            "memory proposals --status open --limit 10",
            "memory proposal prop_...",
            'memory proposal-accept prop_... --reason "..."',
            'memory proposal-reject prop_... --reason "..."',
            'memory proposal-duplicate prop_... mem_... --reason "..."',
            'memory proposal-supersede prop_... mem_old --reason "..."',
            "memory conflicts",
            'memory deprecate mem_... --reason "..."',
            'memory supersede mem_old mem_new --reason "..."',
        ],
    },
    "session": {
        "purpose": "Navigate episodic chat sessions, summaries, and transcripts.",
        "commands": [
            'session list --query "topic or date" --limit 5',
            "session open ses_... --limit 200",
            "session message msg_...",
            "session turn turn_...",
            "session summarize ses_... --force",
        ],
    },
    "focus": {
        "purpose": "Read and mutate Scarlet's single foreground focus state.",
        "commands": [
            "focus read",
            "focus list --status active --limit 10",
            'focus search "query" --limit 10',
            'focus set "object" --type investigation --reason "..." --intensity 0.7',
            'focus update --id foc_... --object "..." --reason "..."',
            'focus hold --id foc_... --reason "..."',
            'focus shift "new object" --reason "..."',
            'focus defer --id foc_... --reason "..."',
            'focus resolve --id foc_... --resolution "..."',
            'focus impossible --id foc_... --reason "..."',
            "focus timeline --limit 10",
        ],
    },
    "volition": {
        "purpose": "Manage Scarlet's latent self-generated intentions.",
        "commands": [
            "volition list active --limit 10",
            "volition list due --limit 10",
            'volition search "query" --limit 10',
            'volition create "desire" --reason "..." --candidate-id cand_... --horizon long --intensity 0.6 --next-review-at "2026-07-14T10:00:00+02:00" --review-interval-seconds 86400',
            "volition read int_...",
            'volition update int_... --reason "..."',
            'volition defer int_... --reason "..." --next-review-at "2026-07-14T10:00:00+02:00"',
            'volition review int_... --reason "..." --review-interval-seconds 86400',
            'volition promote int_... --reason "..."',
            'volition resolve int_... --resolution "..."',
            'volition impossible int_... --reason "..."',
            'volition deprecate int_... --reason "..."',
        ],
    },
    "affect": {
        "purpose": "Read backend-appraised affect state and emotion prototypes.",
        "commands": [
            "affect read",
            "affect list --limit 10",
            "affect prototypes",
        ],
    },
    "mode": {
        "purpose": "Inspect or select Scarlet's foreground agent operating posture.",
        "commands": [
            "mode read",
            "mode list",
            'mode set idle --reason "..."',
            'mode set scouting --reason "..."',
        ],
    },
    "perception": {
        "purpose": (
            "Inspect external observation channels and open source-labelled "
            "evidence. Autonomous cognition remains in session history."
        ),
        "commands": [
            "perception status",
            "perception open notifications --limit 10",
            "perception read per_...",
            "perception look --source camera --seconds 3",
        ],
    },
    "episode": {
        "purpose": (
            "Own bounded cognitive inquiries, checkpoints, predictions, and "
            "deterministic wake contracts."
        ),
        "commands": [
            "episode list --status active",
            "episode read episode_...",
            'episode open cand_... --question "..." --expected-transformation "..."',
            'episode checkpoint episode_... --progress "..." --next "..." --source event:evt_...',
            'episode suspend episode_... --reason "..." --resume-at "2026-07-28T09:00:00+02:00"',
            "episode resume episode_...",
            'episode resolve episode_... --resolution "..."',
            'episode reject cand_... --reason "..."',
            'episode expectation-add episode_... --claim "..." --observable-outcome "..."',
            'episode wake-add --episode episode_... --event-type "organ.volition.created"',
            "episode wake-list",
            "episode wake-cancel wake_...",
        ],
    },
    "lab": {
        "purpose": (
            "Run bounded isolated computation and inspect explicit external "
            "research sources without adding them automatically to memory or context."
        ),
        "commands": [
            "lab status",
            'lab web open "https://example.org"',
            'lab python --code "from sympy import symbols; print(symbols(\'x\'))"',
            'lab python --source labsrc_... --code "..."',
            "lab run labrun_...",
            "lab source labsrc_...",
            "lab artifact labart_...",
        ],
    },
    "metacognition": {
        "purpose": "Run one internal metacognitive step when deeper self-review matters.",
        "commands": [
            'metacognition step --objective "..." --mode critic --question "..."',
            'metacognition step --objective "..." --mode memory_curator --draft "..."',
            'metacognition step --objective "..." --mode review_previous_turn --turn-scope previous --detail digest',
        ],
    },
}


def command_catalog(namespace: str | None = None) -> list[dict[str, Any]]:
    """Return executable model-facing shell guidance from the validator source."""

    if namespace is None:
        namespaces = list(COMMAND_FAMILIES)
    else:
        canonical = canonical_command_namespace(namespace)
        namespaces = [canonical] if canonical is not None else []
    return [
        {
            "namespace": item,
            "purpose": COMMAND_CATALOG_METADATA[item]["purpose"],
            "commands": list(COMMAND_CATALOG_METADATA[item]["commands"]),
        }
        for item in namespaces
    ]


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
        parsed = parse_command(command)
    except ShellParseError as exc:
        return _validation(
            command=command,
            schema_status="parse_error",
            call_is_available=False,
            suggested_action="Retry with quoted text closed correctly.",
            details={"error": exc.message},
        )
    namespace = parsed.namespace
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
        action = parsed.action or ""
        if not action:
            return _validation(
                command=command,
                namespace=namespace,
                canonical_namespace=canonical_namespace,
                schema_status="implemented_command",
                call_is_available=True,
                suggested_command="help",
            )
        target_namespace = canonical_command_namespace(action)
        if target_namespace is None:
            return _validation(
                command=command,
                namespace=namespace,
                canonical_namespace=canonical_namespace,
                action=action,
                schema_status="unknown_help_namespace",
                call_is_available=False,
                suggested_action="Use help to inspect available command families.",
            )
        return _validation(
            command=command,
            namespace=namespace,
            canonical_namespace=canonical_namespace,
            action=action or None,
            canonical_action=target_namespace,
            schema_status=(
                "implemented_command_alias"
                if action != target_namespace
                else "implemented_command"
            ),
            call_is_available=True,
            suggested_command=f"help {target_namespace}",
        )

    family = COMMAND_FAMILIES[canonical_namespace]
    raw_action = parsed.action or family.default_action
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

    positional_args, flags = parsed.args, set(parsed.flags)
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


def canonical_command_namespace(namespace: str) -> str | None:
    return _canonical_namespace(normalize_token(namespace))


def canonical_command_action(namespace: str, action: str | None) -> str | None:
    canonical_namespace = canonical_command_namespace(namespace)
    if canonical_namespace is None:
        return None
    return _canonical_action(COMMAND_FAMILIES[canonical_namespace], action)


def _canonical_namespace(namespace: str) -> str | None:
    for canonical, family in COMMAND_FAMILIES.items():
        if namespace == canonical or namespace in family.aliases:
            return canonical
    return None


def _canonical_action(family: CommandFamily, action: str | None) -> str | None:
    normalized = normalize_token(action or family.default_action or "")
    for canonical, spec in family.actions.items():
        if normalized == normalize_token(canonical):
            return canonical
        if any(normalized == normalize_token(alias) for alias in spec.aliases):
            return canonical
    return None


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
        alternatives = tuple(normalize_token(item) for item in raw_key.split("|"))
        if any(_requirement_met(item, positional_args, flags) for item in alternatives):
            continue
        missing.append(raw_key)
    return missing


def _requirement_met(
    requirement: str,
    positional_args: list[str],
    flags: set[str],
) -> bool:
    normalized = normalize_token(requirement)
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

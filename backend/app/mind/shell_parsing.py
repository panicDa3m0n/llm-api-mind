"""Parsing and argument helpers for the model-facing Mind shell.

This module is deliberately side-effect free. It knows the command grammar but
not API routes, cognitive handlers, response compaction, or transport errors.
That separation keeps syntax changes independently testable from shell effects.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Any


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


@dataclass(frozen=True)
class ShellParseError(Exception):
    code: str
    message: str
    actions: list[str]


def parse_command(command: str) -> ParsedCommand:
    """Parse one shell command without coupling parse failures to transport."""

    raw = command.strip()
    try:
        tokens = shlex.split(raw)
    except ValueError as exc:
        raise ShellParseError(
            code="shell.parse_error",
            message=str(exc),
            actions=["help", "Retry with quoted text closed correctly"],
        ) from exc
    if not tokens:
        raise ShellParseError(
            code="shell.empty_command",
            message="Mind shell command cannot be empty.",
            actions=["help"],
        )

    namespace = normalize_token(tokens[0])
    if namespace in {"help", "?", "schema", "capabilities"}:
        action = normalize_token(tokens[1]) if len(tokens) > 1 else None
        args, flags = parse_args_and_flags(tokens[2:])
        return ParsedCommand(raw=raw, namespace=namespace, action=action, args=args, flags=flags)

    action = normalize_token(tokens[1]) if len(tokens) > 1 else None
    args, flags = parse_args_and_flags(tokens[2:])
    return ParsedCommand(raw=raw, namespace=namespace, action=action, args=args, flags=flags)


def parse_args_and_flags(tokens: list[str]) -> tuple[list[str], dict[str, list[str | bool]]]:
    args: list[str] = []
    flags: dict[str, list[str | bool]] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("--") and len(token) > 2:
            name, separator, inline_value = token[2:].partition("=")
            normalized = normalize_flag(name)
            if separator:
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


def normalize_token(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def normalize_flag(value: str) -> str:
    return value.strip().casefold().replace("_", "-")


def flag_values(parsed: ParsedCommand, *names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        for item in parsed.flags.get(normalize_flag(name), []):
            if isinstance(item, str):
                values.append(item)
    return values


def flag_string(parsed: ParsedCommand, *names: str) -> str | None:
    values = flag_values(parsed, *names)
    return values[-1] if values else None


def flag_int(parsed: ParsedCommand, default: int, *names: str) -> int:
    value = flag_string(parsed, *names)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def flag_float(
    parsed: ParsedCommand,
    default: float | None,
    *names: str,
) -> float | None:
    value = flag_string(parsed, *names)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def flag_bool(parsed: ParsedCommand, default: bool, *names: str) -> bool:
    for name in names:
        values = parsed.flags.get(normalize_flag(name), [])
        if not values:
            continue
        value = values[-1]
        if isinstance(value, bool):
            return value
        return value.strip().casefold() not in {"0", "false", "no", "off"}
    return default


def joined_args(parsed: ParsedCommand) -> str | None:
    text = " ".join(parsed.args).strip()
    return text or None


def first_arg_or_flag(parsed: ParsedCommand, *flag_names: str) -> str | None:
    return parsed.args[0] if parsed.args else flag_string(parsed, *flag_names)


def copy_flags(
    parsed: ParsedCommand,
    body: dict[str, Any],
    mapping: dict[str, tuple[str, ...]],
) -> None:
    for target, names in mapping.items():
        value = flag_string(parsed, *names)
        if value is not None:
            body[target] = value


def time_filter(
    parsed: ParsedCommand,
    *,
    default_basis: str,
) -> dict[str, Any] | None:
    preset = None
    for candidate in ("today", "yesterday", "last-7-days", "this-session"):
        if flag_bool(parsed, False, candidate):
            preset = candidate.replace("-", "_")
            break
    explicit_preset = flag_string(parsed, "time", "preset", "period", "when")
    if explicit_preset:
        preset = explicit_preset.replace("-", "_")
    from_value = flag_string(parsed, "from", "since")
    to_value = flag_string(parsed, "to", "until")
    if not preset and not from_value and not to_value:
        return None
    return {
        "preset": preset,
        "from": from_value,
        "to": to_value,
        "basis": flag_string(parsed, "basis") or default_basis,
    }

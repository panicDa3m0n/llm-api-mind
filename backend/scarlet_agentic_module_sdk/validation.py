"""Capability-level validation shared by the SDK conformance kit and host."""

from __future__ import annotations

from scarlet_agentic_module_sdk.contracts import (
    AgenticModuleManifest,
    ContextCapability,
    ContextPortResult,
    EventCapability,
    EventPortResult,
    PromptCapability,
    PromptPortResult,
)


DEFAULT_AGENT_MODE_TAGS = ("idle", "interactive", "scouting")


def unknown_mode_tags(
    manifest: AgenticModuleManifest,
    *,
    known_mode_tags: tuple[str, ...] = DEFAULT_AGENT_MODE_TAGS,
) -> list[str]:
    """Return manifest mode tags not recognized by the selected Core catalog."""

    return sorted(set(manifest.mode_tags) - set(known_mode_tags))


def validate_context_result(
    result: ContextPortResult,
    capability: ContextCapability,
) -> None:
    if len(result.contributions) > capability.max_contributions:
        raise ValueError("module returned more context contributions than declared")
    allowed = set(capability.produces_block_types)
    if any(item.block_type not in allowed for item in result.contributions):
        raise ValueError("module returned an undeclared context block type")


def validate_prompt_result(
    result: PromptPortResult,
    *,
    allowed_slots: list[str],
    max_characters: int,
) -> None:
    allowed = set(allowed_slots)
    if any(item.slot not in allowed for item in result.contributions):
        raise ValueError("module returned a prompt contribution for a disallowed slot")
    if sum(len(item.text) for item in result.contributions) > max_characters:
        raise ValueError("module exceeded the prompt character budget")


def validate_event_result(
    result: EventPortResult,
    capability: EventCapability,
) -> None:
    allowed = set(capability.publishes)
    if any(item.event_type not in allowed for item in result.publications):
        raise ValueError("module published an undeclared event type")


def context_capabilities(
    manifest: AgenticModuleManifest,
) -> list[ContextCapability]:
    return [
        item for item in manifest.capabilities if isinstance(item, ContextCapability)
    ]


def prompt_capabilities(
    manifest: AgenticModuleManifest,
) -> list[PromptCapability]:
    return [
        item for item in manifest.capabilities if isinstance(item, PromptCapability)
    ]


def event_capabilities(manifest: AgenticModuleManifest) -> list[EventCapability]:
    return [item for item in manifest.capabilities if isinstance(item, EventCapability)]

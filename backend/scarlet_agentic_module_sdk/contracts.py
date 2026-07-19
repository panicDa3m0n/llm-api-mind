"""Versioned public contracts shared by Agentic Modules and the Core host.

This module defines data only. Discovery, process execution, persistence, and
permission enforcement remain Core host responsibilities.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


__all__ = [
    "AGENTIC_MODULE_LIFECYCLE_VERSION",
    "AGENTIC_MODULE_MANIFEST_VERSION",
    "AGENTIC_MODULE_PORT_VERSION",
    "DEFAULT_CORE_MODULE_CONTRACTS",
    "AgenticModuleManifest",
    "CommandCapability",
    "CommandCatalogResult",
    "CommandDescriptor",
    "CommandPortRequest",
    "CommandPortResult",
    "ContextCapability",
    "ContextContribution",
    "ContextInputBlock",
    "ContextPortBudget",
    "ContextPortRequest",
    "ContextPortResult",
    "ContractModel",
    "CoreCompatibility",
    "EventCapability",
    "EventPortRequest",
    "EventPortResult",
    "HealthPortRequest",
    "HealthPortResult",
    "ModuleCapability",
    "ModuleDependency",
    "ModuleError",
    "ModuleEvent",
    "ModuleHealth",
    "ModuleLifecycle",
    "ModuleLifecycleEvent",
    "ModuleLifecyclePhase",
    "ModulePermission",
    "ModuleResources",
    "ModuleRuntime",
    "ModuleTimeouts",
    "PortCallContext",
    "PromptCapability",
    "PromptContribution",
    "PromptPortRequest",
    "PromptPortResult",
    "compare_semver",
    "validate_semver",
]


AGENTIC_MODULE_MANIFEST_VERSION = "agentic-module-manifest-v1"
AGENTIC_MODULE_PORT_VERSION = "agentic-module-port-v1"
AGENTIC_MODULE_LIFECYCLE_VERSION = "agentic-module-lifecycle-v1"
DEFAULT_CORE_MODULE_CONTRACTS = {
    "agentic-module-port": AGENTIC_MODULE_PORT_VERSION,
    "agentic-module-lifecycle": AGENTIC_MODULE_LIFECYCLE_VERSION,
}

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
_MODULE_ID_PATTERN = r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$"
_NAME_PATTERN = r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"


class ContractModel(BaseModel):
    """Strict base model for every public module contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_semver(value: str) -> str:
    """Return a valid SemVer 2.0 string or raise a stable validation error."""

    match = _SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError("must be a SemVer 2.0 value such as 1.2.3")
    prerelease = match.group("prerelease")
    if prerelease is not None and any(
        part.isdigit() and len(part) > 1 and part.startswith("0")
        for part in prerelease.split(".")
    ):
        raise ValueError(
            "numeric SemVer prerelease identifiers cannot have leading zeroes"
        )
    return value


def compare_semver(left: str, right: str) -> int:
    """Compare two validated SemVer 2.0 values by precedence."""

    left_parts = _semver_parts(validate_semver(left))
    right_parts = _semver_parts(validate_semver(right))
    for left_number, right_number in zip(left_parts[:3], right_parts[:3], strict=True):
        if left_number != right_number:
            return -1 if left_number < right_number else 1
    return _compare_prerelease(left_parts[3], right_parts[3])


def _semver_parts(value: str) -> tuple[int, int, int, str | None]:
    match = _SEMVER_RE.fullmatch(value)
    if match is None:  # pragma: no cover - guarded by validate_semver
        raise ValueError("invalid semantic version")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        match.group("prerelease"),
    )


def _compare_prerelease(left: str | None, right: str | None) -> int:
    if left is None and right is None:
        return 0
    if left is None:
        return 1
    if right is None:
        return -1
    left_parts = left.split(".")
    right_parts = right.split(".")
    for left_part, right_part in zip(left_parts, right_parts, strict=False):
        if left_part == right_part:
            continue
        left_numeric = left_part.isdigit()
        right_numeric = right_part.isdigit()
        if left_numeric and right_numeric:
            return -1 if int(left_part) < int(right_part) else 1
        if left_numeric != right_numeric:
            return -1 if left_numeric else 1
        return -1 if left_part < right_part else 1
    if len(left_parts) == len(right_parts):
        return 0
    return -1 if len(left_parts) < len(right_parts) else 1


class ModulePermission(str, Enum):
    """Complete allowlist of Core capabilities visible to a module."""

    CONTEXT_READ = "context.read"
    CONTEXT_CONTRIBUTE = "context.contribute"
    PROMPT_CONTRIBUTE = "prompt.contribute"
    COMMAND_REGISTER = "command.register"
    EVENT_SUBSCRIBE = "event.subscribe"
    EVENT_PUBLISH = "event.publish"
    MODULE_STATE_READ = "module_state.read"
    MODULE_STATE_WRITE = "module_state.write"


class CoreCompatibility(ContractModel):
    minimum_core_version: str
    maximum_core_version_exclusive: str | None = None
    required_contracts: dict[str, str] = Field(default_factory=dict)

    @field_validator("minimum_core_version", "maximum_core_version_exclusive")
    @classmethod
    def _validate_versions(cls, value: str | None) -> str | None:
        return validate_semver(value) if value is not None else None

    @field_validator("required_contracts")
    @classmethod
    def _validate_contract_versions(cls, value: dict[str, str]) -> dict[str, str]:
        for contract_name, contract_version in value.items():
            if re.fullmatch(_NAME_PATTERN, contract_name) is None:
                raise ValueError(f"invalid contract name: {contract_name}")
            if not contract_version.strip():
                raise ValueError(f"empty contract version for {contract_name}")
        return value

    @model_validator(mode="after")
    def _validate_range(self) -> CoreCompatibility:
        maximum = self.maximum_core_version_exclusive
        if (
            maximum is not None
            and compare_semver(maximum, self.minimum_core_version) <= 0
        ):
            raise ValueError(
                "maximum_core_version_exclusive must be greater than minimum_core_version"
            )
        return self

    def supports(self, core_version: str) -> bool:
        if compare_semver(core_version, self.minimum_core_version) < 0:
            return False
        maximum = self.maximum_core_version_exclusive
        return maximum is None or compare_semver(core_version, maximum) < 0


class ModuleDependency(ContractModel):
    module_id: str = Field(pattern=_MODULE_ID_PATTERN)
    minimum_version: str
    maximum_version_exclusive: str | None = None
    optional: bool = False

    @field_validator("minimum_version", "maximum_version_exclusive")
    @classmethod
    def _validate_versions(cls, value: str | None) -> str | None:
        return validate_semver(value) if value is not None else None

    @model_validator(mode="after")
    def _validate_range(self) -> ModuleDependency:
        maximum = self.maximum_version_exclusive
        if maximum is not None and compare_semver(maximum, self.minimum_version) <= 0:
            raise ValueError(
                "maximum_version_exclusive must be greater than minimum_version"
            )
        return self

    def accepts(self, module_version: str) -> bool:
        if compare_semver(module_version, self.minimum_version) < 0:
            return False
        maximum = self.maximum_version_exclusive
        return maximum is None or compare_semver(module_version, maximum) < 0


class ContextCapability(ContractModel):
    kind: Literal["context"] = "context"
    capability_id: str = Field(pattern=_NAME_PATTERN)
    port_version: Literal["agentic-module-port-v1"] = "agentic-module-port-v1"
    produces_block_types: list[str] = Field(min_length=1, max_length=20)
    max_contributions: int = Field(default=5, ge=1, le=100)

    @field_validator("produces_block_types")
    @classmethod
    def _unique_block_types(cls, value: list[str]) -> list[str]:
        return _unique_names(value, field_name="produces_block_types")


class PromptCapability(ContractModel):
    kind: Literal["prompt"] = "prompt"
    capability_id: str = Field(pattern=_NAME_PATTERN)
    port_version: Literal["agentic-module-port-v1"] = "agentic-module-port-v1"
    slots: list[Literal["policy_appendix", "turn_context"]] = Field(
        min_length=1,
        max_length=2,
    )
    max_characters: int = Field(default=4000, ge=1, le=20000)

    @field_validator("slots")
    @classmethod
    def _unique_slots(cls, value: list[str]) -> list[str]:
        return _unique_names(value, field_name="slots")


class CommandCapability(ContractModel):
    kind: Literal["command"] = "command"
    capability_id: str = Field(pattern=_NAME_PATTERN)
    port_version: Literal["agentic-module-port-v1"] = "agentic-module-port-v1"
    namespace: str = Field(pattern=_NAME_PATTERN)
    commands: list[str] = Field(min_length=1, max_length=100)

    @field_validator("commands")
    @classmethod
    def _unique_commands(cls, value: list[str]) -> list[str]:
        return _unique_names(value, field_name="commands")


class EventCapability(ContractModel):
    kind: Literal["event"] = "event"
    capability_id: str = Field(pattern=_NAME_PATTERN)
    port_version: Literal["agentic-module-port-v1"] = "agentic-module-port-v1"
    subscribes_to: list[str] = Field(default_factory=list, max_length=100)
    publishes: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("subscribes_to", "publishes")
    @classmethod
    def _unique_event_types(cls, value: list[str], info: Any) -> list[str]:
        return _unique_names(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _require_event_direction(self) -> EventCapability:
        if not self.subscribes_to and not self.publishes:
            raise ValueError("event capability must subscribe, publish, or both")
        return self


ModuleCapability = Annotated[
    ContextCapability | PromptCapability | CommandCapability | EventCapability,
    Field(discriminator="kind"),
]


class ModuleResources(ContractModel):
    max_memory_mb: int = Field(default=256, ge=32, le=8192)
    max_cpu_percent: int = Field(default=50, ge=1, le=400)
    max_concurrent_calls: int = Field(default=1, ge=1, le=64)
    max_request_bytes: int = Field(default=1_000_000, ge=1024, le=50_000_000)
    max_response_bytes: int = Field(default=1_000_000, ge=1024, le=50_000_000)


class ModuleTimeouts(ContractModel):
    startup_seconds: float = Field(default=10.0, gt=0, le=300)
    call_seconds: float = Field(default=30.0, gt=0, le=900)
    health_seconds: float = Field(default=5.0, gt=0, le=60)
    shutdown_seconds: float = Field(default=10.0, gt=0, le=300)


class ModuleHealth(ContractModel):
    interval_seconds: float = Field(default=30.0, ge=5.0, le=3600)
    failure_threshold: int = Field(default=3, ge=1, le=20)
    recovery_threshold: int = Field(default=1, ge=1, le=20)


class ModuleLifecycle(ContractModel):
    protocol_version: Literal["agentic-module-lifecycle-v1"] = (
        "agentic-module-lifecycle-v1"
    )
    startup: Literal["eager", "lazy"] = "lazy"
    restart: Literal["never", "on_failure"] = "on_failure"
    max_restarts: int = Field(default=3, ge=0, le=20)

    @model_validator(mode="after")
    def _validate_restart_policy(self) -> ModuleLifecycle:
        if self.restart == "never" and self.max_restarts != 0:
            raise ValueError("max_restarts must be 0 when restart is never")
        return self


ModuleLifecyclePhase = Literal[
    "discover",
    "validate",
    "load",
    "start",
    "health",
    "stop",
    "failure",
]


class ModuleLifecycleEvent(ContractModel):
    module_id: str = Field(pattern=_MODULE_ID_PATTERN)
    phase: ModuleLifecyclePhase
    status: Literal["started", "succeeded", "failed", "skipped"]
    occurred_at: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class ModuleRuntime(ContractModel):
    transport: Literal["stdio-json-v1"] = "stdio-json-v1"
    entrypoint: list[str] = Field(min_length=1, max_length=16)

    @field_validator("entrypoint")
    @classmethod
    def _validate_entrypoint(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("entrypoint arguments must not be empty")
        return value


_REQUIRED_PERMISSION_BY_KIND: dict[str, ModulePermission] = {
    "context": ModulePermission.CONTEXT_CONTRIBUTE,
    "prompt": ModulePermission.PROMPT_CONTRIBUTE,
    "command": ModulePermission.COMMAND_REGISTER,
}


class AgenticModuleManifest(ContractModel):
    schema_version: Literal["agentic-module-manifest-v1"] = "agentic-module-manifest-v1"
    module_id: str = Field(pattern=_MODULE_ID_PATTERN)
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=1000)
    module_version: str
    core_compatibility: CoreCompatibility
    mode_tags: list[str] = Field(min_length=1, max_length=20)
    capabilities: list[ModuleCapability] = Field(min_length=1, max_length=100)
    permissions: set[ModulePermission] = Field(default_factory=set, max_length=20)
    dependencies: list[ModuleDependency] = Field(default_factory=list, max_length=100)
    runtime: ModuleRuntime
    resources: ModuleResources = Field(default_factory=ModuleResources)
    timeouts: ModuleTimeouts = Field(default_factory=ModuleTimeouts)
    health: ModuleHealth = Field(default_factory=ModuleHealth)
    lifecycle: ModuleLifecycle = Field(default_factory=ModuleLifecycle)

    @field_validator("module_version")
    @classmethod
    def _validate_module_version(cls, value: str) -> str:
        return validate_semver(value)

    @field_validator("mode_tags")
    @classmethod
    def _validate_mode_tags(cls, value: list[str]) -> list[str]:
        return _unique_names(value, field_name="mode_tags")

    @model_validator(mode="after")
    def _validate_manifest_relationships(self) -> AgenticModuleManifest:
        capability_ids = [item.capability_id for item in self.capabilities]
        _require_unique(capability_ids, field_name="capability ids")
        dependency_ids = [item.module_id for item in self.dependencies]
        _require_unique(dependency_ids, field_name="dependency ids")
        if self.module_id in dependency_ids:
            raise ValueError("a module cannot depend on itself")

        required_permissions = {
            permission
            for capability in self.capabilities
            if (permission := _REQUIRED_PERMISSION_BY_KIND.get(capability.kind))
            is not None
        }
        for capability in self.capabilities:
            if capability.kind != "event":
                continue
            if capability.subscribes_to:
                required_permissions.add(ModulePermission.EVENT_SUBSCRIBE)
            if capability.publishes:
                required_permissions.add(ModulePermission.EVENT_PUBLISH)
        missing = required_permissions - self.permissions
        if missing:
            values = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"capabilities require undeclared permissions: {values}")
        return self


class PortCallContext(ContractModel):
    protocol_version: Literal["agentic-module-port-v1"] = "agentic-module-port-v1"
    request_id: str = Field(min_length=1, max_length=120)
    module_id: str = Field(pattern=_MODULE_ID_PATTERN)
    core_version: str
    active_mode_tag: str = Field(pattern=_NAME_PATTERN)
    session_id: str | None = Field(default=None, max_length=120)
    turn_id: str | None = Field(default=None, max_length=120)
    deadline_at: datetime

    @field_validator("core_version")
    @classmethod
    def _validate_core_version(cls, value: str) -> str:
        return validate_semver(value)


class ContextPortBudget(ContractModel):
    max_tokens: int = Field(ge=0, le=100_000)
    max_items: int = Field(ge=0, le=1000)


class ContextInputBlock(ContractModel):
    block_id: str = Field(min_length=1, max_length=160)
    block_type: str = Field(pattern=_NAME_PATTERN)
    content: dict[str, Any] = Field(default_factory=dict)


class ContextPortRequest(ContractModel):
    context: PortCallContext
    budget: ContextPortBudget
    inputs: list[ContextInputBlock] = Field(default_factory=list, max_length=100)


class ContextContribution(ContractModel):
    contribution_id: str = Field(min_length=1, max_length=160)
    block_type: str = Field(pattern=_NAME_PATTERN)
    content: dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: int = Field(ge=0, le=100_000)
    priority: int = Field(default=50, ge=0, le=100)


class ContextPortResult(ContractModel):
    contributions: list[ContextContribution] = Field(
        default_factory=list, max_length=100
    )


class PromptPortRequest(ContractModel):
    context: PortCallContext
    slots: list[Literal["policy_appendix", "turn_context"]] = Field(min_length=1)
    max_characters: int = Field(ge=1, le=20_000)


class PromptContribution(ContractModel):
    contribution_id: str = Field(min_length=1, max_length=160)
    slot: Literal["policy_appendix", "turn_context"]
    text: str = Field(min_length=1, max_length=20_000)
    priority: int = Field(default=50, ge=0, le=100)


class PromptPortResult(ContractModel):
    contributions: list[PromptContribution] = Field(default_factory=list, max_length=20)


class CommandDescriptor(ContractModel):
    name: str = Field(pattern=_NAME_PATTERN)
    description: str = Field(min_length=1, max_length=500)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class CommandCatalogResult(ContractModel):
    namespace: str = Field(pattern=_NAME_PATTERN)
    commands: list[CommandDescriptor] = Field(min_length=1, max_length=100)


class CommandPortRequest(ContractModel):
    context: PortCallContext
    namespace: str = Field(pattern=_NAME_PATTERN)
    command: str = Field(pattern=_NAME_PATTERN)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModuleError(ContractModel):
    code: str = Field(pattern=_NAME_PATTERN)
    message: str = Field(min_length=1, max_length=2000)
    retryable: bool = False


class CommandPortResult(ContractModel):
    status: Literal["success", "error"]
    output: dict[str, Any] = Field(default_factory=dict)
    error: ModuleError | None = None

    @model_validator(mode="after")
    def _validate_status(self) -> CommandPortResult:
        if (self.status == "error") != (self.error is not None):
            raise ValueError(
                "error details must be present exactly when status is error"
            )
        return self


class ModuleEvent(ContractModel):
    event_id: str = Field(min_length=1, max_length=160)
    event_type: str = Field(pattern=_NAME_PATTERN)
    occurred_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


class EventPortRequest(ContractModel):
    context: PortCallContext
    event: ModuleEvent


class EventPortResult(ContractModel):
    acknowledged: bool = True
    publications: list[ModuleEvent] = Field(default_factory=list, max_length=100)


class HealthPortRequest(ContractModel):
    context: PortCallContext


class HealthPortResult(ContractModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    details: dict[str, Any] = Field(default_factory=dict)


def _unique_names(value: list[str], *, field_name: str) -> list[str]:
    for item in value:
        if re.fullmatch(_NAME_PATTERN, item) is None:
            raise ValueError(f"invalid {field_name} value: {item}")
    _require_unique(value, field_name=field_name)
    return value


def _require_unique(values: list[str], *, field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")

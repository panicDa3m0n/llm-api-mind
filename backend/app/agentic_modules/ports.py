"""Typed port routing and bounded contribution composition for Module Host."""

from __future__ import annotations

from typing import Any, Callable, Protocol

from pydantic import Field

from app.agentic_modules.contracts import (
    CommandCapability,
    CommandPortRequest,
    CommandPortResult,
    ContextCapability,
    ContextContribution,
    ContextInputBlock,
    ContextPortBudget,
    ContextPortRequest,
    ContextPortResult,
    ContractModel,
    EventCapability,
    EventPortRequest,
    EventPortResult,
    HealthPortRequest,
    HealthPortResult,
    ModuleEvent,
    ModulePermission,
    PortCallContext,
    PromptCapability,
    PromptContribution,
    PromptPortRequest,
    PromptPortResult,
)
from app.agentic_modules.registry import RegisteredModule
from app.agentic_modules.telemetry import ModuleReceipt


class HostedContextContribution(ContractModel):
    module_id: str
    capability_id: str
    contribution: ContextContribution


class HostedPromptContribution(ContractModel):
    module_id: str
    capability_id: str
    contribution: PromptContribution


class ModuleContextBatch(ContractModel):
    contributions: list[HostedContextContribution] = Field(default_factory=list)
    receipts: list[ModuleReceipt] = Field(default_factory=list)


class ModulePromptBatch(ContractModel):
    contributions: list[HostedPromptContribution] = Field(default_factory=list)
    receipts: list[ModuleReceipt] = Field(default_factory=list)


class ModuleEventBatch(ContractModel):
    publications: list[ModuleEvent] = Field(default_factory=list)
    receipts: list[ModuleReceipt] = Field(default_factory=list)


class ModulePortHost(Protocol):
    @property
    def running_module_ids(self) -> list[str]: ...

    def _registration(self, module_id: str) -> RegisteredModule: ...

    def _call_context(
        self,
        module_id: str,
        *,
        session_id: str | None,
        turn_id: str | None,
    ) -> PortCallContext: ...

    def _command_routes(
        self,
    ) -> dict[tuple[str, str], tuple[str, CommandCapability]]: ...

    async def _call_model(
        self,
        module_id: str,
        *,
        operation: str,
        payload: dict[str, Any],
        result_model: type[ContractModel],
        request_id: str,
        capability_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        timeout_seconds: float | None = None,
        result_validator: Callable[[Any], None] | None = None,
    ) -> tuple[Any | None, ModuleReceipt]: ...


async def collect_health(
    host: ModulePortHost,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> dict[str, HealthPortResult]:
    results: dict[str, HealthPortResult] = {}
    for module_id in host.running_module_ids:
        request = HealthPortRequest(
            context=host._call_context(
                module_id,
                session_id=session_id,
                turn_id=turn_id,
            )
        )
        result, _ = await host._call_model(
            module_id,
            operation="health",
            payload=request.model_dump(mode="json"),
            result_model=HealthPortResult,
            request_id=request.context.request_id,
            session_id=session_id,
            turn_id=turn_id,
            timeout_seconds=host._registration(
                module_id
            ).manifest.timeouts.health_seconds,
        )
        if result is not None:
            results[module_id] = result
    return results


async def collect_context(
    host: ModulePortHost,
    *,
    budget: ContextPortBudget,
    inputs: list[ContextInputBlock] | None = None,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> ModuleContextBatch:
    candidates: list[tuple[int, int, HostedContextContribution]] = []
    receipts: list[ModuleReceipt] = []
    for module_index, module_id in enumerate(list(host.running_module_ids)):
        if module_id not in host.running_module_ids:
            continue
        manifest = host._registration(module_id).manifest
        for capability in capabilities(manifest.capabilities, ContextCapability):
            request = ContextPortRequest(
                context=host._call_context(
                    module_id,
                    session_id=session_id,
                    turn_id=turn_id,
                ),
                budget=budget,
                inputs=(
                    inputs or []
                    if ModulePermission.CONTEXT_READ in manifest.permissions
                    else []
                ),
            )
            result, receipt = await host._call_model(
                module_id,
                operation="context.contribute",
                capability_id=capability.capability_id,
                payload=request.model_dump(mode="json"),
                result_model=ContextPortResult,
                request_id=request.context.request_id,
                session_id=session_id,
                turn_id=turn_id,
                result_validator=lambda value: validate_context_result(
                    value, capability
                ),
            )
            receipts.append(receipt)
            if result is None:
                continue
            for local_index, contribution in enumerate(result.contributions):
                candidates.append(
                    (
                        module_index,
                        local_index,
                        HostedContextContribution(
                            module_id=module_id,
                            capability_id=capability.capability_id,
                            contribution=contribution,
                        ),
                    )
                )
    ordered = sorted(
        candidates,
        key=lambda item: (-item[2].contribution.priority, item[0], item[1]),
    )
    selected: list[HostedContextContribution] = []
    used_tokens = 0
    for _, _, item in ordered:
        estimated = item.contribution.estimated_tokens
        if len(selected) >= budget.max_items:
            break
        if used_tokens + estimated > budget.max_tokens:
            continue
        selected.append(item)
        used_tokens += estimated
    return ModuleContextBatch(contributions=selected, receipts=receipts)


async def collect_prompt(
    host: ModulePortHost,
    *,
    slots: list[str],
    max_characters: int,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> ModulePromptBatch:
    candidates: list[tuple[int, int, HostedPromptContribution]] = []
    receipts: list[ModuleReceipt] = []
    for module_index, module_id in enumerate(list(host.running_module_ids)):
        if module_id not in host.running_module_ids:
            continue
        manifest = host._registration(module_id).manifest
        for capability in capabilities(manifest.capabilities, PromptCapability):
            allowed_slots = [slot for slot in slots if slot in capability.slots]
            if not allowed_slots:
                continue
            request = PromptPortRequest(
                context=host._call_context(
                    module_id,
                    session_id=session_id,
                    turn_id=turn_id,
                ),
                slots=allowed_slots,
                max_characters=min(max_characters, capability.max_characters),
            )
            result, receipt = await host._call_model(
                module_id,
                operation="prompt.contribute",
                capability_id=capability.capability_id,
                payload=request.model_dump(mode="json"),
                result_model=PromptPortResult,
                request_id=request.context.request_id,
                session_id=session_id,
                turn_id=turn_id,
                result_validator=lambda value: validate_prompt_result(
                    value,
                    allowed_slots=allowed_slots,
                    max_characters=request.max_characters,
                ),
            )
            receipts.append(receipt)
            if result is None:
                continue
            for local_index, contribution in enumerate(result.contributions):
                candidates.append(
                    (
                        module_index,
                        local_index,
                        HostedPromptContribution(
                            module_id=module_id,
                            capability_id=capability.capability_id,
                            contribution=contribution,
                        ),
                    )
                )
    ordered = sorted(
        candidates,
        key=lambda item: (-item[2].contribution.priority, item[0], item[1]),
    )
    selected: list[HostedPromptContribution] = []
    used_characters = 0
    for _, _, item in ordered:
        size = len(item.contribution.text)
        if used_characters + size > max_characters:
            continue
        selected.append(item)
        used_characters += size
    return ModulePromptBatch(contributions=selected, receipts=receipts)


async def invoke_command(
    host: ModulePortHost,
    *,
    namespace: str,
    command: str,
    arguments: dict[str, Any] | None = None,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> CommandPortResult:
    module_id, capability = host._command_routes().get(
        (namespace, command), (None, None)
    )
    if module_id is None or capability is None:
        return CommandPortResult(
            status="error",
            error={
                "code": "command.unavailable",
                "message": "No active module declares this command.",
                "retryable": False,
            },
        )
    request = CommandPortRequest(
        context=host._call_context(
            module_id,
            session_id=session_id,
            turn_id=turn_id,
        ),
        namespace=namespace,
        command=command,
        arguments=arguments or {},
    )
    result, _ = await host._call_model(
        module_id,
        operation="command.invoke",
        capability_id=capability.capability_id,
        payload=request.model_dump(mode="json"),
        result_model=CommandPortResult,
        request_id=request.context.request_id,
        session_id=session_id,
        turn_id=turn_id,
    )
    return result or CommandPortResult(
        status="error",
        error={
            "code": "command.module_failed",
            "message": "The module command failed without affecting the Core.",
            "retryable": False,
        },
    )


async def dispatch_event(
    host: ModulePortHost,
    event: ModuleEvent,
    *,
    session_id: str | None = None,
    turn_id: str | None = None,
) -> ModuleEventBatch:
    publications: list[ModuleEvent] = []
    receipts: list[ModuleReceipt] = []
    for module_id in list(host.running_module_ids):
        if module_id not in host.running_module_ids:
            continue
        manifest = host._registration(module_id).manifest
        for capability in capabilities(manifest.capabilities, EventCapability):
            if event.event_type not in capability.subscribes_to:
                continue
            request = EventPortRequest(
                context=host._call_context(
                    module_id,
                    session_id=session_id,
                    turn_id=turn_id,
                ),
                event=event,
            )
            result, receipt = await host._call_model(
                module_id,
                operation="event.handle",
                capability_id=capability.capability_id,
                payload=request.model_dump(mode="json"),
                result_model=EventPortResult,
                request_id=request.context.request_id,
                session_id=session_id,
                turn_id=turn_id,
                result_validator=lambda value: validate_event_result(value, capability),
            )
            receipts.append(receipt)
            if result is not None:
                publications.extend(result.publications)
    return ModuleEventBatch(publications=publications, receipts=receipts)


def capabilities(values: list[Any], model: type[Any]) -> list[Any]:
    return [item for item in values if isinstance(item, model)]


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

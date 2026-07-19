"""Opt-in Agentic Module host over the accepted V1 contracts."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

from pydantic import ValidationError

from app.agentic_modules.contracts import (
    DEFAULT_CORE_MODULE_CONTRACTS,
    CommandCapability,
    CommandPortResult,
    ContextInputBlock,
    ContextPortBudget,
    ContractModel,
    HealthPortRequest,
    HealthPortResult,
    ModuleEvent,
    ModulePermission,
    PortCallContext,
)
from app.agentic_modules.ports import (
    ModuleContextBatch,
    ModuleEventBatch,
    ModulePromptBatch,
    capabilities,
    collect_context,
    collect_health,
    collect_prompt,
    dispatch_event as dispatch_module_event,
    invoke_command as invoke_module_command,
)
from app.agentic_modules.registry import ModuleRegistry, RegisteredModule
from app.agentic_modules.telemetry import (
    InMemoryModuleTelemetry,
    ModuleReceipt,
    ModuleTelemetry,
    new_receipt,
)
from app.agentic_modules.transport import JsonLineModuleProcess, ModuleTransportError
from app.agentic_modules.validation import ModuleActivationPlan, build_activation_plan


class AgenticModuleHost:
    """Supervise approved modules without making them part of the Core process."""

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        core_version: str,
        telemetry: ModuleTelemetry | None = None,
        available_contracts: dict[str, str] | None = None,
    ) -> None:
        self.registry = registry
        self.core_version = core_version
        self.telemetry = telemetry or InMemoryModuleTelemetry()
        self.available_contracts = dict(
            DEFAULT_CORE_MODULE_CONTRACTS
            if available_contracts is None
            else available_contracts
        )
        self.active_mode_tag: str | None = None
        self.activation_plan: ModuleActivationPlan | None = None
        self._disabled: set[str] = set()
        self._failed: dict[str, str] = {}
        self._processes: dict[str, JsonLineModuleProcess] = {}
        self._telemetry_session_id: str | None = None
        self._telemetry_turn_id: str | None = None

    @property
    def running_module_ids(self) -> list[str]:
        if self.activation_plan is None:
            return []
        return [
            module_id
            for module_id in self.activation_plan.ordered_active_modules
            if module_id in self._processes and self._processes[module_id].running
        ]

    async def activate(
        self,
        mode_tag: str,
        *,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> ModuleActivationPlan:
        """Plan and start modules for exactly one foreground agent mode."""

        await self.stop()
        self.active_mode_tag = mode_tag
        self._telemetry_session_id = session_id
        self._telemetry_turn_id = turn_id
        self._failed.clear()
        enabled = [
            item.manifest
            for item in self.registry.modules
            if item.manifest.module_id not in self._disabled
        ]
        self.activation_plan = build_activation_plan(
            enabled,
            core_version=self.core_version,
            active_mode_tag=mode_tag,
            available_contracts=self.available_contracts,
        )
        for registration in self.registry.modules:
            await self._emit(
                module_id=registration.manifest.module_id,
                operation="lifecycle.discover",
                status="succeeded",
                details={"manifest_path": str(registration.manifest_path)},
            )
            await self._emit(
                module_id=registration.manifest.module_id,
                operation="lifecycle.validate",
                status="succeeded",
                details={"manifest_sha256": registration.manifest_sha256},
            )
        await self._emit(
            module_id="module-host",
            operation="activation",
            status="succeeded",
            details={
                "active": self.activation_plan.ordered_active_modules,
                "diagnostic_codes": [
                    item.code for item in self.activation_plan.diagnostics
                ]
                + [item.code for item in self.registry.diagnostics],
                "disabled": sorted(self._disabled),
            },
        )
        for module_id in self.activation_plan.ordered_active_modules:
            registration = self._registration(module_id)
            unavailable_dependency = self._runtime_dependency_failure(registration)
            if unavailable_dependency is not None:
                self._failed[module_id] = "dependency.runtime_unavailable"
                await self._emit(
                    module_id=module_id,
                    operation="lifecycle.start",
                    status="skipped",
                    details={"dependency_id": unavailable_dependency},
                )
                continue
            await self._start_registration(registration)
        return self.activation_plan

    async def disable(self, module_id: str) -> ModuleActivationPlan | None:
        self._registration(module_id)
        self._disabled.add(module_id)
        process = self._processes.pop(module_id, None)
        if process is not None:
            await self._stop_process(module_id, process)
        await self._emit(
            module_id=module_id,
            operation="disable",
            status="succeeded",
        )
        if self.active_mode_tag is None:
            return None
        return await self.activate(
            self.active_mode_tag,
            session_id=self._telemetry_session_id,
            turn_id=self._telemetry_turn_id,
        )

    async def enable(self, module_id: str) -> ModuleActivationPlan | None:
        self._registration(module_id)
        self._disabled.discard(module_id)
        await self._emit(
            module_id=module_id,
            operation="enable",
            status="succeeded",
        )
        if self.active_mode_tag is None:
            return None
        return await self.activate(
            self.active_mode_tag,
            session_id=self._telemetry_session_id,
            turn_id=self._telemetry_turn_id,
        )

    async def stop(self) -> None:
        plan = self.activation_plan
        ordered = list(plan.ordered_active_modules) if plan is not None else []
        for module_id in reversed(ordered):
            process = self._processes.pop(module_id, None)
            if process is not None:
                await self._stop_process(module_id, process)
        for module_id, process in list(self._processes.items()):
            await self._stop_process(module_id, process)
            self._processes.pop(module_id, None)

    async def health(
        self,
        *,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> dict[str, HealthPortResult]:
        return await collect_health(
            self,
            session_id=session_id,
            turn_id=turn_id,
        )

    async def contribute_context(
        self,
        *,
        budget: ContextPortBudget,
        inputs: list[ContextInputBlock] | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> ModuleContextBatch:
        return await collect_context(
            self,
            budget=budget,
            inputs=inputs,
            session_id=session_id,
            turn_id=turn_id,
        )

    async def contribute_prompt(
        self,
        *,
        slots: list[str],
        max_characters: int,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> ModulePromptBatch:
        return await collect_prompt(
            self,
            slots=slots,
            max_characters=max_characters,
            session_id=session_id,
            turn_id=turn_id,
        )

    async def invoke_command(
        self,
        *,
        namespace: str,
        command: str,
        arguments: dict[str, Any] | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> CommandPortResult:
        return await invoke_module_command(
            self,
            namespace=namespace,
            command=command,
            arguments=arguments,
            session_id=session_id,
            turn_id=turn_id,
        )

    async def dispatch_event(
        self,
        event: ModuleEvent,
        *,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> ModuleEventBatch:
        return await dispatch_module_event(
            self,
            event,
            session_id=session_id,
            turn_id=turn_id,
        )

    async def _start_registration(self, registration: RegisteredModule) -> None:
        module_id = registration.manifest.module_id
        await self._emit(
            module_id=module_id,
            operation="lifecycle.load",
            status="started",
        )
        process = JsonLineModuleProcess(registration)
        self._processes[module_id] = process
        await self._emit(
            module_id=module_id,
            operation="lifecycle.load",
            status="succeeded",
            details={"transport": registration.manifest.runtime.transport},
        )
        started = time.perf_counter()
        await self._emit(
            module_id=module_id, operation="lifecycle.start", status="started"
        )
        try:
            await process.start()
            result = await process.request(
                "lifecycle.start",
                {"module_id": module_id, "core_version": self.core_version},
                timeout_seconds=registration.manifest.timeouts.startup_seconds,
            )
            if result.get("status") != "ready":
                raise ValueError("lifecycle.start did not return ready status")
        except (ModuleTransportError, ValueError) as exc:
            self._failed[module_id] = _error_code(exc)
            self._processes.pop(module_id, None)
            await process.terminate()
            await self._emit(
                module_id=module_id,
                operation="lifecycle.start",
                status="failed",
                duration_ms=_elapsed_ms(started),
                details={"code": _error_code(exc), "message": str(exc)},
            )
            await self._emit(
                module_id=module_id,
                operation="lifecycle.failure",
                status="failed",
                details={"code": _error_code(exc), "source": "lifecycle.start"},
            )
            return
        await self._emit(
            module_id=module_id,
            operation="lifecycle.start",
            status="succeeded",
            duration_ms=_elapsed_ms(started),
        )
        request = HealthPortRequest(
            context=self._call_context(module_id, session_id=None, turn_id=None)
        )
        health, _ = await self._call_model(
            module_id,
            operation="health",
            payload=request.model_dump(mode="json"),
            result_model=HealthPortResult,
            request_id=request.context.request_id,
            timeout_seconds=registration.manifest.timeouts.health_seconds,
        )
        if health is not None and health.status == "unhealthy":
            await self._quarantine_module(
                module_id,
                code="health.unhealthy",
                source="health",
            )

    async def _stop_process(
        self,
        module_id: str,
        process: JsonLineModuleProcess,
    ) -> None:
        started = time.perf_counter()
        await self._emit(
            module_id=module_id, operation="lifecycle.stop", status="started"
        )
        status = "succeeded"
        details: dict[str, Any] = {}
        try:
            if process.running:
                await process.request(
                    "lifecycle.stop",
                    {"module_id": module_id},
                    timeout_seconds=self._registration(
                        module_id
                    ).manifest.timeouts.shutdown_seconds,
                )
        except ModuleTransportError as exc:
            status = "failed"
            details = {"code": exc.code, "message": str(exc)}
        finally:
            await process.terminate()
        await self._emit(
            module_id=module_id,
            operation="lifecycle.stop",
            status=status,
            duration_ms=_elapsed_ms(started),
            details=details,
        )

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
    ) -> tuple[Any | None, ModuleReceipt]:
        process = self._processes[module_id]
        started = time.perf_counter()
        await self._emit(
            module_id=module_id,
            operation=operation,
            status="started",
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
        )
        try:
            raw = await process.request(
                operation,
                payload,
                capability_id=capability_id,
                request_id=request_id,
                timeout_seconds=timeout_seconds,
            )
            result = result_model.model_validate(raw)
            if result_validator is not None:
                result_validator(result)
        except (ModuleTransportError, ValidationError, ValueError) as exc:
            self._failed[module_id] = _error_code(exc)
            self._processes.pop(module_id, None)
            await process.terminate()
            receipt = await self._emit(
                module_id=module_id,
                operation=operation,
                status="failed",
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                duration_ms=_elapsed_ms(started),
                details={
                    "code": _error_code(exc),
                    "message": str(exc),
                    "stderr_tail": process.stderr_tail[-2000:],
                },
            )
            await self._emit(
                module_id=module_id,
                operation="lifecycle.failure",
                status="failed",
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                details={"code": _error_code(exc), "source": operation},
            )
            await self._quarantine_dependents(module_id)
            return None, receipt
        receipt = await self._emit(
            module_id=module_id,
            operation=operation,
            status="succeeded",
            request_id=request_id,
            session_id=session_id,
            turn_id=turn_id,
            duration_ms=_elapsed_ms(started),
        )
        return result, receipt

    async def _emit(
        self,
        *,
        module_id: str,
        operation: str,
        status: str,
        request_id: str | None = None,
        session_id: str | None = None,
        turn_id: str | None = None,
        duration_ms: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> ModuleReceipt:
        receipt = new_receipt(
            module_id=module_id,
            operation=operation,
            status=status,  # type: ignore[arg-type]
            active_mode_tag=self.active_mode_tag,
            request_id=request_id,
            session_id=(
                session_id if session_id is not None else self._telemetry_session_id
            ),
            turn_id=turn_id if turn_id is not None else self._telemetry_turn_id,
            duration_ms=duration_ms,
            details=details,
        )
        return await self.telemetry.emit(receipt)

    async def _quarantine_module(
        self,
        module_id: str,
        *,
        code: str,
        source: str,
    ) -> None:
        self._failed[module_id] = code
        process = self._processes.pop(module_id, None)
        if process is not None:
            await process.terminate()
        await self._emit(
            module_id=module_id,
            operation="lifecycle.failure",
            status="failed",
            details={"code": code, "source": source},
        )
        await self._quarantine_dependents(module_id)

    async def _quarantine_dependents(self, failed_module_id: str) -> None:
        for registration in self.registry.modules:
            module_id = registration.manifest.module_id
            if module_id not in self._processes:
                continue
            required = {
                item.module_id
                for item in registration.manifest.dependencies
                if not item.optional
            }
            if failed_module_id not in required:
                continue
            self._failed[module_id] = "dependency.runtime_unavailable"
            process = self._processes.pop(module_id)
            await process.terminate()
            await self._emit(
                module_id=module_id,
                operation="lifecycle.failure",
                status="failed",
                details={
                    "code": "dependency.runtime_unavailable",
                    "dependency_id": failed_module_id,
                },
            )
            await self._quarantine_dependents(module_id)

    def _call_context(
        self,
        module_id: str,
        *,
        session_id: str | None,
        turn_id: str | None,
    ) -> PortCallContext:
        timeout = self._registration(module_id).manifest.timeouts.call_seconds
        return PortCallContext(
            request_id=f"modreq_{uuid4().hex}",
            module_id=module_id,
            core_version=self.core_version,
            active_mode_tag=self.active_mode_tag or "idle",
            session_id=session_id,
            turn_id=turn_id,
            deadline_at=datetime.now(timezone.utc) + timedelta(seconds=timeout),
        )

    def _registration(self, module_id: str) -> RegisteredModule:
        registration = self.registry.get(module_id)
        if registration is None:
            raise KeyError(f"Module is not registered: {module_id}")
        return registration

    def _runtime_dependency_failure(
        self,
        registration: RegisteredModule,
    ) -> str | None:
        for dependency in registration.manifest.dependencies:
            if dependency.optional:
                continue
            if dependency.module_id not in self.running_module_ids:
                return dependency.module_id
        return None

    def _command_routes(self) -> dict[tuple[str, str], tuple[str, CommandCapability]]:
        routes: dict[tuple[str, str], tuple[str, CommandCapability]] = {}
        ambiguous: set[tuple[str, str]] = set()
        for module_id in self.running_module_ids:
            manifest = self._registration(module_id).manifest
            if ModulePermission.COMMAND_REGISTER not in manifest.permissions:
                continue
            for capability in capabilities(manifest.capabilities, CommandCapability):
                for command in capability.commands:
                    key = (capability.namespace, command)
                    if key in routes:
                        ambiguous.add(key)
                    else:
                        routes[key] = (module_id, capability)
        for key in ambiguous:
            routes.pop(key, None)
        return routes


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _error_code(exc: Exception) -> str:
    if isinstance(exc, ModuleTransportError):
        return exc.code
    if isinstance(exc, ValidationError):
        return "contract.response_invalid"
    return "host.validation_failed"

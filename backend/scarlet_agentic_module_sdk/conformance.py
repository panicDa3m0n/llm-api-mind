"""Standalone conformance runner for one installed Agentic Module."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field, ValidationError

from scarlet_agentic_module_sdk.client import (
    ModuleClientError,
    ModuleProcessClient,
    resolve_entrypoint_file,
)
from scarlet_agentic_module_sdk.contracts import (
    AGENTIC_MODULE_PORT_VERSION,
    AgenticModuleManifest,
    CommandCapability,
    CommandPortRequest,
    CommandPortResult,
    ContextPortBudget,
    ContextPortRequest,
    ContextPortResult,
    ContractModel,
    EventPortRequest,
    EventPortResult,
    HealthPortRequest,
    HealthPortResult,
    ModuleEvent,
    PortCallContext,
    PromptPortRequest,
    PromptPortResult,
)
from scarlet_agentic_module_sdk.validation import (
    DEFAULT_AGENT_MODE_TAGS,
    context_capabilities,
    event_capabilities,
    prompt_capabilities,
    unknown_mode_tags,
    validate_context_result,
    validate_event_result,
    validate_prompt_result,
)


MANIFEST_FILENAME = "agentic-module.json"
MAX_MANIFEST_BYTES = 1_000_000


class ConformanceDiagnostic(ContractModel):
    step: str
    status: Literal["passed", "failed", "skipped"]
    code: str
    message: str
    location: str | None = None
    request_id: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)


class ConformanceReport(ContractModel):
    ok: bool
    manifest_path: str
    module_id: str | None = None
    manifest_schema_version: str | None = None
    port_version: str = AGENTIC_MODULE_PORT_VERSION
    diagnostics: list[ConformanceDiagnostic] = Field(default_factory=list)


def validate_manifest(
    module_directory: Path,
    *,
    known_mode_tags: tuple[str, ...] = DEFAULT_AGENT_MODE_TAGS,
) -> tuple[AgenticModuleManifest | None, list[ConformanceDiagnostic]]:
    """Read one manifest and return localized, stable diagnostics."""

    manifest_path = module_directory / MANIFEST_FILENAME
    try:
        raw = manifest_path.read_bytes()
    except OSError as exc:
        return None, [_failure("manifest.read", str(exc), location=str(manifest_path))]
    if len(raw) > MAX_MANIFEST_BYTES:
        return None, [
            _failure(
                "manifest.too_large",
                f"Manifest exceeds {MAX_MANIFEST_BYTES} bytes.",
                location=str(manifest_path),
            )
        ]
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, [
            _failure("manifest.invalid_json", str(exc), location=str(manifest_path))
        ]
    try:
        manifest = AgenticModuleManifest.model_validate(payload)
    except ValidationError as exc:
        diagnostics = []
        for item in exc.errors():
            location = _validation_location(item)
            diagnostics.append(
                _failure(
                    "manifest.contract_invalid",
                    str(item["msg"]),
                    location=location or str(manifest_path),
                )
            )
        return None, diagnostics
    unknown = unknown_mode_tags(manifest, known_mode_tags=known_mode_tags)
    if unknown:
        return manifest, [
            _failure(
                "manifest.unknown_mode_tag",
                f"Unknown agent mode tags: {', '.join(unknown)}.",
                location="mode_tags",
            )
        ]
    executable = resolve_entrypoint_file(module_directory, manifest)
    if not executable.is_file():
        return manifest, [
            _failure(
                "manifest.entrypoint_missing",
                f"Entrypoint does not exist: {manifest.runtime.entrypoint[0]}",
                location="runtime.entrypoint.0",
            )
        ]
    return manifest, [
        ConformanceDiagnostic(
            step="manifest",
            status="passed",
            code="manifest.valid",
            message="Manifest, permissions, modes, and entrypoint are valid.",
        )
    ]


async def run_conformance(
    module_directory: Path,
    *,
    core_version: str = "1.61.0",
    active_mode_tag: str = "interactive",
    known_mode_tags: tuple[str, ...] = DEFAULT_AGENT_MODE_TAGS,
) -> ConformanceReport:
    """Exercise manifest, lifecycle, declared ports, errors, and call trace."""

    directory = module_directory.expanduser().resolve()
    manifest_path = directory / MANIFEST_FILENAME
    manifest, diagnostics = validate_manifest(
        directory,
        known_mode_tags=known_mode_tags,
    )
    if manifest is None or any(item.status == "failed" for item in diagnostics):
        return _report(manifest_path, manifest, diagnostics)
    if active_mode_tag not in manifest.mode_tags:
        diagnostics.append(
            _failure(
                "mode.inactive",
                f"Module is not active for mode {active_mode_tag!r}.",
                location="mode_tags",
            )
        )
        return _report(manifest_path, manifest, diagnostics)

    process = _ConformanceProcess(ModuleProcessClient(directory, manifest))
    try:
        await process.start()
        diagnostics.append(
            await process.expect_result(
                "lifecycle.start",
                {"module_id": manifest.module_id, "core_version": core_version},
                expected_model=None,
                expected_status="ready",
                timeout=manifest.timeouts.startup_seconds,
            )
        )
        if diagnostics[-1].status == "failed":
            return _report(manifest_path, manifest, diagnostics)

        health_request = HealthPortRequest(
            context=_call_context(manifest.module_id, core_version, active_mode_tag)
        )
        diagnostics.append(
            await process.expect_result(
                "health",
                health_request.model_dump(mode="json"),
                expected_model=HealthPortResult,
                timeout=manifest.timeouts.health_seconds,
            )
        )
        for capability in context_capabilities(manifest):
            request = ContextPortRequest(
                context=_call_context(
                    manifest.module_id, core_version, active_mode_tag
                ),
                budget=ContextPortBudget(max_tokens=512, max_items=5),
            )
            diagnostics.append(
                await process.expect_result(
                    "context.contribute",
                    request.model_dump(mode="json"),
                    capability_id=capability.capability_id,
                    expected_model=ContextPortResult,
                    result_validator=lambda value, item=capability: (
                        validate_context_result(value, item)
                    ),
                    timeout=manifest.timeouts.call_seconds,
                )
            )
        for capability in prompt_capabilities(manifest):
            max_characters = min(capability.max_characters, 2000)
            request = PromptPortRequest(
                context=_call_context(
                    manifest.module_id, core_version, active_mode_tag
                ),
                slots=list(capability.slots),
                max_characters=max_characters,
            )
            diagnostics.append(
                await process.expect_result(
                    "prompt.contribute",
                    request.model_dump(mode="json"),
                    capability_id=capability.capability_id,
                    expected_model=PromptPortResult,
                    result_validator=lambda value, slots=list(capability.slots), limit=max_characters: (
                        validate_prompt_result(
                            value,
                            allowed_slots=slots,
                            max_characters=limit,
                        )
                    ),
                    timeout=manifest.timeouts.call_seconds,
                )
            )
        for capability in _capabilities(manifest, CommandCapability):
            for command in capability.commands:
                request = CommandPortRequest(
                    context=_call_context(
                        manifest.module_id, core_version, active_mode_tag
                    ),
                    namespace=capability.namespace,
                    command=command,
                    arguments={},
                )
                diagnostics.append(
                    await process.expect_result(
                        "command.invoke",
                        request.model_dump(mode="json"),
                        capability_id=capability.capability_id,
                        expected_model=CommandPortResult,
                        timeout=manifest.timeouts.call_seconds,
                    )
                )
        for capability in event_capabilities(manifest):
            if not capability.subscribes_to:
                continue
            request = EventPortRequest(
                context=_call_context(
                    manifest.module_id, core_version, active_mode_tag
                ),
                event=ModuleEvent(
                    event_id=f"conformance_{uuid4().hex}",
                    event_type=capability.subscribes_to[0],
                    occurred_at=datetime.now(timezone.utc),
                    payload={"source": "sdk-conformance"},
                ),
            )
            diagnostics.append(
                await process.expect_result(
                    "event.handle",
                    request.model_dump(mode="json"),
                    capability_id=capability.capability_id,
                    expected_model=EventPortResult,
                    result_validator=lambda value, item=capability: (
                        validate_event_result(value, item)
                    ),
                    timeout=manifest.timeouts.call_seconds,
                )
            )
        diagnostics.append(
            await process.expect_error(
                "conformance.unknown",
                {},
                timeout=manifest.timeouts.call_seconds,
            )
        )
        diagnostics.append(
            await process.expect_result(
                "lifecycle.stop",
                {"module_id": manifest.module_id},
                expected_model=None,
                expected_status="stopped",
                timeout=manifest.timeouts.shutdown_seconds,
            )
        )
    except (OSError, asyncio.TimeoutError, ValueError) as exc:
        diagnostics.append(_failure("process.failure", str(exc), location="runtime"))
    finally:
        await process.terminate()
    return _report(manifest_path, manifest, diagnostics)


class _ConformanceProcess:
    def __init__(self, client: ModuleProcessClient) -> None:
        self.client = client

    async def start(self) -> None:
        await self.client.start()

    async def expect_result(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        expected_model: type[ContractModel] | None,
        timeout: float,
        capability_id: str | None = None,
        expected_status: str | None = None,
        result_validator: Any | None = None,
    ) -> ConformanceDiagnostic:
        started = time.perf_counter()
        request_id = f"conf_{uuid4().hex}"
        try:
            response = await self.client.request(
                operation,
                payload,
                request_id=request_id,
                capability_id=capability_id,
                timeout=timeout,
            )
            if not response.ok:
                raise ValueError(f"module returned error: {response.error!r}")
            raw_result = response.result
            if raw_result is None:
                raise ValueError("successful response result must be an object")
            if expected_model is not None:
                result = expected_model.model_validate(raw_result)
                if result_validator is not None:
                    result_validator(result)
            elif (
                expected_status is not None
                and raw_result.get("status") != expected_status
            ):
                raise ValueError(f"expected status {expected_status!r}")
        except (
            asyncio.TimeoutError,
            ModuleClientError,
            ValidationError,
            ValueError,
        ) as exc:
            return _timed_failure(operation, exc, started, request_id)
        return _timed_pass(operation, started, request_id)

    async def expect_error(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        timeout: float,
    ) -> ConformanceDiagnostic:
        started = time.perf_counter()
        request_id = f"conf_{uuid4().hex}"
        try:
            response = await self.client.request(
                operation,
                payload,
                request_id=request_id,
                timeout=timeout,
            )
            error = response.error
            if response.ok or not isinstance(error, dict):
                raise ValueError("unknown operation must return a structured error")
            if not isinstance(error.get("code"), str) or not error.get("code"):
                raise ValueError("structured error must contain a non-empty code")
        except (asyncio.TimeoutError, ModuleClientError, ValueError) as exc:
            return _timed_failure("protocol.error", exc, started, request_id)
        return _timed_pass("protocol.error", started, request_id)

    async def terminate(self) -> None:
        await self.client.close()


def _call_context(
    module_id: str,
    core_version: str,
    active_mode_tag: str,
) -> PortCallContext:
    return PortCallContext(
        request_id=f"conf_{uuid4().hex}",
        module_id=module_id,
        core_version=core_version,
        active_mode_tag=active_mode_tag,
        deadline_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )


def _capabilities(
    manifest: AgenticModuleManifest,
    model: type[Any],
) -> list[Any]:
    return [item for item in manifest.capabilities if isinstance(item, model)]


def _failure(
    code: str,
    message: str,
    *,
    location: str | None = None,
) -> ConformanceDiagnostic:
    return ConformanceDiagnostic(
        step="manifest",
        status="failed",
        code=code,
        message=message,
        location=location,
    )


def _validation_location(item: dict[str, Any]) -> str:
    location = ".".join(str(part) for part in item["loc"])
    if location:
        return location
    message = str(item.get("msg", ""))
    if "undeclared permissions" in message:
        return "permissions"
    if "depend on itself" in message:
        return "dependencies"
    if "max_restarts" in message:
        return "lifecycle.max_restarts"
    return "manifest"


def _timed_failure(
    step: str,
    error: Exception,
    started: float,
    request_id: str,
) -> ConformanceDiagnostic:
    return ConformanceDiagnostic(
        step=step,
        status="failed",
        code="protocol.check_failed",
        message=str(error),
        request_id=request_id,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _timed_pass(
    step: str,
    started: float,
    request_id: str,
) -> ConformanceDiagnostic:
    return ConformanceDiagnostic(
        step=step,
        status="passed",
        code="protocol.check_passed",
        message="Protocol check passed.",
        request_id=request_id,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def _report(
    manifest_path: Path,
    manifest: AgenticModuleManifest | None,
    diagnostics: list[ConformanceDiagnostic],
) -> ConformanceReport:
    return ConformanceReport(
        ok=not any(item.status == "failed" for item in diagnostics),
        manifest_path=str(manifest_path),
        module_id=manifest.module_id if manifest is not None else None,
        manifest_schema_version=(
            manifest.schema_version if manifest is not None else None
        ),
        diagnostics=diagnostics,
    )

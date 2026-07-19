"""Module-side JSONL runtime for the Agentic Module Port V1 protocol."""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from pydantic import ValidationError

from scarlet_agentic_module_sdk.contracts import (
    AGENTIC_MODULE_PORT_VERSION,
    CommandPortRequest,
    CommandPortResult,
    ContextPortRequest,
    ContextPortResult,
    EventPortRequest,
    EventPortResult,
    HealthPortRequest,
    HealthPortResult,
    PromptPortRequest,
    PromptPortResult,
)


class ModuleProtocolError(RuntimeError):
    """Structured module error returned to the Core host."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class AgenticModule:
    """Override only the handlers declared by the module manifest."""

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ready"}

    def stop(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "stopped"}

    def health(self, request: HealthPortRequest) -> HealthPortResult:
        return HealthPortResult(status="healthy")

    def contribute_context(
        self,
        request: ContextPortRequest,
        *,
        capability_id: str | None,
    ) -> ContextPortResult:
        return ContextPortResult()

    def contribute_prompt(
        self,
        request: PromptPortRequest,
        *,
        capability_id: str | None,
    ) -> PromptPortResult:
        return PromptPortResult()

    def invoke_command(
        self,
        request: CommandPortRequest,
        *,
        capability_id: str | None,
    ) -> CommandPortResult:
        return CommandPortResult(
            status="error",
            error={
                "code": "command.not_implemented",
                "message": "The module does not implement this command.",
            },
        )

    def handle_event(
        self,
        request: EventPortRequest,
        *,
        capability_id: str | None,
    ) -> EventPortResult:
        return EventPortResult(acknowledged=True)


def serve(
    module: AgenticModule,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """Serve correlated Port V1 requests until lifecycle.stop or EOF."""

    source = input_stream or sys.stdin
    target = output_stream or sys.stdout
    for line in source:
        request_id: str | None = None
        should_stop = False
        try:
            envelope = json.loads(line)
            if not isinstance(envelope, dict):
                raise ModuleProtocolError(
                    "protocol.invalid_envelope",
                    "The request envelope must be a JSON object.",
                )
            request_id = _required_string(envelope, "request_id")
            if envelope.get("protocol_version") != AGENTIC_MODULE_PORT_VERSION:
                raise ModuleProtocolError(
                    "protocol.unsupported_version",
                    f"Expected {AGENTIC_MODULE_PORT_VERSION}.",
                )
            operation = _required_string(envelope, "operation")
            payload = envelope.get("payload")
            if not isinstance(payload, dict):
                raise ModuleProtocolError(
                    "protocol.invalid_payload",
                    "The request payload must be a JSON object.",
                )
            capability_id = envelope.get("capability_id")
            result, should_stop = _dispatch(
                module,
                operation=operation,
                payload=payload,
                capability_id=(
                    capability_id if isinstance(capability_id, str) else None
                ),
            )
            response = {
                "request_id": request_id,
                "ok": True,
                "result": result,
            }
        except (json.JSONDecodeError, ValidationError, ModuleProtocolError) as exc:
            protocol_error = _as_protocol_error(exc)
            response = {
                "request_id": request_id,
                "ok": False,
                "error": {
                    "code": protocol_error.code,
                    "message": str(protocol_error),
                    "retryable": protocol_error.retryable,
                },
            }
        target.write(json.dumps(response, ensure_ascii=True, separators=(",", ":")))
        target.write("\n")
        target.flush()
        if should_stop:
            return


def _dispatch(
    module: AgenticModule,
    *,
    operation: str,
    payload: dict[str, Any],
    capability_id: str | None,
) -> tuple[dict[str, Any], bool]:
    if operation == "lifecycle.start":
        return module.start(payload), False
    if operation == "lifecycle.stop":
        return module.stop(payload), True
    if operation == "health":
        result = module.health(HealthPortRequest.model_validate(payload))
    elif operation == "context.contribute":
        result = module.contribute_context(
            ContextPortRequest.model_validate(payload),
            capability_id=capability_id,
        )
    elif operation == "prompt.contribute":
        result = module.contribute_prompt(
            PromptPortRequest.model_validate(payload),
            capability_id=capability_id,
        )
    elif operation == "command.invoke":
        result = module.invoke_command(
            CommandPortRequest.model_validate(payload),
            capability_id=capability_id,
        )
    elif operation == "event.handle":
        result = module.handle_event(
            EventPortRequest.model_validate(payload),
            capability_id=capability_id,
        )
    else:
        raise ModuleProtocolError(
            "operation.unknown",
            f"Unsupported operation: {operation}",
        )
    return result.model_dump(mode="json"), False


def _required_string(value: dict[str, Any], field: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise ModuleProtocolError(
            "protocol.invalid_envelope",
            f"Envelope field {field!r} must be a non-empty string.",
        )
    return item


def _as_protocol_error(
    error: json.JSONDecodeError | ValidationError | ModuleProtocolError,
) -> ModuleProtocolError:
    if isinstance(error, ModuleProtocolError):
        return error
    if isinstance(error, json.JSONDecodeError):
        return ModuleProtocolError("protocol.invalid_json", str(error))
    locations = [".".join(str(part) for part in item["loc"]) for item in error.errors()]
    path = ", ".join(locations[:5]) or "payload"
    return ModuleProtocolError(
        "protocol.contract_invalid",
        f"Contract validation failed at {path}: {error}",
    )

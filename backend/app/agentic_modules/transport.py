"""Bounded stdio JSON transport for an operator-approved module process."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.agentic_modules.registry import RegisteredModule
from scarlet_agentic_module_sdk.client import resolve_entrypoint
from scarlet_agentic_module_sdk.contracts import AGENTIC_MODULE_PORT_VERSION


class ModuleTransportError(RuntimeError):
    code = "transport.error"


class ModuleProcessUnavailable(ModuleTransportError):
    code = "transport.process_unavailable"


class ModuleRequestTooLarge(ModuleTransportError):
    code = "transport.request_too_large"


class ModuleResponseTooLarge(ModuleTransportError):
    code = "transport.response_too_large"


class ModuleResponseInvalid(ModuleTransportError):
    code = "transport.response_invalid"


class ModuleCallTimeout(ModuleTransportError):
    code = "transport.timeout"


class ModuleRemoteError(ModuleTransportError):
    code = "transport.remote_error"


class JsonLineModuleProcess:
    """One persistent process with serialized, correlated JSONL calls."""

    def __init__(self, registration: RegisteredModule) -> None:
        self.registration = registration
        self._process: asyncio.subprocess.Process | None = None
        self._request_lock = asyncio.Lock()
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr_tail = bytearray()

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    @property
    def stderr_tail(self) -> str:
        return bytes(self._stderr_tail).decode("utf-8", errors="replace")

    async def start(self) -> None:
        if self.running:
            return
        manifest = self.registration.manifest
        entrypoint = _launch_entrypoint(self.registration)
        try:
            self._process = await asyncio.create_subprocess_exec(
                *entrypoint,
                cwd=self.registration.module_directory,
                env=_subprocess_environment(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=manifest.resources.max_response_bytes + 1,
                start_new_session=os.name == "posix",
            )
        except (OSError, ValueError) as exc:
            self._process = None
            raise ModuleProcessUnavailable(f"Could not start module: {exc}") from exc
        if self._process.stderr is not None:
            self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def request(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        capability_id: str | None = None,
        request_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        if not self.running:
            raise ModuleProcessUnavailable("Module process is not running.")
        manifest = self.registration.manifest
        correlation_id = request_id or f"modreq_{uuid4().hex}"
        envelope = {
            "protocol_version": AGENTIC_MODULE_PORT_VERSION,
            "request_id": correlation_id,
            "operation": operation,
            "capability_id": capability_id,
            "payload": payload,
        }
        try:
            encoded = (
                json.dumps(
                    envelope,
                    ensure_ascii=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                + b"\n"
            )
        except (TypeError, ValueError) as exc:
            raise ModuleResponseInvalid(
                f"Request is not JSON serializable: {exc}"
            ) from exc
        if len(encoded) > manifest.resources.max_request_bytes:
            raise ModuleRequestTooLarge(
                f"Request is {len(encoded)} bytes; limit is "
                f"{manifest.resources.max_request_bytes}."
            )

        timeout = timeout_seconds or manifest.timeouts.call_seconds
        async with self._request_lock:
            process = self._require_process()
            if process.stdin is None or process.stdout is None:
                raise ModuleProcessUnavailable("Module stdio pipes are unavailable.")
            try:
                process.stdin.write(encoded)
                await asyncio.wait_for(process.stdin.drain(), timeout=timeout)
                line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=timeout
                )
            except asyncio.TimeoutError as exc:
                await self.terminate()
                raise ModuleCallTimeout(
                    f"Module call exceeded {timeout:.3f} seconds."
                ) from exc
            except (BrokenPipeError, ConnectionResetError, ValueError) as exc:
                await self.terminate()
                message = str(exc)
                if "separator" in message.lower() or "limit" in message.lower():
                    raise ModuleResponseTooLarge(
                        "Module response exceeded the configured byte limit."
                    ) from exc
                raise ModuleProcessUnavailable(
                    f"Module process closed its transport: {message}"
                ) from exc

        if not line:
            return_code = process.returncode
            await self.terminate()
            raise ModuleProcessUnavailable(
                f"Module exited before responding (returncode={return_code})."
            )
        if len(line) > manifest.resources.max_response_bytes:
            await self.terminate()
            raise ModuleResponseTooLarge(
                f"Response is {len(line)} bytes; limit is "
                f"{manifest.resources.max_response_bytes}."
            )
        try:
            response = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            await self.terminate()
            raise ModuleResponseInvalid("Module response is not valid JSON.") from exc
        if not isinstance(response, dict):
            await self.terminate()
            raise ModuleResponseInvalid("Module response must be a JSON object.")
        if response.get("request_id") != correlation_id:
            await self.terminate()
            raise ModuleResponseInvalid("Module response request_id does not match.")
        if response.get("ok") is not True:
            error = response.get("error")
            await self.terminate()
            raise ModuleRemoteError(f"Module rejected the call: {error!r}")
        result = response.get("result")
        if not isinstance(result, dict):
            await self.terminate()
            raise ModuleResponseInvalid(
                "Successful response must contain object result."
            )
        return result

    async def terminate(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.returncode is None:
            if os.name == "posix":
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=self.registration.manifest.timeouts.shutdown_seconds,
                )
            except asyncio.TimeoutError:
                if os.name == "posix":
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                await process.wait()
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stderr_task
            self._stderr_task = None

    def _require_process(self) -> asyncio.subprocess.Process:
        if self._process is None:
            raise ModuleProcessUnavailable("Module process is not running.")
        return self._process

    async def _drain_stderr(self) -> None:
        process = self._process
        if process is None or process.stderr is None:
            return
        while True:
            chunk = await process.stderr.read(4096)
            if not chunk:
                return
            self._stderr_tail.extend(chunk)
            if len(self._stderr_tail) > 65_536:
                del self._stderr_tail[:-65_536]


def _resolved_entrypoint(registration: RegisteredModule) -> list[str]:
    return resolve_entrypoint(
        registration.module_directory,
        registration.manifest,
    )


def _launch_entrypoint(registration: RegisteredModule) -> list[str]:
    entrypoint = _resolved_entrypoint(registration)
    if not sys.platform.startswith("linux"):
        return entrypoint
    wrapper = str(Path(__file__).with_name("process_wrapper.py").resolve())
    return [
        sys.executable,
        wrapper,
        str(registration.manifest.resources.max_memory_mb),
        *entrypoint,
    ]


def _subprocess_environment() -> dict[str, str]:
    allowed = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "SYSTEMROOT")
    environment = {name: os.environ[name] for name in allowed if name in os.environ}
    environment["PYTHONUNBUFFERED"] = "1"
    return environment

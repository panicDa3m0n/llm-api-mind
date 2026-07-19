"""Typed development client for the Agentic Module Port V1 transport."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import model_validator

from scarlet_agentic_module_sdk.contracts import (
    AGENTIC_MODULE_PORT_VERSION,
    AgenticModuleManifest,
    ContractModel,
)


class ModuleClientError(RuntimeError):
    """A bounded process or protocol failure in the development client."""


class PortResponse(ContractModel):
    request_id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_outcome(self) -> PortResponse:
        if self.ok and (self.result is None or self.error is not None):
            raise ValueError("successful response requires result and forbids error")
        if not self.ok and (self.error is None or self.result is not None):
            raise ValueError("failed response requires error and forbids result")
        return self


class ModuleProcessClient:
    """Launch and call one module process without importing Core internals."""

    def __init__(self, directory: Path, manifest: AgenticModuleManifest) -> None:
        self.directory = directory.expanduser().resolve()
        self.manifest = manifest
        self._process: asyncio.subprocess.Process | None = None
        self._request_lock = asyncio.Lock()
        self._stderr_task: asyncio.Task[None] | None = None
        self._stderr_tail = bytearray()

    @property
    def stderr_tail(self) -> str:
        return bytes(self._stderr_tail).decode("utf-8", errors="replace")

    async def start(self) -> None:
        if self._process is not None and self._process.returncode is None:
            return
        entrypoint = resolve_entrypoint(self.directory, self.manifest)
        self._process = await asyncio.create_subprocess_exec(
            entrypoint[0],
            *entrypoint[1:],
            cwd=self.directory,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=self.manifest.resources.max_response_bytes + 1,
        )
        if self._process.stderr is not None:
            self._stderr_task = asyncio.create_task(self._drain_stderr())

    async def request(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        timeout: float,
        capability_id: str | None = None,
        request_id: str | None = None,
    ) -> PortResponse:
        process = self._process
        if process is None or process.stdin is None or process.stdout is None:
            raise ModuleClientError("module process is unavailable")
        correlation_id = request_id or f"sdk_{uuid4().hex}"
        encoded = (
            json.dumps(
                {
                    "protocol_version": AGENTIC_MODULE_PORT_VERSION,
                    "request_id": correlation_id,
                    "operation": operation,
                    "capability_id": capability_id,
                    "payload": payload,
                },
                ensure_ascii=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
        if len(encoded) > self.manifest.resources.max_request_bytes:
            raise ModuleClientError("request exceeds manifest byte limit")
        try:
            async with self._request_lock:
                process.stdin.write(encoded)
                await asyncio.wait_for(process.stdin.drain(), timeout=timeout)
                line = await asyncio.wait_for(
                    process.stdout.readline(), timeout=timeout
                )
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise ModuleClientError(f"module transport closed: {exc}") from exc
        if not line:
            raise ModuleClientError(
                f"module exited with return code {process.returncode}; "
                f"stderr={self.stderr_tail[-1000:]!r}"
            )
        if len(line) > self.manifest.resources.max_response_bytes:
            raise ModuleClientError("response exceeds manifest byte limit")
        try:
            response = PortResponse.model_validate_json(line)
        except ValueError as exc:
            raise ModuleClientError(f"invalid module response: {exc}") from exc
        if response.request_id != correlation_id:
            raise ModuleClientError("response request_id does not match")
        return response

    async def close(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._stderr_task
            self._stderr_task = None

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


def resolve_entrypoint(
    directory: Path,
    manifest: AgenticModuleManifest,
) -> list[str]:
    first = Path(os.path.expanduser(manifest.runtime.entrypoint[0]))
    executable = first if first.is_absolute() else (directory / first).resolve()
    return [str(executable), *manifest.runtime.entrypoint[1:]]

"""Tiny UDS-only runner for bounded, network-disabled Python computations.

This process is intentionally not imported by the application. Deployment must
place it in a separate container with no network and no application/database
mounts. The backend only receives a compact HTTP receipt over a Unix socket.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import resource
import socketserver
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler
from typing import Any


MAX_CODE_CHARS = 12_000
MAX_SOURCE_COUNT = 3
MAX_SOURCE_CHARS = 30_000
MAX_STDIO_CHARS = 32_000
MAX_ARTIFACTS = 8
MAX_ARTIFACT_BYTES = 1_000_000
EXECUTION_TIMEOUT_SECONDS = 15


class UnixHTTPServer(socketserver.UnixStreamServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "ScarletResearchLab/1.0"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            self._json(404, {"ok": False})
            return
        self._json(
            200,
            {
                "ok": True,
                "runner_identity": "research-lab-runner-v1",
                "network": "disabled_by_deployment_contract",
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/execute":
            self._json(404, {"ok": False})
            return
        length = self.headers.get("Content-Length")
        if not length or not length.isdigit() or int(length) > 250_000:
            self._json(413, {"ok": False, "error": "invalid_request_size"})
            return
        try:
            payload = json.loads(self.rfile.read(int(length)))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(400, {"ok": False, "error": "invalid_json"})
            return
        if not isinstance(payload, dict):
            self._json(400, {"ok": False, "error": "invalid_body"})
            return
        self._json(200, execute(payload))

    def log_message(self, _format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def execute(payload: dict[str, Any]) -> dict[str, Any]:
    code = payload.get("code")
    raw_sources = payload.get("sources")
    if not isinstance(code, str) or not code.strip() or len(code) > MAX_CODE_CHARS:
        return _failure("invalid_code")
    if not isinstance(raw_sources, list) or len(raw_sources) > MAX_SOURCE_COUNT:
        return _failure("invalid_sources")
    sources: list[dict[str, str]] = []
    for item in raw_sources:
        if not isinstance(item, dict):
            return _failure("invalid_sources")
        source_id = item.get("id")
        content = item.get("content")
        if not isinstance(source_id, str) or not isinstance(content, str):
            return _failure("invalid_sources")
        if not source_id or len(content) > MAX_SOURCE_CHARS:
            return _failure("invalid_sources")
        sources.append({"id": source_id, "content": content})

    with tempfile.TemporaryDirectory(prefix="research-lab-") as root:
        root_path = Path(root)
        source_dir = root_path / "sources"
        artifact_dir = root_path / "artifacts"
        source_dir.mkdir(mode=0o700)
        artifact_dir.mkdir(mode=0o700)
        source_paths: dict[str, str] = {}
        for index, source in enumerate(sources):
            path = source_dir / f"source_{index}.txt"
            path.write_text(source["content"], encoding="utf-8")
            source_paths[source["id"]] = str(path.relative_to(root_path))
        code_path = root_path / "main.py"
        code_path.write_text(code, encoding="utf-8")
        stdout_path = root_path / "stdout.txt"
        stderr_path = root_path / "stderr.txt"

        started = time.monotonic()
        try:
            with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open(
                "w", encoding="utf-8"
            ) as stderr_handle:
                completed = subprocess.run(
                    [sys.executable, "-I", str(code_path)],
                    cwd=root,
                    env={
                        "PATH": os.defpath,
                        "PYTHONIOENCODING": "utf-8",
                        "PYTHONUNBUFFERED": "1",
                        "LAB_ARTIFACTS_DIR": str(artifact_dir),
                        "LAB_SOURCES_DIR": str(source_dir),
                    },
                    text=True,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    timeout=EXECUTION_TIMEOUT_SECONDS,
                    preexec_fn=_limit_process,
                )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {
                "status": "completed" if completed.returncode == 0 else "failed",
                "stdout": _read_limited(stdout_path),
                "stderr": _read_limited(stderr_path),
                "exit_code": completed.returncode,
                "timed_out": False,
                "elapsed_ms": elapsed_ms,
                "artifacts": _collect_artifacts(artifact_dir),
                "source_paths": source_paths,
                "runner_identity": "research-lab-runner-v1",
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "failed",
                "stdout": _read_limited(stdout_path),
                "stderr": _read_limited(stderr_path),
                "exit_code": None,
                "timed_out": True,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "artifacts": [],
                "source_paths": source_paths,
                "runner_identity": "research-lab-runner-v1",
            }


def _limit_process() -> None:
    limits = (
        (resource.RLIMIT_CPU, 12),
        (resource.RLIMIT_AS, 512 * 1024 * 1024),
        (resource.RLIMIT_FSIZE, MAX_ARTIFACT_BYTES),
        (resource.RLIMIT_NPROC, 16),
        (resource.RLIMIT_NOFILE, 32),
    )
    for limit, value in limits:
        try:
            resource.setrlimit(limit, (value, value))
        except (OSError, ValueError):
            # The sidecar's Linux container remains the enforcement boundary.
            # Some developer kernels reject individual rlimits before exec.
            continue


def _collect_artifacts(artifact_dir: Path) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    root = artifact_dir.resolve()
    for path in sorted(artifact_dir.rglob("*")):
        if (
            not path.is_file()
            or path.is_symlink()
            or root not in path.resolve().parents
            or len(artifacts) >= MAX_ARTIFACTS
        ):
            continue
        content = path.read_bytes()
        if len(content) > MAX_ARTIFACT_BYTES:
            continue
        artifacts.append(
            {
                "name": str(path.relative_to(artifact_dir)),
                "media_type": mimetypes.guess_type(path.name)[0]
                or "application/octet-stream",
                "content_base64": base64.b64encode(content).decode("ascii"),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    return artifacts


def _clip(value: str) -> str:
    if len(value) <= MAX_STDIO_CHARS:
        return value
    suffix = "\n[truncated]"
    return value[: MAX_STDIO_CHARS - len(suffix)] + suffix


def _read_limited(path: Path) -> str:
    if not path.exists():
        return ""
    return _clip(path.read_text(encoding="utf-8", errors="replace"))


def _failure(error: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "stdout": "",
        "stderr": error,
        "exit_code": None,
        "timed_out": False,
        "artifacts": [],
        "source_paths": {},
        "runner_identity": "research-lab-runner-v1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()
    path = Path(args.socket)
    if path.exists():
        path.unlink()
    with UnixHTTPServer(str(path), Handler) as server:
        os.chmod(path, 0o660)
        server.serve_forever()


if __name__ == "__main__":
    main()

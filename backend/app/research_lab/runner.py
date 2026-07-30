"""Client for the separately deployed, network-disabled Research Lab runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


MAX_RECEIPT_TEXT_CHARS = 32_000
MAX_RECEIPT_ARTIFACTS = 8
MAX_RECEIPT_ARTIFACT_BYTES = 1_000_000


class ResearchLabRunnerError(RuntimeError):
    """The isolated runner could not accept or complete a bounded execution."""


@dataclass(frozen=True)
class RunnerArtifact:
    name: str
    media_type: str
    content_base64: str
    sha256: str


@dataclass(frozen=True)
class RunnerExecution:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    artifacts: list[RunnerArtifact]
    source_paths: dict[str, str]
    runner_identity: str


def execute_python(
    *,
    settings: Any,
    code: str,
    sources: list[dict[str, str]],
) -> RunnerExecution:
    uds = getattr(settings, "research_lab_runner_uds", None)
    if not isinstance(uds, str) or not uds.strip():
        raise ResearchLabRunnerError(
            "The isolated Research Lab runner is not configured. "
            "Set RESEARCH_LAB_RUNNER_UDS only after deploying the runner sidecar."
        )

    timeout = float(getattr(settings, "research_lab_runner_timeout_seconds", 20.0))
    transport = httpx.HTTPTransport(uds=uds)
    try:
        with httpx.Client(
            transport=transport,
            base_url="http://research-lab-runner",
            timeout=timeout,
        ) as client:
            response = client.post(
                "/execute",
                json={"code": code, "sources": sources},
            )
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ResearchLabRunnerError(
            "The isolated Research Lab runner is unavailable or returned an invalid receipt."
        ) from exc

    if not isinstance(payload, dict):
        raise ResearchLabRunnerError("The isolated Research Lab runner returned no receipt.")
    raw_artifacts = payload.get("artifacts")
    artifacts: list[RunnerArtifact] = []
    if isinstance(raw_artifacts, list):
        for item in raw_artifacts[:MAX_RECEIPT_ARTIFACTS]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            content_base64 = item.get("content_base64")
            sha256 = item.get("sha256")
            if not (
                isinstance(name, str)
                and name
                and isinstance(content_base64, str)
                and content_base64
                and isinstance(sha256, str)
                and sha256
            ):
                continue
            if len(content_base64) > ((MAX_RECEIPT_ARTIFACT_BYTES * 4) // 3) + 4:
                continue
            artifacts.append(
                RunnerArtifact(
                    name=name,
                    media_type=str(item.get("media_type") or "application/octet-stream"),
                    content_base64=content_base64,
                    sha256=sha256,
                )
            )
    source_paths = payload.get("source_paths")
    return RunnerExecution(
        status=str(payload.get("status") or "failed"),
        stdout=_clip_receipt_text(payload.get("stdout")),
        stderr=_clip_receipt_text(payload.get("stderr")),
        exit_code=payload.get("exit_code") if isinstance(payload.get("exit_code"), int) else None,
        timed_out=bool(payload.get("timed_out")),
        artifacts=artifacts,
        source_paths={
            str(key): str(value)
            for key, value in source_paths.items()
        }
        if isinstance(source_paths, dict)
        else {},
        runner_identity=str(payload.get("runner_identity") or "research-lab-runner-v1"),
    )


def _clip_receipt_text(value: Any) -> str:
    text = str(value or "")
    if len(text) <= MAX_RECEIPT_TEXT_CHARS:
        return text
    suffix = "\n[truncated by backend receipt limit]"
    return text[: MAX_RECEIPT_TEXT_CHARS - len(suffix)] + suffix

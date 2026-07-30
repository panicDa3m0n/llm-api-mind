"""Scarlet's bounded Research Lab shell organ.

The Lab is deliberately not a second memory system, autonomous worker, or
automatic context pack. It persists source-labelled computation evidence that
Scarlet can explicitly reopen through the same ``mind_shell`` surface.
"""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from typing import Any

from sqlmodel import Session

from app.mind.contracts import MemoryOperationResult, MindAPIContext
from app.research_lab.runner import (
    ResearchLabRunnerError,
    RunnerExecution,
    execute_python,
)
from app.research_lab.web import (
    ResearchLabWebError,
    fetch_public_web_document,
)
from app.storage import repositories


def handle_research_lab(
    body: dict[str, Any],
    context: MindAPIContext | None,
    *,
    intent: str,
) -> MemoryOperationResult:
    if context is None or context.engine is None or context.settings is None:
        return _error(
            "lab.context_required",
            "Research Lab commands require an active Scarlet runtime context.",
        )
    if not bool(getattr(context.settings, "research_lab_enabled", False)):
        return MemoryOperationResult(
            ok=False,
            error_code="lab.disabled",
            error_message=(
                "Research Lab is disabled by the operator in this runtime. "
                "It has not accessed code execution or web sources."
            ),
            cognitive_hint=(
                "This capability is operator-gated because it can retrieve external "
                "sources or request isolated computation."
            ),
            suggested_next_actions=["lab status", "Continue without Research Lab"],
        )

    profile_id = str(getattr(context.settings, "user_profile_id", None) or "local-user")
    action = str(body.get("action") or "status").strip().casefold().replace("-", "_")
    if action == "status":
        return _status(context, profile_id=profile_id)
    if action == "python":
        return _python(body, context, profile_id=profile_id, intent=intent)
    if action == "web_open":
        return _web_open(body, context, profile_id=profile_id, intent=intent)
    if action == "run":
        return _run_read(body, context, profile_id=profile_id)
    if action == "source":
        return _source_read(body, context, profile_id=profile_id)
    if action == "artifact":
        return _artifact_read(body, context, profile_id=profile_id)
    return _error("lab.action_unknown", f"Unknown Research Lab action: {action}")


def _status(context: MindAPIContext, *, profile_id: str) -> MemoryOperationResult:
    with Session(context.engine) as db:
        recent = repositories.list_research_lab_runs(
            db,
            profile_id=profile_id,
            limit=5,
        )
    runner_configured = bool(getattr(context.settings, "research_lab_runner_uds", None))
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "lab.status",
            "availability": {
                "web_open": "operator_enabled_public_https_only",
                "python": "runner_configured" if runner_configured else "operator_setup_required",
                "web_search": "not_implemented",
            },
            "isolation": {
                "python_network": "disabled_in_runner",
                "python_host_access": "not_available",
                "automatic_memory_or_context_injection": "disabled",
            },
            "recent_runs": [_run_summary(item) for item in recent],
        },
        cognitive_hint=(
            "Research Lab evidence is explicit and source-labelled. It is not added "
            "to memory or current context unless Scarlet opens it deliberately."
        ),
        suggested_next_actions=[
            'lab web open "https://..."',
            'lab python --code "from sympy import symbols; print(symbols(\'x\'))"',
        ],
    )


def _python(
    body: dict[str, Any],
    context: MindAPIContext,
    *,
    profile_id: str,
    intent: str,
) -> MemoryOperationResult:
    code = str(body.get("code") or "")
    max_code = int(getattr(context.settings, "research_lab_code_max_chars", 12_000))
    if not code.strip():
        return _error("lab.code_required", "lab python requires code.")
    if len(code) > max_code:
        return _error("lab.code_too_large", "The code exceeds the Research Lab size limit.")
    source_ids = _string_list(body.get("source_ids"))
    with Session(context.engine) as db:
        sources = _load_sources(db, source_ids=source_ids, profile_id=profile_id)
        if len(sources) != len(source_ids):
            return _error(
                "lab.source_not_found",
                "One or more requested Research Lab sources were not found for this profile.",
            )
        run = repositories.create_research_lab_run(
            db,
            profile_id=profile_id,
            session_id=context.session_id,
            turn_id=context.turn_id,
            action="python",
            intent=intent,
            request={"code_sha256": _sha256_text(code), "code_chars": len(code)},
            source_ids=source_ids,
            runner_identity="research-lab-runner-v1",
        )
        runner_sources = [
            {"id": source.id, "content": source.content}
            for source in sources
        ]
    try:
        execution = execute_python(
            settings=context.settings,
            code=code,
            sources=runner_sources,
        )
    except ResearchLabRunnerError as exc:
        return _failed_run(context, run_id=run.id, code="lab.runner_unavailable", message=str(exc))

    return _complete_python_run(
        context,
        profile_id=profile_id,
        run_id=run.id,
        execution=execution,
    )


def _web_open(
    body: dict[str, Any],
    context: MindAPIContext,
    *,
    profile_id: str,
    intent: str,
) -> MemoryOperationResult:
    url = str(body.get("url") or "").strip()
    if not url:
        return _error("lab.url_required", "lab web open requires a public HTTPS URL.")
    with Session(context.engine) as db:
        run = repositories.create_research_lab_run(
            db,
            profile_id=profile_id,
            session_id=context.session_id,
            turn_id=context.turn_id,
            action="web_open",
            intent=intent,
            request={"url": url},
        )
    try:
        document = fetch_public_web_document(
            url,
            timeout_seconds=float(
                getattr(context.settings, "research_lab_web_timeout_seconds", 12.0)
            ),
            max_bytes=int(getattr(context.settings, "research_lab_web_max_bytes", 512_000)),
            max_chars=int(getattr(context.settings, "research_lab_source_max_chars", 30_000)),
        )
    except ResearchLabWebError as exc:
        return _failed_run(context, run_id=run.id, code="lab.web_unavailable", message=str(exc))

    with Session(context.engine) as db:
        source = repositories.create_research_lab_source(
            db,
            run_id=run.id,
            profile_id=profile_id,
            url=document.url,
            title=document.title,
            content=document.content,
            content_sha256=document.content_sha256,
            content_type=document.content_type,
            retrieved_at=document.retrieved_at,
            metadata={"byte_size": document.byte_size},
        )
        repositories.complete_research_lab_run(
            db,
            run=run,
            result={
                "source_id": source.id,
                "url": source.url,
                "title": source.title,
                "content_type": source.content_type,
                "content_sha256": source.content_sha256,
                "content_chars": len(source.content),
            },
        )
        db.refresh(run)
        db.refresh(source)
        run_payload = _run_summary(run)
        source_payload = _source_summary(source)
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "lab.web_open",
            "run": run_payload,
            "source": source_payload,
        },
        cognitive_hint=(
            "The document is a bounded external source, not a memory or automatic "
            "context item. Open it by id when its text is useful."
        ),
        suggested_next_actions=[
            f"lab source {source.id}",
            f'lab python --source {source.id} --code "..."',
        ],
    )


def _complete_python_run(
    context: MindAPIContext,
    *,
    profile_id: str,
    run_id: str,
    execution: RunnerExecution,
) -> MemoryOperationResult:
    stdout = _clip(execution.stdout, 32_000)
    stderr = _clip(execution.stderr, 32_000)
    with Session(context.engine) as db:
        run = repositories.get_research_lab_run(db, run_id)
        if run is None:
            return _error("lab.run_not_found", "The Research Lab run disappeared before it could be stored.")
        artifacts = []
        max_artifact_bytes = int(
            getattr(context.settings, "research_lab_artifact_max_bytes", 1_000_000)
        )
        for item in execution.artifacts[:8]:
            try:
                content = base64.b64decode(item.content_base64, validate=True)
            except ValueError:
                continue
            if len(content) > max_artifact_bytes:
                continue
            artifact = repositories.create_research_lab_artifact(
                db,
                run_id=run.id,
                profile_id=profile_id,
                name=_safe_artifact_name(item.name),
                media_type=item.media_type or _media_type(item.name),
                content_bytes=content,
                sha256=hashlib.sha256(content).hexdigest(),
            )
            artifacts.append(artifact)
        result = {
            "status": execution.status,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": execution.exit_code,
            "timed_out": execution.timed_out,
            "source_paths": execution.source_paths,
            "artifact_ids": [item.id for item in artifacts],
        }
        completed = repositories.complete_research_lab_run(
            db,
            run=run,
            result=result,
            status="completed" if execution.status == "completed" else "failed",
        )
        db.refresh(completed)
        for artifact in artifacts:
            db.refresh(artifact)
        completed_payload = _run_summary(completed)
        artifact_payloads = [_artifact_summary(item) for item in artifacts]
    return MemoryOperationResult(
        ok=execution.status == "completed",
        result={
            "operation": "lab.python",
            "run": completed_payload,
            "output": result,
            "artifacts": artifact_payloads,
        },
        cognitive_hint=(
            "This is an isolated computation receipt. Treat printed results as "
            "evidence from the declared code and sources, and inspect source ids "
            "when their provenance matters."
        ),
        suggested_next_actions=[
            f"lab run {completed_payload['id']}",
            *[item["open_command"] for item in artifact_payloads],
        ],
        error_code=(None if execution.status == "completed" else "lab.execution_failed"),
        error_message=(None if execution.status == "completed" else "The isolated code run failed; inspect its receipt."),
    )


def _run_read(
    body: dict[str, Any],
    context: MindAPIContext,
    *,
    profile_id: str,
) -> MemoryOperationResult:
    run_id = str(body.get("run_id") or "").strip()
    if not run_id:
        return _error("lab.run_required", "lab run requires a run id.")
    with Session(context.engine) as db:
        run = repositories.get_research_lab_run(db, run_id)
        if run is None or run.profile_id != profile_id:
            return _error("lab.run_not_found", f"Research Lab run not found: {run_id}")
        artifacts = repositories.list_research_lab_artifacts(db, run_id=run.id)
        run_payload = _run_detail(run)
        artifact_payloads = [_artifact_summary(item) for item in artifacts]
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "lab.run",
            "run": run_payload,
            "artifacts": artifact_payloads,
        },
        cognitive_hint="This reopens the exact stored laboratory receipt and its source ids.",
        suggested_next_actions=[item["open_command"] for item in artifact_payloads],
    )


def _source_read(
    body: dict[str, Any],
    context: MindAPIContext,
    *,
    profile_id: str,
) -> MemoryOperationResult:
    source_id = str(body.get("source_id") or "").strip()
    if not source_id:
        return _error("lab.source_required", "lab source requires a source id.")
    with Session(context.engine) as db:
        source = repositories.get_research_lab_source(db, source_id)
        if source is None or source.profile_id != profile_id:
            return _error("lab.source_not_found", f"Research Lab source not found: {source_id}")
        source_payload = {
            **_source_summary(source),
            "content": _clip(
                source.content,
                int(getattr(context.settings, "research_lab_model_source_max_chars", 12_000)),
            ),
        }
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "lab.source",
            "source": source_payload,
        },
        cognitive_hint="This is source text retrieved at the declared time; it is not an asserted fact or a memory.",
        suggested_next_actions=[f'lab python --source {source_payload["id"]} --code "..."'],
    )


def _artifact_read(
    body: dict[str, Any],
    context: MindAPIContext,
    *,
    profile_id: str,
) -> MemoryOperationResult:
    artifact_id = str(body.get("artifact_id") or "").strip()
    if not artifact_id:
        return _error("lab.artifact_required", "lab artifact requires an artifact id.")
    with Session(context.engine) as db:
        artifact = repositories.get_research_lab_artifact(db, artifact_id)
        if artifact is None or artifact.profile_id != profile_id:
            return _error("lab.artifact_not_found", f"Research Lab artifact not found: {artifact_id}")
        text: str | None = None
        if artifact.media_type.startswith("text/") or artifact.media_type in {
            "application/json",
            "application/csv",
        }:
            text = _clip(
                artifact.content_bytes.decode("utf-8", errors="replace"),
                int(getattr(context.settings, "research_lab_model_source_max_chars", 12_000)),
            )
        artifact_payload = {**_artifact_summary(artifact), "text": text}
    return MemoryOperationResult(
        ok=True,
        result={
            "operation": "lab.artifact",
            "artifact": artifact_payload,
        },
        cognitive_hint=(
            "Text artifacts can be read here. Binary artifacts remain available to the "
            "human-facing trace/UI layer without being injected into model context."
        ),
    )


def _load_sources(db: Session, *, source_ids: list[str], profile_id: str) -> list[Any]:
    if len(source_ids) > 3:
        return []
    sources = [repositories.get_research_lab_source(db, source_id) for source_id in source_ids]
    return [source for source in sources if source is not None and source.profile_id == profile_id]


def _failed_run(
    context: MindAPIContext,
    *,
    run_id: str,
    code: str,
    message: str,
) -> MemoryOperationResult:
    with Session(context.engine) as db:
        run = repositories.get_research_lab_run(db, run_id)
        if run is not None:
            repositories.fail_research_lab_run(
                db,
                run=run,
                error={"code": code, "message": message},
            )
    return _error(code, message)


def _run_summary(run: Any) -> dict[str, Any]:
    return {
        "id": run.id,
        "action": run.action,
        "status": run.status,
        "source_ids": run.source_ids_json,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


def _run_detail(run: Any) -> dict[str, Any]:
    return {
        **_run_summary(run),
        "intent": run.intent,
        "request": run.request_json,
        "result": run.result_json,
        "error": run.error_json,
        "runner_identity": run.runner_identity,
    }


def _source_summary(source: Any) -> dict[str, Any]:
    return {
        "id": source.id,
        "run_id": source.run_id,
        "url": source.url,
        "title": source.title,
        "content_type": source.content_type,
        "content_sha256": source.content_sha256,
        "retrieved_at": source.retrieved_at.isoformat(),
        "content_chars": len(source.content),
        "open_command": f"lab source {source.id}",
    }


def _artifact_summary(artifact: Any) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "run_id": artifact.run_id,
        "name": artifact.name,
        "media_type": artifact.media_type,
        "byte_size": artifact.byte_size,
        "sha256": artifact.sha256,
        "open_command": f"lab artifact {artifact.id}",
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    values: list[str] = []
    for item in value:
        normalized = str(item).strip()
        if normalized and normalized not in values:
            values.append(normalized)
    return values


def _clip(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    suffix = "\n[Truncated by Research Lab limit]"
    if limit <= len(suffix):
        return value[:limit]
    return value[: limit - len(suffix)].rstrip() + suffix


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_artifact_name(value: str) -> str:
    return value.replace("\\", "/").split("/")[-1][:200] or "artifact"


def _media_type(name: str) -> str:
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def _error(code: str, message: str) -> MemoryOperationResult:
    return MemoryOperationResult(
        ok=False,
        error_code=code,
        error_message=message,
        suggested_next_actions=["lab status", "help lab"],
    )

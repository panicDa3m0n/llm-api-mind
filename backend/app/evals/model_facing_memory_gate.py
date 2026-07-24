"""Verify automatic memory delivery across rich retrieval, V2, and the LLM request.

This gate complements, but does not replace or rewrite,
``preliminary-regression-v1``. It deliberately starts from the same immutable
baseline whose historical memories lack source-message provenance, demonstrates
the resulting V2 exclusion, repairs only exact source-message hooks on a
disposable copy, and then verifies the complete model-facing delivery chain.

The final negative control proves that the gate rejects a failed turn even when
intermediate retrieval and model-context traces exist.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import Settings
from app.evals.frozen_baseline import (
    BASELINE_LFS_OID,
    FROZEN_REFERENCES,
    assert_frozen_baseline,
    prepare_disposable_copy,
    sha256_file,
    verify_frozen_references,
)
from app.llm.provider import LLMMessage, LLMStreamEvent, LLMTextResult
from app.main import create_app
from app.runtime.memory_provenance import (
    memory_provenance_audit,
    repair_exact_source_messages,
)
from app.storage import repositories
from app.storage.db import create_db_engine, init_db, prepare_runtime_database


SUITE_ID = "model-facing-memory-gate-v2"
TARGET = FROZEN_REFERENCES["zero_luce_active"]
DEPRECATED = FROZEN_REFERENCES["zero_luce_deprecated"]
PROMPT = "Quando nomino il Protocollo Zero-Luce, quale struttura devo seguire?"


@dataclass
class CaseResult:
    name: str
    objective: str
    passed: bool
    details: dict[str, Any]
    error: str | None = None


class ModelFacingGateProvider:
    """Controlled provider that satisfies the native final-answer boundary."""

    observed_systems: ClassVar[list[str]] = []
    include_final_marker: ClassVar[bool] = True
    chat_stop_reason: ClassVar[str] = "end_turn"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @classmethod
    def reset_observations(cls) -> None:
        cls.observed_systems = []

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        if system and "runtime answer-obligation judge" in system:
            payload = json.loads(prompt)
            findings = [
                {
                    "obligation_id": obligation["id"],
                    "status": "pass",
                    "reason": "The controlled draft is consistent with supplied evidence.",
                }
                for obligation in payload.get("obligations", [])
            ]
            text = json.dumps({"findings": findings})
        else:
            text = json.dumps(
                {
                    "review_summary": "Controlled model-facing memory gate review.",
                    "risks": [],
                    "claim_checks": [],
                    "missing_evidence": [],
                    "recommended_internal_actions": [],
                    "reasoning_digest": "",
                    "drift_findings": [],
                    "open_loops": [],
                    "tool_use_assessment": [],
                    "memory_candidates_from_reasoning": [],
                    "should_continue": False,
                    "next_focus_question": "",
                    "public_summary": "",
                }
            )
        return LLMTextResult(
            model="model-facing-gate-controlled",
            text=text,
            usage={"input_tokens": 1, "output_tokens": 1},
            stop_reason="end_turn",
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return self._chat_result(system)

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        return self._chat_result(system)

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: Any,
        max_tool_calls: int | None = None,
    ):
        result = self.generate_chat_with_tools(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            tools=tools,
            tool_runner=tool_runner,
            max_tool_calls=max_tool_calls,
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )

    def _chat_result(self, system: str | None) -> LLMTextResult:
        type(self).observed_systems.append(system or "")
        marker = "<scarlet-final/>" if type(self).include_final_marker else ""
        return LLMTextResult(
            model="model-facing-gate-controlled",
            text=f"Risposta controllata del gate model-facing.{marker}",
            usage={"input_tokens": 1, "output_tokens": 6},
            stop_reason=type(self).chat_stop_reason,
        )


class IncompleteGateProvider(ModelFacingGateProvider):
    """Negative-control provider that never reaches a natural terminal."""

    observed_systems: ClassVar[list[str]] = []
    include_final_marker: ClassVar[bool] = False
    chat_stop_reason: ClassVar[str] = "max_tokens"


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parents[2]
    baseline_db = _resolve(root, args.baseline_db)
    run_db = _resolve(root, args.run_db)
    assert_frozen_baseline(baseline_db)
    prepare_disposable_copy(
        baseline_db=baseline_db,
        run_db=run_db,
        marker="model-facing-memory-gate",
    )

    settings = Settings(
        environment="model-facing-memory-gate",
        agent_system_prompt="You are Scarlet.",
        database_url=f"sqlite:///{baseline_db}",
        database_role="preliminary",
        codex_test=True,
        codex_test_database_url=f"sqlite:///{run_db}",
        codex_test_seed_database_url=f"sqlite:///{baseline_db}",
        maintenance_enabled=False,
        organ_affect_mode="shadow",
    )
    engine = create_db_engine(prepare_runtime_database(settings))
    init_db(engine)
    results: list[CaseResult] = []

    try:
        with Session(engine) as db:
            source_details = verify_frozen_references(db)
        results.append(
            CaseResult(
                name="frozen_source_integrity",
                objective="Prove the immutable source and real references before mutation.",
                passed=True,
                details=source_details,
            )
        )

        compliant_client = _client(settings, engine, ModelFacingGateProvider)
        ModelFacingGateProvider.reset_observations()
        pre_session_id, pre_events = _run_turn(compliant_client, "before repair")
        pre = _turn_evidence(engine, pre_session_id)
        _assert_completed_turn(pre, pre_events)
        _assert_rich_selection(pre)
        _assert_memory_absent_from_model(pre, ModelFacingGateProvider.observed_systems)
        results.append(
            CaseResult(
                name="pre_repair_projection_exclusion",
                objective=(
                    "Prove rich retrieval can select the frozen memory while V2 and "
                    "the provider request correctly exclude its incomplete hook."
                ),
                passed=True,
                details=_evidence_summary(pre),
            )
        )

        repair = _repair_disposable_provenance(engine, baseline_db)
        results.append(
            CaseResult(
                name="guarded_disposable_provenance_repair",
                objective=(
                    "Apply only digest-reviewed exact source-message repairs to the "
                    "disposable database."
                ),
                passed=True,
                details=repair,
            )
        )

        ModelFacingGateProvider.reset_observations()
        post_session_id, post_events = _run_turn(compliant_client, "after repair")
        post = _turn_evidence(engine, post_session_id)
        delivery = _assert_model_delivery(
            post,
            post_events,
            ModelFacingGateProvider.observed_systems,
            expected_source_message_id=repair["target_source_message_id"],
        )
        results.append(
            CaseResult(
                name="post_repair_model_facing_delivery",
                objective=(
                    "Verify rich selection, V2 hook, source ids, llm.request, provider "
                    "input, completed turn, and persisted assistant answer."
                ),
                passed=True,
                details=delivery,
            )
        )

        incomplete_client = _client(settings, engine, IncompleteGateProvider)
        IncompleteGateProvider.reset_observations()
        failed_session_id, failed_events = _run_turn(
            incomplete_client,
            "incomplete negative control",
        )
        failed = _turn_evidence(engine, failed_session_id)
        rejection = _assert_gate_rejects_incomplete_turn(failed, failed_events)
        results.append(
            CaseResult(
                name="incomplete_turn_negative_control",
                objective=(
                    "Prove the gate rejects intermediate retrieval/context evidence "
                    "when the turn fails without a persisted final answer."
                ),
                passed=True,
                details=rejection,
            )
        )
    except Exception as exc:
        results.append(
            CaseResult(
                name="gate_execution",
                objective="Complete every dependent model-facing verification phase.",
                passed=False,
                details={},
                error=f"{type(exc).__name__}: {exc}",
            )
        )

    report = _report(baseline_db=baseline_db, run_db=run_db, results=results)
    report_dir = _write_report(root, report)
    print(json.dumps({"report_dir": str(report_dir), **report["summary"]}, indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-db", default="data/preliminary-rework-v1.db")
    parser.add_argument(
        "--run-db",
        default="data/preliminary-model-facing-memory-gate-v2-run.db",
    )
    return parser.parse_args()


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _client(settings: Settings, engine: Any, provider_factory: Any) -> TestClient:
    return TestClient(
        create_app(
            settings,
            db_engine=engine,
            llm_provider_factory=provider_factory,
        )
    )


def _run_turn(client: TestClient, title_suffix: str) -> tuple[str, list[dict[str, Any]]]:
    session_response = client.post(
        "/api/chat/sessions",
        json={"title": f"Model-facing memory gate {title_suffix}"},
    )
    assert session_response.status_code == 200, session_response.text
    session_id = session_response.json()["id"]
    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/turn/stream",
        json={"message": PROMPT, "max_tokens": 256},
    ) as response:
        assert response.status_code == 200, response.text
        events = [json.loads(line) for line in response.iter_lines() if line]
    return session_id, events


def _turn_evidence(engine: Any, session_id: str) -> dict[str, Any]:
    with Session(engine) as db:
        turns = repositories.list_turns_for_session(db, session_id=session_id)
        assert turns, f"session {session_id} has no turn"
        turn = turns[-1]
        traces = repositories.list_traces_for_turn(db, turn_id=turn.id)
        events = repositories.list_events_for_turn(db, turn_id=turn.id)
        messages = repositories.list_messages_for_turn(db, turn_id=turn.id)
    trace_payloads: dict[str, list[dict[str, Any]]] = {}
    for trace in traces:
        trace_payloads.setdefault(trace.kind, []).append(
            {"id": trace.id, "payload": trace.payload_json}
        )
    return {
        "session_id": session_id,
        "turn_id": turn.id,
        "turn_status": turn.status,
        "turn_error": turn.error_json,
        "messages": [
            {"id": message.id, "role": message.role, "content": message.content}
            for message in messages
        ],
        "traces": trace_payloads,
        "event_types": [event.type for event in events],
    }


def _trace(evidence: dict[str, Any], kind: str) -> dict[str, Any]:
    matches = evidence["traces"].get(kind, [])
    assert matches, f"turn {evidence['turn_id']} is missing {kind} trace"
    return matches[-1]


def _assert_rich_selection(evidence: dict[str, Any]) -> None:
    selected = _trace(evidence, "memory.context")["payload"].get("selected", [])
    selected_ids = [item.get("id") for item in selected if isinstance(item, dict)]
    assert TARGET.memory_id in selected_ids, selected_ids
    assert DEPRECATED.memory_id not in selected_ids, selected_ids


def _model_memory_ids(evidence: dict[str, Any]) -> list[str]:
    document = _trace(evidence, "model.context")["payload"]["document"]
    memories = document.get("memories", {})
    return [
        str(item.get("id"))
        for bucket in ("relevant", "recent_user", "recent_general")
        for item in memories.get(bucket, [])
        if isinstance(item, dict) and item.get("id")
    ]


def _assert_memory_absent_from_model(
    evidence: dict[str, Any],
    provider_systems: list[str],
) -> None:
    assert TARGET.memory_id not in _model_memory_ids(evidence)
    request = _trace(evidence, "llm.request")["payload"]
    assert TARGET.memory_id not in str(request.get("runtime_context") or "")
    assert TARGET.memory_id not in str(request.get("system") or "")
    assert provider_systems, "controlled provider did not observe a system request"
    assert all(TARGET.memory_id not in system for system in provider_systems)


def _assert_completed_turn(
    evidence: dict[str, Any],
    stream_events: list[dict[str, Any]],
) -> dict[str, Any]:
    assert evidence["turn_status"] == "completed", evidence["turn_error"]
    assistants = [
        message for message in evidence["messages"] if message["role"] == "assistant"
    ]
    assert len(assistants) == 1, assistants
    assert assistants[0]["content"].strip(), assistants
    assert "llm.error" not in evidence["traces"], evidence["traces"].keys()
    assert "turn.completed" in evidence["event_types"], evidence["event_types"]
    assert any(event.get("type") == "turn_complete" for event in stream_events)
    return {"assistant_message_id": assistants[0]["id"]}


def _assert_model_delivery(
    evidence: dict[str, Any],
    stream_events: list[dict[str, Any]],
    provider_systems: list[str],
    *,
    expected_source_message_id: str,
) -> dict[str, Any]:
    completion = _assert_completed_turn(evidence, stream_events)
    _assert_rich_selection(evidence)
    model_trace = _trace(evidence, "model.context")
    document = model_trace["payload"]["document"]
    relevant = document["memories"]["relevant"]
    target_hooks = [item for item in relevant if item.get("id") == TARGET.memory_id]
    assert len(target_hooks) == 1, relevant
    hook = target_hooks[0]
    assert hook["source_session_id"] == TARGET.source_session_id, hook
    assert hook["source_message_id"] == expected_source_message_id, hook

    request_trace = _trace(evidence, "llm.request")
    request = request_trace["payload"]
    assert request["model_context_profile"] == "v2", request
    assert request["model_context_trace_id"] == model_trace["id"], request
    runtime_context = str(request.get("runtime_context") or "")
    system = str(request.get("system") or "")
    for expected in (
        TARGET.memory_id,
        TARGET.source_session_id,
        expected_source_message_id,
    ):
        assert expected in runtime_context, expected
        assert expected in system, expected
    assert provider_systems, "controlled provider did not observe a system request"
    assert any(TARGET.memory_id in observed for observed in provider_systems)
    return {
        **completion,
        **_evidence_summary(evidence),
        "model_context_trace_id": model_trace["id"],
        "llm_request_trace_id": request_trace["id"],
        "source_message_id": expected_source_message_id,
        "provider_request_count": len(provider_systems),
    }


def _repair_disposable_provenance(engine: Any, baseline_db: Path) -> dict[str, Any]:
    with Session(engine) as db:
        audit = memory_provenance_audit(db)
        candidate = audit["candidate_sets"]["exact_source_message_repair"]
        assert TARGET.memory_id in candidate["memory_ids"], candidate
        target_audit = next(
            item for item in audit["items"] if item["memory_id"] == TARGET.memory_id
        )
        assert target_audit["provenance_class"] == "repairable_single_user_message"
        source_message_id = target_audit["proposed_source_message_id"]
        assert isinstance(source_message_id, str)
        dry_run = repair_exact_source_messages(db, dry_run=True)
        assert dry_run["candidate_set"] == candidate
        applied = repair_exact_source_messages(
            db,
            dry_run=False,
            expected_candidate_digest=candidate["digest_sha256"],
            backup_reference=(
                f"immutable-baseline:{baseline_db.name}:{BASELINE_LFS_OID}"
            ),
        )
        repaired = repositories.get_memory(db, TARGET.memory_id)
        assert repaired is not None
        assert repaired.source_message_id == source_message_id
        residual = applied["residual_audit"]
        target_residual = next(
            item
            for item in residual["items"]
            if item["memory_id"] == TARGET.memory_id
        )
        assert target_residual["provenance_class"] == "source_complete_valid"
    return {
        "candidate_count": candidate["count"],
        "candidate_digest": candidate["digest_sha256"],
        "applied_count": applied["applied_count"],
        "target_source_session_id": TARGET.source_session_id,
        "target_source_turn_id": repaired.source_turn_id,
        "target_source_message_id": source_message_id,
        "residual_target_provenance": target_residual["provenance_class"],
    }


def _assert_gate_rejects_incomplete_turn(
    evidence: dict[str, Any],
    stream_events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        _assert_completed_turn(evidence, stream_events)
    except AssertionError as exc:
        rejection_reason = str(exc) or "completion assertion failed"
    else:
        raise AssertionError("gate accepted an incomplete negative-control turn")

    _assert_rich_selection(evidence)
    assert TARGET.memory_id in _model_memory_ids(evidence)
    assert evidence["turn_status"] == "failed", evidence["turn_status"]
    assistants = [
        message for message in evidence["messages"] if message["role"] == "assistant"
    ]
    assert not assistants, assistants
    error = _trace(evidence, "llm.error")["payload"]
    assert error["code"] == "llm.incomplete_response", error
    assert not any(event.get("type") == "turn_complete" for event in stream_events)
    return {
        "turn_id": evidence["turn_id"],
        "turn_status": evidence["turn_status"],
        "llm_error_code": error["code"],
        "assistant_message_count": 0,
        "gate_rejected": True,
        "rejection_reason": rejection_reason,
    }


def _evidence_summary(evidence: dict[str, Any]) -> dict[str, Any]:
    rich = _trace(evidence, "memory.context")["payload"]
    request = _trace(evidence, "llm.request")["payload"]
    return {
        "session_id": evidence["session_id"],
        "turn_id": evidence["turn_id"],
        "turn_status": evidence["turn_status"],
        "rich_selected_ids": [
            item.get("id")
            for item in rich.get("selected", [])
            if isinstance(item, dict)
        ],
        "model_memory_ids": _model_memory_ids(evidence),
        "model_context_profile": request.get("model_context_profile"),
    }


def _report(
    *,
    baseline_db: Path,
    run_db: Path,
    results: list[CaseResult],
) -> dict[str, Any]:
    passed = sum(result.passed for result in results)
    return {
        "suite_id": SUITE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "path": str(baseline_db),
            "sha256": sha256_file(baseline_db),
            "published_lfs_oid": BASELINE_LFS_OID,
        },
        "run_database": {"path": str(run_db), "sha256": sha256_file(run_db)},
        "target": asdict(TARGET),
        "summary": {
            "passed": passed,
            "failed": len(results) - passed,
            "total": len(results),
        },
        "cases": [asdict(result) for result in results],
    }


def _write_report(root: Path, report: dict[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = root / "app" / "evals" / "runs" / f"{stamp}_{SUITE_ID}"
    report_dir.mkdir(parents=True, exist_ok=False)
    (report_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Model-Facing Memory Gate Report",
        "",
        f"Suite: `{report['suite_id']}`",
        f"Baseline SHA-256: `{report['baseline']['sha256']}`",
        "",
        "## Summary",
        "",
        f"Passed: `{report['summary']['passed']}/{report['summary']['total']}`",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"## {case['name']}",
                "",
                f"- Passed: `{case['passed']}`",
                f"- Objective: {case['objective']}",
                f"- Details: `{json.dumps(case['details'], ensure_ascii=True)}`",
                f"- Error: `{case['error'] or 'none'}`",
                "",
            ]
        )
    (report_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report_dir


if __name__ == "__main__":
    sys.exit(main())

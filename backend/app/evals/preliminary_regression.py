"""Run the reproducible pre/post-rework integration baseline.

This runner is intentionally separate from pytest. It exercises the assembled
FastAPI runtime against a frozen copy of the laboratory database, records the
real IDs it depends on, and writes an auditable report for comparison after a
large refactor. The provider is deterministic only where a repeatable response
is required to test integration contracts; it does not assess model quality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import Settings
from app.llm.provider import LLMMessage, LLMStreamEvent, LLMTextResult
from app.main import create_app
from app.mind.context import build_memory_context
from app.mind.memory import MindAPIContext
from app.mind.shell import MindShellRequest, dispatch_mind_shell
from app.runtime.preferences import load_runtime_preferences
from app.storage import repositories
from app.storage.db import create_db_engine, init_db
from app.storage.models import (
    AffectState,
    ChatSession,
    MemoryFact,
    MemoryRecord,
    Turn,
)


SUITE_ID = "preliminary-regression-v1"
BASELINE_LFS_OID = "827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5"
BASELINE_COUNTS = {
    "memories": 34,
    "memory_facts": 25,
    "sessions": 155,
    "messages": 567,
    "focus_records": 0,
    "intention_records": 0,
    "affect_states": 0,
}


@dataclass(frozen=True)
class Reference:
    name: str
    memory_id: str
    source_session_id: str
    fact_id: str | None
    status: str
    required_terms: tuple[str, ...]


REFERENCES = {
    "zero_luce_active": Reference(
        name="active Zero-Luce protocol",
        memory_id="mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3",
        source_session_id="ses_24fbc3a0722d4010b7bde8f74496ef69",
        fact_id="fact_75db0c43231047c0bf4e66d6c5ba2c3a",
        status="active",
        required_terms=("Protocollo Zero-Luce", "Rischio", "Prossima azione"),
    ),
    "zero_luce_deprecated": Reference(
        name="deprecated Zero-Luce predecessor",
        memory_id="mem_abed5590f91b4eb8aa93d1103db024de",
        source_session_id="ses_421dd143a25840adb317ef2afd2c2e9c",
        fact_id="fact_f35cda893b584765a25cffdfc2ae30d8",
        status="deprecated",
        required_terms=("Protocollo Zero-Luce", "tre blocchi"),
    ),
    "episodic_bridge": Reference(
        name="semantic-to-episodic bridge decision",
        memory_id="mem_06ef7093f3e74f099c77d6f356f67d26",
        source_session_id="ses_8f9145b9ca5a4aa78534936dac03a8d5",
        fact_id="fact_0f96f4c04c654d178e64195b5a81e239",
        status="active",
        required_terms=("semantic", "source_session_id", "episodic"),
    ),
}


@dataclass
class CaseResult:
    name: str
    objective: str
    passed: bool
    references: list[str]
    details: dict[str, Any]
    error: str | None = None


class PreliminaryProvider:
    """Controlled provider for runtime, affect, and metacognition plumbing."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        review = {
            "review_summary": "Controlled review requires current shell help.",
            "risks": [],
            "claim_checks": [],
            "missing_evidence": ["current Mind shell help"],
            "recommended_internal_actions": [
                {"command": "help", "reason": "Inspect current capabilities."}
            ],
            "reasoning_digest": "",
            "drift_findings": [],
            "open_loops": [],
            "tool_use_assessment": [],
            "memory_candidates_from_reasoning": [],
            "should_continue": True,
            "next_focus_question": "Which shell command is available?",
            "public_summary": "",
        }
        return LLMTextResult(
            model="preliminary-controlled-provider",
            text=json.dumps(review),
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
        return LLMTextResult(
            model="preliminary-controlled-provider",
            text="Preliminary runtime response.",
            usage={"input_tokens": len(messages), "output_tokens": 3},
            stop_reason="end_turn",
        )

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
        return self.generate_chat(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
        )

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
        yield LLMStreamEvent(type="text_delta", data={"text": result.text})
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parents[2]
    baseline_db = _resolve(root, args.baseline_db)
    run_db = _resolve(root, args.run_db)
    source_db = _resolve(root, args.source_db)

    if args.prepare_baseline:
        _prepare_baseline(
            source_db=source_db,
            baseline_db=baseline_db,
            replace=args.replace_baseline,
        )
    _assert_baseline(baseline_db)
    _prepare_run_database(baseline_db=baseline_db, run_db=run_db)
    run_database_sha256_before_tests = _sha256(run_db)

    settings = Settings(
        environment="preliminary-regression",
        agent_system_prompt="You are Scarlet.",
        database_url=f"sqlite:///{baseline_db}",
        codex_test=True,
        codex_test_database_url=f"sqlite:///{run_db}",
        codex_test_seed_database_url=f"sqlite:///{baseline_db}",
        maintenance_enabled=False,
        gpt_bridge_api_key="preliminary-regression-key",
        organ_affect_mode="model",
    )
    engine = create_db_engine(settings.codex_test_database_url)
    init_db(engine)
    client = TestClient(
        create_app(
            settings,
            db_engine=engine,
            llm_provider_factory=PreliminaryProvider,
        )
    )

    results: list[CaseResult] = []
    _run_case(
        results,
        "source_reference_integrity",
        "Verify the frozen laboratory data and the selected real references before any mutation.",
        list(REFERENCES),
        lambda: _check_source_references(engine),
    )
    _run_case(
        results,
        "automatic_memory_retrieval",
        "Verify runtime-context automatic retrieval selects the active real memory and excludes its deprecated predecessor.",
        ["zero_luce_active", "zero_luce_deprecated"],
        lambda: _check_automatic_retrieval(client),
    )
    _run_case(
        results,
        "manual_shell_memory_session_fact_navigation",
        "Verify model-facing shell help, memory search/facts/open/graph, and source-session navigation against real IDs.",
        ["zero_luce_active", "episodic_bridge"],
        lambda: _check_shell_navigation(engine),
    )
    _run_case(
        results,
        "semantic_memory_lifecycle",
        "Verify a fresh semantic memory can be written, retrieved, and deprecated in the isolated run database.",
        [],
        lambda: _check_memory_lifecycle(engine),
    )
    _run_case(
        results,
        "focus_and_volition_lifecycle",
        "Verify focus and latent-intention state transitions through the shell in a traceable session context.",
        [],
        lambda: _check_focus_and_volition(engine),
    )
    _run_case(
        results,
        "affect_runtime_and_shell_read",
        "Verify a message-driven affect appraisal enters runtime context and remains read-only through the shell.",
        [],
        lambda: _check_affect(client, engine),
    )
    _run_case(
        results,
        "metacognition_shell_contract",
        "Verify a metacognition step reaches the provider, validates a recommended shell command, and records a trace.",
        [],
        lambda: _check_metacognition(engine),
    )
    _run_case(
        results,
        "internal_maintenance_boundary",
        "Verify deterministic fact backfill remains an internal capability rather than a normal shell command.",
        [],
        lambda: _check_maintenance_boundary(engine),
    )
    _run_case(
        results,
        "gpt_bridge_lifecycle",
        "Verify external GPT bootstrap, shell action, and finalize preserve one coherent Scarlet turn.",
        [],
        lambda: _check_gpt_bridge(client),
    )

    report = _report(
        baseline_db=baseline_db,
        run_db=run_db,
        run_database_sha256_before_tests=run_database_sha256_before_tests,
        results=results,
    )
    report_dir = _write_report(root, report)
    print(json.dumps({"report_dir": str(report_dir), **report["summary"]}, indent=2))
    return 0 if report["summary"]["failed"] == 0 else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", default="data/app.db")
    parser.add_argument("--baseline-db", default="data/preliminary-rework-v1.db")
    parser.add_argument("--run-db", default="data/preliminary-rework-v1-run.db")
    parser.add_argument(
        "--prepare-baseline",
        action="store_true",
        help="Copy --source-db to --baseline-db after validating the published LFS hash.",
    )
    parser.add_argument("--replace-baseline", action="store_true")
    return parser.parse_args()


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _prepare_baseline(*, source_db: Path, baseline_db: Path, replace: bool) -> None:
    if not source_db.exists():
        raise RuntimeError(f"Baseline source database does not exist: {source_db}")
    source_hash = _sha256(source_db)
    if source_hash != BASELINE_LFS_OID:
        raise RuntimeError(
            "Refusing to freeze a moving or unknown database. Expected published "
            f"LFS SHA-256 {BASELINE_LFS_OID}, received {source_hash}."
        )
    if baseline_db.exists() and not replace:
        raise RuntimeError(
            f"Baseline already exists: {baseline_db}. Use --replace-baseline only "
            "when deliberately recreating the checkpoint."
        )
    baseline_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_db, baseline_db)


def _assert_baseline(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(
            f"Frozen baseline missing: {path}. Run once with --prepare-baseline "
            "and the published Git-LFS database as --source-db."
        )
    actual_hash = _sha256(path)
    if actual_hash != BASELINE_LFS_OID:
        raise RuntimeError(
            f"Frozen baseline hash mismatch: expected {BASELINE_LFS_OID}, got {actual_hash}."
        )


def _prepare_run_database(*, baseline_db: Path, run_db: Path) -> None:
    if run_db.exists():
        if "preliminary-rework" not in run_db.name:
            raise RuntimeError(f"Refusing to remove non-suite database: {run_db}")
        run_db.unlink()
    run_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(baseline_db, run_db)


def _run_case(
    results: list[CaseResult],
    name: str,
    objective: str,
    references: list[str],
    check: Callable[[], dict[str, Any]],
) -> None:
    try:
        results.append(
            CaseResult(
                name=name,
                objective=objective,
                passed=True,
                references=references,
                details=check(),
            )
        )
    except AssertionError as exc:
        results.append(
            CaseResult(
                name=name,
                objective=objective,
                passed=False,
                references=references,
                details={},
                error=str(exc) or "assertion failed",
            )
        )
    except Exception as exc:  # Preserve unexpected integration failures in report.
        results.append(
            CaseResult(
                name=name,
                objective=objective,
                passed=False,
                references=references,
                details={},
                error=f"{type(exc).__name__}: {exc}",
            )
        )


def _check_source_references(engine: Any) -> dict[str, Any]:
    with Session(engine) as db:
        counts = {
            "memories": len(db.exec(select(MemoryRecord)).all()),
            "memory_facts": len(db.exec(select(MemoryFact)).all()),
            "sessions": len(db.exec(select(ChatSession)).all()),
            "messages": _table_count(db, "messages"),
            "focus_records": _table_count(db, "focus_records"),
            "intention_records": _table_count(db, "intention_records"),
            "affect_states": len(db.exec(select(AffectState)).all()),
        }
        assert counts == BASELINE_COUNTS, f"baseline inventory changed: {counts}"
        resolved: dict[str, Any] = {}
        for key, reference in REFERENCES.items():
            memory = db.get(MemoryRecord, reference.memory_id)
            assert memory is not None, f"missing memory reference {reference.memory_id}"
            assert memory.status == reference.status, (
                f"{reference.memory_id} status {memory.status!r} != {reference.status!r}"
            )
            assert memory.source_session_id == reference.source_session_id
            for term in reference.required_terms:
                assert term.casefold() in memory.content.casefold(), (
                    f"{reference.memory_id} missing expected term {term!r}"
                )
            assert db.get(ChatSession, reference.source_session_id) is not None
            if reference.fact_id is not None:
                fact = db.get(MemoryFact, reference.fact_id)
                assert fact is not None, f"missing fact reference {reference.fact_id}"
                assert fact.memory_id == reference.memory_id
                assert fact.status == reference.status
            resolved[key] = asdict(reference)
    return {"counts": counts, "references": resolved}


def _check_automatic_retrieval(client: TestClient) -> dict[str, Any]:
    active = REFERENCES["zero_luce_active"]
    deprecated = REFERENCES["zero_luce_deprecated"]
    session = client.post(
        "/api/chat/sessions", json={"title": "Preliminary automatic retrieval"}
    ).json()
    events = _stream_turn(
        client,
        session["id"],
        "Quando nomino il Protocollo Zero-Luce, quale struttura devo seguire?",
    )
    memory_context = _event_data(events, "memory_context")
    selected = memory_context.get("selected", [])
    selected_ids = [item.get("id") for item in selected if isinstance(item, dict)]
    assert active.memory_id in selected_ids, (
        f"automatic retrieval omitted active reference: {selected_ids}"
    )
    assert deprecated.memory_id not in selected_ids, (
        f"automatic retrieval injected deprecated reference: {selected_ids}"
    )
    runtime_context = _event_data(events, "runtime_context")
    block_types = [
        item.get("type")
        for item in runtime_context.get("blocks", [])
        if isinstance(item, dict)
    ]
    assert {"session_context", "message_context", "scarlet_state"} <= set(block_types)
    return {
        "session_id": session["id"],
        "selected_ids": selected_ids,
        "block_types": block_types,
        "candidate_count": memory_context.get("candidate_count"),
    }


def _check_shell_navigation(engine: Any) -> dict[str, Any]:
    context = _new_context(engine, "Preliminary shell navigation")
    active = REFERENCES["zero_luce_active"]
    bridge = REFERENCES["episodic_bridge"]
    help_response = _shell("help memory", context)
    assert help_response.ok is True
    assert help_response.result["operation"] == "mind_shell.help"

    search = _shell('memory search "Protocollo Zero-Luce" --top 5', context)
    assert search.ok is True
    search_ids = [item["id"] for item in search.result["data"]["memories"]]
    assert active.memory_id in search_ids, search_ids

    facts = _shell('memory facts --query "Protocollo Zero-Luce"', context)
    assert facts.ok is True
    fact_ids = _nested_ids(facts.result["data"], "fact")
    assert active.fact_id in fact_ids, fact_ids

    opened = _shell(f"memory open {bridge.memory_id}", context)
    assert opened.ok is True
    memory = opened.result["data"]["memory"]
    assert memory["source_session_id"] == bridge.source_session_id

    graph = _shell(f"memory graph {active.memory_id} --depth 2 --limit 30", context)
    assert graph.ok is True
    assert graph.result["target"] == "memory.graph"

    session = _shell(f"session open {bridge.source_session_id} --limit 20", context)
    assert session.ok is True
    assert session.result["data"]["session"]["id"] == bridge.source_session_id
    assert session.result["data"]["transcript_window"]["returned_count"] >= 2
    return {
        "context_session_id": context.session_id,
        "search_ids": search_ids,
        "fact_ids": fact_ids,
        "opened_source_session_id": memory["source_session_id"],
        "graph_target": graph.result["target"],
        "session_message_count": session.result["data"]["transcript_window"]["returned_count"],
    }


def _check_memory_lifecycle(engine: Any) -> dict[str, Any]:
    context = _new_context(engine, "Preliminary semantic memory lifecycle")
    write = _shell(
        'memory write --type task_context --scope project '
        '--content "Preliminary rework regression marker for isolated lifecycle verification." '
        '--reason "Verify shell write, retrieval, and lifecycle behavior before refactor." '
        '--future-use "Compare the same operation after the rework."',
        context,
    )
    assert write.ok is True
    memory_id = write.result["data"]["memory_id"]
    search = _shell('memory search "preliminary rework regression marker" --top 5', context)
    assert search.ok is True
    assert memory_id in [item["id"] for item in search.result["data"]["memories"]]
    deprecated = _shell(
        f'memory deprecate {memory_id} --reason "Lifecycle verification completed."',
        context,
    )
    assert deprecated.ok is True
    return {
        "session_id": context.session_id,
        "memory_id": memory_id,
        "search_result_count": len(search.result["data"]["memories"]),
        "deprecated_target": deprecated.result["target"],
    }


def _check_focus_and_volition(engine: Any) -> dict[str, Any]:
    context = _new_context(engine, "Preliminary focus and volition lifecycle")
    focus = _shell(
        'focus set "preliminary regression integrity" --type investigation '
        '--reason "Check focus lifecycle before a structural rework." --intensity 0.7',
        context,
    )
    assert focus.ok is True
    focus_id = focus.result["data"]["active_focus"]["id"]
    current = _shell("focus read", context)
    assert current.ok is True
    assert current.result["data"]["focus"]["id"] == focus_id
    resolved = _shell(
        f'focus resolve {focus_id} --resolution "Preliminary focus check completed."',
        context,
    )
    assert resolved.ok is True

    intention = _shell(
        'volition create "verificare la regressione dopo il rework" '
        '--reason "Keep the comparison requirement visible." --horizon short --intensity 0.6',
        context,
    )
    assert intention.ok is True
    intention_id = intention.result["data"]["intention"]["id"]
    read = _shell(f"volition read {intention_id}", context)
    assert read.ok is True
    assert read.result["data"]["intention"]["id"] == intention_id
    closed = _shell(
        f'volition resolve {intention_id} --resolution "Preliminary lifecycle check completed."',
        context,
    )
    assert closed.ok is True
    return {
        "session_id": context.session_id,
        "focus_id": focus_id,
        "focus_resolution_target": resolved.result["target"],
        "intention_id": intention_id,
        "intention_resolution_target": closed.result["target"],
    }


def _check_affect(client: TestClient, engine: Any) -> dict[str, Any]:
    session = client.post(
        "/api/chat/sessions", json={"title": "Preliminary affect appraisal"}
    ).json()
    events = _stream_turn(
        client,
        session["id"],
        "Non funziona, continua a dare errore e mi blocca.",
    )
    runtime_context = _event_data(events, "runtime_context")
    affect_blocks = [
        item
        for item in runtime_context.get("blocks", [])
        if isinstance(item, dict) and item.get("type") == "affective_context"
    ]
    assert len(affect_blocks) == 1, affect_blocks
    assert affect_blocks[0]["content"]["current_emotion"] == "frustration"
    turn_id = _latest_turn_id(engine, session["id"])
    response = _shell("affect read", _context(engine, session["id"], turn_id))
    assert response.ok is True
    affect = response.result["data"]["affect_state"]
    assert affect["emotion"] == "frustration"
    assert response.result["data"]["affect_policy"]["read_only"] is True
    return {
        "session_id": session["id"],
        "turn_id": turn_id,
        "emotion": affect["emotion"],
        "affect_state_id": affect["id"],
    }


def _check_metacognition(engine: Any) -> dict[str, Any]:
    context = _new_context(engine, "Preliminary metacognition shell contract")
    response = _shell(
        'metacognition step --objective "Verify whether the shell contract is current" '
        '--mode critic --draft "The shell contract is current."',
        context,
    )
    assert response.ok is True
    review = response.result["data"]["review"]
    assert review["should_continue"] is True
    actions = review["recommended_internal_actions"]
    assert actions[0]["command"] == "help"
    assert actions[0]["call_is_available"] is True
    trace_ids = response.result["data"]["trace_ids"]
    assert trace_ids
    return {
        "session_id": context.session_id,
        "trace_ids": trace_ids,
        "recommended_command": actions[0]["command"],
        "recommended_command_status": actions[0]["schema_status"],
    }


def _check_maintenance_boundary(engine: Any) -> dict[str, Any]:
    context = _new_context(engine, "Preliminary maintenance boundary")
    help_response = _shell("help memory", context)
    commands = help_response.result["catalog"]["commands"][0]["commands"]
    assert not any("backfill" in command for command in commands), commands
    with Session(engine) as db:
        session = db.get(ChatSession, context.session_id)
        assert session is not None
        user_message = repositories.add_message(
            db,
            session_id=session.id,
            turn_id=context.turn_id,
            role="user",
            content="Verifico il confine della manutenzione interna.",
        )
        history = repositories.list_messages(db, session_id=session.id)
        runtime = build_memory_context(
            db,
            chat_session=session,
            current_user_message=user_message,
            history=history,
            settings=context.settings,
            runtime_preferences=load_runtime_preferences(db, context.settings),
            turn_id=context.turn_id,
        ).runtime_payload
    capability = runtime["capabilities"].get("memory.facts.backfill")
    assert capability == "internal_maintenance_only", capability
    return {"backfill_capability": capability, "shell_commands": commands}


def _check_gpt_bridge(client: TestClient) -> dict[str, Any]:
    headers = {"X-GPT-Bridge-Key": "preliminary-regression-key"}
    bootstrap = client.post(
        "/gpt/bootstrap",
        headers=headers,
        json={"title": "Preliminary GPT bridge", "message": "Riprendiamo il filo."},
    )
    assert bootstrap.status_code == 200, bootstrap.text
    boot = bootstrap.json()
    session_id, turn_id = boot["session_id"], boot["turn_id"]
    assert boot["context"]["profile"] == "gpt-bootstrap-compact-v1"
    action = client.post(
        "/gpt/action",
        headers=headers,
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "command": "help memory",
            "intent": "Verify the bridge delegates to the shell.",
        },
    )
    assert action.status_code == 200, action.text
    action_payload = action.json()
    assert action_payload["response"]["ok"] is True
    assert action_payload["response"]["result"]["operation"] == "mind_shell.help"
    answer = "Il turno bridge preliminare e stato finalizzato."
    finalize = client.post(
        "/gpt/finalize",
        headers=headers,
        json={"session_id": session_id, "turn_id": turn_id, "answer": answer},
    )
    assert finalize.status_code == 200, finalize.text
    final_payload = finalize.json()
    assert final_payload["final_answer_to_show"] == answer
    return {
        "session_id": session_id,
        "turn_id": turn_id,
        "tool_call_id": action_payload["tool_call_id"],
        "final_answer_to_show": final_payload["final_answer_to_show"],
    }


def _new_context(engine: Any, title: str) -> MindAPIContext:
    with Session(engine) as db:
        session = repositories.create_chat_session(db, title=title)
        turn = repositories.create_turn(db, session_id=session.id, model="preliminary")
        session_id = session.id
        turn_id = turn.id
    return _context(engine, session_id, turn_id)


def _context(engine: Any, session_id: str, turn_id: str | None = None) -> MindAPIContext:
    return MindAPIContext(
        engine=engine,
        session_id=session_id,
        turn_id=turn_id,
        settings=Settings(
            environment="preliminary-regression",
            maintenance_enabled=False,
            organ_affect_mode="model",
        ),
        provider_factory=PreliminaryProvider,
    )


def _shell(command: str, context: MindAPIContext):
    return dispatch_mind_shell(
        MindShellRequest(command=command, intent="Preliminary regression verification."),
        context=context,
    )


def _stream_turn(client: TestClient, session_id: str, message: str) -> list[dict[str, Any]]:
    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/turn/stream",
        json={"message": message, "max_tokens": 256},
    ) as response:
        assert response.status_code == 200, response.text
        return [json.loads(line) for line in response.iter_lines() if line]


def _event_data(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for event in events:
        if event.get("type") == event_type and isinstance(event.get("data"), dict):
            return event["data"]
    raise AssertionError(f"missing stream event {event_type!r}")


def _nested_ids(payload: Any, prefix: str) -> list[str]:
    if isinstance(payload, dict):
        values: list[str] = []
        for key, value in payload.items():
            if key == "id" and isinstance(value, str) and value.startswith(f"{prefix}_"):
                values.append(value)
            values.extend(_nested_ids(value, prefix))
        return values
    if isinstance(payload, list):
        return [item for value in payload for item in _nested_ids(value, prefix)]
    return []


def _latest_turn_id(engine: Any, session_id: str) -> str:
    with Session(engine) as db:
        turn = db.exec(
            select(Turn)
            .where(Turn.session_id == session_id)
            .order_by(Turn.started_at.desc())
        ).first()
        assert turn is not None
        return turn.id


def _table_count(db: Session, table: str) -> int:
    result = db.connection().exec_driver_sql(f"SELECT COUNT(*) FROM {table}")
    return int(result.scalar_one())


def _report(
    *,
    baseline_db: Path,
    run_db: Path,
    run_database_sha256_before_tests: str,
    results: list[CaseResult],
) -> dict[str, Any]:
    passed = sum(result.passed for result in results)
    return {
        "suite_id": SUITE_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": {
            "path": str(baseline_db),
            "sha256": _sha256(baseline_db),
            "published_lfs_oid": BASELINE_LFS_OID,
            "inventory": BASELINE_COUNTS,
        },
        "run_database": {
            "path": str(run_db),
            "sha256_before_tests": run_database_sha256_before_tests,
        },
        "references": {key: asdict(value) for key, value in REFERENCES.items()},
        "summary": {"passed": passed, "failed": len(results) - passed, "total": len(results)},
        "cases": [asdict(result) for result in results],
    }


def _write_report(root: Path, report: dict[str, Any]) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_dir = root / "app" / "evals" / "runs" / f"{stamp}_{SUITE_ID}"
    report_dir.mkdir(parents=True, exist_ok=False)
    (report_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8"
    )
    lines = [
        "# Preliminary Regression Report",
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
                f"- References: `{', '.join(case['references']) or 'test-created only'}`",
                f"- Details: `{json.dumps(case['details'], ensure_ascii=True)}`",
                f"- Error: `{case['error'] or 'none'}`",
                "",
            ]
        )
    (report_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return report_dir


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    sys.exit(main())

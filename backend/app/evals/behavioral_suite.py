"""Run and review the repeatable natural-language Scarlet behavior suite.

Execution uses the real configured provider and a fresh disposable copy of the
frozen preliminary database for every independent group repetition. The runner
automates only objective evidence. Qualitative layers remain pending until a
human or project-informed LLM evaluator records a reasoned judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.evals.behavioral_contracts import (
    BehavioralJudgment,
    BehavioralRunRecord,
    BehavioralScenario,
    BehavioralScenarioGroup,
    BehavioralSuite,
    EvaluationLayerResult,
)
from app.evals.behavioral_evidence import (
    describe_state_changes,
    evaluate_objective_evidence,
    extract_turn_evidence,
    snapshot_cognitive_state,
)
from app.evals.frozen_baseline import (
    BASELINE_LFS_OID,
    assert_frozen_baseline,
    prepare_disposable_copy,
    sha256_file,
    verify_frozen_references,
)
from app.llm.factory import active_provider_model, active_provider_name
from app.main import create_app
from app.storage.db import create_db_engine
from app.storage.models import ChatSession, MemoryFact, MemoryRecord


DEFAULT_CATALOG = Path("app/evals/scenarios/behavioral-v1/suite.json")
DEFAULT_RUNS_DIR = Path("app/evals/runs")
DEFAULT_RUN_DB_ROOT = Path("data/behavioral-suite-runs")


def load_behavioral_suite(path: Path) -> BehavioralSuite:
    return BehavioralSuite.model_validate_json(path.read_text(encoding="utf-8"))


def run_behavioral_suite(
    *,
    suite: BehavioralSuite,
    catalog_path: Path,
    backend_root: Path,
    runs_dir: Path,
    run_db_root: Path,
    selected_group_ids: set[str] | None = None,
) -> Path:
    baseline_db = _resolve(backend_root, suite.baseline_database)
    assert_frozen_baseline(baseline_db)
    if suite.database_fingerprint != BASELINE_LFS_OID:
        raise RuntimeError("Suite fingerprint differs from the canonical frozen baseline.")

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suite_run_id = f"{run_stamp}_{suite.id}"
    output_dir = _resolve(backend_root, runs_dir) / suite_run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    scenario_by_id = {scenario.id: scenario for scenario in suite.scenarios}
    base_settings = Settings()
    records: list[BehavioralRunRecord] = []
    evidence_index: list[dict[str, Any]] = []

    groups = [
        group
        for group in suite.groups
        if selected_group_ids is None or group.id in selected_group_ids
    ]
    if not groups:
        raise RuntimeError("No behavioral groups selected.")

    _write_json(
        output_dir / "manifest.json",
        {
            "suite_run_id": suite_run_id,
            "suite": suite.model_dump(mode="json"),
            "catalog_path": str(catalog_path),
            "catalog_sha256": sha256_file(catalog_path),
            "git_commit": _git_commit(backend_root),
            "provider": active_provider_name(base_settings),
            "model": active_provider_model(base_settings),
            "max_tokens": _provider_max_tokens(base_settings),
            "selected_groups": [group.id for group in groups],
            "judgment_policy": (
                "Objective runtime facts are checked deterministically. Cognitive choice, "
                "answer quality, and longitudinal value require a reasoned human or "
                "project-informed LLM-as-human judgment."
            ),
        },
    )

    total_repetitions = sum(group.repetitions for group in groups)
    completed_repetitions = 0
    for group in groups:
        for repetition in range(1, group.repetitions + 1):
            completed_repetitions += 1
            print(
                f"[{completed_repetitions}/{total_repetitions}] group={group.id} "
                f"repetition={repetition}: preparing isolated database",
                flush=True,
            )
            run_db = (
                _resolve(backend_root, run_db_root)
                / suite_run_id
                / f"preliminary-behavioral-{group.id}-r{repetition}.db"
            )
            prepare_disposable_copy(
                baseline_db=baseline_db,
                run_db=run_db,
                marker="behavioral-",
            )
            group_records, group_evidence = _run_group_repetition(
                suite=suite,
                group=group,
                repetition=repetition,
                scenario_by_id=scenario_by_id,
                baseline_db=baseline_db,
                run_db=run_db,
                base_settings=base_settings,
                output_dir=output_dir,
            )
            records.extend(group_records)
            evidence_index.extend(group_evidence)
            _write_records(output_dir / "records.pending.json", records)
            _write_json(output_dir / "evidence-index.json", evidence_index)
            print(
                f"[{completed_repetitions}/{total_repetitions}] group={group.id} "
                f"repetition={repetition}: captured {len(group_records)} turn(s)",
                flush=True,
            )

    _write_pending_summary(output_dir, suite, records)
    return output_dir


def apply_judgments(*, run_dir: Path, judgment_path: Path) -> Path:
    records = _load_records(run_dir / "records.pending.json")
    judgments = TypeAdapter(list[BehavioralJudgment]).validate_json(
        judgment_path.read_text(encoding="utf-8")
    )
    by_run_id = {judgment.run_id: judgment for judgment in judgments}
    missing = [record.run_id for record in records if record.run_id not in by_run_id]
    extra = sorted(set(by_run_id) - {record.run_id for record in records})
    if missing or extra:
        raise RuntimeError(f"Judgment coverage mismatch; missing={missing}, extra={extra}")

    reviewed: list[BehavioralRunRecord] = []
    for record in records:
        judgment = by_run_id[record.run_id]
        if judgment.scenario_id != record.scenario_id:
            raise RuntimeError(f"Judgment scenario mismatch for {record.run_id}")
        reviewed.append(
            record.model_copy(
                update={
                    "cognitive_choice": judgment.cognitive_choice,
                    "answer_outcome": judgment.answer_outcome,
                    "longitudinal_effect": judgment.longitudinal_effect,
                }
            )
        )
    destination = run_dir / "records.reviewed.json"
    _write_records(destination, reviewed)
    _write_reviewed_summary(run_dir, reviewed)
    return destination


def compare_reviewed_runs(*, before_dir: Path, after_dir: Path) -> dict[str, Any]:
    before = _load_records(before_dir / "records.reviewed.json")
    after = _load_records(after_dir / "records.reviewed.json")
    before_by_key = {_record_key(record): record for record in before}
    after_by_key = {_record_key(record): record for record in after}
    if set(before_by_key) != set(after_by_key):
        raise RuntimeError("Reviewed runs do not contain equivalent scenario repetitions.")

    objective_regressions: list[dict[str, Any]] = []
    qualitative_review: list[dict[str, Any]] = []
    for key in sorted(before_by_key):
        old = before_by_key[key]
        new = after_by_key[key]
        if old.technical_execution.status == "pass" and new.technical_execution.status != "pass":
            objective_regressions.append(
                {
                    "key": key,
                    "before": old.technical_execution.model_dump(mode="json"),
                    "after": new.technical_execution.model_dump(mode="json"),
                }
            )
        for layer_name in (
            "cognitive_choice",
            "answer_outcome",
            "longitudinal_effect",
        ):
            old_layer = getattr(old, layer_name)
            new_layer = getattr(new, layer_name)
            if old_layer.status != new_layer.status or old.response_text != new.response_text:
                qualitative_review.append(
                    {
                        "key": key,
                        "layer": layer_name,
                        "before_judgment": old_layer.model_dump(mode="json"),
                        "after_judgment": new_layer.model_dump(mode="json"),
                        "before_answer": old.response_text,
                        "after_answer": new.response_text,
                        "decision": "requires_reasoned_review",
                    }
                )
    return {
        "comparison_policy": (
            "Only objective technical regressions are classified automatically. "
            "Natural-language or qualitative differences require reasoned review."
        ),
        "objective_regressions": objective_regressions,
        "qualitative_review": qualitative_review,
        "automatically_admissible": not objective_regressions,
    }


def _run_group_repetition(
    *,
    suite: BehavioralSuite,
    group: BehavioralScenarioGroup,
    repetition: int,
    scenario_by_id: dict[str, BehavioralScenario],
    baseline_db: Path,
    run_db: Path,
    base_settings: Settings,
    output_dir: Path,
) -> tuple[list[BehavioralRunRecord], list[dict[str, Any]]]:
    settings = _evaluation_settings(
        base_settings,
        suite=suite,
        baseline_db=baseline_db,
        run_db=run_db,
    )
    engine = create_db_engine(f"sqlite:///{run_db}")
    app = create_app(settings, db_engine=engine)
    with Session(engine) as db:
        verify_frozen_references(db)

    records: list[BehavioralRunRecord] = []
    evidence_index: list[dict[str, Any]] = []
    scenario_sessions: dict[str, str] = {}
    with TestClient(app) as client:
        for scenario_id in group.scenario_ids:
            scenario = scenario_by_id[scenario_id]
            _verify_starting_condition(scenario, engine)
            session_id = _resolve_scenario_session(
                client=client,
                scenario=scenario,
                scenario_sessions=scenario_sessions,
            )
            scenario_sessions[scenario.id] = session_id
            state_before = snapshot_cognitive_state(
                engine, profile_id=settings.user_profile_id
            )
            print(
                f"  {scenario.id}: sending natural prompt in session {session_id}",
                flush=True,
            )
            events = _stream_turn(client, session_id, scenario.natural_user_prompt)
            complete = _final_turn(events)
            turn_id = str(complete.get("turn_id") or _first_turn_id(events) or "")
            if not turn_id:
                raise RuntimeError(f"{scenario.id} produced no turn id")
            traces_response = client.get(f"/api/debug/traces/{turn_id}")
            traces_response.raise_for_status()
            traces = traces_response.json()
            response_text = _answer_text(events, complete)
            evidence = extract_turn_evidence(events=events, traces=traces)
            state_after = snapshot_cognitive_state(
                engine, profile_id=settings.user_profile_id
            )
            technical = evaluate_objective_evidence(
                scenario=scenario,
                evidence=evidence,
                state_before=state_before,
                state_after=state_after,
            )
            record_id = f"{group.id}-r{repetition}-{scenario.id}"
            record = BehavioralRunRecord(
                scenario_id=scenario.id,
                run_id=record_id,
                group_id=group.id,
                repetition=repetition,
                started_from_fingerprint=suite.database_fingerprint,
                scenario_definition_digest=_scenario_digest(scenario),
                provider=active_provider_name(settings),
                model=active_provider_model(settings),
                completed_at=datetime.now(timezone.utc),
                session_ids=[session_id],
                turn_ids=[turn_id],
                response_text=response_text,
                technical_execution=technical,
                cognitive_choice=_pending_layer("Awaiting reasoned cognitive-choice review."),
                answer_outcome=_pending_layer("Awaiting reasoned answer-quality review."),
                longitudinal_effect=_pending_layer(
                    "Awaiting review against this scenario's chain and final state."
                ),
                raw_trace_ids=evidence["trace_ids"],
                observed_state_changes=describe_state_changes(state_before, state_after),
            )
            evidence_path = output_dir / "evidence" / f"{record_id}.json"
            _write_json(
                evidence_path,
                {
                    "record": record.model_dump(mode="json"),
                    "scenario": scenario.model_dump(mode="json"),
                    "events": events,
                    "traces": traces,
                    "extracted_evidence": evidence,
                    "state_before": state_before,
                    "state_after": state_after,
                    "database": str(run_db),
                },
            )
            records.append(record)
            evidence_index.append(
                {
                    "run_id": record_id,
                    "scenario_id": scenario.id,
                    "group_id": group.id,
                    "repetition": repetition,
                    "evidence_path": str(evidence_path.relative_to(output_dir)),
                    "technical_status": technical.status,
                }
            )
    engine.dispose()
    return records, evidence_index


def _evaluation_settings(
    base: Settings,
    *,
    suite: BehavioralSuite,
    baseline_db: Path,
    run_db: Path,
) -> Settings:
    overrides: dict[str, Any] = {
        "environment": "behavioral-evaluation",
        "database_url": f"sqlite:///{baseline_db}",
        "database_role": "preliminary",
        "codex_test": True,
        "codex_test_database_url": f"sqlite:///{run_db}",
        "codex_test_seed_database_url": f"sqlite:///{baseline_db}",
        "maintenance_enabled": False,
        "summary_reconcile_enabled": False,
    }
    overrides.update(suite.configuration)
    return Settings(**{**base.model_dump(), **overrides})


def _verify_starting_condition(
    scenario: BehavioralScenario,
    engine: Engine,
) -> None:
    with Session(engine) as db:
        for reference in scenario.starting_condition.references:
            if reference.kind == "memory":
                row = db.get(MemoryRecord, reference.id)
            elif reference.kind == "fact":
                row = db.get(MemoryFact, reference.id)
            elif reference.kind == "session":
                row = db.get(ChatSession, reference.id)
            else:
                continue
            expected_exists = bool(reference.expected.get("exists", True))
            if (row is not None) != expected_exists:
                raise RuntimeError(
                    f"{scenario.id} starting reference {reference.id} existence mismatch"
                )
            if row is not None:
                for field, expected in reference.expected.items():
                    if field == "exists":
                        continue
                    if getattr(row, field, None) != expected:
                        raise RuntimeError(
                            f"{scenario.id} reference {reference.id} field {field} changed"
                        )


def _resolve_scenario_session(
    *,
    client: TestClient,
    scenario: BehavioralScenario,
    scenario_sessions: dict[str, str],
) -> str:
    arrangement = scenario.starting_condition.session_arrangement
    prerequisites = scenario.starting_condition.prerequisite_scenario_ids
    if arrangement in {"same_session", "continued_session"}:
        if not prerequisites:
            raise RuntimeError(f"{scenario.id} needs a prerequisite session")
        return scenario_sessions[prerequisites[-1]]
    response = client.post(
        "/api/chat/sessions",
        json=_evaluation_session_payload(),
    )
    response.raise_for_status()
    return str(response.json()["id"])


def _evaluation_session_payload() -> dict[str, str]:
    """Keep evaluator identity out of Scarlet's model-facing session context."""
    return {"title": "Conversazione con Scarlet"}


def _stream_turn(
    client: TestClient, session_id: str, message: str
) -> list[dict[str, Any]]:
    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/turn/stream",
        json={"message": message},
    ) as response:
        response.raise_for_status()
        return [json.loads(line) for line in response.iter_lines() if line]


def _final_turn(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("type") == "turn_complete" and isinstance(event.get("data"), dict):
            return event["data"]
    return {}


def _first_turn_id(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        data = event.get("data")
        if isinstance(data, dict) and isinstance(data.get("turn_id"), str):
            return data["turn_id"]
    return None


def _answer_text(events: list[dict[str, Any]], complete: dict[str, Any]) -> str:
    assistant = complete.get("assistant_message")
    if isinstance(assistant, dict) and isinstance(assistant.get("content"), str):
        return assistant["content"]
    return "".join(
        str(event.get("data", {}).get("text", ""))
        for event in events
        if event.get("type") == "text_delta" and isinstance(event.get("data"), dict)
    )


def _pending_layer(note: str) -> EvaluationLayerResult:
    return EvaluationLayerResult(
        status="inconclusive",
        evidence=[],
        notes=note,
        evaluator="pending",
    )


def _write_pending_summary(
    output_dir: Path,
    suite: BehavioralSuite,
    records: list[BehavioralRunRecord],
) -> None:
    technical_passes = sum(
        record.technical_execution.status == "pass" for record in records
    )
    lines = [
        f"# Behavioral Suite Run: {suite.title}",
        "",
        f"- Records: `{len(records)}`",
        f"- Objective technical passes: `{technical_passes}/{len(records)}`",
        "- Qualitative review: `pending`",
        "",
        "Natural-language quality is intentionally not scored by string matching. "
        "Review each evidence file against the scenario rubric, then apply a "
        "complete behavioral-judgment-v1 file.",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record.run_id}",
                "",
                f"- Technical: `{record.technical_execution.status}`",
                f"- Session: `{record.session_ids[0]}`",
                f"- Turn: `{record.turn_ids[0]}`",
                f"- State changes: `{', '.join(record.observed_state_changes) or 'none'}`",
                "",
            ]
        )
    (output_dir / "summary.pending.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def _write_reviewed_summary(
    run_dir: Path, records: list[BehavioralRunRecord]
) -> None:
    accepted = sum(record.accepted for record in records)
    lines = [
        "# Reviewed Behavioral Suite",
        "",
        f"- Fully accepted records: `{accepted}/{len(records)}`",
        "- Aggregate counts are orientation only; each rationale remains authoritative.",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"## {record.run_id}",
                "",
                f"- Technical execution: `{record.technical_execution.status}`",
                f"- Cognitive choice: `{record.cognitive_choice.status}`",
                f"- Answer outcome: `{record.answer_outcome.status}`",
                f"- Longitudinal effect: `{record.longitudinal_effect.status}`",
                f"- Accepted: `{record.accepted}`",
                "",
                f"Cognitive rationale: {record.cognitive_choice.notes}",
                "",
                f"Answer rationale: {record.answer_outcome.notes}",
                "",
                f"Longitudinal rationale: {record.longitudinal_effect.notes}",
                "",
            ]
        )
    (run_dir / "summary.reviewed.md").write_text("\n".join(lines), encoding="utf-8")


def _scenario_digest(scenario: BehavioralScenario) -> str:
    encoded = json.dumps(
        scenario.model_dump(mode="json"),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _provider_max_tokens(settings: Settings) -> int:
    return (
        settings.minimax_max_tokens
        if settings.llm_provider.casefold() == "minimax"
        else settings.qwen_max_tokens
    )


def _record_key(record: BehavioralRunRecord) -> str:
    return f"{record.group_id}:{record.repetition}:{record.scenario_id}"


def _write_records(path: Path, records: list[BehavioralRunRecord]) -> None:
    _write_json(path, [record.model_dump(mode="json") for record in records])


def _load_records(path: Path) -> list[BehavioralRunRecord]:
    return TypeAdapter(list[BehavioralRunRecord]).validate_json(
        path.read_text(encoding="utf-8")
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _resolve(root: Path, path: Path | str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _git_commit(backend_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=backend_root,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--backend-root", type=Path, default=Path.cwd())

    run = subparsers.add_parser("run")
    run.add_argument("--backend-root", type=Path, default=Path.cwd())
    run.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    run.add_argument("--run-db-root", type=Path, default=DEFAULT_RUN_DB_ROOT)
    run.add_argument("--group", action="append", default=[])

    review = subparsers.add_parser("apply-judgments")
    review.add_argument("run_dir", type=Path)
    review.add_argument("judgments", type=Path)

    compare = subparsers.add_parser("compare")
    compare.add_argument("before_dir", type=Path)
    compare.add_argument("after_dir", type=Path)
    compare.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.command == "apply-judgments":
        destination = apply_judgments(
            run_dir=args.run_dir,
            judgment_path=args.judgments,
        )
        print(destination)
        return 0
    if args.command == "compare":
        comparison = compare_reviewed_runs(
            before_dir=args.before_dir,
            after_dir=args.after_dir,
        )
        if args.output:
            _write_json(args.output, comparison)
        print(json.dumps(comparison, ensure_ascii=True, indent=2))
        return 1 if comparison["objective_regressions"] else 0

    backend_root = args.backend_root.resolve()
    catalog_path = _resolve(backend_root, args.catalog)
    suite = load_behavioral_suite(catalog_path)
    baseline = _resolve(backend_root, suite.baseline_database)
    assert_frozen_baseline(baseline)
    if args.command == "validate":
        print(
            json.dumps(
                {
                    "suite": suite.id,
                    "groups": len(suite.groups),
                    "scenarios": len(suite.scenarios),
                    "database_fingerprint": sha256_file(baseline),
                },
                indent=2,
            )
        )
        return 0

    output_dir = run_behavioral_suite(
        suite=suite,
        catalog_path=catalog_path,
        backend_root=backend_root,
        runs_dir=args.runs_dir,
        run_db_root=args.run_db_root,
        selected_group_ids=set(args.group) or None,
    )
    print(f"Behavioral suite evidence saved to {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

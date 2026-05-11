from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_RUNS_DIR = Path("app/evals/runs")


@dataclass(frozen=True)
class Expectation:
    kind: str
    value: str
    label: str | None = None


@dataclass(frozen=True)
class ScenarioTurn:
    id: str
    message: str
    expectations: list[Expectation] = field(default_factory=list)
    notes: str | None = None


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    description: str
    max_tokens: int | None
    turns: list[ScenarioTurn]
    review_questions: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    label: str
    passed: bool
    detail: str


@dataclass
class TurnRecord:
    index: int
    turn_id: str | None
    prompt: str
    answer: str
    events: list[dict[str, Any]]
    trace_ids: list[str]
    traces: list[dict[str, Any]]
    latency_ms: int | None
    usage: dict[str, Any]
    checks: list[CheckResult]
    human_note: str | None = None


@dataclass
class RunResult:
    run_id: str
    mode: str
    session_id: str
    output_dir: Path
    turns: list[TurnRecord]

    @property
    def passed(self) -> bool:
        checks = [check for turn in self.turns for check in turn.checks]
        return bool(checks) and all(check.passed for check in checks)


class EvalHTTPClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(base_url=self.base_url, timeout=None)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def create_session(self, *, title: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._client.post(
            "/api/chat/sessions",
            json={"title": title, "metadata": metadata or {}},
        )
        response.raise_for_status()
        return response.json()

    def stream_turn(
        self,
        *,
        session_id: str,
        message: str,
        max_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"message": message}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        events: list[dict[str, Any]] = []
        with self._client.stream(
            "POST",
            f"/api/chat/sessions/{session_id}/turn/stream",
            json=payload,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                events.append(json.loads(line))
        return events

    def fetch_traces(self, turn_id: str) -> list[dict[str, Any]]:
        response = self._client.get(f"/api/debug/traces/{turn_id}")
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()


def load_scenario(path: Path) -> Scenario:
    raw = json.loads(path.read_text(encoding="utf-8"))
    turns = [
        ScenarioTurn(
            id=str(turn["id"]),
            message=str(turn["message"]),
            expectations=[
                Expectation(
                    kind=str(expectation["kind"]),
                    value=str(expectation["value"]),
                    label=expectation.get("label"),
                )
                for expectation in turn.get("expectations", [])
            ],
            notes=turn.get("notes"),
        )
        for turn in raw.get("turns", [])
    ]
    if not turns:
        raise ValueError(f"Scenario has no turns: {path}")

    return Scenario(
        id=str(raw["id"]),
        title=str(raw["title"]),
        description=str(raw.get("description", "")),
        max_tokens=raw.get("max_tokens"),
        turns=turns,
        review_questions=[str(question) for question in raw.get("review_questions", [])],
    )


def run_scripted_scenario(
    *,
    client: EvalHTTPClient,
    scenario: Scenario,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    run_id: str | None = None,
) -> RunResult:
    run_id = run_id or _new_run_id(scenario.id)
    output_dir = runs_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    session = client.create_session(
        title=f"Eval scripted: {scenario.title}",
        metadata={"eval_mode": "scripted", "scenario_id": scenario.id, "run_id": run_id},
    )

    turns: list[TurnRecord] = []
    for index, scenario_turn in enumerate(scenario.turns, start=1):
        events = client.stream_turn(
            session_id=session["id"],
            message=scenario_turn.message,
            max_tokens=scenario.max_tokens,
        )
        record = _build_turn_record(
            client=client,
            index=index,
            prompt=scenario_turn.message,
            events=events,
            expectations=scenario_turn.expectations,
            human_note=scenario_turn.notes,
        )
        turns.append(record)
        _append_jsonl(output_dir / "transcript.jsonl", _turn_record_json(record))

    result = RunResult(
        run_id=run_id,
        mode="scripted",
        session_id=session["id"],
        output_dir=output_dir,
        turns=turns,
    )
    _write_run_files(output_dir, result, scenario=scenario)
    return result


def run_interactive(
    *,
    client: EvalHTTPClient,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    title: str = "Adaptive interactive eval",
    max_tokens: int | None = None,
    input_stream: Any = sys.stdin,
    output_stream: Any = sys.stdout,
) -> RunResult:
    run_id = _new_run_id("interactive")
    output_dir = runs_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    session = client.create_session(
        title=f"Eval interactive: {title}",
        metadata={"eval_mode": "interactive", "run_id": run_id},
    )

    print(f"Interactive eval run: {run_id}", file=output_stream)
    print("Type /quit to finish. After each answer, add a human note or press Enter.", file=output_stream)

    turns: list[TurnRecord] = []
    index = 1
    while True:
        prompt = _read_line("prompt> ", file=output_stream, stream=input_stream)
        if prompt is None:
            break
        prompt = prompt.strip()
        if not prompt:
            continue
        if prompt.lower() in {"/q", "/quit", "/exit"}:
            break

        events = client.stream_turn(
            session_id=session["id"],
            message=prompt,
            max_tokens=max_tokens,
        )
        record = _build_turn_record(
            client=client,
            index=index,
            prompt=prompt,
            events=events,
            expectations=[],
        )
        _print_turn(record, output_stream)
        note = _read_line("note> ", file=output_stream, stream=input_stream)
        if note:
            record.human_note = note.strip() or None
        turns.append(record)
        _append_jsonl(output_dir / "transcript.jsonl", _turn_record_json(record))
        _write_run_files(output_dir, RunResult(run_id, "interactive", session["id"], output_dir, turns))
        index += 1

    result = RunResult(
        run_id=run_id,
        mode="interactive",
        session_id=session["id"],
        output_dir=output_dir,
        turns=turns,
    )
    _write_run_files(output_dir, result)
    return result


def _build_turn_record(
    *,
    client: EvalHTTPClient,
    index: int,
    prompt: str,
    events: list[dict[str, Any]],
    expectations: list[Expectation],
    human_note: str | None = None,
) -> TurnRecord:
    complete = _final_turn(events)
    turn_id = complete.get("turn_id") if complete else _first_turn_id(events)
    traces = client.fetch_traces(str(turn_id)) if turn_id else []
    answer = _answer_text(events, complete)
    checks = [evaluate_expectation(expectation, answer=answer, events=events, traces=traces) for expectation in expectations]
    return TurnRecord(
        index=index,
        turn_id=str(turn_id) if turn_id else None,
        prompt=prompt,
        answer=answer,
        events=events,
        trace_ids=list(complete.get("trace_ids", [])) if complete else [],
        traces=traces,
        latency_ms=complete.get("latency_ms") if complete else None,
        usage=dict(complete.get("usage", {})) if complete else {},
        checks=checks,
        human_note=human_note,
    )


def evaluate_expectation(
    expectation: Expectation,
    *,
    answer: str,
    events: list[dict[str, Any]],
    traces: list[dict[str, Any]],
) -> CheckResult:
    label = expectation.label or f"{expectation.kind}: {expectation.value}"
    value = expectation.value
    trace_kinds = [str(trace.get("kind")) for trace in traces]

    if expectation.kind == "answer_contains":
        passed = value.lower() in answer.lower()
        return CheckResult(label, passed, "answer contains value" if passed else "answer did not contain value")

    if expectation.kind == "answer_not_contains":
        passed = value.lower() not in answer.lower()
        return CheckResult(label, passed, "answer omitted value" if passed else "answer contained forbidden value")

    if expectation.kind == "trace_kind":
        passed = value in trace_kinds
        return CheckResult(label, passed, f"trace kinds: {', '.join(trace_kinds)}")

    if expectation.kind == "event_type":
        event_types = [str(event.get("type")) for event in events]
        passed = value in event_types
        return CheckResult(label, passed, f"event types: {', '.join(event_types)}")

    if expectation.kind == "tool_call_path":
        paths = _tool_call_paths(traces)
        passed = value in paths
        return CheckResult(label, passed, f"tool paths: {', '.join(paths) or 'none'}")

    return CheckResult(label, False, f"unknown expectation kind: {expectation.kind}")


def _tool_call_paths(traces: Iterable[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for trace in traces:
        payload = trace.get("payload", {})
        if not isinstance(payload, dict):
            continue
        arguments = payload.get("arguments", {})
        if isinstance(arguments, dict) and isinstance(arguments.get("path"), str):
            paths.append(arguments["path"])
    return paths


def _final_turn(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("type") == "turn_complete":
            data = event.get("data", {})
            return data if isinstance(data, dict) else {}
    return {}


def _first_turn_id(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        data = event.get("data", {})
        if isinstance(data, dict) and isinstance(data.get("turn_id"), str):
            return data["turn_id"]
    return None


def _answer_text(events: list[dict[str, Any]], complete: dict[str, Any]) -> str:
    assistant_message = complete.get("assistant_message")
    if isinstance(assistant_message, dict) and isinstance(assistant_message.get("content"), str):
        return assistant_message["content"]
    return "".join(
        str(event.get("data", {}).get("text", ""))
        for event in events
        if event.get("type") == "text_delta" and isinstance(event.get("data"), dict)
    )


def _operation_summary(events: list[dict[str, Any]]) -> list[str]:
    summary: list[str] = []
    for event in events:
        data = event.get("data", {})
        if not isinstance(data, dict):
            data = {}
        label = str(event.get("type"))
        if "seq" in data:
            label = f"{data['seq']}. {label}"
        if "model_step" in data:
            label = f"{label} model={data['model_step']}"
        if event.get("type") in {"tool_call", "tool_result", "tool_use_start"}:
            label = f"{label} tool={data.get('tool_name', 'mind_api')}"
        summary.append(label)
    return summary


def _print_turn(record: TurnRecord, output_stream: Any) -> None:
    print("", file=output_stream)
    print(f"turn {record.index}: {record.turn_id}", file=output_stream)
    print("operations:", file=output_stream)
    for operation in _operation_summary(record.events):
        print(f"- {operation}", file=output_stream)
    print("answer:", file=output_stream)
    print(record.answer, file=output_stream)
    print("", file=output_stream)


def _write_run_files(output_dir: Path, result: RunResult, scenario: Scenario | None = None) -> None:
    (output_dir / "run.json").write_text(
        json.dumps(
            {
                "run_id": result.run_id,
                "mode": result.mode,
                "session_id": result.session_id,
                "passed": result.passed if result.mode == "scripted" else None,
                "turn_count": len(result.turns),
                "scenario": _scenario_json(scenario) if scenario else None,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(_summary_markdown(result, scenario), encoding="utf-8")


def _summary_markdown(result: RunResult, scenario: Scenario | None = None) -> str:
    lines = [
        f"# Eval Run {result.run_id}",
        "",
        f"- Mode: `{result.mode}`",
        f"- Session: `{result.session_id}`",
        f"- Turns: `{len(result.turns)}`",
    ]
    if scenario is not None:
        lines.extend(
            [
                f"- Scenario: `{scenario.id}`",
                f"- Result: `{'passed' if result.passed else 'failed'}`",
                "",
                scenario.description,
            ]
        )
    lines.append("")

    for turn in result.turns:
        lines.extend(
            [
                f"## Turn {turn.index}",
                "",
                f"- Turn ID: `{turn.turn_id}`",
                f"- Latency: `{turn.latency_ms}` ms",
                f"- Trace IDs: {', '.join(f'`{trace_id}`' for trace_id in turn.trace_ids) or '`none`'}",
                "",
                "Prompt:",
                "",
                "```txt",
                turn.prompt,
                "```",
                "",
                "Answer:",
                "",
                "```txt",
                turn.answer,
                "```",
                "",
                "Operations:",
                "",
            ]
        )
        lines.extend(f"- {operation}" for operation in _operation_summary(turn.events))
        if turn.checks:
            lines.extend(["", "Checks:", ""])
            for check in turn.checks:
                mark = "PASS" if check.passed else "FAIL"
                lines.append(f"- `{mark}` {check.label}: {check.detail}")
        if turn.human_note:
            lines.extend(["", "Human note:", "", turn.human_note])
        lines.append("")
    return "\n".join(lines)


def _scenario_json(scenario: Scenario | None) -> dict[str, Any] | None:
    if scenario is None:
        return None
    return {
        "id": scenario.id,
        "title": scenario.title,
        "description": scenario.description,
        "max_tokens": scenario.max_tokens,
        "review_questions": scenario.review_questions,
    }


def _turn_record_json(record: TurnRecord) -> dict[str, Any]:
    return {
        "index": record.index,
        "turn_id": record.turn_id,
        "prompt": record.prompt,
        "answer": record.answer,
        "events": record.events,
        "operation_summary": _operation_summary(record.events),
        "trace_ids": record.trace_ids,
        "trace_kinds": [trace.get("kind") for trace in record.traces],
        "traces": record.traces,
        "latency_ms": record.latency_ms,
        "usage": record.usage,
        "checks": [check.__dict__ for check in record.checks],
        "human_note": record.human_note,
    }


def _append_jsonl(path: Path, item: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=True) + "\n")


def _new_run_id(prefix: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_prefix = "".join(character if character.isalnum() or character in {"-", "_"} else "_" for character in prefix)
    return f"{timestamp}_{safe_prefix}"


def _read_line(prompt: str, *, file: Any, stream: Any) -> str | None:
    print(prompt, end="", file=file, flush=True)
    line = stream.readline()
    if line == "":
        return None
    return line.rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run traceable Scarlet evaluation sessions.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    subparsers = parser.add_subparsers(dest="command", required=True)

    scripted = subparsers.add_parser("scripted", help="Run a JSON scenario without human prompts.")
    scripted.add_argument("scenario", type=Path)

    interactive = subparsers.add_parser("interactive", help="Run an adaptive human-in-the-loop eval.")
    interactive.add_argument("--title", default="Adaptive interactive eval")
    interactive.add_argument("--max-tokens", type=int, default=None)

    args = parser.parse_args(argv)
    client = EvalHTTPClient(base_url=args.base_url)
    try:
        if args.command == "scripted":
            scenario = load_scenario(args.scenario)
            result = run_scripted_scenario(client=client, scenario=scenario, runs_dir=args.runs_dir)
        else:
            result = run_interactive(
                client=client,
                runs_dir=args.runs_dir,
                title=args.title,
                max_tokens=args.max_tokens,
            )
    finally:
        client.close()

    print(f"Run saved to {result.output_dir}")
    if result.mode == "scripted":
        print(f"Result: {'passed' if result.passed else 'failed'}")
        return 0 if result.passed else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

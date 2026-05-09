import json

import httpx

from app.evals.runner import EvalHTTPClient, load_scenario, run_scripted_scenario


def test_scripted_eval_runner_records_transcript_and_checks(tmp_path) -> None:
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "schema_probe",
                "title": "Schema Probe",
                "description": "test scenario",
                "max_tokens": 4096,
                "turns": [
                    {
                        "id": "inspect",
                        "message": "inspect schema",
                        "expectations": [
                            {"kind": "event_type", "value": "tool_call"},
                            {"kind": "trace_kind", "value": "mind.tool_call"},
                            {"kind": "tool_call_path", "value": "/mind/schema"},
                            {"kind": "answer_contains", "value": "GET /mind/schema"},
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    scenario = load_scenario(scenario_path)
    client = EvalHTTPClient(
        base_url="http://testserver",
        client=httpx.Client(
            transport=httpx.MockTransport(_mock_eval_api),
            base_url="http://testserver",
            timeout=None,
        ),
    )

    result = run_scripted_scenario(
        client=client,
        scenario=scenario,
        runs_dir=tmp_path / "runs",
        run_id="run_schema_probe",
    )

    assert result.passed is True
    assert result.session_id == "ses_eval"
    assert result.turns[0].turn_id == "turn_eval"
    assert result.turns[0].answer == "GET /mind/schema is implemented."
    assert [check.passed for check in result.turns[0].checks] == [True, True, True, True]

    transcript = result.output_dir / "transcript.jsonl"
    summary = result.output_dir / "summary.md"
    run_json = result.output_dir / "run.json"
    assert transcript.exists()
    assert summary.exists()
    assert run_json.exists()
    assert "tool_call" in transcript.read_text(encoding="utf-8")
    assert "Result: `passed`" in summary.read_text(encoding="utf-8")
    assert json.loads(run_json.read_text(encoding="utf-8"))["passed"] is True


def _mock_eval_api(request: httpx.Request) -> httpx.Response:
    if request.method == "POST" and request.url.path == "/api/chat/sessions":
        return httpx.Response(
            200,
            json={
                "id": "ses_eval",
                "title": "Eval scripted: Schema Probe",
                "created_at": "2026-05-09T00:00:00Z",
                "updated_at": "2026-05-09T00:00:00Z",
                "metadata": {},
            },
        )

    if request.method == "POST" and request.url.path == "/api/chat/sessions/ses_eval/turn/stream":
        events = [
            {
                "type": "turn_started",
                "data": {
                    "seq": 1,
                    "turn_id": "turn_eval",
                    "session_id": "ses_eval",
                    "user_message": {
                        "id": "msg_user",
                        "session_id": "ses_eval",
                        "turn_id": "turn_eval",
                        "role": "user",
                        "content": "inspect schema",
                        "created_at": "2026-05-09T00:00:00Z",
                        "metadata": {},
                    },
                    "trace_ids": ["trace_request"],
                },
            },
            {
                "type": "tool_call",
                "data": {
                    "seq": 2,
                    "turn_id": "turn_eval",
                    "model_step": 1,
                    "provider_tool_use_id": "toolu_eval",
                    "tool_name": "mind_api",
                    "arguments": {
                        "method": "GET",
                        "path": "/mind/schema",
                        "intent": "inspect",
                    },
                },
            },
            {
                "type": "text_delta",
                "data": {
                    "seq": 3,
                    "turn_id": "turn_eval",
                    "model_step": 2,
                    "text": "GET /mind/schema is implemented.",
                },
            },
            {
                "type": "turn_complete",
                "data": {
                    "seq": 4,
                    "turn_id": "turn_eval",
                    "status": "completed",
                    "trace_ids": ["trace_request", "trace_tool", "trace_response"],
                    "latency_ms": 10,
                    "usage": {"input_tokens": 1, "output_tokens": 2},
                    "session": {
                        "id": "ses_eval",
                        "title": "Eval scripted: Schema Probe",
                        "created_at": "2026-05-09T00:00:00Z",
                        "updated_at": "2026-05-09T00:00:00Z",
                        "metadata": {},
                    },
                    "user_message": {
                        "id": "msg_user",
                        "session_id": "ses_eval",
                        "turn_id": "turn_eval",
                        "role": "user",
                        "content": "inspect schema",
                        "created_at": "2026-05-09T00:00:00Z",
                        "metadata": {},
                    },
                    "assistant_message": {
                        "id": "msg_assistant",
                        "session_id": "ses_eval",
                        "turn_id": "turn_eval",
                        "role": "assistant",
                        "content": "GET /mind/schema is implemented.",
                        "created_at": "2026-05-09T00:00:00Z",
                        "metadata": {},
                    },
                    "model": "MiniMax-M2.7",
                },
            },
        ]
        content = "".join(json.dumps(event) + "\n" for event in events)
        return httpx.Response(
            200,
            content=content,
            headers={"content-type": "application/x-ndjson"},
        )

    if request.method == "GET" and request.url.path == "/api/debug/traces/turn_eval":
        return httpx.Response(
            200,
            json=[
                {
                    "id": "trace_request",
                    "session_id": "ses_eval",
                    "turn_id": "turn_eval",
                    "kind": "llm.request",
                    "payload": {},
                    "created_at": "2026-05-09T00:00:00Z",
                },
                {
                    "id": "trace_tool",
                    "session_id": "ses_eval",
                    "turn_id": "turn_eval",
                    "kind": "mind.tool_call",
                    "payload": {
                        "arguments": {
                            "method": "GET",
                            "path": "/mind/schema",
                            "intent": "inspect",
                        }
                    },
                    "created_at": "2026-05-09T00:00:00Z",
                },
            ],
        )

    return httpx.Response(404, json={"detail": "not found"})

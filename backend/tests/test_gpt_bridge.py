import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.storage import repositories


def _app(db_engine: Engine, **overrides) -> TestClient:
    settings = Settings(
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
        **overrides,
    )
    return TestClient(
        create_app(
            settings=settings,
            db_engine=db_engine,
            llm_provider_factory=lambda _settings: None,
        )
    )


def test_gpt_bridge_bootstrap_action_finalize_roundtrip(db_engine: Engine) -> None:
    client = _app(db_engine)

    bootstrap = client.post(
        "/gpt/bootstrap",
        json={
            "title": "GPT Bridge Test",
            "message": "Ciao Scarlet, oggi ho poco tempo ma mi andava di sentirti.",
        },
    )

    assert bootstrap.status_code == 200
    bootstrap_payload = bootstrap.json()
    assert bootstrap_payload["ok"] is True
    session_id = bootstrap_payload["session_id"]
    assert session_id == bootstrap_payload["session"]["id"]
    turn_id = bootstrap_payload["turn_id"]
    context = bootstrap_payload["context"]
    assert context["profile"] == "gpt-bootstrap-compact-v1"
    assert "model_context" not in context
    assert "system" not in context
    assert "base_system" not in context
    assert "runtime_payload" not in context
    assert context["runtime_context"]
    assert "memory_context" not in context
    assert "runtime_payload_summary" not in context
    assert context["tools"][0]["name"] == "mind_shell"
    assert context["mind_shell_action_endpoint"] == "POST /gpt/action"
    assert context["finalize_endpoint"] == "POST /gpt/finalize"
    assert "full_effective_system_prompt" in context["full_diagnostics"][
        "omitted_from_action_response"
    ]
    assert len(json.dumps(bootstrap_payload)) < 120_000
    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    model_context_trace = next(
        trace for trace in traces if trace["kind"] == "model.context"
    )
    serialized_model_context = json.dumps(
        model_context_trace["payload"]["document"],
        ensure_ascii=False,
        indent=2,
    )
    assert serialized_model_context in context["runtime_context"]
    accounting_trace = next(
        trace for trace in traces if trace["kind"] == "context.accounting.preflight"
    )
    assert accounting_trace["payload"]["measurement_boundary"][
        "is_total_model_input"
    ] is False
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    assert accounting_trace["id"] in context["full_diagnostics"][
        "available_in_trace_ids"
    ]
    assert request_trace["id"] in context["full_diagnostics"][
        "available_in_trace_ids"
    ]

    action = client.post(
        "/gpt/action",
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "command": "help",
            "intent": "Understand available cognitive commands.",
        },
    )

    assert action.status_code == 200
    action_payload = action.json()
    assert action_payload["ok"] is True
    assert action_payload["response"]["ok"] is True
    assert action_payload["response"]["result"]["operation"] == "mind_shell.help"
    assert action_payload["tool_call_id"].startswith("tool_")

    finalize = client.post(
        "/gpt/finalize",
        json={
            "session_id": session_id,
            "turn_id": turn_id,
            "answer": "Eccomi. Tengo il filo leggero e resto qui con te.",
        },
    )

    assert finalize.status_code == 200
    finalize_payload = finalize.json()
    assert finalize_payload["ok"] is True
    assert finalize_payload["status"] == "completed"
    assert finalize_payload["assistant_message"]["content"].startswith("Eccomi.")
    assert finalize_payload["final_answer_to_show"].startswith("Eccomi.")

    with Session(db_engine) as db:
        messages = repositories.list_messages(db, session_id=session_id)
        assert [message.role for message in messages] == ["user", "assistant"]
        traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
        assert [trace.kind for trace in traces].count("llm.request") == 1
        assert [trace.kind for trace in traces].count("mind.tool_call") == 1
        assert [trace.kind for trace in traces].count("llm.response") == 1

    next_bootstrap = client.post(
        "/gpt/bootstrap",
        json={
            "session_id": session_id,
            "message": "Riprendiamo da qui, senza ripartire da zero.",
        },
    )

    assert next_bootstrap.status_code == 200
    next_context = next_bootstrap.json()["context"]
    assert next_context["provider_history_source"] == "session.provider_history_json"
    provider_roles = [
        message["role"] for message in next_context["provider_messages_recent"]
    ]
    assert provider_roles == ["user", "assistant", "user"]


def test_gpt_bridge_requires_key_outside_local(db_engine: Engine) -> None:
    client = _app(
        db_engine,
        environment="production",
        gpt_bridge_api_key="secret-bridge-key",
    )

    rejected = client.post("/gpt/bootstrap", json={"message": "Ciao"})
    assert rejected.status_code == 401

    accepted = client.post(
        "/gpt/bootstrap",
        json={"message": "Ciao"},
        headers={"X-GPT-Bridge-Key": "secret-bridge-key"},
    )
    assert accepted.status_code == 200


def test_gpt_bridge_routes_are_exposed_in_openapi(db_engine: Engine) -> None:
    client = _app(db_engine)

    schema = client.get("/openapi.json").json()

    assert "/gpt/bootstrap" in schema["paths"]
    assert "/gpt/action" in schema["paths"]
    assert "/gpt/finalize" in schema["paths"]
    assert (
        schema["paths"]["/gpt/bootstrap"]["post"]["operationId"]
        == "bootstrapScarletBeforeEveryAnswer"
    )
    assert (
        schema["paths"]["/gpt/action"]["post"]["operationId"]
        == "runScarletMindAction"
    )
    assert (
        schema["paths"]["/gpt/finalize"]["post"]["operationId"]
        == "finalizeScarletBeforeAnswer"
    )
    assert (
        schema["paths"]["/gpt/finalize"]["post"]["summary"]
        == "Persist the external GPT final answer and complete the turn"
    )
    assert (
        "final_answer_to_show"
        in schema["components"]["schemas"]["GPTBridgeFinalizeResponse"][
            "properties"
        ]
    )
    bootstrap_response_schema = schema["components"]["schemas"][
        "GPTBridgeBootstrapResponse"
    ]
    assert "session_id" in bootstrap_response_schema["required"]
    assert "session_id" in bootstrap_response_schema["properties"]
    action_request_schema = schema["components"]["schemas"]["GPTBridgeActionRequest"]
    assert "intent" in action_request_schema["required"]


def test_gpt_bridge_mcp_tool_descriptors_include_required_lifecycle_phrases(
    db_engine: Engine,
) -> None:
    client = _app(db_engine)

    initialized = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
    )

    assert initialized.status_code == 200
    assert initialized.headers["mcp-session-id"].startswith("mcp_")
    assert initialized.json()["result"]["capabilities"]["tools"] == {
        "listChanged": False
    }

    tools = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": initialized.headers["mcp-session-id"]},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )

    assert tools.status_code == 200
    tool_by_name = {
        tool["name"]: tool for tool in tools.json()["result"]["tools"]
    }
    assert "start_scarlet_turn_required" in tool_by_name
    assert "finish_scarlet_turn_required" in tool_by_name
    assert (
        "Usa sempre a inizio di ogni turno"
        in tool_by_name["start_scarlet_turn_required"]["description"]
    )
    assert (
        "Usa sempre prima della tua risposta finale"
        in tool_by_name["finish_scarlet_turn_required"]["description"]
    )
    assert tool_by_name["scarlet_memory_command"]["inputSchema"]["required"] == [
        "command"
    ]
    assert tool_by_name["start_scarlet_turn_required"]["outputSchema"][
        "required"
    ] == ["ok", "summary"]
    assert tool_by_name["finish_scarlet_turn_required"]["outputSchema"][
        "required"
    ] == ["ok", "summary"]
    assert tool_by_name["scarlet_memory_command"]["outputSchema"]["required"] == [
        "ok",
        "summary",
    ]
    assert (
        tool_by_name["scarlet_help_command"]["annotations"]["readOnlyHint"] is True
    )
    assert (
        tool_by_name["scarlet_memory_command"]["annotations"]["readOnlyHint"] is False
    )


def test_gpt_bridge_mcp_start_command_finish_roundtrip(db_engine: Engine) -> None:
    client = _app(db_engine)

    initialized = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
    )
    mcp_session_id = initialized.headers["mcp-session-id"]

    start = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": mcp_session_id},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "start_scarlet_turn_required",
                "arguments": {
                    "title": "MCP Bridge Test",
                    "message": "Ciao Scarlet, sto provando il connector MCP.",
                },
            },
        },
    )

    assert start.status_code == 200
    start_result = start.json()["result"]
    assert start_result["isError"] is False
    start_content = start_result["structuredContent"]
    session_id = start_content["session"]["id"]
    turn_id = start_content["turn_id"]
    assert start_content["context"]["profile"] == "gpt-bootstrap-compact-v1"

    help_call = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": mcp_session_id},
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "scarlet_help_command",
                "arguments": {"command": "help", "intent": "Check shell help."},
            },
        },
    )

    assert help_call.status_code == 200
    help_content = help_call.json()["result"]["structuredContent"]
    assert help_content["ok"] is True
    assert help_content["response"]["result"]["operation"] == "mind_shell.help"

    finish = client.post(
        "/mcp",
        headers={"Mcp-Session-Id": mcp_session_id},
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "finish_scarlet_turn_required",
                "arguments": {
                    "answer": "Ci sono. Il connector MCP ha chiuso bene il turno."
                },
            },
        },
    )

    assert finish.status_code == 200
    finish_content = finish.json()["result"]["structuredContent"]
    assert finish_content["ok"] is True
    assert finish_content["status"] == "completed"
    assert finish_content["turn_id"] == turn_id

    with Session(db_engine) as db:
        messages = repositories.list_messages(db, session_id=session_id)
        assert [message.role for message in messages] == ["user", "assistant"]
        traces = repositories.list_traces_for_turn(db, turn_id=turn_id)
        assert [trace.kind for trace in traces].count("llm.request") == 1
        assert [trace.kind for trace in traces].count("mind.tool_call") == 1
        assert [trace.kind for trace in traces].count("llm.response") == 1


def test_gpt_bridge_mcp_accepts_private_preview_query_key(
    db_engine: Engine,
) -> None:
    client = _app(
        db_engine,
        environment="production",
        gpt_bridge_api_key="secret-bridge-key",
    )

    rejected = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert rejected.status_code == 401

    accepted = client.post(
        "/mcp?key=secret-bridge-key",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert accepted.status_code == 200
    assert accepted.json()["result"]["serverInfo"]["name"] == "scarlet-api-mind"


def test_gpt_bridge_gpt_builder_assets_are_valid() -> None:
    plugin_dir = Path(__file__).parents[1] / "app" / "plugins" / "gpt_bridge"
    prompt = (plugin_dir / "scarlet_gpt_system_prompt.md").read_text()
    mcp_prompt = (plugin_dir / "scarlet_mcp_system_prompt.md").read_text()
    action_schema = json.loads((plugin_dir / "openapi_gpt_action.json").read_text())

    assert len(prompt) <= 8000
    assert len(mcp_prompt) <= 8000
    assert "bootstrapScarletBeforeEveryAnswer" in prompt
    assert "finalizeScarletBeforeAnswer" in prompt
    assert "FIRST TOOL: call `start_scarlet_turn_required`" in mcp_prompt
    assert "FINAL TOOL: before showing any final answer" in mcp_prompt
    assert "finish_scarlet_turn_required" in mcp_prompt
    assert "you are not Scarlet for this turn yet" in prompt
    assert "final_answer_to_show" in prompt
    assert "Do not ask permission to bootstrap" in prompt
    assert "Use only these GPT Actions" in prompt
    assert "X-GPT-Bridge-Key" in json.dumps(action_schema)
    assert sorted(action_schema["paths"]) == [
        "/gpt/action",
        "/gpt/bootstrap",
        "/gpt/finalize",
    ]
    assert (
        action_schema["paths"]["/gpt/bootstrap"]["post"]["operationId"]
        == "bootstrapScarletBeforeEveryAnswer"
    )
    assert (
        action_schema["paths"]["/gpt/action"]["post"]["operationId"]
        == "runScarletMindAction"
    )
    assert (
        action_schema["paths"]["/gpt/finalize"]["post"]["operationId"]
        == "finalizeScarletBeforeAnswer"
    )
    bootstrap_schema = action_schema["components"]["schemas"]["BootstrapResponse"]
    assert "session_id" in bootstrap_schema["required"]
    assert "session_id" in bootstrap_schema["properties"]
    assert "action_policy" in bootstrap_schema["properties"]
    assert "required_actions" in bootstrap_schema["properties"]
    assert "recommended_actions" in bootstrap_schema["properties"]
    assert "intent" in action_schema["components"]["schemas"]["ActionRequest"][
        "required"
    ]
    finalize_props = action_schema["components"]["schemas"]["FinalizeResponse"][
        "properties"
    ]
    assert "final_answer_to_show" in finalize_props
    assert "final_answer_to_show" in action_schema["components"]["schemas"][
        "FinalizeResponse"
    ]["required"]

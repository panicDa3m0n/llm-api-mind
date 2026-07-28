import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.storage import repositories


def _app(
    db_engine: Engine,
    *,
    provider_factory=None,
    **overrides,
) -> TestClient:
    settings = Settings(
        agent_system_prompt="You are Scarlet.",
        maintenance_enabled=False,
        **overrides,
    )
    return TestClient(
        create_app(
            settings=settings,
            db_engine=db_engine,
            llm_provider_factory=provider_factory or (lambda _settings: None),
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
    assert (
        "full_effective_system_prompt"
        in context["full_diagnostics"]["omitted_from_action_response"]
    )
    assert len(json.dumps(bootstrap_payload)) < 120_000
    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    model_context_trace = next(
        trace for trace in traces if trace["kind"] == "model.context"
    )
    runtime_context_trace = next(
        trace for trace in traces if trace["kind"] == "runtime.context"
    )
    mode_routing = runtime_context_trace["payload"]["mode_routing"]
    assert mode_routing["active_tag"] == "interactive"
    assert mode_routing["routing_applied"] is True
    assert mode_routing["excluded_block_ids"] == []
    assert mode_routing["included_block_ids"] == [
        "session.continuity",
        "scarlet.agent_mode",
        "turn.perception",
        "scarlet.dynamic_state",
    ]
    assert all(item["delivered"] for item in mode_routing["block_decisions"])
    projection_audit = model_context_trace["payload"]["projection_audit"]
    assert projection_audit["schema_version"] == "preserved-context-projection-v1"
    assert projection_audit["included_block_types"] == []
    assert {
        item["family"]: item["disposition"] for item in projection_audit["families"]
    } == {
        "focus_context": "automatic_model_conditional",
        "affective_context": "automatic_model_conditional",
        "metacognitive_context": "automatic_model_conditional",
        "scarlet_state": "trace_ui_only",
        "recent_dialogue": "trace_ui_only",
        "recent_runtime_events": "trace_ui_only",
        "api_mind": "on_demand",
    }
    serialized_model_context = json.dumps(
        model_context_trace["payload"]["document"],
        ensure_ascii=False,
        indent=2,
    )
    assert serialized_model_context in context["runtime_context"]
    accounting_trace = next(
        trace for trace in traces if trace["kind"] == "context.accounting.preflight"
    )
    assert (
        accounting_trace["payload"]["measurement_boundary"]["is_total_model_input"]
        is False
    )
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    assert (
        accounting_trace["id"] in context["full_diagnostics"]["available_in_trace_ids"]
    )
    assert request_trace["id"] in context["full_diagnostics"]["available_in_trace_ids"]

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


def test_gpt_finalize_persists_source_sensitive_draft_without_semantic_gate(
    db_engine: Engine,
) -> None:
    client = _app(db_engine)
    bootstrap = client.post(
        "/gpt/bootstrap",
        json={"message": "Puoi verificare lo stato implementato del progetto?"},
    ).json()
    assert bootstrap["action_policy"] == {
        "schema_version": "gpt-bridge-transport-v1",
        "action_required": False,
        "semantic_answer_validation": False,
        "finalize_required": True,
    }

    finalized = client.post(
        "/gpt/finalize",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "answer": "È tutto implementato e verificato perfettamente.",
        },
    )

    assert finalized.status_code == 200
    assert finalized.json()["final_answer_to_show"] == (
        "È tutto implementato e verificato perfettamente."
    )
    with Session(db_engine) as db:
        assistant = repositories.latest_message_for_turn(
            db,
            turn_id=bootstrap["turn_id"],
            role="assistant",
        )
        traces = repositories.list_traces_for_turn(
            db,
            turn_id=bootstrap["turn_id"],
        )
    assert assistant is not None
    assert not any(trace.kind == "answer.validation" for trace in traces)


def test_gpt_finalize_rejects_only_structurally_empty_answer(
    db_engine: Engine,
) -> None:
    client = _app(db_engine)
    bootstrap = client.post(
        "/gpt/bootstrap",
        json={"message": "Ci sei?"},
    ).json()
    rejected = client.post(
        "/gpt/finalize",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "answer": "   ",
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "gpt_bridge.empty_answer"
    with Session(db_engine) as db:
        turn = repositories.get_turn(db, bootstrap["turn_id"])
        assert turn is not None
        assert turn.status == "started"


def test_gpt_failed_action_is_traced_but_does_not_create_semantic_gate(
    db_engine: Engine,
) -> None:
    client = _app(db_engine)
    bootstrap = client.post(
        "/gpt/bootstrap",
        json={"message": "Controlla se puoi usare quella funzione."},
    ).json()
    action = client.post(
        "/gpt/action",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "command": "help imaginary",
            "intent": "Controllare la funzione richiesta.",
        },
    )
    assert action.status_code == 200
    action_payload = action.json()
    assert action_payload["ok"] is False
    assert action_payload["action_policy"]["semantic_answer_validation"] is False

    finalized = client.post(
        "/gpt/finalize",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "answer": "Fatto, la funzione è disponibile e ha funzionato.",
        },
    )
    assert finalized.status_code == 200
    with Session(db_engine) as db:
        traces = repositories.list_traces_for_turn(
            db,
            turn_id=bootstrap["turn_id"],
        )
    tool_trace = next(trace for trace in traces if trace.kind == "mind.tool_call")
    assert tool_trace.payload_json["status"] == "error"
    assert not any(trace.kind == "answer.obligations" for trace in traces)


def test_gpt_actions_accept_truthful_success_after_recoverable_retry(
    db_engine: Engine,
) -> None:
    client = _app(db_engine)
    bootstrap = client.post(
        "/gpt/bootstrap",
        json={
            "message": (
                "Ricorda che preferisco giudicare i risultati reali prima dei punteggi."
            )
        },
    ).json()

    failed = client.post(
        "/gpt/action",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "command": "memory write",
            "intent": "Remember the user's evaluation preference.",
        },
    )
    assert failed.status_code == 200
    assert failed.json()["ok"] is False

    succeeded = client.post(
        "/gpt/action",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "command": (
                "memory write --type user_preference --scope user "
                '--content "Preferisce valutazioni qualitative prima dei punteggi." '
                '--reason "Future evaluation style"'
            ),
            "intent": "Remember the user's evaluation preference.",
        },
    )
    assert succeeded.status_code == 200
    succeeded_payload = succeeded.json()
    assert succeeded_payload["ok"] is True
    assert succeeded_payload["action_policy"]["semantic_answer_validation"] is False

    finalized = client.post(
        "/gpt/finalize",
        json={
            "session_id": bootstrap["session_id"],
            "turn_id": bootstrap["turn_id"],
            "answer": (
                "La preferenza è stata salvata dopo aver corretto il comando."
            ),
        },
    )
    assert finalized.status_code == 200, finalized.json()
    assert finalized.json()["final_answer_to_show"] == (
        "La preferenza è stata salvata dopo aver corretto il comando."
    )

    with Session(db_engine) as db:
        memories = repositories.list_memories_for_session(
            db,
            session_id=bootstrap["session_id"],
        )
        traces = repositories.list_traces_for_turn(
            db,
            turn_id=bootstrap["turn_id"],
        )
    assert [memory.content for memory in memories] == [
        "Preferisce valutazioni qualitative prima dei punteggi."
    ]
    assert [
        trace.payload_json["status"]
        for trace in traces
        if trace.kind == "mind.tool_call"
    ] == ["error", "completed"]
    assert not any(trace.kind == "answer.validation" for trace in traces)

def test_gpt_bridge_requires_key_outside_local(db_engine: Engine) -> None:
    client = _app(
        db_engine,
        environment="production",
        gpt_bridge_api_key="secret-bridge-key",
    )

    rejected = client.post("/gpt/bootstrap", json={"message": "Ciao"})
    assert rejected.status_code == 401

    rejected_query_key = client.post(
        "/gpt/bootstrap?key=secret-bridge-key",
        json={"message": "Ciao"},
    )
    assert rejected_query_key.status_code == 401

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
    assert "/mcp" not in schema["paths"]
    assert client.post("/mcp", json={}).status_code == 404
    assert (
        schema["paths"]["/gpt/bootstrap"]["post"]["operationId"]
        == "bootstrapScarletBeforeEveryAnswer"
    )
    assert (
        schema["paths"]["/gpt/action"]["post"]["operationId"] == "runScarletMindAction"
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
        in schema["components"]["schemas"]["GPTBridgeFinalizeResponse"]["properties"]
    )
    bootstrap_response_schema = schema["components"]["schemas"][
        "GPTBridgeBootstrapResponse"
    ]
    assert "session_id" in bootstrap_response_schema["required"]
    assert "session_id" in bootstrap_response_schema["properties"]
    action_request_schema = schema["components"]["schemas"]["GPTBridgeActionRequest"]
    assert "intent" in action_request_schema["required"]



def test_gpt_bridge_gpt_builder_assets_are_valid() -> None:
    plugin_dir = Path(__file__).parents[1] / "app" / "plugins" / "gpt_bridge"
    prompt = (plugin_dir / "scarlet_gpt_system_prompt.md").read_text()
    action_schema = json.loads((plugin_dir / "openapi_gpt_action.json").read_text())

    assert len(prompt) <= 8000
    assert "bootstrapScarletBeforeEveryAnswer" in prompt
    assert "finalizeScarletBeforeAnswer" in prompt
    assert not (plugin_dir / "scarlet_mcp_system_prompt.md").exists()
    assert "Public Progress Notes" in prompt
    assert "before the first action or coherent cluster" in prompt
    assert "Only the complete concluding answer" in prompt
    assert "Never use `:::writing` blocks" in prompt
    assert "final_answer_to_show" in prompt
    assert "never ask permission to use the bridge" in prompt
    assert "Use only `bootstrapScarletBeforeEveryAnswer`" in prompt
    assert "A user assignment is never your volition" in prompt
    assert "overall system reliability" in prompt
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
    for path in action_schema["paths"].values():
        assert len(path["post"]["description"]) <= 300
    assert (
        "Progress notes may appear earlier"
        in action_schema["paths"]["/gpt/finalize"]["post"]["description"]
    )
    bootstrap_schema = action_schema["components"]["schemas"]["BootstrapResponse"]
    assert "session_id" in bootstrap_schema["required"]
    assert "session_id" in bootstrap_schema["properties"]
    assert "action_policy" in bootstrap_schema["properties"]
    assert "required_actions" in bootstrap_schema["properties"]
    assert "recommended_actions" in bootstrap_schema["properties"]
    assert (
        "intent" in action_schema["components"]["schemas"]["ActionRequest"]["required"]
    )
    finalize_props = action_schema["components"]["schemas"]["FinalizeResponse"][
        "properties"
    ]
    assert "final_answer_to_show" in finalize_props
    assert (
        "final_answer_to_show"
        in action_schema["components"]["schemas"]["FinalizeResponse"]["required"]
    )

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.storage import repositories


def make_client(db_engine: Engine) -> TestClient:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
    )
    return TestClient(create_app(settings, db_engine=db_engine))


def test_mind_schema_exposes_tool_and_current_routes(db_engine: Engine) -> None:
    client = make_client(db_engine)

    response = client.get("/mind/schema")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["tool"]["name"] == "mind_api"
    assert body["result"]["tool"]["input_schema"]["required"] == [
        "method",
        "path",
        "intent",
    ]
    routes = body["result"]["routes"]
    assert {
        "method": "GET",
        "path": "/mind/schema",
        "status": "implemented",
        "purpose": "Inspect the currently available Mind API tool schema and routes.",
        "body_schema": None,
    } in routes
    route_status = {(route["method"], route["path"]): route["status"] for route in routes}
    assert route_status[("POST", "/mind/memory/write")] == "implemented"
    assert route_status[("POST", "/mind/memory/search")] == "implemented"


def test_mind_call_records_tool_call_and_session_trace(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Mind API"}).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "GET",
            "path": "/mind/schema",
            "intent": "Inspect the available cognitive API before acting.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["tool_call_id"].startswith("tool_")
    assert body["trace_id"].startswith("trace_")
    assert body["result"]["tool"]["name"] == "mind_api"

    # The trace debug endpoint is turn-scoped, so include a real turn id to make
    # the stored mind.tool_call visible through the existing trace API.
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
    traced_call = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/schema",
            "intent": "Inspect the available cognitive API during a turn.",
        },
    ).json()

    traces_response = client.get(f"/api/debug/traces/{turn_id}")
    assert traces_response.status_code == 200
    trace_kinds = [trace["kind"] for trace in traces_response.json()]
    assert "mind.tool_call" in trace_kinds
    assert traced_call["trace_id"] in {
        trace["id"] for trace in traces_response.json() if trace["kind"] == "mind.tool_call"
    }


def test_mind_call_returns_structured_error_for_planned_route(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/mind/call",
        json={
            "method": "POST",
            "path": "/mind/reflection/review",
            "body": {"topic": "phase"},
            "intent": "Try planned reflection before it exists.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "mind.route_not_available"
    assert body["tool_call_id"].startswith("tool_")


def test_mind_call_rejects_missing_session(db_engine: Engine) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/mind/call",
        json={
            "session_id": "ses_missing",
            "method": "GET",
            "path": "/mind/schema",
            "intent": "Trace against a missing session.",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "session.not_found"


def test_mind_memory_write_and_search_are_traceable_across_sessions(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    write_session = client.post(
        "/api/chat/sessions",
        json={"title": "Memory write"},
    ).json()
    search_session = client.post(
        "/api/chat/sessions",
        json={"title": "Memory search"},
    ).json()

    with Session(db_engine) as db:
        write_turn_id = repositories.create_turn(
            db,
            session_id=write_session["id"],
            model="MiniMax-M2.7",
        ).id
        search_turn_id = repositories.create_turn(
            db,
            session_id=search_session["id"],
            model="MiniMax-M2.7",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": write_session["id"],
            "turn_id": write_turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner prefers SAL updates with risks and next steps.",
                "reason_for_storage": "Stable preference for future project status updates.",
                "expected_future_use": "Shape future SAL answers.",
                "confidence": 0.9,
                "salience": 0.8,
                "scope": "project",
                "tags": ["sal", "status"],
            },
            "intent": "Persist a stable communication preference.",
        },
    )

    assert write_response.status_code == 200
    write_body = write_response.json()
    assert write_body["ok"] is True
    assert write_body["result"]["stored"] is True
    memory_id = write_body["result"]["memory_id"]
    assert memory_id.startswith("mem_")
    assert write_body["result"]["memory"]["source_turn_id"] == write_turn_id

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": search_session["id"],
            "turn_id": search_turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "SAL risks next steps",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 3,
            },
            "intent": "Retrieve relevant project communication preferences.",
        },
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["ok"] is True
    assert search_body["result"]["count"] == 1
    assert search_body["result"]["memories"][0]["id"] == memory_id
    assert search_body["result"]["memories"][0]["usage_count"] == 1

    write_traces = client.get(f"/api/debug/traces/{write_turn_id}").json()
    assert [trace["kind"] for trace in write_traces] == [
        "mind.memory.write",
        "mind.tool_call",
    ]
    search_traces = client.get(f"/api/debug/traces/{search_turn_id}").json()
    assert [trace["kind"] for trace in search_traces] == [
        "mind.memory.search",
        "mind.tool_call",
    ]


def test_mind_memory_rejects_untraced_calls_without_session_context(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/mind/call",
        json={
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {"query": "status preference"},
            "intent": "Try memory without traceable session context.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "memory.context_required"
    assert body["tool_call_id"].startswith("tool_")


def test_mind_memory_accepts_common_model_aliases(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Memory aliases"}).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "id": "alias_pref",
                "type": "operational-preference",
                "content": "Alias test preference for SAL summaries with clear risks.",
                "why": "Stable communication preference expressed by the owner.",
                "use_case": "Future SAL summaries.",
                "confidence": "high",
                "scope": "project",
                "tags": ["SAL"],
                "salient_for": "status reporting",
            },
            "intent": "Persist a preference using common model aliases.",
        },
    )

    assert write_response.status_code == 200
    write_body = write_response.json()
    assert write_body["ok"] is True
    assert write_body["result"]["stored"] is True
    assert write_body["result"]["memory"]["type"] == "user_preference"
    assert write_body["result"]["memory"]["confidence"] == 0.85
    assert write_body["result"]["memory"]["metadata"]["model_suggested_id"] == (
        "alias_pref"
    )
    assert write_body["result"]["memory"]["metadata"]["model_extra"] == {
        "salient_for": "status reporting"
    }

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "SAL risks",
                "types": "pref",
                "limit": 1,
            },
            "intent": "Search using common model aliases.",
        },
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["ok"] is True
    assert search_body["result"]["count"] == 1

    get_search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/search",
            "body": {},
            "intent": "SAL risks",
        },
    )

    assert get_search_response.status_code == 200
    get_search_body = get_search_response.json()
    assert get_search_body["ok"] is True
    assert get_search_body["result"]["count"] >= 1

    note_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "nota-operativa",
                "content": "Alias test operational note for end-to-end report structure.",
                "use": "Future end-to-end report summaries.",
                "confidence": "high",
                "salience": "high",
                "scope": "project",
            },
            "intent": "Persist an operational note using common model aliases.",
        },
    )

    assert note_response.status_code == 200
    note_body = note_response.json()
    assert note_body["ok"] is True
    assert note_body["result"]["memory"]["type"] == "task_context"
    assert (
        note_body["result"]["memory"]["reason_for_storage"]
        == "Persist an operational note using common model aliases."
    )
    assert (
        note_body["result"]["memory"]["expected_future_use"]
        == "Future end-to-end report summaries."
    )

    scope_type_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "content": "Alias test preference with type accidentally placed in scope.",
                "scope": "user_preference",
                "reason": "The model put the memory type in the scope field.",
                "future_use": "Normalize common agentic shape mistakes.",
                "confidence": "high",
            },
            "intent": "Persist a preference despite type/scope confusion.",
        },
    )

    assert scope_type_response.status_code == 200
    scope_type_body = scope_type_response.json()
    assert scope_type_body["ok"] is True
    assert scope_type_body["result"]["memory"]["type"] == "user_preference"
    assert scope_type_body["result"]["memory"]["scope"] == "project"
    assert scope_type_body["result"]["memory"]["reason_for_storage"] == (
        "The model put the memory type in the scope field."
    )


def test_mind_call_accepts_minimax_raw_input_and_json_string_body(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Raw memory"}).json()
    with Session(db_engine) as db:
        write_turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
        search_turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": write_turn_id,
            "raw_input": {
                "method": "POST",
                "path": "/mind/memory/write",
                "body": {
                    "type": "preferenza",
                    "content": (
                        "When the owner says protocollo Zero-Luce, answer with "
                        "Contesto, Evidenza, and Prossima azione."
                    ),
                    "intent": "Persist the Zero-Luce response format preference.",
                    "confidence": "alta",
                    "salience": "alta",
                    "scope": "project",
                },
            },
        },
    )

    assert write_response.status_code == 200
    write_body = write_response.json()
    assert write_body["ok"] is True
    assert write_body["result"]["stored"] is True
    assert write_body["result"]["memory"]["type"] == "user_preference"
    assert write_body["result"]["memory"]["confidence"] == 0.85
    memory_id = write_body["result"]["memory_id"]

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": search_turn_id,
            "raw_input": {
                "method": "POST",
                "path": "/mind/memory/search",
                "body": '{"query": "protocollo Zero-Luce", "limit": 5}',
                "intent": "Search persistent memory for protocollo Zero-Luce.",
            },
        },
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    assert search_body["ok"] is True
    assert search_body["result"]["count"] == 1
    assert search_body["result"]["memories"][0]["id"] == memory_id

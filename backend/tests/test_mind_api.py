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
            "path": "/mind/memory/search",
            "body": {"query": "phase"},
            "intent": "Try planned memory before it exists.",
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

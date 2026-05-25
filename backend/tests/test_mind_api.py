import json
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.main import create_app
from app.mind.schema import schema_metadata
from app.storage import repositories


class FakeMetacognitionProvider:
    prompts: list[str] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.prompts.append(prompt)
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=json.dumps(
                {
                    "review_summary": "Schema-dependent draft needs evidence.",
                    "risks": [
                        {
                            "risk": "API shape may be stale.",
                            "severity": "high",
                            "mitigation": "Inspect /mind/schema.",
                        }
                    ],
                    "claim_checks": [
                        {
                            "claim": "The endpoint is implemented.",
                            "support": "needs_evidence",
                            "confidence": 0.42,
                            "recommended_action": "Check schema first.",
                        }
                    ],
                    "missing_evidence": ["current Mind API schema"],
                    "recommended_internal_actions": [
                        {
                            "method": "GET",
                            "path": "/mind/schema",
                            "reason": "Confirm current route shape.",
                        },
                        {
                            "method": "GET",
                            "path": "/mind/metacognition/step",
                            "reason": "Deliberately wrong method from reviewer.",
                        }
                    ],
                    "should_continue": True,
                    "next_focus_question": "What does /mind/schema report?",
                    "public_summary": "Ho verificato che serve conferma schema.",
                }
            ),
            usage={"input_tokens": 10, "output_tokens": 20},
            provider_message_id="meta_msg_1",
            stop_reason="end_turn",
        )


class FakeRepairingMetacognitionProvider:
    prompts: list[str] = []
    call_count = 0

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.prompts.append(prompt)
        self.__class__.call_count += 1
        if self.__class__.call_count == 1:
            text = '{"review_summary": "Broken", "risks [}'
        else:
            text = json.dumps(
                {
                    "review_summary": "Repair completed.",
                    "risks": [],
                    "claim_checks": [],
                    "missing_evidence": [],
                    "recommended_internal_actions": [],
                    "should_continue": False,
                    "next_focus_question": None,
                    "public_summary": "Riparazione JSON completata.",
                }
            )
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            usage={"input_tokens": 1, "output_tokens": 1},
            provider_message_id=f"repair_msg_{self.__class__.call_count}",
            stop_reason="end_turn",
        )


class FakeSessionSummaryProvider:
    prompts: list[str] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.prompts.append(prompt)
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=json.dumps(
                {
                    "summary": (
                        "The owner defined episodic recall as session summaries "
                        "plus exact transcript retrieval."
                    ),
                    "topics": ["episodic recall", "session summaries"],
                    "decisions": [
                        "Keep semantic memories separate from episodic sessions."
                    ],
                    "open_questions": ["How often summaries should refresh."],
                    "notable_context": [
                        "Semantic memories should keep source_session_id provenance."
                    ],
                }
            ),
            usage={"input_tokens": 50, "output_tokens": 60},
            provider_message_id="session_summary_msg_1",
            stop_reason="end_turn",
        )


def make_client(db_engine: Engine, *, provider_factory=None) -> TestClient:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
    )
    return TestClient(
        create_app(
            settings,
            llm_provider_factory=provider_factory,
            db_engine=db_engine,
        )
    )


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
    assert body["result"]["schema_version"] == "2026-05-24.temporal-sparse-v1"
    assert body["result"]["schema_digest"].startswith("sha256:")
    assert body["result"]["schema_digest"] == schema_metadata()["schema_digest"]
    assert body["result"]["schema_policy"]["source_of_truth"] == "GET /mind/schema"
    routes = body["result"]["routes"]
    schema_route = next(
        route for route in routes if route["method"] == "GET" and route["path"] == "/mind/schema"
    )
    assert schema_route["status"] == "implemented"
    assert "purpose" in schema_route
    assert "body_schema" not in schema_route
    assert "examples" not in schema_route
    route_status = {(route["method"], route["path"]): route["status"] for route in routes}
    assert route_status[("POST", "/mind/memory/write")] == "implemented"
    assert route_status[("POST", "/mind/memory/search")] == "implemented"
    assert route_status[("GET", "/mind/memory/{memory_id}")] == "implemented"
    assert route_status[("GET", "/mind/memory/facts")] == "implemented"
    assert route_status[("POST", "/mind/memory/facts/backfill")] == "implemented"
    assert route_status[("GET", "/mind/memory/conflicts")] == "implemented"
    assert route_status[("POST", "/mind/memory/deprecate")] == "implemented"
    assert route_status[("POST", "/mind/memory/supersede")] == "implemented"
    assert route_status[("GET", "/mind/sessions")] == "implemented"
    assert route_status[("GET", "/mind/sessions/{session_id}")] == "implemented"
    assert (
        route_status[("POST", "/mind/sessions/{session_id}/summarize")]
        == "implemented"
    )
    summarize_route = next(
        route
        for route in routes
        if route["method"] == "POST"
        and route["path"] == "/mind/sessions/{session_id}/summarize"
    )
    assert "body_schema" not in summarize_route
    assert "max_messages" not in str(summarize_route)
    assert route_status[("POST", "/mind/metacognition/step")] == "implemented"
    assert ("POST", "/mind/events/emit") not in route_status
    assert ("POST", "/mind/validation/claims") not in route_status
    assert ("POST", "/mind/blackboard/write") not in route_status
    assert ("GET", "/mind/blackboard") not in route_status
    assert ("POST", "/mind/reflection/after-turn") not in route_status
    assert ("POST", "/mind/reflection/review") not in route_status


def test_mind_error_includes_endpoint_usage_guide(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Usage guide"}).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {"query": "cioccolato", "top_k": 999},
            "intent": "Search memory with an invalid limit to inspect recovery hints.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "memory.invalid_search"
    assert body["usage_guide"]["method"] == "POST"
    assert body["usage_guide"]["path"] == "/mind/memory/search"
    assert body["usage_guide"]["body_schema"]["properties"]["top_k"]["maximum"] == 20
    assert body["usage_guide"]["parameters"]["query"]["required"] is True
    assert body["usage_guide"]["parameters"]["query"]["description"]
    assert body["usage_guide"]["parameters"]["top_k"]["maximum"] == 20
    assert body["usage_guide"]["parameters"]["top_k"]["description"]
    assert body["usage_guide"]["parameters"]["time"]["properties"]["basis"]["enum"] == [
        "source_conversation",
        "recorded",
        "valid",
        None,
    ]
    assert body["usage_guide"]["examples"][0]["body"]["top_k"] == 5
    assert body["suggested_next_actions"][0].startswith("Use usage_guide")
    assert "Call GET /mind/schema" not in body["suggested_next_actions"]


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
    events_response = client.get(f"/api/debug/events?turn_id={turn_id}")
    assert events_response.status_code == 200
    event_types = [event["type"] for event in events_response.json()]
    assert event_types == [
        "mind.tool_call.started",
        "mind.tool_call.completed",
    ]
    completed_event = events_response.json()[1]
    assert completed_event["trace_id"] == traced_call["trace_id"]
    assert completed_event["tool_call_id"] == traced_call["tool_call_id"]
    assert completed_event["payload"]["operation"]["path"] == "/mind/schema"


def test_mind_call_returns_structured_error_for_planned_route(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/mind/call",
        json={
            "method": "POST",
            "path": "/mind/attention/context",
            "body": {"topic": "phase"},
            "intent": "Try planned attention before it exists.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "mind.route_not_available"
    assert body["result"]["schema"]["schema_digest"].startswith("sha256:")
    assert {
        "method": "POST",
        "path": "/mind/metacognition/step",
        "status": "implemented",
    } in body["result"]["implemented_routes"]
    assert body["tool_call_id"].startswith("tool_")


def test_unknown_mind_route_returns_route_suggestions(db_engine: Engine) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/mind/call",
        json={
            "method": "GET",
            "path": "/mind/memory",
            "intent": "Try a generic memory list route that is not implemented.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "mind.route_not_available"
    assert body["usage_guide"] is None
    suggested_routes = {
        (route["method"], route["path"])
        for route in body["result"]["route_suggestions"]
    }
    assert ("POST", "/mind/memory/search") in suggested_routes
    assert ("GET", "/mind/memory/{memory_id}") in suggested_routes


def test_mind_metacognition_step_is_traceable(db_engine: Engine) -> None:
    FakeMetacognitionProvider.prompts = []
    client = make_client(db_engine, provider_factory=FakeMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Metacognition"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Critique a draft answer before responding.",
            "body": {
                "mode": "critic",
                "objective": "Answer whether a Mind API endpoint is implemented.",
                "focus_question": "What evidence is missing before I answer?",
                "internal_prompt": "Review the draft and identify required API checks.",
                "known_evidence": [],
                "uncertainties": ["The route schema may have changed."],
                "draft_answer": "The endpoint is implemented.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["mode"] == "critic"
    assert body["result"]["review"]["should_continue"] is True
    assert "current Mind API schema" in body["result"]["review"]["missing_evidence"]
    assert body["result"]["review"]["recommended_internal_actions"][0]["path"] == "/mind/schema"
    assert (
        body["result"]["review"]["recommended_internal_actions"][0]["schema_status"]
        == "implemented"
    )
    wrong_method_action = body["result"]["review"]["recommended_internal_actions"][1]
    assert wrong_method_action["schema_status"] == "wrong_method"
    assert wrong_method_action["suggested_method"] == "POST"
    assert wrong_method_action["call_is_available"] is False
    assert body["result"]["model"] == "MiniMax-M2.7"
    assert FakeMetacognitionProvider.prompts
    assert "available_mind_api_routes" in FakeMetacognitionProvider.prompts[0]

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    assert "mind.metacognition.step" in [trace["kind"] for trace in traces]


def test_mind_metacognition_repairs_malformed_json_review(
    db_engine: Engine,
) -> None:
    FakeRepairingMetacognitionProvider.prompts = []
    FakeRepairingMetacognitionProvider.call_count = 0
    client = make_client(db_engine, provider_factory=FakeRepairingMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Metacognition repair"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Repair malformed reviewer JSON.",
            "body": {
                "objective": "Recover from a malformed internal review.",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["json_repair_applied"] is True
    assert body["result"]["review"]["review_summary"] == "Repair completed."
    assert FakeRepairingMetacognitionProvider.call_count == 2

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    metacognition_trace = next(
        trace for trace in traces if trace["kind"] == "mind.metacognition.step"
    )
    assert metacognition_trace["payload"]["json_repair_applied"] is True


def test_mind_metacognition_accepts_common_model_aliases(
    db_engine: Engine,
) -> None:
    FakeMetacognitionProvider.prompts = []
    client = make_client(db_engine, provider_factory=FakeMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Metacognition aliases"},
    ).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Accept common MiniMax-shaped metacognition aliases.",
            "body": {
                "mode": "orient",
                "prompt": "Verificare la forma corrente degli endpoint cognitivi disponibili.",
                "context": {"source": "runtime_context"},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert FakeMetacognitionProvider.prompts
    assert "Verificare la forma corrente" in FakeMetacognitionProvider.prompts[0]
    assert "runtime_context" in FakeMetacognitionProvider.prompts[0]


def test_mind_metacognition_accepts_goal_alias_for_objective(
    db_engine: Engine,
) -> None:
    FakeMetacognitionProvider.prompts = []
    client = make_client(db_engine, provider_factory=FakeMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Metacognition goal alias"},
    ).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Accept goal alias for objective.",
            "body": {
                "mode": "orient",
                "goal": "verificare la forma delle API cognitive disponibili",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "verificare la forma" in FakeMetacognitionProvider.prompts[0]


def test_parallel_cognitive_routes_are_not_available(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions", json={"title": "Single metacognition route"}
    ).json()

    for method, path in [
        ("POST", "/mind/validation/claims"),
        ("POST", "/mind/blackboard/write"),
        ("GET", "/mind/blackboard"),
        ("POST", "/mind/reflection/after-turn"),
        ("POST", "/mind/reflection/review"),
    ]:
        response = client.post(
            "/mind/call",
            json={
                "session_id": session["id"],
                "method": method,
                "path": path,
                "intent": "Ensure parallel cognitive routes are not exposed.",
                "body": {},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["error"]["code"] == "mind.route_not_available"


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


def test_mind_memory_search_supports_source_conversation_time_filter(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    old_session = client.post(
        "/api/chat/sessions",
        json={"title": "Old protocol"},
    ).json()
    new_session = client.post(
        "/api/chat/sessions",
        json={"title": "New protocol"},
    ).json()
    search_session = client.post(
        "/api/chat/sessions",
        json={"title": "Temporal memory search"},
    ).json()

    now = repositories.utc_now()
    old_time = now - timedelta(days=3)
    window_start = old_time - timedelta(hours=1)
    window_end = old_time + timedelta(hours=1)
    with Session(db_engine) as db:
        old_turn = repositories.create_turn(
            db,
            session_id=old_session["id"],
            model="MiniMax-M2.7",
        )
        new_turn = repositories.create_turn(
            db,
            session_id=new_session["id"],
            model="MiniMax-M2.7",
        )
        search_turn_id = repositories.create_turn(
            db,
            session_id=search_session["id"],
            model="MiniMax-M2.7",
        ).id
        old_message = repositories.add_message(
            db,
            session_id=old_session["id"],
            turn_id=old_turn.id,
            role="user",
            content="Abbiamo deciso il protocollo Nebbia-Rossa storico.",
        )
        new_message = repositories.add_message(
            db,
            session_id=new_session["id"],
            turn_id=new_turn.id,
            role="user",
            content="Abbiamo deciso il protocollo Nebbia-Rossa moderno.",
        )
        old_message.created_at = old_time
        new_message.created_at = now
        db.add(old_message)
        db.add(new_message)
        old_memory = repositories.add_memory(
            db,
            memory_type="decision",
            scope="project",
            content="Nebbia-Rossa storico uses archived report wording.",
            reason_for_storage="Historical protocol decision.",
            expected_future_use="Recover old Nebbia-Rossa decisions by source time.",
            confidence=0.9,
            salience=0.8,
            source_session_id=old_session["id"],
            source_turn_id=old_turn.id,
            tags=["nebbia-rossa"],
        )
        old_memory_id = old_memory.id
        new_memory = repositories.add_memory(
            db,
            memory_type="decision",
            scope="project",
            content="Nebbia-Rossa moderno uses compact report wording.",
            reason_for_storage="Current protocol decision.",
            expected_future_use="Recover current Nebbia-Rossa decisions.",
            confidence=0.9,
            salience=0.8,
            source_session_id=new_session["id"],
            source_turn_id=new_turn.id,
            tags=["nebbia-rossa"],
        )
        new_memory_id = new_memory.id

    response = client.post(
        "/mind/call",
        json={
            "session_id": search_session["id"],
            "turn_id": search_turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "intent": "Find Nebbia-Rossa memories from the old conversation window.",
            "body": {
                "query": "Nebbia-Rossa protocollo",
                "scope": "project",
                "top_k": 10,
                "time": {
                    "from": window_start.isoformat(),
                    "to": window_end.isoformat(),
                    "basis": "source_conversation",
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    returned_ids = [memory["id"] for memory in body["result"]["memories"]]
    assert old_memory_id in returned_ids
    assert new_memory_id not in returned_ids
    assert body["result"]["time"]["basis"] == "source_conversation"
    assert "fts5_sparse_v1" in body["result"]["retrieval_stages"]


def test_mind_sessions_summarize_list_and_read_preserve_episodic_provenance(
    db_engine: Engine,
) -> None:
    FakeSessionSummaryProvider.prompts = []
    client = make_client(db_engine, provider_factory=FakeSessionSummaryProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Episodic recall design"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn_id,
            role="user",
            content=(
                "Memoria episodica significa poter recuperare sessioni e transcript."
            ),
        )
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn_id,
            role="assistant",
            content=(
                "Tengo la memoria semantica separata dal richiamo episodico."
            ),
        )
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn_id,
            role="user",
            content="La summary deve usare tutta la cronologia user-agent.",
        )
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=turn_id,
            role="assistant",
            content="Non uso un limite max_messages per la compattazione.",
        )

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "intent": "Store the semantic decision with session provenance.",
            "body": {
                "type": "decision",
                "content": (
                    "Semantic memories stay separate from episodic session recall."
                ),
                "reason_for_storage": "Durable architecture decision.",
                "expected_future_use": "Guide memory system design.",
                "confidence": 0.9,
                "salience": 0.9,
                "scope": "project",
                "tags": ["memory", "episodic"],
            },
        },
    )
    assert write_response.status_code == 200
    memory_id = write_response.json()["result"]["memory_id"]

    summarize_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": f"/mind/sessions/{session['id']}/summarize",
            "intent": "Create the episodic summary for this conversation.",
            "body": {"force": True, "focus": "memory architecture"},
        },
    )

    assert summarize_response.status_code == 200
    summarize_body = summarize_response.json()
    assert summarize_body["ok"] is True
    assert summarize_body["result"]["summary"]["session_id"] == session["id"]
    assert "episodic recall" in summarize_body["result"]["summary"]["summary"]
    assert memory_id in summarize_body["result"]["summary"]["memory_ids"]
    assert FakeSessionSummaryProvider.prompts
    summary_prompt_payload = json.loads(
        FakeSessionSummaryProvider.prompts[0].split("\n\n", 1)[1]
    )
    assert summary_prompt_payload["message_scope"] == "full_user_assistant_history"
    assert summary_prompt_payload["messages_included"] == 4
    assert [
        message["role"] for message in summary_prompt_payload["transcript"]
    ] == ["user", "assistant", "user", "assistant"]

    list_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/sessions?limit=5",
            "intent": "List recent episodic sessions.",
        },
    )

    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["ok"] is True
    listed_session = next(
        item for item in list_body["result"]["sessions"] if item["id"] == session["id"]
    )
    assert listed_session["title"] == "Episodic recall design"
    assert listed_session["summary"]["status"] == "active"
    assert memory_id in listed_session["memory_ids"]

    read_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": f"/mind/sessions/{session['id']}",
            "intent": "Read the exact transcript behind a memory source.",
            "body": {"include_messages": True, "include_memories": True},
        },
    )

    assert read_response.status_code == 200
    read_body = read_response.json()
    assert read_body["ok"] is True
    assert [message["role"] for message in read_body["result"]["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert read_body["result"]["memories_written"][0]["id"] == memory_id
    assert (
        read_body["result"]["memories_written"][0]["source_session_id"]
        == session["id"]
    )

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    trace_kinds = [trace["kind"] for trace in traces]
    assert "mind.sessions.summarize" in trace_kinds
    assert "mind.tool_call" in trace_kinds


def test_mind_sessions_list_supports_time_filtered_sparse_search(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    old_session = client.post(
        "/api/chat/sessions",
        json={"title": "Nebbia old"},
    ).json()
    new_session = client.post(
        "/api/chat/sessions",
        json={"title": "Nebbia new"},
    ).json()

    now = repositories.utc_now()
    old_time = now - timedelta(days=4)
    window_start = old_time - timedelta(hours=1)
    window_end = old_time + timedelta(hours=1)
    with Session(db_engine) as db:
        old_turn = repositories.create_turn(
            db,
            session_id=old_session["id"],
            model="MiniMax-M2.7",
        )
        new_turn = repositories.create_turn(
            db,
            session_id=new_session["id"],
            model="MiniMax-M2.7",
        )
        new_turn_id = new_turn.id
        old_message = repositories.add_message(
            db,
            session_id=old_session["id"],
            turn_id=old_turn.id,
            role="user",
            content="Sessione storica sul protocollo Nebbia-Rossa e report lungo.",
        )
        new_message = repositories.add_message(
            db,
            session_id=new_session["id"],
            turn_id=new_turn.id,
            role="user",
            content="Sessione recente sul protocollo Nebbia-Rossa e report breve.",
        )
        old_message.created_at = old_time
        new_message.created_at = now
        db.add(old_message)
        db.add(new_message)
        db.commit()

    response = client.post(
        "/mind/call",
        json={
            "session_id": new_session["id"],
            "turn_id": new_turn_id,
            "method": "GET",
            "path": "/mind/sessions",
            "intent": "Find old Nebbia-Rossa episodic context.",
            "body": {
                "query": "Nebbia-Rossa report",
                "limit": 10,
                "time": {
                    "from": window_start.isoformat(),
                    "to": window_end.isoformat(),
                    "basis": "conversation",
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    returned_ids = [item["id"] for item in body["result"]["sessions"]]
    assert old_session["id"] in returned_ids
    assert new_session["id"] not in returned_ids
    assert body["result"]["time"]["basis"] == "conversation"
    assert "fts5_sparse_v1" in body["result"]["retrieval_stages"]


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


def test_mind_memory_atomic_facts_support_alias_query_and_conflicts(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Atomic facts"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id

    old_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "When the owner says Zero Light protocol, answer with "
                    "Context, Evidence, and Next action."
                ),
                "reason": "Stable old response format for Zero Light protocol.",
                "expected_future_use": "Use when the protocol is requested.",
                "confidence": 0.9,
                "salience": 0.8,
                "scope": "project",
                "tags": ["zero-light", "response-format"],
            },
            "intent": "Persist old Zero Light response format.",
        },
    )
    new_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "Protocollo Zero-Luce: rispondere con Contesto, Evidenza, "
                    "Rischio, Prossima azione."
                ),
                "reason": "Updated response format for protocollo Zero-Luce.",
                "expected_future_use": "Use when Zero-Luce is requested.",
                "confidence": 0.95,
                "salience": 0.9,
                "scope": "project",
                "tags": ["zero-luce", "formato-risposta"],
                "metadata": {
                    "blocchi": [
                        "Contesto",
                        "Evidenza",
                        "Rischio",
                        "Prossima azione",
                    ]
                },
            },
            "intent": "Persist updated Zero-Luce response format.",
        },
    )

    assert old_response.status_code == 200
    assert new_response.status_code == 200
    old_body = old_response.json()
    new_body = new_response.json()
    old_memory_id = old_body["result"]["memory_id"]
    new_memory_id = new_body["result"]["memory_id"]
    old_fact = old_body["result"]["memory"]["facts"][0]
    new_fact = new_body["result"]["memory"]["facts"][0]
    assert old_fact["entity"] == "protocollo-zero-luce"
    assert old_fact["predicate"] == "response_format"
    assert old_fact["value"]["blocks"] == [
        "Contesto",
        "Evidenza",
        "Prossima azione",
    ]
    assert new_fact["value"]["blocks"] == [
        "Contesto",
        "Evidenza",
        "Rischio",
        "Prossima azione",
    ]

    facts_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/facts",
            "body": {
                "query": "Zero Light protocol",
                "predicate": "formato-risposta",
            },
            "intent": "Inspect canonical facts by multilingual alias.",
        },
    )

    assert facts_response.status_code == 200
    facts_body = facts_response.json()
    assert facts_body["ok"] is True
    assert facts_body["result"]["count"] == 2
    assert {
        fact["memory_id"] for fact in facts_body["result"]["facts"]
    } == {old_memory_id, new_memory_id}

    conflicts_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/conflicts",
            "intent": "Find active atomic fact conflicts.",
        },
    )

    assert conflicts_response.status_code == 200
    conflicts_body = conflicts_response.json()
    assert conflicts_body["ok"] is True
    fact_conflict = conflicts_body["result"]["conflicts"][0]
    assert fact_conflict["basis"] == "atomic_fact"
    assert fact_conflict["entity"] == "protocollo-zero-luce"
    assert fact_conflict["predicate"] == "response_format"
    assert set(fact_conflict["memory_ids"]) == {old_memory_id, new_memory_id}

    supersede_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/supersede",
            "body": {
                "old_memory_id": old_memory_id,
                "new_memory_id": new_memory_id,
                "reason": "Four-block canonical fact supersedes three-block fact.",
            },
            "intent": "Resolve atomic fact conflict.",
        },
    )

    assert supersede_response.status_code == 200
    supersede_body = supersede_response.json()
    old_facts = supersede_body["result"]["old_memory"]["facts"]
    new_facts = supersede_body["result"]["new_memory"]["facts"]
    assert old_facts[0]["status"] == "deprecated"
    assert old_facts[0]["superseded_by_fact_id"] == new_facts[0]["id"]
    assert new_facts[0]["supersedes_fact_id"] == old_facts[0]["id"]

    resolved_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/conflicts",
            "intent": "Confirm fact conflict was resolved.",
        },
    )

    assert resolved_response.status_code == 200
    assert resolved_response.json()["result"]["count"] == 0


def test_mind_memory_facts_backfill_is_traceable(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Fact backfill"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
        memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=(
                "Protocollo Zero-Luce uses four blocks: Contesto, Evidenza, "
                "Rischio, Prossima azione."
            ),
            reason_for_storage="Existing memory before atomic facts.",
            expected_future_use="Use when Zero-Luce is requested.",
            confidence=0.95,
            salience=0.9,
            scope="project",
            tags=["zero-luce", "formato-risposta"],
        )
        memory_id = memory.id

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/facts/backfill",
            "body": {"memory_id": memory_id},
            "intent": "Backfill facts for existing Zero-Luce memory.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["created_count"] == 1
    assert body["result"]["facts"][0]["entity"] == "protocollo-zero-luce"

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    trace_kinds = [trace["kind"] for trace in traces]
    assert "mind.memory.facts.backfill" in trace_kinds
    assert "mind.tool_call" in trace_kinds


def test_mind_memory_facts_backfill_rebuilds_supersession_links(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Fact backfill supersession"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
        old_memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=(
                "Protocollo Zero-Luce uses three blocks: Contesto, Evidenza, "
                "Prossima azione."
            ),
            reason_for_storage="Old response format before facts.",
            expected_future_use="Use when Zero-Luce is requested.",
            confidence=0.8,
            salience=0.8,
            scope="project",
            tags=["zero-luce", "formato-risposta"],
        )
        new_memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=(
                "Protocollo Zero-Luce uses four blocks: Contesto, Evidenza, "
                "Rischio, Prossima azione."
            ),
            reason_for_storage="Updated response format before facts.",
            expected_future_use="Use when Zero-Luce is requested.",
            confidence=0.95,
            salience=0.9,
            scope="project",
            tags=["zero-luce", "formato-risposta"],
        )
        old_memory_id = old_memory.id
        new_memory_id = new_memory.id
        repositories.update_memory_lifecycle(
            db,
            memory_id=old_memory_id,
            status="deprecated",
            metadata={
                "lifecycle": {
                    "superseded_by": new_memory_id,
                    "deprecated_reason": "Four-block format replaced it.",
                }
            },
        )

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/facts/backfill",
            "body": {"include_inactive": True},
            "intent": "Backfill facts and reconstruct supersession links.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    facts = body["result"]["facts"]
    old_fact = next(fact for fact in facts if fact["memory_id"] == old_memory_id)
    new_fact = next(fact for fact in facts if fact["memory_id"] == new_memory_id)
    assert old_fact["status"] == "deprecated"
    assert old_fact["superseded_by_fact_id"] == new_fact["id"]
    assert new_fact["supersedes_fact_id"] == old_fact["id"]


def test_mind_memory_lifecycle_supersedes_and_deprecates_conflict(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Memory lifecycle"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M2.7",
        ).id
        old_memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=(
                "Protocollo Zero-Luce uses three blocks: Contesto, Evidenza, "
                "Prossima azione."
            ),
            reason_for_storage="Old Zero-Luce response format.",
            expected_future_use="Use when Zero-Luce is requested.",
            confidence=0.9,
            salience=0.8,
            scope="project",
            tags=["zero-luce", "protocollo", "formato-risposta"],
        )
        new_memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=(
                "Protocollo Zero-Luce uses four blocks: Contesto, Evidenza, "
                "Rischio, Prossima azione."
            ),
            reason_for_storage="Updated Zero-Luce response format.",
            expected_future_use="Use when Zero-Luce is requested.",
            confidence=0.95,
            salience=0.9,
            scope="project",
            tags=["zero-luce", "protocollo", "formato-risposta"],
        )
        old_memory_id = old_memory.id
        new_memory_id = new_memory.id

    conflicts_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/conflicts",
            "intent": "Inspect active memory conflicts before lifecycle repair.",
        },
    )

    assert conflicts_response.status_code == 200
    conflicts_body = conflicts_response.json()
    assert conflicts_body["ok"] is True
    assert conflicts_body["result"]["count"] == 1
    assert set(conflicts_body["result"]["conflicts"][0]["memory_ids"]) == {
        old_memory_id,
        new_memory_id,
    }

    supersede_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/supersede",
            "body": {
                "target_id": old_memory_id,
                "superseded_by": new_memory_id,
                "reason": "The four-block version supersedes the old format.",
            },
            "intent": "Resolve the Zero-Luce lifecycle conflict.",
        },
    )

    assert supersede_response.status_code == 200
    supersede_body = supersede_response.json()
    assert supersede_body["ok"] is True
    assert supersede_body["result"]["old_memory"]["status"] == "deprecated"
    assert supersede_body["result"]["new_memory"]["status"] == "active"
    assert (
        supersede_body["result"]["old_memory"]["metadata"]["lifecycle"]["last_event"][
            "superseded_by"
        ]
        == new_memory_id
    )
    assert old_memory_id in (
        supersede_body["result"]["new_memory"]["metadata"]["lifecycle"]["supersedes"]
    )

    read_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": f"/mind/memory/{old_memory_id}",
            "intent": "Verify the deprecated memory remains inspectable.",
        },
    )

    assert read_response.status_code == 200
    read_body = read_response.json()
    assert read_body["ok"] is True
    assert read_body["result"]["memory"]["status"] == "deprecated"

    resolved_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/conflicts",
            "intent": "Confirm no active conflict remains.",
        },
    )

    assert resolved_response.status_code == 200
    resolved_body = resolved_response.json()
    assert resolved_body["ok"] is True
    assert resolved_body["result"]["count"] == 0

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {"query": "Zero-Luce Rischio", "top_k": 5},
            "intent": "Search active Zero-Luce memories after lifecycle repair.",
        },
    )

    assert search_response.status_code == 200
    search_body = search_response.json()
    returned_ids = {
        item["id"] for item in search_body["result"]["memories"]
    }
    assert new_memory_id in returned_ids
    assert old_memory_id not in returned_ids

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    trace_kinds = [trace["kind"] for trace in traces]
    assert "memory.conflicts" in trace_kinds
    assert "mind.memory.supersede" in trace_kinds
    assert "mind.memory.read" in trace_kinds

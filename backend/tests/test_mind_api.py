import json
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import LLMTextResult
from app.main import create_app
from app.mind.schema import route_usage_guide, schema_metadata
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
                            "mitigation": "Use help.",
                        }
                    ],
                    "claim_checks": [
                        {
                            "claim": "The command is implemented.",
                            "support": "needs_evidence",
                            "confidence": 0.42,
                            "recommended_action": "Check shell help first.",
                        }
                    ],
                    "missing_evidence": ["current Mind shell help"],
                    "recommended_internal_actions": [
                        {
                            "command": "help",
                            "reason": "Confirm current command surface.",
                        },
                        {
                            "command": "memory inspect --kind=conflict --sample=20",
                            "reason": "Deliberately wrong action shape from reviewer.",
                        },
                        {
                            "command": "unknown_family inspect",
                            "reason": "Deliberately wrong command family from reviewer.",
                        }
                    ],
                    "reasoning_digest": "Previous reasoning considered shell help evidence.",
                    "drift_findings": [],
                    "open_loops": [],
                    "tool_use_assessment": [],
                    "memory_candidates_from_reasoning": [],
                    "should_continue": True,
                    "next_focus_question": "What does help report?",
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


class FakeOpenRouterRetrievalClient:
    embedding_calls: list[dict] = []
    rerank_calls: list[dict] = []

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def embed_texts(self, *, model: str, texts: list[str]) -> list[list[float]]:
        self.__class__.embedding_calls.append({"model": model, "texts": texts})
        return [_fake_embedding(text) for text in texts]

    def rerank(
        self,
        *,
        model: str,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> dict:
        self.__class__.rerank_calls.append(
            {
                "model": model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            }
        )
        scored = []
        for index, document in enumerate(documents):
            lowered = document.casefold()
            score = 0.99 if (
                "cacao" in lowered
                or "tisana" in lowered
                or "camomilla" in lowered
            ) else 0.21
            scored.append(
                {
                    "index": index,
                    "relevance_score": score,
                    "document": {"text": document},
                }
            )
        scored.sort(key=lambda item: item["relevance_score"], reverse=True)
        return {
            "id": "rerank_fake_1",
            "model": model,
            "provider": "fake-openrouter",
            "usage": {"total_tokens": 42},
            "results": scored[:top_n],
        }


def _fake_embedding(text: str) -> list[float]:
    lowered = text.casefold()
    if (
        "cacao" in lowered
        or "tisana" in lowered
        or "camomilla" in lowered
        or "bevanda" in lowered
        or "caffe" in lowered
        or "concentr" in lowered
    ):
        return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    if "camminata" in lowered or "hiking" in lowered:
        return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]


def make_client(
    db_engine: Engine,
    *,
    provider_factory=None,
    settings_overrides: dict | None = None,
) -> TestClient:
    settings_data = {
        "app_name": "Test Mind",
        "environment": "test",
        "minimax_api_key": "test-key",
        "minimax_model": "MiniMax-M2.7",
        "minimax_max_tokens": 4096,
        "retrieval_hybrid_mode": "off",
    }
    settings_data.update(settings_overrides or {})
    settings = Settings(
        **settings_data,
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
    assert body["result"]["schema_version"] == (
        "2026-07-28.semantic-authority-v2"
    )
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
    assert route_status[("POST", "/mind/memory/facts/backfill")] == (
        "internal_maintenance_only"
    )
    assert route_status[("POST", "/mind/memory/graph")] == "implemented"
    assert route_status[("GET", "/mind/memory/conflicts")] == "implemented"
    assert route_status[("GET", "/mind/memory/proposals")] == "implemented"
    assert (
        route_status[("GET", "/mind/memory/proposals/{proposal_id}")]
        == "implemented"
    )
    assert (
        route_status[("POST", "/mind/memory/proposals/decide")]
        == "implemented"
    )
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
    assert route_status[("POST", "/mind/focus")] == "implemented"
    assert route_status[("POST", "/mind/volition")] == "implemented"
    assert route_status[("POST", "/mind/affect")] == "implemented"
    focus_guide = route_usage_guide("POST", "/mind/focus")
    volition_guide = route_usage_guide("POST", "/mind/volition")
    assert focus_guide is not None
    assert volition_guide is not None
    assert "timeline" in focus_guide["body_schema"]["properties"]["action"]["enum"]
    assert "list_due" in volition_guide["body_schema"]["properties"]["action"]["enum"]
    metacognition_route = next(
        route
        for route in routes
        if route["method"] == "POST" and route["path"] == "/mind/metacognition/step"
    )
    assert "body_schema" not in metacognition_route
    assert "thinking retrospection" in metacognition_route["purpose"]
    assert ("POST", "/mind/attention/context") not in route_status
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


def test_mind_memory_proposals_are_model_facing_candidates(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={"title": "Hidden proposal"}).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "GET",
            "path": "/mind/memory/proposals",
            "body": {"status": "pending", "limit": 10},
            "intent": "Inspect pending memory proposals.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["operation"] == "memory.proposals.list"
    assert body["result"]["proposals"] == []


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


def test_mind_call_returns_structured_error_for_removed_attention_route(
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
    assert "current Mind shell help" in body["result"]["review"]["missing_evidence"]
    assert body["result"]["review"]["recommended_internal_actions"][0]["command"] == "help"
    assert (
        body["result"]["review"]["recommended_internal_actions"][0]["schema_status"]
        == "implemented_command"
    )
    malformed_memory_action = body["result"]["review"]["recommended_internal_actions"][1]
    assert malformed_memory_action["schema_status"] == "missing_required_argument"
    assert malformed_memory_action["call_is_available"] is False
    assert malformed_memory_action["canonical_namespace"] == "memory"
    assert malformed_memory_action["canonical_action"] == "open"
    unknown_command_action = body["result"]["review"]["recommended_internal_actions"][2]
    assert unknown_command_action["schema_status"] == "unknown_command_family"
    assert unknown_command_action["call_is_available"] is False
    assert body["result"]["model"] == "MiniMax-M2.7"
    assert FakeMetacognitionProvider.prompts
    assert "available_mind_shell_commands" in FakeMetacognitionProvider.prompts[0]

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


def test_mind_metacognition_error_guide_includes_retrospection_fields(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine, provider_factory=FakeMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Metacognition usage guide"},
    ).json()

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Inspect local recovery guidance for an invalid retrospective call.",
            "body": {
                "mode": "recover_open_loops",
                "objective": "Review the previous reasoning loop.",
                "turn_scope": "previous",
                "detail": "everything",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "metacognition.invalid_body"
    assert body["usage_guide"]["method"] == "POST"
    assert body["usage_guide"]["path"] == "/mind/metacognition/step"
    assert body["usage_guide"]["parameters"]["turn_scope"]["enum"] == [
        "none",
        "previous",
    ]
    assert body["usage_guide"]["parameters"]["detail"]["enum"] == [
        "digest",
        "excerpt",
        "raw",
    ]
    assert (
        body["usage_guide"]["accepted_aliases"]["reasoning_scope"]
        == "turn_scope"
    )


def test_mind_metacognition_can_retrospect_previous_turn_thinking(
    db_engine: Engine,
) -> None:
    FakeMetacognitionProvider.prompts = []
    client = make_client(db_engine, provider_factory=FakeMetacognitionProvider)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Thinking retrospection"},
    ).json()

    with Session(db_engine) as db:
        previous_turn = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        )
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            role="user",
            content="Ho chiesto di verificare se Scarlet perdeva un loop aperto.",
        )
        repositories.add_event(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            event_type="assistant.note.emitted",
            payload={"text": "Controllo il punto critico prima della risposta."},
        )
        repositories.add_tool_call(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            tool_name="mind_api",
            arguments={
                "method": "GET",
                "path": "/mind/schema",
                "intent": "Inspect available cognitive routes.",
            },
            result={"ok": True, "result": {"schema_version": "test"}},
            status="completed",
        )
        repositories.add_message(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            role="assistant",
            content="Ho verificato lo schema, ma devo ancora controllare il loop aperto.",
        )
        repositories.add_trace(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            kind="llm.response",
            payload={
                "raw_provider_messages": [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "thinking",
                                "thinking": (
                                    "I should verify the schema and then return "
                                    "to the open loop about missed memory writes."
                                ),
                            },
                            {
                                "type": "text",
                                "text": "Ho verificato lo schema.",
                            },
                        ],
                    }
                ]
            },
        )
        repositories.add_event(
            db,
            session_id=session["id"],
            turn_id=previous_turn.id,
            event_type="llm.thinking.captured",
            payload={"chars": 83},
        )
        previous_turn_id = previous_turn.id
        repositories.complete_turn(db, turn_id=previous_turn_id)
        current_turn = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        )
        current_turn_id = current_turn.id

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": current_turn_id,
            "method": "POST",
            "path": "/mind/metacognition/step",
            "intent": "Use previous thinking to detect an unresolved loop.",
            "body": {
                "mode": "recover_open_loops",
                "objective": "Review the previous turn for unresolved reasoning loops.",
                "reasoning_scope": "previous",
                "reasoning_detail": "digest",
                "known_evidence": {
                    "item": ["The user asked for thinking visibility."]
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["mode"] == "recover_open_loops"
    assert body["result"]["retrospection"]["available"] is True
    assert body["result"]["retrospection"]["source_turn_id"] == previous_turn_id
    assert body["result"]["retrospection"]["thinking_block_count"] == 1
    assert body["result"]["retrospection"]["tool_call_count"] == 1
    assert (
        "Previous reasoning considered shell help evidence"
        in body["result"]["review"]["reasoning_digest"]
    )
    assert FakeMetacognitionProvider.prompts
    prompt = FakeMetacognitionProvider.prompts[0]
    assert "thinking-retrospection-pack-v1" in prompt
    assert "missed memory writes" in prompt
    assert '"known_evidence": [\n    "The user asked for thinking visibility."\n  ]' in prompt

    traces = client.get(f"/api/debug/traces/{current_turn_id}").json()
    metacognition_trace = next(
        trace for trace in traces if trace["kind"] == "mind.metacognition.step"
    )
    trace_pack = metacognition_trace["payload"]["retrospection_pack"]
    assert trace_pack["available"] is True
    assert trace_pack["thinking"]["available"] is True


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
    assert write_body["result"]["memory"]["facts"] == []
    with Session(db_engine) as db:
        surfaces = repositories.list_memory_surfaces(db, target_id=memory_id)
        graph_nodes = repositories.list_memory_graph_nodes(
            db,
            source_memory_id=memory_id,
        )
    surface_kinds = {surface.surface_kind for surface in surfaces}
    assert {
        "memory_text",
        "preference_text",
        "future_use_text",
        "temporal_text",
    }.issubset(surface_kinds)
    memory_text_surface = next(
        surface for surface in surfaces if surface.surface_kind == "memory_text"
    )
    assert memory_text_surface.embedding_status == "pending"
    assert memory_text_surface.metadata_json["compiler"] == (
        "deterministic_backend_surface_compiler"
    )
    assert any(node.node_key == f"memory:{memory_id}" for node in graph_nodes)

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
    assert "memory_surfaces_v1" in search_body["result"]["retrieval_readiness"][
        "readiness_stages"
    ]
    assert "memory_surface_taxonomy_v1" in search_body["result"]["retrieval_readiness"][
        "readiness_stages"
    ]
    assert search_body["result"]["memories"][0]["id"] == memory_id
    assert search_body["result"]["memories"][0]["usage_count"] == 0
    with Session(db_engine) as db:
        activities = repositories.list_memory_activities(db, memory_id=memory_id)
    assert activities[0].activity_kind == "manual_search"

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


def test_mind_memory_content_chunks_are_internal_surfaces_only(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Memory chunk surfaces"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    long_content = (
        "The user is experimenting with a human-like memory system for Scarlet. "
        "The first point is that content retrieval should find the exact claim "
        "inside long memories. "
        "The second point is that support surfaces should not be enough to select "
        "a memory on their own. "
        "The third point is that the model-facing packet must stay clean and "
        "deduplicated even when multiple internal chunks match."
    )
    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "project_fact",
                "scope": "memory_retrieval_design",
                "content": long_content,
                "reason_for_storage": "Checkpoint for retrieval-surface design.",
                "expected_future_use": "Use when evaluating long-memory search.",
            },
            "intent": "Persist a long memory that requires chunk surfaces.",
        },
    )

    assert write_response.status_code == 200
    memory_id = write_response.json()["result"]["memory_id"]
    with Session(db_engine) as db:
        chunk_surfaces = repositories.list_memory_surfaces(
            db,
            target_id=memory_id,
            surface_kind="content_chunk_text",
        )
    assert len(chunk_surfaces) >= 1
    assert len({surface.surface_key for surface in chunk_surfaces}) == len(
        chunk_surfaces
    )

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "exact claim inside long memories",
                "top_k": 5,
            },
            "intent": "Verify chunk surfaces deduplicate to a clean memory packet.",
        },
    )

    assert search_response.status_code == 200
    memories = search_response.json()["result"]["memories"]
    assert [memory["id"] for memory in memories].count(memory_id) == 1
    assert "content_chunk_text" not in memories[0]


def test_mind_memory_static_salience_does_not_override_query_relevance(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Dynamic relevance"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id
        relevant = repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content=(
                "L'utente adora il cioccolato ma non può mangiarne troppo "
                "perche poi sta male."
            ),
            reason_for_storage="Vincolo alimentare personale.",
            expected_future_use="Usare per suggerimenti alimentari e dolci.",
            confidence=0.1,
            salience=0.1,
            source_session_id=session["id"],
            source_turn_id=turn_id,
        )
        repositories.add_memory(
            db,
            memory_type="user_preference",
            scope="user",
            content="L'utente apprezza film con scene ambientate in cioccolaterie.",
            reason_for_storage="Preferenza narrativa occasionale.",
            expected_future_use="Usare per suggerimenti di film.",
            confidence=0.99,
            salience=0.99,
            source_session_id=session["id"],
            source_turn_id=turn_id,
        )
        relevant_id = relevant.id

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "cioccolato troppo sto male vincolo alimentare",
                "scope": "user",
                "top_k": 2,
            },
            "intent": "A/B guard: query relevance must beat stored static salience.",
        },
    )

    assert search_response.status_code == 200
    memories = search_response.json()["result"]["memories"]
    assert memories[0]["id"] == relevant_id
    assert "salience" not in memories[0]
    assert "confidence" not in memories[0]


def test_mind_memory_search_reports_trace_only_shadow_retrieval(
    db_engine: Engine,
) -> None:
    client = make_client(
        db_engine,
        settings_overrides={
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "local",
            "retrieval_shadow_top_k": 3,
            "retrieval_shadow_vector_dim": 64,
        },
    )
    write_session = client.post(
        "/api/chat/sessions",
        json={"title": "Shadow write"},
    ).json()
    search_session = client.post(
        "/api/chat/sessions",
        json={"title": "Shadow search"},
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
                "content": "The owner prefers cacao tea during evening focus work.",
                "reason_for_storage": "Stable beverage preference for future suggestions.",
                "expected_future_use": "Avoid suggesting late coffee when cacao tea fits.",
                "confidence": 0.88,
                "salience": 0.76,
                "scope": "project",
                "tags": ["cacao", "focus"],
            },
            "intent": "Persist a stable beverage preference.",
        },
    )
    assert write_response.status_code == 200
    memory_id = write_response.json()["result"]["memory_id"]

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": search_session["id"],
            "turn_id": search_turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "cacao tea evening focus",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 2,
            },
            "intent": "Retrieve relevant beverage preferences.",
        },
    )
    assert search_response.status_code == 200
    body = search_response.json()
    assert body["ok"] is True
    assert body["result"]["memories"][0]["id"] == memory_id
    assert body["result"]["retrieval_stages"] == [
        "fts5_sparse_v1",
        "lexical_fallback_v1",
    ]
    shadow = body["result"]["retrieval_shadow"]
    assert shadow["ok"] is True
    assert shadow["status"] == "completed"
    assert shadow["backend"] == "local"
    assert shadow["ranking_policy"] == "trace_only_no_active_ranking"
    assert {item["target_id"] for item in shadow["results"]} == {memory_id}

    search_traces = client.get(f"/api/debug/traces/{search_turn_id}").json()
    search_trace = search_traces[0]["payload"]
    assert search_trace["retrieval_shadow"]["backend"] == "local"
    assert {
        item["target_id"]
        for item in search_trace["retrieval_shadow"]["results"]
    } == {memory_id}


def test_mind_memory_search_reports_openrouter_embedding_and_rerank_shadow(
    db_engine: Engine,
    monkeypatch,
) -> None:
    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    FakeOpenRouterRetrievalClient.rerank_calls.clear()
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        FakeOpenRouterRetrievalClient,
    )
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_embedding_model": "test/embed",
            "retrieval_shadow_top_k": 3,
            "retrieval_shadow_vector_dim": 8,
            "retrieval_shadow_cloud_surface_limit": 20,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 3,
        },
    )
    write_session = client.post(
        "/api/chat/sessions",
        json={"title": "OpenRouter shadow write"},
    ).json()
    search_session = client.post(
        "/api/chat/sessions",
        json={"title": "OpenRouter shadow search"},
    ).json()

    with Session(db_engine) as db:
        write_turn_id = repositories.create_turn(
            db,
            session_id=write_session["id"],
            model="MiniMax-M3",
        ).id
        search_turn_id = repositories.create_turn(
            db,
            session_id=search_session["id"],
            model="MiniMax-M3",
        ).id

    cacao_response = client.post(
        "/mind/call",
        json={
            "session_id": write_session["id"],
            "turn_id": write_turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner prefers cacao tea during evening focus work.",
                "reason_for_storage": "Stable beverage preference for future suggestions.",
                "expected_future_use": "Prefer cacao tea over late coffee suggestions.",
                "confidence": 0.88,
                "salience": 0.76,
                "scope": "project",
                "tags": ["cacao", "focus"],
            },
            "intent": "Persist a stable beverage preference.",
        },
    )
    assert cacao_response.status_code == 200
    cacao_memory_id = cacao_response.json()["result"]["memory_id"]

    other_response = client.post(
        "/mind/call",
        json={
            "session_id": write_session["id"],
            "turn_id": write_turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner likes quiet hiking routes on weekends.",
                "reason_for_storage": "Stable leisure preference for future suggestions.",
                "expected_future_use": "Suggest calm outdoor plans when relevant.",
                "confidence": 0.81,
                "salience": 0.62,
                "scope": "project",
                "tags": ["hiking", "weekend"],
            },
            "intent": "Persist a stable leisure preference.",
        },
    )
    assert other_response.status_code == 200

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": search_session["id"],
            "turn_id": search_turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "bevanda serale per concentrarmi senza caffe",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 2,
            },
            "intent": "Retrieve a beverage preference using paraphrased Italian.",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    shadow = body["result"]["retrieval_shadow"]
    assert shadow["ok"] is True
    assert shadow["status"] == "completed"
    assert shadow["backend"] == "openrouter"
    assert shadow["embedding_model"] == "test/embed"
    assert shadow["ranking_policy"] == "trace_only_no_active_ranking"
    assert shadow["embedding_cache"]["misses"] > 0
    assert {item["target_id"] for item in shadow["results"]} >= {cacao_memory_id}
    assert shadow["grouped_results"][0]["target_id"] == cacao_memory_id
    assert shadow["grouped_results"][0]["ranking_policy"] == (
        "memory_target_role_aware_surface_score_v2"
    )
    assert shadow["grouped_results"][0]["contributing_surfaces"]
    assert shadow["rerank"]["ok"] is True
    assert shadow["rerank"]["status"] == "completed"
    assert shadow["rerank"]["model"] == "test/rerank"
    assert shadow["rerank"]["results"][0]["target_id"] == cacao_memory_id
    assert shadow["rerank"]["results"][0]["backend"] == "openrouter_rerank"
    assert shadow["rerank"]["grouped_status"] == "completed"
    assert shadow["rerank"]["grouped_results"][0]["target_id"] == cacao_memory_id
    assert shadow["rerank"]["grouped_results"][0]["backend"] == (
        "openrouter_grouped_rerank"
    )
    assert FakeOpenRouterRetrievalClient.embedding_calls
    assert FakeOpenRouterRetrievalClient.rerank_calls

    search_traces = client.get(f"/api/debug/traces/{search_turn_id}").json()
    trace_shadow = search_traces[0]["payload"]["retrieval_shadow"]
    assert trace_shadow["backend"] == "openrouter"
    assert trace_shadow["rerank"]["results"][0]["target_id"] == cacao_memory_id
    assert trace_shadow["rerank"]["grouped_results"][0]["target_id"] == cacao_memory_id

    with Session(db_engine) as db:
        cacao_surfaces = repositories.list_memory_surfaces(
            db,
            target_type="memory",
            target_id=cacao_memory_id,
            limit=20,
        )
        assert cacao_surfaces
        assert {
            surface.embedding_status for surface in cacao_surfaces
        } == {"embedded"}
        assert {
            surface.embedding_model for surface in cacao_surfaces
        } == {"test/embed"}
        assert all(surface.embedding_vector_id for surface in cacao_surfaces)
        for surface in cacao_surfaces:
            surface.embedding_status = "pending"
            surface.embedding_model = None
            surface.embedding_vector_id = None
            db.add(surface)
        db.commit()

    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    second_search_response = client.post(
        "/mind/call",
        json={
            "session_id": search_session["id"],
            "turn_id": search_turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "bevanda serale per concentrarmi senza caffe",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 2,
            },
            "intent": "Retrieve a beverage preference using cached embeddings.",
        },
    )
    assert second_search_response.status_code == 200
    second_shadow = second_search_response.json()["result"]["retrieval_shadow"]
    assert second_shadow["embedding_cache"]["hits"] > 0

    with Session(db_engine) as db:
        refreshed_surfaces = repositories.list_memory_surfaces(
            db,
            target_type="memory",
            target_id=cacao_memory_id,
            limit=20,
        )
        assert {
            surface.embedding_status for surface in refreshed_surfaces
        } == {"embedded"}
        assert {
            surface.embedding_model for surface in refreshed_surfaces
        } == {"test/embed"}
        assert all(surface.embedding_vector_id for surface in refreshed_surfaces)


def test_mind_memory_search_active_hybrid_promotes_grouped_dense_candidate(
    db_engine: Engine,
    monkeypatch,
) -> None:
    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    FakeOpenRouterRetrievalClient.rerank_calls.clear()
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        FakeOpenRouterRetrievalClient,
    )
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_embedding_model": "test/embed",
            "retrieval_shadow_top_k": 3,
            "retrieval_shadow_vector_dim": 8,
            "retrieval_shadow_cloud_surface_limit": 20,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 3,
            "retrieval_hybrid_mode": "active",
            "retrieval_hybrid_min_dense_score": 0.38,
            "retrieval_hybrid_min_rerank_score": 0.55,
        },
    )
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Active hybrid retrieval"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    cacao_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner prefers cacao tea during evening focus work.",
                "reason_for_storage": "Stable beverage preference for future suggestions.",
                "expected_future_use": "Prefer cacao tea over late coffee suggestions.",
                "confidence": 0.88,
                "salience": 0.76,
                "scope": "project",
                "tags": ["cacao", "focus"],
            },
            "intent": "Persist a stable beverage preference.",
        },
    )
    assert cacao_response.status_code == 200
    cacao_memory_id = cacao_response.json()["result"]["memory_id"]

    other_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner likes quiet hiking routes on weekends.",
                "reason_for_storage": "Stable leisure preference for future suggestions.",
                "expected_future_use": "Suggest calm outdoor plans when relevant.",
                "confidence": 0.81,
                "salience": 0.62,
                "scope": "project",
                "tags": ["hiking", "weekend"],
            },
            "intent": "Persist a stable leisure preference.",
        },
    )
    assert other_response.status_code == 200

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "bevanda serale per concentrarmi senza caffe",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 1,
            },
            "intent": "Retrieve a beverage preference using paraphrased Italian.",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["result"]["retrieval_hybrid"]["active"] is True
    assert body["result"]["memories"][0]["id"] == cacao_memory_id
    assert body["result"]["memories"][0]["retrieval_signals"]["hybrid"][
        "dense_signal"
    ] is True


def test_mind_memory_search_hybrid_prefers_direct_content_over_broad_overlap(
    db_engine: Engine,
    monkeypatch,
) -> None:
    """Prediction: direct beverage content beats broad evening/report overlap."""
    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    FakeOpenRouterRetrievalClient.rerank_calls.clear()
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        FakeOpenRouterRetrievalClient,
    )
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_embedding_model": "test/embed",
            "retrieval_shadow_top_k": 5,
            "retrieval_shadow_vector_dim": 8,
            "retrieval_shadow_cloud_surface_limit": 30,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 5,
            "retrieval_hybrid_mode": "active",
            "retrieval_hybrid_min_dense_score": 0.38,
            "retrieval_hybrid_min_rerank_score": 0.55,
        },
    )
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Hybrid calibration prediction"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    direct_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "L'utente preferisce una tisana serale alla camomilla, "
                    "calda e senza caffeina, quando vuole rilassarsi."
                ),
                "reason_for_storage": "Preferenza personale su bevande serali.",
                "expected_future_use": (
                    "Usare quando si parla di sera, bevande, sonno o relax."
                ),
                "scope": "user",
            },
            "intent": "Seed the expected direct memory.",
        },
    )
    assert direct_response.status_code == 200
    direct_memory_id = direct_response.json()["result"]["memory_id"]

    distractor_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "response_format",
                "content": "L'utente preferisce report serali sintetici con tre sezioni.",
                "reason_for_storage": "Preferenza di formato per riepiloghi.",
                "expected_future_use": "Usare per report di fine giornata.",
                "scope": "project",
            },
            "intent": "Seed a broad evening/report distractor.",
        },
    )
    assert distractor_response.status_code == 200

    support_only_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "L'utente ama percorsi di trekking tranquilli nel weekend.",
                "reason_for_storage": "Preferenza ricreativa personale.",
                "expected_future_use": (
                    "Potrebbe aiutare anche per tisane serali o routine senza caffeina."
                ),
                "scope": "user",
            },
            "intent": "Seed a misleading auxiliary-surface memory.",
        },
    )
    assert support_only_response.status_code == 200

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "tisana serale senza caffeina per rilassarmi",
                "top_k": 3,
            },
            "intent": (
                "Calibration probe: direct content should beat broad overlap "
                "and support-only hints."
            ),
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    memories = body["result"]["memories"]
    assert memories[0]["id"] == direct_memory_id
    assert memories[0]["retrieval_signals"]["hybrid"]["rerank_signal"] is True
    assert FakeOpenRouterRetrievalClient.rerank_calls
    assert (
        FakeOpenRouterRetrievalClient.rerank_calls[-1]["query"]
        == "tisana serale senza caffeina per rilassarmi"
    )


def test_mind_memory_search_active_hybrid_does_not_select_dense_below_threshold(
    db_engine: Engine,
    monkeypatch,
) -> None:
    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    FakeOpenRouterRetrievalClient.rerank_calls.clear()
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        FakeOpenRouterRetrievalClient,
    )
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_embedding_model": "test/embed",
            "retrieval_shadow_top_k": 3,
            "retrieval_shadow_vector_dim": 8,
            "retrieval_shadow_cloud_surface_limit": 20,
            "retrieval_shadow_rerank_enabled": False,
            "retrieval_hybrid_mode": "active",
            "retrieval_hybrid_min_dense_score": 0.6,
        },
    )
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Active hybrid negative control"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner likes quiet hiking routes on weekends.",
                "reason_for_storage": "Stable leisure preference for future suggestions.",
                "expected_future_use": "Suggest calm outdoor plans when relevant.",
                "confidence": 0.81,
                "salience": 0.62,
                "scope": "project",
                "tags": ["hiking", "weekend"],
            },
            "intent": "Persist a stable leisure preference.",
        },
    )
    assert response.status_code == 200

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "playlist jazz notturna per cucinare",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 3,
            },
            "intent": "Negative control: no related memory should be promoted.",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["result"]["retrieval_hybrid"]["active"] is True
    assert body["result"]["retrieval_hybrid"]["entry_count"] == 0
    assert body["result"]["memories"] == []


def test_mind_memory_search_active_hybrid_does_not_promote_support_only_surface(
    db_engine: Engine,
    monkeypatch,
) -> None:
    FakeOpenRouterRetrievalClient.embedding_calls.clear()
    FakeOpenRouterRetrievalClient.rerank_calls.clear()
    monkeypatch.setattr(
        "app.mind.shadow_retrieval.OpenRouterRetrievalClient",
        FakeOpenRouterRetrievalClient,
    )
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_embedding_model": "test/embed",
            "retrieval_shadow_top_k": 3,
            "retrieval_shadow_vector_dim": 8,
            "retrieval_shadow_cloud_surface_limit": 20,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 3,
            "retrieval_hybrid_mode": "active",
            "retrieval_hybrid_min_dense_score": 0.38,
            "retrieval_hybrid_min_rerank_score": 0.55,
        },
    )
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Support-only dense retrieval"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner likes quiet hiking routes on weekends.",
                "reason_for_storage": "Stable leisure preference for future suggestions.",
                "expected_future_use": (
                    "Use when choosing a beverage for evening focus without caffeine."
                ),
                "confidence": 0.84,
                "salience": 0.67,
                "scope": "project",
                "tags": ["hiking", "weekend"],
            },
            "intent": "Persist a leisure preference with a misleading future-use hint.",
        },
    )
    assert write_response.status_code == 200
    memory_id = write_response.json()["result"]["memory_id"]

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "bevanda serale per concentrarmi senza caffe",
                "types": ["user_preference"],
                "scope": "project",
                "top_k": 3,
            },
            "intent": "Negative control: future-use support must not select a memory.",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    shadow = body["result"]["retrieval_shadow"]
    group = next(
        item for item in shadow["grouped_results"] if item["target_id"] == memory_id
    )
    assert group["active_rank_eligible"] is False
    assert group["promotable_score"] == 0.0
    assert group["support_score"] >= 0.38
    assert "future_use_text" in group["support_surface_kinds"]
    assert "future_use_text" not in group["promotable_surface_kinds"]
    assert shadow["rerank"]["status"] == (
        "deferred_to_memory_level_final_arbiter"
    )
    assert body["result"]["retrieval_hybrid"]["entry_count"] == 0
    assert body["result"]["memories"] == []


def test_mind_memory_search_uses_networkx_graph_expansion_for_dynamic_concepts(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Graph expansion memory search"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "Adora il cioccolato ma non può mangiarne troppo: il corpo "
                    "segnala un limite preciso, superata quella soglia sta male."
                ),
                "reason_for_storage": (
                    "Vincolo alimentare personale espresso dall'utente."
                ),
                "expected_future_use": (
                    "Riferimento per raccomandazioni alimentari, suggerimenti, "
                    "dolci e benessere."
                ),
                "confidence": 0.95,
                "salience": 0.85,
                "scope": "user",
                "tags": [
                    "preferenza-alimentare",
                    "cioccolato",
                    "limite-salutare",
                ],
            },
            "intent": "Persist a personal food constraint.",
        },
    )
    assert write_response.status_code == 200
    memory_id = write_response.json()["result"]["memory_id"]

    search_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/search",
            "body": {
                "query": "preferenza alimentare con limite salutare",
                "types": ["user_preference"],
                "scope": "user",
                "top_k": 3,
            },
            "intent": "Retrieve personal constraints through dynamic graph concepts.",
        },
    )

    assert search_response.status_code == 200
    body = search_response.json()
    assert body["ok"] is True
    assert body["result"]["retrieval_graph"]["backend"] == "networkx"
    assert body["result"]["retrieval_graph"]["ranking_policy"] == (
        "networkx_associative_memory_graph_v1"
    )
    assert body["result"]["memories"][0]["id"] == memory_id
    graph_signal = body["result"]["memories"][0]["retrieval_signals"]["graph"]
    assert "scope:user" in graph_signal["domains"]
    assert "type:user_preference" in graph_signal["domains"]
    assert graph_signal["score"] > 0


def test_mind_memory_graph_exposes_associative_neighbors(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Graph navigation"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    write_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "scope": "user",
                "content": "The user prefers quiet evening tea when they need focus.",
                "reason_for_storage": "Useful future personalization around evening focus.",
                "expected_future_use": "Suggest calm evening routines.",
            },
            "intent": "Persist a personal evening focus preference.",
        },
    )
    memory_id = write_response.json()["result"]["memory_id"]

    graph_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/graph",
            "body": {"memory_id": memory_id, "depth": 2, "limit": 40},
            "intent": "Inspect graph neighbors for a retrieved memory.",
        },
    )

    assert graph_response.status_code == 200
    body = graph_response.json()
    assert body["ok"] is True
    assert body["result"]["root_memory"]["id"] == memory_id
    node_keys = {node["node_key"] for node in body["result"]["nodes"]}
    assert f"memory:{memory_id}" in node_keys
    assert body["result"]["edges"]


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
    assert "confidence" not in write_body["result"]["memory"]
    assert "salience" not in write_body["result"]["memory"]
    ignored = write_body["result"]["memory"]["metadata"][
        "agent_supplied_fields_ignored_for_ranking"
    ]
    assert ignored["confidence"] == 0.85
    assert ignored["tags"] == ["sal"]
    assert ignored["metadata"]["model_suggested_id"] == "alias_pref"
    assert ignored["metadata"]["model_extra"] == {"salient_for": "status reporting"}

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
    assert scope_type_body["result"]["memory"]["scope"] == "general"
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
    assert "confidence" not in write_body["result"]["memory"]
    assert (
        write_body["result"]["memory"]["metadata"][
            "agent_supplied_fields_ignored_for_ranking"
        ]["confidence"]
        == 0.85
    )
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


def test_mind_memory_fact_alias_matching_uses_phrase_boundaries(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    session = client.post(
        "/api/chat/sessions",
        json={"title": "Fact alias boundaries"},
    ).json()
    with Session(db_engine) as db:
        turn_id = repositories.create_turn(
            db,
            session_id=session["id"],
            model="MiniMax-M3",
        ).id

    chocolate_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "Adora il cioccolato ma non può mangiarne troppo: il corpo "
                    "segnala un limite preciso, superata quella soglia sta male."
                ),
                "reason": "Stable personal food constraint.",
                "expected_future_use": "Use for future food suggestions.",
                "confidence": 0.9,
                "salience": 0.85,
                "scope": "user",
                "tags": [
                    "preferenza-alimentare",
                    "cioccolato",
                    "limite-salutare",
                ],
            },
            "intent": "Persist a personal food constraint.",
        },
    )

    assert chocolate_response.status_code == 200
    chocolate_body = chocolate_response.json()
    assert chocolate_body["ok"] is True
    chocolate_facts = chocolate_body["result"]["memory"]["facts"]
    assert all(fact["entity"] != "sal-updates" for fact in chocolate_facts)

    brief_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": (
                    "User prefers brief, non-technical responses, especially "
                    "for evaluative or analytical tasks."
                ),
                "reason": "Stable communication style preference.",
                "expected_future_use": "Default to plain short answers when relevant.",
                "confidence": 0.85,
                "salience": 0.7,
                "scope": "user",
                "tags": ["communication_style", "preferences", "register"],
            },
            "intent": "Persist a communication style preference.",
        },
    )

    assert brief_response.status_code == 200
    brief_body = brief_response.json()
    assert brief_body["ok"] is True
    assert brief_body["result"]["memory"]["facts"] == []
    assert brief_body["result"]["memory"]["tags"] == []
    ignored_fields = brief_body["result"]["memory"]["metadata"][
        "agent_supplied_fields_ignored_for_ranking"
    ]
    assert ignored_fields["tags"] == [
        "communication_style",
        "preferences",
        "register",
    ]

    sal_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "POST",
            "path": "/mind/memory/write",
            "body": {
                "type": "user_preference",
                "content": "The owner prefers SAL updates with risks and next steps.",
                "reason": "Stable status-reporting preference.",
                "expected_future_use": "Shape future SAL summaries.",
                "confidence": 0.9,
                "salience": 0.8,
                "scope": "project",
                "tags": ["sal", "status"],
            },
            "intent": "Persist a real SAL status update preference.",
        },
    )

    assert sal_response.status_code == 200
    sal_body = sal_response.json()
    assert sal_body["ok"] is True
    assert sal_body["result"]["memory"]["facts"] == []


def test_mind_memory_writes_do_not_create_heuristic_facts_or_conflicts(
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
    assert old_body["result"]["memory"]["facts"] == []
    assert new_body["result"]["memory"]["facts"] == []

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
    assert facts_body["result"]["count"] == 0
    assert facts_body["result"]["facts"] == []

    unfiltered_facts_response = client.post(
        "/mind/call",
        json={
            "session_id": session["id"],
            "turn_id": turn_id,
            "method": "GET",
            "path": "/mind/memory/facts",
            "body": {},
            "intent": (
                "Inspect canonical facts; this operational intent must not "
                "be interpreted as a data query."
            ),
        },
    )

    assert unfiltered_facts_response.status_code == 200
    unfiltered_facts_body = unfiltered_facts_response.json()
    assert unfiltered_facts_body["ok"] is True
    assert unfiltered_facts_body["result"]["count"] == 0
    assert unfiltered_facts_body["result"]["facts"] == []

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
    assert conflicts_body["result"]["count"] == 0
    assert conflicts_body["result"]["conflicts"] == []

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
    assert old_facts == []
    assert new_facts == []

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


def test_mind_memory_facts_backfill_is_traceable_noop(db_engine: Engine) -> None:
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
    assert body["result"]["created_count"] == 0
    assert body["result"]["facts"] == []

    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    trace_kinds = [trace["kind"] for trace in traces]
    assert "mind.memory.facts.backfill" in trace_kinds
    assert "mind.tool_call" in trace_kinds


def test_mind_memory_facts_backfill_preserves_memory_lifecycle_without_facts(
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
    assert facts == []
    with Session(db_engine) as db:
        old_after = repositories.get_memory(db, old_memory_id)
        new_after = repositories.get_memory(db, new_memory_id)
    assert old_after is not None and old_after.status == "deprecated"
    assert new_after is not None and new_after.status == "active"


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
    assert conflicts_body["result"]["count"] == 0
    assert conflicts_body["result"]["related_overlap_count"] == 0
    assert conflicts_body["result"]["related_overlaps"] == []
    assert conflicts_body["result"]["review_candidates"] == []

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

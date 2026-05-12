import json

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session

from app.config import Settings
from app.llm.provider import (
    LLMMessage,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolRunner,
    LLMToolUse,
)
from app.main import create_app
from app.storage import repositories


class FakeChatProvider:
    seen_chat_systems: list[str | None] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=f"text:{prompt}",
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        self.__class__.seen_chat_systems.append(system)
        last_message = messages[-1]
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=f"assistant:{last_message.content}:history={len(messages)}",
            usage={"input_tokens": len(messages), "output_tokens": 3},
            provider_message_id="provider_msg_1",
            raw_content=[
                {
                    "type": "text",
                    "text": f"assistant:{last_message.content}:history={len(messages)}",
                }
            ],
            stop_reason="end_turn",
        )

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
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
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ):
        result = self.generate_chat(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
        )
        yield LLMStreamEvent(type="text_delta", data={"text": result.text})
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class FakeToolCallingProvider(FakeChatProvider):
    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ) -> LLMTextResult:
        executed = tool_runner(
            LLMToolUse(
                id="toolu_schema",
                name="mind_api",
                input={
                    "method": "GET",
                    "path": "/mind/schema",
                    "intent": "Inspect schema before answering.",
                },
            )
        )
        return LLMTextResult(
            model=self.settings.minimax_model,
            text="I inspected the Mind API schema.",
            usage={"input_tokens": 10, "output_tokens": 5},
            provider_message_id="provider_msg_tool_loop",
            raw_content=[
                {
                    "type": "text",
                    "text": "I inspected the Mind API schema.",
                }
            ],
            stop_reason="end_turn",
            tool_calls=[executed],
            raw_provider_messages=[
                {
                    "id": "provider_msg_tool_loop",
                    "stop_reason": "end_turn",
                    "content": [
                        {
                            "type": "text",
                            "text": "I inspected the Mind API schema.",
                        }
                    ],
                }
            ],
        )

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ):
        yield LLMStreamEvent(
            type="thinking_delta",
            data={"text": "I should inspect the schema."},
        )
        yield LLMStreamEvent(
            type="tool_input_delta",
            data={"partial_json": '{"method":"GET","path":"/mind/schema"'},
        )
        executed = tool_runner(
            LLMToolUse(
                id="toolu_schema",
                name="mind_api",
                input={
                    "method": "GET",
                    "path": "/mind/schema",
                    "intent": "Inspect schema before answering.",
                },
            )
        )
        yield LLMStreamEvent(
            type="tool_call",
            data={
                "provider_tool_use_id": executed.provider_tool_use_id,
                "tool_name": executed.tool_name,
                "arguments": executed.arguments,
            },
        )
        yield LLMStreamEvent(type="tool_result", data=executed.model_dump(mode="json"))
        yield LLMStreamEvent(type="text_delta", data={"text": "Schema inspected."})
        yield LLMStreamEvent(
            type="final_result",
            data={
                "result": LLMTextResult(
                    model=self.settings.minimax_model,
                    text="Schema inspected.",
                    usage={"input_tokens": 12, "output_tokens": 4},
                    provider_message_id="provider_msg_stream",
                    raw_content=[{"type": "text", "text": "Schema inspected."}],
                    stop_reason="end_turn",
                    tool_calls=[executed],
                    raw_provider_messages=[
                        {
                            "id": "provider_msg_stream",
                            "stop_reason": "end_turn",
                            "content": [{"type": "text", "text": "Schema inspected."}],
                        }
                    ],
                ).model_dump(mode="json")
            },
        )


class FakeMemoryProvider(FakeChatProvider):
    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ) -> LLMTextResult:
        write = tool_runner(
            LLMToolUse(
                id="toolu_memory_write",
                name="mind_api",
                input={
                    "method": "POST",
                    "path": "/mind/memory/write",
                    "body": {
                        "type": "user_preference",
                        "content": (
                            "The owner prefers SAL updates with risks and next steps."
                        ),
                        "reason_for_storage": (
                            "Stable communication preference for future status updates."
                        ),
                        "expected_future_use": "Shape future SAL answers.",
                        "confidence": 0.9,
                        "salience": 0.8,
                        "scope": "project",
                        "tags": ["sal", "status"],
                    },
                    "intent": "Persist a stable project communication preference.",
                },
            )
        )
        search = tool_runner(
            LLMToolUse(
                id="toolu_memory_search",
                name="mind_api",
                input={
                    "method": "POST",
                    "path": "/mind/memory/search",
                    "body": {
                        "query": "SAL risks next steps",
                        "types": ["user_preference"],
                        "scope": "project",
                        "top_k": 3,
                    },
                    "intent": "Retrieve the stored project communication preference.",
                },
            )
        )
        return LLMTextResult(
            model=self.settings.minimax_model,
            text="Memory stored and retrieved.",
            usage={"input_tokens": 20, "output_tokens": 5},
            provider_message_id="provider_msg_memory_loop",
            raw_content=[{"type": "text", "text": "Memory stored and retrieved."}],
            stop_reason="end_turn",
            tool_calls=[write, search],
            raw_provider_messages=[
                {
                    "id": "provider_msg_memory_loop",
                    "stop_reason": "end_turn",
                    "content": [
                        {"type": "text", "text": "Memory stored and retrieved."}
                    ],
                }
            ],
        )


def make_client(db_engine: Engine) -> TestClient:
    FakeChatProvider.seen_chat_systems = []
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
            llm_provider_factory=lambda settings: FakeChatProvider(settings),
            db_engine=db_engine,
        )
    )


def make_tool_client(db_engine: Engine) -> TestClient:
    FakeChatProvider.seen_chat_systems = []
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
            llm_provider_factory=lambda settings: FakeToolCallingProvider(settings),
            db_engine=db_engine,
        )
    )


def make_memory_client(db_engine: Engine) -> TestClient:
    FakeChatProvider.seen_chat_systems = []
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
            llm_provider_factory=lambda settings: FakeMemoryProvider(settings),
            db_engine=db_engine,
        )
    )


def add_project_memory(
    db_engine: Engine,
    *,
    content: str,
    tags: list[str] | None = None,
) -> str:
    with Session(db_engine) as db:
        memory = repositories.add_memory(
            db,
            memory_type="project_fact",
            content=content,
            reason_for_storage="Project protocol detail used for memory context tests.",
            expected_future_use="Retrieve protocol details during future chat turns.",
            confidence=0.9,
            salience=0.85,
            scope="project",
            tags=tags or [],
        )
        return memory.id


def test_chat_turn_persists_messages_and_traces(db_engine: Engine) -> None:
    client = make_client(db_engine)

    session_response = client.post(
        "/api/chat/sessions",
        json={"title": "Baseline", "metadata": {"source": "test"}},
    )
    assert session_response.status_code == 200
    session = session_response.json()

    turn_response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "hello"},
    )

    assert turn_response.status_code == 200
    turn = turn_response.json()
    assert turn["status"] == "completed"
    assert turn["model"] == "MiniMax-M2.7"
    assert turn["usage"] == {"input_tokens": 1, "output_tokens": 3}
    assert turn["user_message"]["content"] == "hello"
    assert turn["assistant_message"]["content"] == "assistant:hello:history=1"
    assert len(turn["trace_ids"]) == 3

    messages_response = client.get(f"/api/chat/sessions/{session['id']}/messages")
    assert messages_response.status_code == 200
    messages = messages_response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [message["content"] for message in messages] == [
        "hello",
        "assistant:hello:history=1",
    ]

    traces_response = client.get(f"/api/debug/traces/{turn['turn_id']}")
    assert traces_response.status_code == 200
    traces = traces_response.json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "llm.request",
        "llm.response",
    ]
    memory_context = traces[0]["payload"]
    assert memory_context["searched"] is True
    assert memory_context["selected"] == []
    assert memory_context["negative_evidence"] == "no_relevant_memory_selected"
    request_trace = traces[1]["payload"]
    assert request_trace["max_tokens"] == 4096
    assert request_trace["system_present"] is True
    assert request_trace["system_source"] == "bundled"
    assert request_trace["runtime_context_present"] is True
    assert request_trace["memory_context_trace_id"] == traces[0]["id"]
    assert "<runtime_context>" in request_trace["system"]
    assert "You are Scarlet" in request_trace["base_system"]
    assert "LLM API Mind" in request_trace["base_system"]
    assert "feminine agent identity" in request_trace["base_system"]
    assert "sono pronta" in request_trace["base_system"]
    assert "mind_api" in request_trace["base_system"]
    assert "Visible Metacognition Experiment" in request_trace["base_system"]
    assert "Metacognizione:" in request_trace["base_system"]
    assert "medical" not in request_trace["base_system"].lower()
    assert "diagnostic" not in request_trace["base_system"].lower()
    assert FakeChatProvider.seen_chat_systems[-1] == request_trace["system"]
    assert request_trace["messages"][0]["content"] == "hello"
    assert traces[2]["payload"]["provider_message_id"] == "provider_msg_1"


def test_chat_turn_can_override_system_prompt(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()
    custom_system = "You are a test-only identity."

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "hello", "system": custom_system},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    request_trace = traces[1]["payload"]
    assert traces[0]["kind"] == "memory.context"
    assert request_trace["base_system"] == custom_system
    assert request_trace["system"].startswith(custom_system)
    assert "<runtime_context>" in request_trace["system"]
    assert request_trace["system_source"] == "request"
    assert FakeChatProvider.seen_chat_systems[-1] == request_trace["system"]


def test_second_chat_turn_uses_persisted_history(db_engine: Engine) -> None:
    client = make_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    first_turn = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "first"},
    )
    assert first_turn.status_code == 200

    second_turn = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "second"},
    )

    assert second_turn.status_code == 200
    body = second_turn.json()
    assert body["assistant_message"]["content"] == "assistant:second:history=3"


def test_chat_turn_selects_relevant_memory_context(db_engine: Engine) -> None:
    client = make_client(db_engine)
    memory_id = add_project_memory(
        db_engine,
        content=(
            "Il protocollo Zero-Luce usa memoria automatica per verificare "
            "continuita e fonte prima della risposta."
        ),
        tags=["zero-luce", "protocollo"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Cosa sai di Zero-Luce?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected_count"] == 1
    assert memory_context["selected"][0]["id"] == memory_id
    assert memory_context["selected"][0]["classification"] == "selected"
    request_trace = traces[1]["payload"]
    assert memory_id in request_trace["runtime_context"]
    assert "Zero-Luce" in request_trace["system"]


def test_chat_turn_excludes_weak_memory_overlap(db_engine: Engine) -> None:
    client = make_client(db_engine)
    memory_id = add_project_memory(
        db_engine,
        content=(
            "Il protocollo Zero-Luce richiede attribuzione alla memoria "
            "persistente quando viene recuperato."
        ),
        tags=[],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Cosa sai del protocollo Mare-Vetro?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected"] == []
    assert memory_context["selected_count"] == 0
    assert [item["id"] for item in memory_context["excluded"]] == [memory_id]
    assert memory_context["excluded"][0]["signals"]["generic_overlap"] == [
        "protocollo"
    ]


def test_chat_turn_dispatches_and_traces_mind_api_tool_call(
    db_engine: Engine,
) -> None:
    client = make_tool_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "inspect schema first"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["content"] == "I inspected the Mind API schema."
    assert len(body["trace_ids"]) == 4

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "llm.request",
        "mind.tool_call",
        "llm.response",
    ]
    assert traces[1]["payload"]["tools"][0]["name"] == "mind_api"
    assert traces[1]["payload"]["memory_context_trace_id"] == traces[0]["id"]
    tool_trace = traces[2]
    assert tool_trace["payload"]["tool_name"] == "mind_api"
    assert tool_trace["payload"]["arguments"]["path"] == "/mind/schema"
    assert tool_trace["payload"]["result"]["ok"] is True
    response_trace = traces[3]
    assert response_trace["payload"]["tool_calls"][0]["tool_name"] == "mind_api"
    assert (
        response_trace["payload"]["tool_calls"][0]["trace_id"]
        == tool_trace["id"]
    )


def test_chat_turn_dispatches_traceable_memory_write_and_search(
    db_engine: Engine,
) -> None:
    client = make_memory_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "store and retrieve memory"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["assistant_message"]["content"] == "Memory stored and retrieved."
    assert len(body["trace_ids"]) == 7

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "llm.request",
        "mind.memory.write",
        "mind.tool_call",
        "mind.memory.search",
        "mind.tool_call",
        "llm.response",
    ]
    write_trace = traces[2]
    assert write_trace["payload"]["stored"] is True
    memory_id = write_trace["payload"]["memory_id"]
    assert memory_id.startswith("mem_")
    assert traces[3]["payload"]["arguments"]["path"] == "/mind/memory/write"
    assert traces[3]["payload"]["result"]["result"]["trace_ids"] == [write_trace["id"]]
    assert traces[4]["payload"]["returned_memory_ids"] == [memory_id]
    assert traces[5]["payload"]["arguments"]["path"] == "/mind/memory/search"
    assert traces[6]["payload"]["tool_calls"][0]["tool_name"] == "mind_api"
    assert traces[6]["payload"]["tool_calls"][1]["tool_name"] == "mind_api"


def test_streaming_chat_turn_emits_agentic_events_and_persists_traces(
    db_engine: Engine,
) -> None:
    client = make_tool_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream",
        json={"message": "inspect schema first"},
    ) as response:
        assert response.status_code == 200
        events = [line for line in response.iter_lines() if line]

    decoded_events = [json.loads(line) for line in events]
    event_types = [event["type"] for event in decoded_events]
    assert event_types == [
        "turn_started",
        "memory_context",
        "thinking_delta",
        "tool_input_delta",
        "tool_call",
        "tool_result",
        "text_delta",
        "turn_complete",
    ]
    event_data = [event["data"] for event in decoded_events]
    assert [data["seq"] for data in event_data] == list(range(1, len(event_data) + 1))
    assert {data["turn_id"] for data in event_data} == {event_data[0]["turn_id"]}

    complete = event_data[-1]
    assert complete["assistant_message"]["content"] == "Schema inspected."

    traces = client.get(f"/api/debug/traces/{complete['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "llm.request",
        "mind.tool_call",
        "llm.response",
    ]
    assert event_data[1]["searched"] is True
    assert event_data[1]["selected_count"] == 0
    assert traces[3]["payload"]["stream"] is True


def test_chat_turn_returns_404_for_missing_session(db_engine: Engine) -> None:
    client = make_client(db_engine)

    response = client.post(
        "/api/chat/sessions/ses_missing/turn",
        json={"message": "hello"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "session.not_found"


def test_chat_turn_returns_503_when_provider_is_not_configured(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key=None,
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
    )
    client = TestClient(create_app(settings, db_engine=db_engine))
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "hello"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "llm.not_configured"

import json

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.config import Settings
from app.llm.provider import (
    LLMMessage,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolRunner,
    LLMToolUse,
)
from app.main import create_app


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
    assert len(turn["trace_ids"]) == 2

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
    assert [trace["kind"] for trace in traces] == ["llm.request", "llm.response"]
    assert traces[0]["payload"]["max_tokens"] == 4096
    assert traces[0]["payload"]["system_present"] is True
    assert traces[0]["payload"]["system_source"] == "bundled"
    assert "You are Scarlet" in traces[0]["payload"]["system"]
    assert "LLM API Mind" in traces[0]["payload"]["system"]
    assert "feminine agent identity" in traces[0]["payload"]["system"]
    assert "sono pronta" in traces[0]["payload"]["system"]
    assert "mind_api" in traces[0]["payload"]["system"]
    assert "medical" not in traces[0]["payload"]["system"].lower()
    assert "diagnostic" not in traces[0]["payload"]["system"].lower()
    assert FakeChatProvider.seen_chat_systems[-1] == traces[0]["payload"]["system"]
    assert traces[0]["payload"]["messages"][0]["content"] == "hello"
    assert traces[1]["payload"]["provider_message_id"] == "provider_msg_1"


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
    assert traces[0]["payload"]["system"] == custom_system
    assert traces[0]["payload"]["system_source"] == "request"
    assert FakeChatProvider.seen_chat_systems[-1] == custom_system


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
    assert len(body["trace_ids"]) == 3

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "llm.request",
        "mind.tool_call",
        "llm.response",
    ]
    assert traces[0]["payload"]["tools"][0]["name"] == "mind_api"
    tool_trace = traces[1]
    assert tool_trace["payload"]["tool_name"] == "mind_api"
    assert tool_trace["payload"]["arguments"]["path"] == "/mind/schema"
    assert tool_trace["payload"]["result"]["ok"] is True
    response_trace = traces[2]
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
    assert len(body["trace_ids"]) == 6

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "llm.request",
        "mind.memory.write",
        "mind.tool_call",
        "mind.memory.search",
        "mind.tool_call",
        "llm.response",
    ]
    write_trace = traces[1]
    assert write_trace["payload"]["stored"] is True
    memory_id = write_trace["payload"]["memory_id"]
    assert memory_id.startswith("mem_")
    assert traces[2]["payload"]["arguments"]["path"] == "/mind/memory/write"
    assert traces[2]["payload"]["result"]["result"]["trace_ids"] == [write_trace["id"]]
    assert traces[3]["payload"]["returned_memory_ids"] == [memory_id]
    assert traces[4]["payload"]["arguments"]["path"] == "/mind/memory/search"
    assert traces[5]["payload"]["tool_calls"][0]["tool_name"] == "mind_api"
    assert traces[5]["payload"]["tool_calls"][1]["tool_name"] == "mind_api"


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
        "llm.request",
        "mind.tool_call",
        "llm.response",
    ]
    assert traces[2]["payload"]["stream"] is True


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

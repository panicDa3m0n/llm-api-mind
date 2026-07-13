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
    seen_max_tool_calls: list[int | None] = []
    seen_chat_messages: list[list[LLMMessage]] = []

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
        self.__class__.seen_chat_messages.append(messages)
        last_message = messages[-1]
        last_text = _message_text(last_message.content)
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=f"assistant:{last_text}:history={len(messages)}",
            usage={"input_tokens": len(messages), "output_tokens": 3},
            provider_message_id="provider_msg_1",
            raw_content=[
                {
                    "type": "text",
                    "text": f"assistant:{last_text}:history={len(messages)}",
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
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        self.__class__.seen_max_tool_calls.append(max_tool_calls)
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
        max_tool_calls: int | None = None,
    ):
        self.__class__.seen_max_tool_calls.append(max_tool_calls)
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


class FakeOpenRouterRetrievalClient:
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
        return [_fake_embedding(text) for text in texts]

    def rerank(
        self,
        *,
        model: str,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> dict:
        scored = [
            {
                "index": index,
                "relevance_score": 0.99 if "cacao" in document.casefold() else 0.21,
            }
            for index, document in enumerate(documents)
        ]
        scored.sort(key=lambda item: item["relevance_score"], reverse=True)
        return {"results": scored[:top_n], "provider": "fake-openrouter"}


def _fake_embedding(text: str) -> list[float]:
    lowered = text.casefold()
    if (
        "cacao" in lowered
        or "bevanda" in lowered
        or "caffe" in lowered
        or "concentr" in lowered
    ):
        return [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    if "hiking" in lowered or "camminata" in lowered:
        return [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    return [0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25]


class FakeToolCallingProvider(FakeChatProvider):
    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict],
        tool_runner: LLMToolRunner,
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        self.__class__.seen_max_tool_calls.append(max_tool_calls)
        self.__class__.seen_chat_messages.append(messages)
        executed = tool_runner(
            LLMToolUse(
                id="toolu_schema",
                name="mind_shell",
                input={
                    "command": "help",
                    "intent": "Inspect shell help before answering.",
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
                    "id": "provider_msg_tool_use",
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "I should inspect the schema.",
                            "signature": "test-signature",
                        },
                        {
                            "type": "text",
                            "text": "I will inspect the schema before answering.",
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_schema",
                            "name": "mind_shell",
                            "input": {
                                "command": "help",
                                "intent": "Inspect shell help before answering.",
                            },
                        },
                    ],
                },
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
        max_tool_calls: int | None = None,
    ):
        self.__class__.seen_max_tool_calls.append(max_tool_calls)
        self.__class__.seen_chat_messages.append(messages)
        yield LLMStreamEvent(
            type="thinking_delta",
            data={"model_step": 1, "index": 0, "text": "I should inspect the schema."},
        )
        yield LLMStreamEvent(
            type="text_delta",
            data={
                "model_step": 1,
                "index": 1,
                "text": "I will inspect the schema before answering.",
            },
        )
        yield LLMStreamEvent(
            type="tool_input_delta",
            data={
                "model_step": 1,
                "index": 2,
                "partial_json": '{"command":"help"',
            },
        )
        yield LLMStreamEvent(
            type="thinking_captured",
            data={
                "model_step": 1,
                "index": 0,
                "provider_message_id": "provider_msg_stream_tool_use",
                "stop_reason": "tool_use",
                "text": "I should inspect the schema.",
                "has_text": True,
            },
        )
        yield LLMStreamEvent(
            type="assistant_note",
            data={
                "model_step": 1,
                "index": 1,
                "provider_message_id": "provider_msg_stream_tool_use",
                "stop_reason": "tool_use",
                "text": "I will inspect the schema before answering.",
            },
        )
        executed = tool_runner(
            LLMToolUse(
                id="toolu_schema",
                name="mind_shell",
                input={
                    "command": "help",
                    "intent": "Inspect shell help before answering.",
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
        yield LLMStreamEvent(
            type="text_delta",
            data={"model_step": 2, "index": 0, "text": "Schema inspected."},
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={
                "model_step": 2,
                "index": 0,
                "provider_message_id": "provider_msg_stream",
                "stop_reason": "end_turn",
                "text": "Schema inspected.",
            },
        )
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
                            "id": "provider_msg_stream_tool_use",
                            "stop_reason": "tool_use",
                            "content": [
                                {
                                    "type": "thinking",
                            "thinking": "I should inspect the schema.",
                            "signature": "test-signature",
                        },
                        {
                            "type": "text",
                            "text": "I will inspect the schema before answering.",
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_schema",
                                    "name": "mind_shell",
                                    "input": {
                                        "command": "help",
                                        "intent": "Inspect shell help before answering.",
                                    },
                                },
                            ],
                        },
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
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        self.__class__.seen_max_tool_calls.append(max_tool_calls)
        self.__class__.seen_chat_messages.append(messages)
        write = tool_runner(
            LLMToolUse(
                id="toolu_memory_write",
                name="mind_shell",
                input={
                    "command": (
                        'memory write --type user_preference --scope project '
                        '--content "The owner prefers SAL updates with risks and next steps." '
                        '--reason "Stable communication preference for future status updates." '
                        '--future-use "Shape future SAL answers."'
                    ),
                    "intent": "Persist a stable project communication preference.",
                },
            )
        )
        search = tool_runner(
            LLMToolUse(
                id="toolu_memory_search",
                name="mind_shell",
                input={
                    "command": (
                        'memory search "SAL risks next steps" '
                        '--type user_preference --scope project --top 3'
                    ),
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
                    "id": "provider_msg_memory_tools",
                    "stop_reason": "tool_use",
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "I should write and verify the memory.",
                            "signature": "test-signature",
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_memory_write",
                            "name": "mind_shell",
                            "input": {
                                "command": "memory write ...",
                            },
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_memory_search",
                            "name": "mind_shell",
                            "input": {
                                "command": "memory search ...",
                            },
                        },
                    ],
                },
                {
                    "id": "provider_msg_memory_loop",
                    "stop_reason": "end_turn",
                    "content": [
                        {"type": "text", "text": "Memory stored and retrieved."}
                    ],
                }
            ],
        )


def make_client(db_engine: Engine, settings_overrides: dict | None = None) -> TestClient:
    FakeChatProvider.seen_chat_systems = []
    FakeChatProvider.seen_max_tool_calls = []
    FakeChatProvider.seen_chat_messages = []
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
        **(settings_overrides or {}),
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
    FakeChatProvider.seen_max_tool_calls = []
    FakeChatProvider.seen_chat_messages = []
    FakeToolCallingProvider.seen_max_tool_calls = []
    FakeToolCallingProvider.seen_chat_messages = []
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
    FakeChatProvider.seen_max_tool_calls = []
    FakeChatProvider.seen_chat_messages = []
    FakeMemoryProvider.seen_max_tool_calls = []
    FakeMemoryProvider.seen_chat_messages = []
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


def add_user_memory(
    db_engine: Engine,
    *,
    content: str,
    reason_for_storage: str,
    expected_future_use: str,
    tags: list[str] | None = None,
) -> str:
    with Session(db_engine) as db:
        memory = repositories.add_memory(
            db,
            memory_type="user_preference",
            content=content,
            reason_for_storage=reason_for_storage,
            expected_future_use=expected_future_use,
            confidence=0.95,
            salience=0.85,
            scope="user",
            tags=tags or [],
        )
        return memory.id


def _message_text(content: str | list[dict]) -> str:
    if isinstance(content, str):
        return content
    return " ".join(
        str(block.get("text", ""))
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


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
    assert len(turn["trace_ids"]) == 8

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
        "metacognitive.context",
        "runtime.context",
        "model.context",
        "context.accounting.preflight",
        "llm.request",
        "llm.response",
        "context.accounting.observed",
    ]
    memory_context = traces[0]["payload"]
    metacognitive_context = traces[1]["payload"]
    assert metacognitive_context["mode"] == "shadow"
    assert metacognitive_context["model_facing"] is False
    assert metacognitive_context["selection"]["selected_count"] == 1
    assert memory_context["searched"] is True
    assert memory_context["selected"] == []
    assert memory_context["negative_evidence"] == "no_relevant_memory_selected"
    assert memory_context["temporal_context"]["timestamp_source"] == (
        "backend_turn_start"
    )
    assert memory_context["temporal_context"]["now"]
    assert memory_context["temporal_context"]["timezone"] == "Europe/Rome"
    assert "now_utc" not in memory_context["temporal_context"]
    runtime_context_trace = traces[2]["payload"]
    assert runtime_context_trace["schema_version"] == "runtime-context-v1"
    assert [block["type"] for block in runtime_context_trace["blocks"]] == [
        "session_context",
        "agent_mode_context",
        "message_context",
        "scarlet_state",
    ]
    model_context_trace = traces[3]["payload"]
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    assert request_trace["max_tokens"] == 4096
    assert request_trace["tool_loop_policy"] == "model_controlled_unbounded"
    assert request_trace["provider_history_source"] == "messages.text_reconstructed"
    assert request_trace["provider_message_stats"]["message_count"] == 1
    assert request_trace["provider_message_stats"]["content_block_count"] == 1
    assert request_trace["provider_messages"][0]["role"] == "user"
    assert request_trace["system_present"] is True
    assert request_trace["system_source"] == "bundled"
    assert request_trace["runtime_context_present"] is True
    assert request_trace["memory_context_trace_id"] == traces[0]["id"]
    assert request_trace["metacognitive_context_trace_id"] == traces[1]["id"]
    assert request_trace["metacognitive_context_mode"] == "shadow"
    assert request_trace["metacognitive_context_model_facing"] is False
    assert request_trace["runtime_context_trace_id"] == traces[2]["id"]
    assert request_trace["model_context_trace_id"] == traces[3]["id"]
    assert model_context_trace["document"]["schema_version"] == (
        "scarlet-model-context-v2"
    )
    assert "<runtime_context>" in request_trace["system"]
    runtime_payload = json.loads(
        request_trace["runtime_context"]
        .removeprefix("<runtime_context>\n")
        .removesuffix("\n</runtime_context>")
    )
    assert runtime_payload["schema_version"] == "scarlet-model-context-v2"
    assert runtime_payload == model_context_trace["document"]
    assert runtime_payload["session"]["user"] == {"name": "Utente locale"}
    assert runtime_payload["session"]["location"] == "Italia"
    assert runtime_payload["session"]["timezone"]["id"] == "Europe/Rome"
    assert set(runtime_payload["memories"]) == {
        "relevant",
        "recent_user",
        "recent_general",
    }
    assert "You are Scarlet" in request_trace["base_system"]
    assert "LLM API Mind" in request_trace["base_system"]
    assert "digital individual in development" in request_trace["base_system"]
    assert "sono pronta" in request_trace["base_system"]
    assert "mind_shell" in request_trace["base_system"]
    assert "API Mind is your internal cognitive environment" in request_trace[
        "base_system"
    ]
    assert "use your digital brain" in request_trace["base_system"]
    assert "Perception And Source Of Truth" in request_trace["base_system"]
    assert "runtime_context.session.now" in request_trace["base_system"]
    assert "There is no fixed cognitive step budget" in request_trace["base_system"]
    assert "Previous-Turn Continuity Check" in request_trace["base_system"]
    assert "include_inactive=true" in request_trace["base_system"]
    assert "Visible Metacognition Experiment" not in request_trace["base_system"]
    assert "Metacognizione:" not in request_trace["base_system"]
    assert "diagnostic assistant" not in request_trace["base_system"].lower()
    assert FakeChatProvider.seen_chat_systems[-1] == request_trace["system"]
    assert FakeChatProvider.seen_max_tool_calls[-1] is None
    assert request_trace["messages"][0]["content"] == "hello"
    response_trace = next(
        trace for trace in traces if trace["kind"] == "llm.response"
    )
    assert response_trace["payload"]["provider_message_id"] == "provider_msg_1"
    events_response = client.get(f"/api/debug/events?turn_id={turn['turn_id']}")
    assert events_response.status_code == 200
    events = events_response.json()
    assert [event["type"] for event in events] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "metacognitive.context.shadowed",
        "runtime.context.built",
        "llm.request.created",
        "llm.response.completed",
        "message.assistant.persisted",
        "assistant.answer.completed",
        "turn.completed",
        "maintenance.job.scheduled",
    ]
    assert [event["seq"] for event in events] == list(range(1, len(events) + 1))
    assert events[2]["payload"]["negative_evidence"] == "no_relevant_memory_selected"
    assert events[3]["payload"]["schema_version"] == (
        "metacognitive-context-shadow-v1"
    )
    assert events[4]["payload"]["schema_version"] == "runtime-context-v1"
    assert events[8]["payload"]["text"] == "assistant:hello:history=1"
    assert events[10]["payload"]["kind"] == "session.idle_maintenance"
    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        provider_history = stored_session.provider_history_json
    assert [item["role"] for item in provider_history] == ["user", "assistant"]
    assert provider_history[0]["content"] == [{"type": "text", "text": "hello"}]
    assert provider_history[1]["content"] == [
        {"type": "text", "text": "assistant:hello:history=1"}
    ]


def test_metacognitive_context_inject_mode_is_model_facing(
    db_engine: Engine,
) -> None:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
        metacognitive_context_mode="inject",
    )
    client = TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda settings: FakeChatProvider(settings),
            db_engine=db_engine,
        )
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Puoi verificare lo stato dei test?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    metacognitive_context = traces[1]["payload"]
    runtime_context = traces[2]["payload"]
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    runtime_payload = json.loads(
        request_trace["runtime_context"]
        .removeprefix("<runtime_context>\n")
        .removesuffix("\n</runtime_context>")
    )

    assert metacognitive_context["mode"] == "inject"
    assert metacognitive_context["model_facing"] is True
    assert request_trace["metacognitive_context_model_facing"] is True
    assert [block["type"] for block in runtime_context["blocks"]] == [
        "session_context",
        "agent_mode_context",
        "message_context",
        "scarlet_state",
        "metacognitive_context",
    ]
    assert any(
        block["type"] == "metacognitive_context"
        for block in runtime_payload["preserved_context"]
    )
    assert "source_sensitive_claim_guard" in request_trace["runtime_context"]


def test_chat_sessions_list_returns_recent_titles(db_engine: Engine) -> None:
    client = make_client(db_engine)

    first = client.post("/api/chat/sessions", json={"title": "First chat"}).json()
    second = client.post("/api/chat/sessions", json={"title": "Second chat"}).json()

    initial_response = client.get("/api/chat/sessions")
    assert initial_response.status_code == 200
    initial_sessions = initial_response.json()
    assert initial_sessions[0]["title"] == "Second chat"
    assert initial_sessions[1]["title"] == "First chat"

    turn_response = client.post(
        f"/api/chat/sessions/{first['id']}/turn",
        json={"message": "refresh first"},
    )
    assert turn_response.status_code == 200

    limited_response = client.get("/api/chat/sessions?limit=1")
    assert limited_response.status_code == 200
    sessions = limited_response.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == first["id"]
    assert sessions[0]["title"] == "First chat"


def test_dashboard_settings_control_runtime_context(db_engine: Engine) -> None:
    client = make_client(db_engine)

    initial = client.get("/api/dashboard/settings")
    assert initial.status_code == 200
    assert initial.json()["timezone"] == "Europe/Rome"
    assert initial.json()["language"] == "it"
    assert initial.json()["country_code"] == "IT"
    assert initial.json()["profile_id"] == "local-user"
    assert initial.json()["codex_test"] is False
    assert initial.json()["database"]["profile"] == "test"

    update = client.put(
        "/api/dashboard/settings",
        json={
            "timezone": "UTC",
            "language": "en",
            "country_code": "US",
            "profile_id": "research-owner",
            "user_display_name": "Research Owner",
            "privacy_scope": "private_user_profile",
        },
    )
    assert update.status_code == 200
    assert update.json()["timezone"] == "UTC"
    assert update.json()["language"] == "en"
    assert update.json()["country_code"] == "US"
    assert update.json()["profile_id"] == "research-owner"
    assert update.json()["user_display_name"] == "Research Owner"
    assert update.json()["privacy_scope"] == "private_user_profile"

    profile = client.get("/api/dashboard/profile")
    assert profile.status_code == 200
    assert profile.json()["profile_id"] == "research-owner"
    assert profile.json()["country_code"] == "US"
    assert profile.json()["privacy_scope"] == "private_user_profile"

    session = client.post("/api/chat/sessions", json={}).json()
    turn = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "hello"},
    ).json()
    traces = client.get(f"/api/debug/traces/{turn['turn_id']}").json()
    runtime_payload = traces[2]["payload"]
    message_context = next(
        block["content"]
        for block in runtime_payload["blocks"]
        if block["type"] == "message_context"
    )
    assert runtime_payload["temporal_context"]["timezone"] == "UTC"
    assert runtime_payload["temporal_context"]["now"].endswith("+00:00")
    assert message_context["current_message"]["language"]["code"] == "en"
    assert message_context["current_message"]["language"]["source"] == (
        "dashboard_settings"
    )
    assert message_context["world"]["location"]["country_code"] == "US"
    assert message_context["world"]["location"]["country"] == "Stati Uniti"
    assert message_context["user_profile"]["identity"]["profile_id"] == (
        "research-owner"
    )
    assert message_context["user_profile"]["identity"]["display_name"] == (
        "Research Owner"
    )
    assert message_context["user_profile"]["privacy"]["scope"] == (
        "private_user_profile"
    )


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
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    assert traces[0]["kind"] == "memory.context"
    assert traces[1]["kind"] == "metacognitive.context"
    assert traces[1]["payload"]["mode"] == "shadow"
    assert traces[1]["payload"]["model_facing"] is False
    assert traces[2]["kind"] == "runtime.context"
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
    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    assert request_trace["provider_history_source"] == "session.provider_history_json"
    assert request_trace["provider_message_stats"]["message_count"] == 3
    assert [message["role"] for message in request_trace["provider_messages"]] == [
        "user",
        "assistant",
        "user",
    ]
    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        provider_history = stored_session.provider_history_json
    assert [item["role"] for item in provider_history] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]


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
    assert "fts5_sparse_v1" in memory_context["query_plan"]["retrieval_stages"]
    assert "sparse_score" in memory_context["selected"][0]["signals"]
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    runtime_payload = json.loads(
        request_trace["runtime_context"]
        .removeprefix("<runtime_context>\n")
        .removesuffix("\n</runtime_context>")
    )
    assert runtime_payload["schema_version"] == "scarlet-model-context-v2"
    assert runtime_payload["memories"]["relevant"] == []
    assert memory_id not in request_trace["runtime_context"]
    assert memory_context["selected"][0]["content"] not in request_trace["system"]


def test_chat_turn_active_hybrid_selects_paraphrased_memory_context(
    db_engine: Engine,
    monkeypatch,
) -> None:
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
    cacao_memory_id = add_project_memory(
        db_engine,
        content="The owner prefers cacao tea during evening focus work.",
        tags=["cacao", "focus"],
    )
    add_project_memory(
        db_engine,
        content="The owner likes quiet hiking routes on weekends.",
        tags=["hiking", "weekend"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Che bevanda serale scelgo per concentrarmi senza caffe?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["query_plan"]["retrieval_hybrid"]["active"] is True
    assert memory_context["selected"][0]["id"] == cacao_memory_id
    assert memory_context["selected"][0]["signals"]["hybrid"]["dense_signal"] is True
    assert memory_context["selected"][0]["signals"]["hybrid"]["rerank_signal"] is True


def test_chat_turn_graph_expansion_selects_dynamic_personal_food_constraint(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    chocolate_memory_id = add_user_memory(
        db_engine,
        content=(
            "Adora il cioccolato ma non può mangiarne troppo: il corpo segnala "
            "un limite preciso, superata quella soglia sta male."
        ),
        reason_for_storage=(
            "Vincolo alimentare personale espresso dall'utente, rilevante per "
            "suggerimenti futuri su cibo, dolci e benessere."
        ),
        expected_future_use=(
            "Riferimento per raccomandazioni alimentari, suggerimenti, o "
            "qualsiasi contesto in cui il cioccolato possa venire in causa."
        ),
        tags=[
            "preferenza-alimentare",
            "cioccolato",
            "limite-salutare",
            "dato-personale",
        ],
    )
    noisy_project_memory_id = add_project_memory(
        db_engine,
        content=(
            "Scarlet deve riconoscere preferenze durevoli del progetto e "
            "consolidarle nella memoria semantica."
        ),
        tags=["preferenze", "progetto"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={
            "message": (
                "Mi ricordi il mio limite salutare sul cioccolato?"
            )
        },
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    selected_ids = [item["id"] for item in memory_context["selected"]]
    assert chocolate_memory_id in selected_ids
    assert noisy_project_memory_id not in selected_ids
    chocolate_item = next(
        item for item in memory_context["selected"] if item["id"] == chocolate_memory_id
    )
    assert "tag:limite_salutare" in chocolate_item["signals"]["graph"]["domains"]
    assert chocolate_item["signals"]["graph_score"] > 0
    assert memory_context["query_plan"]["retrieval_graph"]["backend"] == "networkx"
    assert memory_context["query_plan"]["retrieval_graph"]["results"]


def test_chat_turn_graph_expansion_does_not_treat_cooking_music_as_food_constraint(
    db_engine: Engine,
) -> None:
    client = make_client(db_engine)
    add_user_memory(
        db_engine,
        content=(
            "Adora il cioccolato ma non può mangiarne troppo: il corpo segnala "
            "un limite preciso, superata quella soglia sta male."
        ),
        reason_for_storage="Vincolo alimentare personale.",
        expected_future_use="Riferimento per raccomandazioni alimentari future.",
        tags=["preferenza-alimentare", "cioccolato", "limite-salutare"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={
            "message": (
                "Che playlist jazz notturna potrei mettere mentre cucino?"
            )
        },
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected"] == []
    assert memory_context["query_plan"]["retrieval_graph"]["status"] in {
        "completed",
        "no_query_seed",
        "no_memory_expansion",
    }
    assert memory_context["query_plan"]["retrieval_graph"]["results"] == []


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
    assert memory_id not in [item["id"] for item in memory_context["selected"]]
    assert memory_context["negative_evidence"] == "no_relevant_memory_selected"


def test_chat_turn_dispatches_and_traces_mind_shell_tool_call(
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
    assert len(body["trace_ids"]) == 9

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "metacognitive.context",
        "runtime.context",
        "model.context",
        "context.accounting.preflight",
        "llm.request",
        "mind.tool_call",
        "llm.response",
        "context.accounting.observed",
    ]
    assert traces[1]["payload"]["mode"] == "shadow"
    assert traces[1]["payload"]["model_facing"] is False
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    assert request_trace["payload"]["tools"][0]["name"] == "mind_shell"
    assert request_trace["payload"]["memory_context_trace_id"] == traces[0]["id"]
    assert request_trace["payload"]["metacognitive_context_trace_id"] == traces[1]["id"]
    assert request_trace["payload"]["runtime_context_trace_id"] == traces[2]["id"]
    assert request_trace["payload"]["tool_loop_policy"] == "model_controlled_unbounded"
    capabilities = traces[2]["payload"]["capabilities"]
    assert capabilities["interface"] == "mind_shell"
    assert capabilities["memory.facts.backfill"] == "internal_maintenance_only"
    assert capabilities["legacy_mind_endpoints"] == "internal_debug_maintenance_only"
    assert FakeToolCallingProvider.seen_max_tool_calls[-1] is None
    tool_trace = next(trace for trace in traces if trace["kind"] == "mind.tool_call")
    assert tool_trace["payload"]["tool_name"] == "mind_shell"
    assert tool_trace["payload"]["arguments"]["command"] == "help"
    assert tool_trace["payload"]["result"]["ok"] is True
    response_trace = next(trace for trace in traces if trace["kind"] == "llm.response")
    assert response_trace["payload"]["tool_calls"][0]["tool_name"] == "mind_shell"
    assert (
        response_trace["payload"]["tool_calls"][0]["trace_id"]
        == tool_trace["id"]
    )
    events = client.get(f"/api/debug/events?turn_id={body['turn_id']}").json()
    event_types = [event["type"] for event in events]
    assert "mind.tool_call.started" in event_types
    assert "mind.tool_call.completed" in event_types
    completed_event = next(
        event for event in events if event["type"] == "mind.tool_call.completed"
    )
    assert completed_event["trace_id"] == tool_trace["id"]
    assert completed_event["payload"]["operation"]["command"] == "help"
    assert completed_event["payload"]["result_summary"]["ok"] is True
    thinking_event = next(
        event for event in events if event["type"] == "llm.thinking.captured"
    )
    assert thinking_event["payload"]["text"] == "I should inspect the schema."
    assert thinking_event["payload"]["model_step"] == 1
    assert thinking_event["payload"]["index"] == 0
    note_event = next(
        event for event in events if event["type"] == "assistant.note.emitted"
    )
    assert note_event["payload"]["text"] == "I will inspect the schema before answering."
    assert note_event["payload"]["model_step"] == 1
    assert note_event["payload"]["index"] == 1
    answer_event = next(
        event for event in events if event["type"] == "assistant.answer.completed"
    )
    assert answer_event["payload"]["text"] == "I inspected the Mind API schema."
    assert answer_event["payload"]["model_step"] == 2
    assert answer_event["payload"]["index"] == 0
    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        provider_history = stored_session.provider_history_json
    assert [item["role"] for item in provider_history] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert provider_history[1]["content"][0]["type"] == "thinking"
    assert provider_history[1]["content"][1]["type"] == "text"
    assert provider_history[1]["content"][2]["type"] == "tool_use"
    assert provider_history[2]["content"][0]["type"] == "tool_result"
    assert provider_history[2]["content"][0]["tool_use_id"] == "toolu_schema"
    assert provider_history[3]["content"] == [
        {"type": "text", "text": "I inspected the Mind API schema."}
    ]


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
    assert len(body["trace_ids"]) == 12

    traces = client.get(f"/api/debug/traces/{body['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "metacognitive.context",
        "runtime.context",
        "model.context",
        "context.accounting.preflight",
        "llm.request",
        "mind.memory.write",
        "mind.tool_call",
        "mind.memory.search",
        "mind.tool_call",
        "llm.response",
        "context.accounting.observed",
    ]
    write_trace = next(trace for trace in traces if trace["kind"] == "mind.memory.write")
    assert write_trace["payload"]["stored"] is True
    memory_id = write_trace["payload"]["memory_id"]
    assert memory_id.startswith("mem_")
    tool_traces = [trace for trace in traces if trace["kind"] == "mind.tool_call"]
    assert tool_traces[0]["payload"]["arguments"]["command"].startswith("memory write")
    assert tool_traces[0]["payload"]["result"]["result"]["data"]["trace_ids"] == [
        write_trace["id"]
    ]
    assert (
        tool_traces[0]["payload"]["result"]["result"]["data"]["memory"][
            "source_message_id"
        ]
        == body["user_message"]["id"]
    )
    search_trace = next(trace for trace in traces if trace["kind"] == "mind.memory.search")
    assert search_trace["payload"]["returned_memory_ids"] == [memory_id]
    assert tool_traces[1]["payload"]["arguments"]["command"].startswith("memory search")
    response_trace = next(trace for trace in traces if trace["kind"] == "llm.response")
    assert response_trace["payload"]["tool_calls"][0]["tool_name"] == "mind_shell"
    assert response_trace["payload"]["tool_calls"][1]["tool_name"] == "mind_shell"
    assert FakeMemoryProvider.seen_max_tool_calls[-1] is None
    events = client.get(f"/api/debug/events?turn_id={body['turn_id']}").json()
    completed_tool_events = [
        event for event in events if event["type"] == "mind.tool_call.completed"
    ]
    assert len(completed_tool_events) == 2
    assert [
        event["payload"]["operation"]["command"].split(" ", 2)[:2]
        for event in completed_tool_events
    ] == [
        ["memory", "write"],
        ["memory", "search"],
    ]


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
    assert event_types[0] == "turn_started"
    assert "memory_context" in event_types
    assert "metacognitive_context" in event_types
    assert "runtime_event" in event_types
    assert "thinking_delta" in event_types
    assert "tool_input_delta" in event_types
    assert "tool_call" in event_types
    assert "tool_result" in event_types
    assert "text_delta" in event_types
    assert event_types[-1] == "turn_complete"
    event_data = [event["data"] for event in decoded_events]
    assert [data["seq"] for data in event_data] == list(range(1, len(event_data) + 1))
    assert {data["turn_id"] for data in event_data} == {event_data[0]["turn_id"]}
    live_runtime_events = [
        event["data"]["event"]
        for event in decoded_events
        if event["type"] == "runtime_event"
    ]
    live_runtime_event_types = [event["type"] for event in live_runtime_events]
    assert live_runtime_event_types[:5] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "metacognitive.context.shadowed",
        "runtime.context.built",
    ]
    assert live_runtime_event_types[:6] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "metacognitive.context.shadowed",
        "runtime.context.built",
        "llm.request.created",
    ]
    assert "mind.tool_call.started" in live_runtime_event_types
    assert "mind.tool_call.completed" in live_runtime_event_types
    assert "mind.tool_call.requested" in live_runtime_event_types
    assert "mind.tool_call.result_returned" in live_runtime_event_types
    assert "assistant.answer.completed" in live_runtime_event_types
    assert live_runtime_event_types[-2:] == [
        "turn.completed",
        "maintenance.job.scheduled",
    ]

    complete = event_data[-1]
    assert complete["assistant_message"]["content"] == "Schema inspected."

    traces = client.get(f"/api/debug/traces/{complete['turn_id']}").json()
    assert [trace["kind"] for trace in traces] == [
        "memory.context",
        "metacognitive.context",
        "runtime.context",
        "model.context",
        "context.accounting.preflight",
        "llm.request",
        "mind.tool_call",
        "llm.response",
        "context.accounting.observed",
    ]
    memory_event = next(event for event in decoded_events if event["type"] == "memory_context")
    assert memory_event["data"]["searched"] is True
    assert memory_event["data"]["selected_count"] == 0
    metacognitive_event = next(
        event for event in decoded_events if event["type"] == "metacognitive_context"
    )
    assert metacognitive_event["data"]["mode"] == "shadow"
    assert metacognitive_event["data"]["model_facing"] is False
    runtime_event = next(event for event in decoded_events if event["type"] == "runtime_context")
    assert runtime_event["data"]["schema_version"] == "runtime-context-v1"
    assert len(runtime_event["data"]["blocks"]) == 4
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    assert request_trace["payload"]["tool_loop_policy"] == "model_controlled_unbounded"
    assert request_trace["payload"]["provider_history_source"] == (
        "messages.text_reconstructed"
    )
    assert request_trace["payload"]["stream"] is True
    assert FakeToolCallingProvider.seen_max_tool_calls[-1] is None
    persisted_events = client.get(
        f"/api/debug/events?turn_id={complete['turn_id']}"
    ).json()
    persisted_event_types = [event["type"] for event in persisted_events]
    assert "mind.tool_call.started" in persisted_event_types
    assert "mind.tool_call.completed" in persisted_event_types
    assert "mind.tool_call.requested" in persisted_event_types
    assert "mind.tool_call.result_returned" in persisted_event_types
    persisted_thinking = next(
        event for event in persisted_events if event["type"] == "llm.thinking.captured"
    )
    assert persisted_thinking["payload"]["text"] == "I should inspect the schema."
    assert persisted_thinking["payload"]["model_step"] == 1
    assert persisted_thinking["payload"]["index"] == 0
    assert persisted_event_types[-2:] == [
        "turn.completed",
        "maintenance.job.scheduled",
    ]
    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        provider_history = stored_session.provider_history_json
    assert [item["role"] for item in provider_history] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert provider_history[1]["content"][1]["type"] == "text"
    assert provider_history[1]["content"][2]["type"] == "tool_use"
    assert provider_history[2]["content"][0]["type"] == "tool_result"


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

import json
from hashlib import sha256

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
from app.runtime.history_compaction import build_chronology_source_map
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
                },
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
                        },
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
                        "memory write --type user_preference --scope project "
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
                        "--type user_preference --scope project --top 3"
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
                },
            ],
        )


class FakeThinkingOnlyProvider(FakeChatProvider):
    @staticmethod
    def _result(model: str) -> LLMTextResult:
        return LLMTextResult(
            model=model,
            text="",
            usage={"input_tokens": 8, "output_tokens": 5},
            provider_message_id="provider_thinking_only",
            raw_content=[
                {
                    "type": "thinking",
                    "thinking": "I should answer, but this message has no public text.",
                    "signature": "test-signature",
                }
            ],
            stop_reason="end_turn",
            raw_provider_messages=[
                {
                    "id": "provider_thinking_only",
                    "stop_reason": "end_turn",
                    "content": [
                        {
                            "type": "thinking",
                            "thinking": "I should answer, but this message has no public text.",
                            "signature": "test-signature",
                        }
                    ],
                }
            ],
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
        return self._result(self.settings.minimax_model)

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
        result = self._result(self.settings.minimax_model)
        yield LLMStreamEvent(
            type="thinking_captured",
            data={
                "model_step": 1,
                "index": 0,
                "provider_message_id": result.provider_message_id,
                "stop_reason": result.stop_reason,
                "text": result.raw_content[0]["thinking"],
                "has_text": True,
            },
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class FakeAnswerBoundaryRecoveryProvider(FakeChatProvider):
    calls = 0

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
        del messages, system, max_tokens, tools, tool_runner, max_tool_calls
        self.__class__.calls += 1
        if self.__class__.calls == 1:
            text = "Controllo un momento e poi ti rispondo."
            provider_message_id = "provider_progress_only"
        else:
            text = "Eccomi, ho concluso la risposta."
            provider_message_id = "provider_corrected_final"
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            usage={"input_tokens": 10, "output_tokens": 5},
            provider_message_id=provider_message_id,
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            raw_provider_messages=[
                {
                    "id": provider_message_id,
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        )

    def stream_chat_with_tools(self, **_kwargs):
        self.__class__.calls = 1
        text = "Controllo un momento e poi ti rispondo."
        result = LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            provider_message_id="provider_progress_only",
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            raw_provider_messages=[
                {
                    "id": "provider_progress_only",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        )
        yield LLMStreamEvent(
            type="text_delta",
            data={"model_step": 1, "index": 0, "text": text},
        )
        yield LLMStreamEvent(
            type="assistant_answer",
            data={
                "model_step": 1,
                "index": 0,
                "provider_message_id": result.provider_message_id,
                "stop_reason": result.stop_reason,
                "text": text,
            },
        )
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )


class FakeAnswerBoundaryFailureProvider(FakeAnswerBoundaryRecoveryProvider):
    def generate_chat_with_tools(self, **kwargs) -> LLMTextResult:
        result = super().generate_chat_with_tools(**kwargs)
        text = "Sto ancora verificando."
        return result.model_copy(
            update={
                "text": text,
                "raw_content": [{"type": "text", "text": text}],
                "raw_provider_messages": [
                    {
                        "id": result.provider_message_id,
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}],
                    }
                ],
            }
        )

    def generate_text(self, *, prompt: str, **_kwargs) -> LLMTextResult:
        payload = json.loads(prompt)
        findings = [
            {
                "obligation_id": item["id"],
                "status": "fail",
                "reason": "The draft is still a progress note.",
            }
            for item in payload["obligations"]
        ]
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=json.dumps({"findings": findings}),
            provider_message_id="provider_finality_rejected",
            stop_reason="end_turn",
        )


class FakeMarkerlessConclusiveRecoveryProvider(FakeAnswerBoundaryRecoveryProvider):
    def generate_chat_with_tools(self, **kwargs) -> LLMTextResult:
        result = super().generate_chat_with_tools(**kwargs)
        if self.__class__.calls == 1:
            return result
        text = "Eccomi, ho concluso la risposta senza dipendere dalla nota precedente."
        return result.model_copy(
            update={
                "text": text,
                "raw_content": [{"type": "text", "text": text}],
                "raw_provider_messages": [
                    {
                        "id": result.provider_message_id,
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": text}],
                    }
                ],
            }
        )

    def generate_text(self, *, prompt: str, **_kwargs) -> LLMTextResult:
        payload = json.loads(prompt)
        findings = [
            {
                "obligation_id": item["id"],
                "status": "pass",
                "reason": "The corrected draft is complete and conclusive.",
            }
            for item in payload["obligations"]
        ]
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=json.dumps({"findings": findings}),
            provider_message_id="provider_finality_accepted",
            stop_reason="end_turn",
        )


class FakeEmptyCorrectedBoundaryProvider(FakeAnswerBoundaryRecoveryProvider):
    def generate_chat_with_tools(self, **kwargs) -> LLMTextResult:
        result = super().generate_chat_with_tools(**kwargs)
        if self.__class__.calls == 1:
            return result
        return result.model_copy(
            update={
                "text": "",
                "raw_content": [],
                "raw_provider_messages": [
                    {
                        "id": result.provider_message_id,
                        "stop_reason": "end_turn",
                        "content": [],
                    }
                ],
            }
        )


class FakeSemanticAnswerRecoveryProvider(FakeAnswerBoundaryRecoveryProvider):
    def generate_chat_with_tools(self, **_kwargs) -> LLMTextResult:
        self.__class__.calls += 1
        if self.__class__.calls == 1:
            text = "È tutto verificato."
            provider_message_id = "provider_unsupported_claim"
        else:
            text = "Non ho evidenza sufficiente per confermarlo."
            provider_message_id = "provider_grounded_correction"
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            provider_message_id=provider_message_id,
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            raw_provider_messages=[
                {
                    "id": provider_message_id,
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        )

    def generate_text(self, *, prompt: str, **_kwargs) -> LLMTextResult:
        payload = json.loads(prompt)
        answer = str(payload["draft_answer"]).casefold()
        findings = [
            {
                "obligation_id": item["id"],
                "status": "pass" if "non ho evidenza" in answer else "fail",
                "reason": "Fixture semantic judgment.",
            }
            for item in payload["obligations"]
        ]
        return LLMTextResult(
            model="semantic-validator-test",
            text=json.dumps({"findings": findings}),
        )


class FakeRecoveredActionProvider(FakeChatProvider):
    memory_content = "Preferisce valutazioni qualitative prima dei punteggi."

    def _result_with_actions(
        self,
        tool_runner: LLMToolRunner,
    ) -> LLMTextResult:
        failed = tool_runner(
            LLMToolUse(
                id="toolu_failed_memory_write",
                name="mind_shell",
                input={
                    "command": "memory write",
                    "intent": "Remember the user's evaluation preference.",
                },
            )
        )
        succeeded = tool_runner(
            LLMToolUse(
                id="toolu_successful_memory_write",
                name="mind_shell",
                input={
                    "command": (
                        "memory write --type user_preference --scope user "
                        f"--content \"{self.memory_content}\" "
                        "--reason \"Future evaluation style\""
                    ),
                    "intent": "Remember the user's evaluation preference.",
                },
            )
        )
        text = "Ho salvato la preferenza dopo aver corretto il comando."
        return LLMTextResult(
            model=self.settings.minimax_model,
            text=text,
            provider_message_id="provider_recovered_action",
            raw_content=[{"type": "text", "text": text}],
            stop_reason="end_turn",
            tool_calls=[failed, succeeded],
            raw_provider_messages=[
                {
                    "id": "provider_recovered_action",
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}],
                }
            ],
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
        del messages, system, max_tokens, tools, max_tool_calls
        return self._result_with_actions(tool_runner)

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
        del messages, system, max_tokens, tools, max_tool_calls
        result = self._result_with_actions(tool_runner)
        yield LLMStreamEvent(
            type="final_result",
            data={"result": result.model_dump(mode="json")},
        )

    def generate_text(self, *, prompt: str, **_kwargs) -> LLMTextResult:
        payload = json.loads(prompt)
        if payload.get("task") != (
            "Evaluate the draft only against each listed obligation."
        ):
            return super().generate_text(prompt=prompt)
        findings = []
        for obligation in payload["obligations"]:
            evidence = obligation.get("evidence") or {}
            recovered = any(
                item.get("result_ok") is True
                for item in evidence.get("later_same_operation_attempts", [])
                if isinstance(item, dict)
            )
            findings.append(
                {
                    "obligation_id": obligation["id"],
                    "status": "pass" if recovered else "fail",
                    "reason": (
                        "The later same-intent memory write persisted successfully."
                        if recovered
                        else "No successful equivalent retry is present."
                    ),
                }
            )
        return LLMTextResult(
            model="semantic-validator-test",
            text=json.dumps({"findings": findings}),
        )


def make_client(
    db_engine: Engine, settings_overrides: dict | None = None
) -> TestClient:
    FakeChatProvider.seen_chat_systems = []
    FakeChatProvider.seen_max_tool_calls = []
    FakeChatProvider.seen_chat_messages = []
    overrides = settings_overrides or {}
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M2.7",
        minimax_max_tokens=4096,
        **overrides,
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


def make_thinking_only_client(db_engine: Engine) -> TestClient:
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M3",
        minimax_max_tokens=4096,
        maintenance_enabled=False,
    )
    return TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda active: FakeThinkingOnlyProvider(active),
            db_engine=db_engine,
        )
    )


def make_answer_boundary_client(
    db_engine: Engine,
    *,
    provider_class=FakeAnswerBoundaryRecoveryProvider,
) -> TestClient:
    provider_class.calls = 0
    settings = Settings(
        app_name="Test Mind",
        environment="test",
        minimax_api_key="test-key",
        minimax_model="MiniMax-M3",
        minimax_max_tokens=4096,
        maintenance_enabled=False,
    )
    return TestClient(
        create_app(
            settings,
            llm_provider_factory=lambda active: provider_class(active),
            db_engine=db_engine,
        )
    )
def add_project_memory(
    db_engine: Engine,
    *,
    content: str,
    tags: list[str] | None = None,
    with_provenance: bool = False,
) -> str:
    with Session(db_engine) as db:
        source_session_id: str | None = None
        source_turn_id: str | None = None
        source_message_id: str | None = None
        if with_provenance:
            source_session = repositories.create_chat_session(
                db,
                title="Memory source fixture",
            )
            source_turn = repositories.create_turn(
                db,
                session_id=source_session.id,
                model="test",
            )
            source_message = repositories.add_message(
                db,
                session_id=source_session.id,
                turn_id=source_turn.id,
                role="user",
                content=content,
            )
            repositories.add_message(
                db,
                session_id=source_session.id,
                turn_id=source_turn.id,
                role="assistant",
                content="Stored as a sourceable memory fixture.",
            )
            repositories.complete_turn(db, turn_id=source_turn.id)
            source_session_id = source_session.id
            source_turn_id = source_turn.id
            source_message_id = source_message.id
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
            source_session_id=source_session_id,
            source_turn_id=source_turn_id,
            source_message_id=source_message_id,
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
    assert metacognitive_context["selection"]["selected_count"] == 0
    assert metacognitive_context["policy"]["lexical_triggering"] is False
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
    mode_routing = runtime_context_trace["mode_routing"]
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
    model_context_trace = traces[3]["payload"]
    projection_audit = model_context_trace["projection_audit"]
    projection_by_family = {
        item["family"]: item for item in projection_audit["families"]
    }
    assert projection_audit["included_block_types"] == []
    assert projection_by_family["scarlet_state"]["source_present"] is True
    assert projection_by_family["scarlet_state"]["included_in_model"] is False
    assert projection_by_family["recent_dialogue"]["source_present"] is True
    assert projection_by_family["api_mind"]["disposition"] == "on_demand"
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
    assert "## Cognitive Conduct" in request_trace["base_system"]
    assert "## Evidence Discipline" in request_trace["base_system"]
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
    assert runtime_payload["preserved_context"] == []
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
    assert (
        "API Mind is your internal cognitive environment"
        in request_trace["base_system"]
    )
    assert "use your digital brain" in request_trace["base_system"]
    assert "Perception And Source Of Truth" in request_trace["base_system"]
    assert "runtime_context.session.now" in request_trace["base_system"]
    assert "fixed action budget:" in request_trace["base_system"]
    assert "Previous-Turn Continuity Check" in request_trace["base_system"]
    assert "include_inactive=true" in request_trace["base_system"]
    assert "Visible Metacognition Experiment" not in request_trace["base_system"]
    assert "Metacognizione:" not in request_trace["base_system"]
    assert "diagnostic assistant" not in request_trace["base_system"].lower()
    assert FakeChatProvider.seen_chat_systems[-1] == request_trace["system"]
    assert FakeChatProvider.seen_max_tool_calls[-1] is None
    assert request_trace["messages"][0]["content"] == "hello"
    response_trace = next(trace for trace in traces if trace["kind"] == "llm.response")
    assert response_trace["payload"]["provider_message_id"] == "provider_msg_1"
    events_response = client.get(f"/api/debug/events?turn_id={turn['turn_id']}")
    assert events_response.status_code == 200
    events = events_response.json()
    assert [event["type"] for event in events] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "memory.recent_context.built",
        "session.continuity.built",
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
    assert events[5]["payload"]["schema_version"] == (
        "metacognitive-context-observation-v2"
    )
    assert events[6]["payload"]["schema_version"] == "runtime-context-v1"
    assert events[10]["payload"]["text"] == "assistant:hello:history=1"
    assert events[12]["payload"]["kind"] == "session.idle_maintenance"
    with Session(db_engine) as db:
        stored_session = repositories.get_chat_session(db, session["id"])
        assert stored_session is not None
        provider_history = stored_session.provider_history_json
    assert [item["role"] for item in provider_history] == ["user", "assistant"]
    assert provider_history[0]["content"] == [{"type": "text", "text": "hello"}]
    assert provider_history[1]["content"] == [
        {"type": "text", "text": "assistant:hello:history=1"}
    ]


def test_metacognitive_context_does_not_inject_without_semantic_component(
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
    assert metacognitive_context["model_facing"] is False
    assert request_trace["metacognitive_context_model_facing"] is False
    assert [block["type"] for block in runtime_context["blocks"]] == [
        "session_context",
        "agent_mode_context",
        "message_context",
        "scarlet_state",
    ]
    assert not any(
        block["type"] == "metacognitive_context"
        for block in runtime_payload["preserved_context"]
    )
    assert "source_sensitive_claim_guard" not in request_trace["runtime_context"]


def test_chat_sessions_list_returns_recent_titles(db_engine: Engine) -> None:
    client = make_client(db_engine)

    first = client.post("/api/chat/sessions", json={"title": "First chat"}).json()
    client.post("/api/chat/sessions", json={"title": "Second chat"})

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


def test_dashboard_research_lab_lists_reads_and_deletes_artifacts(
    db_engine: Engine,
) -> None:
    client = make_client(
        db_engine,
        {"research_lab_enabled": True, "research_lab_runner_uds": "/tmp/lab.sock"},
    )
    with Session(db_engine) as db:
        session = repositories.create_chat_session(db, title="Laboratorio")
        run = repositories.create_research_lab_run(
            db,
            profile_id="local-user",
            session_id=session.id,
            turn_id="turn_lab_dashboard",
            action="python",
            intent="Preparare un risultato leggibile.",
            request={"code_sha256": "a" * 64},
        )
        repositories.complete_research_lab_run(
            db,
            run=run,
            result={"stdout": "risultato pronto\\n", "stderr": ""},
        )
        artifact = repositories.create_research_lab_artifact(
            db,
            run_id=run.id,
            profile_id="local-user",
            name="risultato.json",
            media_type="application/json",
            content_bytes=b'{"value": 42}',
            sha256="b" * 64,
        )

    listing = client.get("/api/dashboard/research-lab")
    assert listing.status_code == 200
    body = listing.json()
    assert body["enabled"] is True
    assert body["runner_configured"] is True
    assert body["total"] == 1
    assert body["runs"][0]["result"]["stdout"] == "risultato pronto\\n"
    assert body["runs"][0]["artifacts"][0]["id"] == artifact.id

    content = client.get(
        f"/api/dashboard/research-lab/artifacts/{artifact.id}/content"
    )
    assert content.status_code == 200
    assert content.headers["content-type"].startswith("application/json")
    assert content.content == b'{"value": 42}'
    assert "inline" in content.headers["content-disposition"]

    deletion = client.delete(f"/api/dashboard/research-lab/artifacts/{artifact.id}")
    assert deletion.status_code == 204
    assert client.get(
        f"/api/dashboard/research-lab/artifacts/{artifact.id}/content"
    ).status_code == 404
    assert client.get("/api/dashboard/research-lab").json()["runs"][0]["artifacts"] == []


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


def test_active_history_compaction_routes_sync_and_stream_without_mutating_canonical(
    db_engine: Engine,
) -> None:
    client = make_client(
        db_engine,
        settings_overrides={"history_compaction_mode": "active"},
    )
    session = client.post("/api/chat/sessions", json={}).json()
    session_id = session["id"]
    first = client.post(
        f"/api/chat/sessions/{session_id}/turn",
        json={"message": "first"},
    ).json()
    client.post(
        f"/api/chat/sessions/{session_id}/turn",
        json={"message": "second"},
    )

    with Session(db_engine) as db:
        source_map = build_chronology_source_map(
            db,
            session_id=session_id,
            chars_per_token=2.0,
        )
        first_unit = source_map["turns"][0]
        summary = "The first completed turn is preserved in compact form."
        repositories.create_history_compaction(
            db,
            session_id=session_id,
            summary=summary,
            summary_sha256=sha256(summary.encode()).hexdigest(),
            source_history_sha256=source_map["canonical_history_sha256"],
            covered_through_turn_id=first["turn_id"],
            covered_turn_ids=[first["turn_id"]],
            covered_sources=[
                {
                    "turn_id": first["turn_id"],
                    "sha256": first_unit["sha256"],
                    "estimated_tokens": first_unit["estimated_tokens"],
                }
            ],
            source_estimated_tokens=first_unit["estimated_tokens"],
            summary_estimated_tokens=20,
            trigger_turn_id=first["turn_id"],
            model="MiniMax-M3",
            provider_message_id="provider_compaction",
            metadata={
                "legacy_prefix_sha256": source_map["legacy_prefix"]["sha256"]
            },
        )

    sync = client.post(
        f"/api/chat/sessions/{session_id}/turn",
        json={"message": "third"},
    ).json()
    sync_traces = client.get(f"/api/debug/traces/{sync['turn_id']}").json()
    sync_request = next(trace for trace in sync_traces if trace["kind"] == "llm.request")
    assert sync_request["payload"]["provider_history_source"] == (
        "history_compaction_artifact"
    )
    assert len(sync_request["payload"]["canonical_provider_messages"]) == 5
    assert len(sync_request["payload"]["provider_messages"]) == 3
    assert summary in sync_request["payload"]["system"]

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/turn/stream",
        json={"message": "fourth"},
    ) as response:
        decoded = [json.loads(line) for line in response.iter_lines() if line]
    complete = decoded[-1]["data"]
    stream_traces = client.get(
        f"/api/debug/traces/{complete['turn_id']}"
    ).json()
    stream_request = next(
        trace for trace in stream_traces if trace["kind"] == "llm.request"
    )
    assert stream_request["payload"]["provider_history_source"] == (
        "history_compaction_artifact"
    )
    assert len(stream_request["payload"]["canonical_provider_messages"]) == 7
    assert len(stream_request["payload"]["provider_messages"]) == 5
    assert summary in stream_request["payload"]["system"]

    with Session(db_engine) as db:
        stored = repositories.get_chat_session(db, session_id)
        routing_traces = repositories.list_traces_for_session(
            db,
            session_id=session_id,
            kinds=["history.routing"],
            limit=20,
        )

    assert stored is not None
    assert len(stored.provider_history_json) == 8
    assert [message["role"] for message in stored.provider_history_json] == [
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert [
        trace.payload_json["status"] for trace in routing_traces
    ].count("derived_history_active") == 2


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
            "retrieval_hybrid_min_rerank_score": 0.55,
        },
    )
    cacao_memory_id = add_project_memory(
        db_engine,
        content="The owner prefers cacao tea during evening focus work.",
        tags=["cacao", "focus"],
        with_provenance=True,
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
    request_trace = next(
        trace["payload"] for trace in traces if trace["kind"] == "llm.request"
    )
    runtime_payload = json.loads(
        request_trace["runtime_context"]
        .removeprefix("<runtime_context>\n")
        .removesuffix("\n</runtime_context>")
    )
    relevant = runtime_payload["memories"]["relevant"]
    assert [item["id"] for item in relevant] == [cacao_memory_id]
    assert relevant[0]["source_session_id"].startswith("ses_")
    assert relevant[0]["source_message_id"].startswith("msg_")


def test_chat_turn_final_reranker_rejects_strong_deterministic_match(
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
            "retrieval_shadow_cloud_surface_limit": 20,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 5,
            "retrieval_hybrid_mode": "active",
            "retrieval_hybrid_min_rerank_score": 0.55,
        },
    )
    memory_id = add_project_memory(
        db_engine,
        content="Il protocollo Zero-Luce verifica la continuita della memoria.",
        tags=["zero-luce"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Cosa prevede esattamente il protocollo Zero-Luce?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected"] == []
    rerank = memory_context["query_plan"]["retrieval_rerank"]
    rejected = next(
        item for item in rerank["entries"] if item["memory_id"] == memory_id
    )
    assert rejected["evaluated"] is True
    assert rejected["accepted"] is False
    assert "sparse" in rejected["recall_routes"]


def test_chat_turn_sparse_candidate_reaches_final_reranker_outside_dense_sample(
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
            "retrieval_shadow_cloud_surface_limit": 1,
            "retrieval_shadow_rerank_enabled": True,
            "retrieval_shadow_rerank_model": "test/rerank",
            "retrieval_shadow_rerank_candidate_limit": 10,
            "retrieval_shadow_rerank_top_n": 5,
            "retrieval_hybrid_mode": "active",
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
        json={"message": "Ricordi la mia preferenza per il cacao?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected"][0]["id"] == cacao_memory_id
    rerank = memory_context["query_plan"]["retrieval_rerank"]
    accepted = next(
        item for item in rerank["entries"] if item["memory_id"] == cacao_memory_id
    )
    assert accepted["accepted"] is True
    assert "sparse" in accepted["recall_routes"]
    assert "dense" not in accepted["recall_routes"]


def test_chat_turn_active_rerank_fails_closed_when_reranker_is_unavailable(
    db_engine: Engine,
) -> None:
    client = make_client(
        db_engine,
        settings_overrides={
            "openrouter_api_key": "test-openrouter-key",
            "retrieval_shadow_enabled": True,
            "retrieval_shadow_backend": "openrouter",
            "retrieval_shadow_rerank_enabled": False,
            "retrieval_hybrid_mode": "active",
        },
    )
    memory_id = add_project_memory(
        db_engine,
        content="Il protocollo Zero-Luce verifica la continuita della memoria.",
        tags=["zero-luce"],
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Cosa prevede il protocollo Zero-Luce?"},
    )

    assert response.status_code == 200
    traces = client.get(f"/api/debug/traces/{response.json()['turn_id']}").json()
    memory_context = traces[0]["payload"]
    assert memory_context["selected"] == []
    assert memory_context["negative_evidence"] == "final_rerank_unavailable"
    rerank = memory_context["query_plan"]["retrieval_rerank"]
    assert rerank["status"] == "configuration_error"
    assert rerank["fail_closed"] is True
    assert any(item["memory_id"] == memory_id for item in rerank["entries"])


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
        json={"message": ("Mi ricordi il mio limite salutare sul cioccolato?")},
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
        json={"message": ("Che playlist jazz notturna potrei mettere mentre cucino?")},
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
    assert response_trace["payload"]["tool_calls"][0]["trace_id"] == tool_trace["id"]
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
    assert (
        note_event["payload"]["text"] == "I will inspect the schema before answering."
    )
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
    write_trace = next(
        trace for trace in traces if trace["kind"] == "mind.memory.write"
    )
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
    search_trace = next(
        trace for trace in traces if trace["kind"] == "mind.memory.search"
    )
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
    assert live_runtime_event_types[:7] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "memory.recent_context.built",
        "session.continuity.built",
        "metacognitive.context.shadowed",
        "runtime.context.built",
    ]
    assert live_runtime_event_types[:8] == [
        "turn.started",
        "message.user.persisted",
        "memory.context.built",
        "memory.recent_context.built",
        "session.continuity.built",
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
    memory_event = next(
        event for event in decoded_events if event["type"] == "memory_context"
    )
    assert memory_event["data"]["searched"] is True
    assert memory_event["data"]["selected_count"] == 0
    metacognitive_event = next(
        event for event in decoded_events if event["type"] == "metacognitive_context"
    )
    assert metacognitive_event["data"]["mode"] == "shadow"
    assert metacognitive_event["data"]["model_facing"] is False
    runtime_event = next(
        event for event in decoded_events if event["type"] == "runtime_context"
    )
    assert runtime_event["data"]["schema_version"] == "runtime-context-v1"
    assert len(runtime_event["data"]["blocks"]) == 4
    request_trace = next(trace for trace in traces if trace["kind"] == "llm.request")
    model_context_trace = next(
        trace for trace in traces if trace["kind"] == "model.context"
    )
    assert request_trace["payload"]["tool_loop_policy"] == "model_controlled_unbounded"
    assert request_trace["payload"]["provider_history_source"] == (
        "messages.text_reconstructed"
    )
    assert request_trace["payload"]["model_context_profile"] == "v2"
    assert request_trace["payload"]["model_context_trace_id"] == (
        model_context_trace["id"]
    )
    assert model_context_trace["id"] in complete["trace_ids"]
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


def test_stream_v2_emits_only_replayable_provider_independent_events(
    db_engine: Engine,
) -> None:
    client = make_tool_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream-v2",
        json={"message": "inspect schema first"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache, no-transform"
        assert response.headers["x-accel-buffering"] == "no"
        assert response.headers["x-scarlet-stream-schema"] == "scarlet-stream-v2"
        turn_id = response.headers["x-scarlet-turn-id"]
        events = [json.loads(line) for line in response.iter_lines() if line]

    required = {
        "schema_version",
        "event_id",
        "seq",
        "session_id",
        "turn_id",
        "event_type",
        "phase",
        "timestamp",
        "visibility",
        "links",
        "payload",
    }
    assert events
    assert all(set(event) == required for event in events)
    assert {event["schema_version"] for event in events} == {"scarlet-stream-v2"}
    assert len({event["event_id"] for event in events}) == len(events)
    assert [event["seq"] for event in events] == sorted(
        event["seq"] for event in events
    )
    event_types = [event["event_type"] for event in events]
    assert "assistant.note.emitted" in event_types
    assert "mind.tool_call.started" in event_types
    assert "mind.tool_call.completed" in event_types
    assert "assistant.answer.completed" in event_types
    assert "message.assistant.persisted" in event_types
    assert "turn.completed" in event_types
    thinking = next(
        event for event in events if event["event_type"] == "llm.thinking.captured"
    )
    assert thinking["visibility"] == "debug"
    assert thinking["payload"]["text"] == "I should inspect the schema."
    assert not {
        "thinking_delta",
        "text_delta",
        "tool_input_delta",
        "tool_call",
        "tool_result",
        "turn_complete",
    }.intersection(event_types)

    user_event = next(
        event for event in events if event["event_type"] == "message.user.persisted"
    )
    assistant_event = next(
        event
        for event in events
        if event["event_type"] == "message.assistant.persisted"
    )
    assert user_event["payload"]["message"]["content"] == "inspect schema first"
    assert assistant_event["payload"]["message"]["content"] == "Schema inspected."
    assert assistant_event["links"]["message_id"] == assistant_event["payload"][
        "message"
    ]["id"]
    tool_event = next(
        event for event in events if event["event_type"] == "mind.tool_call.completed"
    )
    assert tool_event["links"]["trace_id"].startswith("trace_")
    assert tool_event["links"]["tool_call_id"].startswith("tool_")
    returned_event = next(
        event
        for event in events
        if event["event_type"] == "mind.tool_call.result_returned"
    )
    assert "result" not in returned_event["payload"]
    runtime_context_event = next(
        event for event in events if event["event_type"] == "runtime.context.built"
    )
    assert "blocks" not in runtime_context_event["payload"]
    terminal = next(
        event for event in events if event["event_type"] == "turn.completed"
    )
    assert terminal["payload"]["turn"]["status"] == "completed"
    assert terminal["turn_id"] == turn_id

    with client.stream(
        "GET",
        f"/api/chat/sessions/{session['id']}/turns/{turn_id}/stream-v2",
        params={"after_seq": terminal["seq"] - 1},
    ) as resumed:
        assert resumed.status_code == 200
        assert resumed.headers["cache-control"] == "no-cache, no-transform"
        assert resumed.headers["x-accel-buffering"] == "no"
        assert resumed.headers["x-scarlet-turn-id"] == turn_id
        resumed_events = [
            json.loads(line) for line in resumed.iter_lines() if line
        ]
    assert [event["event_id"] for event in resumed_events] == [
        terminal["event_id"]
    ]


def test_live_stream_interleaves_transient_frames_with_durable_events(
    db_engine: Engine,
) -> None:
    client = make_tool_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream-live",
        json={"message": "inspect schema first"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-cache, no-transform"
        assert response.headers["x-accel-buffering"] == "no"
        assert response.headers["x-scarlet-stream-schema"] == "scarlet-live-v1"
        turn_id = response.headers["x-scarlet-turn-id"]
        items = [json.loads(line) for line in response.iter_lines() if line]

    assert items
    assert {item["schema_version"] for item in items} == {"scarlet-live-v1"}
    events = [item["event"] for item in items if item["kind"] == "event"]
    frames = [item["frame"] for item in items if item["kind"] == "frame"]
    assert all(item["frame"] is None for item in items if item["kind"] == "event")
    assert all(item["event"] is None for item in items if item["kind"] == "frame")
    assert {frame["frame_type"] for frame in frames} == {
        "thinking_delta",
        "text_delta",
        "tool_input_delta",
    }
    assert {
        frame["frame_id"]
        for frame in frames
        if frame["frame_type"] == "text_delta"
    } == {
        f"content-{turn_id}-1-1",
        f"content-{turn_id}-2-0",
    }
    event_types = [event["event_type"] for event in events]
    assert "message.user.persisted" in event_types
    assert "memory.context.built" in event_types
    assert "memory.recent_context.built" in event_types
    assert "session.continuity.built" in event_types
    assert "mind.tool_call.started" in event_types
    assert "mind.tool_call.completed" in event_types
    assert "assistant.answer.completed" in event_types
    assert event_types[-1] == "turn.completed"
    assert [event["seq"] for event in events] == sorted(
        event["seq"] for event in events
    )

    first_page = client.get(
        f"/api/chat/sessions/{session['id']}/events",
        params={"after_seq": 0, "limit": 3},
    ).json()
    assert first_page["schema_version"] == "scarlet-stream-v2"
    assert first_page["cursor"]["has_more"] is True
    second_page = client.get(
        f"/api/chat/sessions/{session['id']}/events",
        params={
            "after_seq": first_page["cursor"]["next_after_seq"],
            "limit": 1000,
        },
    ).json()
    replayed = [*first_page["events"], *second_page["events"]]
    assert [event["event_id"] for event in replayed[: len(events)]] == [
        event["event_id"] for event in events
    ]
    assert replayed[len(events)]["event_type"] == "maintenance.job.scheduled"
    assert second_page["cursor"]["has_more"] is False
    assert second_page["cursor"]["next_after_seq"] == second_page["cursor"][
        "latest_seq"
    ]


def test_live_stream_accepts_android_webview_cors_preflight(
    db_engine: Engine,
) -> None:
    client = make_tool_client(db_engine)

    response = client.options(
        "/api/chat/sessions/session-placeholder/turn/stream-live",
        headers={
            "Origin": "https://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://localhost"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "Authorization" in response.headers["access-control-allow-headers"]
    assert "Content-Type" in response.headers["access-control-allow-headers"]


def test_stream_v2_persists_a_replayable_terminal_error(db_engine: Engine) -> None:
    client = make_thinking_only_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream-v2",
        json={"message": "Dimmi cosa ne pensi."},
    ) as response:
        events = [json.loads(line) for line in response.iter_lines() if line]

    assert events[-1]["event_type"] == "turn.failed"
    assert events[-1]["phase"] == "failed"
    assert events[-1]["payload"]["code"] == "llm.incomplete_response"
    assert events[-1]["payload"]["turn"]["status"] == "failed"
    assert not any(
        event["event_type"] == "assistant.answer.completed" for event in events
    )

    replay = client.get(
        f"/api/chat/sessions/{session['id']}/events",
        params={"after_seq": events[-2]["seq"]},
    ).json()
    assert [event["event_id"] for event in replay["events"]] == [
        events[-1]["event_id"]
    ]
    assert replay["cursor"]["has_more"] is False


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


def test_chat_turn_rejects_thinking_only_final_result(db_engine: Engine) -> None:
    client = make_thinking_only_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Dimmi cosa ne pensi."},
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "llm.incomplete_response"
    with Session(db_engine) as db:
        turns = repositories.list_turns_for_session(db, session_id=session["id"])
        messages = repositories.list_messages(db, session_id=session["id"])
        tool_calls = repositories.list_tool_calls_for_turn(
            db,
            turn_id=turns[-1].id,
        )
        memories = repositories.list_all_memories(db)
    assert turns[-1].status == "failed"
    assert turns[-1].error_json["code"] == "llm.incomplete_response"
    assert [message.role for message in messages] == ["user"]
    assert tool_calls == []
    assert memories == []


def test_streaming_chat_rejects_thinking_only_final_result(
    db_engine: Engine,
) -> None:
    client = make_thinking_only_client(db_engine)
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream",
        json={"message": "Dimmi cosa ne pensi."},
    ) as response:
        assert response.status_code == 200
        events = [json.loads(line) for line in response.iter_lines() if line]

    assert events[-1]["type"] == "error"
    assert events[-1]["data"]["code"] == "llm.incomplete_response"
    assert not any(event["type"] == "turn_complete" for event in events)
    with Session(db_engine) as db:
        turns = repositories.list_turns_for_session(db, session_id=session["id"])
        messages = repositories.list_messages(db, session_id=session["id"])
    assert turns[-1].status == "failed"
    assert turns[-1].error_json["code"] == "llm.incomplete_response"
    assert [message.role for message in messages] == ["user"]


def test_native_finality_accepts_provider_end_turn_without_semantic_gate(
    db_engine: Engine,
) -> None:
    client = make_answer_boundary_client(
        db_engine,
        provider_class=FakeSemanticAnswerRecoveryProvider,
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={"message": "Puoi verificare lo stato implementato?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["content"] == "È tutto verificato."
    assert FakeSemanticAnswerRecoveryProvider.calls == 1
    traces = client.get(f"/api/debug/traces/{payload['turn_id']}").json()
    assert not any(trace["kind"] == "answer.validation" for trace in traces)
    response_trace = next(trace for trace in traces if trace["kind"] == "llm.response")
    assert response_trace["payload"]["finality_contract"] == {
        "accepted": True,
        "source": "provider_stop_reason",
        "response_visibility": "public",
        "semantic_validation": False,
    }


def test_native_sync_accepts_truthful_success_after_recoverable_action_retry(
    db_engine: Engine,
) -> None:
    client = make_answer_boundary_client(
        db_engine,
        provider_class=FakeRecoveredActionProvider,
    )
    session = client.post("/api/chat/sessions", json={}).json()

    response = client.post(
        f"/api/chat/sessions/{session['id']}/turn",
        json={
            "message": (
                "Ricorda che preferisco giudicare i risultati reali prima dei punteggi."
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["assistant_message"]["content"] == (
        "Ho salvato la preferenza dopo aver corretto il comando."
    )
    traces = client.get(f"/api/debug/traces/{payload['turn_id']}").json()
    assert not any(trace["kind"] == "answer.validation" for trace in traces)
    assert [
        trace["payload"]["status"]
        for trace in traces
        if trace["kind"] == "mind.tool_call"
    ] == ["error", "completed"]

    with Session(db_engine) as db:
        memories = repositories.list_memories(db)
    assert [
        memory.content
        for memory in memories
        if memory.content == FakeRecoveredActionProvider.memory_content
    ] == [FakeRecoveredActionProvider.memory_content]


def test_native_stream_accepts_truthful_success_after_recoverable_action_retry(
    db_engine: Engine,
) -> None:
    client = make_answer_boundary_client(
        db_engine,
        provider_class=FakeRecoveredActionProvider,
    )
    session = client.post("/api/chat/sessions", json={}).json()

    with client.stream(
        "POST",
        f"/api/chat/sessions/{session['id']}/turn/stream",
        json={
            "message": (
                "Ricorda che preferisco giudicare i risultati reali prima dei punteggi."
            )
        },
    ) as response:
        assert response.status_code == 200
        events = [json.loads(line) for line in response.iter_lines() if line]

    assert events[-1]["type"] == "turn_complete"
    assert events[-1]["data"]["assistant_message"]["content"] == (
        "Ho salvato la preferenza dopo aver corretto il comando."
    )
    turn_id = events[-1]["data"]["turn_id"]
    traces = client.get(f"/api/debug/traces/{turn_id}").json()
    assert not any(trace["kind"] == "answer.validation" for trace in traces)
    tool_traces = [trace for trace in traces if trace["kind"] == "mind.tool_call"]
    assert [trace["payload"]["status"] for trace in tool_traces] == [
        "error",
        "completed",
    ]
    assert [trace["payload"]["result"]["ok"] for trace in tool_traces] == [
        False,
        True,
    ]

    with Session(db_engine) as db:
        memories = repositories.list_memories(db)
    assert any(
        memory.content == FakeRecoveredActionProvider.memory_content
        for memory in memories
    )

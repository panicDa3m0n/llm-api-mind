from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import pytest

from app.llm.minimax_client import AnthropicCompatibleProvider
from app.llm.provider import (
    LLMExecutedToolCall,
    LLMIncompleteResponseError,
    LLMMessage,
    LLMRequestError,
    LLMTextResult,
)


class FakeContentBlock:
    type = "text"
    text = "pong"

    def model_dump(self) -> dict[str, str]:
        return {"type": "text", "text": "pong"}


class FakeTextBlock:
    type = "text"

    def __init__(self, text: str) -> None:
        self.text = text

    def model_dump(self) -> dict[str, str]:
        return {"type": "text", "text": self.text}


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, *, tool_id: str = "tool_1") -> None:
        self.id = tool_id
        self.name = "mind_shell"
        self.input = {"command": "help", "intent": "Inspect capabilities"}

    def model_dump(self) -> dict[str, Any]:
        return {
            "type": "tool_use",
            "id": self.id,
            "name": self.name,
            "input": self.input,
        }


class FakeStream:
    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def __iter__(self) -> "FakeStream":
        return self

    def __next__(self) -> object:
        raise StopIteration

    def get_final_message(self) -> SimpleNamespace:
        return SimpleNamespace(
            id="provider_msg_stream",
            model="MiniMax-M2.7",
            content=[FakeContentBlock()],
            usage={"input_tokens": 1, "output_tokens": 1},
            stop_reason="end_turn",
        )


class FakeMessages:
    def __init__(self) -> None:
        self.create_called = False
        self.stream_calls: list[dict[str, Any]] = []

    def create(self, **_kwargs: Any) -> None:
        self.create_called = True
        raise AssertionError("Provider calls should use stream internally.")

    def stream(self, **kwargs: Any) -> FakeStream:
        self.stream_calls.append(kwargs)
        return FakeStream()


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


class FakeThinkingBlock:
    type = "thinking"
    thinking = "I have enough evidence, but I forgot to answer publicly."
    signature = "test-thinking-signature"

    def model_dump(self) -> dict[str, str]:
        return {
            "type": "thinking",
            "thinking": self.thinking,
            "signature": self.signature,
        }


class FakeMessageStream(FakeStream):
    def __init__(self, message: SimpleNamespace) -> None:
        self.message = message

    def get_final_message(self) -> SimpleNamespace:
        return self.message


class FakeMessageSequence:
    def __init__(self, messages: list[SimpleNamespace]) -> None:
        self.messages = list(messages)
        self.stream_calls: list[dict[str, Any]] = []

    def stream(self, **kwargs: Any) -> FakeMessageStream:
        self.stream_calls.append(kwargs)
        return FakeMessageStream(self.messages.pop(0))


def make_provider(
    *,
    model: str = "MiniMax-M2.7",
    max_tokens: int = 131072,
    stream_max_attempts: int = 5,
    max_token_continuations: int = 8,
) -> AnthropicCompatibleProvider:
    provider = AnthropicCompatibleProvider(
        api_key="test-key",
        api_key_name="MINIMAX_API_KEY",
        base_url="https://api.minimax.io/anthropic",
        model=model,
        max_tokens=max_tokens,
        provider_name="MiniMax",
        stream_max_attempts=stream_max_attempts,
        stream_retry_backoff_seconds=0,
        max_token_continuations=max_token_continuations,
    )
    provider._client = FakeAnthropicClient()
    return provider


def test_generate_chat_always_uses_stream() -> None:
    provider = make_provider()

    result = provider.generate_chat(
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=131072,
    )

    assert isinstance(result, LLMTextResult)
    assert result.text == "pong"
    assert provider._client.messages.create_called is False
    assert provider._client.messages.stream_calls[0]["max_tokens"] == 131072
    assert "thinking" not in provider._client.messages.stream_calls[0]


def test_generate_chat_uses_stream_for_small_default_token_budget() -> None:
    provider = make_provider(max_tokens=4096)

    result = provider.generate_chat(
        messages=[LLMMessage(role="user", content="ping")],
    )

    assert result.text == "pong"
    assert provider._client.messages.create_called is False
    assert provider._client.messages.stream_calls[0]["max_tokens"] == 4096
    assert "thinking" not in provider._client.messages.stream_calls[0]


def test_generate_chat_with_tools_always_uses_stream() -> None:
    provider = make_provider()

    result = provider.generate_chat_with_tools(
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=131072,
        tools=[],
        tool_runner=lambda _tool_use: None,  # No tool_use blocks are returned.
    )

    assert result.text == "pong"
    assert provider._client.messages.create_called is False
    assert provider._client.messages.stream_calls[0]["max_tokens"] == 131072
    assert provider._client.messages.stream_calls[0]["tools"] == []
    assert "thinking" not in provider._client.messages.stream_calls[0]


def test_generate_chat_enables_thinking_for_m3() -> None:
    provider = make_provider(model="MiniMax-M3")

    result = provider.generate_chat(
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=131072,
    )

    assert result.text == "pong"
    assert provider._client.messages.stream_calls[0]["thinking"] == {"type": "adaptive"}


def test_generate_chat_with_tools_enables_thinking_for_m3() -> None:
    provider = make_provider(model="MiniMax-M3")

    result = provider.generate_chat_with_tools(
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=131072,
        tools=[],
        tool_runner=lambda _tool_use: None,
    )

    assert result.text == "pong"
    assert provider._client.messages.stream_calls[0]["thinking"] == {"type": "adaptive"}


def test_tool_chat_continues_max_tokens_and_preserves_provider_history() -> None:
    provider = make_provider(model="MiniMax-M3")
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id="provider_truncated",
                model="MiniMax-M3",
                content=[
                    FakeThinkingBlock(),
                    FakeTextBlock("Prima parte della risposta,"),
                ],
                usage={"input_tokens": 10, "output_tokens": 7},
                stop_reason="max_tokens",
            ),
            SimpleNamespace(
                id="provider_recovered",
                model="MiniMax-M3",
                content=[FakeTextBlock("seguita dalla conclusione.")],
                usage={"input_tokens": 12, "output_tokens": 1},
                stop_reason="end_turn",
            ),
        ]
    )
    provider._client = SimpleNamespace(messages=sequence)

    events = list(
        provider.stream_chat_with_tools(
            messages=[LLMMessage(role="user", content="ping")],
            tools=[],
            tool_runner=lambda _tool_use: None,
        )
    )

    assert [event.type for event in events].count("completion_recovery") == 1
    assert [event.type for event in events].count("assistant_continuation") == 1
    result = LLMTextResult.model_validate(events[-1].data["result"])
    assert result.text == (
        "Prima parte della risposta,\nseguita dalla conclusione."
    )
    assert result.stop_reason == "end_turn"
    assert result.completion_recovery["attempted"] is True
    assert result.completion_recovery["recovered"] is True
    assert result.completion_recovery["attempt_count"] == 1
    assert len(sequence.stream_calls) == 2
    continuation_messages = sequence.stream_calls[1]["messages"]
    assert continuation_messages[-2]["role"] == "assistant"
    assert continuation_messages[-2]["content"][0]["type"] == "thinking"
    assert continuation_messages[-1]["role"] == "user"
    assert "reached max_tokens" in continuation_messages[-1]["content"][0]["text"]
    assert [message["id"] for message in result.raw_provider_messages] == [
        "provider_truncated",
        "provider_recovered"
    ]
    assert result.provider_history_tail == [
        {
            "role": "assistant",
            "content": [
                FakeThinkingBlock().model_dump(),
                {"type": "text", "text": "Prima parte della risposta,"},
            ],
        },
        continuation_messages[-1],
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "seguita dalla conclusione."}],
        },
    ]


def test_tool_chat_treats_thinking_only_end_turn_as_terminal_failure() -> None:
    provider = make_provider(model="MiniMax-M3")
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id=f"provider_thinking_only_{index}",
                model="MiniMax-M3",
                content=[FakeThinkingBlock()],
                usage={"input_tokens": 10, "output_tokens": 7},
                stop_reason="end_turn",
            )
            for index in range(1)
        ]
    )
    provider._client = SimpleNamespace(messages=sequence)

    with pytest.raises(LLMIncompleteResponseError) as exc_info:
        list(
            provider.stream_chat_with_tools(
                messages=[LLMMessage(role="user", content="ping")],
                tools=[],
                tool_runner=lambda _tool_use: None,
            )
        )

    assert len(sequence.stream_calls) == 1
    assert exc_info.value.details == {
        "reason": "thinking_only_end_turn",
        "stop_reason": "end_turn",
        "provider_message_id": "provider_thinking_only_0",
        "recoverable": False,
    }


def test_tool_chat_bounds_pathological_max_tokens_continuations() -> None:
    provider = make_provider(
        model="MiniMax-M3",
        max_token_continuations=2,
    )
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id=f"provider_max_{index}",
                model="MiniMax-M3",
                content=[FakeThinkingBlock()],
                usage={"input_tokens": 10, "output_tokens": 7},
                stop_reason="max_tokens",
            )
            for index in range(3)
        ]
    )
    provider._client = SimpleNamespace(messages=sequence)

    with pytest.raises(LLMIncompleteResponseError) as exc_info:
        list(
            provider.stream_chat_with_tools(
                messages=[LLMMessage(role="user", content="ping")],
                tools=[],
                tool_runner=lambda _tool_use: None,
            )
        )

    assert len(sequence.stream_calls) == 3
    assert exc_info.value.details == {
        "reason": "max_tokens_continuation_limit",
        "stop_reason": "max_tokens",
        "provider_message_id": "provider_max_2",
        "continuation_count": 2,
        "continuation_limit": 2,
        "recoverable": False,
    }


def test_tool_chat_rejects_tool_use_when_stop_reason_is_max_tokens() -> None:
    provider = make_provider(model="MiniMax-M3")
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id="provider_truncated_tool",
                model="MiniMax-M3",
                content=[FakeToolUseBlock()],
                usage={"input_tokens": 10, "output_tokens": 5},
                stop_reason="max_tokens",
            )
        ]
    )
    provider._client = SimpleNamespace(messages=sequence)
    executed: list[str] = []

    with pytest.raises(LLMIncompleteResponseError) as exc_info:
        list(
            provider.stream_chat_with_tools(
                messages=[LLMMessage(role="user", content="ping")],
                tools=[],
                tool_runner=lambda tool_use: executed.append(tool_use.id),
            )
        )

    assert executed == []
    assert len(sequence.stream_calls) == 1
    assert exc_info.value.details == {
        "reason": "truncated_tool_use",
        "stop_reason": "max_tokens",
        "provider_message_id": "provider_truncated_tool",
        "recoverable": False,
    }


def test_tool_chat_executes_tool_only_for_tool_use_stop_reason() -> None:
    provider = make_provider()
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id="provider_tool",
                model="MiniMax-M2.7",
                content=[
                    FakeTextBlock("Controllo le capacità."),
                    FakeToolUseBlock(),
                ],
                usage={"input_tokens": 10, "output_tokens": 5},
                stop_reason="tool_use",
            ),
            SimpleNamespace(
                id="provider_final",
                model="MiniMax-M2.7",
                content=[FakeTextBlock("Controllo completato.")],
                usage={"input_tokens": 12, "output_tokens": 2},
                stop_reason="end_turn",
            ),
        ]
    )
    provider._client = SimpleNamespace(messages=sequence)

    def run_tool(tool_use: Any) -> LLMExecutedToolCall:
        return LLMExecutedToolCall(
            provider_tool_use_id=tool_use.id,
            tool_name=tool_use.name,
            arguments=tool_use.input,
            result={"ok": True},
            status="completed",
        )

    events = list(
        provider.stream_chat_with_tools(
            messages=[LLMMessage(role="user", content="ping")],
            tools=[],
            tool_runner=run_tool,
        )
    )

    assert [event.type for event in events].count("assistant_note") == 1
    assert [event.type for event in events].count("assistant_answer") == 1
    assert [event.type for event in events].count("tool_call") == 1
    result = LLMTextResult.model_validate(events[-1].data["result"])
    assert result.text == "Controllo completato."
    assert len(result.tool_calls) == 1


class FailingStream(FakeMessageStream):
    def __init__(
        self,
        message: SimpleNamespace,
        error: anthropic.AnthropicError,
    ) -> None:
        super().__init__(message)
        self.error = error

    def __iter__(self) -> "FailingStream":
        raise self.error


class RetryMessages:
    def __init__(self) -> None:
        self.calls = 0

    def stream(self, **_kwargs: Any) -> FakeMessageStream:
        self.calls += 1
        message = SimpleNamespace(
            id="provider_after_retry",
            model="MiniMax-M3",
            content=[FakeContentBlock()],
            usage={"input_tokens": 1, "output_tokens": 1},
            stop_reason="end_turn",
        )
        if self.calls == 1:
            return FailingStream(
                message,
                anthropic.APIConnectionError(
                    message="stream disconnected",
                    request=httpx.Request("POST", "https://provider.test/messages"),
                ),
            )
        return FakeMessageStream(message)


def test_tool_chat_retries_interrupted_provider_stream() -> None:
    provider = make_provider(model="MiniMax-M3", stream_max_attempts=5)
    messages = RetryMessages()
    provider._client = SimpleNamespace(messages=messages)

    events = list(
        provider.stream_chat_with_tools(
            messages=[LLMMessage(role="user", content="ping")],
            tools=[],
            tool_runner=lambda _tool_use: None,
        )
    )

    retry = next(event for event in events if event.type == "provider_retry")
    assert retry.data["provider_attempt"] == 1
    assert retry.data["next_provider_attempt"] == 2
    assert retry.data["provider_attempt_limit"] == 5
    assert messages.calls == 2
    result = LLMTextResult.model_validate(events[-1].data["result"])
    assert result.text == "pong"


class BadRequestMessages:
    def __init__(self) -> None:
        self.calls = 0

    def stream(self, **_kwargs: Any) -> FakeMessageStream:
        self.calls += 1
        request = httpx.Request("POST", "https://provider.test/messages")
        response = httpx.Response(400, request=request)
        return FailingStream(
            SimpleNamespace(),
            anthropic.BadRequestError(
                "invalid request",
                response=response,
                body={"error": "invalid request"},
            ),
        )


def test_tool_chat_does_not_retry_non_transient_provider_error() -> None:
    provider = make_provider(model="MiniMax-M3", stream_max_attempts=5)
    messages = BadRequestMessages()
    provider._client = SimpleNamespace(messages=messages)

    with pytest.raises(LLMRequestError, match="invalid request"):
        list(
            provider.stream_chat_with_tools(
                messages=[LLMMessage(role="user", content="ping")],
                tools=[],
                tool_runner=lambda _tool_use: None,
            )
        )

    assert messages.calls == 1

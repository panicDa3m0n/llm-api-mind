from types import SimpleNamespace
from typing import Any

import pytest

from app.llm.minimax_client import AnthropicCompatibleProvider
from app.llm.provider import LLMIncompleteResponseError, LLMMessage, LLMTextResult


class FakeContentBlock:
    type = "text"
    text = "pong"

    def model_dump(self) -> dict[str, str]:
        return {"type": "text", "text": "pong"}


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
) -> AnthropicCompatibleProvider:
    provider = AnthropicCompatibleProvider(
        api_key="test-key",
        api_key_name="MINIMAX_API_KEY",
        base_url="https://api.minimax.io/anthropic",
        model=model,
        max_tokens=max_tokens,
        provider_name="MiniMax",
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


def test_tool_chat_recovers_one_thinking_only_end_turn() -> None:
    provider = make_provider(model="MiniMax-M3")
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id="provider_thinking_only",
                model="MiniMax-M3",
                content=[FakeThinkingBlock()],
                usage={"input_tokens": 10, "output_tokens": 7},
                stop_reason="end_turn",
            ),
            SimpleNamespace(
                id="provider_recovered",
                model="MiniMax-M3",
                content=[FakeContentBlock()],
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
    result = LLMTextResult.model_validate(events[-1].data["result"])
    assert result.text == "pong"
    assert result.completion_recovery["attempted"] is True
    assert result.completion_recovery["recovered"] is True
    assert result.completion_recovery["attempt_count"] == 1
    assert len(sequence.stream_calls) == 2
    continuation_messages = sequence.stream_calls[1]["messages"]
    assert continuation_messages[-2]["role"] == "assistant"
    assert continuation_messages[-2]["content"][0]["type"] == "thinking"
    assert continuation_messages[-1]["role"] == "user"
    assert "public answer" in continuation_messages[-1]["content"][0]["text"]
    assert [message["id"] for message in result.raw_provider_messages] == [
        "provider_recovered"
    ]


def test_tool_chat_fails_after_repeated_thinking_only_end_turn() -> None:
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
            for index in range(2)
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

    assert len(sequence.stream_calls) == 2
    assert exc_info.value.details == {
        "reason": "thinking_only_end_turn",
        "stop_reason": "end_turn",
        "provider_message_id": "provider_thinking_only_1",
        "recovery_attempt_count": 1,
        "terminal_message_count": 2,
        "recovery_limit": 1,
    }


def test_tool_chat_does_not_retry_empty_non_thinking_terminal_message() -> None:
    provider = make_provider(model="MiniMax-M3")
    sequence = FakeMessageSequence(
        [
            SimpleNamespace(
                id="provider_empty",
                model="MiniMax-M3",
                content=[],
                usage={"input_tokens": 10, "output_tokens": 0},
                stop_reason="end_turn",
            )
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
        "reason": "empty_terminal_message",
        "stop_reason": "end_turn",
        "provider_message_id": "provider_empty",
        "recovery_attempt_count": 0,
        "terminal_message_count": 1,
        "recovery_limit": 1,
    }

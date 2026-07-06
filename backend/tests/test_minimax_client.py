from types import SimpleNamespace
from typing import Any

from app.llm.minimax_client import AnthropicCompatibleProvider
from app.llm.provider import LLMMessage, LLMTextResult


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
    assert provider._client.messages.stream_calls[0]["thinking"] == {
        "type": "adaptive"
    }


def test_generate_chat_with_tools_enables_thinking_for_m3() -> None:
    provider = make_provider(model="MiniMax-M3")

    result = provider.generate_chat_with_tools(
        messages=[LLMMessage(role="user", content="ping")],
        max_tokens=131072,
        tools=[],
        tool_runner=lambda _tool_use: None,
    )

    assert result.text == "pong"
    assert provider._client.messages.stream_calls[0]["thinking"] == {
        "type": "adaptive"
    }

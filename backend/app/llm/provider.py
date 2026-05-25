from collections.abc import Callable, Iterator
from typing import Any, Protocol

from pydantic import BaseModel, Field


class LLMProviderError(Exception):
    """Base class for LLM provider failures."""


class LLMConfigurationError(LLMProviderError):
    """Raised when provider configuration is incomplete or invalid."""


class LLMRequestError(LLMProviderError):
    """Raised when the upstream LLM provider request fails."""


class LLMTextResult(BaseModel):
    model: str
    text: str
    usage: dict[str, Any] = Field(default_factory=dict)
    provider_message_id: str | None = None
    raw_content: list[dict[str, Any]] = Field(default_factory=list)
    stop_reason: str | None = None
    tool_calls: list["LLMExecutedToolCall"] = Field(default_factory=list)
    raw_provider_messages: list[dict[str, Any]] = Field(default_factory=list)


class LLMMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]]


class LLMToolUse(BaseModel):
    id: str
    name: str
    input: dict[str, Any] = Field(default_factory=dict)


class LLMExecutedToolCall(BaseModel):
    provider_tool_use_id: str
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    status: str
    latency_ms: int | None = None
    tool_call_id: str | None = None
    trace_id: str | None = None


class LLMStreamEvent(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


LLMToolRunner = Callable[[LLMToolUse], LLMExecutedToolCall]


class LLMProvider(Protocol):
    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        """Generate text from a single user prompt."""

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        """Generate text from a chat history."""

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: LLMToolRunner,
        max_tool_calls: int | None = None,
    ) -> LLMTextResult:
        """Generate text from chat history with the model-controlled tool loop."""

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: LLMToolRunner,
        max_tool_calls: int | None = None,
    ) -> Iterator[LLMStreamEvent]:
        """Stream chat events from the model-controlled tool loop."""

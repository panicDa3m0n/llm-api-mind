import json
from collections.abc import Iterator
from typing import Any

import anthropic

from app.config import Settings
from app.llm.provider import (
    LLMConfigurationError,
    LLMExecutedToolCall,
    LLMMessage,
    LLMRequestError,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolRunner,
    LLMToolUse,
)


class MiniMaxProvider:
    """MiniMax M2 provider through the Anthropic-compatible API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.minimax_api_key:
            raise LLMConfigurationError("MINIMAX_API_KEY is not configured.")

        self._settings = settings
        self._client = anthropic.Anthropic(
            api_key=settings.minimax_api_key,
            base_url=settings.minimax_base_url,
        )

    def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        return self.generate_chat(
            messages=[LLMMessage(role="user", content=prompt)],
            system=system,
            max_tokens=max_tokens,
        )

    def generate_chat(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
    ) -> LLMTextResult:
        effective_max_tokens = max_tokens or self._settings.minimax_max_tokens
        try:
            message = self._client.messages.create(
                model=self._settings.minimax_model,
                max_tokens=effective_max_tokens,
                system=system or "You are a concise assistant.",
                messages=[self._to_anthropic_message(item) for item in messages],
            )
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        return LLMTextResult(
            model=getattr(message, "model", self._settings.minimax_model),
            text=self._extract_text(message.content),
            usage=self._extract_usage(message),
            provider_message_id=getattr(message, "id", None),
            raw_content=self._extract_raw_content(message.content),
            stop_reason=getattr(message, "stop_reason", None),
        )

    def generate_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ) -> LLMTextResult:
        effective_max_tokens = max_tokens or self._settings.minimax_max_tokens
        provider_messages = [self._to_anthropic_message(item) for item in messages]
        executed_tool_calls: list[LLMExecutedToolCall] = []
        raw_provider_messages: list[dict[str, Any]] = []
        usage_totals: dict[str, Any] = {}

        try:
            for _ in range(max_tool_calls + 1):
                message = self._client.messages.create(
                    model=self._settings.minimax_model,
                    max_tokens=effective_max_tokens,
                    system=system or "You are a concise assistant.",
                    messages=provider_messages,
                    tools=tools,
                )
                raw_content = self._extract_raw_content(message.content)
                raw_provider_messages.append(
                    {
                        "id": getattr(message, "id", None),
                        "model": getattr(message, "model", self._settings.minimax_model),
                        "stop_reason": getattr(message, "stop_reason", None),
                        "content": raw_content,
                        "usage": self._extract_usage(message),
                    }
                )
                usage_totals = self._merge_usage(
                    usage_totals,
                    self._extract_usage(message),
                )
                tool_uses = self._extract_tool_uses(message.content)
                if not tool_uses:
                    return LLMTextResult(
                        model=getattr(message, "model", self._settings.minimax_model),
                        text=self._extract_text(message.content),
                        usage=usage_totals,
                        provider_message_id=getattr(message, "id", None),
                        raw_content=raw_content,
                        stop_reason=getattr(message, "stop_reason", None),
                        tool_calls=executed_tool_calls,
                        raw_provider_messages=raw_provider_messages,
                    )

                provider_messages.append(
                    {
                        "role": "assistant",
                        "content": raw_content,
                    }
                )
                tool_results: list[dict[str, Any]] = []
                for tool_use in tool_uses:
                    executed = tool_runner(tool_use)
                    executed_tool_calls.append(executed)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(executed.result, ensure_ascii=True),
                            "is_error": executed.status != "completed",
                        }
                    )
                provider_messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        raise LLMRequestError(
            f"MiniMax tool loop exceeded max_tool_calls={max_tool_calls}."
        )

    def stream_chat_with_tools(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]],
        tool_runner: LLMToolRunner,
        max_tool_calls: int = 4,
    ) -> Iterator[LLMStreamEvent]:
        effective_max_tokens = max_tokens or self._settings.minimax_max_tokens
        provider_messages = [self._to_anthropic_message(item) for item in messages]
        executed_tool_calls: list[LLMExecutedToolCall] = []
        raw_provider_messages: list[dict[str, Any]] = []
        usage_totals: dict[str, Any] = {}

        try:
            for step in range(max_tool_calls + 1):
                yield LLMStreamEvent(
                    type="model_request",
                    data={"step": step + 1, "model": self._settings.minimax_model},
                )
                with self._client.messages.stream(
                    model=self._settings.minimax_model,
                    max_tokens=effective_max_tokens,
                    system=system or "You are a concise assistant.",
                    messages=provider_messages,
                    tools=tools,
                ) as stream:
                    for event in stream:
                        for stream_event in self._stream_events_from_raw_event(event):
                            stream_event.data["model_step"] = step + 1
                            yield stream_event
                    message = stream.get_final_message()

                raw_content = self._extract_raw_content(message.content)
                raw_provider_messages.append(
                    {
                        "id": getattr(message, "id", None),
                        "model": getattr(message, "model", self._settings.minimax_model),
                        "stop_reason": getattr(message, "stop_reason", None),
                        "content": raw_content,
                        "usage": self._extract_usage(message),
                    }
                )
                usage_totals = self._merge_usage(
                    usage_totals,
                    self._extract_usage(message),
                )
                tool_uses = self._extract_tool_uses(message.content)
                if not tool_uses:
                    yield LLMStreamEvent(
                        type="final_result",
                        data={
                            "result": LLMTextResult(
                                model=getattr(
                                    message,
                                    "model",
                                    self._settings.minimax_model,
                                ),
                                text=self._extract_text(message.content),
                                usage=usage_totals,
                                provider_message_id=getattr(message, "id", None),
                                raw_content=raw_content,
                                stop_reason=getattr(message, "stop_reason", None),
                                tool_calls=executed_tool_calls,
                                raw_provider_messages=raw_provider_messages,
                            ).model_dump(mode="json")
                        },
                    )
                    return

                provider_messages.append(
                    {
                        "role": "assistant",
                        "content": raw_content,
                    }
                )
                tool_results: list[dict[str, Any]] = []
                for tool_use in tool_uses:
                    yield LLMStreamEvent(
                        type="tool_call",
                        data={
                            "model_step": step + 1,
                            "provider_tool_use_id": tool_use.id,
                            "tool_name": tool_use.name,
                            "arguments": tool_use.input,
                        },
                    )
                    executed = tool_runner(tool_use)
                    executed_tool_calls.append(executed)
                    yield LLMStreamEvent(
                        type="tool_result",
                        data={
                            "model_step": step + 1,
                            **executed.model_dump(mode="json"),
                        },
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(executed.result, ensure_ascii=True),
                            "is_error": executed.status != "completed",
                        }
                    )
                provider_messages.append(
                    {
                        "role": "user",
                        "content": tool_results,
                    }
                )
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        raise LLMRequestError(
            f"MiniMax tool loop exceeded max_tool_calls={max_tool_calls}."
        )

    def _sanitize_error(self, message: str) -> str:
        api_key = self._settings.minimax_api_key
        if api_key:
            return message.replace(api_key, "***")
        return message

    @staticmethod
    def _extract_text(content_blocks: list[Any]) -> str:
        text_parts: list[str] = []
        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                text = getattr(block, "text", "")
                if text:
                    text_parts.append(text)
        return "\n".join(text_parts).strip()

    @staticmethod
    def _to_anthropic_message(message: LLMMessage) -> dict[str, Any]:
        return {
            "role": message.role,
            "content": [{"type": "text", "text": message.content}],
        }

    @staticmethod
    def _extract_raw_content(content_blocks: list[Any]) -> list[dict[str, Any]]:
        raw_blocks: list[dict[str, Any]] = []
        for block in content_blocks:
            if hasattr(block, "model_dump"):
                raw_blocks.append(block.model_dump())
            elif isinstance(block, dict):
                raw_blocks.append(block)
        return raw_blocks

    @staticmethod
    def _extract_tool_uses(content_blocks: list[Any]) -> list[LLMToolUse]:
        tool_uses: list[LLMToolUse] = []
        for block in content_blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            tool_input = getattr(block, "input", {})
            if not isinstance(tool_input, dict):
                tool_input = {}
            tool_uses.append(
                LLMToolUse(
                    id=getattr(block, "id", ""),
                    name=getattr(block, "name", ""),
                    input=tool_input,
                )
            )
        return tool_uses

    @staticmethod
    def _extract_usage(message: Any) -> dict[str, Any]:
        usage = getattr(message, "usage", None)
        if usage is None:
            return {}
        if hasattr(usage, "model_dump"):
            return usage.model_dump()
        if isinstance(usage, dict):
            return usage
        return {}

    @staticmethod
    def _stream_events_from_raw_event(event: Any) -> Iterator[LLMStreamEvent]:
        event_type = getattr(event, "type", "")
        if event_type == "content_block_start":
            block = getattr(event, "content_block", None)
            block_type = getattr(block, "type", None)
            if block_type == "thinking":
                yield LLMStreamEvent(
                    type="thinking_start",
                    data={"index": getattr(event, "index", None)},
                )
            elif block_type == "tool_use":
                yield LLMStreamEvent(
                    type="tool_use_start",
                    data={
                        "index": getattr(event, "index", None),
                        "provider_tool_use_id": getattr(block, "id", None),
                        "tool_name": getattr(block, "name", None),
                    },
                )
            elif block_type == "text":
                yield LLMStreamEvent(
                    type="text_start",
                    data={"index": getattr(event, "index", None)},
                )
            return

        if event_type == "content_block_delta":
            delta = getattr(event, "delta", None)
            delta_type = getattr(delta, "type", None)
            if delta_type == "thinking_delta":
                yield LLMStreamEvent(
                    type="thinking_delta",
                    data={
                        "index": getattr(event, "index", None),
                        "text": getattr(delta, "thinking", ""),
                    },
                )
            elif delta_type == "text_delta":
                yield LLMStreamEvent(
                    type="text_delta",
                    data={
                        "index": getattr(event, "index", None),
                        "text": getattr(delta, "text", ""),
                    },
                )
            elif delta_type == "input_json_delta":
                yield LLMStreamEvent(
                    type="tool_input_delta",
                    data={
                        "index": getattr(event, "index", None),
                        "partial_json": getattr(delta, "partial_json", ""),
                    },
                )
            return

        if event_type == "message_delta":
            delta = getattr(event, "delta", None)
            stop_reason = getattr(delta, "stop_reason", None)
            if stop_reason:
                yield LLMStreamEvent(
                    type="model_stop",
                    data={"stop_reason": stop_reason},
                )

    @staticmethod
    def _merge_usage(
        totals: dict[str, Any],
        usage: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(totals)
        for key, value in usage.items():
            if isinstance(value, int) and isinstance(merged.get(key), int):
                merged[key] += value
            elif isinstance(value, int) and key not in merged:
                merged[key] = value
            elif key not in merged:
                merged[key] = value
        return merged

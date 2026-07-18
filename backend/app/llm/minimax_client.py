import json
from collections.abc import Iterator
from typing import Any

import anthropic

from app.config import Settings
from app.llm.provider import (
    LLMConfigurationError,
    LLMExecutedToolCall,
    LLMIncompleteResponseError,
    LLMMessage,
    LLMRequestError,
    LLMStreamEvent,
    LLMTextResult,
    LLMToolRunner,
    LLMToolUse,
)


class AnthropicCompatibleProvider:
    """Provider implementation for Anthropic-compatible Messages APIs."""

    def __init__(
        self,
        *,
        api_key: str | None,
        api_key_name: str,
        base_url: str,
        model: str,
        max_tokens: int,
        provider_name: str,
        incomplete_final_max_retries: int = 1,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError(f"{api_key_name} is not configured.")

        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._provider_name = provider_name
        self._incomplete_final_max_retries = incomplete_final_max_retries
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
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
        effective_max_tokens = max_tokens or self._max_tokens
        return self._generate_chat_via_stream(
            messages=messages,
            system=system,
            max_tokens=effective_max_tokens,
        )

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
        effective_max_tokens = max_tokens or self._max_tokens
        return self._collect_final_stream_result(
            self.stream_chat_with_tools(
                messages=messages,
                system=system,
                max_tokens=effective_max_tokens,
                tools=tools,
                tool_runner=tool_runner,
                max_tool_calls=max_tool_calls,
            )
        )

    def _generate_chat_via_stream(
        self,
        *,
        messages: list[LLMMessage],
        system: str | None,
        max_tokens: int,
    ) -> LLMTextResult:
        provider_messages = [self._to_anthropic_message(item) for item in messages]
        try:
            stream_kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": max_tokens,
                "system": system or "You are a concise assistant.",
                "messages": provider_messages,
            }
            thinking_config = self._thinking_config()
            if thinking_config is not None:
                stream_kwargs["thinking"] = thinking_config
            with self._client.messages.stream(
                **stream_kwargs,
            ) as stream:
                for _event in stream:
                    pass
                message = stream.get_final_message()
        except anthropic.AnthropicError as exc:
            raise LLMRequestError(self._sanitize_error(str(exc))) from exc

        raw_content = self._extract_raw_content(message.content)
        return LLMTextResult(
            model=getattr(message, "model", self._model),
            text=self._extract_text(message.content),
            usage=self._extract_usage(message),
            provider_message_id=getattr(message, "id", None),
            raw_content=raw_content,
            stop_reason=getattr(message, "stop_reason", None),
            raw_provider_messages=[
                {
                    "id": getattr(message, "id", None),
                    "model": getattr(message, "model", self._model),
                    "stop_reason": getattr(message, "stop_reason", None),
                    "content": raw_content,
                    "usage": self._extract_usage(message),
                }
            ],
        )

    @staticmethod
    def _collect_final_stream_result(events: Iterator[LLMStreamEvent]) -> LLMTextResult:
        for event in events:
            if event.type != "final_result":
                continue
            return LLMTextResult.model_validate(event.data["result"])
        raise LLMRequestError("Provider stream ended without a final_result event.")

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
        effective_max_tokens = max_tokens or self._max_tokens
        provider_messages = [self._to_anthropic_message(item) for item in messages]
        executed_tool_calls: list[LLMExecutedToolCall] = []
        raw_provider_messages: list[dict[str, Any]] = []
        completion_recovery_attempts: list[dict[str, Any]] = []
        usage_totals: dict[str, Any] = {}

        try:
            step = 0
            while max_tool_calls is None or step <= max_tool_calls:
                step += 1
                yield LLMStreamEvent(
                    type="model_request",
                    data={"step": step, "model": self._model},
                )
                stream_kwargs: dict[str, Any] = {
                    "model": self._model,
                    "max_tokens": effective_max_tokens,
                    "system": system or "You are a concise assistant.",
                    "messages": provider_messages,
                    "tools": tools,
                }
                thinking_config = self._thinking_config()
                if thinking_config is not None:
                    stream_kwargs["thinking"] = thinking_config
                with self._client.messages.stream(
                    **stream_kwargs,
                ) as stream:
                    for event in stream:
                        for stream_event in self._stream_events_from_raw_event(event):
                            stream_event.data["model_step"] = step
                            yield stream_event
                    message = stream.get_final_message()

                raw_content = self._extract_raw_content(message.content)
                stop_reason = getattr(message, "stop_reason", None)
                provider_message_id = getattr(message, "id", None)
                raw_message = {
                    "id": provider_message_id,
                    "model": getattr(message, "model", self._model),
                    "stop_reason": stop_reason,
                    "content": raw_content,
                    "usage": self._extract_usage(message),
                }
                usage_totals = self._merge_usage(
                    usage_totals,
                    self._extract_usage(message),
                )
                tool_uses = self._extract_tool_uses(message.content)
                for semantic_event in self._semantic_events_from_raw_content(
                    raw_content,
                    provider_message_id=provider_message_id,
                    stop_reason=stop_reason,
                    model_step=step,
                ):
                    yield semantic_event
                if not tool_uses:
                    final_text = self._extract_text(message.content)
                    if not final_text:
                        recovery_attempt_count = sum(
                            1
                            for attempt in completion_recovery_attempts
                            if attempt.get("recoverable") is True
                        )
                        recoverable = (
                            stop_reason == "end_turn"
                            and self._has_thinking_content(raw_content)
                            and recovery_attempt_count
                            < self._incomplete_final_max_retries
                        )
                        incomplete = {
                            **raw_message,
                            "reason": "thinking_only_end_turn"
                            if self._has_thinking_content(raw_content)
                            else "empty_terminal_message",
                            "recoverable": recoverable,
                        }
                        completion_recovery_attempts.append(incomplete)
                        if recoverable:
                            yield LLMStreamEvent(
                                type="completion_recovery",
                                data={
                                    "model_step": step,
                                    "attempt": len(completion_recovery_attempts),
                                    "reason": incomplete["reason"],
                                    "provider_message_id": provider_message_id,
                                    "stop_reason": stop_reason,
                                },
                            )
                            provider_messages.extend(
                                [
                                    {"role": "assistant", "content": raw_content},
                                    self._completion_continuation_message(),
                                ]
                            )
                            continue
                        raise LLMIncompleteResponseError(
                            (
                                f"{self._provider_name} ended without public text "
                                "or a tool call."
                            ),
                            details={
                                "reason": incomplete["reason"],
                                "stop_reason": stop_reason,
                                "provider_message_id": provider_message_id,
                                "recovery_attempt_count": sum(
                                    1
                                    for attempt in completion_recovery_attempts
                                    if attempt.get("recoverable") is True
                                ),
                                "terminal_message_count": len(
                                    completion_recovery_attempts
                                ),
                                "recovery_limit": self._incomplete_final_max_retries,
                            },
                        )
                    raw_provider_messages.append(raw_message)
                    yield LLMStreamEvent(
                        type="final_result",
                        data={
                            "result": LLMTextResult(
                                model=getattr(
                                    message,
                                    "model",
                                    self._model,
                                ),
                                text=final_text,
                                usage=usage_totals,
                                provider_message_id=getattr(message, "id", None),
                                raw_content=raw_content,
                                stop_reason=getattr(message, "stop_reason", None),
                                tool_calls=executed_tool_calls,
                                raw_provider_messages=raw_provider_messages,
                                completion_recovery={
                                    "attempted": bool(completion_recovery_attempts),
                                    "recovered": bool(completion_recovery_attempts),
                                    "attempt_count": len(completion_recovery_attempts),
                                    "attempts": completion_recovery_attempts,
                                },
                            ).model_dump(mode="json")
                        },
                    )
                    return

                raw_provider_messages.append(raw_message)
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
                            "model_step": step,
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
                            "model_step": step,
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
            f"{self._provider_name} tool loop exceeded max_tool_calls={max_tool_calls}."
        )

    def _sanitize_error(self, message: str) -> str:
        if self._api_key:
            return message.replace(self._api_key, "***")
        return message

    def _thinking_config(self) -> dict[str, str] | None:
        if self._model.startswith("MiniMax-M3"):
            return {"type": "adaptive"}
        return None

    @staticmethod
    def _has_thinking_content(raw_content: list[dict[str, Any]]) -> bool:
        return any(block.get("type") == "thinking" for block in raw_content)

    @staticmethod
    def _completion_continuation_message() -> dict[str, Any]:
        return {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Your previous message ended without a public answer or "
                        "a tool call. Continue the same turn now. Use a real tool "
                        "call if one is required; otherwise provide the final public "
                        "answer. Do not quote or expose private thinking."
                    ),
                }
            ],
        }

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
        if isinstance(message.content, list):
            return {
                "role": message.role,
                "content": message.content,
            }
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
    def _semantic_events_from_raw_content(
        raw_content: list[dict[str, Any]],
        *,
        provider_message_id: str | None,
        stop_reason: str | None,
        model_step: int,
    ) -> Iterator[LLMStreamEvent]:
        has_tool_use = any(block.get("type") == "tool_use" for block in raw_content)
        text_event_type = "assistant_note" if has_tool_use else "assistant_answer"
        for index, block in enumerate(raw_content):
            block_type = block.get("type")
            if block_type == "thinking":
                thinking = block.get("thinking")
                yield LLMStreamEvent(
                    type="thinking_captured",
                    data={
                        "index": index,
                        "model_step": model_step,
                        "provider_message_id": provider_message_id,
                        "stop_reason": stop_reason,
                        "text": thinking if isinstance(thinking, str) else "",
                        "has_text": isinstance(thinking, str)
                        and bool(thinking.strip()),
                    },
                )
            elif block_type == "text":
                text = block.get("text")
                if not isinstance(text, str) or not text.strip():
                    continue
                yield LLMStreamEvent(
                    type=text_event_type,
                    data={
                        "index": index,
                        "model_step": model_step,
                        "provider_message_id": provider_message_id,
                        "stop_reason": stop_reason,
                        "text": text.strip(),
                    },
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


class MiniMaxProvider(AnthropicCompatibleProvider):
    """MiniMax provider through the Anthropic-compatible API."""

    def __init__(self, settings: Settings) -> None:
        super().__init__(
            api_key=settings.minimax_api_key,
            api_key_name="MINIMAX_API_KEY",
            base_url=settings.minimax_base_url,
            model=settings.minimax_model,
            max_tokens=settings.minimax_max_tokens,
            provider_name="MiniMax",
            incomplete_final_max_retries=settings.incomplete_final_max_retries,
        )

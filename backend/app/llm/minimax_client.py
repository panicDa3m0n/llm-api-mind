import json
import time
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
        stream_max_attempts: int = 5,
        stream_retry_backoff_seconds: float = 0.5,
        max_token_continuations: int = 8,
    ) -> None:
        if not api_key:
            raise LLMConfigurationError(f"{api_key_name} is not configured.")

        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._provider_name = provider_name
        self._stream_max_attempts = stream_max_attempts
        self._stream_retry_backoff_seconds = stream_retry_backoff_seconds
        self._max_token_continuations = max_token_continuations
        self._client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
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
        raw_provider_messages: list[dict[str, Any]] = []
        provider_history_tail: list[dict[str, Any]] = []
        text_segments: list[str] = []
        usage_totals: dict[str, Any] = {}
        continuation_attempts: list[dict[str, Any]] = []
        step = 0

        while True:
            step += 1
            message = self._collect_provider_message(
                self._stream_provider_message(
                    provider_messages=provider_messages,
                    system=system,
                    max_tokens=max_tokens,
                    tools=None,
                    model_step=step,
                )
            )
            raw_content = self._extract_raw_content(message.content)
            stop_reason = getattr(message, "stop_reason", None)
            provider_message_id = getattr(message, "id", None)
            usage = self._extract_usage(message)
            raw_message = {
                "id": provider_message_id,
                "model": getattr(message, "model", self._model),
                "stop_reason": stop_reason,
                "content": raw_content,
                "usage": usage,
            }
            raw_provider_messages.append(raw_message)
            usage_totals = self._merge_usage(usage_totals, usage)
            segment = self._extract_text(message.content)
            if segment:
                text_segments.append(segment)

            if stop_reason == "max_tokens":
                if self._extract_tool_uses(message.content):
                    raise self._truncated_tool_use_error(raw_message)
                self._ensure_continuation_available(
                    continuation_attempts,
                    raw_message=raw_message,
                )
                continuation_attempts.append(
                    {
                        "provider_message_id": provider_message_id,
                        "model_step": step,
                        "stop_reason": stop_reason,
                    }
                )
                assistant_history = {"role": "assistant", "content": raw_content}
                continuation = self._max_tokens_continuation_message()
                provider_messages.extend([assistant_history, continuation])
                provider_history_tail.extend([assistant_history, continuation])
                continue

            if stop_reason != "end_turn":
                raise LLMIncompleteResponseError(
                    f"{self._provider_name} ended with unsupported stop reason.",
                    details={
                        "reason": "unexpected_stop_reason",
                        "stop_reason": stop_reason,
                        "provider_message_id": provider_message_id,
                    },
                )
            final_text = "\n".join(text_segments).strip()
            if not final_text:
                raise self._empty_end_turn_error(raw_message)
            provider_history_tail.append(
                {"role": "assistant", "content": raw_content}
            )
            return LLMTextResult(
                model=getattr(message, "model", self._model),
                text=final_text,
                usage=usage_totals,
                provider_message_id=provider_message_id,
                raw_content=raw_content,
                stop_reason=stop_reason,
                raw_provider_messages=raw_provider_messages,
                completion_recovery=self._continuation_metadata(
                    continuation_attempts
                ),
                provider_history_tail=provider_history_tail,
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
        provider_history_tail: list[dict[str, Any]] = []
        continuation_attempts: list[dict[str, Any]] = []
        pending_text_segments: list[str] = []
        usage_totals: dict[str, Any] = {}

        step = 0
        tool_call_count = 0
        while max_tool_calls is None or tool_call_count < max_tool_calls:
            step += 1
            message = yield from self._stream_provider_message(
                provider_messages=provider_messages,
                system=system,
                max_tokens=effective_max_tokens,
                tools=tools,
                model_step=step,
            )

            raw_content = self._extract_raw_content(message.content)
            stop_reason = getattr(message, "stop_reason", None)
            provider_message_id = getattr(message, "id", None)
            usage = self._extract_usage(message)
            raw_message = {
                "id": provider_message_id,
                "model": getattr(message, "model", self._model),
                "stop_reason": stop_reason,
                "content": raw_content,
                "usage": usage,
            }
            raw_provider_messages.append(raw_message)
            usage_totals = self._merge_usage(usage_totals, usage)
            tool_uses = self._extract_tool_uses(message.content)
            segment = self._extract_text(message.content)

            for semantic_event in self._semantic_events_from_raw_content(
                raw_content,
                provider_message_id=provider_message_id,
                stop_reason=stop_reason,
                model_step=step,
            ):
                yield semantic_event

            if stop_reason == "max_tokens":
                if tool_uses:
                    raise self._truncated_tool_use_error(raw_message)
                self._ensure_continuation_available(
                    continuation_attempts,
                    raw_message=raw_message,
                )
                if segment:
                    pending_text_segments.append(segment)
                continuation_attempts.append(
                    {
                        "provider_message_id": provider_message_id,
                        "model_step": step,
                        "stop_reason": stop_reason,
                    }
                )
                yield LLMStreamEvent(
                    type="completion_recovery",
                    data={
                        "model_step": step,
                        "attempt": len(continuation_attempts),
                        "reason": "max_tokens",
                        "provider_message_id": provider_message_id,
                        "stop_reason": stop_reason,
                    },
                )
                assistant_history = {"role": "assistant", "content": raw_content}
                continuation = self._max_tokens_continuation_message()
                provider_messages.extend([assistant_history, continuation])
                provider_history_tail.extend([assistant_history, continuation])
                continue

            if stop_reason == "end_turn":
                if tool_uses:
                    raise LLMIncompleteResponseError(
                        f"{self._provider_name} returned tool blocks at end_turn.",
                        details={
                            "reason": "tool_use_with_end_turn",
                            "stop_reason": stop_reason,
                            "provider_message_id": provider_message_id,
                        },
                    )
                final_text = "\n".join(
                    [*pending_text_segments, *([segment] if segment else [])]
                ).strip()
                if not final_text:
                    raise self._empty_end_turn_error(raw_message)
                provider_history_tail.append(
                    {"role": "assistant", "content": raw_content}
                )
                yield LLMStreamEvent(
                    type="final_result",
                    data={
                        "result": LLMTextResult(
                            model=getattr(message, "model", self._model),
                            text=final_text,
                            usage=usage_totals,
                            provider_message_id=provider_message_id,
                            raw_content=raw_content,
                            stop_reason=stop_reason,
                            tool_calls=executed_tool_calls,
                            raw_provider_messages=raw_provider_messages,
                            completion_recovery=self._continuation_metadata(
                                continuation_attempts
                            ),
                            provider_history_tail=provider_history_tail,
                        ).model_dump(mode="json")
                    },
                )
                return

            if stop_reason != "tool_use" or not tool_uses:
                raise LLMIncompleteResponseError(
                    f"{self._provider_name} returned an inconsistent tool response.",
                    details={
                        "reason": "tool_stop_mismatch",
                        "stop_reason": stop_reason,
                        "provider_message_id": provider_message_id,
                        "tool_use_count": len(tool_uses),
                    },
                )

            pending_text_segments.clear()
            assistant_history = {"role": "assistant", "content": raw_content}
            provider_messages.append(assistant_history)
            provider_history_tail.append(assistant_history)
            tool_results: list[dict[str, Any]] = []
            for tool_use in tool_uses:
                tool_call_count += 1
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
            tool_history = {"role": "user", "content": tool_results}
            provider_messages.append(tool_history)
            provider_history_tail.append(tool_history)

        raise LLMRequestError(
            f"{self._provider_name} tool loop exceeded max_tool_calls={max_tool_calls}."
        )

    def _stream_provider_message(
        self,
        *,
        provider_messages: list[dict[str, Any]],
        system: str | None,
        max_tokens: int,
        tools: list[dict[str, Any]] | None,
        model_step: int,
    ) -> Iterator[LLMStreamEvent]:
        for attempt in range(1, self._stream_max_attempts + 1):
            yield LLMStreamEvent(
                type="model_request",
                data={
                    "step": model_step,
                    "model": self._model,
                    "provider_attempt": attempt,
                    "provider_attempt_limit": self._stream_max_attempts,
                },
            )
            stream_kwargs: dict[str, Any] = {
                "model": self._model,
                "max_tokens": max_tokens,
                "system": system or "You are a concise assistant.",
                "messages": provider_messages,
            }
            if tools is not None:
                stream_kwargs["tools"] = tools
            thinking_config = self._thinking_config()
            if thinking_config is not None:
                stream_kwargs["thinking"] = thinking_config
            try:
                with self._client.messages.stream(**stream_kwargs) as stream:
                    for event in stream:
                        for stream_event in self._stream_events_from_raw_event(event):
                            stream_event.data.update(
                                {
                                    "model_step": model_step,
                                    "provider_attempt": attempt,
                                }
                            )
                            yield stream_event
                    return stream.get_final_message()
            except anthropic.AnthropicError as exc:
                sanitized_error = self._sanitize_error(str(exc))
                if (
                    attempt >= self._stream_max_attempts
                    or not self._is_retryable_provider_error(exc)
                ):
                    raise LLMRequestError(sanitized_error) from exc
                yield LLMStreamEvent(
                    type="provider_retry",
                    data={
                        "model_step": model_step,
                        "provider_attempt": attempt,
                        "next_provider_attempt": attempt + 1,
                        "provider_attempt_limit": self._stream_max_attempts,
                        "error": sanitized_error,
                    },
                )
                delay = self._stream_retry_backoff_seconds * (2 ** (attempt - 1))
                if delay:
                    time.sleep(delay)
        raise AssertionError("provider retry loop must return or raise")

    @staticmethod
    def _is_retryable_provider_error(exc: anthropic.AnthropicError) -> bool:
        if isinstance(
            exc,
            (anthropic.APIConnectionError, anthropic.APITimeoutError),
        ):
            return True
        if isinstance(exc, anthropic.APIStatusError):
            return exc.status_code in {408, 409, 429} or exc.status_code >= 500
        return False

    @staticmethod
    def _collect_provider_message(
        events: Iterator[LLMStreamEvent],
    ) -> Any:
        while True:
            try:
                next(events)
            except StopIteration as completed:
                return completed.value

    def _sanitize_error(self, message: str) -> str:
        if self._api_key:
            return message.replace(self._api_key, "***")
        return message

    def _thinking_config(self) -> dict[str, str] | None:
        if self._model.startswith("MiniMax-M3"):
            return {"type": "adaptive"}
        return None

    @staticmethod
    def _max_tokens_continuation_message() -> dict[str, Any]:
        return {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Continue the same assistant response exactly from where it "
                        "stopped because the previous provider response reached "
                        "max_tokens. Do not repeat completed content. Continue using "
                        "tools if the task requires them; otherwise finish the answer."
                    ),
                }
            ],
        }

    def _empty_end_turn_error(
        self,
        raw_message: dict[str, Any],
    ) -> LLMIncompleteResponseError:
        raw_content = raw_message["content"]
        reason = (
            "thinking_only_end_turn"
            if any(block.get("type") == "thinking" for block in raw_content)
            else "empty_end_turn"
        )
        return LLMIncompleteResponseError(
            f"{self._provider_name} ended the turn without public text.",
            details={
                "reason": reason,
                "stop_reason": raw_message["stop_reason"],
                "provider_message_id": raw_message["id"],
                "recoverable": False,
            },
        )

    def _truncated_tool_use_error(
        self,
        raw_message: dict[str, Any],
    ) -> LLMIncompleteResponseError:
        return LLMIncompleteResponseError(
            f"{self._provider_name} truncated a tool request at max_tokens.",
            details={
                "reason": "truncated_tool_use",
                "stop_reason": raw_message["stop_reason"],
                "provider_message_id": raw_message["id"],
                "recoverable": False,
            },
        )

    def _ensure_continuation_available(
        self,
        attempts: list[dict[str, Any]],
        *,
        raw_message: dict[str, Any],
    ) -> None:
        if len(attempts) < self._max_token_continuations:
            return
        raise LLMIncompleteResponseError(
            f"{self._provider_name} repeatedly exhausted max_tokens.",
            details={
                "reason": "max_tokens_continuation_limit",
                "stop_reason": raw_message["stop_reason"],
                "provider_message_id": raw_message["id"],
                "continuation_count": len(attempts),
                "continuation_limit": self._max_token_continuations,
                "recoverable": False,
            },
        )

    @staticmethod
    def _continuation_metadata(
        attempts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "attempted": bool(attempts),
            "recovered": bool(attempts),
            "reason": "max_tokens" if attempts else None,
            "attempt_count": len(attempts),
            "attempts": attempts,
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
        text_event_type = {
            "tool_use": "assistant_note",
            "end_turn": "assistant_answer",
            "max_tokens": "assistant_continuation",
        }.get(stop_reason)
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
                if (
                    text_event_type is None
                    or not isinstance(text, str)
                    or not text.strip()
                ):
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
            stream_max_attempts=settings.provider_stream_max_attempts,
            stream_retry_backoff_seconds=(
                settings.provider_stream_retry_backoff_seconds
            ),
            max_token_continuations=settings.provider_max_token_continuations,
        )

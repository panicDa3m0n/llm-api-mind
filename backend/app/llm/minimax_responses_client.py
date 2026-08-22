"""MiniMax Responses adapter for transient multimodal Scarlet turns.

The native Scarlet runtime remains provider-neutral. This adapter translates
the canonical text/tool history to MiniMax's Responses contract only while a
turn carries transient image or video input. Raw media is deliberately absent
from the returned provider-history tail.
"""

from __future__ import annotations

import json
import time
from collections.abc import Generator, Iterator
from typing import Any

import httpx

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


class MiniMaxResponsesProvider:
    """OpenAI Responses-compatible MiniMax adapter with a Mind tool loop."""

    def __init__(
        self,
        settings: Settings,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        if not settings.minimax_api_key:
            raise LLMConfigurationError("MINIMAX_API_KEY is not configured.")
        self._api_key = settings.minimax_api_key
        self._model = settings.minimax_model
        self._max_tokens = settings.minimax_max_tokens
        self._stream_max_attempts = settings.provider_stream_max_attempts
        self._retry_backoff_seconds = settings.provider_stream_retry_backoff_seconds
        self._max_token_continuations = settings.provider_max_token_continuations
        self._client = client or httpx.Client(
            base_url=settings.minimax_responses_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.minimax_api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(300.0, connect=30.0),
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
        return self._collect_final_result(
            self.stream_chat_with_tools(
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                tools=[],
                tool_runner=self._unexpected_tool_runner,
                max_tool_calls=0,
            )
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
        return self._collect_final_result(
            self.stream_chat_with_tools(
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                tools=tools,
                tool_runner=tool_runner,
                max_tool_calls=max_tool_calls,
            )
        )

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
        provider_input = self._messages_to_responses_input(messages)
        response_tools = [self._to_responses_tool(tool) for tool in tools]
        effective_max_tokens = max_tokens or self._max_tokens
        executed_tool_calls: list[LLMExecutedToolCall] = []
        raw_provider_messages: list[dict[str, Any]] = []
        provider_history_tail: list[dict[str, Any]] = []
        pending_text_segments: list[str] = []
        continuation_attempts: list[dict[str, Any]] = []
        usage_totals: dict[str, Any] = {}
        step = 0
        tool_call_count = 0

        while max_tool_calls is None or tool_call_count <= max_tool_calls:
            step += 1
            payload: dict[str, Any] = {
                "model": self._model,
                "input": provider_input,
                "instructions": system or "You are a concise assistant.",
                "max_output_tokens": effective_max_tokens,
                "stream": True,
                "reasoning": {"effort": "medium"},
            }
            if response_tools:
                payload["tools"] = response_tools
                payload["tool_choice"] = "auto"

            response = yield from self._stream_response(payload, model_step=step)
            status = response.get("status")
            output = response.get("output")
            if not isinstance(output, list):
                output = []
            raw_content, tool_uses = self._normalize_output(output)
            text_segment = self._extract_text(raw_content)
            usage = response.get("usage")
            if not isinstance(usage, dict):
                usage = {}
            usage_totals = self._merge_usage(usage_totals, usage)
            provider_message_id = self._string(response.get("id"))
            stop_reason = self._stop_reason(response, tool_uses)
            raw_message = {
                "id": provider_message_id,
                "model": response.get("model", self._model),
                "status": status,
                "stop_reason": stop_reason,
                "content": raw_content,
                "usage": usage,
            }
            raw_provider_messages.append(raw_message)

            for event in self._semantic_events(
                raw_content,
                provider_message_id=provider_message_id,
                stop_reason=stop_reason,
                model_step=step,
            ):
                yield event

            assistant_history = (
                {"role": "assistant", "content": raw_content}
                if raw_content
                else None
            )

            if status == "incomplete":
                reason = self._incomplete_reason(response)
                if reason != "max_output_tokens" or tool_uses:
                    raise LLMIncompleteResponseError(
                        "MiniMax Responses ended before a complete model step.",
                        details={
                            "reason": reason or "responses_incomplete",
                            "provider_message_id": provider_message_id,
                            "tool_use_count": len(tool_uses),
                        },
                    )
                if len(continuation_attempts) >= self._max_token_continuations:
                    raise LLMIncompleteResponseError(
                        "MiniMax Responses repeatedly exhausted max_output_tokens.",
                        details={
                            "reason": "max_tokens_continuation_limit",
                            "continuation_count": len(continuation_attempts),
                            "continuation_limit": self._max_token_continuations,
                        },
                    )
                if text_segment:
                    pending_text_segments.append(text_segment)
                continuation_attempts.append(
                    {
                        "provider_message_id": provider_message_id,
                        "model_step": step,
                        "stop_reason": "max_tokens",
                    }
                )
                yield LLMStreamEvent(
                    type="completion_recovery",
                    data={
                        "model_step": step,
                        "attempt": len(continuation_attempts),
                        "reason": "max_tokens",
                        "provider_message_id": provider_message_id,
                        "stop_reason": "max_tokens",
                    },
                )
                provider_input.extend(output)
                continuation = self._continuation_input()
                provider_input.append(continuation)
                if assistant_history is not None:
                    provider_history_tail.append(assistant_history)
                provider_history_tail.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": continuation["content"][0]["text"],
                            }
                        ],
                    }
                )
                continue

            if status == "failed":
                error = response.get("error")
                raise LLMRequestError(
                    self._sanitize_error(json.dumps(error, ensure_ascii=True))
                )
            if status != "completed":
                raise LLMIncompleteResponseError(
                    "MiniMax Responses returned an unsupported terminal status.",
                    details={
                        "reason": "unexpected_responses_status",
                        "status": status,
                        "provider_message_id": provider_message_id,
                    },
                )

            if tool_uses:
                pending_text_segments.clear()
                if assistant_history is not None:
                    provider_history_tail.append(assistant_history)
                provider_input.extend(output)
                canonical_tool_results: list[dict[str, Any]] = []
                for tool_use in tool_uses:
                    if max_tool_calls is not None and tool_call_count >= max_tool_calls:
                        raise LLMRequestError(
                            "MiniMax Responses tool loop exceeded max_tool_calls."
                        )
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
                    serialized_result = json.dumps(
                        executed.result,
                        ensure_ascii=True,
                    )
                    output_value: str | list[dict[str, Any]] = serialized_result
                    if executed.provider_content_parts:
                        output_value = [
                            {"type": "input_text", "text": serialized_result},
                            *executed.provider_content_parts,
                        ]
                    provider_input.append(
                        {
                            "type": "function_call_output",
                            "call_id": tool_use.id,
                            "output": output_value,
                        }
                    )
                    canonical_tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": serialized_result,
                            "is_error": executed.status != "completed",
                        }
                    )
                provider_history_tail.append(
                    {"role": "user", "content": canonical_tool_results}
                )
                continue

            final_text = "\n".join(
                [*pending_text_segments, *([text_segment] if text_segment else [])]
            ).strip()
            if not final_text:
                raise LLMIncompleteResponseError(
                    "MiniMax Responses completed without public text.",
                    details={
                        "reason": "empty_end_turn",
                        "provider_message_id": provider_message_id,
                    },
                )
            if assistant_history is not None:
                provider_history_tail.append(assistant_history)
            yield LLMStreamEvent(
                type="final_result",
                data={
                    "result": LLMTextResult(
                        model=self._string(response.get("model")) or self._model,
                        text=final_text,
                        usage=usage_totals,
                        provider_message_id=provider_message_id,
                        raw_content=raw_content,
                        stop_reason="end_turn",
                        tool_calls=executed_tool_calls,
                        raw_provider_messages=raw_provider_messages,
                        completion_recovery={
                            "attempted": bool(continuation_attempts),
                            "recovered": bool(continuation_attempts),
                            "reason": (
                                "max_tokens" if continuation_attempts else None
                            ),
                            "attempt_count": len(continuation_attempts),
                            "attempts": continuation_attempts,
                        },
                        provider_history_tail=provider_history_tail,
                    ).model_dump(mode="json")
                },
            )
            return

        raise LLMRequestError("MiniMax Responses tool loop did not terminate.")

    def _stream_response(
        self,
        payload: dict[str, Any],
        *,
        model_step: int,
    ) -> Generator[LLMStreamEvent, None, dict[str, Any]]:
        for attempt in range(1, self._stream_max_attempts + 1):
            yield LLMStreamEvent(
                type="model_request",
                data={
                    "step": model_step,
                    "model": self._model,
                    "provider_attempt": attempt,
                    "provider_attempt_limit": self._stream_max_attempts,
                    "transport": "minimax_responses",
                },
            )
            started_blocks: set[tuple[str, int]] = set()
            final_response: dict[str, Any] | None = None
            try:
                with self._client.stream(
                    "POST",
                    "/v1/responses",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        event = self._sse_event(line)
                        if event is None:
                            continue
                        event_type = self._string(event.get("type"))
                        output_index = self._integer(event.get("output_index"))
                        index = output_index if output_index is not None else 0
                        if event_type == "response.output_text.delta":
                            delta = self._string(event.get("delta"))
                            if delta:
                                key = ("text", index)
                                if key not in started_blocks:
                                    started_blocks.add(key)
                                    yield LLMStreamEvent(
                                        type="text_start",
                                        data={
                                            "index": index,
                                            "model_step": model_step,
                                            "provider_attempt": attempt,
                                        },
                                    )
                                yield LLMStreamEvent(
                                    type="text_delta",
                                    data={
                                        "index": index,
                                        "text": delta,
                                        "model_step": model_step,
                                        "provider_attempt": attempt,
                                    },
                                )
                        elif event_type in {
                            "response.reasoning_text.delta",
                            "response.reasoning_summary_text.delta",
                        }:
                            delta = self._string(event.get("delta"))
                            if delta:
                                key = ("thinking", index)
                                if key not in started_blocks:
                                    started_blocks.add(key)
                                    yield LLMStreamEvent(
                                        type="thinking_start",
                                        data={
                                            "index": index,
                                            "model_step": model_step,
                                            "provider_attempt": attempt,
                                        },
                                    )
                                yield LLMStreamEvent(
                                    type="thinking_delta",
                                    data={
                                        "index": index,
                                        "text": delta,
                                        "model_step": model_step,
                                        "provider_attempt": attempt,
                                    },
                                )
                        elif event_type == "response.function_call_arguments.delta":
                            delta = self._string(event.get("delta"))
                            if delta:
                                yield LLMStreamEvent(
                                    type="tool_input_delta",
                                    data={
                                        "index": index,
                                        "partial_json": delta,
                                        "model_step": model_step,
                                        "provider_attempt": attempt,
                                    },
                                )
                        elif event_type in {
                            "response.completed",
                            "response.incomplete",
                            "response.failed",
                        }:
                            candidate = event.get("response")
                            if isinstance(candidate, dict):
                                final_response = candidate
                        elif event.get("object") == "response":
                            final_response = event
                if final_response is None:
                    raise LLMRequestError(
                        "MiniMax Responses stream ended without a terminal response."
                    )
                return final_response
            except (httpx.HTTPError, LLMRequestError) as exc:
                if attempt >= self._stream_max_attempts or not self._retryable(exc):
                    raise LLMRequestError(self._sanitize_error(str(exc))) from exc
                yield LLMStreamEvent(
                    type="provider_retry",
                    data={
                        "model_step": model_step,
                        "provider_attempt": attempt,
                        "next_provider_attempt": attempt + 1,
                        "provider_attempt_limit": self._stream_max_attempts,
                        "error": self._sanitize_error(str(exc)),
                        "transport": "minimax_responses",
                    },
                )
                delay = self._retry_backoff_seconds * (2 ** (attempt - 1))
                if delay:
                    time.sleep(delay)
        raise AssertionError("Responses retry loop must return or raise")

    @staticmethod
    def _messages_to_responses_input(
        messages: list[LLMMessage],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in messages:
            if isinstance(message.content, str):
                items.append(
                    {
                        "type": "message",
                        "role": message.role,
                        "content": message.content,
                    }
                )
                continue
            message_parts: list[dict[str, Any]] = []

            def flush_message_parts() -> None:
                if not message_parts:
                    return
                items.append(
                    {
                        "type": "message",
                        "role": message.role,
                        "content": list(message_parts),
                    }
                )
                message_parts.clear()

            for block in message.content:
                block_type = block.get("type")
                if block_type == "tool_result":
                    flush_message_parts()
                    call_id = block.get("tool_use_id")
                    if isinstance(call_id, str) and call_id:
                        items.append(
                            {
                                "type": "function_call_output",
                                "call_id": call_id,
                                "output": str(block.get("content", "")),
                            }
                        )
                elif block_type == "tool_use":
                    flush_message_parts()
                    call_id = block.get("id")
                    name = block.get("name")
                    if isinstance(call_id, str) and isinstance(name, str):
                        items.append(
                            {
                                "type": "function_call",
                                "call_id": call_id,
                                "name": name,
                                "arguments": json.dumps(
                                    block.get("input", {}),
                                    ensure_ascii=True,
                                ),
                            }
                        )
                elif block_type == "thinking":
                    flush_message_parts()
                    thinking = block.get("thinking")
                    if isinstance(thinking, str) and thinking.strip():
                        items.append(
                            {
                                "type": "reasoning",
                                "summary": [
                                    {
                                        "type": "summary_text",
                                        "text": thinking,
                                    }
                                ],
                            }
                        )
                elif block_type == "text":
                    text = block.get("text")
                    if isinstance(text, str):
                        message_parts.append(
                            {
                                "type": (
                                    "output_text"
                                    if message.role == "assistant"
                                    else "input_text"
                                ),
                                "text": text,
                            }
                        )
                elif block_type in {
                    "input_text",
                    "output_text",
                    "input_image",
                    "input_video",
                }:
                    message_parts.append(block)
            flush_message_parts()
        return items

    @staticmethod
    def _to_responses_tool(tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "name": tool.get("name", ""),
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object"}),
        }

    @staticmethod
    def _normalize_output(
        output: list[Any],
    ) -> tuple[list[dict[str, Any]], list[LLMToolUse]]:
        raw_content: list[dict[str, Any]] = []
        tool_uses: list[LLMToolUse] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")
            if item_type == "message":
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    if part.get("type") == "output_text":
                        text = part.get("text")
                        if isinstance(text, str) and text:
                            raw_content.append({"type": "text", "text": text})
            elif item_type == "reasoning":
                texts: list[str] = []
                for key in ("content", "summary"):
                    parts = item.get(key)
                    if not isinstance(parts, list):
                        continue
                    for part in parts:
                        if isinstance(part, dict) and isinstance(
                            part.get("text"),
                            str,
                        ):
                            texts.append(part["text"])
                if texts:
                    raw_content.append(
                        {"type": "thinking", "thinking": "\n".join(texts)}
                    )
            elif item_type == "function_call":
                call_id = item.get("call_id")
                name = item.get("name")
                if not isinstance(call_id, str) or not isinstance(name, str):
                    continue
                arguments = item.get("arguments", "{}")
                try:
                    parsed = json.loads(arguments) if isinstance(arguments, str) else {}
                except json.JSONDecodeError:
                    parsed = {}
                if not isinstance(parsed, dict):
                    parsed = {}
                tool_use = LLMToolUse(id=call_id, name=name, input=parsed)
                tool_uses.append(tool_use)
                raw_content.append(
                    {
                        "type": "tool_use",
                        "id": call_id,
                        "name": name,
                        "input": parsed,
                    }
                )
        return raw_content, tool_uses

    @staticmethod
    def _semantic_events(
        raw_content: list[dict[str, Any]],
        *,
        provider_message_id: str | None,
        stop_reason: str,
        model_step: int,
    ) -> Iterator[LLMStreamEvent]:
        text_event_type = {
            "tool_use": "assistant_note",
            "end_turn": "assistant_answer",
            "max_tokens": "assistant_continuation",
        }.get(stop_reason)
        for index, block in enumerate(raw_content):
            if block.get("type") == "thinking":
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
            elif block.get("type") == "text" and text_event_type is not None:
                text = block.get("text")
                if isinstance(text, str) and text.strip():
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
    def _extract_text(raw_content: list[dict[str, Any]]) -> str:
        return "\n".join(
            block["text"]
            for block in raw_content
            if block.get("type") == "text" and isinstance(block.get("text"), str)
        ).strip()

    @staticmethod
    def _stop_reason(
        response: dict[str, Any],
        tool_uses: list[LLMToolUse],
    ) -> str:
        if response.get("status") == "incomplete":
            return "max_tokens"
        return "tool_use" if tool_uses else "end_turn"

    @staticmethod
    def _incomplete_reason(response: dict[str, Any]) -> str | None:
        details = response.get("incomplete_details")
        if not isinstance(details, dict):
            return None
        reason = details.get("reason")
        return reason if isinstance(reason, str) else None

    @staticmethod
    def _continuation_input() -> dict[str, Any]:
        return {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": (
                        "Continue the same response exactly from where it stopped. "
                        "Do not repeat completed content. Continue using tools if "
                        "needed; otherwise finish the answer."
                    ),
                }
            ],
        }

    @staticmethod
    def _merge_usage(
        totals: dict[str, Any],
        usage: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(totals)
        for key, value in usage.items():
            if isinstance(value, int) and isinstance(merged.get(key), int):
                merged[key] += value
            elif key not in merged:
                merged[key] = value
        return merged

    @staticmethod
    def _collect_final_result(events: Iterator[LLMStreamEvent]) -> LLMTextResult:
        for event in events:
            if event.type == "final_result":
                return LLMTextResult.model_validate(event.data["result"])
        raise LLMRequestError("Responses stream ended without final_result.")

    @staticmethod
    def _unexpected_tool_runner(tool_use: LLMToolUse) -> LLMExecutedToolCall:
        raise LLMRequestError(f"Unexpected tool call: {tool_use.name}")

    @staticmethod
    def _sse_event(line: str) -> dict[str, Any] | None:
        stripped = line.strip()
        if not stripped.startswith("data:"):
            return None
        payload = stripped[5:].strip()
        if not payload or payload == "[DONE]":
            return None
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise LLMRequestError("MiniMax Responses emitted invalid SSE JSON.") from exc
        return event if isinstance(event, dict) else None

    @staticmethod
    def _retryable(exc: BaseException) -> bool:
        if isinstance(exc, (httpx.ConnectError, httpx.TimeoutException)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code
            return status in {408, 409, 429} or status >= 500
        return False

    def _sanitize_error(self, value: str) -> str:
        return value.replace(self._api_key, "***")

    @staticmethod
    def _string(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _integer(value: Any) -> int | None:
        return value if isinstance(value, int) else None

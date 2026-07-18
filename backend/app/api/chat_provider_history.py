"""Provider-history transformations shared by native and external chat paths."""

import json
from typing import Any

from app.llm.provider import LLMExecutedToolCall, LLMMessage, LLMTextResult
from app.storage.models import ChatSession, Message


ProviderHistory = list[dict[str, Any]]


def provider_messages_for_turn(
    *,
    chat_session: ChatSession,
    history: list[Message],
    current_user_message: Message,
) -> tuple[str, list[LLMMessage]]:
    provider_history = valid_provider_history(chat_session.provider_history_json)
    if provider_history:
        return (
            "session.provider_history_json",
            [
                LLMMessage(role=item["role"], content=item["content"])
                for item in [
                    *provider_history,
                    provider_user_text_message(current_user_message.content),
                ]
            ],
        )

    return (
        "messages.text_reconstructed",
        [
            LLMMessage(role=item["role"], content=item["content"])
            for item in text_provider_history(history)
        ],
    )


def updated_provider_history(
    request_messages: list[LLMMessage],
    result: LLMTextResult,
) -> ProviderHistory:
    history = [
        llm_message_to_provider_history_item(message) for message in request_messages
    ]
    history.extend(provider_history_from_result(result))
    return history


def provider_history_from_result(result: LLMTextResult) -> ProviderHistory:
    valid_recovery_tail = valid_provider_history(result.provider_history_tail)
    if valid_recovery_tail:
        return valid_recovery_tail
    if result.raw_provider_messages:
        return provider_history_from_raw_messages(
            result.raw_provider_messages,
            tool_calls=result.tool_calls,
        )

    raw_content = valid_content_blocks(result.raw_content)
    if not raw_content and result.text:
        raw_content = [{"type": "text", "text": result.text}]
    if not raw_content:
        return []
    return [{"role": "assistant", "content": raw_content}]


def provider_history_from_raw_messages(
    raw_provider_messages: list[dict[str, Any]],
    *,
    tool_calls: list[LLMExecutedToolCall],
) -> ProviderHistory:
    tool_calls_by_id = {
        tool_call.provider_tool_use_id: tool_call for tool_call in tool_calls
    }
    history: ProviderHistory = []
    for raw_message in raw_provider_messages:
        content = valid_content_blocks(raw_message.get("content"))
        if not content:
            continue
        history.append({"role": "assistant", "content": content})
        tool_results = [
            tool_result_block(tool_calls_by_id[tool_use_id])
            for tool_use_id in tool_use_ids(content)
            if tool_use_id in tool_calls_by_id
        ]
        if tool_results:
            history.append({"role": "user", "content": tool_results})
    return history


def tool_result_block(tool_call: LLMExecutedToolCall) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_call.provider_tool_use_id,
        "content": json.dumps(tool_call.result, ensure_ascii=True),
        "is_error": tool_call.status != "completed",
    }


def tool_use_ids(content_blocks: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for block in content_blocks:
        if block.get("type") != "tool_use":
            continue
        tool_use_id = block.get("id")
        if isinstance(tool_use_id, str) and tool_use_id:
            ids.append(tool_use_id)
    return ids


def valid_provider_history(value: Any) -> ProviderHistory:
    if not isinstance(value, list):
        return []
    history: ProviderHistory = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = valid_content_blocks(item.get("content"))
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def text_provider_history(messages: list[Message]) -> ProviderHistory:
    return [
        provider_user_text_message(message.content)
        if message.role == "user"
        else provider_assistant_text_message(message.content)
        for message in messages
        if message.role in {"user", "assistant"}
    ]


def provider_user_text_message(content: str) -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", "text": content}]}


def provider_assistant_text_message(content: str) -> dict[str, Any]:
    return {"role": "assistant", "content": [{"type": "text", "text": content}]}


def llm_message_to_provider_history_item(message: LLMMessage) -> dict[str, Any]:
    content = message.content
    if isinstance(content, str):
        return {
            "role": message.role,
            "content": [{"type": "text", "text": content}],
        }
    return {
        "role": message.role,
        "content": valid_content_blocks(content),
    }


def valid_content_blocks(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    blocks: list[dict[str, Any]] = []
    for block in value:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if isinstance(block_type, str) and block_type:
            blocks.append(block)
    return blocks

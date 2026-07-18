import json

from app.api.chat import (
    ChatMessageResponse as FacadeChatMessageResponse,
    ChatSessionResponse as FacadeChatSessionResponse,
    ChatTurnResponse as FacadeChatTurnResponse,
    EventResponse as FacadeEventResponse,
    TraceResponse as FacadeTraceResponse,
)
from app.api.chat_accounting import (
    context_accounting_summary,
    post_turn_model_history_tokens,
    provider_message_stats,
)
from app.api.chat_provider_history import (
    provider_history_from_result,
    provider_messages_for_turn,
    updated_provider_history,
    valid_provider_history,
)
from app.api.chat_serialization import (
    ChatMessageResponse,
    ChatSessionResponse,
    ChatTurnResponse,
    EventResponse,
    TraceResponse,
    incomplete_result_details,
    memory_context_event_payload,
    ndjson,
    response_event_messages,
    runtime_context_event_payload,
)
from app.llm.provider import LLMExecutedToolCall, LLMMessage, LLMTextResult
from app.storage.models import ChatSession, Message


def _message(*, role: str, content: str, message_id: str) -> Message:
    return Message(
        id=message_id,
        session_id="ses_support",
        turn_id="turn_support",
        role=role,
        content=content,
    )


def test_response_models_remain_reexported_by_chat_facade() -> None:
    assert FacadeChatSessionResponse is ChatSessionResponse
    assert FacadeChatMessageResponse is ChatMessageResponse
    assert FacadeChatTurnResponse is ChatTurnResponse
    assert FacadeTraceResponse is TraceResponse
    assert FacadeEventResponse is EventResponse


def test_provider_messages_prefer_canonical_history_and_append_current_user() -> None:
    canonical = [
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "private continuity"},
                {"type": "text", "text": "public continuity"},
            ],
        }
    ]
    chat_session = ChatSession(
        id="ses_support",
        provider_history_json=canonical,
    )
    current = _message(role="user", content="messaggio corrente", message_id="msg_2")

    source, messages = provider_messages_for_turn(
        chat_session=chat_session,
        history=[_message(role="assistant", content="fallback", message_id="msg_1")],
        current_user_message=current,
    )

    assert source == "session.provider_history_json"
    assert [message.role for message in messages] == ["assistant", "user"]
    assert messages[0].content == canonical[0]["content"]
    assert messages[1].content == [{"type": "text", "text": "messaggio corrente"}]


def test_provider_messages_reconstruct_text_when_canonical_history_is_invalid() -> None:
    chat_session = ChatSession(
        id="ses_support",
        provider_history_json=[{"role": "system", "content": "invalid"}],
    )
    history = [
        _message(role="user", content="prima", message_id="msg_1"),
        _message(role="assistant", content="seconda", message_id="msg_2"),
        _message(role="tool", content="ignored", message_id="msg_3"),
    ]

    source, messages = provider_messages_for_turn(
        chat_session=chat_session,
        history=history,
        current_user_message=history[0],
    )

    assert source == "messages.text_reconstructed"
    assert [message.model_dump(mode="json") for message in messages] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "prima"}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "seconda"}],
        },
    ]


def test_provider_history_rebuilds_tool_exchange_in_provider_order() -> None:
    tool_call = LLMExecutedToolCall(
        provider_tool_use_id="toolu_help",
        tool_name="mind_shell",
        arguments={"command": "help"},
        result={"ok": True, "result": {"operation": "mind.help"}},
        status="completed",
    )
    result = LLMTextResult(
        model="MiniMax-M3",
        text="Fatto.",
        raw_provider_messages=[
            {
                "id": "provider_1",
                "content": [
                    {"type": "text", "text": "Controllo."},
                    {
                        "type": "tool_use",
                        "id": "toolu_help",
                        "name": "mind_shell",
                        "input": {"command": "help"},
                    },
                ],
            },
            {
                "id": "provider_2",
                "content": [{"type": "text", "text": "Fatto."}],
            },
        ],
        tool_calls=[tool_call],
    )

    history = provider_history_from_result(result)

    assert [item["role"] for item in history] == ["assistant", "user", "assistant"]
    tool_result = history[1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_help"
    assert json.loads(tool_result["content"])["ok"] is True
    assert tool_result["is_error"] is False


def test_recovery_tail_is_authoritative_and_updates_request_history() -> None:
    recovery_tail = [
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "bozza rifiutata"}],
        },
        {
            "role": "user",
            "content": [{"type": "text", "text": "correggi"}],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "risposta accettata"}],
        },
    ]
    result = LLMTextResult(
        model="MiniMax-M3",
        text="risposta accettata",
        raw_content=[{"type": "text", "text": "fallback non usato"}],
        provider_history_tail=recovery_tail,
    )

    assert provider_history_from_result(result) == recovery_tail
    assert updated_provider_history(
        [LLMMessage(role="user", content="domanda")],
        result,
    ) == [
        {"role": "user", "content": [{"type": "text", "text": "domanda"}]},
        *recovery_tail,
    ]
    assert valid_provider_history([{"role": "system", "content": []}]) == []


def test_serialization_and_accounting_helpers_keep_compact_contracts() -> None:
    result = LLMTextResult(
        model="MiniMax-M3",
        text="risposta",
        provider_message_id="provider_final",
        stop_reason="end_turn",
    )
    assert response_event_messages(result) == [
        {
            "id": "provider_final",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "risposta"}],
        }
    ]
    assert incomplete_result_details(result)["raw_content_types"] == []
    assert json.loads(ndjson("turn_complete", {"ok": True})) == {
        "type": "turn_complete",
        "data": {"ok": True},
    }

    memory_payload = memory_context_event_payload(
        {"operation": "memory.context", "selected": [{"id": "mem_1"}]}
    )
    assert memory_payload["selected"] == [{"id": "mem_1"}]
    assert memory_payload["near_miss"] == []
    assert runtime_context_event_payload({"blocks": "invalid"})["block_count"] == 0

    stats = provider_message_stats(
        [
            LLMMessage(role="user", content="testo"),
            LLMMessage(
                role="assistant",
                content=[
                    {"type": "thinking", "thinking": "x"},
                    {"type": "text", "text": "y"},
                ],
            ),
        ]
    )
    assert stats["message_count"] == 2
    assert stats["content_block_count"] == 3
    assert stats["approx_tokens"] > 0

    summary = context_accounting_summary(
        {
            "schema_version": "context-accounting-v2",
            "transport": "native",
            "total": {"estimated_input_tokens": 12},
            "policy": {"limit": 500_000},
            "compaction_plan": {"mode": "active"},
            "channels": {"not": "part of summary"},
        }
    )
    assert "channels" not in summary
    assert summary["transport"] == "native"
    assert post_turn_model_history_tokens(
        {
            "canonical_estimated_tokens": 30,
            "turns": [
                {"estimated_tokens": 10},
                {"estimated_tokens": 20},
            ],
        },
        {"status": "derived_history_active", "covered_turn_count": 1},
    ) == 20

import json

from app.evals.history_compaction_calibration import (
    _continuation_instruction,
    _file_sha256,
    _llm_messages,
    _result,
    _summary_input,
    _summary_system,
)
from app.llm.provider import LLMTextResult


def test_summary_input_preserves_source_navigation_ids() -> None:
    payload = json.loads(
        _summary_input(
            "ses_source",
            [
                {
                    "turn_id": "turn_source",
                    "message_ids": ["msg_user", "msg_assistant"],
                    "tool_call_ids": ["tool_source"],
                    "request_trace_id": "trace_request",
                    "response_trace_id": "trace_response",
                    "provider_messages": [
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": "question"}],
                        }
                    ],
                }
            ],
        )
    )

    assert payload["session_id"] == "ses_source"
    source = payload["completed_turn_sources"][0]
    assert source["turn_id"] == "turn_source"
    assert source["message_ids"] == ["msg_user", "msg_assistant"]
    assert source["tool_call_ids"] == ["tool_source"]
    assert source["request_trace_id"] == "trace_request"


def test_calibration_helpers_keep_provider_content_and_result_evidence(
    tmp_path,
) -> None:
    messages = _llm_messages(
        [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "answer"}],
            }
        ]
    )
    result = LLMTextResult(
        model="MiniMax-M3",
        text="done",
        stop_reason="end_turn",
        usage={"input_tokens": 10, "output_tokens": 2},
        provider_message_id="provider_message",
    )
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("source", encoding="utf-8")

    assert messages[0].content == [{"type": "text", "text": "answer"}]
    assert _result(result, 123) == {
        "text": "done",
        "model": "MiniMax-M3",
        "stop_reason": "end_turn",
        "latency_ms": 123,
        "usage": {"input_tokens": 10, "output_tokens": 2},
        "provider_message_id": "provider_message",
    }
    assert _file_sha256(artifact) == (
        "41cf6794ba4200b839c53531555f0f3998df4cbb01a4d5cb0b94e3ca5e23947d"
    )
    assert "turn_id" in _summary_system()
    assert "Non hai tool" in _continuation_instruction()

import json

import httpx

from app.config import Settings
from app.llm.minimax_responses_client import MiniMaxResponsesProvider
from app.llm.provider import LLMExecutedToolCall, LLMMessage


def _sse_response(payload: dict) -> httpx.Response:
    body = "data: " + json.dumps(payload) + "\n\ndata: [DONE]\n\n"
    return httpx.Response(
        200,
        headers={"Content-Type": "text/event-stream"},
        content=body.encode(),
    )


def test_responses_provider_runs_tools_and_keeps_media_transient() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        if len(requests) == 1:
            response = {
                "id": "resp_tool",
                "object": "response",
                "model": "MiniMax-M3",
                "status": "completed",
                "output": [
                    {
                        "id": "reasoning_1",
                        "type": "reasoning",
                        "status": "completed",
                        "summary": [
                            {"type": "summary_text", "text": "I should inspect."}
                        ],
                    },
                    {
                        "id": "message_1",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": "Controllo un dettaglio.",
                                "annotations": [],
                            }
                        ],
                    },
                    {
                        "id": "function_1",
                        "type": "function_call",
                        "status": "completed",
                        "call_id": "call_1",
                        "name": "mind_shell",
                        "arguments": '{"command":"perception status"}',
                    },
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
            return _sse_response(
                {"type": "response.completed", "response": response}
            )
        response = {
            "id": "resp_answer",
            "object": "response",
            "model": "MiniMax-M3",
            "status": "completed",
            "output": [
                {
                    "id": "message_2",
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Ti vedo e ti ho sentito.",
                            "annotations": [],
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 20, "output_tokens": 7},
        }
        body = "\n\n".join(
            [
                "data: "
                + json.dumps(
                    {
                        "type": "response.output_text.delta",
                        "output_index": 0,
                        "delta": "Ti vedo ",
                    }
                ),
                "data: "
                + json.dumps(
                    {"type": "response.completed", "response": response}
                ),
                "data: [DONE]",
            ]
        )
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            content=(body + "\n\n").encode(),
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.minimax.io",
    )
    provider = MiniMaxResponsesProvider(
        Settings(minimax_api_key="test-key"),
        client=client,
    )
    media_url = "data:video/mp4;base64,dmlkZW8="

    def run_tool(_tool_use):
        return LLMExecutedToolCall(
            provider_tool_use_id="call_1",
            tool_name="mind_shell",
            arguments={"command": "perception status"},
            result={"ok": True, "status": "available"},
            status="completed",
            provider_content_parts=[
                {
                    "type": "input_video",
                    "video_url": {"url": media_url, "fps": 1},
                }
            ],
        )

    events = list(
        provider.stream_chat_with_tools(
            messages=[
                LLMMessage(
                    role="user",
                    content=[
                        {"type": "input_text", "text": "Cosa vedi?"},
                        {
                            "type": "input_video",
                            "video_url": {"url": media_url, "fps": 2},
                        },
                    ],
                )
            ],
            system="You are Scarlet.",
            tools=[
                {
                    "name": "mind_shell",
                    "description": "Cognitive shell",
                    "input_schema": {"type": "object"},
                }
            ],
            tool_runner=run_tool,
        )
    )

    result = next(
        event.data["result"] for event in events if event.type == "final_result"
    )
    assert result["text"] == "Ti vedo e ti ho sentito."
    assert result["stop_reason"] == "end_turn"
    assert result["usage"] == {
        "input_tokens": 30,
        "output_tokens": 12,
    }
    assert any(event.type == "assistant_note" for event in events)
    assert any(event.type == "assistant_answer" for event in events)
    assert any(event.type == "text_delta" for event in events)
    assert requests[0]["input"][0]["content"][1]["video_url"]["url"] == media_url
    function_output = next(
        item
        for item in requests[1]["input"]
        if item.get("type") == "function_call_output"
    )
    assert function_output["output"][1]["video_url"]["url"] == media_url
    assert media_url not in json.dumps(result["provider_history_tail"])

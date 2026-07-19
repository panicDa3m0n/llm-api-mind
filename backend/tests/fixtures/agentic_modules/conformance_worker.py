"""Small JSONL process used to verify the real Module Host transport."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone


BEHAVIOR = sys.argv[1] if len(sys.argv) > 1 else "normal"


def respond(request: dict) -> bool:
    operation = request.get("operation")
    request_id = request.get("request_id")
    if operation == "lifecycle.stop":
        result = {"status": "stopped"}
        keep_running = False
    elif operation == "lifecycle.start":
        result = {"status": "ready"}
        keep_running = True
    elif operation == "health":
        result = {"status": "healthy", "details": {"worker": "fixture"}}
        keep_running = True
    elif operation == "context.contribute":
        if BEHAVIOR == "timeout":
            time.sleep(1.0)
        elif BEHAVIOR == "invalid":
            print("not-json", flush=True)
            return True
        elif BEHAVIOR == "crash":
            os._exit(7)
        payload = request.get("payload") or {}
        result = {
            "contributions": [
                {
                    "contribution_id": "fixture-context",
                    "block_type": "fixture.observation",
                    "content": {
                        "observed": True,
                        "input_count": len(payload.get("inputs") or []),
                    },
                    "estimated_tokens": 12,
                    "priority": 80,
                }
            ]
        }
        keep_running = True
    elif operation == "prompt.contribute":
        result = {
            "contributions": [
                {
                    "contribution_id": "fixture-prompt",
                    "slot": "turn_context",
                    "text": "Fixture prompt contribution.",
                    "priority": 60,
                }
            ]
        }
        keep_running = True
    elif operation == "command.invoke":
        payload = request.get("payload") or {}
        result = {
            "status": "success",
            "output": {"echo": payload.get("arguments", {})},
        }
        keep_running = True
    elif operation == "event.handle":
        result = {
            "acknowledged": True,
            "publications": [
                {
                    "event_id": "fixture-publication",
                    "event_type": "fixture.observed",
                    "occurred_at": datetime.now(timezone.utc).isoformat(),
                    "payload": {"handled": True},
                }
            ],
        }
        keep_running = True
    else:
        print(
            json.dumps(
                {
                    "request_id": request_id,
                    "ok": False,
                    "error": {"code": "operation.unknown"},
                }
            ),
            flush=True,
        )
        return True
    print(
        json.dumps({"request_id": request_id, "ok": True, "result": result}),
        flush=True,
    )
    return keep_running


for line in sys.stdin:
    try:
        message = json.loads(line)
    except json.JSONDecodeError:
        continue
    if not respond(message):
        break

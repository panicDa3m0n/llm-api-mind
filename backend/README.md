# Backend

FastAPI backend for the LLM API Mind experimental runtime.

Current scope:

- typed environment configuration;
- `/health` endpoint;
- MiniMax M2.7 provider smoke test;
- configurable Scarlet agent system prompt;
- persistent chat sessions and turns;
- SQLite schema for sessions, messages, turns, and traces;
- pytest coverage for health, LLM smoke wiring, and storage.

## Setup

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
cp .env.example .env
```

Add your MiniMax key to `backend/.env`:

```txt
MINIMAX_API_KEY=...
MINIMAX_MAX_TOKENS=4096
```

The default chat identity is loaded from:

```txt
backend/app/prompts/scarlet_system.md
```

To test another identity without editing the bundled prompt, set one of:

```txt
AGENT_SYSTEM_PROMPT=...
AGENT_SYSTEM_PROMPT_PATH=path/to/system_prompt.md
```

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

```txt
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## MiniMax Smoke Test

After adding `MINIMAX_API_KEY` to `backend/.env`, run:

```bash
python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import create_app

client = TestClient(create_app())
response = client.post("/api/debug/llm-smoke-test", json={
    "prompt": "Reply with exactly: pong"
})
print(response.status_code)
print(response.json())
PY
```

## Persistent Chat Smoke Test

```bash
python3 - <<'PY'
from fastapi.testclient import TestClient
from app.main import create_app

client = TestClient(create_app())
session = client.post("/api/chat/sessions", json={"title": "Local smoke"}).json()
turn = client.post(f"/api/chat/sessions/{session['id']}/turn", json={
    "message": "Reply with exactly: pong"
}).json()
print(turn["assistant_message"]["content"])
print(turn["trace_ids"])
PY
```

## Test

```bash
pytest
```

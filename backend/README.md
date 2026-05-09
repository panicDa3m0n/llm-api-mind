# Backend

FastAPI backend for the LLM API Mind experimental runtime.

Current scope:

- typed environment configuration;
- `/health` endpoint;
- MiniMax M2.7 provider smoke test;
- configurable Scarlet agent system prompt;
- persistent chat sessions and turns;
- SQLite schema for sessions, messages, turns, and traces;
- scripted and interactive evaluation runner for traceable experiments;
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

## Evaluation Runner

The eval runner talks to a running backend over HTTP and writes evidence files under
`backend/app/evals/runs/` by default. That directory is ignored by Git.

Scripted regression scenario:

```bash
python -m app.evals.runner scripted app/evals/scenarios/baseline_tool_schema.json
```

Adaptive human-in-the-loop session:

```bash
python -m app.evals.runner interactive --title "manual continuity probe"
```

Interactive mode is the primary path for behavioral evaluation: choose each next
prompt based on Scarlet's previous answer, then add a short human note after each
turn. Scripted mode is for repeatable checks, not for replacing live evaluation.

## Test

```bash
pytest
```

# Backend

FastAPI backend for the LLM API Mind experimental runtime.

App baseline: V1.3.1.

Current scope:

- typed environment configuration;
- `/health` endpoint;
- switchable MiniMax/Qwen LLM provider smoke test;
- configurable Scarlet agent system prompt;
- persistent chat sessions and turns;
- dashboard-ready recent session listing, session message reload, runtime
  settings, memory panel data, and profile readout;
- SQLite schema for sessions, messages, turns, traces, ordered runtime events,
  maintenance jobs, tool calls, memories, memory facts, memory proposals,
  memory surfaces, memory graph nodes/edges, session summaries, and app
  settings;
- optional retrieval shadow adapter over `memory_surfaces` for local deterministic
  plumbing tests or Milvus Lite trace-only comparison;
- model-controlled, unbounded API Mind cognitive loop through the single `mind_api` interface;
- schema-versioned API Mind discovery plus one LLM-backed internal metacognition route;
- Memory v0 write/search/read/conflicts/deprecate/supersede/facts/backfill through `mind_api`;
- maintenance API access for pending memory proposal review and archival;
- episodic session recall through `GET /mind/sessions`, `GET /mind/sessions/{session_id}`, and `POST /mind/sessions/{session_id}/summarize`;
- automatic Memory Context Pipeline v0 traces before model requests;
- runtime event control plane for UI activity blocks, next-turn context, and
  background maintenance triggers;
- per-session idle maintenance that schedules summary refresh, missed-memory
  review, pending memory proposal creation, cautious resolution, and auditable
  proposal ledger updates after completed turns;
- scripted and interactive evaluation runner for traceable experiments;
- pytest coverage for health, LLM smoke wiring, storage, chat, Mind API, and memory.

## Setup

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
cp .env.example .env
```

Add your MiniMax key to `backend/.env` for the default provider:

```txt
LLM_PROVIDER=minimax
MINIMAX_API_KEY=...
MINIMAX_MAX_TOKENS=131072
```

Idle maintenance defaults to a 15-minute per-session timer:

```txt
MAINTENANCE_ENABLED=true
MAINTENANCE_IDLE_SECONDS=900
MAINTENANCE_WORKER_INTERVAL_SECONDS=5
MAINTENANCE_JOB_BATCH_SIZE=5
```

Dashboard runtime defaults:

```txt
RUNTIME_TIMEZONE=Europe/Rome
RUNTIME_LANGUAGE=it
RUNTIME_LANGUAGE_LABEL=Italiano
RUNTIME_COUNTRY_CODE=IT
RUNTIME_COUNTRY_LABEL=Italia
USER_PROFILE_ID=local-user
USER_DISPLAY_NAME=Utente locale
USER_PRIVACY_SCOPE=local_single_user
```

Persisted `/api/dashboard/settings` values override these defaults for future
runtime-context turns.

If the same session receives another user turn before the timer expires, the
older pending job is superseded. Jobs for other sessions continue independently.

To compare the same Scarlet/API Mind system against Qwen through Alibaba Model
Studio's Anthropic-compatible endpoint, switch only the provider settings:

```txt
LLM_PROVIDER=qwen
QWEN_API_KEY=...
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/apps/anthropic
QWEN_MODEL=qwen3.7-max
QWEN_MAX_TOKENS=4096
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

## LLM Smoke Test

After configuring the selected provider key in `backend/.env`, run:

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
python -m app.evals.runner scripted app/evals/scenarios/memory_v0_preference.json
python -m app.evals.runner scripted app/evals/scenarios/visible_metacognition_probe.json
python -m app.evals.runner scripted app/evals/scenarios/cognitive_api_metacognition_probe.json
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

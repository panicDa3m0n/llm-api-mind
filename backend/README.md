# Backend

FastAPI backend for the LLM API Mind experimental runtime.

App baseline: V1.50.1 candidate (V1.50.0 deployed but not release-accepted).

Current scope:

- typed environment configuration;
- explicit database roles and read-only preflight for production, laboratory,
  test, and preliminary state;
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
- optional retrieval shadow adapter over `memory_surfaces` for local
  deterministic plumbing tests, Milvus Lite trace-only comparison, or
  OpenRouter cloud embedding/rerank shadow evaluation;
- active memory-level rerank arbitration over a deduplicated sparse/dense/KG/
  lexical recall pool; deterministic signals find candidates but never accept
  or order final relevant memories;
- metacognitive context shadow traces for evaluator-visible candidate lessons,
  with controlled injection mode for A/B tests;
- backend-owned memory surface taxonomy for derived cognitive retrieval
  facets; Scarlet writes canonical memory fields, not surface internals;
- model-controlled, unbounded API Mind cognitive loop through the single
  `mind_shell(command, intent)` interface;
- executable command-registry/help conformance, truthful collection
  pagination, explicit targeted misses, and lifecycle-tested session, focus,
  volition, affect, mode, and metacognition families;
- schema-versioned API Mind discovery plus one LLM-backed internal metacognition
  route with previous-turn thinking retrospection;
- semantic memory write/search/open/graph/facts/conflicts/deprecate/supersede
  through `mind_shell`; facts backfill remains internal maintenance;
- maintenance API access for overview, job inspection/manual lab run, pending
  memory proposal review, and archival;
- episodic session recall through `GET /mind/sessions`, `GET /mind/sessions/{session_id}`, and `POST /mind/sessions/{session_id}/summarize`;
- automatic rich retrieval/runtime traces plus the compact
  `scarlet-model-context-v2` document shared by native MiniMax and GPT Actions;
- exact character/byte context accounting, provider token observations, and
  shadow-only history compaction planning;
- agent-mode registry, per-block automatic-routing receipts, persistent
  resumable posture, and `mode` shell family;
- runtime event control plane for UI activity blocks, next-turn context, and
  background maintenance triggers;
- per-session idle maintenance that schedules summary refresh, missed-memory
  review, pending memory proposal creation, cautious resolution, and auditable
  proposal ledger updates after completed turns;
- scripted and interactive evaluation runner for traceable experiments;
- pytest contracts for health, provider wiring, storage, chat, shell/API parity,
  context V2/accounting, GPT bridge, agent modes, behavioral contracts,
  maintenance, memory, focus, volition, and affect.

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

Database ownership defaults to the local laboratory role:

```txt
ENVIRONMENT=local
DATABASE_ROLE=auto
CODEX_TEST=false
DATABASE_URL=sqlite:///./data/app.db
```

Use `CODEX_TEST=true` only with a distinct disposable target/seed. The full
production/laboratory/test/preliminary boundary, including the VPS procedure,
is in `../docs/database-topology.md`. Before a deploy or a persistence-heavy
evaluation, run the read-only check:

```bash
python -m app.ops.database_preflight --require-existing
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

Final-answer obligations default to active enforcement:

```txt
ANSWER_OBLIGATIONS_MODE=active
ANSWER_VALIDATION_MAX_TOKENS=4096
```

The native runtime requires a private final boundary and retries one rejected
draft. Semantic validation is invoked only when a current hard obligation
requires natural-language judgment. GPT bridge finalize returns a recoverable
409 for the first hard rejection, fails the turn on the second, and never
persists a rejected draft.

Metacognitive context defaults to shadow mode:

```txt
METACOGNITIVE_CONTEXT_MODE=shadow
METACOGNITIVE_CONTEXT_MAX_LESSONS=3
```

`shadow` records and streams candidate lessons without sending them to the
model. Use `inject` only for controlled A/B tests where the same block should
enter `runtime_context.blocks`.

Cloud retrieval shadow can be enabled without changing Scarlet's active memory
ranking:

```txt
OPENROUTER_API_KEY=...
RETRIEVAL_SHADOW_ENABLED=true
RETRIEVAL_SHADOW_BACKEND=openrouter
RETRIEVAL_SHADOW_EMBEDDING_MODEL=nvidia/llama-nemotron-embed-vl-1b-v2:free
RETRIEVAL_SHADOW_RERANK_ENABLED=false
RETRIEVAL_SHADOW_RERANK_MODEL=nvidia/llama-nemotron-rerank-vl-1b-v2:free
```

The OpenRouter path writes diagnostic `retrieval_shadow` payloads. Surface
embeddings are cached in SQLite by content hash; query embeddings are generated
per search. Dense results provide one recall route and do not decide final
relevance.

To make one memory-level reranker the sole final relevance authority, enable
active mode explicitly:

```txt
RETRIEVAL_HYBRID_MODE=active
RETRIEVAL_HYBRID_MIN_DENSE_SCORE=0.38
RETRIEVAL_HYBRID_MIN_RERANK_SCORE=0.004
RETRIEVAL_HYBRID_RELATIVE_RERANK_FLOOR=0.01
```

The effective floor is `max(absolute floor, best query score * relative
floor)`. Both inputs are final-reranker outputs; sparse, dense, graph, and
lexical scores only build the candidate pool.

Use `RETRIEVAL_HYBRID_MODE=shadow` to record final-rerank decisions without
changing selected memories. The setting name is retained for compatibility;
V1.31.0 does not perform weighted hybrid score fusion.

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
uvicorn app.asgi:app --reload
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

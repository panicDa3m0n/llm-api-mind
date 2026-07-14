# LLM API Mind

Experimental laboratory for building and evaluating the external cognitive
architecture of Scarlet, a digital individual in development.

The project starts with a simple principle:

```txt
Build the microscope before the mind.
```

The long-term direction is a complex, inspectable cognitive system that can
support memory, perception, self-monitoring, relationship, affect, attention,
volition, learning, action, and eventually embodiment. Human-like cognitive
functions are research targets, not claims that the current implementation has
already reproduced human cognition or established consciousness.

## Current Status

Current app baseline: **V1.30.0**.

The project has a working local baseline runtime:

- FastAPI backend;
- MiniMax M3 baseline provider, with MiniMax M2.7 retained as the direct A/B
  comparison baseline and optional Qwen provider comparison;
- configurable Scarlet system prompt for the agent identity;
- SQLite persistence for sessions, messages, turns, traces, and ordered runtime
  events;
- traceable single-tool `mind_shell(command, intent)` cognitive loop, backed by
  internal `/mind/*` handlers;
- model-controlled, unbounded API Mind cognitive loop during chat turns;
- cognitive API support for schema discipline and a single LLM-backed internal
  metacognition route;
- Memory v0 write/search/read/conflicts/deprecate/supersede with sourceable records and dedicated traces;
- atomic `memory_facts` linked to memories, with canonical entity/predicate/value, lifecycle status, provenance, and backfill;
- derived memory surfaces and graph-ready nodes/edges for future dense
  retrieval, optional Milvus/local shadow indexing, and knowledge-graph expansion while
  keeping SQLite/API Mind as the source of truth;
- backend-owned memory surface taxonomy that splits each memory into
  embeddable cognitive facets such as preference, future-use, temporal, fact,
  and conflict/update surfaces;
- episodic recall through session summaries plus full transcript retrieval by session id;
- rich automatic retrieval/runtime traces plus a compact
  `scarlet-model-context-v2` packet shared by native MiniMax and GPT Actions;
- per-channel context accounting, provider first-step observations, and a
  non-destructive 400k-trigger compaction plan targeting a future 100k
  chronology plus measured recent turns;
- agent-only `idle`/`interactive`/`scouting` modes with multi-tag automatic
  context eligibility and shell inspection/selection;
- runtime event control plane feeding the cockpit timeline and compact
  next-turn operational context;
- backend-owned per-session idle maintenance for session summary refresh,
  missed-memory review, memory proposal generation, and cautious proposal
  resolution;
- visible metacognition prompt probe for concise public self-monitoring notes;
- streaming React cockpit with inline ordered agent-turn timeline and recent
  session sidebar for reopening persisted conversations by title;
- scripted and interactive evaluation runner;
- focus, volition, and affect as implemented standalone organ surfaces, with
  different runtime activation and validation levels;
- accepted baseline, shell, streaming, context V2, memory, organ, and
  preliminary whole-system regression experiments;
- a declared database boundary between production, mutable laboratory state,
  disposable tests, and frozen preliminary regression runs.
- active memory robustness roadmap for response-control, lifecycle, atomic facts, retrieval quality, compaction, CLI/API inspection, and evals.

## Key Documents

- `AGENTS.md`: operating protocol for Codex/Scarlet as IDE agent.
- `docs/project-documentation.md`: main documentation index and branch map.
- `docs/development-process.md`: V1.0.1+ scoped implementation and versioning
  protocol.
- `docs/branches/README.md`: canonical agentic branch index.
- `docs/project-state.md`: current integrated system map and convergent
  roadmap.
- `docs/project-blueprint.md`: main project blueprint.
- `docs/activity-log.md`: continuity log.
- `docs/decisions.md`: architectural decisions.
- `docs/bug-ledger.md`: known bugs, fixes, and environment notes.
- `docs/experiments.md`: hypotheses, baselines, metrics, and results.
- `docs/api-contract.md`: planned and implemented API contracts.
- `docs/database-topology.md`: database ownership, test isolation, and VPS
  deployment safety procedure.
- `docs/memory-roadmap.md`: detailed roadmap for a robust API/CLI-first memory system.
- `docs/cognitive-api-roadmap.md`: roadmap for schema discipline and the
  single-route internal metacognition experiment.
- `docs/runtime-context-packs.md`: context budget, compaction, agent-mode, and
  future embodiment-routing contract.
- `docs/behavioral-validation-framework.md`: evidence-grounded direct Scarlet
  evaluation contract.
- `docs/release-process.md`: commit, changelog, and release discipline.
- `CHANGELOG.md`: concrete history of meaningful changes.

## Immediate Roadmap

```txt
1. Accumulate exact post-V1.30 accounting from long, varied real sessions.
2. Validate a derived 100k chronology plus desired eight-turn tail and define
   degradation when the tail does not fit under 500k.
3. Populate natural behavioral scenarios for context, communication, focus,
   volition, affect, metacognition, identity, and memory.
4. Validate those existing organs and behaviors before coupling organs or
   adding autonomous cycles.
5. Keep duplicate/conflict automation and authenticated ownership as separate
   later workstreams; design ownership before personal data or
   external/embodied operation expands.
6. Reduce code monoliths behind the frozen regression gate.
```

See `docs/project-state.md` for the integrated current-state map and the
priority rationale. The older response-control M1 remains intentionally on hold
until retrieval, maintenance, and evidence receipts are stronger.

## Local Run

Backend:

```bash
cd backend
source .venv/bin/activate
uvicorn app.asgi:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open:

```txt
http://127.0.0.1:5173
```

The local UI is a Tailwind-based Scarlet dashboard with recent sessions,
conversation, live agent stream, semantic memories, user profile, and runtime
settings. Default runtime settings are Italian language, Italy as configured
locale, `Europe/Rome` timezone, and a local active user profile; changes saved
in the dashboard apply to future turns.

Evaluation runner:

```bash
cd backend
python -m app.evals.runner scripted app/evals/scenarios/baseline_tool_schema.json
python -m app.evals.runner scripted app/evals/scenarios/memory_v0_preference.json
python -m app.evals.runner scripted app/evals/scenarios/visible_metacognition_probe.json
python -m app.evals.runner scripted app/evals/scenarios/cognitive_api_metacognition_probe.json
python -m app.evals.runner interactive --title "adaptive baseline"
```

## Secrets

Do not commit real API keys.

## Laboratory State

`backend/data/app.db` is a legacy LFS-tracked laboratory snapshot, not the VPS
production database and not an automatic test target. The current worktree
copy is mutable and must stay out of ordinary code commits. Production data is
the remote mounted database and is never transferred from this repository.

The canonical ownership map and deployment procedure live in
`docs/database-topology.md`. This remains an experimental-lab policy, not a
production privacy model. The repository must still exclude API keys, `.env`
files, provider credentials, and other secrets.

Expected future environment variables:

```txt
LLM_PROVIDER=minimax
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/anthropic
MINIMAX_MODEL=MiniMax-M3
MINIMAX_MAX_TOKENS=131072
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/apps/anthropic
QWEN_MODEL=qwen3.7-max
QWEN_MAX_TOKENS=4096
MAINTENANCE_ENABLED=true
MAINTENANCE_IDLE_SECONDS=900
MAINTENANCE_WORKER_INTERVAL_SECONDS=5
MAINTENANCE_JOB_BATCH_SIZE=5
AGENT_SYSTEM_PROMPT_PATH=
DATABASE_URL=sqlite:///./data/app.db
DATABASE_ROLE=auto
```

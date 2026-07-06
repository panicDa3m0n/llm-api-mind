# LLM API Mind - Project Blueprint

Version: 1.13.0
Status: active experimental runtime
Last updated: 2026-06-19
Primary human: project owner, evaluator, direction, validation  
Primary software engineer: Codex/Scarlet as IDE agent

## 1. Purpose

This project explores whether an LLM can become more capable, coherent, and useful when it is placed inside a modular external cognitive environment exposed through a small API surface.

The goal is not to claim consciousness, simulate mysticism, or build a large agent platform before we have evidence. The goal is to run falsifiable experiments that test whether cognitive components such as memory, attention, reflection, goals, planning, tracing, and asynchronous background processes measurably improve an LLM agent.

The core hypothesis:

```txt
LLM capability can be extended more effectively through a stable cognitive API
than by giving the model many direct tools and long procedural prompts.
```

The project should remain evidence-driven. Every important component must answer:

```txt
What behavior does this improve?
How do we measure it?
What baseline are we comparing against?
What traces prove what happened?
```

## 1.1 Current State Map

The original foundation milestone has been reached and extended. The current
runtime now includes persistent provider-native chat history, API Mind,
semantic memory, atomic facts, episodic session recall, one metacognition
route, runtime events, and a live React cockpit.

The canonical integrated status and convergent roadmap now live in:

```txt
docs/project-state.md
```

The canonical documentation index and branch map now live in:

```txt
docs/project-documentation.md
docs/branches/README.md
```

Use this blueprint for durable philosophy and architecture constraints. Use
`docs/project-state.md` for the current implementation map, confirmed evidence,
planned-but-unimplemented ideas, and priority ordering across converging
functional areas.

## 2. Operating Philosophy

### 2.1 Build Experiments Before Architecture

Avoid designing a huge "digital mind" upfront. Build small components that can be tested immediately, then compose only the pieces that show value.

Preferred sequence:

```txt
hypothesis -> minimal implementation -> trace -> eval -> decision -> integration
```

### 2.2 One Primary Tool For The Agent

The agent should not receive many tools directly. It should primarily receive one stable tool:

```txt
mind_api(method, path, body, intent)
```

The internal API can evolve without constantly retraining or reprompting the agent. The LLM learns the protocol, while the backend owns the implementation details.

### 2.3 API As Cognitive Environment

The API is not only a technical backend. It is the agent's external cognitive environment.

It should provide:

- schemas the agent can inspect;
- schema version and digest signals so route-shape drift is visible;
- structured cognitive hints;
- useful errors;
- trace identifiers;
- suggested next actions when appropriate;
- state summaries;
- memory and attention support;
- internal metacognition through one traceable route, including controlled
  previous-turn thinking retrospection;
- event handling;
- asynchronous background processes.

### 2.4 No Hidden Magic

Terms such as "subconscious" are allowed as architectural metaphors, but every mechanism must be technically explicit.

In this project, "subconscious" means:

```txt
asynchronous background processes triggered by events, schedules, or state changes,
which update the cognitive environment without being directly invoked in the current agent turn.
```

### 2.5 Documentation Is Part Of The Runtime

Because the project is developed with an IDE LLM agent, documentation is not optional. It is a memory system for the engineering process.

The agent must use documentation to avoid:

- repeating old decisions;
- reintroducing fixed bugs;
- drifting from project goals;
- forgetting architectural constraints;
- building unmeasured abstractions;
- hallucinating missing context.

## 3. Roles

### 3.1 Human Role

The human owner provides:

- direction and priorities;
- conceptual feedback;
- acceptance decisions;
- qualitative evaluation of agent behavior;
- API keys and external service access when needed;
- product and research intuition;
- final approval for irreversible or external-world actions.

The human should not need to micromanage implementation details, documentation refreshes, or when the IDE agent rereads project context.

### 3.2 Codex/Scarlet Role

Codex/Scarlet is the primary software engineer and project memory maintainer.

Responsibilities:

- read relevant project docs before non-trivial changes;
- maintain this blueprint as assumptions evolve;
- add or update decision records;
- track bugs and avoid regressions;
- implement code conservatively;
- run relevant tests;
- preserve traceability;
- keep the system small until evidence justifies expansion;
- proactively identify when new documentation is needed.

Expected behavior before work:

```txt
1. Inspect current repo state.
2. Read this blueprint.
3. Read active decisions and recent activity logs once they exist.
4. Identify the smallest useful next change.
5. Implement, verify, and update docs if the change affects architecture or process.
```

## 4. Initial Technical Stack

The initial stack should optimize for fast experiments, inspectability, and future extensibility.

### 4.1 Backend

Preferred:

```txt
Python
FastAPI
Pydantic
SQLModel or SQLAlchemy
SQLite for MVP
pytest
```

Reason:

- FastAPI gives OpenAPI/Swagger naturally.
- Python is strong for LLM orchestration, evals, workers, and data experiments.
- SQLite is enough for early trace and memory tests.
- The stack is easy for an IDE agent to inspect and modify.

Avoid at first:

- microservices;
- Kafka;
- Celery unless truly needed;
- LangChain or LlamaIndex as core dependencies;
- complex auth;
- premature vector database infrastructure;
- frontend-heavy dashboards.

### 4.2 LLM Provider

Initial provider:

```txt
MiniMax M3
Anthropic-compatible API
base_url: https://api.minimax.io/anthropic
model: MiniMax-M3
```

Comparison provider:

```txt
Qwen 3.7 via Alibaba Model Studio
Anthropic-compatible API
base_url: https://dashscope-intl.aliyuncs.com/apps/anthropic
model: qwen3.7-max
```

Provider abstraction should exist early, but stay thin:

```txt
LLMProvider.generate(...)
LLMProvider.stream(...)
LLMProvider.tool_loop(...)
```

Do not let provider-specific response shapes leak everywhere.

### 4.3 Frontend

Preferred:

```txt
Vite
React
TypeScript
minimal debug cockpit
```

Purpose:

- chat with the agent;
- inspect turn traces;
- inspect tool calls;
- inspect memories;
- inspect events;
- inspect current agent state;
- compare baseline and mind-agent runs later.

The frontend is not a landing page and not a polished product at first. It is an experimental cockpit.

### 4.4 Background Processes

Initial approach:

```txt
in-process scheduler
event queue table
simple worker loop
```

Only add external queues or worker systems when local evidence shows they are necessary.

### 4.5 Laboratory State Versioning

During the current private laboratory phase, runtime state is part of the experiment evidence.

The SQLite database is intentionally versioned:

```txt
backend/data/app.db
```

It can contain sessions, messages, turns, traces, tool calls, and Memory v0 records. This allows the Windows and macOS development environments to share the same laboratory continuity through Git.

This policy has strict boundaries:

- API keys, `.env` files, and provider credentials must never be committed.
- The database is allowed because current lab users are technical participants who know that conversations and memory records are repository artifacts.
- A public or multi-user release must revisit the storage policy before accepting external user data.
- SQLite is a binary file, so parallel edits across machines can create merge conflicts; the owner should treat one machine at a time as the active state writer unless a later storage strategy replaces this.

## 5. Target Repository Structure

Expected structure:

```txt
llm-api-mind/
  backend/
    app/
      main.py
      config.py

      llm/
        provider.py
        minimax_client.py

      agent/
        runtime.py
        prompts.py
        tool_loop.py

      mind/
        schema.py
        dispatcher.py
        state.py
        memory.py
        attention.py
        events.py
        reflection.py
        goals.py

      storage/
        db.py
        models.py
        repositories.py

      workers/
        scheduler.py
        subconscious.py

      evals/
        runner.py
        scenarios/

      prompts/
        identity.md
        rules.md
        intelligence.md
        api_protocol.md

    tests/
    pyproject.toml
    .env.example

  frontend/
    src/
      App.tsx
      api.ts
      components/
        Chat.tsx
        TracePanel.tsx
        MemoryPanel.tsx
        StatePanel.tsx
    package.json

  docs/
    project-blueprint.md
    decisions.md
    activity-log.md
    bug-ledger.md
    experiments.md
    api-contract.md

  docker-compose.yml
  README.md
```

This is a target structure, not a command to create everything immediately.

## 6. Core Runtime Architecture

### 6.1 High-Level Flow

```txt
User
  -> frontend chat
  -> backend chat endpoint
  -> agent runtime
  -> attention/context preparation
  -> MiniMax M3
  -> autonomous mind_api cognitive operations
  -> mind API dispatcher
  -> storage/events/memory/metacognition/state
  -> tool result back to model
  -> final assistant response
  -> trace + eval hooks
  -> frontend response and debug panels
```

### 6.2 Agent Visible Tool

The LLM should see one primary cognitive interface:

```json
{
  "name": "mind_api",
  "description": "Scarlet's internal cognitive API. Use it autonomously for schema awareness, memory, facts, traceable state inspection, and cognitive support before answering when that improves correctness.",
  "input_schema": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "enum": ["GET", "POST"]
      },
      "path": {
        "type": "string"
      },
      "body": {
        "type": "object"
      },
      "intent": {
        "type": "string",
        "description": "Short natural language reason for the call."
      }
    },
    "required": ["method", "path", "intent"]
  }
}
```

### 6.3 Internal Mind API Response Shape

Mind API responses should be structured for both machine use and model interpretation:

```json
{
  "ok": true,
  "result": {},
  "cognitive_hint": "Short explanation of how this result may matter.",
  "suggested_next_actions": [],
  "confidence": 0.8,
  "trace_id": "trace_..."
}
```

### 6.4 Cognitive API Autonomy

API Mind is Scarlet's internal cognitive environment, not a user-operated
feature. The user should be able to speak in natural language without knowing
which routes, schemas, memories, or fact stores exist.

Scarlet decides autonomously when to inspect schema, search memory, read facts,
resolve conflicts, or mutate cognitive state through traceable operations. A
normal answer should expose the result and source discipline, not require the
user to instruct tool usage.

The chat runtime should not impose an artificial fixed tool-call cap. Scarlet's
internal loop ends when she has enough evidence to answer or when only human
judgment can resolve the next step. Long-running loops still need normal
engineering observability through traces, streaming events, and eventual
cancellation/backpressure work.

Errors should be equally structured:

```json
{
  "ok": false,
  "error": {
    "code": "memory.not_found",
    "message": "No relevant memory was found for this query.",
    "recoverable": true
  },
  "suggested_next_actions": [
    "Continue without memory",
    "Ask the user for clarification",
    "Try a broader memory search"
  ],
  "trace_id": "trace_..."
}
```

### 6.4.1 Schema Discipline And Internal Cognition

`GET /mind/schema` is the machine-readable capability catalog for the current
API Mind surface. The system prompt should teach Scarlet when to inspect route
availability, while detailed body schemas, examples, and retry guidance are
returned as endpoint-local `usage_guide` on recoverable endpoint errors.

The runtime context should include a compact schema reference:

```json
{
  "mind_schema": {
    "schema_version": "2026-05-24.schema-catalog-v1",
    "schema_digest": "sha256:...",
    "schema_route": "GET /mind/schema"
  }
}
```

First implemented cognitive route:

```txt
POST /mind/metacognition/step
```

This route gives Scarlet one traceable internal cognitive operation:

- metacognitive review;
- claim checks;
- temporary workspace notes;
- reflection;
- next-action planning.

Visible metacognition remains only the public summary layer. Internal
metacognition should be structured and traceable. From V1.8.0, controlled
previous-turn thinking retrospection can inspect reasoning as process evidence,
but it must not treat prior thinking as factual proof about the outside world.

### 6.4 Memory Context Pipeline v0

Memory retrieval should become a runtime perceptual phase, not an optional tool action that the model may or may not choose.

Target turn flow:

```txt
user message
-> build TurnFrame
-> automatic memory retrieval
-> ranking, exclusions, and conflict detection
-> traced memory context pack
-> LLM call with backend-generated runtime context
-> answer
-> optional post-turn consolidation
```

Every chat turn should produce a `memory.context` trace, even when no relevant memory is selected. The absence of relevant memory should be an observable runtime result, not an unverified model claim.

`TurnFrame` should use more than the current user message:

```json
{
  "current_user_message": "...",
  "recent_dialogue": ["..."],
  "previous_memory_context": {},
  "session_metadata": {},
  "active_project_scope": "project",
  "available_capabilities": {},
  "time": "..."
}
```

The model-facing runtime context should be generated by the backend and kept separate from the stable system prompt and from user text:

```txt
<runtime_context>
{
  "memory_context": {
    "searched": true,
    "trace_id": "trace_...",
    "selected": [],
    "near_miss": [],
    "excluded": [],
    "conflicts": [],
    "negative_evidence": "none"
  },
  "capabilities": {
    "memory.write": "implemented",
    "memory.search": "implemented",
    "memory.{memory_id}": "implemented",
    "memory.conflicts": "implemented",
    "memory.deprecate": "implemented",
    "memory.supersede": "implemented",
    "memory.update": "unavailable"
  }
}
</runtime_context>
```

The v0 implementation should be budgeted and traceable:

- run retrieval on every turn;
- inspect more candidates internally than the model sees, for example top 10 to 20;
- pass only zero to five selected memories to the model;
- trace selected, near-miss, excluded, and conflicting candidates;
- record why each candidate was selected or excluded;
- preserve source IDs, confidence, salience, age, and usage metadata.

Retrieval should become multi-stage over time:

1. Lexical search with SQLite FTS5/BM25 for exact names and rare terms.
2. Dense embeddings for paraphrases and conceptual similarity.
3. Rank fusion, initially Reciprocal Rank Fusion, to combine sparse and dense rankings.
4. Reranking to evaluate whether a candidate helps this turn.
5. Relevance guard to separate `selected`, `near_miss`, and `excluded`.
6. Conflict detection when active memories describe the same subject inconsistently.

The first implementation slice does not require embeddings. The current v0 implementation starts with automatic per-turn lexical retrieval over active memory records, a relevance guard, runtime context injection, and `memory.context` traces. SQLite FTS5/BM25, dense retrieval, and cross-encoder reranking can follow after the automatic pipeline is observable in live use.

Prompt contract:

- use runtime context as operational evidence, not as user-authored text;
- do not claim memory is absent unless `memory_context.searched` is true, or unless a memory search tool result supports the claim;
- if `selected` is empty and `searched` is true, say that no relevant memory was found;
- if conflicts are present, name the conflict instead of silently choosing one;
- use runtime `capabilities` as the source of truth for implemented vs unavailable APIs;
- if a capability is unavailable, say so and propose implementation instead of promising the action.

A later post-response validator should flag unverifiable memory claims, especially answers that say something is or is not in memory when no `memory.context` trace or explicit memory search exists for the turn.

### 6.5 Memory Robustness Roadmap

The current Memory v0 implementation is accepted as an experimental substrate,
not as the final memory design. Live probes show that the system is strong at
traceability but still needs robustness work before memory can support deeper
cognitive modules.

Detailed roadmap:

```txt
docs/memory-roadmap.md
```

The roadmap incorporates lessons from the project's own live traces and from
the external `obsidian-memory-for-ai` v3 pattern:

```txt
https://github.com/jrcruciani/obsidian-memory-for-ai
```

Useful external ideas to adapt, not copy directly:

- atomic facts;
- controlled predicates;
- entity/predicate/value/provenance as the durable memory unit;
- bi-temporal validity fields;
- lint/health checks;
- generated operational views;
- inbox/proposal and compaction workflows;
- reflect-after-session maintenance.

Project-specific adaptation:

LLM API Mind remains API/CLI-first. Markdown vaults are useful inspiration, but
the source of truth should be backend tables, `mind_api` contracts, CLI wrappers,
traces, and debug views. The model should still primarily see one tool.

Updated memory implementation order:

```txt
1. Entity-aware retrieval guard, then SQLite FTS5/BM25.
2. Proposal inbox and compaction.
3. CLI/debug memory views and expanded evals.
4. Re-test response-control guardrails after lifecycle/retrieval evidence is stronger.
```

The next slices should avoid treating a prompt change as a substitute for memory
semantics. Prompt discipline is useful, but robust memory needs backend state,
contracts, validation, and traceable lifecycle operations.

Status update 2026-05-20:

The owner put response-control M1 on hold because the observed behavior may be a
false bug while lifecycle/conflict management is missing. M2 is now implemented:
`GET /mind/memory/{memory_id}`, `GET /mind/memory/conflicts`,
`POST /mind/memory/deprecate`, and `POST /mind/memory/supersede` are available
through the single `mind_api` surface and were live-verified against the
Zero-Luce memory conflict.

M3 is also initially implemented: `memory_facts` stores canonical
entity/predicate/value facts linked to memory records, memory writes and
backfills create facts, lifecycle operations propagate fact status, and
Zero-Luce multilingual aliases resolve to the same `protocollo-zero-luce` +
`response_format` fact layer. The next memory slice should use these facts to
improve entity-aware retrieval and reduce wrong-entity selected evidence.

Status update 2026-05-22:

The memory architecture now explicitly separates semantic memory from episodic
recall. Semantic memory remains the durable reusable layer in `memories` and
`memory_facts`. Episodic recall is implemented through `session_summaries` plus
`GET /mind/sessions`, `GET /mind/sessions/{session_id}`, and
`POST /mind/sessions/{session_id}/summarize`. A semantic memory's
`source_session_id` is the bridge back to the exact prior conversation when
Scarlet needs provenance, wording, or surrounding context.

## 7. Initial API Surface

### 7.1 Chat And Debug API

Needed for human interaction and development:

```txt
POST /api/chat/sessions
POST /api/chat/sessions/{session_id}/turn
GET  /api/chat/sessions/{session_id}/messages
GET  /api/debug/traces/{turn_id}
GET  /api/debug/events
GET  /api/debug/state/{session_id}
```

### 7.2 Mind API

Initial cognitive API:

```txt
GET  /mind/schema
GET  /mind/state
POST /mind/memory/write
POST /mind/memory/search
GET  /mind/memory/{memory_id}
GET  /mind/memory/conflicts
POST /mind/memory/deprecate
POST /mind/memory/supersede
GET  /mind/sessions
GET  /mind/sessions/{session_id}
POST /mind/sessions/{session_id}/summarize
POST /mind/attention/context
POST /mind/metacognition/step
```

The first implementation can be simple. The important part is stable contracts and traceability.

## 8. Data Model MVP

Initial tables:

```txt
sessions
messages
turns
traces
tool_calls
events
memories
memory_facts
session_summaries
agent_state
eval_runs
eval_results
```

Memory fields:

```txt
id
source_session_id
source_turn_id
source_message_id
type: project_fact | user_preference | decision | correction | task_context | behavioral_pattern | episodic
scope: project | user | session
status
content
reason_for_storage
expected_future_use
salience
confidence
tags_json
metadata_json
usage_count
created_at
updated_at
last_used_at
```

Tool call fields:

```txt
id
turn_id
tool_name
arguments_json
result_json
status
latency_ms
created_at
```

Event fields:

```txt
id
session_id
turn_id
type
payload_json
source
processed_at
created_at
```

## 9. Prompt Architecture

The system prompt should be assembled from small files:

```txt
identity.md
rules.md
intelligence.md
api_protocol.md
runtime_state.md generated by backend
```

Current MVP implementation:

```txt
backend/app/prompts/scarlet_system.md
```

The MVP uses one bundled Scarlet prompt before full prompt assembly exists. It can be replaced through `AGENT_SYSTEM_PROMPT` or `AGENT_SYSTEM_PROMPT_PATH`. Every chat turn should receive an effective system prompt, and the `llm.request` trace should record the prompt source so prompt changes remain inspectable.

Prompt style principle:

```txt
Define the desired agent identity and operating posture in positive terms.
Avoid domain-specific denials or corrective examples unless a real experiment shows
that a model bias cannot be handled through architecture, API state, or traces.
```

Every sentence in the system prompt should have a behavioral purpose. Remove filler, generic platitudes, and defensive rules that might become repeated self-description.

Conversational identity principle:

```txt
The agent should sound present, feminine, and conversationally alive without
pretending to have unprovided memories, senses, or runtime capabilities.
```

Human-like communication should be encoded as observable style choices: answer the user's actual move first, use natural pacing, vary sentence length, ask focused questions only when useful, and let warmth come from attention rather than generic enthusiasm.

When the user asks subjective questions, the prompt should guide Scarlet toward conversational stance and lightweight impressions rather than long explanations about model ontology. When the user requests a non-list or natural response, prose should be preferred.

Visible metacognition principle:

```txt
Scarlet may expose a concise public self-monitoring note when explicitly asked
to think aloud or when a turn is cognitively important. This is not a raw
chain-of-thought dump; it is a short summary of objective, evidence source,
uncertainty/risk, and next cognitive action.
```

### 9.1 Identity

Defines who the agent is, continuity style, tone, and relationship to the human.

### 9.2 Rules

Defines safety, consent, honesty, uncertainty, external actions, and boundaries.

### 9.3 Intelligence

Defines operational cognition:

- verify unstable facts;
- use memory intentionally;
- ask for clarification when needed;
- avoid inventing missing state;
- use the cognitive API before relying on stale assumptions;
- keep responses useful and grounded.

### 9.4 API Protocol

Defines how to use `mind_api`, when to inspect `/mind/schema`, and how to interpret structured errors and hints.

## 10. Tracing Requirements

Every turn should produce a trace that can answer:

```txt
What did the user ask?
What context was provided to the model?
What memory was retrieved?
What automatic memory context was constructed, even if empty?
Which memory candidates were selected, excluded, or marked as near misses?
What tool calls happened?
What did each tool return?
What final answer was produced?
What events were emitted?
What background jobs ran afterward?
What changed in memory or state?
```

Events are separate from deep traces: traces explain a turn in full detail,
while ordered `events` rows are the compact runtime control plane for UI
activity, next-turn context, and future background maintenance triggers.

Minimum trace object:

```json
{
  "turn_id": "...",
  "session_id": "...",
  "user_message": "...",
  "context_pack": [],
  "memory_context": {
    "searched": true,
    "selected": [],
    "near_miss": [],
    "excluded": [],
    "conflicts": []
  },
  "model": "MiniMax-M3",
  "tool_calls": [],
  "events": [],
  "memory_reads": [],
  "memory_writes": [],
  "assistant_response": "...",
  "latency_ms": 0,
  "usage": {},
  "errors": []
}
```

## 11. Experiments

### 11.1 Experiment 1 - Baseline Chat Trace

Hypothesis:

```txt
Before cognitive modules, full tracing alone improves development quality
because failures become inspectable.
```

Build:

- MiniMax chat call;
- session storage;
- message storage;
- full trace capture;
- minimal frontend chat.

Pass condition:

- every chat turn is reproducible from stored trace;
- provider errors are visible and understandable;
- no hidden state is required to debug a response.

### 11.2 Experiment 2 - Episodic Memory

Hypothesis:

```txt
The agent with memory API retrieves prior project facts more accurately than the baseline.
```

Build:

- `/mind/memory/write`;
- `/mind/memory/search`;
- automatic Memory Context Pipeline v0;
- lexical v0 retrieval for the first automatic context slice;
- SQLite FTS5/BM25 search as the next lexical scoring improvement;
- relevance guard and selected/near-miss/excluded trace output;
- memory panel in frontend after the context pack is reliable;
- baseline vs memory-agent scenarios.

Metrics:

- correct recall;
- false recall;
- useful memory retrieval rate;
- unnecessary memory retrieval rate;
- latency impact.

### 11.3 Experiment 3 - Attention Context Pack

Hypothesis:

```txt
An attention module that prepares a small context pack improves response relevance
without flooding the model context.
```

Build:

- `/mind/attention/context`;
- retrieval and ranking over memories, state, active goals, recent events;
- visible context pack in debug trace.

Metrics:

- task success;
- context precision;
- context recall;
- token overhead;
- user-rated usefulness.

### 11.4 Experiment 4 - Reflection After Failure

Hypothesis:

```txt
Structured reflection after failure reduces repeated mistakes across similar tasks.
```

Build:

- reflection mode inside `/mind/metacognition/step`;
- failure event types;
- reflection records;
- optional rule suggestions;
- regression scenarios.

Metrics:

- repeated failure rate;
- correct identification of failure mode;
- useful repair suggestions;
- no harmful overcorrection.

### 11.5 Experiment 5 - Goals And Commitments

Hypothesis:

```txt
A goal registry helps the agent preserve project direction and distinguish stable goals
from momentary conversational tasks.
```

Build:

- `/mind/goals/create`;
- `/mind/goals/update`;
- `/mind/goals/active`;
- state panel;
- goal conflict detection later.

Metrics:

- goal continuity;
- fewer forgotten commitments;
- fewer irrelevant actions;
- better prioritization.

### 11.6 Experiment 6 - Subconscious Jobs

Hypothesis:

```txt
Asynchronous event-driven jobs improve continuity by consolidating memory,
summarizing state, and detecting unresolved tasks outside the immediate turn.
```

Build:

- event queue;
- scheduler;
- background memory consolidation;
- unresolved-task detector;
- debug view for processed events.

Metrics:

- useful background updates;
- stale or harmful updates;
- cost and latency outside the turn;
- effect on subsequent responses.

## 12. Roadmap

### Phase 0 - Project Foundation

Deliverables:

- project blueprint;
- repository conventions;
- initial docs;
- `.env.example`;
- README with run instructions once code exists.

Exit criteria:

- future work has a clear map;
- AI agent has a documentation ritual;
- project scope is explicit.

### Phase 1 - Minimal Chat Runtime

Deliverables:

- FastAPI backend;
- MiniMax provider client;
- simple session and message storage;
- minimal React chat;
- trace per turn;
- basic tests.

Exit criteria:

- user can chat with the configured MiniMax model locally;
- every turn is stored and inspectable;
- provider errors are handled clearly.

### Phase 2 - Single Cognitive Tool

Deliverables:

- `mind_api` tool schema;
- MiniMax tool loop;
- `/mind/schema`;
- dispatcher;
- trace of tool calls.

Exit criteria:

- the model can inspect available cognitive API routes;
- the model can call the API through one tool;
- all tool calls are stored.

### Phase 3 - Memory And Attention

Deliverables:

- memory write/search/read and minimal lifecycle;
- attention context pack;
- debug panels for memory and context;
- first baseline eval scenarios.

Exit criteria:

- memory improves at least one measured scenario;
- attention context is visible and auditable;
- false memories are detectable.

### Phase 4 - Reflection And Bug Learning

Deliverables:

- reflection endpoint;
- failure event tracking;
- reflection records;
- regression scenarios for repeated mistakes.

Exit criteria:

- the agent can produce structured failure analysis;
- repeated bugs can be linked to prior fixes;
- reflection changes are evaluated before becoming rules.

### Phase 5 - Goals And Background Processes

Deliverables:

- goal registry;
- event queue;
- scheduler;
- memory consolidation worker;
- unresolved task detector.

Exit criteria:

- background processes create useful state changes;
- all background changes are traceable;
- human can inspect why state changed.

### Phase 6 - External Actions

Deliverables:

- action permission model;
- action registry;
- dry-run mode;
- human approval gates;
- action traces.

Exit criteria:

- real-world actions are possible but controlled;
- no irreversible action happens without policy support;
- action outcomes are logged.

## 13. Documentation System

This blueprint is the root document. Additional docs should be created when the project reaches the relevant phase.

### 13.1 Required Docs

```txt
AGENTS.md
CHANGELOG.md
docs/project-blueprint.md
docs/decisions.md
docs/activity-log.md
docs/bug-ledger.md
docs/experiments.md
docs/api-contract.md
docs/memory-roadmap.md
docs/release-process.md
```

### 13.2 Decision Log

Use `docs/decisions.md` for architectural decisions.

Decision entry format:

```md
## ADR-0001 - Title

Date:
Status: proposed | accepted | superseded

Context:

Decision:

Alternatives Considered:

Consequences:

Links:
```

### 13.3 Activity Log

Use `docs/activity-log.md` to preserve work continuity.

Entry format:

```md
## 2026-05-08 - Short Title

Goal:
Changes:
Verification:
Open Questions:
Next Suggested Step:
```

### 13.4 Bug Ledger

Use `docs/bug-ledger.md` to prevent rediscovering the same bugs.

Entry format:

```md
## BUG-0001 - Short Title

Date Found:
Status: open | fixed | monitoring
Symptoms:
Root Cause:
Fix:
Regression Test:
Related Files:
Notes:
```

### 13.5 Experiments Doc

Use `docs/experiments.md` for hypotheses, scenarios, metrics, and results.

Entry format:

```md
## EXP-0001 - Title

Hypothesis:
Baseline:
Variant:
Scenario:
Metrics:
Result:
Decision:
```

### 13.6 API Contract Doc

Use `docs/api-contract.md` to document stable API contracts once implemented.

Each API entry should include:

- route;
- purpose;
- request schema;
- response schema;
- error codes;
- example;
- trace behavior.

## 14. AI Agent Development Ritual

Before any non-trivial implementation, Codex/Scarlet should:

```txt
1. Check git status.
2. Inspect project structure.
3. Read docs/project-blueprint.md.
4. Read docs/decisions.md if it exists.
5. Read docs/activity-log.md if it exists.
6. Read docs/bug-ledger.md if it exists and the task touches existing behavior.
7. Identify active phase and smallest useful next change.
8. Implement.
9. Run relevant tests.
10. Update docs when decisions, APIs, experiments, or bug knowledge changed.
```

During work:

- preserve user changes;
- avoid unrelated refactors;
- prefer small verifiable slices;
- keep traceability;
- update plans as steps complete;
- document meaningful discoveries.

After work:

- summarize changed files;
- summarize verification;
- note unresolved risks;
- add follow-up tasks when useful.

## 15. Engineering Guardrails

### 15.1 Add Dependencies Conservatively

Before adding a dependency, answer:

```txt
What problem does it solve now?
Can the standard library or existing stack solve it?
Will it make traces or debugging harder?
Can it be replaced later?
```

### 15.2 Keep Provider Isolation

MiniMax-specific request and response logic should live in the MiniMax provider module.

The agent runtime should deal with normalized messages, tool calls, usage, and errors.

### 15.3 Never Lose Raw Provider Data

For experiments, store normalized traces and raw provider responses when safe.

Raw responses are useful for debugging tool loops, provider quirks, latency, and usage.

### 15.4 Prefer Inspectable State

If a process changes memory, goals, or state, it must leave an event or trace.

No silent mutation of cognitive state.

### 15.5 Prompt Changes Are Code Changes

Prompt files affect behavior and should be treated as code:

- review diffs carefully;
- note why the change was made;
- test behavior if possible;
- avoid large vague prompt rewrites.

## 16. Security And Secrets

Never commit real API keys.

Expected environment variables:

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
DATABASE_URL=sqlite:///./data/app.db
```

Use `.env.example` for placeholders only.

External-world actions must eventually support:

- dry-run mode;
- permission scopes;
- human confirmation;
- action audit logs;
- reversible-first design where possible.

## 17. Evaluation Principles

An improvement is not accepted because it feels intelligent. It is accepted when it improves measured behavior or unlocks a necessary research capability.

Evaluation types:

- automated scenario tests;
- adaptive human-in-the-loop sessions;
- trace inspection;
- baseline vs variant comparison;
- human rating;
- regression tests for known bugs;
- latency and cost comparison.

Minimum comparison pattern:

```txt
baseline MiniMax
vs
MiniMax + specific cognitive module
```

Avoid comparing a full improved system against a weak baseline without isolating which component caused the improvement.

## 18. First Implementation Slice

The first useful implementation should be:

```txt
FastAPI backend
MiniMax provider client
POST /api/chat/sessions
POST /api/chat/sessions/{session_id}/turn
SQLite storage
turn trace
minimal React chat
```

Do not implement memory, attention, goals, or background jobs until the basic runtime trace is stable.

Reason:

```txt
The trace system is the microscope. Build the microscope before studying cognition.
```

## 19. Focus Rules

When uncertain, prefer the option that:

- creates useful evidence sooner;
- reduces hidden state;
- improves debuggability;
- keeps the model-facing API small;
- preserves future flexibility;
- can be tested locally;
- can be explained in one trace.

Avoid:

- large abstractions without a measured need;
- unlogged state changes;
- vague "agent intelligence" additions;
- new components without an experiment;
- changing prompts and code at the same time unless necessary;
- polished UI before reliable behavior.

## 20. Current Next Steps

Immediate next recommended steps:

```txt
1. Keep MiniMax M3 active for owner-led human evaluation, with M2.7 rollback via MINIMAX_MODEL.
2. Inspect real idle maintenance output through maintenance overview/jobs/proposals before adding new background processes.
3. Keep memory merge/update/deprecate automation conservative until embedding/KG evidence is available from the Windows GPU setup.
4. Review Goal/Focus/Task theory before implementing a real operational-management organ.
5. Review Metacognition theory before changing the current single metacognition path.
6. Defer brittle natural-answer validators and product UX polish until the underlying cognition branches justify them.
```

The first milestone is not "digital mind". The first milestone is:

```txt
A local chat agent using MiniMax M3 where every turn is inspectable, reproducible,
and now able to run traceable semantic memory, episodic recall, and metacognition experiments.
```

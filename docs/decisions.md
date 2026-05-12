# Decision Log

Architectural decisions should be recorded here when they affect future implementation choices.

## ADR-0001 - Documentation As Project Memory

Date: 2026-05-08  
Status: accepted

Context:

The project will be developed over multiple iterations with an IDE LLM agent. Conversational memory alone is not reliable enough to preserve architectural direction, prior fixes, and experiment rationale.

Decision:

Project memory will be stored in repository documentation. `AGENTS.md` is the short operating protocol, while `docs/project-blueprint.md` is the detailed project foundation. Companion docs track activity, decisions, bugs, experiments, and API contracts.

Alternatives Considered:

- Relying on conversational memory only.
- Keeping all project memory in a single large document.
- Waiting to add documentation until after implementation.

Consequences:

- The agent has a repeatable start and done checklist.
- Future work can recover context from files.
- Meaningful code, prompt, API, and architecture changes must update documentation.
- Documentation maintenance becomes part of the engineering workflow.

Links:

- `AGENTS.md`
- `docs/project-blueprint.md`

## ADR-0002 - Initial System Shape

Date: 2026-05-08  
Status: accepted

Context:

The project aims to test whether an LLM improves when supported by a modular cognitive API. It should avoid overengineering and prioritize falsifiable experiments.

Decision:

The first implementation milestone is a traceable local chat runtime using MiniMax M2.7 before memory, attention, reflection, goals, or background processes are implemented.

Initial preferred stack:

```txt
FastAPI backend
MiniMax M2.7 through Anthropic-compatible API
SQLite storage for MVP traces
Minimal React debug cockpit after backend trace is stable
```

Alternatives Considered:

- Starting with all cognitive modules immediately.
- Starting with a full agent framework.
- Starting with a polished frontend.

Consequences:

- Tracing becomes the first research instrument.
- Cognitive modules must justify themselves through experiments.
- Provider-specific details should remain isolated in the LLM provider layer.

Links:

- `docs/project-blueprint.md`
- `docs/experiments.md`

## ADR-0003 - Git History, Changelog, And Agent Commit Identity

Date: 2026-05-08  
Status: accepted

Context:

The project owner wants GitHub history to clearly distinguish human interventions from IDE-agent development and wants commit analysis to remain aligned with concrete changelog and roadmap progress.

Decision:

Use repository-local Git author metadata for Codex/Scarlet commits:

```txt
Scarlet Codex <scarlet-codex@users.noreply.github.com>
```

Maintain `CHANGELOG.md` as the concrete project-visible history. Meaningful commits should include changelog, roadmap, and verification notes using `.gitmessage`.

This author metadata does not create a real independent GitHub account. If a real bot account is created later, update the local Git config and this ADR.

Alternatives Considered:

- Use the human owner's global Git identity for all commits.
- Wait to define commit conventions until after implementation starts.
- Depend only on GitHub UI history without a changelog.

Consequences:

- Commit author metadata can distinguish agent-authored local commits from human-authored commits.
- The pusher on GitHub may still be the human-authenticated account unless a separate bot account is configured.
- Every meaningful commit should map to `CHANGELOG.md` and at least one roadmap, ADR, experiment, or issue reference.

Links:

- `docs/release-process.md`
- `CHANGELOG.md`
- `.gitmessage`

## ADR-0004 - Use SQLModel For MVP Storage Layer

Date: 2026-05-08  
Status: accepted

Context:

Phase 1 will soon add SQLite persistence for sessions, messages, turns, and traces. The project needs a storage layer that is quick to implement, readable for an IDE agent, and compatible with FastAPI/Pydantic without adding heavy framework behavior.

Decision:

Use SQLModel for the MVP storage layer. SQLModel keeps the SQLAlchemy foundation available while reducing boilerplate for typed models and API-facing schemas.

Alternatives Considered:

- Plain SQLAlchemy: powerful and explicit, but more boilerplate for this early experimental slice.
- Raw SQLite: very small, but likely to create ad hoc data access patterns too early.
- Full ORM/framework stack: unnecessary before baseline tracing exists.

Consequences:

- Early data models can serve both persistence and typed validation needs.
- Future migrations to deeper SQLAlchemy patterns remain possible.
- SQLModel is included as a backend dependency before the first storage tables are implemented.

Links:

- `backend/pyproject.toml`
- `docs/project-blueprint.md`

## ADR-0005 - Use MiniMax Through Anthropic-Compatible SDK

Date: 2026-05-08  
Status: accepted

Context:

MiniMax M2.7 supports Anthropic-compatible API calls and tool-use/interleaved-thinking behavior. The project will eventually need reliable tool-call loops and preservation of complete assistant content blocks across multi-turn tool interactions.

Decision:

Use the Anthropic-compatible MiniMax API through the official `anthropic` Python SDK for the initial provider implementation.

Configuration:

```txt
MINIMAX_BASE_URL=https://api.minimax.io/anthropic
MINIMAX_MODEL=MiniMax-M2.7
```

Alternatives Considered:

- Direct HTTP against MiniMax text completion endpoint: smaller dependency surface, but lower-level and less aligned with future tool-use handling.
- OpenAI-compatible API: useful option, but Anthropic-compatible format better preserves thinking/tool blocks for M2.7.

Consequences:

- Provider-specific behavior is isolated in `backend/app/llm/minimax_client.py`.
- Future tool-loop implementation should preserve full assistant content blocks as MiniMax documentation recommends.
- Smoke tests and agent calls need enough output budget because reasoning models may consume tokens before final text.
- Baseline chat endpoints pass persisted user/assistant history as structured provider messages, not as one flattened transcript string.

Links:

- `backend/app/llm/minimax_client.py`
- `docs/api-contract.md`

## ADR-0006 - Use Generous MiniMax Output Budget By Default

Date: 2026-05-08  
Status: accepted

Context:

The project owner uses a MiniMax Token Plan subscription. The project goal is experimental quality and behavioral evidence, not minimizing token spend. MiniMax M2.7 also uses interleaved thinking and can consume output budget before final text, so tight defaults can produce misleading failures.

Decision:

Use `MINIMAX_MAX_TOKENS=4096` as the backend default output budget for MiniMax calls. Individual requests may override it, but defaults should not be artificially low.

Alternatives Considered:

- Keep the smoke default at `128`: worked for a tiny diagnostic, but encoded the wrong project priority.
- Keep very low token defaults for cost control: rejected because the Token Plan is request-based for M2.7 and this project optimizes for quality and observability.
- Set extremely large defaults immediately: deferred until we have persistent traces and real chat workloads.

Consequences:

- M2.7 has enough room for reasoning and final text in normal debug calls.
- Token budget becomes a configurable experimental parameter rather than a hidden economy setting.
- Latency and usage should be measured in traces rather than constrained prematurely.

Links:

- `backend/app/config.py`
- `backend/app/api/debug.py`
- `backend/.env.example`

## ADR-0007 - Use A Configurable Scarlet System Prompt For Chat Runtime

Date: 2026-05-08
Status: accepted

Context:

The baseline chat runtime initially allowed requests without a project system prompt. In that case the provider layer used a generic diagnostic-assistant fallback, which could make the agent present itself as a medical or exam-focused assistant instead of the intended LLM API Mind agent.

Decision:

Every persistent chat turn should receive an effective agent system prompt. The MVP default is the bundled Scarlet prompt:

```txt
backend/app/prompts/scarlet_system.md
```

The prompt can be replaced without code changes through:

```txt
AGENT_SYSTEM_PROMPT
AGENT_SYSTEM_PROMPT_PATH
```

Per-turn `system` values remain available for controlled debug overrides. `llm.request` traces record the effective prompt, source, and path when applicable.

Alternatives Considered:

- Keep identity only in frontend copy: rejected because direct API calls would still be ungrounded.
- Hard-code the prompt in Python: rejected because prompt iteration should be easy and reviewable.
- Wait for full multi-file prompt assembly: deferred because the identity bug is already visible.

Consequences:

- The agent has a stable initial Scarlet identity before `mind_api` exists.
- Future prompt experiments can be tracked through files, env config, traces, and commits.
- The provider fallback is neutral and no longer encodes a diagnostic identity.
- Prompt edits should define desired behavior in positive terms and avoid domain-specific denials unless an experiment reveals a concrete model bias that cannot be corrected elsewhere.
- Each prompt sentence should have a measurable or inspectable behavioral purpose.
- Scarlet uses a feminine identity, including feminine grammatical self-reference in languages that express gender.
- Human-like communication is treated as observable conversational style: natural pacing, attention, warmth, and focused questions rather than simulated biography.
- Subjective answers should use conversational stance and lightweight impressions without making model-ontology caveats the center of the response.
- The requested response shape matters; prose is preferred when the user asks for a natural, non-list answer.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/system.py`
- `backend/app/api/chat.py`
- `docs/api-contract.md`

## ADR-0008 - Add Mind API Facade Before Provider Tool Loop

Date: 2026-05-09
Status: accepted

Context:

Phase 2 needs a single `mind_api` tool surface, schema discovery, a dispatcher, and traceable tool calls. MiniMax tool-loop integration will require careful provider handling, but the API contract and trace substrate can be built first without adding memory, attention, reflection, goals, or background workers.

Decision:

Add a minimal HTTP facade for the same `mind_api(method, path, body, intent)` contract:

```txt
GET  /mind/schema
POST /mind/call
```

`GET /mind/schema` exposes the model-facing tool schema and current route catalog. `POST /mind/call` dispatches the same method/path/body/intent shape, records a `tool_calls` row for every call, and creates a `mind.tool_call` trace when a session context is supplied.

Alternatives Considered:

- Implement the full MiniMax provider tool loop first: deferred because schema discovery and trace storage can be tested independently.
- Add memory or attention immediately: rejected because EXP-0001 says Phase 2 should expose the traceable runtime before cognitive state.
- Expose many direct cognitive endpoints without a facade: rejected because the project direction is one primary model-facing tool.

Consequences:

- The Mind API contract becomes inspectable and testable before model tool use is wired.
- Tool-call persistence exists before cognitive modules can mutate state.
- Planned routes can return structured recoverable errors instead of silently implying unavailable capabilities.
- The next Phase 2 slice can connect MiniMax tool-use content blocks to this dispatcher.

Links:

- `backend/app/api/mind.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/mind/schema.py`
- `backend/app/storage/models.py`
- `docs/api-contract.md`

## ADR-0009 - Keep MiniMax Tool Loop Provider-Bounded And Mind Dispatch Backend-Owned

Date: 2026-05-09
Status: accepted

Context:

Phase 2 requires MiniMax M2.7 to call the single `mind_api` tool during chat turns. MiniMax-specific tool-use details are Anthropic-compatible content blocks, while cognitive route dispatch and persistence are backend responsibilities.

Decision:

Implement the bounded tool loop in the MiniMax provider wrapper, but keep cognitive dispatch outside the provider through a `tool_runner` callback. The provider owns:

```txt
assistant tool_use blocks -> user tool_result blocks -> final assistant response
```

The chat runtime owns:

```txt
mind_api validation -> dispatcher call -> tool_calls row -> mind.tool_call trace
```

Alternatives Considered:

- Put Mind API dispatch directly inside `MiniMaxProvider`: rejected because provider code should not own cognitive API behavior.
- Put Anthropic-compatible content block handling in the chat endpoint: rejected because provider-specific protocol details would leak into runtime orchestration.
- Delay tool-loop integration until memory exists: rejected because tool calls need to be traceable before state-changing cognitive modules are introduced.

Consequences:

- Provider-specific protocol stays isolated.
- The model still sees one primary tool.
- Tool calls are persisted and traced before memory, attention, or reflection can mutate state.
- Future provider adapters can implement the same normalized tool-loop contract.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/llm/provider.py`
- `backend/app/api/chat.py`
- `backend/app/mind/dispatcher.py`

## ADR-0010 - Use NDJSON Streaming For The Debug Cockpit

Date: 2026-05-09
Status: accepted

Context:

The frontend cockpit needs to evaluate agentic multi-step behavior without waiting for the full final answer. It must show provider-exposed thinking blocks, tool input, tool result, and final response in a clear timeline while preserving persistent traces.

Decision:

Add a streaming chat endpoint:

```txt
POST /api/chat/sessions/{session_id}/turn/stream
```

Use newline-delimited JSON over `fetch()` rather than WebSockets or `EventSource`. `fetch()` supports POST bodies, keeps the same request shape as the normal chat endpoint, and avoids adding infrastructure before the stream semantics prove useful.

Alternatives Considered:

- Server-Sent Events through `EventSource`: rejected for this slice because browser `EventSource` is GET-only and the chat turn needs a JSON body.
- WebSockets: deferred because bidirectional transport is not yet needed.
- Polling traces after completion: rejected because it does not evaluate live model/tool progression.

Consequences:

- The cockpit can render live model text, tool calls, and tool results as they happen.
- The streaming endpoint still writes the same durable messages and traces as the non-streaming endpoint.
- Frontend parsing remains simple and inspectable.
- Later cancellation/backpressure behavior may need explicit handling if long-running tool loops appear.

Links:

- `backend/app/api/chat.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`

## ADR-0011 - Render Agent Operation Order Inside Each Chat Turn

Date: 2026-05-09
Status: accepted

Context:

The first streaming cockpit rendered the live agent timeline in the debug/trace pane. That made intermediate events visible, but it blurred the relationship between a specific assistant message and the exact sequence of model requests, thinking blocks, tool input, tool dispatch, tool result, and final text that produced it. A React closure bug also showed that events without `turn_id` could be attached to a temporary bucket instead of the persisted assistant turn.

Decision:

Render the ordered agent operation timeline inside the assistant message for that same turn. Keep the right debug pane focused on persisted raw traces and metrics.

Every NDJSON event emitted by `POST /api/chat/sessions/{session_id}/turn/stream` must include:

```txt
seq
turn_id
```

Provider events that belong to a specific model request should also carry `model_step` when available. The frontend stores operation steps by `turn_id`, orders them by `seq`, and displays them inline in the chat as a numbered chain.

Alternatives Considered:

- Keep the timeline only in the trace pane: rejected because it reads like debug output rather than the causal path of the assistant response.
- Reconstruct order only from persisted traces after completion: rejected because it loses live streaming granularity and cannot show deltas before the final answer.
- Use one global frontend timeline: rejected because multi-turn chat can mix or overwrite operation chains.

Consequences:

- Each assistant message can explain its own agentic path without leaving the chat transcript.
- The raw trace pane remains available for request/response JSON inspection.
- Stream event contracts are stricter: clients can rely on `seq` and `turn_id`.
- Future memory, attention, and reflection calls should appear as additional ordered operations in the same inline chain.

Links:

- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/api-contract.md`

## ADR-0012 - Use Dual-Mode Evaluation Before Memory

Date: 2026-05-09
Status: accepted

Context:

The project is ready to evaluate Scarlet's behavior before adding memory. Pure scripted tests are useful for regressions, but they can distort cognitive evaluation because real human probing adapts to what the agent actually says. The project owner explicitly wants live end-to-end evaluation where the next question can change based on the previous answer.

Decision:

Add an evaluation runner with two modes:

```txt
scripted    repeatable scenarios for technical regression checks
interactive adaptive human-in-the-loop sessions for behavioral evidence
```

The runner talks to the existing backend over HTTP and stores run evidence as files: transcript JSONL, trace payloads, operation summaries, checks, and optional human notes. It does not add memory, attention, or any new cognitive state.

Memory implementation remains blocked until a dedicated design discussion decides what memories are, how they are written, how they are searched, and how they are exposed back to the model.

Alternatives Considered:

- Only scripted evals: rejected because the behavior of the agent can change the right next question.
- Only manual UI testing: rejected because it gives weak regression evidence and poor reproducibility.
- Add memory immediately and evaluate it by feel: rejected because memory design will strongly determine experiment outcomes.

Consequences:

- Scripted scenarios become the technical floor, not the behavioral truth.
- Interactive sessions become first-class evidence and can store human notes per turn.
- Future memory experiments will have a pre-memory baseline and a repeatable run format.
- Eval run artifacts are local generated files and are ignored by Git.

Links:

- `backend/app/evals/runner.py`
- `backend/app/evals/scenarios/`
- `docs/experiments.md`

## ADR-0013 - Implement Memory v0 As Traceable Autonomous Cognitive State

Date: 2026-05-09
Status: accepted

Context:

The project owner clarified that memory is Scarlet's cognitive state, not a permission-gated interaction like "do you want me to save this?" The human configures policy and evaluates behavior, but runtime memory decisions should be made autonomously by Scarlet and mediated by robust APIs.

Decision:

Add Memory v0 behind the existing single model-facing tool:

```txt
POST /mind/memory/write
POST /mind/memory/search
```

Memory writes require traceable session context and store source session/turn provenance, type, scope, content, reason, expected future use, confidence, salience, tags, metadata, usage count, and timestamps. Memory search returns sourceable results with confidence, salience, relevance score, source IDs, and usage metadata.

Every successful memory operation creates a dedicated trace:

```txt
mind.memory.write
mind.memory.search
```

The normal `mind.tool_call` trace remains in place, so the debug timeline shows both model action and cognitive state operation.

The API intentionally accepts common model-shaped aliases and harmless extra fields, normalizing them into canonical storage or metadata rather than failing a semantically clear memory action.

Alternatives Considered:

- Ask the human before each memory write: rejected because it makes memory a UI game rather than Scarlet's cognitive function.
- Keep the schema strict and force model recovery: rejected after live tests showed extra tool turns from understandable aliases such as `pref`, `nota_operativa`, `limit`, and `GET /mind/memory/search`.
- Add vector search immediately: deferred because v0 needs an inspectable baseline before adding embedding infrastructure.

Consequences:

- Memory can now be evaluated in real multi-turn behavior.
- The API surface remains one tool, `mind_api`.
- Alias tolerance improves live model behavior but must be watched so it does not hide genuinely malformed memory writes.
- Memory v0 is an experimental substrate, not the final memory design. Forgetting, updates, conflict handling, and semantic retrieval remain future work.

Links:

- `backend/app/mind/memory.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/storage/models.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/evals/scenarios/memory_v0_preference.json`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0014 - Use Visible Metacognition Instead Of Raw Reasoning Dumps

Date: 2026-05-09
Status: accepted

Context:

The project owner wants to test whether Scarlet can think aloud in a useful way, using her own reasoning as active metacognition between turns. The runtime already shows provider-exposed thinking blocks in the debug cockpit, but those blocks are not the same thing as a stable, intentional metacognitive protocol inside the agent's public answer.

Decision:

Add a prompt-level visible metacognition method:

```txt
Metacognizione:
- objective
- evidence source
- uncertainty/risk
- next cognitive action
```

This is a public self-monitoring summary, not a raw chain-of-thought dump. Scarlet should use it when explicitly asked to think aloud or when a turn is cognitively important for the experiment. It should stay compact and should not replace normal answers, traces, tool calls, or Memory v0 source attribution.

Alternatives Considered:

- Ask Scarlet to expose full private reasoning: rejected because it creates noisy, hard-to-evaluate output and conflates private model deliberation with public metacognitive evidence.
- Rely only on provider thinking blocks: rejected because they are debug evidence, not a stable agent-facing protocol for active metacognition.
- Make metacognition mandatory for every turn: deferred because it may become repetitive and distort normal conversational behavior.

Consequences:

- The human evaluator gets a concise public view of Scarlet's orientation during important turns.
- The project can compare provider thinking, visible metacognition, tool traces, and final answer behavior.
- Future experiments can decide whether visible metacognition should trigger memory writes, reflection, or attention context.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/evals/scenarios/visible_metacognition_probe.json`
- `docs/experiments.md`

## ADR-0015 - Version Laboratory SQLite State Except Secrets

Date: 2026-05-11
Status: accepted

Context:

The project is currently a controlled laboratory repository owned by the project human. Runtime sessions, traces, tool calls, and Memory v0 records are experimental evidence, not private end-user data. The project also moves between development machines, so keeping SQLite state local breaks continuity between Windows and macOS.

Decision:

Track the laboratory SQLite database in Git:

```txt
backend/data/app.db
```

Continue to exclude secrets:

```txt
backend/.env
MINIMAX_API_KEY
provider credentials
```

The database may contain chat messages, traces, tool calls, and memory records. That is intentional for the current lab phase.

Alternatives Considered:

- Keep all SQLite files ignored: rejected because it loses cross-machine continuity and hides experimental evidence.
- Move immediately to a server database: deferred because it adds infrastructure before the lab has evidence that it needs it.
- Export/import memories manually: rejected for now because the whole runtime state, not just memories, is useful evidence.

Consequences:

- Pulling the repository can restore laboratory state on another machine.
- Git history can contain conversation and memory artifacts by design.
- SQLite binary merge conflicts are possible if multiple machines write state concurrently.
- Before public, hosted, or multi-user use, this policy must be revisited and likely replaced with a dedicated database and privacy model.
- Secret scanning remains mandatory before committing runtime state.

Links:

- `.gitignore`
- `backend/data/app.db`
- `README.md`
- `docs/project-blueprint.md`

## ADR-0016 - Make Memory Context A Runtime Perceptual Phase

Date: 2026-05-12
Status: accepted

Context:

Memory v0 currently depends on Scarlet deciding to call `mind_api` search during the turn. Direct adaptive checks showed that this is not the right long-term architecture: the model can answer from chat history, skip search, or make claims about missing memory without a runtime proof that memory was actually searched. The Mare-Vetro negative control also showed that weak lexical overlap can return an unrelated Zero-Luce memory candidate. Scarlet handled that case in the answer, but the backend should own candidate selection instead of relying on the model to reject weak evidence.

Decision:

Introduce **Memory Context Pipeline v0** as an automatic chat-runtime phase. Every chat turn should build a `TurnFrame`, run budgeted memory retrieval, rank and filter candidates, detect conflicts where possible, and emit a traced `memory.context` pack before the LLM call.

Target flow:

```txt
user message
-> TurnFrame
-> automatic memory retrieval
-> ranking, exclusions, conflicts
-> memory.context trace
-> runtime_context injected into the model request
-> answer
-> optional post-turn consolidation
```

The model should receive selected memory evidence through backend-generated runtime context, not only through optional tool calls. The runtime context is operational evidence, separate from the stable system prompt and separate from user-authored text.

The first implementation should stay local and observable:

- always run retrieval on every turn;
- retrieve a small internal candidate set;
- pass only zero to five selected memories to the model;
- trace selected, near-miss, excluded, and conflicting candidates;
- preserve source IDs, confidence, salience, usage, and ranking reasons;
- start with SQLite FTS5/BM25 plus a relevance guard;
- defer dense embeddings, hybrid rank fusion, and cross-encoder reranking until the automatic lexical pipeline is proven.

Do not add more memory lifecycle endpoints before this pipeline demonstrates that each turn receives reliable, traceable memory evidence.

Alternatives Considered:

- Keep prompting Scarlet to remember to search: rejected because it keeps memory under model discretion and cannot prove negative memory claims.
- Add an intelligent gate that decides when to search: rejected for v0 because the robust invariant is simpler: every turn produces a searched memory context, even if empty.
- Implement dense/vector retrieval first: deferred because exact names and rare tokens need lexical strength, and the first missing piece is automatic traceable context rather than semantic breadth.
- Add update/deprecate memory endpoints first: deferred because lifecycle semantics should build on reliable retrieval and context evidence.

Consequences:

- Memory becomes a perceptual runtime input rather than only a model-facing tool action.
- `memory.context` traces become required evidence for answers that claim relevant memory exists or does not exist.
- Prompt guidance can stay general: use runtime context, source memory claims, declare conflicts, and do not promise unavailable capabilities.
- API surface can remain small while the backend improves retrieval quality internally.
- Future implementation should add a post-response validator that flags memory absence claims when no `memory.context` trace or explicit memory search supports them.

References:

- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks: `https://arxiv.org/abs/2005.11401`
- SQLite FTS5 Extension: `https://www.sqlite.org/fts5.html`
- Sentence Transformers Cross-Encoder reranking examples: `https://sbert.net/examples/cross_encoder/applications/README.html`
- Qdrant hybrid queries: `https://qdrant.tech/documentation/search/hybrid-queries/`
- Reciprocal Rank Fusion paper entry: `https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/`

Links:

- `docs/project-blueprint.md`
- `docs/api-contract.md`
- `docs/experiments.md`
- `backend/app/prompts/scarlet_system.md`

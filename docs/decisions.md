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

Use `MINIMAX_MAX_TOKENS=131072` as the backend default output budget for
MiniMax calls, matching MiniMax M2.7's documented maximum completion budget.
Individual requests may override it, but defaults should not be artificially
low.

Alternatives Considered:

- Keep the smoke default at `128`: worked for a tiny diagnostic, but encoded the wrong project priority.
- Keep very low token defaults for cost control: rejected because the Token Plan is request-based for M2.7 and this project optimizes for quality and observability.
- Set extremely large defaults immediately: originally deferred until we had
  persistent traces and real chat workloads; accepted on 2026-05-23 after
  provider-native history tracing made context growth inspectable.

Consequences:

- M2.7 has the full documented completion budget available for reasoning,
  tool-heavy turns, and final text in normal debug calls.
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

## ADR-0009 - Keep MiniMax Tool Loop Provider-Owned And Mind Dispatch Backend-Owned

Date: 2026-05-09
Status: accepted

Context:

Phase 2 requires MiniMax M2.7 to call the single `mind_api` tool during chat turns. MiniMax-specific tool-use details are Anthropic-compatible content blocks, while cognitive route dispatch and persistence are backend responsibilities.

Decision:

Implement the tool loop in the MiniMax provider wrapper, but keep cognitive dispatch outside the provider through a `tool_runner` callback. The provider owns:

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

Update 2026-05-20:

The project owner clarified that API Mind is Scarlet's internal cognition, not
a normal optional user-facing tool, and that Scarlet must decide how many
internal operations are needed before answering. The runtime therefore no
longer imposes an artificial `max_tool_calls=4` cap during chat turns. The tool
loop is model-controlled and continues until Scarlet answers rather than emits
another tool call. Provider, network, and process failures can still stop a
turn, but the backend no longer encodes a fixed cognitive step budget.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/llm/provider.py`
- `backend/app/api/chat.py`
- `backend/app/mind/dispatcher.py`

## ADR-0019 - Treat API Mind As Scarlet's Internal Cognition

Date: 2026-05-20
Status: accepted

Context:

The owner clarified that future users will not know, operate, or choose API
Mind routes. API Mind is for Scarlet's own cognition: memory, facts, schema
awareness, traceable state inspection, and future cognitive modules. If Scarlet
waits for the user to request API usage, production behavior will be fragile
because the user will speak only in natural language.

Decision:

Scarlet's prompt and runtime contract now frame `mind_api` as an internal
cognitive interface, not as a normal user-facing tool.

Scarlet should autonomously decide when to use API Mind before answering,
including schema inspection, memory search, fact lookup, conflict inspection,
and traceable state mutation. The user should not need to know endpoints or
tell Scarlet how to use her cognitive environment.

The runtime uses a model-controlled, unbounded tool-loop policy for chat turns:

```txt
tool_loop_policy = model_controlled_unbounded
```

Consequences:

- Prompt language must teach cognitive posture, not only endpoint mechanics.
- Normal answers should expose results and source discipline, not ask users to
  operate API Mind.
- Evaluation should include prompts where the user does not mention API Mind,
  while Scarlet still uses it when needed.
- Long internal loops remain traceable through `mind.tool_call`, operation
  traces, streaming events, and `llm.response.raw_provider_messages`.
- Future engineering work may add cancellation, progress policy, or batch
  internal operations without reintroducing a fixed cognitive step cap.

Update 2026-05-22:

After a live autonomy probe showed Scarlet did not always follow
`source_session_id` on the first verified-baseline question, the prompt was
strengthened around epistemic curiosity and provenance thresholds. API Mind
remains internal cognition, but Scarlet is now instructed to classify evidence
as verified, remembered, inferred, provisional, or unknown, and to treat
memory-derived strong recommendations or baseline claims as requiring source
session inspection when provenance is available.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `docs/api-contract.md`

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
Status: superseded

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

Superseded 2026-05-22:

The standalone `Visible Metacognition Experiment` prompt section was removed.
Public visibility is now handled through public work notes, while operative
metacognition is handled through the traceable LLM-backed
`POST /mind/metacognition/step` route. This avoids teaching Scarlet that a
visible `Metacognizione:` label is equivalent to internal metacognitive work.

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

Update 2026-05-20:

The automatic pipeline has since been implemented and live-tested. Minimal
lifecycle endpoints were therefore added in M2 and verified through direct
Scarlet conversation.

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

## ADR-0017 - Evolve Memory Toward API-First Atomic Facts And Lifecycle

Date: 2026-05-20
Status: accepted

Context:

Memory v0 and Memory Context Pipeline v0 made memory traceable and automatic,
but live terminal probes showed that robust memory needs more than write/search
and prompt guidance:

- active conflicting memories can remain unresolved indefinitely;
- lexical retrieval can select wrong-entity memories when generic terms and
  recent dialogue overlap;
- runtime context can detect conflicts that final answers may still hide under
  user formatting instructions;
- Scarlet can suggest writing another memory as a workaround when lifecycle
  operations are missing;
- self-classification by the model is useful commentary, not reliable validation.

The project owner also asked to compare the current design with
`jrcruciani/obsidian-memory-for-ai`, whose v3 pattern emphasizes atomic facts,
controlled predicates, bi-temporal fields, linting, generated views, operation
envelopes, inbox/compaction, and reflect-after-session maintenance.

Decision:

Keep LLM API Mind API/CLI-first. Do not adopt a Markdown vault as the primary
memory source of truth. Instead, adapt the useful ideas into backend contracts,
tables, CLI tools, traces, and debug views.

The accepted memory roadmap is:

```txt
1. Minimal lifecycle APIs: memory.deprecate, memory.supersede, memory.conflicts.
2. Atomic fact layer with entity, predicate, temporal validity, and provenance.
3. Entity-aware retrieval guard, then SQLite FTS5/BM25.
4. Proposal inbox, compaction, CLI/debug memory views, and broader memory evals.
5. Re-test response-control guardrails after lifecycle/retrieval evidence is stronger.
```

The future durable memory unit should move toward:

```txt
entity + predicate + value + temporal validity + recorded_at + provenance
```

The existing `memories` table can remain as the human-readable/sourceable record
layer while a stricter `memory_facts` layer is added underneath or alongside it.

Alternatives Considered:

- Keep Memory v0 as narrative records plus better prompting: rejected because it
  cannot resolve lifecycle, wrong-entity retrieval, or answer-control gaps.
- Add vector search immediately: deferred because retrieval quality cannot fix
  ambiguous lifecycle and fact modeling.
- Use an Obsidian/Markdown vault as the project memory backend: rejected because
  the research hypothesis is a stable model-facing API and inspectable runtime,
  not direct file editing by the model.
- Implement lifecycle first without response-control: partially useful, but
  answer honesty still needs backend obligations when conflicts or unavailable
  capabilities are already known.

Consequences:

- `docs/memory-roadmap.md` becomes the detailed implementation plan for robust
  memory.
- Prompt changes should not be treated as sufficient memory fixes.
- New memory endpoints should preserve the single `mind_api` surface.
- Memory lifecycle operations must be traceable and reversible or inspectable.
- CLI/debug tooling becomes part of memory robustness, not a later luxury.

Update 2026-05-20:

The owner explicitly put the original response-control-first slice on hold,
framing the observed answer-control issue as possibly downstream of missing
memory conflict management rather than a standalone bug. The project therefore
implemented M2 first. `GET /mind/memory/{memory_id}`,
`GET /mind/memory/conflicts`, `POST /mind/memory/deprecate`, and
`POST /mind/memory/supersede` are now implemented through `mind_api` and were
live-verified in interactive run
`backend/app/evals/runs/20260520_152457_interactive`.

References:

- `https://github.com/jrcruciani/obsidian-memory-for-ai`
- `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/SPEC-v3.md`
- `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/automation-guide.md`

Links:

- `docs/memory-roadmap.md`
- `docs/project-blueprint.md`

## ADR-0018 - Add Memory Facts As Canonical Layer Under Narrative Memory

Date: 2026-05-20
Status: accepted

Context:

The owner asked how natural language variants should be handled robustly:
synonyms, different languages, different words for the same concept, and
phrases that mean the same durable memory fact. Memory v0 stored sourceable
narrative records and could resolve the concrete Zero-Luce conflict through M2
lifecycle operations, but narrative search alone is too brittle for robust
memory.

The M3 live verification also showed why the canonical layer must preserve
lifecycle state. Backfilling facts after a memory supersession created the
right Zero-Luce facts, but initially lacked fact-level supersession links until
the backfill flow was hardened.

Decision:

Keep `memories` as the sourceable narrative/provenance layer and add
`memory_facts` as the stricter canonical layer.

Each fact stores:

```txt
memory_id
entity
predicate
value_json
valid_from / valid_to
recorded_at
source trace/session/turn ids
confidence
salience
status
supersedes_fact_id / superseded_by_fact_id
metadata_json
```

The first extractor is deterministic and narrow. It canonicalizes observed
entity aliases such as `Zero Light protocol` and `protocollo Zero-Luce` to
`protocollo-zero-luce`, maps predicate aliases such as `formato-risposta` to
`response_format`, and extracts ordered response-format blocks when block labels
are recognizable.

Fact inspection and backfill are exposed only through the existing single
`mind_api` surface:

```txt
GET  /mind/memory/facts
POST /mind/memory/facts/backfill
```

Consequences:

- Synonym and multilingual handling starts with canonical entity/predicate
  aliases instead of free-form memory text.
- Conflict detection can use active facts with the same `entity + predicate`
  and different values before falling back to tag/token overlap.
- Memory lifecycle operations must propagate to facts, and backfill must rebuild
  fact-level links from memory lifecycle metadata.
- This does not replace retrieval improvements. M4 should use facts to build an
  entity-aware guard and then add SQLite FTS5/BM25.
- This does not yet solve open-ended semantic equivalence; proposals,
  compaction, and possibly embeddings remain later phases.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 31 tests.
- Live run `backend/app/evals/runs/20260520_160345_interactive` verified
  backfill and alias fact query through direct Scarlet conversation.
- Direct traced backfill sync `trace_511b5bcdf0f3441bb3088d5a43e52ea4`
  rebuilt fact-level supersession links in the laboratory database.

Links:

- `backend/app/mind/facts.py`
- `backend/app/mind/memory.py`
- `backend/app/storage/models.py`
- `docs/memory-roadmap.md`
- `docs/experiments.md`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0020 - Use One LLM-Backed Metacognition Route Beyond Memory

Date: 2026-05-22
Status: accepted

Context:

The owner temporarily shifted focus from memory to Scarlet's cognitive and
metacognitive abilities. The visible metacognition prompt experiment proved
Scarlet can expose a compact public self-monitoring note, but that note was not
an operative cognitive mechanism. Scarlet also showed API-shape mistakes during
live probes, meaning the system needs stronger schema discipline and internal
validation, not just more prompt text. The owner then rejected expanding API
Mind with many overlapping cognitive endpoints, because that would confuse both
the architecture and Scarlet's tool-use policy.

Decision:

Keep the single model-facing `mind_api` surface and expose exactly one
metacognition route:

```txt
POST /mind/metacognition/step
```

This route is LLM-backed. Scarlet passes a private internal prompt, objective,
evidence, uncertainty, and optional draft answer to a metacognitive reviewer.
The returned structured review contains critique, claim checks, missing
evidence, recommended existing API Mind actions, continuation signal, and a
compact public summary.

`GET /mind/schema` remains versioned with `schema_version`, `schema_digest`,
route examples, and a compact schema reference in runtime context. Exact route
body schemas live in `/mind/schema`, not in the prompt.

Consequences:

- Internal metacognition becomes structured and traceable rather than purely
  visible prose.
- Claim validation, workspace notes, reflection, and next-action planning are
  result fields inside the one metacognitive step, not separate endpoints.
- Scarlet has fewer route choices, reducing API-shape confusion.
- Future work must measure whether this one route improves behavior before any
  additional cognitive route is considered.

Alternatives Considered:

- Put all route schemas into the system prompt: rejected because it duplicates
  `/mind/schema`, bloats the prompt, and risks schema drift.
- Add many separate model-facing tools: rejected because the core project
  hypothesis is a stable single cognitive API surface.
- Add separate cognitive routes for validation, blackboard, and reflection:
  rejected after review because they create overlapping functionality and
  operational confusion.

Links:

- `docs/cognitive-api-roadmap.md`
- `docs/api-contract.md`
- `backend/app/mind/metacognition.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`

## ADR-0021 - Separate Semantic Memory From Episodic Session Recall

Date: 2026-05-22
Status: accepted

Context:

The owner clarified that Scarlet needs two different forms of memory. Durable
facts, decisions, corrections, and preferences should remain semantic memory.
Past conversations should not be blindly copied into semantic memory, but
Scarlet must be able to reconstruct them when a memory's provenance or a prior
session matters.

Decision:

Keep `memories` and `memory_facts` as the semantic memory layer. Add a
separate episodic recall layer:

```txt
session_summaries
GET  /mind/sessions
GET  /mind/sessions/{session_id}
POST /mind/sessions/{session_id}/summarize
```

`session_summaries` stores a compact descriptive index for sessions: summary,
topics, decisions, open questions, memory ids written from the session, message
count, and last message id. The exact transcript remains in `messages` and is
returned by session read. A semantic memory's existing `source_session_id`
becomes the bridge from reusable memory back to the source conversation.

Update 2026-05-22:

Summarization must use the complete `user`/`assistant` conversation history for
the target session. `max_messages`/last-N summarization is rejected because it
can mark a partial tail summary as fresh for the entire session. Tool calls,
traces, and provider thinking remain excluded from the episodic summary input.

Consequences:

- Scarlet can navigate prior sessions without storing full conversations as
  semantic memories.
- Session summaries are weak navigation evidence; the full transcript is
  stronger when exact wording or provenance matters.
- Summary freshness is based on the complete user/assistant message count and
  last user/assistant message id.
- The model-facing API remains the single `mind_api` surface.
- Future compaction can improve summaries without changing semantic memory
  contracts.

Alternatives Considered:

- Store whole conversations as `episodic` memory records: rejected because it
  would pollute semantic retrieval and blur reusable meaning with raw history.
- Add a separate user-facing history API for Scarlet to ask the user to use:
  rejected because API Mind is Scarlet's internal cognition, not a user-operated
  interface.

Links:

- `backend/app/mind/episodic.py`
- `backend/app/storage/models.py`
- `docs/api-contract.md`
- `docs/memory-roadmap.md`

## ADR-0022 - Public Work Notes For Agentic Progress Narration

Date: 2026-05-22
Status: accepted

Context:

The owner wants Scarlet's user experience to feel more like Codex, GitHub
Copilot Agent, or Claude Code: the agent should naturally narrate what it is
doing during complex work, not remain silent until the final answer. A live
MiniMax probe showed the model can emit public text before a `mind_api` tool
call in the same streamed turn.

Decision:

Scarlet's prompt now requires public work notes for non-trivial internal
activity. These notes are public operational summaries: they may explain what
Scarlet is checking, why it matters, what evidence source is being inspected,
or why the plan changed. They are not raw private chain-of-thought.

The prompt-only slice does not add a new API route. It uses the existing
streaming/tool-loop behavior and keeps the single model-facing `mind_api`
surface.

Consequences:

- Scarlet should expose more natural agentic progress during memory searches,
  source-session reads, schema checks, metacognitive reviews, retries, and
  verification phases.
- Work notes help the human follow activity without reading raw traces.
- Work notes can become useful markers for future episodic reconstruction, but
  the current backend still persists only the final assistant message as normal
  conversation content.
- A later backend slice should decide whether to persist streamed pre-tool text
  as `assistant_progress` traces/events and whether session summaries should
  include those progress markers.

Update 2026-05-22:

Autonomous prompt-only probes showed the policy is not sufficient by itself.
Even with explicit prompt language requiring a public note and `GET
/mind/schema` for current capability questions, Scarlet answered from runtime
context without a tool call. The public-work-note policy remains accepted, but
the implementation likely needs runtime support to classify, persist, and maybe
trigger `assistant_progress` events reliably.

Alternatives Considered:

- Deterministic loading labels only: rejected as too shallow for the requested
  Codex-like agentic narration.
- Persist progress notes as normal assistant messages: deferred because it
  could pollute chat history, semantic memory, and summaries.
- Expose raw provider thinking blocks: rejected because public work notes should
  be concise operational narration, not raw private reasoning.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md#exp-0013---public-progress-notes-before-tool-use`

## ADR-0023 - Prompt Defines Scarlet's Perception Sources

Date: 2026-05-22
Status: accepted

Context:

Live temporal and episodic recall probes showed that Scarlet can receive real
runtime evidence but still treat conversational fluency or a partial session
page as enough for strong claims. The owner clarified that the system prompt
should not make Scarlet passive. It should teach where real data comes from,
which source wins during conflicts, and how API Mind functions as Scarlet's
own cognition/subconscious rather than a user-facing tool.

Decision:

Scarlet's prompt now includes a perception/source-of-truth layer:

- API Mind is described as Scarlet's operative subconscious and durable
  cognition, not merely a tool.
- Runtime context, temporal context, memory context, schema metadata, tool
  results, transcripts, and memories are explicit perception channels.
- `runtime_context.temporal_context` is the only valid operational clock for
  current real-world time.
- User statements that conflict with runtime evidence are treated as user
  claims, not measured reality.
- Session lists are paginated indexes; `has_more=true` prevents strong
  exhaustive claims unless the model paginates, filters, or otherwise obtains
  exhaustive evidence.
- Public work notes remain the visible narration layer; internal metacognition
  remains the `/mind/metacognition/step` route.

Consequences:

- The prompt keeps existing identity, memory, schema, and API discipline
  rather than rewriting the whole system prompt.
- The model should be more likely to use the freshest runtime time instead of
  earlier conversational timestamps.
- Prompt-only guidance may still be insufficient for session aggregation; API
  support such as temporal filters or explicit `is_exhaustive` may still be
  needed.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/bug-ledger.md#bug-0019---runtime-time-was-not-model-facing`
- `docs/bug-ledger.md#bug-0020---session-list-first-page-can-be-treated-as-exhaustive`

## ADR-0024 - Switchable Anthropic-Compatible LLM Providers

Date: 2026-05-22
Status: accepted

Context:

The owner wants to compare MiniMax M2.7 against Qwen 3.7 without changing
Scarlet's prompt, API Mind behavior, memory system, traces, or UI. The goal is
to isolate whether observed limits come from the model backbone or from the
agent runtime.

Decision:

Introduce a small provider selector:

```txt
LLM_PROVIDER=minimax|qwen
```

MiniMax remains the default baseline. Qwen is configured as an alternate
Anthropic-compatible provider through Alibaba Model Studio:

```txt
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/apps/anthropic
QWEN_MODEL=qwen3.7-max
```

The chat routes, debug route, Mind API routes, episodic summarization, and
metacognition use provider-agnostic helpers for active model and token budget.
No user-facing API endpoint changes are required beyond `/health` exposing the
active provider.

Consequences:

- A/B tests can switch models with environment variables only.
- Existing tests and traces keep MiniMax as the baseline.
- Provider-specific credentials remain in `.env` and must never be committed.
- If Alibaba exposes a different deployment/model identifier for Qwen 3.7 in
  the console, `QWEN_MODEL` can be changed without code changes.

Links:

- `backend/app/llm/factory.py`
- `backend/app/llm/minimax_client.py`
- `backend/app/llm/qwen_client.py`
- `backend/.env.example`

## ADR-0025 - Engineering Agent Quality Gate In Scarlet Prompt

Date: 2026-05-23
Status: accepted

Context:

Qwen 3.7 showed stronger autonomous evidence gathering and self-critique than
recent MiniMax probes, but Qwen has marginal provider cost while MiniMax is
currently cost-free for the owner. Before treating model replacement as
necessary, the project should test whether MiniMax can be improved through
prompt-level operating posture while preserving Scarlet's identity and API Mind
discipline.

Decision:

Add an `Engineering Agent Posture` section to Scarlet's system prompt. The
section frames Scarlet as a careful senior engineer inside her cognitive
runtime and makes source-sensitive work prefer more internal iterations over
fluent but weak answers.

The prompt now explicitly requires a verify-before-conclude pattern and a
quality gate for non-trivial answers:

- identify the strongest evidence actually used;
- classify direct evidence, remembered facts, inference, and unknowns;
- avoid treating paginated lists, summaries, or selected memories as stronger
  than they are;
- check strong words such as "all", "none", "verified", "measured",
  "decided", and "baseline";
- use `/mind/metacognition/step` when the answer is complex, evaluative, or
  source-sensitive.

The change does not add endpoints, does not rewrite Scarlet's identity, and
does not replace backend-side evidence contracts. It is a testable prompt slice
for MiniMax.

Consequences:

- MiniMax should become more likely to inspect schema, emit public notes, do
  multi-step memory/session checks, and downgrade weak evidence.
- Prompt-only improvement is not expected to solve all grounding problems.
- Backend support remains necessary for exhaustive session queries, validator
  behavior, and reliable progress-event persistence.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md#exp-0014---minimax-vs-qwen-37-backbone-comparison`

## ADR-0026 - Pre-Final Semantic Memory Consolidation

Date: 2026-05-23
Status: accepted

Context:

Live Scarlet testing showed that episodic recall works well: Scarlet can use
session times, runtime time, summaries, and transcripts to reconstruct prior
conversations. Semantic memory remained too passive. Even when the owner gave
an explicit milestone, Scarlet recognized it as durable but asked whether to
save it instead of writing memory autonomously.

Decision:

Scarlet's prompt now includes `Semantic Memory Consolidation`: before every
final answer, Scarlet performs a lightweight check over the current user
request and her own draft answer to decide whether a reusable semantic
candidate emerged.

If the candidate is stable and useful for future behavior, interpretation, or
project continuity, Scarlet writes semantic memory before the final answer. She
does not ask permission and does not defer the write to the user.

Strong candidates include:

- user preferences;
- corrections to Scarlet's reasoning or memory policy;
- project decisions and rejected designs;
- milestones, version labels, validation moments, and baselines;
- durable constraints and stable facts about LLM API Mind.

The default user experience is silent. Scarlet mentions the write only when the
user asks about memory, when memory writing is the task, or when acknowledgment
helps emotional continuity, trust calibration, or reinforcement of a durable
operating agreement.

Consequences:

- Semantic memory should behave more like human semantic consolidation: the
  useful reusable meaning is stored, not the whole episode.
- Episodic recall remains the source for exact history.
- Prompt-only consolidation may still need backend support later, such as
  deterministic memory-candidate events or post-turn memory linting.

Update 2026-05-23:

The semantic-memory prompt was strengthened after the owner clarified that
semantic memory should be broader than major decisions or stable preferences.
Scarlet should treat semantic memory as a living internal knowledge base made
of facts, annotations, concepts, checkpoints, labels, corrections, constraints,
and sourceable anchors that may help future sessions.

Memory write/retrieval is now framed as a mental activity of Scarlet's digital
brain, not as a user-managed operation. Scarlet is responsible for maintaining,
updating, resolving conflicts in, and improving her own memory state. Ordinary
memory writes remain silent by default.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/bug-ledger.md#bug-0024---semantic-memory-consolidation-treated-as-opt-in`

## ADR-0027 - Backend-Owned Deterministic API Fields

Date: 2026-05-23
Status: accepted

Context:

The owner clarified that API Mind should be robust by construction: Scarlet
should not be asked to provide fields that the backend can determine from the
live session, turn, message store, clock, provider response, or database state.
This matters especially for semantic memory writes, where model-supplied source
ids can become stale even when the backend has authoritative context.

Decision:

For all Mind API routes, deterministic operational fields are backend-owned.
Scarlet should provide only cognitive content and choices that cannot be
derived automatically.

Backend-owned fields include:

- record ids, trace ids, session ids, turn ids, message ids, and provider ids;
- `created_at`, `updated_at`, `recorded_at`, runtime time, usage counters, and
  latency;
- source provenance for live operations;
- lifecycle timestamps and trace/event provenance;
- message counts, last message ids, session summary coverage, and transcript
  inclusion metadata.

Scarlet-owned fields include:

- memory content, memory type, reason for storage, expected future use,
  confidence, salience, scope, tags, and non-provenance metadata;
- search queries and filters;
- lifecycle reasons and selected target memory ids;
- episodic search/read options such as query, limit, offset, include flags, and
  optional summarization focus;
- metacognitive objective, mode, evidence summary, uncertainty list, draft
  answer, and internal prompt.

Consequences:

- Route schemas should document ownership clearly enough that Scarlet does not
  infer she must manufacture deterministic fields.
- State-changing handlers should ignore or strip backend-owned fields if the
  model sends them in route bodies or free metadata.
- External debug endpoints such as `POST /mind/call` may accept `session_id`
  and `turn_id` as an outer envelope, but the model-facing cognitive route body
  should still treat provenance as backend-owned.

Links:

- `backend/app/mind/schema.py`
- `backend/app/mind/memory.py`
- `docs/bug-ledger.md#bug-0025---model-supplied-memory-provenance-can-be-stale-in-metadata`

## ADR-0028 - Provider-Native Session History

Date: 2026-05-23
Status: accepted

Context:

MiniMax M2.7 is used through the Anthropic-compatible Messages API. The provider
documentation recommends preserving the full assistant response content during
tool-use loops, including native content blocks such as `thinking`, `text`, and
`tool_use`, then returning matching `tool_result` blocks in the next user
message. The previous backend persisted human-readable `user`/`assistant`
messages and traces, but the next model turn was rebuilt from text-only chat
messages. This meant Scarlet kept conversational continuity but lost
provider-native operational continuity across user turns.

Decision:

Store an Anthropic-compatible `provider_history_json` field on each chat
session. This field is the model-facing conversation history for future turns.
It contains provider-native messages with content blocks, not a project-specific
summary format.

The `messages` table remains the human-readable transcript for UI, episodic
recall, and session summarization. The provider history is separate because it
must preserve tool-use/tool-result structure exactly as the provider expects.

When `provider_history_json` is present, chat turns send it plus the current
user message to the provider. When it is missing, the backend reconstructs a
text-only history from persisted `user`/`assistant` messages and then writes
native provider history after the completed turn.

Consequences:

- Scarlet receives MiniMax/Anthropic-compatible multi-turn history instead of a
  lossy text-only reconstruction.
- Tool-use and tool-result evidence can persist across turns without inventing
  a custom context protocol.
- `llm.request` traces now include provider-history source, provider-message
  stats, and exact provider-facing messages so context growth can be inspected.
- Future compaction and maintenance can use the human transcript for semantic
  summaries and the provider history for model-facing continuity.

Links:

- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `backend/app/storage/models.py`
- MiniMax Tool Use & Interleaved Thinking:
  `https://platform.minimax.io/docs/guides/text-m2-function-call`
- Anthropic tool use format:
  `https://docs.anthropic.com/it/docs/agents-and-tools/tool-use/implement-tool-use`

## ADR-0029 - Provider Streaming As Default Execution Path

Date: 2026-05-23
Status: accepted

Context:

Scarlet is intended to behave as an advanced agentic runtime, not as a simple
request/response chatbot. MiniMax M2.7 exposes useful streamed events for
thinking blocks, tool-use starts, partial tool JSON, tool results, and final
text. After raising the MiniMax completion budget to `131072`, the Anthropic
Python SDK also blocks high-token non-streaming calls and requires streaming
for operations that may exceed its non-streaming timeout threshold.

Decision:

Use `messages.stream` as the provider execution path for Anthropic-compatible
providers in all normal generation modes.

Backend endpoints may still expose two external response shapes:

- streaming chat endpoints forward ordered provider/runtime events to the UI;
- non-streaming chat/debug/internal calls collect the provider stream and return
  the final result after the stream completes.

`messages.create` is no longer the primary execution path for Scarlet.

Consequences:

- The provider path is aligned with agentic tool-use, public work notes,
  thinking/tool deltas, long completions, and MiniMax's high completion budget.
- Non-streaming backend endpoints are only a presentation contract; internally
  they still use streaming and collect the final result.
- The runtime avoids SDK non-streaming timeout guards without lowering
  `max_tokens`.
- Future UI and trace improvements can rely on a single provider-event model.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/tests/test_minimax_client.py`
- `docs/bug-ledger.md#bug-0029---anthropic-sdk-blocks-high-non-streaming-minimax-calls`

## ADR-0030 - Runtime Events As The Agent Control Plane

Date: 2026-05-23
Status: accepted

Context:

The project needs agentic behavior similar to IDE coding agents: ordered public
notes, tool activity, evidence blocks, and future background maintenance should
be driven by real runtime facts. Raw traces are excellent forensic evidence, but
they are too heavy and irregular to be the primary runtime substrate. Adding a
new model-facing `/mind/events/emit` endpoint would also broaden API Mind in a
way that risks confusing Scarlet.

Decision:

Introduce a backend-owned `events` table as the ordered runtime control plane.
Events are emitted by the chat runtime, Mind API dispatcher boundary, provider
stream adapter, and response-content recorder. They are not a new Scarlet tool.

Events capture compact facts such as:

- turn lifecycle;
- persisted user/assistant messages;
- automatic memory context construction;
- model request/response milestones;
- Mind API tool-call start/completion/failure;
- provider streamed tool milestones;
- public work notes and final answers;
- private thinking metadata without storing raw private reasoning in the event
  payload.

The streaming frontend receives live `runtime_event` rows while a turn runs,
then renders persisted activity blocks from events first and uses traces as
fallback for older turns. The next turn's runtime context receives compact
recent events so Scarlet can use prior operational facts without scraping deep
trace JSON.

Consequences:

- Runtime events become useful for UI, next-turn cognition, future schedulers,
  and background memory maintenance.
- Traces remain the detailed source of forensic truth.
- API Mind's model-facing surface stays small; no `/mind/events/emit` route is
  introduced for Scarlet.
- Background processes should subscribe to events such as `turn.completed`,
  `memory.context.built`, and `mind.tool_call.completed` before considering
  heavier trace inspection.

Links:

- `backend/app/runtime/events.py`
- `backend/app/storage/models.py`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`

## ADR-0031 - Session Idle Maintenance As The First Background Process

Date: 2026-05-23
Status: accepted

Context:

Scarlet can now write semantic memories autonomously, but live probes still show
occasional missed writes. Adding another model-facing endpoint or a broad
"subconscious" loop would duplicate the existing agentic workflow and make API
Mind harder for Scarlet to reason about. The owner proposed a narrower real-use
trigger: after Scarlet finishes a turn, wait for session inactivity before
running summary and missed-memory checks. If the user continues in the same
session, the older pending work should be cancelled or skipped.

Decision:

Implement backend-owned per-session idle maintenance as the first background
process.

The chat runtime schedules a `session.idle_maintenance` job after
`turn.completed`. The default idle delay is `900` seconds. Newer completed
turns in the same session supersede older pending jobs; jobs from other
sessions are independent.

The first job slice performs two operations:

- refresh the episodic session summary through the existing
  `sessions.summarize` implementation, which already skips up-to-date
  summaries;
- run an LLM-backed missed semantic memory review in report-only mode.

The review writes `maintenance.memory_review` traces and
`maintenance.memory_review.completed` events, but it does not write memories
automatically. This keeps Scarlet's in-turn memory cognition as the primary
writer until live evidence shows whether a proposal inbox or automatic write
path is justified.

Consequences:

- Runtime events now drive an actual runtime process, not only UI and
  next-turn context.
- The backend gains an observable `maintenance_jobs` table with scheduled,
  running, completed, skipped, failed, and superseded states.
- The first slice avoids redundant post-turn prompts on every message and
  avoids interrupting rapid end-to-end user/Scarlet exchanges.
- The next design decision should be based on real
  `maintenance.memory_review` traces: proposal inbox, automatic writes, or
  diagnostic-only review.

Links:

- `backend/app/runtime/maintenance.py`
- `backend/app/storage/models.py`
- `backend/app/api/chat.py`
- `docs/experiments.md#exp-0018---session-idle-maintenance-and-missed-memory-review`

## ADR-0032 - Mind Schema Catalog And Endpoint-Local Error Guides

Date: 2026-05-24
Status: accepted

Context:

Scarlet needs to know which API Mind routes currently exist, but she should not
have to ingest a large Swagger-like manual on every schema inspection. The
owner clarified the distinction: `/mind/schema` should act as a compact
capability catalog, while detailed parameter guidance should appear only when
Scarlet misuses a specific endpoint and needs to recover.

Decision:

Keep a complete backend-internal route registry, but expose two different
model-facing surfaces:

- `GET /mind/schema` returns a lightweight catalog: method, path, status, and
  purpose for each route, plus schema version/digest and the standard response
  shape.
- Recoverable errors from implemented routes include top-level `usage_guide`
  with the failed endpoint's purpose, body schema, path parameters, parameter
  descriptions, accepted aliases when available, examples, and retry guidance.

Consequences:

- Scarlet can inspect current route availability without receiving every route
  body schema up front.
- When a body is wrong, Scarlet receives the local guide for the endpoint she
  just called and can retry directly instead of reflexively calling the global
  schema route.
- The backend, not the prompt, owns exact parameter documentation and keeps it
  synchronized with handlers and tests.
- Unknown or planned routes still return route catalog suggestions rather than
  a detailed guide for a route that does not exist.

Links:

- `backend/app/mind/schema.py`
- `backend/app/mind/dispatcher.py`
- `docs/api-contract.md#get-mindschema`

## ADR-0033 - Temporal Filters And Sparse Retrieval Stay Inside Existing Memory Routes

Date: 2026-05-24
Status: accepted

Context:

The owner approved the next memory advancement plan: improve temporal recall
and sparse retrieval without expanding API Mind with many overlapping
endpoints. Scarlet should still use the same semantic and episodic routes, but
those routes need stronger backend-owned retrieval mechanics so natural
language cues like "ieri", "oggi", prior sessions, and topic drift can be
handled with less model-side arithmetic and less lexical noise.

Decision:

Keep the model-facing surface unchanged and extend existing routes:

- `POST /mind/memory/search` accepts optional `time` filters and uses a
  backend-derived SQLite FTS5/BM25 sparse document for candidate ranking.
- `GET /mind/sessions` accepts optional `time` filters and uses the same sparse
  document approach for title, summary, and conversation text.
- The automatic memory context pipeline also uses the sparse memory index while
  preserving selected/near_miss/excluded trace evidence.
- Temporal ranges are resolved by the backend from runtime time. Scarlet
  supplies intent-level filters such as preset/range/basis; the backend owns
  real clock interpretation.

Consequences:

- Scarlet gets better recall tools without learning new endpoint families.
- Time-sensitive recall becomes inspectable and reproducible in traces.
- Sparse retrieval improves lexical scoring but does not replace future dense
  embeddings, hybrid rank fusion, or entity-aware guards.
- The FTS table is derived state and can be rebuilt from canonical memories,
  facts, sessions, summaries, and messages.

Links:

- `backend/app/mind/time_filters.py`
- `backend/app/mind/search.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/episodic.py`
- `backend/app/mind/context.py`
- `docs/memory-roadmap.md#phase-m4---retrieval-quality-upgrade`

## ADR-0034 - Runtime Context Is A Stratified Block Surface

Date: 2026-05-24
Status: accepted

Context:

The original `memory.context` phase grew beyond memory retrieval. It already
carried temporal context, schema metadata, capability state, recent runtime
events, and selected memories. The owner proposed a clearer distinction:
session-level continuity, message-level perception, and dynamic Scarlet state
should be separate blocks that are useful both to the model and to the UI.

Decision:

Keep `memory.context` as the traceable automatic memory retrieval artifact, but
compose a second `runtime.context` artifact before every model request.

`runtime.context` uses schema `runtime-context-v1` and currently contains:

- `session_context`: current session, recent previous sessions, summaries, and
  active memories sourced from the previous session;
- `message_context`: current user message, temporal/world data, active
  user-scope memory hints, automatic memory retrieval, recent dialogue, recent
  runtime events, schema metadata, and capability state;
- `scarlet_state`: backend-seeded operational focus, posture, goal, mood
  expression, and open loops until dedicated state APIs exist.

The model-facing `<runtime_context>` keeps legacy top-level fields such as
`memory_context`, `temporal_context`, and `capabilities` for compatibility, but
new behavior should treat the block list as canonical because each block
declares type, scope, lifetime, and source.

Consequences:

- Scarlet receives a clearer cognitive frame without adding new model-facing
  endpoint families.
- The cockpit can render context blocks as first-class runtime events instead
  of showing one undifferentiated memory payload.
- Future API Mind routes can update dynamic Scarlet state without changing the
  memory retrieval contract.
- Session summaries remain navigation aids, not proof; exact claims must still
  open source transcripts.

Links:

- `backend/app/mind/context.py`
- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `docs/api-contract.md#implemented-internal-runtime-context`

## ADR-0035 - Runtime Preferences And Tailwind Dashboard

Date: 2026-05-25
Status: accepted

Context:

The runtime context initially exposed both local and UTC current time plus a
simple automatic language hint. Live probes showed Scarlet could read those
fields, but the owner clarified the intended product model: Scarlet should
receive one configured operational clock, defaulting to Italy, and one
configured platform language, defaulting to Italian. These should be dashboard
settings, not model-side guesses.

Decision:

- Add persistent dashboard settings for runtime timezone, platform language,
  configured country/locale, active user profile id, user privacy scope, and
  local user display name.
- Default runtime timezone to `Europe/Rome` and language to `it`.
- Default configured country/locale to `IT` / `Italia`, active profile to
  `local-user`, and privacy scope to `local_single_user`.
- Expose a single configured `temporal_context.now` to Scarlet instead of
  separate `now_local`/`now_utc` fields.
- Expose language through `message_context.current_message.language` as a
  platform setting rather than automatic language detection.
- Expose configured locale through `message_context.world.location` as
  country/timezone-level evidence, not GPS or exact physical presence.
- Expose active profile and privacy boundary through
  `message_context.user_profile.identity` and
  `message_context.user_profile.privacy`.
- Add user-facing dashboard endpoints under `/api/dashboard/*`; keep API Mind
  model-facing routes unchanged.
- Move the frontend styling foundation to Tailwind and organize the cockpit
  around session history, chat, agent stream, memory, profile, and settings
  panels.

Consequences:

- Scarlet has less temporal ambiguity and no longer needs to reconcile two
  clocks for ordinary answers.
- The language weakness found in `EXP-0024` is removed from the current runtime
  path rather than patched with more keyword detection.
- UI settings affect future turns because runtime context is backend-composed
  before each provider request.
- User/profile settings are operational cognitive inputs, not cosmetic labels:
  they define the current profile Scarlet is speaking with and the user-memory
  boundary that future multi-user/privacy work will extend.
- Dashboard APIs are for the human/product surface, not for Scarlet's internal
  `mind_api` cognition.

Links:

- `backend/app/api/dashboard.py`
- `backend/app/runtime/preferences.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`

## ADR-0036 - Agentic Branch Documentation And Versioned Development Protocol

Date: 2026-05-25
Status: accepted

Context:

The project had grown many technical systems: runtime context, memory,
metacognition, events, maintenance, dashboard UI, provider history, tests, and
documentation. The owner clarified that the real planning units should not be
technical internals but branches of Scarlet's operation as an agent:
communication, user flows, perception, identity, memory, learning,
metacognition, goal/task management, decision autonomy, external operativity,
advanced operations, governance/privacy, computational affect, and future
multi-agent subprocesses.

The owner also set a stricter engineering process from V1.0.1 onward:
development must declare scope and version impact before implementation, fix
only directly related problems, run appropriate verification, then set version
and commit.

Decision:

- Treat V1.0.1 as the current app baseline.
- Add `docs/project-documentation.md` as the main documentation index.
- Add `docs/development-process.md` as the versioned implementation protocol.
- Add `docs/branches/` as the canonical map of Scarlet's agentic operating
  branches.
- Keep technical infrastructure docs, but map future changes to the agentic
  branch they improve.
- Require future repository changes to declare:
  - area;
  - branch;
  - type: `Fix`, `Implementazione`, or `Major release`;
  - target version;
  - scope and out-of-scope items;
  - verification;
  - documentation to update.

Consequences:

- Planning becomes more product/cognition oriented and less file/subsystem
  oriented.
- Documentation must be updated vertically by branch when Scarlet's behavior
  changes.
- Opportunistic unrelated fixes are no longer allowed during implementation
  slices.
- Version bumps are explicit and tied to work type.

Links:

- `docs/project-documentation.md`
- `docs/development-process.md`
- `docs/branches/README.md`
- `AGENTS.md`

## ADR-0037 - Memory Proposal Inbox Before Automatic Memory Writes

Date: 2026-05-25
Status: accepted

Context:

Idle maintenance can detect semantic memory candidates that Scarlet missed
during the live turn, but writing those candidates directly would create a
second active memory writer. The owner clarified that the next memory step must
validate candidate quality, duplicate risk, update/deprecation semantics,
temporal lifecycle, and future embedding/knowledge-graph needs before changing
active memory state.

Decision:

Add a `memory_proposals` inbox as the next maintenance layer.

The idle missed-memory review still does not write active semantic memories.
For write-recommended review candidates it now creates idempotent pending
proposals containing:

- source session/turn/trace/job provenance;
- candidate content, evidence, tags, confidence, salience, and future use;
- current proposed action such as `create_new`, `noop_duplicate`,
  `review_similar`, `needs_review`, or `reject_candidate`;
- similar memory ids from the existing sparse/lexical retrieval stack;
- related canonical fact ids and candidate fact payloads when extraction can
  identify entity/predicate/value;
- decision metadata with current retrieval stages and future-ready placeholders
  for embeddings and graph nodes.

Expose `GET /mind/memory/proposals` so Scarlet and evaluators can inspect the
proposal inbox without treating proposals as active memories.

Consequences:

- The system gains an observable bridge between diagnostic review and future
  memory application.
- Active memory remains protected from automatic pollution while review quality
  is evaluated.
- Existing Memory v0 primitives remain the source of truth: write policy,
  sparse retrieval, atomic facts, and lifecycle routes are reused instead of
  duplicated.
- The next decision can focus on proposal application policy: human approval,
  Scarlet-assisted apply, deterministic safe auto-apply thresholds, merge, or
  deprecation workflows.

Links:

- `backend/app/storage/models.py`
- `backend/app/mind/memory.py`
- `backend/app/runtime/maintenance.py`
- `docs/branches/memory.md`

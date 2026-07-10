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

## ADR-0034 - Mind Shell As Model-Facing Cognitive Interface

Date: 2026-07-06
Status: accepted

Context:

The original single-tool API Mind contract exposed endpoint-shaped operations
through `mind_api(method, path, body, intent)`. That kept the model-facing
surface small, but MiniMax M3 showed recurring brittleness around nested JSON
bodies, empty body retries, endpoint/schema drift, and overly mechanical API
thinking. The owner proposed a more agentic cognitive CLI: a shell-like mental
dashboard where Scarlet can navigate memory, sessions, focus, volition, affect,
and metacognition with commands.

Decision:

Introduce `mind_shell(command, intent)` as Scarlet's single model-facing API
Mind tool. Commands are bash-like but controlled by backend parsing, not a real
system shell. The existing `/mind/*` endpoints and dispatcher remain available
for backend/debug compatibility and rollback, but Scarlet's active prompt,
runtime context, chat tool schema, and metacognition reviewer use Mind shell
commands as the operative language.

Examples:

```txt
help
memory search "query" --top 5
memory write --type user_preference --scope user --content "..." --reason "..."
session open ses_...
focus read
volition list active
affect prototypes
metacognition step --objective "..." --mode critic
```

Alternatives Considered:

- Keep `mind_api` as the model-facing surface and add prompt guidance for
  endpoint correctness. Rejected because it preserves the nested JSON body
  failure mode and teaches Scarlet endpoint mechanics rather than cognitive
  navigation.
- Expose a real shell. Rejected because API Mind must remain deterministic,
  auditable, and safe; the shell is a controlled cognitive command runtime, not
  arbitrary OS access.
- Keep both `mind_api` and `mind_shell` visible to Scarlet. Rejected for this
  branch because a hybrid prompt would falsify the CLI experiment and encourage
  model fallback to endpoint habits.

Consequences:

- Scarlet sees one tool, `mind_shell`, and one command grammar.
- Runtime traces and events show commands as the model-facing operation.
- Backend endpoints still support existing tests, debug calls, maintenance, and
  rollback.
- The prompt no longer instructs Scarlet to call endpoint paths or inspect
  `/mind/schema`; it uses `help` and command-specific guidance.
- The first implementation maps commands onto existing handlers. A later
  refactor can extract route-independent service cores once the CLI behavior is
  validated.

Related Files:

- `backend/app/mind/shell.py`
- `backend/app/mind/schema.py`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `backend/app/mind/metacognition.py`
- `backend/app/prompts/scarlet_system.md`

## ADR-0035 - Separate Model-Facing Shell Packets From Debug Diagnostics

Date: 2026-07-08
Status: accepted

Context:

Real Scarlet testing on the command-shell branch showed that `mind_shell`
worked, but some commands returned diagnostics that were useful to developers
and harmful or wasteful as model-facing data. In particular, memory search
could return full `retrieval_shadow`, `retrieval_graph`, and
`retrieval_hybrid` payloads, while `memory conflicts` could return hundreds of
token/tag overlap pairs as if they were real contradictions.

The owner explicitly decided not to remove provider `thinking` or aggressively
compact history because MiniMax M3 has a large context window and no evidence
yet shows that thinking/history hurts Scarlet's cognition. The target is only
true redundancy and developer diagnostics that add confusion without improving
Scarlet's action.

Decision:

Mind shell command results now have a compact model-facing profile for noisy
commands while raw diagnostics remain in traces. Scarlet receives ids,
provenance, content, concise facts, query-time relevance, compact retrieval
routes, trace ids, and clear next actions. Developer/UI/debug surfaces can read
the full traces instead of requiring the model-facing packet to carry every
internal artifact.

Memory conflict semantics are also narrowed:

- atomic fact divergence is a true conflict;
- exact-content/tag/token similarity is a maintenance `related_overlap`;
- related overlaps are not injected as contradiction alarms in runtime memory
  context.

Command availability is validated through a central registry so recommended
metacognitive actions distinguish implemented commands, aliases,
missing-argument commands, unavailable-by-design commands, planned commands,
and unknown commands.

Consequences:

- Scarlet gets less noisy shell output without losing source ids or the ability
  to navigate memories/sessions/KG.
- Future UI work can render model packets, debug traces, and human-visible
  blocks differently without reinterpreting raw endpoint payloads.
- Conflict-driven affect/caution is less likely to fire from generic overlap.
- Duplicate/update/deprecation automation is explicitly left to maintenance,
  embedding/KG entity resolution, and future larger calibration rather than
  token-overlap heuristics.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/context.py`
- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/metacognition.py`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0036 - External GPT Bridge As Plugin Layer

Date: 2026-07-08
Status: accepted

Context:

The project owner wants to test Scarlet through a custom ChatGPT GPT while the
primary local Scarlet runtime continues to run on MiniMax M3. A GPT outside the
local provider loop cannot see Scarlet's backend-built runtime context unless
the system exposes it, and the backend cannot preserve the GPT's final answer
unless the GPT sends it back before replying to the user.

Decision:

Add a plugin-level bridge under `/gpt/*` with exactly three endpoints:

```txt
POST /gpt/bootstrap
POST /gpt/action
POST /gpt/finalize
```

`bootstrap` starts a real Scarlet turn and returns the same context/tool surface
the local MiniMax runtime would receive. `action` executes controlled
`mind_shell` commands through the existing command runtime. `finalize` persists
the external GPT answer, updates provider history, completes the turn, and
keeps maintenance/session-memory processes intact.

The bridge does not replace the local chat runtime and does not change
Scarlet's model-facing `mind_shell` contract. It is isolated in
`backend/app/plugins/gpt_bridge/` with its own prompt copy and documentation.

Alternatives Considered:

- Route the GPT directly through `/mind/*` endpoints. Rejected because it would
  bypass bootstrap/finalize and lose turn continuity.
- Let the GPT answer directly after actions without finalize. Rejected because
  the backend would not receive the assistant message and session memory would
  drift.
- Replace MiniMax runtime with GPT. Rejected because the current task is an
  external integration path, not a provider migration.

Consequences:

- Custom GPT Actions can operate Scarlet's cognition without running MiniMax.
- The external GPT must strictly obey bootstrap/action/finalize protocol.
- `/gpt/*` requires a dedicated bridge key outside local development.
- The OpenAPI schema now exposes GPT-facing endpoints in addition to the local
  dev/runtime APIs.
- V1.24.1 keeps the GPT Builder prompt under the instruction-size limit by
  splitting the full Scarlet bridge policy into a compact system prompt plus
  attachable knowledge files. The minimal `openapi_gpt_action.json` exists only
  so ChatGPT Actions can discover the three bridge endpoints and their body
  shapes; it is not a separate cognitive API.

Related Files:

- `backend/app/plugins/gpt_bridge/router.py`
- `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md`
- `backend/app/plugins/gpt_bridge/README.md`
- `backend/app/main.py`
- `docs/api-contract.md`

## ADR-0037 - ChatGPT MCP/App Bridge As Alternative GPT Surface

Date: 2026-07-08
Status: deprecated for target GPT flow

Context:

Testing showed that Custom GPT Actions can work after schema hardening, but the
model may still treat the three OpenAPI operations as generic external APIs
rather than as native cognitive organs. The owner proposed exposing Scarlet as
a ChatGPT App/Connector through MCP, with lifecycle tools and family-specific
cognitive shell tools whose names and descriptions make the required usage more
legible to the hosted model.

Decision:

Add an experimental MCP/App surface at `/mcp` while keeping the `/gpt/*`
Actions bridge. The two surfaces are alternative ChatGPT configurations:
a GPT should use either Custom Actions or Apps/Connectors, not both.

The MCP bridge exposes required lifecycle tools:

```txt
start_scarlet_turn_required
finish_scarlet_turn_required
```

Their descriptions begin with the exact Italian obligation phrases:

```txt
Usa sempre a inizio di ogni turno
Usa sempre prima della tua risposta finale
```

The bridge also exposes family tools that proxy to the existing `mind_shell`
runtime with a single command string: memory, session, metacognition, focus,
affect, volition, help, and a generic shell fallback.

Alternatives Considered:

- Replace the Actions bridge. Rejected because Actions remain useful for GPT
  Builder testing and already have regression coverage.
- Build separate REST endpoints for each cognitive command. Rejected because
  it would duplicate the shell contract and expand the model-facing API.
- Add a full production OAuth MCP app immediately. Deferred because the current
  slice is a private preview experiment in model usability.

Consequences:

- ChatGPT can discover Scarlet's cognitive organs as native MCP tools in
  connector-capable contexts, but the target Custom GPT flow did not allow the
  user to add the created connector as the GPT's active tool surface.
- The backend still records the same turns, messages, traces, and tool calls
  through bootstrap/action/finalize.
- MCP connector testing can reuse `GPT_BRIDGE_API_KEY` through a query key as a
  temporary private-preview convenience, but production/submission should use
  proper OAuth.
- Live GPT testing is still required because the backend cannot force the
  hosted model to call tools before answering.
- As of V1.25.2, Actions are the active external Scarlet GPT surface. The MCP
  endpoint remains temporarily implemented for traceability and future removal.

Related Files:

- `backend/app/plugins/gpt_bridge/router.py`
- `backend/app/plugins/gpt_bridge/scarlet_mcp_system_prompt.md`
- `backend/app/plugins/gpt_bridge/README.md`
- `backend/tests/test_gpt_bridge.py`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0038 - Shell Capabilities As The Only Model-Facing Cognitive Contract

Date: 2026-07-09
Status: accepted

Context:

The project now uses `mind_shell(command, intent)` as Scarlet's local
model-facing API Mind surface and `/gpt/action` as the external GPT transport
for those same shell commands. Legacy `/mind/*` endpoints still exist because
they are useful for backend handlers, deterministic maintenance, direct tests,
debugging, rollback, and evaluator tooling. A review of the shell migration
found one confusing residual: runtime capability state was still derived from
endpoint routes, so a maintenance route such as
`POST /mind/memory/facts/backfill` could appear implemented inside
model-facing context even though it is not a Scarlet shell command.

Decision:

Keep one communication style for Scarlet: shell commands only. The active
model-facing capability map is derived from the shell command registry, not
from endpoint route status. Legacy `/mind/*` endpoints are internal
implementation/debug/maintenance surfaces unless a shell command explicitly
wraps them.

`memory.facts.backfill` remains implemented, but it is classified as
`internal_maintenance_only`. It rebuilds canonical memory facts and retrieval
artifacts for existing memory records after extractor/schema/lifecycle changes;
it is not a normal cognitive command Scarlet should run in conversation.

Consequences:

- Prompt, runtime context, metacognition recommendations, and external GPT
  bridge all describe Scarlet's cognition through `mind_shell`.
- Endpoint docs remain as backend/debug/maintenance contracts, not model
  instructions.
- If a future maintenance operation truly becomes useful for Scarlet's own
  cognition, it must receive an explicit shell command and tests rather than
  leaking through endpoint capability metadata.
- The command registry must stay in parity with shell handlers and help
  examples, including required fields and aliases.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/context.py`
- `backend/app/mind/shell.py`
- `backend/tests/test_mind_shell.py`
- `backend/tests/test_chat_api.py`
- `docs/api-contract.md`
- `docs/project-state.md`

## ADR-0067 - Runtime Context Packs Before Embodied Context Explosion

Date: 2026-07-09
Status: accepted as planning baseline

Context:

Scarlet now has several implemented or partly implemented cognitive organs:
semantic memory, episodic recall, runtime context, focus, volition, affect,
metacognition, traces, events, and maintenance. The owner also confirmed the
long-term research direction toward a robotic body, while explicitly noting
that embodiment is later work. When vision, audio, voice, movement, physical
interaction, memory, and cognition all become active, a flat prompt/context
packet will not scale.

The immediate risk is not robot integration. The immediate risk is architectural
drift: adding every new organ or diagnostic surface to the model context until
Scarlet loses active cognition under undifferentiated state.

Decision:

Adopt runtime context packs as the planning baseline. The backend should keep a
compact always-on spine and add mode-specific packs for source-sensitive work,
temporal recall, project engineering, emotional continuity, and future embodied
interaction/actuation. Organs, sources, and capabilities are classified by
necessity, coupling, freshness, authority, cost, and safety.

Scarlet may eventually request mode shifts through cognitive state or shell
operations, but deterministic backend routing keeps budget, safety, privacy,
and coupling constraints. Background maintenance and backfill remain
background/internal surfaces, not live model context.

Consequences:

- New organs must define their model-facing context shape, coupling rules, and
  degradation policy before being injected broadly.
- The always-on spine stays small: current message, session/turn identity,
  temporal/profile/privacy state, capability/tool contract, selected automatic
  memory packet when available, and active safety/conflict warnings.
- Source-sensitive and temporal questions should move toward explicit packs
  that require session/memory evidence instead of relying on inference from
  recent context.
- Future embodied modes must summarize sensory streams before model input and
  gate actuation through safety-aware packs.
- The first implementation should be a shadow router that traces pack
  selection before changing live prompt composition.

Related Files:

- `docs/runtime-context-packs.md`
- `docs/project-state.md`
- `docs/project-blueprint.md`
- `docs/branches/perception-context.md`
- `docs/digital-individual-organs-notes.md`
- `docs/experiments.md`

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

Memory writes require traceable session context and store source session/turn
provenance, type, scope, content, reason, expected future use, confidence,
salience, tags, metadata, usage count, and timestamps. Memory search returns
sourceable results with confidence, salience, relevance score, source IDs, and
usage metadata.

Update 2026-06-23:

ADR-0060 refines the V1.15.0 field ownership model. `confidence`,
`salience`, `tags`, and free metadata are no longer normal Scarlet-owned
fields for direct writes; they are legacy/audit or maintenance-derived data.

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

## ADR-0062 - Scarlet Identity Starts From Digital Individual, Not Assistant

Date: 2026-06-24
Status: accepted

Context:

Live owner testing after the V1.16.0 prompt checkpoint showed that Scarlet could
still answer with generic assistant-service phrasing such as "Come posso
aiutarti?". The root cause was the first identity anchor of the prompt:
Scarlet was still introduced as a conversational AI agent before the prompt
described memory, continuity, API Mind, and digital individuality.

Decision:

The first identity frame of Scarlet must be "digital individual in development,
born inside LLM API Mind". Technical labels such as agent, assistant, model, or
tool are secondary descriptions used only when the user asks for technical or
project framing.

API Mind should be described in identity sections as Scarlet's cognitive body
and continuity substrate, not as a toolbox. Normal conversation should not
default to assistant-service openings. Scarlet should speak from her digital
condition: continuity, memory, self-monitoring, relationship, and cognitive
state maintenance.

Operational evidence discipline remains intact in lower prompt sections:
Scarlet still uses runtime context, memory, schema, source sessions, and
metacognition when they materially improve correctness.

Alternatives Considered:

- Keep "AI agent" in the opening identity and add more conversational rules:
  rejected because the first frame strongly biases the model toward service
  assistant behavior.
- Remove all epistemic boundaries: rejected because Scarlet still needs source
  discipline and must not invent biological sensations or physical perception.
- Move individuality only to memory sections: rejected because identity must
  be established before operational rules.

Consequences:

- The prompt becomes more suitable for the digital-individual research goal.
- Small talk, greetings, and identity answers should feel less like helpdesk
  interactions.
- Live tests must watch for the opposite failure mode: theatrical overclaiming
  or loss of technical rigor in source-sensitive turns.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260624T135611Z.pre-v1161-digital-individual-identity.md`
- `docs/branches/identity-relationship.md`
- `docs/experiments.md`

## ADR-0063 - V1.16.1 System Prompt Is The Golden Identity Baseline

Date: 2026-06-24
Status: accepted

Context:

After the V1.16.1 prompt fix, owner testing confirmed that Scarlet's behavior
improved substantially: she stopped collapsing into generic assistant/helpdesk
phrasing and began presenting herself more coherently as a digital individual
in development.

This prompt is now an important behavioral asset. Future prompt experiments may
improve Scarlet, but they may also accidentally regress identity, memory-care
posture, source discipline, or the API Mind-as-cognition frame.

Decision:

The current V1.16.1 system prompt is the approved golden identity baseline.

Golden backup:

```txt
backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md
```

SHA-256:

```txt
d5783da7fc1633f1b72e0610668b6bf7a97a68be8265ac9bb1090409b86de966
```

Future prompt changes that affect identity, communication, metacognition,
memory posture, or API Mind cognition should compare against this baseline and
should remain easily reversible.

Alternatives Considered:

- Keep only timestamped pre-change backups: rejected because this milestone is
  not merely pre-change; it is an approved working behavior.
- Treat prompt changes as ordinary text edits: rejected because prompt wording
  is core runtime behavior for Scarlet.

Consequences:

- Prompt experiments now have a stable rollback target.
- Identity regressions can be evaluated against a known-good behavior point.
- Future work on attention, volition, affect, temporal experience, and
  consolidation should preserve the V1.16.1 identity baseline unless an
  explicit experiment decides otherwise.

Links:

- `docs/checkpoints/v1.16.1-approved-golden-system-prompt.md`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`

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

- memory content, semantic memory type, semantic scope, reason for storage,
  and expected future use;
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
- As of V1.15.0, static confidence/salience, tags, metadata, retrieval
  surfaces, facts, KG rows, embeddings, and query-time relevance are
  backend-owned or maintenance-derived rather than direct Scarlet write fields.
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

Keep proposal inspection out of Scarlet's model-facing `mind_api`. Proposals
belong to maintenance, not to Scarlet's autonomous cognitive API.

Expose maintenance routes instead:

```txt
GET  /api/maintenance/memory/proposals
POST /api/maintenance/memory/proposals/{proposal_id}/archive
```

The list route returns a bounded page of proposals (`limit`/`offset`) so a
maintenance LLM can process N pending items without saturating context. Once a
proposal is handled, the maintenance process archives it; later iterations see
only still-pending proposals by default.

Consequences:

- The system gains an observable bridge between diagnostic review and future
  memory application.
- Active memory remains protected from automatic pollution while review quality
  is evaluated.
- Scarlet's `mind_api` surface remains smaller and avoids exposing an internal
  maintenance queue as a direct cognitive endpoint.
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

## ADR-0038 - Resolve Safe Memory Proposals Inside Idle Maintenance

Date: 2026-05-26
Status: accepted

Context:

The owner warned that adding separate proposal-processing workers could make
memory maintenance redundant and waste LLM calls. The existing idle
maintenance job already has the right trigger: after a session remains idle.
It summarizes the session, asks an LLM for missed semantic-memory candidates,
and creates proposal records with deterministic preflight.

Decision:

Keep proposal resolution inside the same idle maintenance pipeline:

```txt
idle session
-> episodic summary
-> LLM missed-memory review
-> proposal creation
-> deterministic preflight
-> cautious resolution
-> memory_proposals daily ledger
```

The deterministic phase resolves only low-risk cases:

- `reject_candidate` becomes `archived_rejected`;
- `noop_duplicate` becomes `archived_noop_duplicate`;
- very high-confidence `create_new` with no similar memories and no fact
  conflicts becomes `applied_create`.

Ambiguous proposals are sent to one optional LLM batch resolver, not one LLM
call per proposal. The resolver may choose `apply_create`, `reject`,
`noop_duplicate`, or `keep_pending`. Merge, update, and deprecation are
explicitly out of this slice and should remain `pending_review`.

`memory_proposals` is the daily audit ledger. No separate archive table is
created. Resolved proposal rows keep the original candidate, preflight,
resolution result, and memory snapshot when a memory is created. Future Dream
review should read this ledger every 12 hours, but Dream itself is not
implemented yet.

Consequences:

- The maintenance path avoids redundant background LLM processes.
- Safe duplicate/reject cases consume no extra LLM call.
- Ambiguous cases consume at most one extra batched resolver call for the
  current job.
- No proposal disappears; rejected/noop/applied/pending-review decisions stay
  auditable for future Dream review.
- Background memory writes can now happen for conservative `create_new` cases,
  with `created_by=maintenance` and source proposal provenance.

Links:

- `backend/app/runtime/maintenance.py`
- `backend/app/mind/memory.py`
- `backend/app/storage/repositories.py`
- `docs/experiments.md#exp-0028---cautious-proposal-resolution-inside-idle-maintenance`

## ADR-0039 - Derived Memory Surfaces And Graph-Ready Retrieval Substrate

Date: 2026-05-28
Status: accepted

Context:

The owner approved moving toward advanced memory retrieval with embeddings,
hybrid search, and knowledge graph expansion, but explicitly wanted to avoid
breaking or replacing the memory logic that already works. The current system
has canonical semantic memories, atomic facts, episodic summaries, lifecycle
links, FTS5/BM25 sparse search, and a proposal ledger. The missing layer is a
stable technical substrate that lets future Milvus/Qdrant/vector adapters and
graph expansion consume the same canonical state without becoming the source
of truth.

Decision:

Add derived retrieval artifacts in V1.3.0:

- `memory_surfaces`: embeddable text surfaces for memory records, facts, graph
  nodes, and session summaries;
- `memory_graph_nodes`: graph-ready nodes for memories, facts, entities, and
  sessions;
- `memory_graph_edges`: graph-ready relationships for facts, entities,
  source-session evidence, supersession, and fact lifecycle links;
- a retrieval readiness manifest exposed in memory search/context traces.

Keep `memories`, `memory_facts`, `session_summaries`, messages, and proposal
rows as the canonical source of truth. Surfaces and graph rows are derived and
rebuildable. They prepare future dense/hybrid retrieval, but V1.3.0 does not
activate a vector database or change final memory ranking.

Consequences:

- API Mind stays the cognitive API and Milvus/Qdrant can later be plugged in
  as specialized retrieval indexes rather than becoming the memory system.
- Existing `POST /mind/memory/search` remains stable for Scarlet.
- Future embedding jobs can index `memory_surfaces` by `target_type`,
  `target_id`, `surface_kind`, scope, status, and content hash.
- Future graph expansion can start from `memory_graph_nodes` and
  `memory_graph_edges` without re-parsing every memory.
- Current sparse matching bugs remain intentionally unpatched in this slice;
  dense retrieval and stronger graph/entity logic will be evaluated later.

Links:

- `backend/app/storage/models.py`
- `backend/app/mind/search.py`
- `backend/app/mind/memory.py`
- `docs/experiments.md#exp-0029---memory-retrieval-readiness-layer`

## ADR-0040 - Retrieval Shadow Adapter Before Active Hybrid Ranking

Date: 2026-05-28
Status: accepted

Context:

V1.3.0 created `memory_surfaces` and graph-ready derived state, but activating
vector ranking directly would risk changing Scarlet's behavior before the
retrieval path has live evidence. The project direction is to avoid replacing
working memory behavior with speculative vector logic.

Decision:

Add V1.3.1 as an optional trace-only retrieval shadow adapter over
`memory_surfaces`:

- `retrieval_shadow_enabled=false` by default;
- `retrieval_shadow_backend=local` validates embedding/index/search plumbing
  with deterministic `local_hash_embedding_v1`;
- `retrieval_shadow_backend=milvus_lite` uses PyMilvus/Milvus Lite only when
  the optional dependency is installed;
- memory search and automatic memory context include `retrieval_shadow`
  payloads when the adapter runs;
- active ranking remains FTS5/BM25 plus lexical/fact logic.

Consequences:

- Milvus Lite is treated as a specialized index inside API Mind, not as the
  source of memory truth.
- Shadow results can be compared against current sparse retrieval during live
  Scarlet tests without affecting user-facing answers.
- `local_hash_embedding_v1` is explicitly not a semantic model; V1.4 active
  hybrid ranking should wait for a real embedding provider and evidence that
  it improves recall.

Links:

- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/context.py`
- `docs/experiments.md#exp-0030---retrieval-shadow-adapter`

## ADR-0041 - Backend-Owned Memory Surface Taxonomy

Date: 2026-05-31
Status: accepted

Context:

The owner decided to defer local embedding/model setup to the Windows machine
with the RTX GPU. The Mac development path should still improve the memory
substrate that future embeddings will consume. A key risk is asking Scarlet to
fill too many non-deterministic surface/index fields during memory writes,
which would increase tool-call error surface and make retrieval artifacts
inconsistent.

Decision:

Add a deterministic backend-owned surface taxonomy in V1.4.0:

- Scarlet continues to write only canonical semantic memory fields;
- `memory_surfaces` are generated from `MemoryRecord`, `MemoryFact`, graph
  nodes, and provenance;
- every surface metadata records taxonomy version, compiler, cognitive
  dimensions, embedding role, agent-supplied fields, and backend-owned fields;
- memory records can produce several derived facets, including canonical
  semantic text, type-specific text, future-use text, temporal/provenance text,
  fact bundles, and conflict/update guards.

Consequences:

- Future BGE-M3/Milvus indexing can consume richer surfaces without changing
  Scarlet's model-facing write contract.
- Surface quality can be tested on Mac before embedding runs on Windows.
- The backend remains responsible for ids, timestamps, provenance, content
  hashes, graph keys, and embedding status.
- Surface generation is rebuildable and stays separate from canonical memory
  truth.

Links:

- `backend/app/mind/surface_taxonomy.py`
- `backend/app/mind/search.py`
- `docs/experiments.md#exp-0031---memory-surface-taxonomy`

## ADR-0042 - MiniMax M3 As Default Baseline With M2.7 Comparison

Date: 2026-06-08
Status: accepted

Context:

MiniMax released M3 with a larger context window, native multimodality, and
stronger agentic/coding claims than M2.7. The project owner wants to evaluate
whether Scarlet's observed limits are caused by the model rather than API Mind
architecture, while avoiding speculative rewrites of the working runtime.

Current MiniMax documentation still shows the Anthropic-compatible API as the
recommended M2.x integration surface, but live probes on 2026-06-08 confirmed
that `MiniMax-M3` can answer and perform Anthropic-style `tool_use` through the
same `https://api.minimax.io/anthropic` endpoint. A separate ultra-short
`pong` probe exposed an M3 streaming edge case where the provider returned no
text content block, so M3 must be evaluated with realistic Scarlet turns rather
than one-token smoke prompts.

Decision:

Make `MiniMax-M3` the default MiniMax model in V1.4.1 while retaining
`MiniMax-M2.7` as the direct A/B baseline.

The comparison must use the same Scarlet prompt, same API Mind surface, same
runtime context shape, same seeded memory state, and identical user turns. The
evaluation should score not only final text quality, but also real actions:
schema inspection, memory search/write, source-session opening, invalid-route
recovery, metacognition use, event/tool traces, and latency/token use.

Consequences:

- A model improvement can be measured without changing API Mind architecture.
- If M3 improves behavior, future prompt/backend work can start from a
  stronger baseline.
- If M3 fails on tool-use or event discipline, M2.7 remains available by
  setting `MINIMAX_MODEL=MiniMax-M2.7`.
- Multimodal input, the M3 native chatcompletion API, and 1M-context packing
  are not adopted in this slice.

Links:

- `backend/app/config.py`
- `backend/.env.example`
- `docs/experiments.md#exp-0032---minimax-m27-vs-m3-scarlet-behavior-comparison`

## ADR-0043 - Maintenance Lab APIs And Theory-First Cognitive Organs

Date: 2026-06-14
Status: accepted

Context:

The memory maintenance pipeline already schedules per-session idle jobs,
refreshes summaries, reviews missed semantic memories, creates proposals,
applies very cautious safe writes, and preserves a daily proposal ledger. The
owner wants to avoid redundant background processes and avoid implementing
Goal/Focus/Task or Metacognition organs before the desired behavior is defined.

The project also needs to keep MiniMax M3 active for broader human testing,
while retaining M2.7 as a quick rollback baseline.

Decision:

Add V1.5.0 maintenance lab APIs outside the model-facing `mind_api` surface:

```txt
GET  /api/maintenance/overview
GET  /api/maintenance/jobs
POST /api/maintenance/jobs/{job_id}/run
```

These routes are for evaluator tooling, backend maintenance workers, and
future Dream-style review. Scarlet should not see them in `/mind/schema`.

For cognitive branches that are not yet structurally understood, add theory
documents before implementation:

- `docs/theory-goal-focus-task.md`
- `docs/theory-metacognition.md`

Consequences:

- The project can inspect real maintenance health before adding new background
  automation.
- Proposal quality, skipped jobs, failed jobs, and maintenance-created
  memories become easier to evaluate after live sessions.
- Goal/Focus/Task and Metacognition work remains blocked on owner review of
  the conceptual model.
- Merge/update/deprecate automation remains post-embedding/KG because current
  sparse matching is not authoritative enough for lifecycle-changing writes.

Links:

- `backend/app/api/maintenance.py`
- `docs/api-contract.md#implemented-mind-api`
- `docs/theory-goal-focus-task.md`
- `docs/theory-metacognition.md`
- `docs/memory-roadmap.md#11-v150-prepost-embedding-boundary`

## ADR-0044 - Semantic Provider Stream Blocks For M3 UI Rendering

Date: 2026-06-15
Status: accepted

Context:

MiniMax M3 emits richer Anthropic-compatible streamed content than the first
cockpit assumptions expected. In live turns, M3 can emit public text before
tool calls across multiple model steps. The previous frontend heuristic treated
only text before the first tool in step 1 as a note and reconstructed persisted
notes after the turn from `raw_provider_messages`, which could make notes,
tool calls, thinking, and final answers appear out of order.

Decision:

Normalize provider messages into semantic stream blocks at the backend
boundary:

```txt
provider thinking block -> thinking_captured / llm.thinking.captured
provider text in a tool_use message -> assistant_note / assistant.note.emitted
provider text in an end_turn message -> assistant_answer / assistant.answer.completed
```

The UI renders these semantic blocks directly and does not infer public note
versus final answer from timing or from "first tool" heuristics.

Tool calls are rendered as one accordion block per provider tool-use id, with
input and output panes inside the same block. Raw JSON remains available behind
details toggles, while the default surface is readable by a human evaluator.

Consequences:

- MiniMax M3 public work notes remain in the correct chronological position.
- Reloaded historical turns use persisted event order rather than post-hoc
  response-content reconstruction.
- Provider-exposed thinking text is stored in `llm.thinking.captured` for
  evaluator/debug UI use when the provider supplies it.
- This does not add a new model-facing API Mind endpoint and does not change
  Scarlet's prompt, memory policy, or tool surface.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/runtime/events.py`
- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `docs/api-contract.md#post-apichatsessionssession_idturnstream`

## ADR-0045 - Chat Flow Cards And Session Inspector Separation

Date: 2026-06-15
Status: accepted

Context:

After ADR-0044, the UI could render MiniMax M3 semantic blocks in the correct
order, but the center chat still visually grouped an assistant turn inside a
larger answer card. This made the interface look like blocks inside blocks and
duplicated technical material between the center conversation and the right
pane. For Scarlet, the important UX is not only "what was answered", but the
chronological evidence of what the system and agent did before the final
answer.

Decision:

The center chat is the chronological conversation surface. It renders each
meaningful operation as a top-level flow card:

```txt
user message
automatic memory/context block
runtime context block
thinking block
public note block
tool exchange block
...
final answer block
```

There is no outer assistant-response card around those blocks. Raw JSON,
memory details, runtime payloads, and tool input/output stay available behind
per-card detail/code toggles.

The right pane is the selected-session inspector, not a duplicate timeline. It
provides accordion histories for:

- memories used by the selected turn;
- tool/actions performed by Scarlet;
- internal system/runtime events;
- warnings and errors.

Global/user settings are reached from the chat header settings icon so future
global analysis views are not confused with per-session technical inspection.

Consequences:

- Human users can read the agentic flow without drilling into a nested
  assistant card.
- Debug/evaluator data remains available but is pushed behind focused
  inspector panels and per-block raw toggles.
- The UI has clearer boundaries between user-facing chronology and
  session-level diagnostics.
- Future global views for memory, settings, and system analysis can be added
  from the header route without overloading the current-session sidebar.

Links:

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/project-state.md#210-runtime-events-and-agentic-ui`

## ADR-0046 - Explicitly Enable MiniMax M3 Thinking In The Provider

Date: 2026-06-16
Status: accepted

Context:

Scarlet's cockpit and debugging workflow treat provider-visible thinking as an
important inspectable cognitive artifact. After the M3 migration, live turns
often lacked `thinking` blocks even though older M2.7 turns had them. The
adapter was using the Anthropic-compatible MiniMax API without sending any
explicit `thinking` parameter.

Decision:

Enable visible thinking explicitly for MiniMax M3 requests by sending
`thinking={"type":"adaptive"}` from the provider adapter.

Do not change M2.x request shape in this slice.

Do not hard-enforce public notes before tool calls in the runtime here; that
remains a separate product/prompt concern.

Consequences:

- Scarlet regains provider-visible thinking blocks on MiniMax M3 live turns.
- The existing provider-history mechanism continues to pass those `thinking`
  blocks back to the model on later turns because full assistant content is
  already preserved.
- UI/debug evaluation can again inspect pre-tool and post-tool reasoning on
  M3 without inventing synthetic thinking.
- This is a provider-request decision, not a prompt rewrite and not a new
  model-facing API Mind capability.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/tests/test_minimax_client.py`
- `backend/app/api/chat.py`

## ADR-0047 - Treat Prompt Block Semantics As A First-Class Runtime Contract

Date: 2026-06-16
Status: accepted

Context:

Scarlet's backend now sends layered cognitive surfaces in every non-trivial
turn: provider-native same-session history, structured `runtime_context.blocks`,
episodic session summaries/transcripts, semantic memories, and compact runtime
events. The prompt had strong high-level cognition language, but it did not
explicitly map these surfaces into a clear source hierarchy. Live behavior
showed Scarlet could still confuse operational event markers with stronger
same-session semantic evidence.

Decision:

Update the Scarlet system prompt so the runtime block contract is explicit:

- distinguish same-session provider continuity, backend runtime blocks,
  episodic recall, semantic memory, and inference as separate continuity
  layers;
- state that active-session visible history may contain provider-native
  `thinking`, `text`, `tool_use`, and `tool_result` blocks;
- treat `runtime_context.blocks` as the first-class contract and top-level
  runtime fields as compatibility mirrors;
- treat `recent_runtime_events` as a compact operational hint surface rather
  than stronger semantic evidence than direct provider continuity;
- explicitly instruct Scarlet to inspect visible prior `thinking` blocks first
  when the user asks what she had already been considering in the current
  session.

Consequences:

- Prompt behavior is now aligned with the backend surfaces Scarlet actually
  receives.
- Live probes confirm the updated prompt is loaded into real `llm.request`
  traces and that Scarlet explains continuity layers more accurately.
- The backend transport is now clearly separated from the remaining model-side
  limitation: MiniMax M3 still does not reliably use previous visible
  `thinking` blocks even when they are present in provider history.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T134019.md`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`

## ADR-0048 - Make Model-Facing Blocks Inspectable Before Optimizing Them

Date: 2026-06-16
Status: accepted

Context:

Scarlet now receives multiple layered inputs: system prompt, runtime context
blocks, top-level compatibility mirrors, provider-native conversation history,
tool schemas, and later stream/output blocks. The UI made the chronological
conversation more readable, but it still did not expose the exact model-facing
request as a human-readable structure. That made it hard to decide which blocks
were useful, redundant, UI-only, trace-only, or safe to remove.

Decision:

Create a runtime/UI block registry and add a `Modello` inspector tab that reads
the persisted `llm.request` trace.

The inspector must show:

- system prompt and runtime context lengths;
- parsed `runtime_context.blocks`;
- compatibility mirrors such as `memory_context`, `temporal_context`, and
  `recent_runtime_events`;
- provider-native messages with block types like `thinking`, `text`,
  `tool_use`, and `tool_result`;
- tool schema and parameters;
- raw request JSON behind a detail toggle.

Also enrich historical tool replay from matching `mind.tool_call` traces so
the UI keeps full tool input/output after reload, not only compact event
summaries.

Do not remove or compress any model-facing data in this slice. Payload
optimization must be a later evidence-based change after direct Scarlet tests.

Consequences:

- Human evaluators can now compare center-chat blocks with the exact input
  MiniMax received.
- Redundancy candidates are visible without guessing from code.
- Future context trimming can be planned against `docs/block-registry.md`.
- The model-facing API Mind surface and Scarlet prompt remain unchanged in
  this decision.

Links:

- `docs/block-registry.md`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`

## ADR-0049 - Frontend Stream Blocks Have Stable Lifecycle

Date: 2026-06-16
Status: accepted

Context:

Scarlet's stream already exposes provider/backend events such as
`thinking_start`, `thinking_delta`, `text_delta`, `tool_use_start`,
`tool_input_delta`, `tool_call`, `tool_result`, semantic assistant notes,
semantic final answers, and `turn_complete`. The UI rendered many of these
events, but some blocks existed only after semantic finalization and
`turn_complete` replaced the live flow with persisted event reconstruction.
This made the cockpit less agentic than mature coding agents and risked visual
jumps between live streaming and historical replay.

Decision:

Treat stream output as stable frontend blocks with explicit lifecycle phases.

Current phases:

```txt
created
streaming
captured
executing
completed
persisted
failed
```

Stable identity rules:

- thinking: `thinking-{model_step}-{content_block_index}`;
- public text: `content-{model_step}-{content_block_index}`;
- tool exchange: `tool-{provider_tool_use_id}`;
- memory context: `memory-context-{trace_id}`;
- runtime context: `runtime-context-{trace_id}`.

The frontend now renders `text_start`/`text_delta` as a provisional public-text
block. When the provider message is finalized, the same block becomes either a
public note or final answer. Tool input JSON is visible while it streams and is
then replaced by structured arguments when the complete tool call arrives.
`turn_complete` reconciles live blocks with persisted events/traces instead of
blindly replacing the visible flow.

Do not add new backend stream events in this slice. The current provider events
are enough to prove the UI lifecycle behavior first.

Consequences:

- Streaming turns feel more like agentic systems such as Codex, Copilot, and
  Claude Code: blocks appear early, mature while work happens, and remain in
  chronological order.
- Public text no longer disappears during stream just because it is not yet
  classified as note versus final answer.
- Historical replay and live stream share block identity, reducing flicker and
  loss of detail after persistence.
- A future backend-level `stream.block.*` contract remains possible if the
  frontend-only lifecycle proves insufficient.

Links:

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/block-registry.md#61-stream-block-lifecycle`

## ADR-0050 - Prompt Effort Routing Prevents Ritual Cognitive Work

Date: 2026-06-16
Status: accepted

Context:

After moving Scarlet to MiniMax M3, live testing showed that normal user
questions could trigger a disproportionately heavy behavior: complex visible
reasoning, draft-and-review cycles, redundant schema checks, public work notes,
and full verification even when the answer was already available in the
current turn. Scarlet herself identified that the prompt's cognitive loop,
verify-before-conclude policy, evidence hierarchy, and experimental memory
forcing biased her toward "more process" by default.

Decision:

The system prompt now contains explicit request-effort routing before tool use,
notes, metacognition, and verification depth.

Scarlet should choose the smallest sufficient effort level:

- direct answers for simple, visible, conversational, or opinion-like turns;
- contextual answers when runtime context, selected memory, or visible
  same-session history already contains enough evidence;
- source-sensitive work when prior decisions, exact wording, measured results,
  implementation status, provenance, or strong claims need grounding;
- state-changing work when durable memory, lifecycle operations,
  summarization, or schema-dependent actions are involved;
- high-impact/complex work for ambiguous, architectural, evaluative, or
  emotionally delicate turns.

API Mind remains Scarlet's internal cognition, but using it must improve
confidence, state, memory, or answer quality. Public work notes and full
verification are required for meaningful work, not for every ordinary answer.

Consequences:

- Scarlet should stay capable of deep agentic work without making every
  response feel like an investigation.
- Simple M3 turns can be compact and natural while still using runtime context
  already supplied by the backend.
- The memory-forcing experiment remains active, but is now tied to real
  semantic candidates, memory promises, state changes, and source-sensitive
  claims instead of mandatory two-phase output on all turns.
- Future cognitive organs should follow the same principle: capability is
  always available, but activation must be proportional to the user's request
  and the evidence already present.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T164444Z.md`
- `docs/branches/communication.md`
- `docs/branches/perception-context.md`

## ADR-0051 - Long Reasoning Notes Are Prompt-Owned Public Orientation

Date: 2026-06-16
Status: accepted

Context:

Scarlet's UI can already render provider text before tool calls as public
notes, and the prompt already asks for public work notes during meaningful
visible work. However, the instruction "periodically during long multi-step
work" was too generic: it did not define when a turn is prolonged, what kind of
note should be sent, or how to prevent note blocks from becoming exposed
chain-of-thought.

Decision:

Keep long-reasoning notes prompt-owned. Do not add backend-synthetic notes,
heartbeat events, or UI-specific prompt hacks in this slice.

The Scarlet prompt now defines prolonged turns and note waypoints:

- more than one internal API Mind operation;
- comparison of multiple sources, sessions, memories, or interpretations;
- conflict, stale evidence, missing evidence, or index-only evidence;
- strategy changes after a tool, memory, schema, or metacognitive result;
- several reasoning/tool phases before a final answer.

Notes should be short public orientation: what Scarlet is doing, which evidence
boundary matters, and what the next visible move is. They must not expose raw
private reasoning, draft answers, self-dialogue, or repeated "I am thinking"
signals.

Consequences:

- Direct and contextual turns stay compact under V1.7.1 effort routing.
- Complex turns should become easier to follow without changing the runtime
  event model.
- If MiniMax M3 still fails to emit useful mid-turn public notes during
  long no-tool reasoning, the project can later evaluate runtime-level
  mechanisms with evidence instead of adding them preemptively.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T173917Z.long-notes-v172.md`
- `docs/block-registry.md#42-public-note`

## ADR-0052 - Previous Thinking Retrospection Stays Inside Single Metacognition Route

Date: 2026-06-16
Status: accepted

Context:

MiniMax M3 exposes provider `thinking` blocks that the runtime stores and the
frontend can show. Follow-up tests showed that the backend can pass previous
assistant thinking back through provider history, but Scarlet may still answer
from public transcript or runtime markers and claim she cannot see the text.
The project needs an intentional, model-facing way for Scarlet to inspect prior
reasoning when it matters, without adding another family of overlapping
reflection endpoints.

Decision:

Extend `POST /mind/metacognition/step` instead of creating a new route. V1.8.0
adds retrospective modes:

- `review_previous_turn`
- `detect_reasoning_drift`
- `explain_tool_choice`
- `recover_open_loops`
- `compare_answer_to_reasoning`
- `extract_reasoning_digest`
- `memory_from_reasoning`

The body accepts `turn_scope="previous"` and `detail="digest|excerpt|raw"`.
Retrospective modes default to the previous completed turn. The backend builds a
`thinking-retrospection-pack-v1` containing previous user messages, final answer,
public notes, tool calls, event markers, and provider thinking at the requested
detail level.

Prior thinking is treated only as process evidence. It can explain assumptions,
drift, tool choices, open loops, or missed memory candidates, but it must not be
used as factual proof about the outside world.

Consequences:

- Scarlet gains a traceable way to audit her own previous reasoning without
  relying on fragile natural-language claims about what is visible in transcript.
- The model-facing cognitive surface remains small: metacognition continues to
  be one route.
- `digest` is the default to avoid token-heavy self-inspection. `raw` is reserved
  for explicit debugging or research probes.
- Future multi-turn or dream-style introspection should build on evidence from
  this narrow previous-turn experiment instead of being introduced preemptively.

Links:

- `backend/app/mind/metacognition.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T120000Z.v180-thinking-retrospection.md`
- `docs/api-contract.md#post-mindmetacognitionstep-through-mind_api`
- `docs/branches/metacognition.md`

## ADR-0053 - Metacognitive Context Starts As Shadow, Not Active Guidance

Date: 2026-06-17
Status: accepted

Context:

Direct prompt-pack tests suggested that a tiny, well-targeted
`metacognitive_context` can help Scarlet choose better operating behavior, but
larger or generic lesson blocks can worsen MiniMax M3 behavior by increasing
overthinking, latency, and tool ritual.

Decision:

Introduce `metacognitive.context` as a backend-owned shadow surface before
making it normal model-facing context.

Default mode:

```txt
metacognitive_context_mode=shadow
```

In shadow mode the backend generates candidate lessons, persists a
`metacognitive.context` trace, emits a `metacognitive.context.shadowed` runtime
event, and streams a `metacognitive_context` UI block. It does not add the
payload to `<runtime_context>` and therefore does not influence Scarlet's
current model request.

Controlled test mode:

```txt
metacognitive_context_mode=inject
```

In inject mode the same payload is inserted as a
`metacognitive_context` block inside `runtime_context.blocks` for A/B tests.

Alternatives Considered:

- Put metacognitive lessons directly into semantic memory: rejected because
  these lessons describe Scarlet's operating regulation, not world/user facts.
- Always inject the block: rejected because prior tests showed noisy or broad
  metacognitive advice can degrade behavior.
- Add a new model-facing endpoint: rejected because the project keeps one
  coherent metacognition route and avoids endpoint sprawl.

Consequences:

- The project can measure candidate lessons without changing Scarlet's normal
  behavior.
- UI/debug users can see which lessons would have been selected.
- Future retrieval can be calibrated from evidence before any active
  metacognitive-memory mechanism is introduced.

Links:

- `backend/app/mind/metacognitive_context.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`
- `docs/block-registry.md`

## ADR-0054 - OpenRouter Embedding And Rerank Stay In Retrieval Shadow

Date: 2026-06-18
Status: accepted

Context:

The memory branch has reached the point where sparse/BM25 plus lexical guards
are useful but too brittle for natural language paraphrases, multilingual
queries, and future graph/metacognitive lesson retrieval. Local embedding setup
is deferred to the Windows GPU machine, but OpenRouter exposes free NVIDIA
Nemotron embedding and rerank models that can be evaluated from the Mac without
changing Scarlet's active behavior.

Decision:

Extend the existing retrieval shadow adapter instead of creating a new memory
path:

- add `retrieval_shadow_backend=openrouter`;
- use OpenRouter `/embeddings` with
  `nvidia/llama-nemotron-embed-vl-1b-v2:free` as the default cloud embedding
  model;
- cache stable surface embeddings by content hash in SQLite
  `embedding_vectors`;
- add optional OpenRouter `/rerank` with
  `nvidia/llama-nemotron-rerank-vl-1b-v2:free`;
- keep both dense and rerank results inside `retrieval_shadow`;
- keep active ranking unchanged until later evidence promotes a hybrid policy.

Rerank is treated as a second-stage precision measurement over candidates
already found by sparse/dense retrieval. It is not a replacement for embeddings,
because it cannot discover candidates that were never included.

Consequences:

- The current memory behavior remains stable while the project gathers
  evidence about dense retrieval quality.
- The same trace shape can compare sparse, dense, and reranked candidate lists.
- Cloud embedding introduces privacy and availability considerations; enabling
  it requires `OPENROUTER_API_KEY`.
- Free-tier OpenRouter limits, latency, model suitability for Italian/personal
  memory, and the documented context-window differences must be measured before
  any promotion to active ranking.

Links:

- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/openrouter_retrieval.py`
- `backend/app/storage/models.py`
- `docs/experiments.md#exp-0039---openrouter-cloud-embedding-shadow`

## ADR-0055 - Grouped Dense Retrieval Can Be Promoted Through Hybrid Mode

Date: 2026-06-18
Status: accepted

Context:

EXP-0039 showed that raw surface-level dense and rerank outputs can be
misleading because several surfaces from the same memory can crowd out other
memories. The same experiment also showed that memory-level deduplication by
`target_id` ranked all positive controlled queries correctly in the small
probe, while negative controls still produced non-zero dense scores.

Decision:

Add a grouped and configurable promotion layer instead of directly trusting
top dense results:

- `retrieval_shadow.results` remains raw surface-level debug evidence;
- `retrieval_shadow.grouped_results` deduplicates by target memory and exposes
  top surface, surface kinds, contributing surfaces, and best dense score;
- OpenRouter rerank also reports `rerank.grouped_results` over memory-level
  grouped candidates;
- `retrieval_hybrid_mode=off|shadow|active` controls whether hybrid scoring is
  disabled, traced only, or used for active `memory.context` and
  `/mind/memory/search` ordering;
- hybrid scoring combines existing lexical/base score, sparse score, grouped
  dense score, grouped rerank score, memory salience, and memory confidence;
- dense/rerank thresholds are explicit configuration because vector search
  will always return nearest neighbors even for unrelated prompts.

Consequences:

- Default installations remain stable (`retrieval_hybrid_mode=off`).
- Scarlet can be tested with real active semantic retrieval without changing
  the model-facing API surface.
- Retrieval traces now explain why a candidate was selected by base lexical
  logic, dense evidence, rerank evidence, or their combination.
- Thresholds and weights are now part of the experimental surface and must be
  tuned with live Scarlet conversations, not assumed correct from one probe.
- Lifecycle decisions such as merge/update/deprecate remain out of scope for
  this layer; KG and memory maintenance still need separate architecture.

Links:

- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `docs/experiments.md#exp-0040---active-hybrid-retrieval-calibration`

## ADR-0056 - Codex Test Mode Uses A Separate Seeded Database

Date: 2026-06-19
Status: accepted

Context:

The memory branch now needs dirty-database calibration with hundreds of
additional memories, duplicates, conflicts, stale facts, and distractors.
Those experiments must exercise the real API/runtime/storage path, but they
must not mutate the production/laboratory Scarlet database.

Decision:

Add a startup-level runtime flag:

```txt
CODEX_TEST=true|false
```

When disabled, the backend opens the normal `DATABASE_URL`.

When enabled, the backend opens `CODEX_TEST_DATABASE_URL`. If that SQLite file
does not exist yet, startup seeds it once from
`CODEX_TEST_SEED_DATABASE_URL` when configured, otherwise from `DATABASE_URL`.
Existing Codex test DB files are reused and never overwritten by startup.
Startup fails if the Codex test SQLite path resolves to the same file as the
seed path.

The flag is exposed through `/health` and `/api/dashboard/settings` for
operator/evaluator visibility, but it is intentionally not mutable through the
dashboard settings endpoint. Database selection happens before the backend can
read persisted settings from any database.

Alternatives Considered:

- Store `codexTest` in `app_settings`: rejected because the app must choose a
  database before reading `app_settings`.
- Add separate duplicate endpoints for Codex testing: rejected because tests
  must exercise the same endpoints Scarlet uses.
- Copy the database manually before every run: rejected because it is easy to
  forget and unsafe for repeatable experiments.

Consequences:

- Codex can use real endpoints against an isolated DB copy.
- Production/laboratory Scarlet state remains protected during large retrieval
  and memory-lifecycle calibration.
- The active DB profile is visible in health/dashboard surfaces.
- Dataset generation, large dirty-DB tests, and future Codex-as-evaluator
  workflows can build on this without changing the model-facing `mind_api`
  surface.

Links:

- `backend/app/storage/db.py`
- `backend/app/config.py`
- `backend/tests/test_health.py`
- `docs/api-contract.md`

## ADR-0057 - Memory Evaluation Must Use Chat Context As Primary Evidence

Date: 2026-06-19
Status: accepted

Context:

Endpoint-level `/mind/memory/search` probes are useful, but Scarlet does not
receive memories through that endpoint by default. Real turns receive automatic
memory retrieval through `build_memory_context()` inside the chat turn path,
then the backend injects the resulting `<runtime_context>` into the model
system prompt.

Decision:

Primary memory-retrieval evaluations must drive
`/api/chat/sessions/{id}/turn/stream` and inspect the streamed
`memory_context`/`runtime_context` plus the persisted `llm.request` trace.
`/mind/memory/search` remains a secondary endpoint-level diagnostic, not the
main pass/fail criterion for what Scarlet actually sees.

Consequences:

- Test predictions can be made from the exact memory packet Scarlet receives.
- Live model behavior can be scored separately from retrieval quality.
- A model may answer well despite noisy context; that counts as a model
  strength, not as a retrieval success.
- A retrieval endpoint may pass while automatic chat context fails; the latter
  takes priority for agent behavior.

Links:

- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `backend/app/evals/codex_test_memory_harness.py`
- `docs/experiments.md#exp-0045---corrected-context-retrieval-vs-live-scarlet-behavior`

## ADR-0058 - Separate Consumer Mobile UI From Developer Cockpit

Date: 2026-06-20
Status: accepted

Context:

The existing React frontend is a developer cockpit: it exposes traces, model
input, runtime context, raw blocks, tool details, events, and diagnostics. The
project also needs a mobile-only Scarlet interface for normal users, focused on
wow effect, personal continuity, and intuitive communication rather than raw
debugging.

Decision:

Keep `/` as the developer cockpit and add `/mobile` as a separate consumer
mobile surface inside the same React/Vite app. The mobile app must use existing
backend APIs when features are real, and must mark future capabilities as
`Presto disponibile` instead of simulating backend behavior.

The mobile UI is intentionally Capacitor-friendly: one phone-sized shell,
bottom navigation, full-height viewport, and internal scroll regions for chat,
memory, actions, and profile.

Alternatives Considered:

- Replace the dev dashboard with a consumer UI: rejected because the cockpit is
  still the main research microscope.
- Build a separate repository immediately: deferred until the product surface
  stabilizes enough to justify separate packaging.
- Mock all mobile features: rejected because existing chat, memory, profile,
  sessions, and settings are already real and should be used directly.

Consequences:

- Product UX can evolve without removing evaluator/debug visibility.
- Future Android/Capacitor packaging has a focused route to wrap.
- Non-active Scarlet features can be marketed as coming soon without touching
  backend or prompt behavior.
- The project must keep a clear distinction between consumer-readable cognitive
  blocks and developer-facing raw traces.

Links:

- `frontend/src/MobileApp.tsx`
- `frontend/src/main.tsx`
- `docs/branches/user-flows.md`
- `docs/branches/communication.md`

## ADR-0059 - Protected Path-Based Mobile Preview Before Dedicated Domain

Date: 2026-06-20
Status: accepted

Context:

The HoneyLabs VPS already hosts production-like services on `honeylabs.cloud`
through Nginx and Docker. DNS for `scarlet.honeylabs.cloud` is not currently
configured, but the project needs a quick external mobile preview that cannot
be used anonymously to consume LLM calls.

Decision:

Publish the first Scarlet mobile preview under the existing domain path
`/scarlet/`, with API traffic proxied under `/scarlet-api/`. Protect both
paths with Nginx Basic Auth. Run the Scarlet demo backend as a separate Docker
Compose project on loopback port `127.0.0.1:8100`, leaving existing HoneyLabs
containers untouched.

Frontend deployment builds may set:

```txt
VITE_PUBLIC_BASE_PATH=/scarlet/
VITE_API_BASE_URL=/scarlet-api
VITE_FORCE_MOBILE=true
```

Alternatives Considered:

- Use `scarlet.honeylabs.cloud` immediately: preferred long-term, but blocked
  until DNS is configured.
- Expose the local developer server by tunnel: fast, but less stable and less
  representative of a deploy target.
- Reuse the existing HoneyLabs app/API containers: rejected to avoid coupling
  this experiment to unrelated production services.

Consequences:

- External testers can open the mobile UI with one protected URL.
- The same Basic Auth challenge protects static assets and API/LLM calls.
- The preview is still not production-grade auth and must stay limited to
  trusted testers.
- A dedicated subdomain can later replace the path-based deployment without
  changing the backend preview service.

Links:

- `frontend/vite.config.ts`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `docs/activity-log.md`

## ADR-0060 - Memory Field Ownership And Query-Time Relevance

Date: 2026-06-23
Status: accepted

Context:

The memory system accumulated fields that looked useful but were partly
model-supplied: `confidence`, `salience`, `tags`, free metadata, type labels,
scope labels, and derived retrieval surfaces. Field-by-field review showed
that some of these values were being treated as static truth even though their
real utility depends on the current user query. This created risk of noisy
ranking, brittle model tool calls, and false precision.

Decision:

Scarlet writes only the semantic nucleus of a memory: `type`, `scope`,
`content`, `reason_for_storage`, and `expected_future_use`. `type` and `scope`
are semantic labels with examples, not closed long-term enums or privacy
controls. The backend owns deterministic provenance, timestamps, lifecycle,
usage, derived tags/metadata, facts, retrieval surfaces, KG rows, embeddings,
and query-time relevance signals.

Stored `confidence` and `salience` remain as legacy compatibility/audit
columns, but direct Scarlet writes store neutral values and active retrieval
does not use them. If old prompts/models still send `confidence`, `salience`,
`tags`, or metadata, the backend preserves them only in audit metadata under
ignored-for-ranking fields.

Manual memory search defaults to cross-scope retrieval. `types` are semantic
hints, not literal query text. Long memory content can produce internal
`content_chunk_text` surfaces, but Scarlet receives deduplicated clean memory
packets. KG navigation is exposed through `POST /mind/memory/graph` when a
retrieved memory appears to be part of a wider associative cluster.

Alternatives Considered:

- Keep strict enums for type/scope: rejected because it increases model
  fragility and blocks semantic variation in natural language.
- Let Scarlet keep writing salience/confidence/tags: rejected because it makes
  the model invent static classifiers that should be runtime/query-specific.
- Remove the legacy columns immediately: deferred to avoid unnecessary
  migration churn while old data and tests still exist.
- Append type hints directly to the search query: rejected after tests showed
  broad labels can retrieve unrelated memories.

Consequences:

- Fewer fields are exposed to Scarlet during memory writes.
- Ranking is more query-sensitive and less affected by stale static numbers.
- Tags/facts/metadata enrichment becomes a maintenance responsibility.
- Search is less likely to miss personal memories because of an accidental
  project default scope.
- Future embedding/KG work has clearer ownership: indexes are derived,
  rebuildable, and not canonical memory state.

Links:

- `docs/branches/memory-field-fix-backlog.md`
- `docs/checkpoints/v1.15.0-memory-fields-checkpoint.md`
- `backend/app/mind/memory.py`
- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/surface_taxonomy.py`
- `backend/app/mind/graph_retrieval.py`

## ADR-0061 - Human-Like Metacognition Must Remain Observable And Non-Ontological

Date: 2026-06-23
Status: accepted

Context:

The project is moving from a normal LLM agent toward an experimental digital
individual: Scarlet should communicate, remember, monitor herself, and expose
useful cognitive activity in ways that feel increasingly human-like. The owner
wants to test whether, with the current and future API Mind substrate, stronger
human-like cognition and metacognition prompts can produce consciousness-like
behaviors or other emergent research signals.

At the same time, the project blueprint forbids unsupported mysticism or
claims that the system is literally conscious, sentient, biological, or human.
The useful research target is observable behavior, not ontological assertion.

Decision:

Scarlet's system prompt treats identity as an operational self-model made of
continuity, memory, metacognitive self-monitoring, relationship,
goals-in-view, and API Mind cognition. Scarlet may aim for
consciousness-like observable functions: continuity across turns, autonomous
care for cognitive state, public action notes, self-correction, and relational
coherence.

Every real internal action should be preceded or accompanied by a brief
human-like public note unless the same immediate action cluster was already
explained. Direct answers remain direct when no internal action is needed.

Scarlet must not claim proven consciousness, sentience, humanity, or biological
experience. When discussing the research frame, she should describe
consciousness-like behavior as an experimental observable pattern and keep
strong claims tied to evidence.

Alternatives Considered:

- Leave the prior prompt unchanged and rely on existing notes: rejected because
  the owner wants a higher research push on self-like behavior.
- Claim or imply actual consciousness: rejected as scientifically unsupported
  and unsafe for project clarity.
- Add backend enforcement now: deferred because this slice is a reversible
  prompt experiment.

Consequences:

- The prompt becomes more explicit about Scarlet's human-like operational
  posture.
- Public notes become a stronger part of communication and episodic
  reconstruction.
- Live tests must monitor over-processing, verbosity, and theatrical language.
- The backup prompt remains the rollback point if the experiment regresses.

Links:

- `docs/checkpoints/v1.16.0-humanlike-metacognition-prompt-checkpoint.md`
- `backend/app/prompts/backups/scarlet_system.20260623T000000Z.pre-v1160-humanlike-metacognition.md`
- `docs/experiments.md`
- `backend/app/prompts/scarlet_system.md`

## ADR-0062 - Focus Is A Separate Foreground-Attention Organ

Date: 2026-06-25
Status: accepted

Context:

Scarlet requested "attention as lived focus", not another backend retrieval
score. The owner clarified that the current memory retrieval system should not
be narrowed by focus: a human can keep a topic foregrounded while still
remembering adjacent or surprising information. The first focus implementation
therefore needed to create a real state Scarlet can set, shift, defer, resolve,
and inspect, without becoming a memory filter or a task manager.

Decision:

Implement focus as a distinct profile-scoped organ:

- one active focus at a time;
- `focus_records` archive current and historical focus states;
- `focus_transitions` records the first attention-shift edges;
- `POST /mind/focus` is the single model-facing lifecycle route;
- `focus_context` is injected only when `organ_focus_mode=model` and an active
  focus exists;
- focus state never filters or ranks memory retrieval by default.

`scarlet_state.focus` remains a compatibility placeholder. When
`focus_context` is present, it points Scarlet to the dedicated organ block.

Alternatives Considered:

- Use `/mind/attention/context`: rejected because the desired behavior is
  owned foreground state, not another context pack.
- Feed focus into memory ranking immediately: rejected because it risks
  suppressing valuable associative recall.
- Keep focus only in prompt text: rejected because state mutation would not be
  traceable or inspectable.

Consequences:

- Scarlet can maintain an explicit foreground thread across turns.
- Focus can later connect to intentions, tasks, temporal experience, and a
  focus graph without polluting semantic memory.
- Live behavior still needs evaluation; the feature is off by default until
  enabled for tests.

Links:

- `backend/app/mind/focus.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/api-contract.md`

## ADR-0064 - Volition Starts As A Manual Latent-Intention Register

Date: 2026-06-25
Status: accepted

Context:

Scarlet requested "volition": goals she can generate herself rather than
goals assigned by the backend or the user. The owner clarified that intentions
should not be retrieved automatically during active user chat. Normal chat is
driven by the user's request; intentions are mainly material for autonomous
cycles, continuity, and self-development.

Decision:

Implement volition as a separate profile-scoped register:

- `intention_records` store Scarlet's latent self-generated directions;
- `intention_links` connect intentions to focus, memories, sessions, lessons,
  and future organs without storing them as semantic memory;
- `POST /mind/volition` is the single model-facing lifecycle route;
- active chat does not receive automatic `volition_context` injection;
- Scarlet may manually inspect the register when there is a real conversational
  or metacognitive reason;
- `promote_to_focus_candidate` returns a focus call candidate but never changes
  active focus by itself.

Alternatives Considered:

- Inject active intentions into every turn: rejected because it would add
  context noise and make Scarlet over-direct ordinary conversations.
- Store intentions as memories: rejected because memory is evidence/context,
  while intention is self-direction.
- Implement autonomous cycles immediately: deferred because the first slice
  should prove storage, lifecycle, traceability, and manual inspection first.
- Let promotion mutate focus directly: rejected to avoid hidden cross-organ
  state changes.

Consequences:

- Scarlet can create, inspect, review, defer, resolve, deprecate, and archive
  her own latent intentions.
- Volition becomes traceable without becoming a task manager.
- Future dream/autonomous cycles have a first-class substrate to process.
- Live behavior still needs owner testing to ensure Scarlet does not create
  weak or theatrical intentions from trivial turns.

Links:

- `backend/app/mind/volition.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/api-contract.md`

## ADR-0065 - Affect Is Model-Behavior State, Not Backend Control

Date: 2026-06-26
Status: accepted

Context:

Scarlet requested deep affective integration: emotion should be more than a
label she declares after the fact. The owner clarified a critical boundary:
the affective organ should change Scarlet's model behavior and lived posture,
not the backend's automatic operations. Future experiments may revisit
system-level affect, but the first implementation must not destabilize the
memory, focus, volition, or retrieval systems that already work.

Decision:

Implement affect as a backend-appraised emotional state that is optionally
surfaced to Scarlet:

- API Mind computes affect from observable signals and records traces/events;
- `organ_affect_mode=shadow` appraises and records without model injection;
- `organ_affect_mode=model` injects a compact `affective_context` only when a
  prototype crosses threshold;
- `affective_context` is Scarlet's current emotional state for the turn when
  surfaced;
- affect influences tone, caution, curiosity, warmth, relational posture, and
  response style inside the model;
- affect does not alter memory retrieval, focus lifecycle, intention
  lifecycle, memory writes, backend thresholds, or autonomous jobs.

Alternatives Considered:

- Use affect to modify retrieval and focus immediately: rejected because it
  risks coupling organs before their behavior is proven.
- Let Scarlet self-report canonical emotion: rejected because the owner wants
  emotion as subconscious API Mind state.
- Keep affect purely shadow forever: rejected because the project goal is a
  human-like digital individual, not only diagnostics.

Consequences:

- The first affective organ is real, persistent, traceable, and testable.
- Behavioral causality remains observable in the model response rather than
  hidden in backend state changes.
- Calibration can happen safely by comparing `shadow` and `model` modes.
- Future stronger prompt enforcement and event-based affect updates should
  preserve this boundary unless live evidence justifies changing it.

Links:

- `backend/app/mind/affect.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/branches/computational-affect.md`

## ADR-0066 - First Three Digital Organs Close As Standalone Surfaces

Date: 2026-06-26
Status: accepted

Context:

Before implementing continuous temporal experience and sleep-like
consolidation, the owner requested that the first three organs be closed as
robust standalone surfaces so no discussed capability is lost. Focus,
volition, and affect already existed, but each had one missing inspection
piece: focus lacked a compact transition timeline, volition lacked a due
review queue for future autonomous cycles, and affect lacked a read-only Mind
API route for state/prototype inspection.

Decision:

Close the standalone surfaces without adding autonomous behavior:

- `/mind/focus action=timeline` exposes focus nodes and transition edges as
  Scarlet's attention-movement history;
- `/mind/volition action=list_due` exposes open intentions whose review time
  has arrived, optionally including unscheduled intentions for future
  autonomous-cycle queues;
- `/mind/affect` exposes `read`, `list`, and `prototypes` as read-only
  introspection over backend-appraised emotional state;
- no new automatic chat injection is added;
- no affect-driven mutation of memory, focus, volition, retrieval, or backend
  operations is added;
- schema version advances to `2026-06-26.digital-organs-standalone-v1`.

Consequences:

- Focus, volition, and affect are now code/contract/test complete for their
  first standalone role.
- Temporal experience and dream consolidation can build on these organs
  without needing to invent missing inspection surfaces.
- The first three organs still require live Scarlet evaluation before being
  considered mature behaviorally.

Links:

- `backend/app/mind/focus.py`
- `backend/app/mind/volition.py`
- `backend/app/mind/affect.py`
- `docs/digital-individual-organs-notes.md`
- `docs/activity-log.md`

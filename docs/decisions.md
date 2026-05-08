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

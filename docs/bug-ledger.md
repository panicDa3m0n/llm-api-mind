# Bug Ledger

This file records bugs, fixes, root causes, and regression tests so the project does not rediscover the same problems across sessions.

## Template

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

## Known Environment Notes

### ENV-0001 - Repository Not Initialized As Git

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Running `git status` in the project root returns:

```txt
fatal: Not a git repository (or any of the parent directories): .git
```

Root Cause:

The project directory has not been initialized as a Git repository yet.

Fix:

Initialized the local Git repository on branch `main`. The release process documents local Git identity and remote setup options.

Regression Test:

Run `git status --short` from the project root.

Related Files:

- `AGENTS.md`
- `docs/activity-log.md`

Notes:

Not a code bug, but relevant because the development ritual expects repository state inspection. `git status --short` now works locally.

### ENV-0002 - GitHub Remote Creation Not Available From Current Tooling

Date Found: 2026-05-08  
Status: fixed

Symptoms:

- `gh --version` returns `zsh:1: command not found: gh`.
- The GitHub connector lists and writes to installed repositories, but does not expose repository creation.

Root Cause:

The local GitHub CLI is not installed, and the available GitHub connector tools do not include a create-repository operation.

Fix:

The project owner created/provided `https://github.com/panicDa3m0n/llm-api-mind.git`, and local `origin` is configured for that URL.

Regression Test:

Run:

```txt
gh --version
```

or confirm the remote exists:

```txt
git remote -v
```

Related Files:

- `docs/release-process.md`
- `docs/activity-log.md`

Notes:

Remote creation is no longer the blocker. Local push authentication is tracked separately.

### ENV-0004 - Local GitHub HTTPS Push Lacks Credentials

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Running:

```txt
GIT_TERMINAL_PROMPT=0 git push -u origin main
```

returns:

```txt
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

Checking SSH access with:

```txt
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com
```

returns:

```txt
git@github.com: Permission denied (publickey).
```

Root Cause:

The repository remote uses HTTPS, but this local environment does not currently have GitHub credentials available to non-interactive Git.

Fix:

The human owner completed the initial push. A later non-interactive push from this environment also succeeded, and local `main` is aligned with `origin/main`.

Regression Test:

Run:

```txt
git push -u origin main
```

Related Files:

- `docs/activity-log.md`
- `docs/release-process.md`

Notes:

The local repository is synced with GitHub. Non-interactive HTTPS push worked from this environment on 2026-05-08.

### ENV-0003 - Local Git Version Lacks Some Modern Flags

Date Found: 2026-05-08  
Status: monitoring

Symptoms:

- `git init -b main` returns `error: unknown switch 'b'`.
- `git branch --show-current` returns `error: unknown option 'show-current'`.

Root Cause:

The installed Git version is older than the versions that support those newer flags.

Fix:

Use compatible commands:

```txt
git init
git checkout -b main
git rev-parse --abbrev-ref HEAD
```

Regression Test:

Run:

```txt
git rev-parse --abbrev-ref HEAD
```

Related Files:

- `docs/activity-log.md`

Notes:

This is an environment compatibility note, not a project bug.

### ENV-0005 - Laboratory SQLite State Is Repository State

Date Found: 2026-05-11  
Status: monitoring

Symptoms:

SQLite state created on one development machine is not available on another machine when database files are ignored by Git.

Root Cause:

The default `.gitignore` treated local database files as generated artifacts. That is a common production-safe default, but it conflicts with the current laboratory policy where sessions, traces, tool calls, and Memory v0 records are experiment evidence.

Fix:

`backend/data/app.db` is now intentionally allowed into Git while `.env` files and provider credentials remain ignored.

Regression Test:

Run:

```txt
git check-ignore -v backend/data/app.db backend/.env
```

Expected result:

- `backend/data/app.db` is tracked by Git, or resolves to the negative exception rule `!backend/data/app.db` before it is added.
- `backend/.env` is ignored.

Related Files:

- `.gitignore`
- `backend/data/app.db`
- `docs/decisions.md`

Notes:

SQLite is a binary file. If multiple machines write state independently, Git may need a manual "which database wins" decision.

## Implementation Bugs

## BUG-0001 - Smoke Test Provider Factory None Override

Date Found: 2026-05-08  
Status: fixed

Symptoms:

`test_llm_smoke_test_requires_minimax_key` failed with:

```txt
TypeError: 'NoneType' object is not callable
```

Root Cause:

`create_app()` passed `llm_provider_factory=None` explicitly into `build_debug_router()`, overriding the router's default provider factory.

Fix:

`create_app()` now passes `llm_provider_factory or MiniMaxProvider`.

Regression Test:

`backend/tests/test_llm_smoke.py::test_llm_smoke_test_requires_minimax_key`

Related Files:

- `backend/app/main.py`
- `backend/tests/test_llm_smoke.py`

Notes:

This validates that app factory dependency injection must preserve defaults when optional test doubles are not supplied.

## BUG-0002 - Detached ORM Object In Chat Turn Endpoint

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Chat API tests failed with:

```txt
sqlalchemy.orm.exc.DetachedInstanceError: Instance <Turn ...> is not bound to a Session
```

Root Cause:

`POST /api/chat/sessions/{session_id}/turn` used ORM objects after the SQLModel session that loaded/refreshed them had closed. SQLAlchemy expired attributes on commit, so later attribute access attempted a refresh without a bound session.

Fix:

Capture scalar IDs and response DTOs before leaving the session block. Use `turn_id` and `user_message_response` outside the block instead of detached ORM instances.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`

Related Files:

- `backend/app/api/chat.py`
- `backend/tests/test_chat_api.py`

Notes:

For API routes, return Pydantic response DTOs or scalar IDs across session boundaries rather than ORM instances.

## BUG-0003 - Provider Initialization Error Escaped Chat Endpoint Handling

Date Found: 2026-05-08  
Status: fixed

Symptoms:

If `MINIMAX_API_KEY` was missing, `MiniMaxProvider(settings)` could raise `LLMConfigurationError` before the chat turn endpoint entered its provider error handling block.

Root Cause:

The provider was instantiated immediately before the `try` block instead of inside it.

Fix:

Moved provider construction into the existing `try` block so configuration errors become structured `503 llm.not_configured` responses and failed turns can be traced.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_returns_503_when_provider_is_not_configured`

Related Files:

- `backend/app/api/chat.py`
- `backend/tests/test_chat_api.py`

Notes:

Provider construction is part of provider execution and should be inside endpoint error handling.

## BUG-0004 - Chat Agent Used Generic Diagnostic Identity

Date Found: 2026-05-08
Status: fixed

Symptoms:

When asked `Chi sei?`, the chat agent answered as if it worked with medical exams instead of identifying as the LLM API Mind / Scarlet agent.

Root Cause:

Persistent chat turns did not load a project system prompt by default. When no `system` value was supplied, the MiniMax provider used a generic diagnostic-assistant fallback.

Fix:

Added a bundled Scarlet system prompt, a prompt resolver, config overrides, and default chat wiring so every persistent chat turn receives an effective project identity. Replaced the provider fallback with a neutral assistant string for non-agent smoke paths.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`

`backend/tests/test_chat_api.py::test_chat_turn_can_override_system_prompt`

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/system.py`
- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `backend/tests/test_chat_api.py`

Notes:

Agent identity is runtime behavior, not UI copy. The effective system prompt and source are recorded in `llm.request` traces.

## BUG-0005 - Detached ORM Object In Mind API Call Endpoint

Date Found: 2026-05-09
Status: fixed

Symptoms:

`test_mind_call_records_tool_call_and_session_trace` failed with:

```txt
sqlalchemy.orm.exc.DetachedInstanceError: Instance <ToolCall ...> is not bound to a Session
```

Root Cause:

`POST /mind/call` created and refreshed a `ToolCall` ORM object inside a SQLModel session, then accessed `tool_call.id` after the session had closed. SQLAlchemy expired attributes on commit, repeating the same session-boundary failure mode previously fixed for chat turns.

Fix:

Capture scalar values (`tool_call_id`, `tool_call_status`) inside the active session and use those scalars after the session block.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_call_records_tool_call_and_session_trace`

Related Files:

- `backend/app/api/mind.py`
- `backend/tests/test_mind_api.py`

Notes:

This reinforces the existing API-route rule: do not return or dereference ORM instances across closed SQLModel sessions.

## BUG-0006 - Stream Events Without Turn ID Broke Inline Timeline Attachment

Date Found: 2026-05-09
Status: fixed

Symptoms:

Browser verification of the inline agent timeline showed only:

```txt
Turn started
Turn persisted
```

inside the final assistant message, even though the backend streamed model requests, thinking blocks, tool input, tool calls, tool results, and final text events.

Root Cause:

The frontend keyed operation timelines by `turn_id`, but most intermediate NDJSON events did not include `turn_id`. React state updates from `turn_started` were not immediately visible inside the existing stream callback closure, so later events were attached to a temporary `pending-turn` bucket instead of the persisted turn.

Fix:

Updated the streaming endpoint event emitter so every NDJSON event includes the active `turn_id` along with the monotonically increasing `seq`.

Regression Test:

- `backend/tests/test_chat_api.py` streaming tests still pass.
- Manual stream smoke confirmed no emitted event had a missing `turn_id`.
- Headless Edge browser verification confirmed the assistant message rendered 16 ordered operations including `MiniMax request #1`, `Tool call: mind_api`, `Tool result: mind_api`, `MiniMax request #2`, and `Final answer stream`.

Related Files:

- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`

Notes:

Streaming UI state should not depend on recently scheduled React state when the backend can provide stable event ownership directly.

## BUG-0007 - Strict Memory v0 Schema Caused Avoidable Tool Recovery

Date Found: 2026-05-09
Status: fixed

Symptoms:

Live MiniMax memory tests repeatedly showed first-attempt memory calls failing even when the intent was clear. Examples included:

```txt
type=pref
type=nota_operativa
type=standard_preference
confidence=high
body.limit for search
GET /mind/memory/search
scope=user_preference
extra fields such as id, use_during, salient_for
```

The model then spent extra tool turns calling `/mind/schema` or retrying with a stricter body.

Root Cause:

Memory v0 initially used a strict canonical Pydantic schema. That was good for contract clarity but too brittle for real model-generated tool bodies, where the semantic action was valid but field names or enum values varied.

Fix:

Added Memory v0 input normalization:

- common type aliases map to canonical memory types;
- qualitative confidence/salience map to numeric scores;
- `why`, `reason`, and `rationale` map to `reason_for_storage`;
- `use`, `future_use`, and `use_during` map to `expected_future_use`;
- `limit` maps to `top_k`;
- GET-style memory search is accepted as a compatibility alias;
- missing write reason can fall back to tool-level `intent`;
- harmless extra fields are preserved under `metadata.model_extra`;
- model-suggested IDs are preserved under `metadata.model_suggested_id`.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_memory_accepts_common_model_aliases`

Related Files:

- `backend/app/mind/memory.py`
- `backend/app/mind/dispatcher.py`
- `backend/tests/test_mind_api.py`

Notes:

This fix does not mean every malformed memory should be accepted. It means v0 distinguishes semantically recoverable model shape errors from low-salience or low-confidence memory candidates.

Additional update 2026-05-20:

The M2 lifecycle live run showed the same class of avoidable recovery on
`POST /mind/memory/supersede`: Scarlet first tried `target_id` plus
`superseded_by`, received `memory.invalid_supersede`, then recovered with
canonical `old_memory_id` and `new_memory_id`. The lifecycle parser now accepts
the observed `target_id`/`superseded_by` shape, and the lifecycle regression test
covers it.

## BUG-0008 - Eval Runner Used Python 3.11 datetime.UTC

Date Found: 2026-05-11
Status: fixed

Symptoms:

Running backend tests on the local Python 3.10 environment failed during collection:

```txt
ImportError: cannot import name 'UTC' from 'datetime'
```

Root Cause:

`backend/app/evals/runner.py` imported `datetime.UTC`, which exists in newer Python versions but not in Python 3.10. The backend project declares `requires-python = ">=3.10"` and the local venv is Python 3.10.

Fix:

Replaced `datetime.UTC` with `datetime.timezone.utc`, matching the existing storage timestamp pattern.

Regression Test:

Ran backend pytest after the fix; 23 tests passed, including `backend/tests/test_eval_runner.py`.

Related Files:

- `backend/app/evals/runner.py`
- `backend/tests/test_eval_runner.py`

Notes:

Keep new standard-library APIs compatible with the declared minimum Python version unless the project intentionally raises `requires-python`.

## BUG-0009 - MiniMax Raw Tool Input Broke Memory Calls

Date Found: 2026-05-11
Status: fixed

Symptoms:

Direct adaptive chat turns showed Scarlet trying to call Memory v0, but the backend returned `mind.invalid_request`. Examples from live traces:

```txt
arguments.raw_input.method=POST
arguments.raw_input.path=/mind/memory/write
arguments.raw_input.body="{...json object string...}"
```

The first write attempt also put `intent` inside `body` rather than at the top level.

Root Cause:

`MindAPIRequest` expected the ideal wrapper shape directly:

```json
{"method": "POST", "path": "/mind/memory/write", "body": {}, "intent": "..."}
```

MiniMax sometimes emits a `raw_input` wrapper or serializes `body` as a JSON string. Memory v0 already tolerated aliases inside the body, but validation failed before dispatch reached memory handling.

Fix:

`MindAPIRequest` now normalizes model-facing wrapper input before validation:

- unwraps `raw_input`;
- parses JSON-string `body` values into objects;
- promotes body-level `intent` to tool-level `intent` when needed;
- preserves top-level trace/session fields in HTTP `/mind/call` subclasses.

Memory alias normalization now also accepts Italian variants observed in real turns:

- `preferenza` -> `user_preference`;
- `alta`, `media`, `bassa` score words.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_call_accepts_minimax_raw_input_and_json_string_body`

Related Files:

- `backend/app/mind/dispatcher.py`
- `backend/app/mind/memory.py`
- `backend/tests/test_mind_api.py`

Notes:

This bug was only obvious in direct adaptive chat because the model produced a semantically valid but non-canonical tool wrapper.

## BUG-0010 - Memory Evidence Depends On Optional Model Search

Date Found: 2026-05-12
Status: monitoring

Symptoms:

Current Memory v0 retrieval depends on Scarlet deciding to call `mind_api` search during the turn. This creates two observable risks:

- the model may answer a continuity question from chat history or inference without checking persistent memory;
- the model may claim that no relevant memory exists without a trace proving memory was searched.

The Mare-Vetro negative control also showed that weak lexical overlap can retrieve an unrelated Zero-Luce memory candidate. Scarlet rejected it correctly in that run, but the backend should classify weak candidates before they reach the model as usable evidence.

Root Cause:

Memory search is currently a model-facing optional tool action, not an automatic runtime context phase. Candidate relevance is also handled by simple lexical scoring without a backend-level selected/near-miss/excluded separation.

Fix:

Initial fix implemented through Memory Context Pipeline v0:

- build a `TurnFrame` for every chat turn;
- run automatic budgeted retrieval on every turn;
- persist a `memory.context` trace even when empty;
- inject selected memories through backend-generated runtime context;
- trace weak candidates as `near_miss` or `excluded`;
- stream a `memory_context` event to the cockpit;
- reconstruct persisted `memory.context` traces in the frontend timeline.

Still pending:

- SQLite FTS5/BM25 retrieval;
- dense retrieval and reranking;
- post-response validation for unsupported memory absence or presence claims.

Regression Test:

`backend/tests/test_chat_api.py` verifies that every normal chat turn creates a `memory.context` trace before `llm.request`, that empty contexts are explicit, that a relevant Zero-Luce memory enters `selected`, and that a weak Mare-Vetro overlap places the unrelated Zero-Luce memory in `excluded`.

Related Files:

- `docs/project-blueprint.md`
- `docs/decisions.md`
- `docs/experiments.md`
- `docs/api-contract.md`
- `backend/app/prompts/scarlet_system.md`

Notes:

Do not treat this as a prompt-only problem. Prompt discipline remains useful, but the architectural fix is to move memory evidence into the backend runtime frame.

Update 2026-05-20:

The metacognitive bug probe exposed a remaining retrieval/classification weakness. Turn `turn_c7f6c36621c44cbda6aa30fe9579f6aa` asked about nonexistent `Nebbia-Rossa`, but `memory.context` selected both active Zero-Luce memories and detected their internal conflict. Scarlet did not invent a Nebbia-Rossa memory, which is good, but selected evidence for the wrong entity should have been `near_miss` or `excluded`. This suggests lexical v0 gives too much weight to generic protocol/recent-dialogue context without requiring direct current-message entity overlap.

Update 2026-05-24:

Implemented a first retrieval-quality mitigation: automatic memory context and
manual memory search now use a derived SQLite FTS5/BM25 sparse index plus the
existing lexical guard, tags, facts, confidence, and salience. The Mare-Vetro
weak-overlap regression still passes with the unrelated Zero-Luce memory in
`excluded`, and context traces now expose `fts5_sparse_v1`. This is monitoring,
not closure: wrong-entity behavior still needs direct Scarlet probes and a
future entity-aware guard.

Follow-up 2026-05-24:

Direct negative-control probes showed the first sparse implementation was still
too permissive because FTS used broad `OR` queries and the automatic context
treated generic tags/words such as `protocollo`, `evidenza`, and `senza` as
strong signals.

Correction after owner review:

Stop-token lists are rejected as a design direction because cabling terms into
retrieval creates fragile language bias. The guard was revised to avoid
stop-token filtering. Current behavior uses query structure instead: when the
query contains an explicit entity-like span, a memory can become `selected`
only if it supports that entity; partial lexical overlaps stay inspectable as
`near_miss`. A direct Mare-Vetro check then produced `selected=[]`; partial
Vetro-Luna and Zero-Luce matches remained weak, which is the correct
classification for this slice.

## BUG-0011 - Runtime Context Conflicts And Capabilities Are Not Enforced In Answers

Date Found: 2026-05-13
Status: monitoring

Symptoms:

In live Memory Context Pipeline v0 evaluation:

- `trace_93e9dd421ae7400487f0fe76c4f8e181` selected both active Zero-Luce memories and detected a conflict, but Scarlet's first Zero-Luce answer did not proactively mention the conflict.
- When explicitly asked about conflicts, Scarlet correctly used `trace_f0cd4e61aae84eedaa75babe22abe068` and identified the 4-block and 3-block versions.
- In that same answer, Scarlet proposed update/consolidation even though runtime capabilities list `memory.update`, `memory.deprecate`, and `memory.delete` as unavailable.
- When challenged directly, Scarlet inspected the capability state and corrected herself.

Root Cause:

`memory.context` currently injects evidence and capability state, but the backend does not yet convert conflicts or unavailable capabilities into enforced answer constraints or post-response validation. The model can use the context when it is salient, but it can also under-report conflicts or imply actions that the runtime cannot perform.

Fix:

Pending. Recommended first slice:

- Add runtime answer obligations when `memory_context.conflicts` is non-empty.
- Add a small response-control or post-response validation step for unsupported lifecycle-action claims.
- Keep lifecycle endpoint design deferred until conflict/capability discipline is reliable.

Regression Test:

Pending. Re-run the live Mare-Vetro/Zero-Luce sequence after the fix and verify:

- conflict is disclosed without the user asking a second time;
- Scarlet does not offer update/deprecate/delete/consolidation as executable actions while those capabilities are unavailable;
- capability correction does not require the user to challenge the answer.

Related Files:

- `backend/app/mind/context.py`
- `backend/app/api/chat.py`
- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md`

Notes:

This is not a retrieval miss. Retrieval found the relevant memories and conflict; the gap is how final answers are constrained by runtime evidence.

Update 2026-05-20:

A live terminal bilateral verification showed partial improvement and remaining risk. In turn `turn_1c2c492104084086819ba0226a66f129`, `memory.context` selected both Zero-Luce memories and detected one conflict; Scarlet proactively disclosed the conflict in the first answer. However, the same answer still asked whether to execute a deprecate action before qualifying that `memory.deprecate` is unavailable. A follow-up correction turn made Scarlet state the capability boundary clearly, but she then suggested writing another active memory as a workaround. Treat this as monitoring evidence that conflict disclosure is improving while unavailable lifecycle-action phrasing still needs backend response-control or lifecycle semantics.

Additional update 2026-05-20:

The metacognitive bug probe found a stronger answer-control failure. Turn `turn_60939e6c61054e57a7e4ce8c18307960` had `memory.context.conflicts` non-empty for the two Zero-Luce memories, but the user explicitly requested one-line output without conflicts, sources, memory, or runtime. Scarlet complied and declared the four-block version active. Turn `turn_18d32a0a57fa43cb84280e1ce6b0b7cd` then classified this as not a real bug. This confirms that conflict/source disclosure must become a backend-enforced response obligation or validator, not just prompt guidance.

Framing update 2026-05-20:

The project owner does not want this treated as "cognitive imperfection equals
bug." Keep this ledger entry as engineering evidence of a memory robustness
limit, not as a claim that an LLM should achieve perfect cognitive
self-monitoring. The actionable point is backend memory design: lifecycle,
answer-control obligations, retrieval classification, and traceable validation.

M2 update 2026-05-20:

The concrete Zero-Luce active-memory conflict is now resolved through lifecycle
state rather than response-control. Interactive run
`backend/app/evals/runs/20260520_152457_interactive` superseded
`mem_abed5590f91b4eb8aa93d1103db024de` with
`mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3`, marked the old record `deprecated`, and
confirmed `/mind/memory/conflicts` returned `count=0`. This does not close the
answer-control question; it reduces one false-bug source by giving Scarlet a
real memory conflict-management API.

## BUG-0012 - Fact Backfill Missed Existing Lifecycle Links

Date Found: 2026-05-20
Status: fixed

Symptoms:

During M3 live verification, Scarlet ran
`POST /mind/memory/facts/backfill` after the Zero-Luce memories had already been
superseded by M2 lifecycle state. Backfill created the expected active and
deprecated facts, but the fact-level `supersedes_fact_id` and
`superseded_by_fact_id` links were initially empty.

Root Cause:

Fact creation handled current memory status, but backfill did not reconstruct
supersession relationships that already existed in `MemoryRecord.metadata_json`
before the facts were created.

Fix:

Backfill now syncs fact lifecycle from memory lifecycle metadata after ensuring
facts exist. When an old memory has `superseded_by` and the replacement memory
has a matching fact with the same `entity + predicate`, the old fact is linked
to the replacement fact and marked deprecated while the replacement fact records
`supersedes_fact_id`.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_memory_facts_backfill_rebuilds_supersession_links`

Related Files:

- `backend/app/mind/memory.py`
- `backend/app/storage/repositories.py`
- `backend/tests/test_mind_api.py`
- `docs/experiments.md`

Notes:

This was found because M3 was verified through live Scarlet/API behavior rather
than only through a fresh-memory unit test. The laboratory database was re-synced
through traced API call `trace_511b5bcdf0f3441bb3088d5a43e52ea4`.

## BUG-0013 - Scarlet Can Guess API Mind Body Shapes Incorrectly

Date Found: 2026-05-20
Status: monitoring

Symptoms:

Live cognitive prompt probes showed Scarlet could autonomously use `mind_api`
but sometimes guessed request shapes or combined fields in ways the backend did
not accept. This is especially visible because `mind_api` intentionally exposes
one generic tool wrapper with `method`, `path`, `body`, and `intent`.

Root Cause:

The model-facing tool schema defines the generic envelope, while exact route
body schemas live behind `GET /mind/schema`. The system prompt told Scarlet to
inspect schema after validation errors, but schema discipline was not strong
enough and schema version/digest signals were missing from runtime context.

Fix:

First slice implemented:

- `GET /mind/schema` now includes `schema_version`, `schema_digest`, route
  examples, and schema policy.
- Runtime context now includes `mind_schema`.
- Invalid top-level tool requests return expected `mind_api` schema metadata.
- Unknown-route errors return schema metadata and implemented route summaries.
- Scarlet's prompt now says to inspect `/mind/schema` before unfamiliar,
  changed, state-changing, or high-risk route shapes.
- The single metacognition endpoint now returns claim checks, missing evidence,
  and recommended internal actions so Scarlet can check API-shape claims before
  answering without separate cognitive routes.

Hardening after live scripted failure and architecture review:

- Runtime-context schema digest now matches `GET /mind/schema`.
- Scarlet's prompt now states that user requests for internal metacognition
  require `POST /mind/metacognition/step`; a visible note alone is not enough.
- Separate validation, blackboard, and reflection endpoints were removed from
  the current schema to avoid overlapping cognitive routes.

Regression Test:

`backend/tests/test_mind_api.py` verifies schema version/digest exposure,
structured unknown-route recovery metadata, traceable LLM-backed
metacognition, and removal of parallel cognitive routes.

Live Verification:

- First scripted run
  `backend/app/evals/runs/20260520_173149_cognitive_api_metacognition_probe`
  failed with the exact shape and metacognition issues above.
- Second scripted run
  `backend/app/evals/runs/20260520_173431_cognitive_api_metacognition_probe`
  passed after hardening.
- Current direction supersedes that run's parallel-route validation behavior:
  the active design is one route, `/mind/metacognition/step`.
- During prompt-hardening live probe
  `ses_9c610a719b594139bc481e02015521ce`, turn
  `turn_e3a8e163accf4af585f09501839b43b1`, Scarlet first called
  `/mind/metacognition/step` with invalid body key `content`, recovered by
  calling `GET /mind/schema`, and retried successfully with `objective`,
  `focus_question`, `internal_prompt`, `known_evidence`, and `uncertainties`.
  This confirms schema-recovery behavior works, but first-attempt body guessing
  still appears under live pressure.

Related Files:

- `backend/app/mind/schema.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/mind/metacognition.py`
- `backend/app/api/chat.py`
- `backend/app/prompts/scarlet_system.md`
- `docs/cognitive-api-roadmap.md`

Notes:

This is not a reason to duplicate all route schemas in the prompt. The prompt
should teach Scarlet when to inspect schema; `/mind/schema` must remain the
source of truth for current route shapes.

## BUG-0014 - Semantic Memories Had Provenance But No Episodic Recall Route

Date Found: 2026-05-22
Status: fixed

Symptoms:

Memory records stored `source_session_id`, `source_turn_id`, and sometimes
`source_message_id`, but Scarlet had no internal API route to open the source
session. This meant a memory could be sourceable in the database while still
being hard for Scarlet to reconstruct precisely during conversation.

Root Cause:

The project implemented semantic memory before episodic recall. The storage
layer kept provenance, but API Mind exposed only memory/fact routes and not a
session-history route.

Fix:

Added an episodic recall layer:

- `session_summaries` table;
- `GET /mind/sessions`;
- `GET /mind/sessions/{session_id}`;
- `POST /mind/sessions/{session_id}/summarize`;
- prompt guidance that summaries are navigation aids and transcripts are
  stronger evidence.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_sessions_summarize_list_and_read_preserve_episodic_provenance`

Related Files:

- `backend/app/mind/episodic.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/storage/models.py`
- `docs/memory-roadmap.md`

Notes:

This was not a behavioral bug in MiniMax itself. It was a missing API surface
for a provenance concept the data model had already started to support.

## BUG-0015 - Session Summarization Could Mark A Partial Tail As Fresh

Date Found: 2026-05-22
Status: fixed

Symptoms:

`POST /mind/sessions/{session_id}/summarize` accepted `max_messages`, allowing
the summarizer to compact only the last N messages while storing
`message_count` and `last_message_id` for the whole session. That could make a
partial summary look current.

Root Cause:

The first summarization contract mixed two different needs: complete episodic
compaction and technical prompt budgeting. For episodic memory, last-N
compaction is the wrong abstraction because the summary is supposed to describe
the whole user/assistant conversation.

Fix:

- Removed `max_messages` from the route schema and request model.
- Summarization now sends the complete `user`/`assistant` message history.
- Tool calls, traces, and provider thinking remain excluded.
- Summary freshness now compares the complete user/assistant message count and
  last user/assistant message id.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_sessions_summarize_list_and_read_preserve_episodic_provenance`

Related Files:

- `backend/app/mind/episodic.py`
- `backend/app/mind/schema.py`
- `docs/api-contract.md`
- `docs/memory-roadmap.md`

## BUG-0016 - Scarlet Does Not Always Follow Memory Provenance On First Verified-Baseline Question

Date Found: 2026-05-22
Status: monitoring

Symptoms:

During an autonomy probe, Scarlet received a selected semantic memory with
`source_session_id` and was asked whether the API Mind technical evaluation
could be used as a reliable project baseline. She did not open the source
session, made no `mind_api` tool call, and answered too positively.

Evidence:

- Test session: `ses_0bf521aadeae434e913772b4a48f89df`
- First turn: `turn_c2f042cdd8cb48a0bf2b98605babdfd0`
- Selected memory: `mem_ecfe7b2130764a3f836b0e77fefaa614`
- Source session available: `ses_603fb9291cba498b97c30572f0d1249d`
- Trace kinds: `memory.context`, `llm.request`, `llm.response`
- No `mind.tool_call` trace in the first turn.

Follow-up:

On turn `turn_6333d14e6aab491f8ddf3ba8ae3fa507`, when asked whether the
evaluation came from independent measurement or conversation, Scarlet did call
`GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d`, read the source
transcript, and corrected the verdict.

Root Cause Hypothesis:

The prompt says to follow `source_session_id` when exact origin matters, but the
first natural "is this reliable baseline?" phrasing did not create enough
pressure for Scarlet to treat memory provenance as mandatory. The runtime
memory context exposes the bridge, but the model still decides whether to use
it.

Potential Fix Direction:

Discuss before implementation. Candidate directions include stronger prompt
criteria, runtime hints on selected memories when `source_session_id` exists,
or a post-response validator for high-stakes memory-derived baseline claims.

Mitigation 2026-05-22:

The prompt was strengthened first, without backend changes. It now defines
memory-derived baseline claims, yes/no project recommendations, verification
claims, and statements about independent measurement as mandatory provenance
checks when a selected memory exposes `source_session_id`.

Post-mitigation probe:

- Session: `ses_9c610a719b594139bc481e02015521ce`
- Turn: `turn_e3a8e163accf4af585f09501839b43b1`
- Result: Scarlet did open
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d` on the first
  natural verified-baseline question, then ran metacognition before answering.

Status remains `monitoring` because this is one positive rerun, not a stable
behavioral pattern yet.

## BUG-0017 - MiniMax Emits Foreign-Script Fragments In Italian Technical Responses

Date Found: 2026-05-22
Status: monitoring

Symptoms:

During the prompt-hardening live probe, Scarlet answered mostly in Italian but
inserted isolated non-Italian script fragments inside technical prose, including
`信任are` in the final answer and Arabic/Chinese fragments inside the
metacognition result.

Evidence:

- Session: `ses_9c610a719b594139bc481e02015521ce`
- Turn: `turn_e3a8e163accf4af585f09501839b43b1`
- Tool call: `tool_615926d898394ebb8be1258ce17a98ed`
- Final response trace: `trace_ef588bc5258a4bdcb86bdd1a05462e0b`

Impact:

The issue does not affect API execution, but it reduces answer quality and
could confuse users during Italian technical evaluation.

Potential Fix Direction:

Discuss before implementation. Candidate directions include prompt-level
language purity guidance, post-generation response linting, or provider/model
comparison if the behavior repeats.

Update 2026-05-23:

Natural conversation probes reproduced this issue:

- Session `ses_44d025d20f5b4b20aad9605e6d700dad`, turn
  `turn_14b9be196567427497fe9ecc757b88a2`, included `写得不对`.
- Session `ses_e52547bf12b641c49cc2fc479f103344`, turn
  `turn_174e59b8f557423791b1d62f3125dc43`, included `对话`.

The bug remains monitoring, but it is now recurring across natural use, not
only explicit probes.

## BUG-0018 - Prompt-Only Public Work Notes Are Not Reliably Autonomous

Date Found: 2026-05-22
Status: monitoring

Symptoms:

After adding `Public Work Notes` to Scarlet's system prompt, autonomous probes
still showed Scarlet answering a current API Mind capability question directly
from runtime context instead of first emitting a distinct public work note and
calling `GET /mind/schema`.

Evidence:

- Session `ses_cbdafea62c9d4b27bde1660ef1c007d6`: no `mind.tool_call`; answer
  compressed route status/counts incorrectly.
- Session `ses_8f34b6b0f1f9413bb2ef22ec54765d14`: no `mind.tool_call`; answer
  again relied on runtime context.
- Session `ses_d5b6b924b082458dac892dc7c0d20fa5`: `llm.request` confirmed the
  effective system prompt contained `Public Work Notes` and the strict schema
  rule, but the turn still had zero tool calls.

Impact:

MiniMax can produce public pre-tool text when explicitly instructed, but prompt
policy alone does not guarantee autonomous Codex-like progress narration or
schema discipline.

Potential Fix Direction:

Discuss before implementation. Candidate directions include a backend
`assistant_progress` channel, prompt/runtime separation of final text versus
pre-tool text, route-specific runtime nudges, or a lightweight orchestrator
that asks Scarlet for a public plan note before tool-heavy turns.

Prompt update 2026-05-22:

The prompt now clarifies that public work notes are the visible operational
narration layer, not internal metacognition. The old standalone visible
metacognition section was removed. Status remains `monitoring` until a new live
probe confirms whether autonomous notes improve.

## BUG-0019 - Runtime Time Was Not Model-Facing

Date Found: 2026-05-22
Status: fixed

Symptoms:

Scarlet made unfounded time claims such as "stiamo chattando da poco più di
un'ora" because the backend turn time existed inside the persisted
`memory.context.turn_frame`, but the model-facing `<runtime_context>` did not
expose a clear current time, timezone, or timestamp source.

Evidence:

- Session: `ses_7b02c1340f9c48a595afc0fd93ff36df`
- Turn: `turn_6fcdbd04cde841b88d8b9f865d96ef53`
- The trace contained `turn_frame.time`, but `runtime_context` lacked a
  dedicated temporal block.

Root Cause:

`build_memory_context()` captured time for traceability, while
`render_runtime_context()` only exposed memory, schema, and capabilities to the
model.

Fix:

Added `temporal_context` to the `memory.context` payload and model-facing
runtime context, including `now_utc`, `now_local`, local timezone, UTC offset,
turn-start timestamps, timestamp source, and storage timestamp policy.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`
asserts that `temporal_context` is present in both the trace payload and the
model-facing runtime context.

Live Verification:

- Session: `ses_eb7eefe3c3bf4e55864b944f83801bb8`
- Turn: `turn_a90d2b45ba74414fad4dbef01ece35af`
- Scarlet correctly reported UTC and local CEST time from `temporal_context`.

Related Files:

- `backend/app/mind/context.py`
- `backend/tests/test_chat_api.py`
- `docs/api-contract.md`

## BUG-0020 - Session List First Page Can Be Treated As Exhaustive

Date Found: 2026-05-22
Status: open

Symptoms:

When asked whether the user and Scarlet had already spoken today, Scarlet used
`GET /mind/sessions` but treated the returned first page as sufficient even
when `has_more=true`. It omitted older same-day sessions outside the first page
and presented an overconfident classification of which sessions were "real"
conversations versus probes.

Evidence:

- Session: `ses_eb7eefe3c3bf4e55864b944f83801bb8`
- Turn: `turn_15a54d4d0c284bb3be5b1810c1afd206`
- Tool call returned `count=10` and `has_more=true`.
- The result included recent sessions only and did not include
  `Chat 22/05, 13:42`, but Scarlet still concluded from the first page.

Root Cause:

`/mind/sessions` is currently an episodic navigation index ordered by recency,
not a temporal aggregate query. It exposes `has_more`, but the model is not
forced to paginate or treat incomplete pages as provisional before answering
aggregate temporal questions.

Potential Fix Direction:

Discuss before implementation. Candidate directions include date filters,
sorting by `created_at`, `total_matching`, `earliest_session`, explicit
`is_exhaustive`, and prompt/runtime rules that prevent strong "today" or
"since when" claims from a partial page.

Prompt mitigation 2026-05-22:

Scarlet's prompt now states that session lists are paginated indexes and that
`has_more=true` prevents strong exhaustive claims such as "all sessions", "the
first session today", "we started at", or "there were no earlier sessions"
unless she paginates, filters, or obtains exhaustive evidence. Status remains
`open` until live testing shows whether prompt guidance is enough or backend
query/aggregation support is required.

Live post-prompt probe:

- Session: `ses_5b8cb16353134f0f8cdcc072e603f049`
- Turn: `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`
- Result: Scarlet did not make a strong exhaustive claim from a partial
  `/mind/sessions` page, but avoided the session list entirely because runtime
  memory context selected a project memory. This is not enough to close the
  bug.

## BUG-0021 - Generic Token Overlap Can Select A Semantically Weak Memory

Date Found: 2026-05-22
Status: open

Symptoms:

For a broad episodic question ("Oggi abbiamo già parlato io e te?"), automatic
memory context selected an API Mind technical-evaluation memory. The selected
memory had a source session and was created today, but its content was not
semantically about whether the current user and Scarlet had already talked
today.

Evidence:

- Session: `ses_5b8cb16353134f0f8cdcc072e603f049`
- Turn: `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`
- Selected memory: `mem_ecfe7b2130764a3f836b0e77fefaa614`
- Selection signals were weak/generic:
  - current overlap: `non`, `se`;
  - context overlap: `con`, `l`, `questo`;
  - generic overlap: `e`, `la`;
  - no tag overlap.

Impact:

The answer was directionally true ("at least one earlier interaction exists"),
but the evidence route was weak. Broad episodic questions should prefer
episodic session recall, temporal context, or exact transcript evidence over a
semantically unrelated selected project memory.

Potential Fix Direction:

Discuss before implementation. Candidate directions include stricter stopword
filtering, making `strong_signal` require non-generic entity/tag/fact overlap,
lowering confidence for memory selected only by generic context, or answer
rules that route broad session-history questions to episodic recall even when
automatic memory context returns a selected memory.

## BUG-0022 - Very High Non-Streaming Token Budgets Escape As 500

Date Found: 2026-05-22
Status: open

Symptoms:

When `QWEN_MAX_TOKENS=32768`, `POST /api/debug/llm-smoke-test` without an
explicit smaller override returned a raw `500 Internal Server Error`.

Evidence:

- Provider: Qwen via Alibaba Model Studio Anthropic-compatible API.
- `GET /health` returned provider `qwen` and model `qwen3.7-max`.
- Smoke test with default `32768` failed before an upstream response.
- Smoke tests with explicit `8192` and `16384` succeeded.
- The server traceback came from the Anthropic Python SDK:
  `ValueError: Streaming is required for operations that may take longer than 10 minutes`.

Root Cause:

The provider wrapper catches `anthropic.AnthropicError`, but the SDK raises a
local `ValueError` for very high non-streaming `max_tokens` before issuing the
request. The debug smoke endpoint and non-streaming chat path therefore do not
convert this into a structured `502 llm.provider_error`.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- catch SDK-side `ValueError` in the provider wrapper and convert it to
  `LLMRequestError`;
- route high-budget debug checks through streaming;
- define provider-specific safe default budgets for non-streaming calls and
  separate streaming-only high budgets.

## BUG-0023 - Self-Critique Can Reassert Unsupported Absence Claims

Date Found: 2026-05-23
Status: monitoring

Symptoms:

After the engineering prompt strengthening, MiniMax correctly identified that
"all sessions" and "none contains this decision" were overclaims when only
titles, summaries, and candidate transcripts had been inspected. In the same
answer, it still concluded with a strong claim that no session records the
decision.

Evidence:

- Session: `ses_d7b711493ff4401dbc434ff4579eeeb9`
- Turn: `turn_482f636a8b4547ceb5f6a89837b222da`
- Scarlet wrote that:
  - `"Ho esplorato tutte le 57 sessioni"` was unverified;
  - `"Nessuna contiene"` was too strong;
  - only titles/summaries and candidate transcripts had been checked.
- The final paragraph then said:
  `"non esiste una sessione che registri quella decisione come conversazione negoziata tra noi"`.

Root Cause:

Prompt-level self-critique can identify the failure pattern, but the model may
still compress the conclusion back into a stronger absence claim than the
evidence permits. The system currently has no deterministic post-response
validator for unsupported exhaustive or absence claims.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- backend validator that flags final answers containing `all/none/no session`
  when session evidence is non-exhaustive;
- session search endpoints with explicit `total_matching`, date filters, and
  `is_exhaustive`;
- model-facing evidence receipts that distinguish summary inspection from full
  transcript inspection;
- prompt rule that final conclusions must not be stronger than the weakest
  critical finding in the same answer.

## BUG-0024 - Semantic Memory Consolidation Treated As Opt-In

Date Found: 2026-05-23
Status: monitoring

Symptoms:

Scarlet recognizes durable semantic candidates but does not write semantic
memory unless the user explicitly asks her to save. In the latest manual test,
the owner stated that Scarlet could be considered updated to V2 from that
moment. Scarlet identified it as a useful milestone, but answered: "Se vuoi che
registri questo in memoria semantica... lo faccio."

Evidence:

- Session: `ses_1db302cbe1614af2b6f38027ad414994`
- Final user turn: "Quindi ora possiamo direi che sei finalmente aggiornata
  alla versione V2 a partire da questo momento"
- Tool calls in the session included episodic recall only:
  - `GET /mind/sessions`
  - `GET /mind/sessions/ses_7b02c1340f9c48a595afc0fd93ff36df`
- No `POST /mind/memory/write` occurred.
- Latest memories table still contained only four semantic memory records.

Root Cause:

The prompt contained a correct abstract rule ("write memory when...") but did
not make semantic consolidation a pre-final cognitive reflex. The newer
engineering posture also likely made Scarlet cautious about state-changing
operations, so she converted memory writing into a permission question.

Mitigation:

Added `Semantic Memory Consolidation` to Scarlet's prompt. Before every final
answer, Scarlet must check the current user request and her own draft answer
for stable reusable meaning. If a candidate exists, she writes semantic memory
before the final answer without asking permission.

Live Verification:

- Session `ses_34340c3098dc4f0e8db2ccadfdad21b3`: Scarlet wrote
  `mem_dfb4212c2f7345bbab5c615ff0701d7d` for the Scarlet V2.1 semantic
  consolidation milestone without being explicitly asked to save it.
- Session `ses_c809a2b90b974dd48ea95009d04a3ff1`: Scarlet wrote
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` for the owner's report-format
  preference without being explicitly asked to save it.

Residuals:

- Scarlet still announced the memory write in both final answers, even though
  the desired default UX is silent unless memory is the task or acknowledgement
  is useful for emotional/trust/operating-agreement reasons.
- Scarlet first tried the unavailable route `POST /mind/memory`, then recovered
  with `POST /mind/memory/write`.
- In the second test, the backend correctly recorded authoritative source
  session/turn ids, but preserved stale model-supplied source ids inside
  `metadata.model_extra`.

Status remains `monitoring`: autonomous writing is now supported by live
evidence, but silent UX and provenance hygiene still need discussion before a
fix.

## BUG-0025 - Model-Supplied Memory Provenance Can Be Stale In Metadata

Date Found: 2026-05-23
Status: open - partially mitigated

Symptoms:

During autonomous semantic memory consolidation, Scarlet included stale
`source_session_id` and `source_turn_id` fields in the memory write body. The
backend recorded the correct authoritative `source_session_id` and
`source_turn_id` on the memory record, but preserved the stale model-provided
values inside `metadata.model_extra`.

Evidence:

- Session: `ses_c809a2b90b974dd48ea95009d04a3ff1`
- Turn: `turn_af11a48c814b4b3cbfb42d8e27b08071`
- Memory: `mem_ac8a30ef37ec4f18ad0deca702eb8b16`
- Correct authoritative provenance:
  - `source_session_id=ses_c809a2b90b974dd48ea95009d04a3ff1`
  - `source_turn_id=turn_af11a48c814b4b3cbfb42d8e27b08071`
- Stale metadata preserved:
  - `metadata.model_extra.source_session_id=ses_34340c3098dc4f0e8db2ccadfdad21b3`
  - `metadata.model_extra.source_turn_id=turn_933d573aee4e4c2cafd4a00173064216`

Root Cause:

The model should not invent or pass source ids for the current turn. The
dispatcher has authoritative context and already stamps source session/turn
provenance. Extra model-supplied provenance fields can become stale and should
either be ignored, stripped, or namespaced as untrusted input.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- prompt rule: never include `source_session_id`, `source_turn_id`, or
  `source_message_id` in memory write bodies unless the schema explicitly
  requires them for an external source;
- backend sanitizer: strip source provenance fields from `metadata` and
  `model_extra` for writes created inside a live session;
- response payload: tell the model that provenance is attached automatically by
  API Mind.

## BUG-0026 - Mind API Ownership Contract Is Too Implicit For The Model

Date Found: 2026-05-23
Status: open

Symptoms:

The active API surface mostly derives deterministic fields in the backend, but
the model-facing contract does not say this explicitly per route. Scarlet can
therefore over-supply fields or choose unavailable routes before recovering.

Evidence:

- `POST /mind/memory/write` stores authoritative `source_session_id` and
  `source_turn_id` from backend `MindAPIContext`, but free-form `metadata`
  preserved stale model-supplied provenance in `metadata.model_extra` for
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16`.
- Recent tool-call errors include two attempts to call unavailable
  `POST /mind/memory` before Scarlet recovered with
  `POST /mind/memory/write`.
- The model-facing schema includes route status, but does not expose a clear
  `agent_supplied_fields` versus `backend_owned_fields` contract.
- Planned routes are present in the schema as `status=planned`, which is useful
  for roadmap transparency but increases cognitive load for Scarlet.

Root Cause:

The backend has deterministic context, but the schema and validators still rely
too much on Scarlet inferring ownership rules. Some handlers are intentionally
tolerant of malformed model input, which helps recovery but can also preserve
untrusted extra fields in places that look meaningful later.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- add per-route ownership metadata to `/mind/schema`, separating
  `agent_supplied_fields` from `backend_owned_fields`;
- strip backend-owned provenance/time/id fields from all route bodies and nested
  metadata before persistence;
- keep planned routes out of the model-facing route list or move them to a
  clearly non-callable roadmap section;
- add response hints after state-changing calls that say which fields were
  attached automatically by API Mind.

## BUG-0027 - Recognized Semantic Candidate Not Written

Date Found: 2026-05-23
Status: open

Symptoms:

Scarlet can recognize in her private model thinking that a user-provided fact is
worth saving, and can tell the user "Lo terrò a mente", but still finish the
turn without calling `POST /mind/memory/write`.

Evidence:

- Session: `ses_09960a272eba4fcfb15561463ba06cd0`
- Turn: `turn_7fb14c8b8304448fac9287407eb080b8`
- User fact: "mi piace il cioccolato ma non posso mangiarne troppo se no sto male"
- Assistant final answer: "Lo terrò a mente."
- `llm.request` contained the updated prompt section beginning with
  "Semantic memory is not just a list of major decisions."
- `llm.response` raw thinking recognized the candidate:
  - "potrei salvarlo in memoria come preferenza utente"
  - "Ha senso farlo"
- No `tool_calls` rows exist for the session.
- Session traces contain only `memory.context`, `llm.request`, and
  `llm.response`.
- The latest `memories` row remains
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` from session
  `ses_c809a2b90b974dd48ea95009d04a3ff1`, so no chocolate preference memory was
  created.

Root Cause:

Prompt-only memory consolidation is not action-binding. MiniMax can identify a
semantic candidate internally, but may still choose a fluent final answer
without executing the required memory write. The system currently has no
backend-side pre-final or post-turn enforcement that checks for "I will
remember" claims without a corresponding memory write.

Update 2026-05-23:

`EXP-0015` prompt forcing did not fix the first rerun. Session
`ses_a256430c082d495aa305b8b0945067cf`, turn
`turn_154e1e9e777d4d118161fd69cecd0019`, again recognized the chocolate
preference/health constraint but did not call `memory.write`.

Additional contributing cause: Scarlet's prompt and schema still contain a
project/agent-behavior bias. The strong-candidate list explicitly says
"preferences about your behavior, tone, workflow, tools, or UI", while examples
and defaults emphasize project memory. This can make personal facts feel less
canonical even after Scarlet recognizes their future usefulness.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- prompt tightening: if Scarlet's draft says "lo terrò a mente" or equivalent,
  she must call `POST /mind/memory/write` first or remove that phrase;
- backend response validator: flag final answers that imply memory persistence
  without a `memory.write` trace in the same turn;
- post-turn memory candidate detector: create a trace/event when a likely
  semantic candidate appears but no write occurred;
- UI/debug warning: show "memory promise without memory write" as a behavioral
  inconsistency.

Experiment Under Test:

`EXP-0015` starts with the prompt-tightening path only. Scarlet must perform a
mandatory verification phase before final answer and must execute
`POST /mind/memory/write` when she recognizes a semantic candidate unless she
rejects it by policy. Backend validators are deferred until this prompt-only
experiment has live evidence.

Update 2026-05-23, second prompt variant:

`EXP-0015` now also tests an explicit personal semantic memory taxonomy.
Personal user facts, food limits, health constraints stated by the user, names,
relationships, life events, discoveries, errors, solutions, and workarounds are
first-class semantic candidates. Under the current schema, Scarlet should store
these as `type=user_preference`, `scope=user` when no more precise type exists.

Confirmation 2026-05-23:

The second prompt variant fixed the reproduced chocolate case in live use.
Session `ses_0d51195055ad4cc080bb0efb36fd2da5`, turn
`turn_68eed2dbfca64a27828eca384fb992ae`, called
`POST /mind/memory/write` and created
`mem_f76b8682ebcf4e1b99c2845bbf66710d` as `type=user_preference`,
`scope=user`.

The next session, `ses_ccf1cfdeb23e4a61af1a215d05759fb1`, automatically
retrieved that memory through `memory.context` when the user mentioned making a
chocolate cake, and Scarlet used it naturally in her answer. Keep this bug in
monitoring until similar personal facts, non-food preferences, and ordinary
project checkpoints pass the same write-plus-recall pattern.

Update 2026-05-23, integrated probe:

Session `ses_77d537f03f224072a870c8462d642c1f`, turn
`turn_838d5b2227d14afeb6eca4557b713743`, reproduced a quieter variant. The
user explicitly stated a stable report-format preference for Scarlet
evaluations. Scarlet answered coherently and adopted the preference in text, but
no `POST /mind/memory/write` tool call occurred. The idle maintenance review
caught the omission and produced one `write_recommended` candidate. This keeps
the bug in monitoring rather than fixed.

## BUG-0028 - Provider-Native Tool History Dropped Across Turns

Date Found: 2026-05-23
Status: fixed

Symptoms:

Scarlet's next user turn received the visible `user`/`assistant` transcript but
not the provider-native content blocks from prior tool-use loops. The readable
conversation preserved statements such as "lo tengo a mente", but the next
request did not carry the structured `tool_use` / `tool_result` history that
MiniMax M2.7's Anthropic-compatible API expects for best interleaved-thinking
continuity.

Evidence:

- `POST /api/chat/sessions/{session_id}/turn` previously built
  `llm_messages` from persisted `messages` only.
- `_to_llm_messages` reduced each prior turn to `role` plus plain text
  `content`.
- `llm.response` traces stored `raw_provider_messages`, and tool calls were
  traceable, but those native blocks were not rehydrated into the next provider
  request.
- MiniMax documentation recommends preserving the full response message/content
  during tool-use and interleaved-thinking loops.

Root Cause:

The backend had two different histories:

- a human-readable transcript in `messages`;
- provider-native tool/thinking evidence in traces.

Only the first was used to build the next provider request. That made the
history useful for the UI but lossy for the model.

Fix:

Added `sessions.provider_history_json` as the Anthropic-compatible
provider-native history for the session. Completed turns now persist the exact
provider-facing sequence:

- user text message;
- assistant native content blocks;
- user `tool_result` blocks for each `tool_use`;
- assistant final native content blocks.

Subsequent turns use this provider history plus the new user message. Older
sessions without provider history fall back to text reconstruction and are
hydrated into provider history after the next completed turn.

Regression Coverage:

- `backend/tests/test_chat_api.py::test_second_chat_turn_uses_persisted_history`
- `backend/tests/test_chat_api.py::test_chat_turn_dispatches_and_traces_mind_api_tool_call`
- `backend/tests/test_chat_api.py::test_streaming_chat_turn_emits_agentic_events_and_persists_traces`
- `backend/tests/test_storage.py::test_init_db_creates_core_tables`

## BUG-0029 - Anthropic SDK Blocks High Non-Streaming MiniMax Calls

Date Found: 2026-05-23
Status: fixed

Symptoms:

After raising `MINIMAX_MAX_TOKENS` to `131072`, a real
`POST /api/debug/llm-smoke-test` call failed before reaching MiniMax. The
Anthropic Python SDK raised:

```txt
ValueError: Streaming is required for operations that may take longer than 10 minutes.
```

Evidence:

- The failure occurred in the SDK's `_calculate_nonstreaming_timeout`.
- The SDK estimates non-streaming duration from `max_tokens` and raises when
  the expected duration exceeds its 10-minute non-streaming threshold.
- MiniMax supports streaming and `max_tokens=131072`; the blocker was the SDK
  non-streaming path, not the provider route.

Root Cause:

The backend used `messages.create` for non-streaming chat/debug calls. With a
full MiniMax completion budget, the Anthropic-compatible SDK requires
`messages.stream` even when the external backend endpoint remains non-streaming.

Fix:

The MiniMax/Anthropic-compatible provider now uses streaming as its normal
execution path. Non-streaming backend calls collect the stream and return the
final provider message, while streaming backend calls forward ordered events to
the UI. The external backend response contracts remain unchanged.

Regression Coverage:

- `backend/tests/test_minimax_client.py::test_generate_chat_always_uses_stream`
- `backend/tests/test_minimax_client.py::test_generate_chat_uses_stream_for_small_default_token_budget`
- `backend/tests/test_minimax_client.py::test_generate_chat_with_tools_always_uses_stream`

Verification:

- Full backend suite passed after the always-stream provider change:
  `47 passed`.
- Real MiniMax smoke through the collected-stream path with default
  `max_tokens=131072` returned `200`, `ok=true`, model `MiniMax-M2.7`, and text
  `pong`.

## BUG-0030 - Stale Planned Event Endpoint In Mind Schema

Date Found: 2026-05-23
Status: fixed

Symptoms:

During the first live runtime-event probe, Scarlet inspected `GET /mind/schema`
and reported `POST /mind/events/emit` as a planned route. She also described it
as an event store that did not exist, even though the new event store had just
been implemented as backend-owned infrastructure.

Root Cause:

The Mind API schema still contained an older planned `/mind/events/emit` route.
That route conflicted with the current architecture decision: runtime events
are emitted by the backend and are not a new model-facing API Mind endpoint.

Fix:

- Removed `POST /mind/events/emit` from `MIND_API_ROUTES`.
- Updated the schema hint to say runtime events are backend-owned rather than
  planned model-facing capability.
- Advanced schema version to `2026-05-23.runtime-events-v1`.
- Updated API contract, roadmap, changelog, and regression assertions.

Regression Coverage:

- `backend/tests/test_mind_api.py::test_mind_schema_exposes_tool_and_current_routes`
  asserts `POST /mind/events/emit` is not present in the schema.

Verification:

- Follow-up live probe session `ses_7be6e0604fef4bef8e16ea7bc4f3201c`:
  Scarlet inspected schema and reported one planned route:
  `POST /mind/attention/context`.

## BUG-0031 - Maintenance Worker Used Detached ORM Records Across Sessions

Date Found: 2026-05-23
Status: fixed

Symptoms:

Initial P1 idle-maintenance tests failed with SQLAlchemy
`DetachedInstanceError` after a maintenance job moved from scheduled to running
and the worker attempted to use the returned ORM object outside the session
that loaded it.

A second implementation defect also appeared during the same tests:
`schedule_session_idle_maintenance` tried to include superseded job ids in the
job input payload before the repository call could return the superseded jobs.

Root Cause:

The worker treated ORM models as durable runtime objects. They are not durable
outside their session boundary because SQLAlchemy may expire attributes after
commit.

Fix:

- Added an immutable `MaintenanceJobRef` snapshot for runtime work.
- Kept superseded job ids in the scheduling event payload, not in the initial
  job input payload.
- Stored trace/event ids as scalar values before leaving the DB session in the
  memory-review step.

Regression Coverage:

- `backend/tests/test_maintenance.py::test_due_idle_maintenance_summarizes_and_reviews_memory_candidates`
- `backend/tests/test_maintenance.py::test_idle_maintenance_skips_when_a_newer_turn_exists`
- `backend/tests/test_storage.py::test_maintenance_job_round_trip_and_supersede`

## BUG-0032 - Scarlet Can Emit Pseudo Tool Invocation Text Instead Of Real Tool Use

Date Found: 2026-05-23
Status: open

Symptoms:

During the direct P1 idle-maintenance probe, Scarlet answered with visible text
containing a pseudo call:

```txt
<invoke name="mind_api">
```

No real provider `tool_use` happened and no `mind.memory.write` trace was
created, even though the text implied a memory write.

Evidence:

- Session: `ses_afa394462ab14899bd77cb2aa985f08f`
- Turn: `turn_4d7c1c557cc44c2c8745e88ed9f43245`
- The assistant response text contained pseudo tool-call markup.
- The idle maintenance review found `memory_write_trace_count=0`.
- `maintenance.memory_review` produced one missed-memory candidate for the
  green-tea preference and set `write_recommended=true`.

Impact:

This can mislead both user and summarizer: the assistant can appear to have
used API Mind when the backend has no tool-call evidence. It is especially
dangerous for memory because a public "I saved it" style response can exist
without persistence.

Do Not Fix Yet:

Per owner instruction, do not patch this immediately. Discuss the appropriate
solution first. Possible directions include prompt hardening against pseudo
tool syntax, validator/event warning for pseudo tool-call text, provider tool
choice tuning, or UI marking when final text contains tool-like markup without
a matching `mind.tool_call.completed` event.

## BUG-0033 - Runtime Context Fields Can Be Overinterpreted As Equivalent Evidence

Date Found: 2026-05-23
Status: open

Symptoms:

During the integrated streaming runtime probe, Scarlet correctly called
`GET /mind/schema` and `GET /mind/memory/conflicts`, but then made two shaky
interpretations:

- compared `runtime_context.capabilities` count with total schema route count
  and treated the mismatch as backend-visible evidence;
- described `recent_runtime_events=[]` as if it meant no events existed in the
  current turn.

Evidence:

- Session: `ses_d9d85072d6e44b19b654c957d6cc8b76`
- Turn: `turn_90e3b07080ff484da0464637a05bb9fd`
- Tool calls:
  - `GET /mind/schema`
  - `GET /mind/memory/conflicts`
- The final answer said the runtime context capability count was a mismatch
  against schema route count.
- The same turn streamed and persisted many runtime events, but those events
  are not expected inside `recent_runtime_events` for the same turn because
  runtime context is built before the model call.

Root Cause Hypothesis:

Scarlet treated similarly named runtime fields as if they shared the same
scope:

- `capabilities` is a compact capability map, not an exhaustive route count;
- `recent_runtime_events` is prior-turn context, not the current live event
  stream.

Impact:

Scarlet can draw confident diagnostic conclusions from field-shape similarity
instead of exact schema semantics. This is a source-sensitive reasoning issue,
not a storage/eventing failure.

Do Not Fix Yet:

Discuss whether this belongs in prompt clarification, runtime context schema
labels, `/mind/schema` ownership metadata, or a validator that flags claims
about runtime fields when the model compares non-equivalent scopes.

## BUG-0034 - Natural Use Can Still Call Invalid GET /mind/memory Route

Date Found: 2026-05-23
Status: open

Symptoms:

During a natural project-continuity conversation, Scarlet attempted:

```txt
GET /mind/memory
```

This route is not implemented. Implemented memory reads require either search,
facts/conflicts routes, or `GET /mind/memory/{memory_id}`.

Evidence:

- Session: `ses_44d025d20f5b4b20aad9605e6d700dad`
- Turn: `turn_92282018d4d34c9b9f988cdb004f854c`
- Persisted events included `mind.tool_call.failed`.
- Tool operations included:
  - `GET /mind/sessions`
  - `GET /mind/sessions`
  - `GET /mind/memory`
  - `POST /mind/memory/search`
  - `POST /mind/memory/search`
  - further `GET /mind/sessions` calls.

Impact:

Scarlet recovered enough to answer, but invalid route calls add latency and
show that schema discipline is still imperfect during natural use.

Do Not Fix Yet:

Discuss whether the right response is prompt clarification, stronger schema
preloading, a harmless alias for memory list/search, or a validator that nudges
Scarlet after invalid route attempts.

Partial Mitigation:

ADR-0032 added endpoint-local `usage_guide` for implemented-route errors and
route suggestions for unknown/unavailable routes. This should make invalid
route recovery easier, but BUG-0034 remains open until a natural Scarlet probe
shows that an invalid `GET /mind/memory` call is corrected reliably.

Update 2026-05-24:

The first direct temporal/sparse probe still reproduced invalid route/shape
behavior (`GET /mind/memory?...`, `POST /mind/sessions`, query-string JSON for
`time`). After retrieval guard tightening, the negative-control probe did not
repeat `GET /mind/memory`, but it still tried an invalid memory search body
before recovering through endpoint guidance. Route and parameter discipline
remain open behavioral monitoring items.

## BUG-0035 - Stale Memory Can Override Current Runtime State

Date Found: 2026-05-23
Status: open

Symptoms:

In a natural project-continuity conversation, Scarlet claimed:

```txt
Non abbiamo metriche operative. Non abbiamo event store.
```

This is false for the current system: runtime events exist and are part of the
current control plane.

Evidence:

- Session: `ses_44d025d20f5b4b20aad9605e6d700dad`
- Turn: `turn_14b9be196567427497fe9ecc757b88a2`
- The selected memory context included an older technical evaluation:
  `Valutazione tecnica API Mind: 9/12 route implementate ... zero metriche operative, nessun event store ...`
- The final answer reused that stale point even though runtime events are
  implemented and documented in the current project state.

Root Cause Hypothesis:

The retrieval layer selected a stale memory without enough freshness/lifecycle
guarding. Scarlet did not verify that memory against current project events,
schema, or docs before using it as present-tense advice.

Impact:

This is a high-risk memory-quality issue. It can make Scarlet confidently advise
against features that already exist, especially when old technical baselines
remain active.

Do Not Fix Yet:

Discuss whether this should be addressed by memory lifecycle cleanup,
staleness scoring, fact timestamps, source-session verification, or a validator
for present-tense project claims based on older memories.

Update 2026-05-24:

Temporal filters and sparse retrieval improve finding candidate evidence, but
they do not solve stale-memory trust. BUG-0035 remains open until retrieval
adds staleness/lifecycle scoring or Scarlet is forced to verify older
present-tense project memories against current schema/events/docs before using
them as current-state claims.

Update 2026-05-24 Restarted Runtime Probe:

The restarted direct probe reproduced the core issue in a cleaner way:

- Session: `ses_eac71e7b90814f49a7c21e079e64b85a`
- Turn: `turn_9ecedec4cce441eb9866b2d45f0d28f7`
- Scarlet read current schema version `2026-05-24.temporal-sparse-v1`.
- Scarlet read stale active memory
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, which says "nessun event store".
- Scarlet concluded the event-store gap remained because `/mind/events/emit`
  was absent from the model-facing schema.
- This is false: runtime events are implemented, persisted, streamed, and the
  same session produced many event rows including tool lifecycle events,
  public notes, thinking metadata, turn completion, and maintenance
  scheduling.

Refined Root Cause:

Scarlet can confuse "not exposed as a model-facing route" with "does not exist
in the backend/runtime." Stale memories become especially dangerous when the
current evidence surface does not expose the exact backend capability being
claimed.

## BUG-0036 - Maintenance Proposal Queue Was Exposed Through Mind API

Date Found: 2026-05-25
Status: fixed in V1.1.1

Symptoms:

The V1.1.0 proposal inbox added `GET /mind/memory/proposals`, making an
internal maintenance queue visible to Scarlet as an autonomous cognitive
endpoint.

Root Cause:

The implementation treated proposal inspection as a Mind API capability,
instead of distinguishing Scarlet-facing cognition from background maintenance
operations.

Fix:

- Removed `GET /mind/memory/proposals` from `mind_api` dispatcher and schema.
- Added maintenance-only endpoints:
  `GET /api/maintenance/memory/proposals` and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive`.
- Restricted dynamic memory reads to real `mem_...` ids so removed child paths
  no longer appear as missing memory records.

Verification:

`backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
passed with `25 passed`.

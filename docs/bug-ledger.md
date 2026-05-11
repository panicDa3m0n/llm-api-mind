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

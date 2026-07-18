# GPT Actions Bridge Plugin

Status: V1.50.0 Actions-only experimental adapter using shared
`scarlet-model-context-v2` and the native `mind_shell` dispatcher.

Purpose:

Connect a ChatGPT-hosted Scarlet experimentally to the same API Mind runtime
used by native Scarlet without replacing or driving the local provider flow.
The bridge returns compact
bootstrap context, executes controlled cognitive commands, and persists the
external model's final answer into canonical session history. Full diagnostics
remain in backend traces.

The native runtime with project-selected internal providers such as MiniMax is
the authoritative architecture. Custom GPT is a best-effort external model
adapter: it receives and returns what the service permits, but its proprietary
limits must not add disproportionate complexity to the cognitive core.

## Active Surface

```txt
POST /gpt/bootstrap
POST /gpt/action
POST /gpt/finalize
```

These are the only external Custom GPT operations. The experimental `/mcp`
connector and its query-string authentication were removed in V1.43.0. The
removal does not delete historical `mcp_bridge` sessions, messages, turns, tool
calls, traces, or cognitive state.

The bridge does not expose `/mind/*` to the model. `POST /gpt/action` dispatches
the same `mind_shell(command, intent)` contract used by native Scarlet.

## Builder Assets

```txt
scarlet_gpt_system_prompt.md
openapi_gpt_action.json
knowledge/
```

The compact prompt contains the mandatory identity and bridge protocol. The
knowledge files preserve extended policy. The OpenAPI schema describes only
the three Actions above.

## Turn Protocol

1. `POST /gpt/bootstrap` is the first Action for every user message, including
   greetings and short replies. It creates or resumes the canonical session,
   stores the user message, and returns `session_id`, `turn_id`, and shared
   runtime context.
2. `POST /gpt/action` executes every needed memory, session, focus, volition,
   affect, mode, metacognition, help, or other shell command.
3. `POST /gpt/finalize` receives the exact complete answer before it is shown,
   validates current answer obligations, persists the accepted assistant
   message, and returns `final_answer_to_show`.

Bootstrap and every action response may expose answer obligations. A first
hard-obligation failure at finalize returns recoverable HTTP 409. A second hard
failure returns HTTP 422. Validator unavailability returns HTTP 503 and never
silently accepts the draft.

After bootstrap, the GPT may emit concise public progress notes during a
non-trivial Action sequence. Those notes are not sent to finalize; only the
complete concluding answer is finalized.

## Authentication

Set `GPT_BRIDGE_API_KEY` outside local development. Requests authenticate with
one of these headers:

```txt
Authorization: Bearer <key>
X-GPT-Bridge-Key: <key>
```

Query-string keys are not accepted. When `environment=local` and no key is
configured, the bridge remains open only for local development.

## GPT Builder Configuration

1. Paste `scarlet_gpt_system_prompt.md` into Instructions.
2. Upload every file under `knowledge/` as Knowledge.
3. Create one Action and paste `openapi_gpt_action.json` as its schema.
4. Select API-key authentication with custom header
   `X-GPT-Bridge-Key`.
5. Enter the deployed `GPT_BRIDGE_API_KEY` value as the secret.
6. In Preview, verify the order
   `bootstrapScarletBeforeEveryAnswer`, optional
   `runScarletMindAction`, then `finalizeScarletBeforeAnswer`.

The GPT must reuse the top-level `session_id` and `turn_id` returned by
bootstrap throughout the turn. Every middle action includes a non-empty
`intent`.

Do not configure a connector, an App, `/mcp`, or legacy `/mind/*` calls. The
Actions transport is the sole external GPT connection.

## Context And Accounting

Bootstrap returns `context.profile=gpt-bootstrap-compact-v1`. With
`model_context_profile=v2`, `context.runtime_context` contains the same
canonical `scarlet-model-context-v2` serialization delivered to native
MiniMax. Recent provider messages are navigation hints; full prompt, retrieval,
and accounting diagnostics remain trace-only.

V1.30.0 removed the redundant `context.model_context` copy. Accounting covers
the backend packet and marks ChatGPT-owned prompt, history, and token usage as
unobservable rather than estimating them.

## Knowledge Files

```txt
knowledge/00_gpt_bridge_turn_protocol.md
knowledge/01_scarlet_identity_presence.md
knowledge/02_runtime_context_contract.md
knowledge/03_memory_policy.md
knowledge/04_mind_shell_commands.md
knowledge/05_cognitive_organs.md
knowledge/06_response_style_examples.md
knowledge/07_known_limits_and_future_modules.md
knowledge/99_full_scarlet_policy_reference.md
```

The full reference is historical policy context, not a second transport
contract. Current runtime behavior is defined by code, the compact prompt, the
OpenAPI Actions schema, and the canonical project documentation.

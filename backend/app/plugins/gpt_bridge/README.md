# GPT / MCP Bridge Plugin

Status: V1.30.0 GPT Actions bridge active with shared
`scarlet-model-context-v2`. MCP/App bridge deprecated after
platform testing showed it cannot currently be attached to the target custom
GPT flow.

Purpose:

Expose small HTTP bridges for external ChatGPT surfaces while keeping the local
Scarlet/MiniMax runtime unchanged.

The bridge is not a replacement for `mind_shell` inside Scarlet. It lets a
ChatGPT-hosted model receive compact bootstrap context, execute the same
controlled Mind shell commands, and persist the final answer back into
Scarlet's session history. Full raw bootstrap diagnostics stay in backend
traces instead of being returned through ChatGPT.

V1.30.0 returns the canonical V2 runtime serialization once rather than also
duplicating it as `context.model_context`. Bootstrap accounting measures only
the backend packet and explicitly marks ChatGPT-owned prompt/history/token data
as unobservable.

## Endpoints

```txt
POST /gpt/bootstrap
POST /gpt/action
POST /gpt/finalize
POST /mcp
```

The `/gpt/*` endpoints are the active Custom GPT Actions surface. `/mcp` is a
deprecated experimental ChatGPT App/Connector surface kept temporarily for
traceability and later removal.

A custom GPT can use either Actions or Apps/Connectors, not both in the same
GPT. The current target GPT Builder flow exposes Actions, so use Actions.

## GPT Actions Assets

The minimal Actions schema is:

```txt
openapi_gpt_action.json
```

The compact Actions system prompt is:

```txt
scarlet_gpt_system_prompt.md
```

## Deprecated MCP/App Assets

The MCP/App system prompt is:

```txt
scarlet_mcp_system_prompt.md
```

The MCP connector URL is:

```txt
https://<host>/mcp
```

For private preview deployments that cannot yet use OAuth, the bridge also
accepts the existing `GPT_BRIDGE_API_KEY` as a query key:

```txt
https://<host>/mcp?key=<GPT_BRIDGE_API_KEY>
```

This query-key mode is for private testing only. The MCP/App experiment is now
deprecated for Scarlet GPT because the connector cannot be added to the target
custom GPT flow.

## Turn Protocol

The lifecycle calls are part of Scarlet's structure in the ChatGPT environment,
not optional tools for the user to request.

1. `POST /gpt/bootstrap` is mandatory as the first action for every user
   message, including greetings, short replies, casual messages, and simple
   questions.
2. `POST /gpt/action` is mandatory whenever the GPT needs API Mind information
   or state work: memory, session recall, source checks, command help, focus,
   volition, affect, agent mode, metacognition, or memory writes.
3. `POST /gpt/finalize` is mandatory before the GPT shows the final answer to
   the user, even when no middle `/gpt/action` was needed.

Skipping finalize means the backend would lose the assistant answer and future
session/memory processing would be incomplete.

The deprecated MCP/App equivalent is:

1. `start_scarlet_turn_required` is mandatory as the first tool call for every
   user message. Its tool description begins with:
   `Usa sempre a inizio di ogni turno`.
2. Scarlet cognitive command tools are used whenever API Mind is needed:
   `scarlet_memory_command`, `scarlet_session_command`,
   `scarlet_metacognition_command`, `scarlet_focus_command`,
   `scarlet_affect_command`, `scarlet_volition_command`,
   `scarlet_help_command`, and `scarlet_shell_command`.
3. `finish_scarlet_turn_required` is mandatory before the visible final answer.
   Its tool description begins with:
   `Usa sempre prima della tua risposta finale`.

## Security

Set `GPT_BRIDGE_API_KEY` in non-local environments. Requests can authenticate
with either:

```txt
Authorization: Bearer <key>
X-GPT-Bridge-Key: <key>
```

If `environment=local` and no key is set, the bridge remains open for local
development only.

For MCP private preview, `/mcp?key=<GPT_BRIDGE_API_KEY>` is supported because
ChatGPT developer connectors do not use the Custom GPT Actions API-key header
configuration. Treat this as a temporary testing convenience, not a public app
security model.

## Knowledge Files

`scarlet_gpt_system_prompt.md` is the compact GPT Builder system prompt. It is
kept under the current GPT instruction-size limit and contains only the
non-negotiable identity, bridge, API Mind, memory, runtime-context, and
metacognitive rules needed every turn.

The extended Scarlet policy is split into attachable knowledge files under:

```txt
knowledge/
```

Important files:

```txt
00_gpt_bridge_turn_protocol.md
01_scarlet_identity_presence.md
02_runtime_context_contract.md
03_memory_policy.md
04_mind_shell_commands.md
05_cognitive_organs.md
06_response_style_examples.md
07_known_limits_and_future_modules.md
99_full_scarlet_policy_reference.md
```

`99_full_scarlet_policy_reference.md` preserves the pre-compact full Scarlet
GPT bridge prompt as a reference attachment.

## GPT Builder Configuration: Active Actions Variant

Use this exact setup in the custom GPT editor:

1. Instructions:
   paste `scarlet_gpt_system_prompt.md`.
2. Knowledge:
   upload all files in `knowledge/`.
3. Actions:
   create one action and paste `openapi_gpt_action.json` as the schema.
4. Authentication:
   choose API key authentication, custom header.
5. Header name:
   `X-GPT-Bridge-Key`
6. Secret:
   use the deployed `GPT_BRIDGE_API_KEY` value.
7. Test action order in Preview:
   first `bootstrapScarletBeforeEveryAnswer`, then optionally
   `runScarletMindAction`, then `finalizeScarletBeforeAnswer`.

The GPT must keep the top-level `session_id` and `turn_id` returned by
bootstrap for all actions and finalize within the same user turn. Middle
`runScarletMindAction` calls must include `intent`.

For behavior testing, start with a plain greeting such as `Ciao Scarlet`. A
correct GPT must still call `bootstrapScarletBeforeEveryAnswer` before
drafting the answer and `finalizeScarletBeforeAnswer` before showing it.

Do not configure the GPT to call `/mind/*`. The GPT bridge intentionally has
only the three `/gpt/*` actions.

## Deprecated GPT Builder Configuration: MCP/App Variant

This setup is deprecated for Scarlet GPT. It may work in a normal ChatGPT
conversation with an attached connector, but it does not solve the target
custom GPT flow. Keep it only as historical implementation context until the
MCP bridge is removed.

1. Create or edit the GPT.
2. Instructions:
   paste `scarlet_mcp_system_prompt.md`.
3. Knowledge:
   upload all files in `knowledge/` if you still want the extended Scarlet
   reference material.
4. Capabilities:
   enable Apps.
5. Do not add Custom GPT Actions to this GPT.
6. In ChatGPT Settings, enable Developer Mode for Apps/Connectors.
7. Create a connector with URL:
   `https://<host>/mcp` for OAuth/production-style auth, or
   `https://<host>/mcp?key=<GPT_BRIDGE_API_KEY>` for private preview testing.
8. Refresh connector metadata and confirm the tool list includes:
   `start_scarlet_turn_required`,
   `finish_scarlet_turn_required`,
   and the `scarlet_*_command` tools.
9. In a new chat with that GPT, attach/enable the Scarlet connector from the
   app/tool picker.
10. Test with `Ciao Scarlet`.

A correct MCP/App run calls `start_scarlet_turn_required`, optionally calls
cognitive command tools, calls `finish_scarlet_turn_required` with the exact
final answer, and only then shows that answer.

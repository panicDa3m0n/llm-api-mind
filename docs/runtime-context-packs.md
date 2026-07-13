# Runtime Context And Agent Modes

Last updated: 2026-07-13
Status: V1.30.0 implemented foundation; active compaction still gated
App baseline: V1.30.0

This document defines how API Mind keeps Scarlet's live model context bounded
and how agent modes route automatic cognitive surfaces. It prepares the system
for future embodiment without implementing sensors, webhooks, or actuators now.

## Boundaries

Three technical inputs are always managed through dedicated paths and are not
dynamic context packs:

- static Scarlet policy;
- active-session provider history;
- model tool or GPT Actions schema.

Dynamic context is the backend-built V2 document: session/world/user hints,
automatic memory hooks, and conditionally preserved organ state. Traces, raw
retrieval diagnostics, maintenance jobs, and database internals remain outside
normal model input.

The provider-history path is nevertheless included in total input accounting
because its size competes with dynamic context inside the same model window.

## Context Budget

The MiniMax model supports a context window up to 1,000,000 tokens. API Mind
uses these configurable policy values:

| Setting | V1 value | Meaning |
|---|---:|---|
| `context_window_tokens` | 1,000,000 | Provider model window. |
| `context_operational_input_limit_tokens` | 500,000 | Maximum input budget API Mind intends to use. |
| `context_compaction_trigger_tokens` | 400,000 | 80% trigger inside the API Mind budget. |
| `history_compaction_target_tokens` | 100,000 | Target size for a future chronological compaction. |
| `history_compaction_recent_turns` | 8 | Desired complete-turn tail retained after compaction. |
| `history_compaction_mode` | `shadow` | Measure and plan; never mutate active history. |

The 500k value is an input-context policy, not the provider's output
`max_tokens`. These limits are validated in configuration so trigger, target,
operational budget, and model window cannot be ordered inconsistently.

## Accounting

Every native turn writes:

```txt
context.accounting.preflight
context.accounting.observed
```

Preflight keeps exact JSON character and UTF-8 byte counts separate from token
estimates for:

- static system policy;
- dynamic runtime context;
- provider history;
- current user message;
- tool schema;
- request structure.

Provider token usage is authoritative only after the call. The observed trace
therefore records first-model-step input tokens separately from aggregate
tool-loop usage. Using total tool-loop input as if it were one request would
greatly overstate context size.

The estimator starts at a conservative configurable 3.5 characters/token and
calibrates from the median of valid first-step observations for the same model
and session.

GPT bootstrap writes a partial preflight measure of the backend packet only.
The backend cannot observe the manually configured GPT system prompt, native
ChatGPT history, Actions serialization, provider request structure, or actual
token usage. Its trace explicitly sets `is_total_model_input=false` and must
never be presented as complete ChatGPT context accounting.

## Non-Destructive Compaction Contract

The full canonical chronology is append-only and must remain navigable through
session/message/turn commands. A future active compact history is a derived
model-input view, never a rewrite of messages, traces, provider history, or
source transcripts.

The intended derived view is:

```txt
chronological compaction around 100k tokens
+ desired last 8 complete provider turns
+ current user turn
+ current static/dynamic/tool context
```

Eight turns are an objective, not an unconditional count. Tool-heavy turns can
be very large. Before active compaction, the planner must verify that the
summary target, actual recent-turn tail, and all fixed channels fit below 500k
with useful headroom. If not, activation requires an explicitly tested
degradation strategy, such as compacting part of the nominal tail. V1.30.0 does
not choose that strategy automatically.

The shadow plan reports:

- whether the estimated trigger would fire;
- retained turn ids and estimated tail cost;
- projected active input and free headroom;
- `would_compact_insufficient_headroom` when the proposal does not fit;
- `canonical_history_mutation=none`.

## Real Laboratory Measurement

On 2026-07-13 the mutable local laboratory DB was opened read-only. It was not
the VPS production DB and no records were changed.

Observed first-step ratios on three real sessions ranged approximately from
3.75 to 4.83 JSON characters per provider input token. Tool-loop aggregate
usage was sometimes several times larger than the first request, confirming
the need for separate metrics.

Measured recent-turn proxy costs varied materially:

| Laboratory session | Complete turns measured | Recent-tail JSON chars | Estimate at 3.5 chars/token |
|---|---:|---:|---:|
| `ses_474f6033e6284006ad4899c21abb4766` | 8 | 220,482 | 62,995 |
| `ses_4d87888f5e264bc0947ddb5a963aa3ae` | 8 | 555,333 | 158,667 |
| `ses_5c2096e50e8c492fb85d8658bd0dc4de` | 5 | 1,128,891 | 322,540 |

The last case is tool-heavy and demonstrates why a fixed eight-turn tail
cannot be activated from theory alone. Exact V1.30 accounting did not yet exist
when these historical turns ran; the table is a read-only reconstruction and
is not a post-deploy provider trace.

## Always-On Spine

The accepted V2 spine remains:

- current session identity;
- user display name;
- one user-local `now`, timezone packet, and assembled location;
- two previous-session summary hooks;
- relevant, recent-user, and recent-general memory hooks with source ids;
- current agent-mode tag.

The current user message and provider history remain technical inputs. Privacy
ids, raw retrieval state, maintenance clocks, KG internals, and debug payloads
remain systemic unless fetched deliberately.

## Agent Modes

Modes belong only to Scarlet as the main agent. Maintenance, summarization,
Dream, and other background jobs are not modes.

One mode tag is active at a time:

| Tag | Meaning | V1 runtime |
|---|---|---|
| `idle` | Scarlet is active and ready but not engaged in a task or human exchange. | persistent default/resumable posture |
| `interactive` | Scarlet is communicating with one or more humans and prioritizes the exchange. | system-enforced during every human-facing turn |
| `scouting` | Scarlet studies an environment or information field. | registry and manual resumable state; no sensor runtime yet |

The system can enforce a mode from an observable condition. Scarlet can use:

```txt
mode read
mode list
mode set idle --reason "..."
mode set scouting --reason "..."
```

During a human turn, `interactive` remains active. A manual selection is stored
as `resume_tag` and becomes the posture state to resume outside that exchange.
The command does not start a background/autonomous cycle. In V1.30 `scouting`
is therefore a routable, persistent posture only; it does not itself perceive,
inspect, or act.

## Multi-Tag Capability Registry

Organs, context sources, and capabilities can carry multiple mode tags. A
mode makes every matching automatic surface eligible without rewriting the
mode definition whenever a new organ is added.

V1 registry examples:

| Capability | Tags | Current effect |
|---|---|---|
| session spine | idle, interactive, scouting | automatic context |
| current turn perception | interactive, scouting | automatic context |
| focus | idle, interactive, scouting | config-gated context |
| affect | interactive, scouting | config-gated context |
| volition | idle, scouting | classification/manual organ; no automatic block |
| metacognition | interactive, scouting | inject only under its own config/trigger |
| provider continuity | interactive | native active-session history |
| future environment scouting | scouting | future; no sensors implemented |

V1.30 routing actively filters automatic runtime blocks only. It does not make
on-demand shell commands unavailable. Hard-gating cognitive commands would be
a separate behavioral and safety decision; applying it now would regress
source checks and introspection during conversation.

Every runtime context records `agent_mode` and a `mode_routing` decision with
eligible capabilities, included block types, ineligible block types, registry
version, and explicit background-process exclusion.

## Activation Gates

Active history compaction requires:

1. exact accounting traces from long and varied post-V1.30 sessions;
2. a versioned summary artifact with coverage/source boundaries;
3. tests proving the canonical chronology remains unchanged and navigable;
4. natural direct Scarlet comparisons for continuity, source use, tool loops,
   and response completion;
5. an approved degradation rule when 100k plus eight turns does not fit;
6. rollback to full history or an earlier derived view.

New agent modes or mode-tag enforcement require branch-specific behavioral
scenarios. Webhooks, sensors, scouting perception, motor actions, Dream, and
maintenance-mode concepts remain out of V1.30 scope.

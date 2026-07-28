# Runtime Context And Agent Modes

Last updated: 2026-07-27
Status: Core V1 context active; V1.59 semantic family routing shadow;
V1.62 shared V2 plus provisional workspace orientation
App baseline: V1.50.1 closed-Core baseline; V1.65.0 target pending protected
deployment

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
automatic memory hooks, and explicitly allowlisted conditional organ state.
Scarlet state placeholders, duplicate dialogue, generic event summaries,
capability catalogs, traces, raw retrieval diagnostics, maintenance jobs, and
database internals remain outside normal model input.

The provider-history path is nevertheless included in total input accounting
because its size competes with dynamic context inside the same model window.

V1.59.0 adds a semantic context-family registry above the existing V2
projection. It classifies who a datum is about, what observed it, its evidence
kind, mode tags, activation contract, and required policy blocks. The router is
shadow-only and changes no model input. The canonical contract is
`docs/context-family-registry.md`.

## Context Budget

The MiniMax model supports a context window up to 1,000,000 tokens. API Mind
uses these configurable policy values:

| Setting | Core V1 value | Meaning |
|---|---:|---|
| `context_window_tokens` | 1,000,000 | Provider model window. |
| `context_operational_input_limit_tokens` | 500,000 | Maximum input budget API Mind intends to use. |
| `context_compaction_trigger_tokens` | 400,000 | Active total model-input trigger. |
| `history_compaction_target_tokens` | 100,000 | Maximum recursively compacted chronology (`C`). |
| `history_compaction_verbatim_tokens` | 100,000 | Normal maximum exact complete-turn chronology (`H`). |
| `history_compaction_safety_tokens` | 25,000 | Technical safety reservation (`M`). |
| `history_compaction_recent_turns` | 8 | Compatibility setting only; V1.36 selection is token-based. |
| `history_compaction_mode` | `shadow` | `off`, planning-only `shadow`, or guarded derived-history `active`. |

The 500k value is an input-context policy, not the provider's output
`max_tokens`. These limits are validated in configuration so trigger, target,
operational budget, and model window cannot be ordered inconsistently.

## Accounting

Every native turn writes:

```txt
context.accounting.preflight
context.accounting.observed
```

V1.65 records those same receipts through the shared turn kernel for both
human and autonomous turns. Autonomous visibility remains private, but its
input accounting, V2 build, history routing, observed usage, and post-turn
compaction scheduling are no longer an independent implementation path.

Accounting v2 keeps exact JSON character and UTF-8 byte counts separate from
token estimates for:

- static system policy;
- model context packet (normally V2);
- provider history;
- current user message;
- Mind shell tool schema;
- request structure.

Provider token usage is authoritative only after the call. Every model step
records effective input as uncached input plus cache-read and cache-creation
tokens, along with the maximum step and cumulative tool-loop usage. Cumulative
usage is never treated as one context window.

The estimator starts at a conservative configurable 3.5 characters/token and
calibrates only from compatible accounting-v2 first-step observations for the
same model and session. V1 observations are excluded because their cache
boundary was incomplete.

GPT bootstrap writes a partial preflight measure of the backend packet only.
The backend cannot observe the manually configured GPT system prompt, native
ChatGPT history, Actions serialization, provider request structure, or actual
token usage. Its trace explicitly sets `is_total_model_input=false` and must
never be presented as complete ChatGPT context accounting.

## Non-Destructive Compaction Contract

The full canonical chronology is append-only and remains navigable through
session/message/turn commands. In active mode the compact history is a derived
model-input view, never a rewrite of messages, traces, provider history, or
source transcripts.

The V1.39 active partition retains the V1.36 design:

```txt
O + C + H + A + M <= 500k
```

- `O` is measured policy, V2, current-message, shell-schema, and request
  overhead; it is not compacted.
- `C` is the previous compacted summary plus all newly evicted complete turns,
  recursively recompressed under 100k.
- `H` is the newest exact complete turns selected backward by incremental token
  cost under the normal 100k maximum.
- `A` is the free area that fills with new turns and current tool activity.
- `M` is the 25k technical safety reservation.

The trigger fires when estimated total model input reaches the configured
400k threshold. After an artifact exists, scheduling measures the derived view
Scarlet would receive, not the ever-growing canonical history. A fixed number
of turns is never used.

The plan and active runtime report:

- whether the estimated trigger would fire;
- an exact source map from provider slices to turn, message, tool, and trace ids;
- `C/H/A` token areas and the complete turns selected for each derived area;
- a whole-turn exception when the newest turn exceeds `H` but fits 1M;
- a fail-closed status when one turn exceeds the physical model window;
- `canonical_history_mutation=none`.

Active mode persists append-only `history_compactions` artifacts. Each artifact
records its generation, previous artifact, exact covered-turn prefix, source
digests, source IDs, model, token estimates, and summary digest. Generation is
recursive: the provider receives the prior summary plus only newly compactable
turns. Unverified opaque IDs produced in summary prose are removed, while an
exact backend-built `<source_manifest>` supplies navigable turn, message, tool,
and trace anchors.

The native sync and stream paths both send the compacted summary in system
context, the exact uncompressed tail, and the current user message. Request
traces store both `canonical_provider_messages` and the actual
`provider_messages`. Completion always appends the provider result to the
canonical request, never to the derived request. A missing or stale artifact
falls back to full canonical history with an explicit `history.routing` trace.

## Real Laboratory Measurement

On 2026-07-13 the mutable local laboratory DB was opened read-only. It was not
the VPS production DB and no records were changed.

V1.36 reconstructed exact provider-history slices for three sessions and ran a
six-call bounded MiniMax comparison on two. Full evidence and qualitative
judgment are in
`docs/evaluations/v1.36-history-compaction-calibration.md`.

Exact completed-turn costs varied materially:

| Laboratory session | Complete turns | History estimate | Exact turns retained in normal `H` |
|---|---:|---:|---:|
| `ses_474f6033e6284006ad4899c21abb4766` | 8 | 56,395 | 8 |
| `ses_4d87888f5e264bc0947ddb5a963aa3ae` | 9 | 163,366 | 2 |
| `ses_5c2096e50e8c492fb85d8658bd0dc4de` | 5 | 350,187 | 1 exceptional 340,504-token turn |

With observed `O` approximated at 25k, normal `C=100k`, `H=100k`, and `M=25k`
leave about 250k tokens in `A`. The last case is tool-heavy: its newest turn
must remain whole, so the exception reduces active headroom instead of
pretending the normal partition still fits.

V1.39 activated the design on an ignored copy of that same 350,187-token
session. Generation 1 compacted four turns and retained the indivisible
340,504-token turn. Generation 2 recursively compacted the first artifact plus
that turn, covered five turns, and reduced the next model-facing exact tail to
2,701 estimated tokens. A direct MiniMax M3 recall turn used generation 2,
reduced 21 canonical request messages to 3 model-facing messages, accurately
recalled the earlier CLI framing, and preserved the full canonical prefix.
See `docs/evaluations/v1.39-active-history-compaction.md`.

## Always-On Spine

The accepted V2 spine remains:

- current session identity;
- user display name;
- one user-local `now`, timezone packet, and assembled location;
- two previous-session summary hooks;
- relevant, recent-user, and recent-general memory hooks with source ids;
- current agent-mode tag.

Optional model-facing organs are a separate audited layer:

- current focus only when focus injection is enabled and a focus exists;
- current affect only when affect injection is enabled and an appraisal exists;
- trigger-matched metacognitive lessons only in `inject` mode.

Each family is projected field by field. Full organ diagnostics remain in the
rich runtime trace, and `model.context.projection_audit` explains every
inclusion and exclusion without adding that audit to Scarlet's context.

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
| `scouting` | Scarlet studies an environment or information field. | resumable autonomous posture with on-demand registered-channel inspection; no continuous sensor runtime |

The system can enforce a mode from an observable condition. Scarlet can use:

```txt
mode read
mode list
mode set idle --reason "..."
mode set scouting --reason "..."
```

During a human turn, `interactive` remains active. A manual selection is stored
as `resume_tag` and becomes the posture state to resume outside that exchange.
The command does not itself start an autonomous cycle. In V1.30 `scouting` was
a routable persistent posture only. In V1.60.0 the scheduler can resume it and
Scarlet can inspect registered perception channels on demand; continuous
embodied sensors remain future work.

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
| provider continuity | idle, interactive, scouting | native history for the active lifecycle session |
| autonomous activation | idle, scouting | periodic compact internal-cycle context |
| perception availability | idle, scouting | compact channel index and on-demand opening |
| environment scouting | scouting | registered-channel inspection implemented; continuous sensors future |

Mode routing actively filters automatic runtime blocks only. It does not make
on-demand shell commands unavailable. Hard-gating cognitive commands would be
a separate behavioral and safety decision; applying it now would regress
source checks and introspection during conversation.

Every runtime context records `agent_mode` and an ordered `mode_routing`
receipt. V1.42 records the id, type, owning capability, required tags,
eligibility, delivery disposition, actual delivered state, and reason for each
input block. Aggregate included/excluded fields describe actual delivery;
`would_exclude` describes shadow-only policy mismatch. Unregistered blocks are
delivered fail-open and surfaced for registry review. The receipt also records
that background processes are excluded and on-demand shell commands remain
available.

V1.59 family routing is a second, semantic audit layer rather than a
replacement for block routing. Block routing answers whether an existing
runtime block is delivered. Family routing answers how model-usable evidence
must be interpreted and which policy must accompany it. A mode match only
makes a family eligible; the family's activation condition must also fire.

## Activation And Monitoring

The active gate completed in V1.39 with:

1. exact accounting traces from long and varied sessions (completed in V1.36);
2. a versioned summary artifact with coverage/source boundaries;
3. tests proving the canonical chronology remains unchanged and navigable;
4. direct Scarlet checks for continuity, source use, recursive routing, and
   response completion;
5. approved whole-turn handling when normal `H` does not fit (defined in
   V1.36) plus a multi-cycle test;
6. fail-safe fallback to full history when no valid active artifact exists.

Ongoing monitoring still needs naturally longer multi-cycle sessions and
provider summary drift review. V1.41 historically added answer obligations
outside the V2 packet; V1.64 removes that validator contract. The GPT bridge
still receives the same backend V2 packet, while backend compaction cannot see
or rewrite native ChatGPT conversation history outside the bridge.

New agent modes or mode-tag enforcement require branch-specific behavioral
scenarios. Native notification collection, continuous sensors, motor actions,
Dream, and maintenance-mode concepts remain outside V1.60.0.

## Shared Human And Autonomous Context

V1.61.0 retires the separate `scarlet-autonomous-context-v1` projection.
Every model turn now receives the common `scarlet-model-context-v2`. The
interactive path remains the behavioral baseline; autonomous activation calls
the same compiler, automatic memory retrieval/rerank, organ projection,
context-family audit, static prompt, and `mind_shell`.

The only lifecycle-specific model datum is source provenance. Current turns
carry `turn_origin`; memory hooks and shell results carry source session,
turn, message, session kind, trigger, actor, message role, and classified
origin. `human_interaction` and `autonomous_cognition` therefore remain
distinguishable without duplicating contracts.

Provider-native histories remain physically separate. Human sessions preserve
their own dialogue; one `scarlet_autonomous` session preserves all internal
cycles. The common session packet places a compact navigable autonomous-session
hint beside the two human `previous_sessions`, while an autonomous activation
receives the same human session hints and common automatic memory blocks.

System/trace-only fields still include scheduler leases, retry state, rich
candidate diagnostics, raw source payloads not opened by Scarlet, routing
audits, and maintenance metadata. Perception remains an external-observation
inbox and is not a second route to internal chronology.

V1.62 keeps this contract intact. A workspace-triggered autonomous turn may
receive a compact `workspace` field in its activation envelope containing only
selected candidate hooks, exact source references, and linked episode/wake
ids. It is explicitly provisional M2.7 orientation, not a second runtime
context, a memory, or evidence that the candidate is true. The full candidate
pool, signal receipts, registry decisions, and arbitration outputs remain
internal/UI/trace evidence.

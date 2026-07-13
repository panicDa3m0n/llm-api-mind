# Runtime Context Packs

Last updated: 2026-07-13
Status: post-V2 planning baseline
App baseline: V1.29.1

This document defines the planning baseline for keeping Scarlet coherent as
her organs, runtime context, and future embodied inputs grow beyond what one
flat prompt/context packet can safely carry.

The immediate goal is not to implement embodiment. The goal is to prevent the
current architecture from drifting toward "send everything to the model" as
memory, focus, volition, affect, metacognition, sessions, traces, and future
eyes/audio/voice/motion channels accumulate.

## Problem

Scarlet already has multiple cognitive organs and evidence sources:

- semantic memory and atomic facts;
- episodic session recall;
- runtime context blocks;
- Mind shell command help and capability state;
- focus, volition, and affect;
- metacognition;
- traces and runtime events;
- maintenance and derived memory surfaces.

Future robotic embodiment will add high-frequency sensory and action domains:
vision, audio, speech, turn-taking, motor plans, actuator safety, environment
state, and real-time interaction loops.

A single always-growing model context would eventually cause:

- lost attention from excessive context mass;
- stale or weak evidence being treated like active perception;
- unnecessary latency and cost;
- coupled organs being separated accidentally;
- background maintenance data leaking into live cognition;
- embodied safety surfaces competing with old project details;
- hard-to-debug behavior because every turn receives too much undifferentiated
  state.

## Principle

Context is not a dump. Context is a routed cognitive surface.

Every context item should have:

- an owner;
- a source;
- a freshness policy;
- an authority level;
- a budget cost;
- a degradation rule;
- a coupling rule;
- a reason for being present in this turn.

The backend should assemble context packs deterministically first. Scarlet can
request a mode shift through shell/state in the future, but the backend keeps
the safety, privacy, budget, and coupling rules.

## Always-On Spine

The always-on spine is the minimum context Scarlet must receive to remain
oriented. It should stay compact and stable.

The accepted V1.29 spine is:

- current session id/title/creation time;
- user display name;
- one user-local `now`, timezone packet, and assembled location;
- two previous-session summary hooks;
- five relevant, five recent-user, and five recent-general memory hooks, with
  cross-list deduplication and source navigation.

The current user message, provider history, static policy, and tool/action
schema are required technical inputs but are not dynamic context packs.
Profile id, privacy enforcement, storage clocks, retrieval diagnostics, KG,
maintenance, and raw capability registries remain systemic unless a later mode
has a demonstrated cognitive reason to expose a compact result.

Never replace the always-on spine with a mode pack. Mode packs extend it.

## Classification Axes

Use these axes for every organ, source, and capability.

### Necessity

- `always_on`: required for coherent operation on every turn.
- `conditional`: loaded by mode, intent, risk, or active state.
- `on_demand`: fetched through `mind_shell` only when needed.
- `background_only`: used by maintenance/offline jobs, not injected into live
  model context.
- `future`: planned but not implemented.

### Coupling

- `independent`: can be used alone.
- `paired`: usually works with another surface but can degrade alone.
- `tightly_coupled`: should be loaded with its partner or not loaded.
- `gated`: requires policy/safety approval before use.

### Freshness

- `realtime`: must reflect the current moment.
- `turn_local`: valid for the current turn.
- `session`: valid within the active session.
- `durable`: semantic/factual state that persists across sessions.
- `archival`: source transcripts, traces, and old records.

### Authority

- runtime fact;
- sensory fact;
- direct API Mind result;
- exact session transcript;
- semantic memory or canonical fact;
- user claim;
- inference.

### Cost

- `tiny`: always affordable.
- `compact`: safe in normal turns.
- `expensive`: only load when evidence value is high.
- `burst`: real-time or high-volume; summarize before model context.

## Organ And Capability Classification

| Organ / source | Necessity | Coupling | Model-facing shape |
|---|---|---|---|
| Temporal context | always_on | independent | Compact operational clock and locale. |
| User identity | always_on compact | independent | Display name only; ownership/privacy stay backend-enforced. |
| Mind shell capability digest | under review | independent | Currently preserved; exact syntax remains on-demand through help. |
| Semantic memory packet | always-on compact | paired with source navigation | Relevant and recent hooks; facts/conflicts/KG on demand. |
| Atomic facts | conditional | tightly coupled with semantic memory | Canonical fact state when memory claims or conflicts matter. |
| Episodic session summaries | always-on compact | paired with session open | Two navigation hints; exact claims require transcript open. |
| Exact session transcripts | on_demand | paired with source-sensitive answers | Retrieved through `session open`. |
| Memory graph | on_demand | paired with semantic memory | Associative expansion when a memory is a doorway. |
| Focus | conditional, under review | paired with volition/tasks | Current foreground state, not a retrieval filter. |
| Volition | conditional | paired with focus/autonomous cycles | Active/due intentions only in relevant modes. |
| Affect | conditional/compact | paired with response style and safety | Tone/posture influence, not factual truth. |
| Metacognition | on_demand | paired with source-sensitive/high-impact work | `metacognition step` result, not raw reasoning. |
| Runtime events | conditional, under review | paired with current session recovery | Currently preserved; full logs remain trace/debug. |
| Maintenance/backfill | background_only | internal services | Never normal live model context; expose status only when relevant. |
| Future vision | conditional realtime | tightly coupled with embodiment safety | Scene/object/event summaries, not raw frames. |
| Future audio/voice | conditional realtime | paired with turn-taking and affect | Transcript/prosody summary, not raw audio. |
| Future motor/actuation | gated | tightly coupled with perception/safety | Plan, constraints, confirmations, and execution result. |

## Mode Packs

Mode packs are named bundles assembled on top of the always-on spine.

### `chat_default`

Normal conversation.

Includes:

- always-on spine;
- only preserved families proven useful for ordinary dialogue;
- active affect/focus only after their own behavioral validation.

### `source_sensitive`

For questions about prior decisions, reliability, measurements, exact wording,
source sessions, traces, or project state.

Includes:

- always-on spine;
- memory provenance and source ids;
- session search/open guidance;
- metacognition validator recommendation;
- explicit evidence-strength labels.

### `temporal_recall`

For "today", "yesterday", "last time", "when did we", or "what thread should
we resume" questions.

Includes:

- always-on spine;
- temporal search policy;
- session list/open capability emphasis;
- warning against exhaustive claims from non-exhaustive pages.

### `project_engineering`

For repository, implementation, branch, docs, tests, and deploy work.

Includes:

- always-on spine;
- project/repo state packet;
- relevant decisions/bugs/experiments;
- test and trace summaries when available.

### `emotional_continuity`

For personal, emotionally delicate, relational, or identity-related turns.

Includes:

- always-on spine;
- affective posture;
- user communication preferences and boundaries;
- safety notes where needed;
- minimal project state unless explicitly requested.

### `embodied_idle` (future)

For a robot body that is present but not actively interacting.

Includes:

- always-on spine;
- low-rate sensory/world summary;
- focus, affect, and active safety state;
- no raw sensory stream.

### `embodied_interaction` (future)

For live user interaction through body, voice, and environment.

Includes:

- always-on spine;
- current transcript/audio turn state;
- visual scene summary;
- user-facing turn-taking state;
- current hazards or safety constraints.

### `embodied_actuation` (future)

For physical movement or environment action.

Includes:

- always-on spine;
- current perception summary;
- motor plan;
- actuator constraints;
- safety gate;
- confirmation/execution result.

This pack must be gated. It must not be silently activated by ordinary chat.

## Router Shape

The future router should choose packs from:

- user message intent and language;
- current session mode;
- active focus/open loop;
- source-sensitivity and verification risk;
- memory retrieval result and conflicts;
- safety/actuation state;
- current sensory load;
- context budget;
- user profile/privacy boundary.

The router should emit a traceable decision:

```json
{
  "pack_id": "source_sensitive",
  "spine_version": "runtime-spine-v1",
  "included_blocks": ["session", "memories", "preserved_context"],
  "omitted_blocks": ["raw_retrieval_shadow"],
  "reason": "User asked whether a prior evaluation is reliable.",
  "budget": {"estimated_tokens": 4200, "limit": 12000},
  "freshness": {"temporal_context": "turn_local"},
  "degradation": []
}
```

## Degradation Rules

If context budget is tight:

1. preserve the always-on spine;
2. preserve active safety/actuation constraints;
3. preserve the evidence source needed for the user's current claim;
4. summarize recent dialogue before dropping source ids;
5. drop raw diagnostics before model-facing summaries;
6. move expensive source reads to on-demand `mind_shell` calls.

Never drop:

- the technical current user message and active-session continuity;
- current session identity and operational clock;
- backend privacy enforcement;
- the active cognitive tool contract;
- actuator safety constraints in embodied modes;
- explicit source conflicts that affect the current answer.

## Implementation Path

1. Keep this document as the planning baseline.
2. Add a backend context-pack registry in shadow mode.
3. Trace pack selection without changing model input.
4. Compare selected packs against actual Scarlet behavior in live sessions.
5. Add compact pack ids and budget metrics to `runtime.context`.
6. Promote router-selected packs into model input only after shadow evidence.
7. Add embodiment-specific packs only after real sensory/actuation surfaces
   exist.

## Current Known Test Pressure

The 2026-07-09 default-token live Scarlet probe showed why this matters:

- temporal/session-sensitive questions can be answered from non-exhaustive
  context if no temporal recall pack forces session search;
- metacognition can recommend further evidence actions that Scarlet does not
  always follow;
- self-architecture claims can be overconfident when the relevant runtime
  organs are not brought into the turn;
- memory write syntax drift can create avoidable retry cost.

These are not embodiment bugs yet. They are early signs that Scarlet needs
context modes and evidence routing before future real-time body context makes
the problem larger.

V1.29.0 adds two measured constraints:

- tool-heavy provider-native history can exceed the compact V2 packet;
- `preserved_context` still carries undiscussed recent dialogue, runtime
  events, capability hints, and Scarlet-state data.

The first router must therefore remain trace-only and measure V2, provider
history, shell results, and GPT bootstrap independently.

Tracked as:

- `BUG-0057`
- `BUG-0058`
- `BUG-0059`
- `BUG-0060`
- `BUG-0061`

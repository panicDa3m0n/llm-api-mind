# V2 Cognitive Companion Plan

Last updated: 2026-07-30
Status: accepted architectural plan; no V2 implementation slice is implied
Baseline: Core V1.50.1 closed; V1.65.0 is the current deployed runtime

## 1. Purpose

V2 turns the closed Core into a coherent companion product direction. It does
not mean adding a collection of disconnected organs, nor claiming that Scarlet
already has human-equivalent cognition. Its outcome is a digital individual
whose interactive life, internal cognitive life, source-backed perception,
relationship continuity, and visible product experience work as one system.

This plan records the owner-approved architectural direction before further
implementation. It is the canonical V2 roadmap for repository planning. Linear
tracks individual work items and their current state; it must be reconciled to
this document before new V2 issues are started.

## 2. Release Boundary

### V1: closed foundation

V1 owns the stable cognitive substrate: canonical history, sessions, memory,
retrieval, context V2, traces, `mind_shell`, provider lifecycle, streaming,
compaction, the existing cognitive organs, the shared native turn kernel,
workspace/endogenous prototypes, Product UI delivery, and the initial module
contracts/host/SDK kit.

V1 is not reopened merely because a branch has future potential. Its accepted
interactive behavior remains the baseline that new work must preserve.

### V2: cognitive companion product

V2 develops and validates the next integrated layer:

1. one observable cognitive lifecycle spanning interactive and autonomous
   experience;
2. dynamic policy and context composition that can admit future sources without
   prompt or context collapse;
3. source-backed signals, temporal perception, attention, and meaningful
   autonomous activation;
4. relational continuity, intentions, and unresolved life threads that improve
   everyday companionship rather than productivity-project management;
5. one or more real companion vertical slices that connect a source, cognition,
   continuity, and a truthful user-visible outcome; and
6. the already delivered Product UI/Android foundation as the consumer surface
   for those real Core states.

V2 also verifies that the existing module contracts, opt-in host, and SDK kit
are adequate *preparation* for future extension. It does not treat the current
kit as a finished third-party ecosystem.

### V3 and later

V3 is the phase for actual product modules, universal connectors, the
developer-facing SDK/distribution experience, stronger package trust and
sandboxing, and controlled third-party extension. Full embodied realtime
audio/video/robotics is a later hardware and model milestone. V2 must make that
work possible without implementing it prematurely.

## 3. V2 Architectural Invariants

Every V2 slice must preserve these rules.

1. **One Scarlet, one cognitive kernel.** Interactive and autonomous turns use
   the same turn kernel, model context contract, memory and retrieval behavior,
   shell, organ contracts, provider finality, traces, and consolidation.
2. **Two episode lineages, not two minds.** There may be many interactive
   sessions and one long-lived autonomous session per profile. Histories remain
   separate and navigable, while both remain available as source-labelled
   continuity to the other lifecycle.
3. **Source type is not session type.** Notifications, device signals, cameras,
   microphones, webhooks, and future actuators are sources. They never create a
   separate cognitive session merely because they have a different transport.
4. **Every source is explicit about provenance.** A record identifies its
   subject, observer, source, time, origin session/turn where relevant, and
   source evidence. Scarlet must not attribute an autonomous elaboration or a
   human-device observation to the human as a statement.
5. **Perception is not automatic prompt injection.** Rich or raw source data
   stays in owned ledgers and buffers. The model receives compact, timely,
   navigable evidence only after an admission/attention decision.
6. **Current, recent, historical, and durable are different states.** A live
   perception may expire; a recent evidence window may remain inspectable; an
   episode is historical; semantic memory requires explicit consolidation.
7. **Semantic authority remains with Scarlet.** Deterministic code owns ids,
   ordering, timestamps, storage, freshness, lifecycle, permissions, receipts,
   retries, and physical-safety boundaries. M2.7 may provide source-backed
   proposals or bounded projections. M3 Scarlet alone makes semantic cognitive
   judgments and explicit organ/memory decisions.
8. **No keyword or score proxy decides natural meaning.** Phrase patterns,
   fixed semantic scores, or opaque helper-model output must not silently
   create memories, conflicts, intentions, affect, or user-facing conclusions.
9. **The Product UI renders Core evidence.** It may narrate a deterministic
   runtime state in human language, but it does not invent thoughts, memories,
   activity, or a second client-owned Scarlet state.
10. **Native Scarlet is authoritative.** GPT remains an experimental transport
    adapter that consumes the same compact Core contracts where its host allows;
    no Core decision is shaped around GPT Action limitations.

## 4. Cognitive Model

### 4.1 Four independent axes

The runtime must not collapse these concepts into one enum or one context pack.

| Axis | Meaning | Examples |
|---|---|---|
| `session_type` | Where the episode belongs chronologically | `interactive`, `autonomous` |
| `activation_cause` | Why Scarlet is active now | human message, source-backed candidate, explicit wake, future external event |
| `agent_mode` | What Scarlet is attending to | `interactive`, `idle`, `scouting` |
| `visibility` | Who receives the result | human answer, internal record, future notification proposal |

An audio conversation therefore remains an interactive session. A future
environment study is an autonomous episode in `scouting`. A notification is a
source event, not a new session. A future realtime interaction is an execution
profile applied to an existing mode, not a third identity or a replacement for
the interactive session.

### 4.2 Shared lifecycle

Every real episode follows the same conceptual lifecycle:

```txt
shared cognitive state
  -> explicit activation cause
  -> common orientation and context compilation
  -> Scarlet episode using the same organs and shell
  -> action/result with source and visibility receipts
  -> common consolidation
  -> updated continuity, candidates, intentions, and open loops
```

The interactive adapter supplies a human message and public delivery. The
autonomous adapter supplies a private activation claim, workspace coordination,
and human-priority yielding. Those differences do not justify another context,
memory, or shell path.

### 4.3 Dynamic policy and context

The native system prompt remains Scarlet's stable policy and identity. Dynamic
evidence does not become ever-growing system-prompt prose. A context compiler
combines the active mode, source family, temporal condition, and requested
operation into:

- the compact model-facing evidence packet;
- a small source-specific policy block only when it changes correct use of that
  evidence; and
- rich trace/UI evidence that stays outside the model packet.

Policy blocks explain boundaries and interpretation; they must not hide
semantic conclusions inside JSON. The existing `scarlet-model-context-v2`
remains the compatibility baseline until an explicitly versioned successor is
implemented and evaluated.

### 4.4 Continuous perception and future realtime

Continuous sensors require a temporal perception plane, not repeated text
summaries or one LLM call per frame:

```txt
capture -> bounded raw buffer -> specialised perception -> live temporal state
        -> source-backed observation/event -> attention candidate -> episode
```

The model normally receives a small capsule with source, time interval,
freshness, uncertainty, and an inspection reference. It can request a precise
window through future shell capabilities. Raw camera/audio streams do not enter
provider history or automatic context.

When future embodiment needs low latency, an execution profile named `realtime`
will add a fast sensorimotor plane beside the deliberative M3 plane. It is not a
V2 implementation commitment. Its future contract must preserve one Scarlet,
link every run to its originating session/turn/objective, retain ordered
evidence handoffs, and prevent fast-path micro-events from becoming automatic
memory.

## 5. Existing V2 Starting Assets

V2 starts from working infrastructure rather than blank theory.

| Asset | Current role | V2 use |
|---|---|---|
| Shared native turn kernel | Human and autonomous turns share context, history, shell, finality, persistence, accounting, and compaction | Preserve it as the only lifecycle owner. |
| Context V2 and mode router | Compact source-navigable context, source receipts, single active mode tags | Evolve through versioned admission, not ad hoc prompt growth. |
| Cognitive Workspace and endogenous windows | Source receipts, M2.7 proposals, M3 episodes, no-work outcomes, rollback modes | Mature candidate quality and wake choice without a second agent. |
| Memory, session, provenance, and proposal ledger | Durable/episodic continuity and Scarlet-owned semantic decisions | Supply sourceable relationship and autonomy evidence. |
| Device Exploration Layer and perception inbox | Isolated raw Android evidence plus bounded, navigable perception surface | Admit one real source only after a dedicated contract and evaluation. |
| Product UI/Android foundation | Real stream/replay rendering, autonomous history, browser/Android delivery parity | Show actual cognitive activity and companion value, not fixtures disguised as state. |
| Module contract, host, and SDK kit | Typed extension boundary, opt-in isolated host, conformance tooling | Audit as V2 preparation; defer real modules and public platform work. |

## 6. Implementation Workstreams

The workstreams are ordered by dependency. Each is divided into a design gate,
a minimal implementation slice, focused verification, direct qualitative
inspection, and a documented decision before the next slice begins. A complete
live behavioral campaign occurs only with explicit owner approval.

### V2-A. Canonical lifecycle and dynamic-policy contract

**Objective:** make the shared lifecycle and the distinction between static
policy, dynamic context, source evidence, and visibility explicit and
executable.

**Implement:**

- preserve the closed shared kernel as the only lifecycle owner and require any
  new V2 source or episode path to enter it; investigate a divergence only when
  current evidence shows that one exists;
- formalise `session_type`, `activation_cause`, `agent_mode`, and `visibility`
  at the relevant storage, trace, and context boundaries;
- define how dynamic source-family policy blocks compose with the static native
  prompt without changing the stable identity contract; and
- version any model-context change, preserving exact trace inspection and GPT
  parity where applicable.

**Do not implement:** new session categories, an autonomous-only context
format, or a second prompt/system policy for background cognition.

**Acceptance evidence:** source-labelled human/autonomous context and history
remain mutually navigable; a direct kernel probe proves parity; no duplicate
context route or semantic fallback is introduced.

### V2-B. Relational continuity, intentions, and open life threads

**Objective:** give Scarlet a small, sourceable continuity substrate for
relationship, pending shared matters, self-directed review, and everyday
initiative.

**Design gate:** distinguish relationship threads, user preferences, Scarlet
volitions, focus, and concrete tasks before adding storage. Scarlet is a
companion, not a developer-task manager. A record must explain whose thread it
is, why it exists, what evidence supports it, its temporal state, and how it
can close, defer, revise, or be rejected.

**Implement only after approval:** the smallest durable lifecycle that lets
Scarlet resume an appropriate relational/open thread without flooding normal
conversation or manufacturing theatrical desires. Reuse existing memory,
focus, volition, episode, and provenance owners wherever their meaning already
fits; add a new organ only when it removes a real ambiguity.

**Acceptance evidence:** natural scenarios show relevant resumption, explicit
source explanation, proportional initiative, truthful no-action outcomes, and
no accumulation of stale pseudo-tasks.

### V2-C. Source admission and temporal perception plane

**Objective:** allow new human-device, environmental, and future embodied
sources to become available to Scarlet without confusing observer/subject,
overloading context, or turning ephemeral data into memory.

**Implement:**

- promote the existing family registry from shadow only through explicit,
  versioned source contracts;
- keep raw capture, normalized observation, live state, recent evidence,
  historical episode, and durable memory as distinct stores/lifecycles;
- require source, observer, temporal interval, freshness, and source reference
  on admitted observations;
- make source data compact and on-demand navigable through the existing small
  shell surface or a deliberately approved extension; and
- choose one bounded real source for a first vertical evaluation only after its
  raw data, value, and failure modes have been observed.

**Do not implement:** broad device ingestion, automatic notification reading,
camera/microphone capture, or automatic context injection merely because a
source exists.

**Acceptance evidence:** the first admitted source can be traced from raw
evidence to a compact model capsule, remains correctly labelled, expires or is
rechecked as appropriate, and does not alter memory without Scarlet's explicit
decision.

### V2-D. Attention, workspace, and autonomous cognitive episodes

**Objective:** make autonomous cognition vary with real evidence, unfinished
threads, and Scarlet-owned interest rather than behaving as a repetitive cron
job.

**Implement:**

- extend the existing Cognitive Workspace rather than creating a parallel
  Global Workspace or deterministic impulse/desire engine;
- let source-backed relational threads, admitted perceptions, current organ
  state, prior episode outcomes, and bounded endogenous windows form
  provisional candidates in one shared pool;
- preserve M2.7 as a non-Scarlet appraiser/proposer and M3 Scarlet as the only
  adopter, investigator, or semantic mutator;
- make no-work, defer, inspect-later, and repeated-work avoidance first-class
  outcomes; and
- retain autonomous chronology, human-turn priority, and source-linked
  episode checkpoints.

**Do not implement:** deterministic desire scores, keyword-recognised emotion
or contradiction, a worker that writes memories/intentions automatically, or
a timer that requires a full Scarlet turn every interval.

**Acceptance evidence:** longitudinal direct observation demonstrates varied
candidate sources, justified wakes and no-wakes, non-repeated episodes, honest
source use, and graceful rollback through the current workspace modes.

### V2-E. First companion vertical slice

**Objective:** prove one complete user-relevant loop rather than many isolated
technical capabilities.

The selected slice must travel through:

```txt
real source or relational evidence
  -> source-labelled availability
  -> attention/candidate decision
  -> interactive or autonomous Scarlet episode
  -> traceable consolidation
  -> truthful companion-visible outcome in Product UI
```

Candidate directions include relational follow-through, a user-approved device
signal that provides timely context, or an open life thread that Scarlet
revisits appropriately. The actual vertical is intentionally not selected in
this plan: it requires owner review of real device evidence and desired user
value.

**Acceptance evidence:** an owner can follow the complete source-to-outcome
chain, Scarlet distinguishes observation from user statement and past from
present, and the feature improves ordinary companionship rather than merely
adding another dashboard counter.

### V2-F. Product expression and communication

**Objective:** make the existing web/Android Product UI the truthful visible
surface of V2 cognition.

**Implement as V2 behavior arrives:**

- render live thinking, notes, tool activity, source hooks, autonomous history,
  memories, relational threads, and availability states from Core stream/replay
  evidence;
- use deterministic human-readable narration only for actual runtime state,
  with technical detail available by expansion;
- expose unavailable future capabilities honestly rather than simulating
  embodiment, notifications, or account features; and
- keep browser and Android artifacts on the same verified Product UI contract.

**Do not implement:** a client-side cognitive state, fabricated live events,
or a separate UI agent.

**Acceptance evidence:** live and replayed turns compose identically from
canonical events; a user can inspect why Scarlet acted or deferred without
having to parse raw debug traces; browser and Android parity passes the release
gate.

### V2-G. Module preparation verification

**Objective:** confirm that V2 work does not bypass or invalidate the extension
boundary already prepared in V1.

**Verify:** context-family and mode additions have typed Core Port ownership;
host isolation, permissions, receipts, and absence-of-module behavior remain
true; SDK schemas do not expose private Core state accidentally.

**Do not implement:** product modules, marketplace/distribution, universal
connectors, hostile-code sandbox guarantees, persistent module product state,
or automatic chat wiring. Those are V3 work even though the V1 SDK kit already
exists.

**Acceptance evidence:** module conformance and no-module regression remain
green after relevant V2 boundary changes; any incompatibility becomes an
explicit V3 design issue rather than an undocumented Core exception.

### V2-H. Integrated validation and release evidence

**Objective:** accept V2 only when its cognitive and product behavior is
observable, sourceable, and no worse than the V1 interactive baseline.

**Required practice:**

- preserve the frozen Core regression suite and run it before/after major
  architecture changes on the same declared test database;
- use focused deterministic tests and direct bounded use for ordinary slices;
- run a broader natural/longitudinal evaluation only when the owner explicitly
  asks for it;
- judge live behavior by actual prompts, actions, sources, outcomes, and
  follow-up effects, not string comparators or counters alone;
- retain production/database ownership boundaries and verify browser/Android
  release parity; and
- keep every promotion reversible through feature/admission modes, append-only
  evidence, and source-preserving fallbacks.

## 7. Dependency Map

```txt
V2-A shared lifecycle + dynamic contract
  ├── V2-B relational/open-thread design and first organ slice
  ├── V2-C source admission and temporal perception
  │     └── V2-D shared workspace/attention/autonomy maturity
  └── V2-D shared workspace/attention/autonomy maturity
          └── V2-E first companion vertical
                  └── V2-F truthful Product UI expression

V2-G module preparation verification gates any changed extension boundary.
V2-H validation gates every promotion and V2 release acceptance.
```

V2-B and V2-C may each begin with their design/evidence phase after V2-A, but
neither should introduce durable semantic state or automatic model admission
until its own contract is approved. V2-E is the integration proof, not a reason
to bypass the earlier boundaries.

## 8. Explicitly Deferred Questions

These questions remain important but are deliberately not implementation scope
until a V2 slice requires them:

- exact semantic duplicate/conflict discovery and resolution;
- authenticated multi-user ownership, data rights, and privacy product flows;
- full temporal-experience and Dream organs;
- a final relational model schema;
- camera/microphone capture, multimodal model selection, and retention policy;
- `realtime_run` protocol, robot control, safety controller, and actuator
  permissions;
- automatic human notifications and external-world actions;
- product modules, universal connectors, external developer distribution, and
  a V3-complete SDK.

Deferral does not erase the ideas. It prevents an attractive future capability
from becoming an untested, duplicate, or semantically fragile addition to a
stable Core.

## 9. First Planning Action

Before the first code issue, reconcile Linear SCA-46 and its child issues with
this plan. Mark completed V1/V2 preparation accurately, move stale UI/module
descriptions out of the active implementation queue, and create one narrowly
scoped V2 issue at a time using the repository development process.

The first implementation issue should be chosen only after owner discussion of
the desired first companion vertical and its evidence source. It must declare
its affected kernel/organ/context surfaces, out-of-scope items, database
boundary, focused verification, direct-use evidence, rollback mode, and
documentation updates.

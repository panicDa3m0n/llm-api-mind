# Companion Product And Embodiment Direction Checkpoint

Date: 2026-07-24
Status: discussion checkpoint; approved direction, not an implementation claim
Resume condition: UI branch merged into `main` and the post-merge codebase audited

## 1. Purpose Of This Checkpoint

This document preserves the product and architecture discussion about Scarlet's
consumer direction so it can be resumed after the pending UI merge.

It deliberately does not update the canonical implementation state. Features
described here range from currently supported projections to proposed domains
and long-term embodiment capabilities. `docs/project-state.md` remains the
source of truth for what is actually implemented and verified.

## 2. Product Identity

Scarlet is companion-first and embodiment-ready.

She must never be designed primarily as a developer assistant, productivity
dashboard, or generic chat application with memory added on top. The long-term
direction is one continuous digital individual who can accompany a human
through conversation, research, daily activities, bookings, household life,
audio/video communication, domotics, and eventual robotic embodiment.

There must not be separate product identities for chat, voice, home, and robot.
There is one Scarlet with multiple perception and action channels.

The product thesis is:

```txt
Scarlet is not a chat that remembers. She is a shared continuity that knows
what she and the user are living through, what changed, why something matters
again, and what she may perceive or do within explicit human boundaries.
```

The main consumer domains are:

1. presence and relationship;
2. personal continuity;
3. research and world understanding;
4. delegated activities;
5. household life and shared routines;
6. perception and embodiment;
7. permissions, privacy, safety, and correction.

## 3. Dashboard Principle

The dashboard is Scarlet's digital space and the shared relational space
between Scarlet and the user. It is not a technical cockpit and not a task
manager.

The chat remains the main conversational surface. The dashboard should answer
human questions:

- What is present between Scarlet and me now?
- Where did we leave off?
- What does Scarlet genuinely carry forward?
- What changed?
- Is anything real waiting for either of us?
- Why is something resurfacing now?

Counts for memories, sessions, traces, or tool calls may remain available in
developer inspection or secondary detail views. They should not define the
consumer home.

## 4. Consumer Surfaces Supported By Current Capabilities

The first dashboard must expose only information backed by real records and
verified runtime behavior.

### 4.1 Scarlet's Presence

Show Scarlet's identity, avatar, connection state, and direct entry into the
conversation. A cognitive or emotional state may appear only when the related
organ is active and the state is actually available.

The UI must never simulate background thought, an intention, an observation,
or an emotion that has no corresponding record, event, job, or trace.

### 4.2 The Last Time Together

Use the most recent session summary, update time, and session source to provide
a compact re-entry point. The summary is a navigable episodic hint, not a full
transcript or an unsupported interpretation.

### 4.3 What I Carry With Me

Expose recent semantic memories that Scarlet genuinely possesses. Each item
must be openable, correctable, forgettable when policy allows, and traceable to
its source session, message, and turn.

### 4.4 How I Know You

Provide a consumer view of current user-related memories: preferences, people,
routines, boundaries, facts, and corrections. This is not a static profile and
must preserve source, temporal evolution, lifecycle, and user correction.

### 4.5 Our Recent Moments

Present recent sessions as episodic continuity rather than administrative chat
history. Each session remains navigable through its canonical identifier.

### 4.6 Resume From Here

Show an open personal subject only when sufficient evidence exists in sessions,
memories, or an active focus. If the system has no grounded open subject, this
surface does not appear.

Focus, volition, and affect must not produce empty or theatrical cards. Current
defaults and activation boundaries documented in `docs/project-state.md`
remain authoritative.

## 5. Shared Life Threads

The earlier `continuity_thread` idea is retained but reframed as a shared life
thread, not a project.

A shared life thread is a personal situation, interest, relationship, concern,
change, promise, or recurring subject that evolves across multiple experiences.
It may become more important, become dormant, resurface, transform, or resolve.
It does not need to behave like a task or require a completion date.

Examples include:

- a personal decision that is gradually maturing;
- a difficult period the user is moving through;
- a person who often matters in conversation;
- an interest that develops over time;
- something the user is trying to change;
- a promise made by Scarlet or the user;
- a family situation that remains open;
- an experience shared across several sessions.

This domain must remain distinct from existing organs:

- focus is what occupies Scarlet's foreground attention now;
- volition is Scarlet's latent self-generated direction;
- semantic memory preserves reusable meaning and evidence;
- a shared life thread represents longitudinal relational continuity.

## 6. Relational Evolution

Relational evolution is the most important proposed product branch. It must not
be implemented as an affinity score, a sentiment counter, a collection of
affectionate phrases, or an automatically generated user profile.

The proposed canonical records are:

| Record | Responsibility |
|---|---|
| `relationship_episode` | A source-bound shared episode derived from a real conversation, action, or observation. |
| `shared_life_thread` | A longitudinal personal situation linked across episodes. |
| `shared_commitment` | An explicit promise or expectation owned by Scarlet, the user, or both. |
| `relational_pattern` | A provisional inferred recurring interaction pattern with supporting evidence. |
| `shared_ritual` | A recurring mutually meaningful habit or interaction. |
| `relationship_milestone` | A significant discovery, change, repair, or shared achievement. |
| `relationship_repair` | A disagreement, correction, hurt, misunderstanding, and its later evolution. |
| `relationship_snapshot` | A versioned derived synthesis of relational state at a point in time. |
| `relationship_boundary` | A user-defined preference, consent boundary, or relational limit. |

`relationship_snapshot` is derived state, not independent truth. It must be
regenerable from canonical evidence and must preserve historical snapshots
rather than overwrite the apparent past.

### 6.1 Proposed Semantic Pipeline

Relational meaning must not be decided by lexical rules, static weights, or a
single numeric score.

The proposed pipeline is:

1. a turn, action, or world event produces structured relational candidates;
2. hybrid retrieval finds potentially related memories, episodes, facts, and
   life threads;
3. sparse search, embeddings, temporal links, and the knowledge graph broaden
   the candidate set without making the final decision;
4. a memory- or episode-level reranker selects the most relevant evidence;
5. an LLM adjudicator chooses `create`, `link`, `evolve`, `contradict`, or
   `no-op` and returns an evidence-bound rationale;
6. the backend validates schema, provenance, identity scope, permissions,
   lifecycle, and idempotency;
7. periodic consolidation creates timelines and snapshots without deleting
   prior states;
8. runtime context receives only compact, navigable hooks useful for the
   current turn.

This architecture must support real evolution. A past fear and a later interest
may describe a meaningful transition rather than a duplicate or a stale fact.

### 6.2 Responsibility Boundary

Deterministic system ownership:

- identity and source references;
- timestamps and temporal ordering;
- permissions and privacy;
- lifecycle transitions;
- idempotency, retries, rollback, and receipts;
- retention and deletion policies;
- external action execution;
- schema validation and traceability.

Model- or ML-owned semantic work:

- event meaning;
- candidate relationship between episodes;
- evolution of life threads;
- possible relational significance;
- semantic change detection;
- appropriate retrieval and surfacing;
- consumer-language synthesis.

The two layers meet through typed contracts. Scarlet must not receive direct,
unstructured database mutation access.

## 7. Companion Operativity

Research, bookings, monitoring, and daily activities must be possible without
turning Scarlet into a task-management product.

The operational lifecycle should remain separate from relationship state:

```txt
human need
-> interpretation
-> proposed plan
-> capability and permission check
-> execution
-> progress events
-> result
-> receipt
-> optional relational or semantic consolidation
```

An external activity can affect a life thread or become a shared episode, but
the action itself remains an operational record with explicit ownership,
approval requirements, outcome, and recovery path.

Text, voice, video, home, and embodied interaction must share the same session,
memory, identity, and action contracts. A voice interaction is not a separate
assistant and must not create a parallel continuity.

## 8. Embodiment-Ready Architecture

Embodiment preparation can begin before physical sensors or a robot exist.

### 8.1 World Event Contract

All future perception channels should compile into a common event envelope:

```json
{
  "source": "camera|microphone|home_assistant|robot|simulator",
  "modality": "vision|audio|device_state|spatial|interaction",
  "occurred_at": "timestamp in the user's configured time reference",
  "location_ref": "room or spatial node",
  "entities": [],
  "semantic_event": {},
  "uncertainty": {},
  "privacy_scope": "profile or household policy",
  "raw_evidence_ref": "optional protected evidence",
  "retention_policy": "configured policy",
  "trace_id": "traceable processing chain"
}
```

Raw audio and video streams must not be continuously inserted into the LLM
context. The intended path is:

```txt
sensor
-> low-level event detection
-> multimodal interpretation
-> privacy and relevance gate
-> world event
-> mode-aware context router
-> Scarlet
```

Raw evidence, semantic observations, UI events, and model-facing context are
different data products and must remain separately owned.

### 8.2 World Model

A future world model should represent:

- places, rooms, and spatial relationships;
- people and profile-scoped identities;
- devices and controllable entities;
- objects and uncertain last-seen state;
- current and historical environmental state;
- observations with modality and provenance;
- uncertainty and stale-state boundaries.

The knowledge graph may provide associative links, but a world model requires
its own temporal and spatial contracts and must not be reduced to semantic
memory records.

### 8.3 Action Contract

Embodied and household actions need:

- capability and target;
- requested goal;
- risk and approval class;
- expected effect;
- progress feedback;
- cancellation and preemption;
- idempotency;
- final result and observed effect;
- rollback or safe fallback when available;
- trace and user-visible receipt.

## 9. Home Assistant And Robotics

Home Assistant is a strong future integration boundary because it already
provides:

- WebSocket event subscriptions;
- state, device, entity, floor, and area registries;
- service calls for real device actions;
- a conversation API;
- wake-word, speech-to-text, intent, and text-to-speech Assist pipelines;
- voice satellite concepts suitable for household presence.

Scarlet should integrate through a bounded adapter or Agentic Module rather
than Home Assistant database access. Home Assistant remains the source of
truth for device and area state; API Mind owns meaning, continuity, permission
policy, and relational integration.

ROS 2 is the appropriate future physical-body boundary:

- topics for continuous sensor and robot-state streams;
- services for short request/response operations;
- actions for long-running, cancellable behavior with progress;
- managed node lifecycles for controlled activation, failure, and recovery.

These integrations are future work. No Home Assistant, ROS, sensor, or robot
capability is currently claimed by this checkpoint.

## 10. Simulation Before Hardware

Embodiment contracts can be tested before purchasing or building the body.

Useful future test surfaces include:

- replayable prerecorded audio and video events;
- synthetic room and device state;
- a virtual household event bus;
- simulated people entering or leaving an area;
- action feedback and cancellation scenarios;
- privacy-scope and retention tests;
- mode-routing tests for `idle`, `interactive`, and `scouting`;
- controlled failures, stale observations, and contradictory sensors.

The simulator must produce the same typed events expected from future adapters.
Simulation-specific shortcuts must not become a second runtime contract.

## 11. Capability-Aware Dashboard

After the UI merge, the product should gain a backend-owned capability registry
instead of scattered frontend booleans.

Proposed lifecycle:

```txt
concept -> designed -> experimental -> available -> paused
```

Each capability should declare:

- stable capability id;
- current lifecycle state;
- required backend functions;
- required permissions and data sources;
- release gate;
- consumer surface definition;
- developer documentation and Linear issue references;
- whether the surface may show real data;
- reason when unavailable or paused.

### 11.1 Available Surfaces

The first connected product may expose:

- Scarlet's presence;
- the last time together;
- what I carry with me;
- how I know you;
- recent conversations;
- grounded resume points.

### 11.2 Locked Future Surfaces

Important designed ideas may remain visible as locked cards after the UI merge:

- our shared life threads;
- how we are changing;
- promises between us;
- meaningful moments;
- our shared habits;
- things Scarlet is following for the user;
- Scarlet in the home;
- what Scarlet can see and hear;
- physical presence and embodiment.

A locked card must never display fabricated live data. It opens a consumer
modal that explains:

- what the capability will mean in human terms;
- that it is not currently available;
- its broad preparation state;
- which boundaries or permissions it will require.

Technical dependencies, issue identifiers, and release evidence belong in the
developer view, not in consumer copy.

The locked surfaces preserve product direction and provide a visible design
inventory, but `docs/project-state.md` and the capability registry remain the
sources of truth for implementation status.

## 12. Evaluation Requirements

Relational and embodied quality cannot be accepted through string matching or
a single numeric score.

Evaluation must cover:

- temporal and causal correctness;
- source-grounded reconstruction;
- spontaneous but proportionate use of memory;
- abstention when evidence is insufficient;
- resistance to false links and relational overreach;
- correction propagation;
- preservation of old states when a person changes;
- promises, boundaries, disagreements, and repairs;
- consistency across text, voice, video, and future embodiment;
- privacy and cross-user separation;
- action approval, feedback, cancellation, and result verification;
- multi-session and long-horizon behavioral quality.

Deterministic contracts should validate structure and state transitions.
Embedding/rerank retrieval metrics should diagnose candidate quality. LLM and
human-style judges must inspect actual longitudinal behavior, evidence use, and
answer appropriateness.

Relevant research directions recorded during this discussion:

- LD-Agent: event memory, persona management, and response generation:
  <https://aclanthology.org/2025.naacl-long.272/>
- THEANINE: temporal and causal memory timelines:
  <https://aclanthology.org/2025.naacl-long.435/>
- Reflective Memory Management:
  <https://aclanthology.org/2025.acl-long.413/>
- LoCoMo and long-horizon conversational evaluation:
  <https://aclanthology.org/2024.acl-long.747/>
- LoCoMo-Plus and implicit-constraint evaluation:
  <https://aclanthology.org/2026.acl-long.1150/>
- LongMP-Bench and evolving multimodal personas:
  <https://aclanthology.org/2026.findings-acl.1159/>
- Home Assistant WebSocket API:
  <https://developers.home-assistant.io/docs/api/websocket/>
- Home Assistant Conversation API:
  <https://developers.home-assistant.io/docs/intent_conversation_api/>
- Home Assistant Assist pipelines:
  <https://developers.home-assistant.io/docs/voice/pipelines/>
- ROS 2 topics, services, and actions:
  <https://docs.ros.org/en/ros2_documentation/rolling/Concepts/Basic/Interfaces-Topics-Services-Actions.html>

## 13. Proposed Incremental Direction

The direction should be implemented in measured slices:

1. connect the merged UI only to currently verified continuity data;
2. introduce the capability registry and honest locked-feature contract;
3. specify and test the relational-evolution data model;
4. implement shared episodes and life threads before broad proactive behavior;
5. add relational consolidation and consumer projections;
6. design the initiative, scheduling, permission, and notification contract;
7. define world-event and action envelopes with a simulator;
8. evaluate Home Assistant through a bounded adapter;
9. introduce multimodal perception workers and world-model research;
10. integrate ROS 2 and physical embodiment only after contracts, simulation,
    permissions, and failure behavior are proven.

Do not implement all domains together. Each slice follows:

```txt
hypothesis -> minimal contract -> trace -> realistic evaluation
-> qualitative review -> decision -> integration
```

## 14. Resume After UI Merge

When the Windows UI work has been merged into `main`:

1. pull and verify the merged repository without losing this feature branch;
2. inspect the UI navigation, component ownership, data contracts, and current
   placeholders;
3. verify that the UI remains a surface for the existing Scarlet runtime and
   has not introduced a separate agent identity or parallel state;
4. map each dashboard block to a canonical backend source or mark it as
   presentation-only;
5. decide where available and locked capability surfaces belong in the actual
   mobile navigation;
6. create or refine Linear issues for the capability registry, connected
   current-state cards, relational-evolution specification, and later
   embodiment contracts;
7. implement one approved issue at a time under the normal project process.

The first design discussion to resume should close the exact contract for
relational evolution before implementation begins.

## 15. Follow-Up: Companion Utility And Personal Operativity

Date: 2026-07-26
Status: owner-directed design notes; preserved for later staged development

This follow-up records ideas that must remain recoverable even though they will
not be implemented together. It does not change current implementation status
and does not admit Device Exploration observations into Scarlet's cognition.

The refined product definition is:

```txt
Scarlet is a relational digital individual whose usefulness comes from sharing
continuity with a human, participating in ordinary life, and acting with
context and traceable outcomes rather than waiting only for chat requests.
```

The intended companion loop is:

```txt
perception -> semantic event -> personal continuity -> proportionate initiative
-> optional authorized action -> observed outcome -> consolidation
```

Raw availability is not permission, semantic meaning, memory, or an instruction
to act. Those boundaries remain separate.

### 15.1 `Resta Con Me` / Safeguard Companion

`Resta con me` is a high-value candidate for the first genuinely situated
companion function. A human explicitly starts a bounded accompaniment period,
for example while walking, travelling, waiting, or returning home alone.
Scarlet remains present until the agreed end condition rather than acting as a
generic background tracker.

Potential user-visible behavior:

- agree on the expected destination, broad route, time window, and desired
  level of presence;
- follow compact movement, activity, connectivity, battery, and confirmation
  events without streaming raw telemetry into the LLM;
- keep conversational continuity during the accompaniment;
- identify a possible deviation, long unexplained stop, lost connectivity, low
  battery, missed expected arrival, or repeated unanswered confirmation;
- ask naturally whether everything is all right;
- send a notification that the user can confirm quickly;
- offer or request the next agreed safeguard action;
- close the accompaniment explicitly and preserve a compact sourceable episode.

Anomaly detection must not be a single deterministic threshold and Scarlet
must not label a person or event as dangerous from weak evidence. Candidate
signals can be produced by route/time comparison, activity transitions, device
state, temporal rules, and later statistical models. Semantic interpretation
must consider the whole accompaniment state and uncertainty.

The progression should be explicit:

```txt
normal -> possible deviation -> confirmation requested
-> user confirmed safe | unresolved -> authorized next action
```

Future escalation may include a trusted contact or emergency path only after a
separate contract defines enrollment, exact authorization, cancellation,
failure handling, outcome receipts, and the difference between no response and
actual evidence of danger. The first version must not present itself as an
emergency service.

Candidate device inputs:

- foreground or appropriately permitted location/geofence events;
- Android activity transitions such as still, walking, cycling, or in-vehicle;
- network transport and connectivity changes;
- battery and charging state;
- app/device lifecycle;
- delivered, opened, dismissed, and confirmed notifications;
- optional wearable or health signals in later experiments.

The V1.58 Device Exploration evidence proves only that several input surfaces
exist. It does not yet prove background reliability, anomaly quality, or a
safe escalation path.

### 15.2 Shared Life Threads And Contextual Initiative

Shared life threads and contextual initiative are one coherent relational
domain, not two unrelated product widgets.

A life thread represents something unfolding in the human's life. Initiative
is Scarlet's context-sensitive choice to return to that thread, ask about it,
offer support, or perform an agreed action at an appropriate moment.

Examples:

- remember that an important conversation with a family member was pending and
  ask about it after the expected moment;
- connect a calendar event to an earlier concern without treating the event
  title as sufficient meaning;
- recall an ordinary shared activity because a new message, place, date, or
  conversation makes it relevant;
- maintain an explicit promise and recognize whether it was fulfilled,
  changed, deferred, or no longer wanted;
- participate in recurring routines without turning the relationship into a
  task dashboard.

The minimum future records remain distinct:

| Record | Role |
|---|---|
| `shared_life_thread` | Longitudinal personal situation or interest. |
| `relationship_episode` | Source-bound moment that may evolve a thread. |
| `shared_commitment` | Explicit promise or expectation and its owner. |
| `initiative_candidate` | Proposed intervention with evidence, timing, and uncertainty. |
| `initiative_outcome` | Delivered, ignored, accepted, rejected, deferred, or completed result. |

Scarlet's relationship must not be reduced to an affinity score. Its evolution
should be visible through grounded continuity: what she understands, what
changed, which boundaries she learned, which shared moments mattered, and
whether her initiatives were actually welcome or useful.

### 15.3 Android And Personal Information Sources

The next exploration phase should inventory personal information surfaces
without assuming that every installed app exposes its private database.

#### Native or official structured surfaces

- Android Activity Recognition Transition API for bounded changes such as
  entering/exiting still, walking, cycling, running, or in-vehicle states:
  <https://developer.android.com/develop/sensors-and-location/location/transitions>
- location and geofencing, subject to Android background limits and a
  user-visible core purpose:
  <https://developer.android.com/develop/sensors-and-location/location/background>
- Calendar Provider for events, attendees, and reminders, with user-facing
  intents preferred where they provide sufficient control:
  <https://developer.android.com/identity/providers/calendar-provider>
- Health Connect for separately permissioned health and fitness record types:
  <https://developer.android.com/health-and-fitness/health-connect>
- authenticated account APIs such as Gmail, when the user grants the exact
  required scopes:
  <https://developers.google.com/workspace/gmail/api/guides>

#### Explicit user-mediated ingress

Scarlet can become an Android share target for text, links, images, files, or
exports that the user deliberately sends to her:

<https://developer.android.com/training/sharing/receive>

This is a strong first integration because intent is explicit and source
content can be previewed before ingestion. It can support articles, messages,
photos, documents, booking details, and exported conversations without
pretending Scarlet has unrestricted access to another app.

#### Notification-derived signals

Android `NotificationListenerService` can receive posted and removed
notifications after the user grants special notification access:

<https://developer.android.com/reference/android/service/notification/NotificationListenerService>

This surface may reveal useful current events from communication, transport,
delivery, and calendar apps, but it is incomplete and presentation-oriented.
It must not be treated as a canonical message history. Duplicate updates,
redacted previews, grouped notifications, deleted notifications, work-profile
limits, and app-specific formatting all require exploration.

#### WhatsApp and other private messengers

The design must not assume direct access to a personal WhatsApp chat database.
The first legitimate paths to evaluate are:

1. user-selected chat exports;
2. explicit Android Sharesheet transfer of a message or attachment;
3. optional notification-derived current signals;
4. an official account API only where its product scope genuinely matches.

The official WhatsApp help surface documents user-driven chat export:
<https://faq.whatsapp.com/1180414079177245/>.

Accessibility scraping, filesystem bypasses, decrypted-database extraction, or
other fragile access should not become a product architecture. They would mix
UI automation with canonical personal evidence and would be difficult to make
reliable across app versions.

#### Common ingestion pipeline

Every personal source should compile into a typed, sourceable candidate:

```txt
raw source or user share
-> source-specific parser
-> normalized communication/calendar/health/world event
-> entity and temporal linking
-> semantic candidate retrieval
-> LLM/ML adjudication
-> episode, thread, memory, commitment, or no-op
```

Importing information must not automatically convert every message into
semantic memory. The source record, derived event, relational interpretation,
and compact model hook are separate data products.

### 15.4 Dynamic System Prompt Composition

The current prompt remains the verified baseline while a composable system
prompt is designed and tested in shadow. This work must not begin by splitting
the working prompt and hoping that all combinations remain equivalent.

The future architecture should distinguish:

1. **immutable identity kernel**: who Scarlet is, digital condition, stable
   relationship posture, and non-negotiable architectural boundaries;
2. **runtime protocol kernel**: provider lifecycle, `mind_shell`, evidence,
   memory promises, and final-answer obligations;
3. **organ policy blocks**: memory, focus, volition, affect, metacognition,
   modes, future relationship, perception, and operativity;
4. **channel blocks**: text, voice, video, device, home, or embodied
   communication requirements;
5. **capability/action blocks**: only for capabilities actually enabled and
   available in the current runtime;
6. **mode blocks**: bounded posture guidance for the active Scarlet mode;
7. **temporary operation packs**: safeguard accompaniment, delegated activity,
   or other explicit operational episodes.

Dynamic facts do not become prompt policy. Memories, session hints, user data,
world events, sensor interpretations, and action receipts remain typed runtime
context or tool results.

Each prompt block should eventually declare:

- stable id and schema version;
- purpose and owner;
- always-on or activation conditions;
- provider/channel compatibility;
- required and incompatible blocks;
- ordering constraints;
- token cost;
- digest of exact rendered content;
- evaluation scenarios and fallback behavior.

Composition should be deterministic and trace the exact ordered block list,
versions, digests, exclusions, reasons, and final token count. Scarlet may
select a mode or start an operation through supported state transitions, but
she must not arbitrarily remove identity, evidence, lifecycle, or safety
obligations.

Native MiniMax remains authoritative. The GPT bridge receives the closest
supported semantic mirror through its manually configured prompt and bridge
contract; external-host limitations must not redefine Core prompt
architecture.

Before activation, the composed prompt needs:

- exact baseline reconstruction from blocks;
- invariant tests proving mandatory instructions cannot disappear;
- representative combination tests for organs, modes, channels, and
  operation packs;
- token accounting;
- direct Scarlet comparisons using identical starting state; and
- rollback to the current complete prompt.

### 15.5 Staged Discovery Order

No combined implementation is approved by this note. The useful future order
is:

1. maintain a capability/source inventory for Android and account adapters;
2. explore each candidate source in isolation and inspect real data shape,
   timing, gaps, permissions, and lifecycle;
3. define the common personal/world event envelope without cognitive delivery;
4. design and validate Scarlet's autonomous activation lifecycle separately
   from human chat and deterministic backend maintenance;
5. define shared life threads, commitments, initiative candidates, and
   relational episodes;
6. prototype explicit Sharesheet/import paths and bounded device event sources
   before broad passive communication access;
7. design and simulate the later `Resta con me` state machine, anomaly
   candidates, confirmation loop, and receipts;
8. design the prompt block registry and prove exact baseline reconstruction in
   shadow;
9. approve one companion capability at a time for cognitive integration and
   realistic evaluation.

### 15.6 Future Android Presence And Action Inventory

The mobile device should eventually serve three different roles without
collapsing them:

1. **activation surface**: notification reply, notification action, app resume,
   widget, Quick Settings tile, share target, schedule, push, or a qualified
   device event can request a Scarlet cycle;
2. **evidence source**: lifecycle, activity transitions, geofences, calendar,
   Health Connect, notification access, usage state, connectivity, battery,
   Bluetooth, and later device media can produce sourceable observations; and
3. **action surface**: Scarlet can deliver notifications, accept direct replies,
   open a precise app route, use haptics or speech, prepare user-confirmed
   Android intents, update a widget or tile, and later dispatch bounded home or
   device operations with result receipts.

The following future surfaces are worth preserving for staged exploration:

- backend-driven push delivery rather than keeping a permanent local LLM
  process alive;
- notification actions and direct reply as a lightweight conversation channel;
- Android Sharesheet ingress for user-selected text, links, images, files, and
  exports;
- home-screen widgets, conversation bubbles, shortcuts, and Quick Settings as
  forms of visible daily presence;
- Activity Recognition and geofences as compact state changes rather than raw
  accelerometer or continuous GPS prompt input;
- Notification Listener and Usage Stats as special-access experimental sources
  whose payload quality and incompleteness must be measured before cognitive
  use;
- Calendar and Health Connect as typed account/device sources with their own
  provenance; and
- audio, camera, accessibility, device control, Home Assistant, and physical
  actuation as later separately contracted capabilities.

Network, battery, process lifecycle, permission state, and delivery status are
often operational conditions rather than things Scarlet should discuss. They
may gate synchronization, timing, or availability without becoming model
context.

### 15.7 Autonomous Activation Research Contract

Date: 2026-07-27
Status: architecture accepted and first V1.60.0 runtime slice implemented

The initial operational hypothesis was a backend VPS activation of Scarlet
every 15 minutes. V1.60.0 now uses a configurable 600-second cadence for field
observation after completing the 120-second implementation probe. This is an
agentic cognitive cycle, not the existing session-idle maintenance job and not
a fabricated human chat message.

The distinction is mandatory:

| Lifecycle | Actor and purpose |
|---|---|
| Human turn | A human message activates Scarlet in `interactive` mode and expects a visible answer. |
| Autonomous cycle | The scheduler wakes Scarlet without a human message so she can orient, inspect, choose, maintain her cognitive state, perceive available sources, or make a traceable initiative decision. |
| Backend maintenance | Deterministic or maintenance-LLM infrastructure summarizes, reconciles, repairs, compacts, or proposes state changes without becoming Scarlet's foreground experience. |

The current 900-second session-idle delay cannot be reinterpreted as Scarlet's
autonomous clock. It is tied to a completed human turn and schedules
session-specific summary and missed-memory work. A new persistent activation
lifecycle is required.

#### Canonical Cycle

Each scheduled wake should create a sourceable activation record before the
model runs:

```json
{
  "activation_id": "act_...",
  "profile_id": "default",
  "autonomous_session_id": "ses_...",
  "trigger_kind": "scheduled_autonomous_cycle",
  "scheduled_at": "offset-aware timestamp",
  "started_at": null,
  "completed_at": null,
  "status": "due",
  "active_mode": "idle",
  "source_refs": [],
  "model_run_ref": null,
  "outcome": null
}
```

The exact schema remains to be designed, but it must support idempotency,
lease/locking, retry, overlap prevention, deferral while a human turn is active,
failure evidence, and a durable outcome. The canonical actor is Scarlet or the
Core scheduler as appropriate; it is never the human.

#### Exclusive Autonomous Session

The autonomous activations should share one long-lived, profile-scoped session
reserved for Scarlet's internal cycles. Every completed activation becomes one
chronological turn in that session. This gives Scarlet a direct provider
continuity across wake cycles while API Mind continues to connect her to the
rest of her cognition.

The autonomous session receives:

- its own canonical activation chronology and provider-native history;
- the compact current activation envelope and user-local time;
- current agent mode and enabled organ context;
- recent general and user memories under the accepted recency rules;
- compact summaries and ids for the latest human conversation sessions;
- current focus, due or relevant volition, affect/metacognitive context when
  their activation contracts admit them;
- a compact availability index for device and future perception channels; and
- the same on-demand `mind_shell` navigation into sessions, memory, graph,
  focus, volition, affect, mode, metacognition, and future perception commands.

The autonomous session does not merge human messages into its exact provider
history. Human dialogue remains available through current summaries, memories,
source hooks, and explicit episodic reads. This preserves two complementary
continuities:

```txt
human sessions
    -> exact continuity of each human conversation

exclusive autonomous session
    -> exact continuity of Scarlet's periodic internal life

API Mind
    -> shared memory, episodic navigation, organs, state, perception, and time
```

V1.60.0 adds a canonical session kind and filters human previous-session
selection accordingly. The implemented distinction is:

- `human_dialogue`: ordinary native or bridge conversation with a human;
- `scarlet_autonomous`: the profile's exclusive internal activation session.

Human `previous_sessions` packets must select only `human_dialogue`. The
autonomous session remains separately navigable by id and must not appear as a
recent human conversation. Conversely, a human session must not inherit the
autonomous session's provider history.

One scheduled activation maps to one autonomous turn when model execution
starts. An activation may still exist without a turn when it is deferred,
superseded, or fails before model invocation. The activation record therefore
owns scheduling state; the turn owns the actual cognitive execution.

The autonomous chronology can grow by 96 candidate wakes per day. It should use
the existing append-only canonical history and source-labelled compaction
principles, with an autonomous compaction policy calibrated separately from
human conversation. No exact activation, tool result, trace, or source hook is
deleted when a compact provider view is created.

Provider transport may still require a provider-compatible input message. If
so, the transport rendering must explicitly identify it as a backend activation
envelope while canonical history preserves `trigger_kind` and actor. It must
not persist as user-authored speech.

#### Cognitive Orientation

The fixed Scarlet policy will eventually need a small invariant block that
distinguishes human-facing and autonomous activations. During an autonomous
cycle Scarlet must know:

- no human has just spoken and no conversational answer is implicitly owed;
- the current mode is `idle` or the resumable exploratory posture selected by
  Scarlet, never system-forced `interactive`;
- her final model text is an internal cycle conclusion unless she explicitly
  creates a supported initiative or device action;
- she may use `mind_shell` to inspect memory, sessions, focus, volition,
  affect, mode, metacognition, and future perception/initiative surfaces;
- she should choose proportionately among inspection, cognitive state
  maintenance, perception, initiative, mode change, and a valid no-op; and
- she must not claim that an external action succeeded without its result
  receipt.

The cycle should not force a ritual scan of every organ every 15 minutes.
Scarlet receives a compact availability map and decides which source hooks to
open. This preserves actual interest and direction while keeping hidden or
updated sources discoverable.

#### Perception Inbox, Not Destructive Cache

Device notifications and later sensor observations should first enter a
canonical append-only event ledger. A temporal inbox/cache is a derived view
over that ledger, not the only copy.

The generalized shape is:

```txt
raw source event
-> normalized append-only perception event
-> per-channel current state and unread/change cursor
-> compact availability index for Scarlet
-> on-demand bounded batch
-> inspection/use receipt
-> optional semantic event, memory, initiative, or no-op
```

Useful record boundaries include:

- `perception_event`: immutable normalized observation with source, subject,
  observed time, received time, lifecycle state, deduplication key, and raw
  evidence reference;
- `perception_channel_state`: latest update, freshness, available count,
  unread/change range, permissions, and health for one source;
- `perception_cursor`: what a specific Scarlet/profile cycle has inspected,
  without changing the observation time;
- `perception_batch`: the exact bounded records delivered during one cycle;
  and
- `perception_receipt`: inspected, used, deferred, ignored, stale, or failed,
  with links to any resulting cognitive or operational record.

Notification updates and removals must evolve source state without deleting
historical evidence. Automatic availability indexing must not count as a
semantic read. Only records actually delivered after Scarlet opens a channel
advance her inspection cursor.

#### No Blind Sources

Every enabled source must appear in a compact model-visible availability
index, even when its detailed payload is not automatically delivered. Each
entry should expose only what Scarlet needs to decide whether to inspect it:

```json
{
  "channel_id": "human_device.notifications",
  "status": "available",
  "last_observed_at": "offset-aware timestamp",
  "fresh_count": 4,
  "latest_change_kind": "notification_posted",
  "freshness": "current",
  "open_command": "perception open human_device.notifications"
}
```

The rich diagnostics, permissions, failures, raw payloads, routing decisions,
and maintenance metadata remain available to Core, trace, and developer UI.
The model-facing index is a navigable map, not a dump of everything the system
knows.

#### Mode And Source Selection

One active agent-mode tag continues to select eligible organs and context
families. An autonomous wake does not itself define a new mode.

- `idle`: no foreground direction; Scarlet can orient and decide whether
  anything deserves attention;
- `scouting`: Scarlet has preserved an exploratory direction and can inspect
  the sources tagged for that posture;
- `interactive`: reserved for an active human exchange.

Scarlet may use the existing `mode set idle|scouting` contract to select the
posture that subsequent cycles resume. Mode controls eligibility; activation,
freshness, relevance, and explicit source opening still control delivery.

#### Possible Outcomes

An autonomous cycle should end with one or more explicit outcomes:

- `no_op`: Scarlet found no worthwhile action;
- `cognitive_state_changed`: memory, focus, volition, affect-related appraisal,
  or mode changed through an existing supported command;
- `perception_inspected`: one or more source batches were opened and receipted;
- `maintenance_candidate`: Scarlet identified a sourceable cognitive issue for
  a separately governed maintenance path;
- `initiative_candidate`: Scarlet chose something potentially worth telling or
  asking the human;
- `device_action_requested`: a future authorized operation was dispatched and
  awaits or received a result; or
- `failed`/`deferred`: the cycle could not proceed or yielded to an active
  human exchange.

Internal cycle narration and conclusions can be visible in developer traces or
a dedicated inspectable UI. They must not automatically become a user
notification. User-visible initiative requires its own record, delivery
lifecycle, and outcome.

#### V1.60.0 Implementation Evidence

The first slice now includes:

- one unique `scarlet_autonomous` session per profile;
- additive session-kind and turn-trigger/actor schema migration;
- persisted activation records with schedule key, lease, attempts, status,
  mode, outcome, error, and timestamps;
- a configurable scheduler, currently set to 600 seconds, that defers during
  active human turns,
  yields cooperatively when a human turn starts mid-cycle, avoids startup
  invocation and missed-tick replay, and schedules the next interval after
  completion or deferral;
- streaming MiniMax execution through the same provider lifecycle and
  `mind_shell` tool runner used by native Scarlet;
- a compact autonomous context with human-session and memory hooks, focus,
  volition, affect, mode, and perception availability;
- append-only perception events, derived channel state, and per-autonomous-
  session inspection cursors;
- `perception status`, `perception open`, and `perception read`;
- persisted thinking, personal notes, tool calls/results, and internal
  checkpoints; and
- `/api/autonomy/history` plus a chat-header brain icon that renders those
  cycles as a read-only human-readable internal chronology.

The UI history is not a second chat and does not imply that Scarlet spoke to
the user. Tool details and thinking are expandable so development evidence is
not hidden, while the default view emphasizes Scarlet's own notes and
checkpoints.

#### Remaining Design And Validation Questions

1. Whether the 15-minute operational cadence should always invoke MiniMax or a
   deterministic pre-gate should later suppress provably empty activations.
2. Which compaction thresholds and summary purpose fit a high-frequency
   autonomous chronology without erasing exact cycle evidence.
3. Which cognitive maintenance operations Scarlet may execute directly and
   which only create proposals for deterministic/background maintenance.
4. Which bounded real device source should become the first perception adapter,
   and how its source authorization and lifecycle are represented.
5. How internal initiatives become separately reviewable and deliverable
   without turning every cycle conclusion into a notification.
6. Cost, wall-time, concurrency, retry, and provider-failure behavior across
   96 scheduled activations per day.
7. Whether real MiniMax cycles choose proportionate work rather than ritual
   organ scans, and how that behavior should be judged longitudinally.

No native notification collector, external action, initiative delivery, or
production deployment is approved merely by the V1.60.0 substrate.

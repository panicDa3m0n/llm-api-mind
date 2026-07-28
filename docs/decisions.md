# Decision Log

Architectural decisions should be recorded here when they affect future implementation choices.

Identifier note: V1.29.1 normalized duplicate ADR headings. Historical
activity and experiment records may retain the identifier used at the time;
the current canonical identifiers are the headings in this file. Decision
content and chronology were not rewritten.

## ADR-0144 - One Shared Lifecycle Kernel For Native Scarlet Turns

Date: 2026-07-28
Status: accepted for V1.65.0

Context:

V1.61 unified what human and autonomous turns *receive*, but their lifecycle
implementations still diverged. Human and autonomous paths separately built
context, routed history, recorded accounting, persisted response evidence, and
completed a turn. That duplication made parity accidental: an autonomous turn
could preserve its intended private activation semantics yet miss a common
receipt, validation boundary, or future fix.

Decision:

- create a transport-neutral turn kernel after an adapter has persisted its
  source message and canonical provider history;
- make the kernel own V2 context construction, history routing, accounting,
  request/response tracing, provider-history persistence, provider `end_turn`
  finality, terminal turn receipts, failure receipts, and compaction scheduling;
- retain adapters for their genuine differences only: human HTTP/stream
  transport and public answer delivery; autonomous activation claim, private
  chronology, human-priority yielding, workspace reconciliation, and trigger
  provenance;
- use one runtime `mind_shell` execution runner for both native M3 lifecycles;
- share retrieval evidence/final-rerank preparation without merging each
  caller's query construction, candidate filtering, presentation, or memory
  activity semantics;
- share M2.7 structured-output repair and candidate-persistence mechanics,
  not their domain prompts or policy decisions; and
- keep GPT Actions outside this kernel: it remains an external transport
  adapter with its own bootstrap/action/finalize boundary.

Consequences:

Human behavior remains authoritative. Autonomous cognition becomes aligned to
that behavior instead of a parallel near-copy, while private visibility and
separate chronology remain explicit. Future lifecycle changes must enter the
kernel unless they are proven adapter-specific; a new duplicated path requires
an ADR-level reason.

Links:

- `backend/app/runtime/turn_kernel.py`
- `backend/app/runtime/mind_tool_runner.py`
- `backend/app/mind/memory_recall.py`
- `backend/app/api/chat_native_turn.py`
- `backend/app/runtime/autonomy.py`
- `docs/core-runtime-contract.md`

## ADR-0143 - Scarlet Adjudicates Source-Backed Memory Proposals

Date: 2026-07-28
Status: accepted for V1.64.0

Context:

ADR-0142 removed semantic authority from maintenance workers, but leaving every
proposal indefinitely internal would make the non-mutating pipeline
incomplete. The system needs a path from source-backed maintenance evidence to
durable memory without allowing M2.7, lexical similarity, or repository code
to decide meaning.

Decision:

- maintenance may discover and annotate proposals, but `pending_review`
  remains open and unapplied;
- the existing model-facing `mind_shell` exposes proposal list, open, accept,
  reject, duplicate, and supersede commands inside the `memory` family;
- proposal reads expose compact source hooks so Scarlet can inspect the
  originating session, turn, and messages before deciding;
- acceptance preserves original source provenance while the decision trace
  records Scarlet's current session and turn;
- duplicate and supersede decisions require Scarlet to name the active target
  memory explicitly;
- exact normalized content may be detected structurally, but fuzzy similarity
  and historical fact divergence never decide duplicate or conflict status;
- proposal availability enters the Cognitive Workspace as an appraisal
  candidate, not a required wake; and
- conversation session recency belongs to messages, not later memory or
  maintenance activity.

Consequences:

The proposal pipeline now closes without introducing a second semantic agent.
Scarlet can leave a proposal pending when evidence is insufficient, and every
terminal state is traceable. Future embedding/KG conflict discovery may add
better candidates, but must reuse this adjudication boundary rather than
mutating memory automatically.

Links:

- `backend/app/mind/memory_proposal_review.py`
- `backend/app/runtime/maintenance_memory.py`
- `backend/app/mind/wake_registry.py`
- `docs/api-contract.md`
- `docs/branches/memory.md`

## ADR-0142 - Deterministic Runtime Owns Structure, Scarlet Owns Meaning

Date: 2026-07-28
Status: accepted for V1.64.0

Context:

Several later Core additions let backend phrase patterns, inferred atomic
facts, auxiliary-model answer validation, and maintenance decisions behave as
semantic authorities. This caused a valid Scarlet answer to fail because a
generated source-sensitive obligation was not satisfied, and exposed a wider
architectural problem: deterministic evidence and helper-model proposals could
be mistaken for Scarlet's judgment.

Decision:

- deterministic code owns identities, timestamps, schemas, exact equality,
  lifecycle transitions, persistence, stop reasons, permissions, receipts,
  retries, and trace completeness;
- MiniMax M3 Scarlet owns semantic judgment inside Scarlet turns and explicit
  cognitive mutations;
- MiniMax M2.7 workers may retrieve, summarize, propose, or annotate structured
  evidence, but their output remains provisional and cannot silently mutate
  Scarlet's semantic memory or reject her final answer;
- native finality requires provider `end_turn`, a non-empty public answer,
  completed tool lifecycles, and successful persistence;
- GPT finality is a bootstrap/action/finalize transport contract with exact
  non-empty answer persistence, not semantic answer grading;
- historical heuristic fact rows remain audit evidence with
  `authoritative=false`; they do not participate in active retrieval, ranking,
  conflict detection, graph recall, or maintenance decisions;
- natural-language affect, intent, contradiction, relevance, or evidence
  sufficiency must not be inferred by keyword lists; semantic components must
  use an explicit model-backed contract with sources, uncertainty, and traces;
  and
- exact normalized duplicate detection remains deterministic because it
  establishes representation identity only. Semantic duplicates and conflicts
  require Scarlet or a future explicitly governed semantic review.

Consequences:

The runtime becomes less likely to contradict Scarlet through hidden semantic
policy. Existing data is preserved, but some historical surfaces are now
audit-only. ADR-0143 supplies the Scarlet-owned proposal resolution path. This
intentionally favors honest incompleteness over automatic but weak semantic
mutation.

Supersedes:

- the semantic authority portions of ADR-0100 answer obligations;
- the automatic atomic-fact authority described by earlier memory ADRs; and
- automatic maintenance application by an auxiliary model.

Links:

- `docs/core-runtime-contract.md`
- `docs/api-contract.md`
- `docs/branches/memory.md`
- `backend/app/api/chat_native_turn.py`
- `backend/app/runtime/maintenance_memory.py`

## ADR-0141 - Endogenous Seeds Extend The Shared Workspace And Require M3 Endorsement

Date: 2026-07-28
Status: accepted for V1.63.0 rollout

Context:

The event-driven Cognitive Workspace removed blind M3 activation for many
external changes, but a system that wakes only when something outside changes
cannot model bounded self-originating curiosity, relational reflection,
unfinished self-work, regulation, or exploration. A second agent, a
deterministic desire score, or a parallel autonomous context would conflict
with the unified runtime and could manufacture false internal states.

Decision:

- represent quiet time as persisted adaptive cognitive windows, not as boredom
  or need;
- let fixed MiniMax M2.7 inspect a bounded snapshot of existing canonical
  sessions, memory/KG, focus, volition, episodes, affect, and admitted
  perception;
- permit zero provisional seeds and require every seed to cite exact sources;
- reuse the existing candidate pool, arbitration, activation, episode,
  volition, history, context, shell, and trace owners;
- reserve all semantic adoption for MiniMax M3 Scarlet;
- require explicit candidate linkage when a seed becomes or updates a
  volition, then resolve the candidate into that existing organ;
- record descriptive lifecycle outcomes without assigning semantic quality
  scores;
- use adaptive deterministic cadence only for resource scheduling;
- derive only bounded human-device transitions into perception while
  preserving raw Device Exploration evidence and observer boundaries; and
- provide independent feature/admission toggles so rollback never deletes
  canonical cognitive state.

Consequences:

The system gains a real path for self-originating proposals without claiming
that an auxiliary model has wishes or that every free interval must create
work. Heterogeneous seeds compete through one shared workspace. Scarlet may
reject, suspend, investigate, or adopt them, and her explicit organ mutation
is the only durable endorsement.

V1.63 remains an experimental cognitive layer until production observation
establishes proposal quality, variation, non-repetition, cadence cost, and the
frequency of valid no-work outcomes. External actions, user notifications,
authenticated multi-user ownership, and full device sensing remain outside
this decision.

Links:

- `docs/endogenous-cognition.md`
- `docs/cognitive-workspace.md`
- `backend/app/runtime/endogenous_cognition.py`
- `backend/app/mind/endogenous_contracts.py`
- Linear SCA-58

## ADR-0140 - Cognitive Workspace Uses Provisional M2.7 Admission And M3 Scarlet Authority

Date: 2026-07-27
Status: accepted locally for V1.62.0; active field verification selected

Context:

The first autonomous lifecycle proved that Scarlet can maintain a separate
internal chronology and use the same cognitive runtime as human interaction.
A fixed ten-minute wake nevertheless asks M3 to orient even when no meaningful
change exists, while naive deterministic importance scores cannot reliably
recognize contradictions, unfinished intentions, failed expectations,
affective shifts, or future embodied evidence. A second parallel context,
memory, or organ system would recreate the divergence fixed in V1.61.

Decision:

- keep events, memory, sessions, focus, volition, affect, perception, and
  activation history as canonical owners;
- add a versioned fail-closed source registry and a receipt for every observed
  signal;
- use MiniMax M2.7 for non-Scarlet semantic appraisal and ignition
  recommendation, with structured source-backed output and one repair attempt;
- reserve MiniMax M3 for Scarlet herself, including autonomous activations;
- prohibit auxiliary workers from using `mind_shell`, mutating cognitive
  state, or speaking as Scarlet;
- persist provisional candidates and source links without converting them
  into truth, memory, focus, or volition;
- let deterministic wake contracts bypass semantic recommendation only when
  their exact condition is validated;
- give M3 Scarlet final lifecycle authority through one additive `episode`
  shell family;
- preserve the existing autonomy runtime as the sole owner of actual M3
  execution, history, leases, human foreground priority, and completion;
- support `off`, `shadow`, `advisory`, and `active`, with `active` as the
  field-verification default and `shadow` as immediate rollback/replay mode;
  and
- retain a bounded active-mode watchdog so a lack of incoming events cannot
  silently disable internal cognition forever.

Consequences:

The new layer coordinates attention without duplicating cognitive organs or
creating another Scarlet. It can observe and compare heterogeneous future
signals while retaining exact source provenance. Invalid or unknown evidence
fails closed. The periodic scheduler remains a rollback and advisory path.
Active field verification is intentional because deterministic tests alone
cannot prove actual receipts, candidates, no-wake choices, repetition control,
or M3 episode outcomes. Historical replay remains shadow-only.

The Workspace is not an external-action permission system. Notifications,
device actions, and embodied safety remain separate future contracts.

Links:

- `docs/cognitive-workspace.md`
- `backend/app/runtime/cognitive_workspace.py`
- `backend/app/mind/wake_registry.py`
- `backend/app/mind/workspace_contracts.py`
- `backend/app/mind/episode.py`
- `backend/app/runtime/autonomy.py`
- Linear SCA-57

## ADR-0139 - Human And Autonomous Turns Share One Cognitive Runtime Contract

Date: 2026-07-27
Status: accepted for V1.61.0

Context:

V1.60 correctly introduced a separate autonomous chronology and activation
lifecycle, but also introduced a second model-context projection. That made
the same Scarlet receive different memory, session, organ, and policy shapes
depending on whether a human or the scheduler activated her. Production
observation then showed that human turns could not reliably orient to internal
cycles and autonomous work could be misread as prior user dialogue.

Decision:

- preserve one provider-native history for every human session and one
  long-lived provider-native history for all autonomous cycles;
- compile both lifecycles through `scarlet-model-context-v2`;
- use the same automatic memory retrieval/rerank, organ projection, static
  system prompt, context-family audit, and `mind_shell`;
- classify the current turn and every sourceable memory through deterministic
  origin, session kind, turn trigger/actor, and message role;
- place a compact, navigable autonomous-session hint beside human
  `previous_sessions`;
- let autonomous retrieval use recent human and autonomous dialogue as
  source-labelled query evidence, without mixing those messages into one
  provider transcript;
- treat `perception` as external-observation navigation only; and
- render model time in the configured user timezone while serializing API and
  stream timestamps as unambiguous UTC RFC 3339.

Consequences:

There is one Scarlet cognitive runtime with two explicit lifecycle origins.
Interactive behavior remains the baseline and is not reimplemented.
Autonomous cognition gains the same contracts instead of a parallel subset.
The histories remain independently auditable, and provenance prevents Scarlet
from claiming that an internal elaboration was discussed with the user.
An explicit chronology restart archives the old autonomous session rather
than deleting its canonical evidence. Only the current session appears in
consumer autonomous history and receives new scheduled cycles.

Links:

- `backend/app/mind/context_provenance.py`
- `backend/app/mind/context_projection.py`
- `backend/app/runtime/autonomy.py`
- `docs/runtime-context-packs.md`

## ADR-0138 - Autonomous Cognition Uses A Separate Persistent Lifecycle

Date: 2026-07-27
Status: accepted for V1.60.0; context projection refined by ADR-0139

Context:

Scarlet previously existed only while a human turn or a background
maintenance job was active. Reusing human chat turns would falsely attribute
internal activations to the user, while reusing maintenance would make
Scarlet's foreground cognitive activity indistinguishable from deterministic
infrastructure. Future device and embodiment sources also need to be
discoverable without dumping every event into model context.

Decision:

- give each profile one long-lived `scarlet_autonomous` session whose
  provider-native history contains only autonomous activations;
- persist every scheduled activation before model execution and govern it with
  a lease, explicit status, attempt count, outcome, error, and next schedule;
- defer an activation while a human turn is active rather than overlapping two
  foreground Scarlet executions;
- let a started autonomous cycle yield cooperatively at provider/tool
  boundaries when a human turn takes foreground priority, preserving partial
  evidence and rescheduling instead of reporting failure;
- use 600 seconds as the current observation interval; retain cadence as
  configuration rather than treating the earlier 15-minute hypothesis as a
  fixed product rule;
- keep the project-selected native provider unchanged for now; evaluate a
  dedicated MiniMax M2.7 autonomous profile only if measured M3 consumption
  justifies a separate cost/behavior experiment;
- distinguish human turns, autonomous activations, and backend maintenance
  through session kind, turn trigger, actor, runtime context, and prompt policy;
- present only a compact orientation spine and availability map initially,
  leaving exact memories, sessions, and perception events navigable through
  `mind_shell`;
- store perception events append-only, derive channel state and inspection
  cursors, and count only explicit channel opening as inspection;
- preserve thinking, public-personal notes, tool calls/results, and internal
  checkpoints as sourceable cycle history; and
- expose that history in Product UI as a read-only conversation-like surface,
  not as another human chat or a notification feed.

Consequences:

Autonomous cognition gains durable continuity and can evolve independently
from human conversation compaction. Human `previous_sessions` remains clean.
The system can ingest future device or sensor evidence without silently making
it model-visible. V1.60.0 still has no native Android notification adapter,
initiative delivery, or external action capability, and live MiniMax behavior
requires bounded evaluation before the cadence is promoted beyond testing.

Links:

- `backend/app/runtime/autonomy.py`
- historical V1.60 autonomous context builder, removed by ADR-0139; current
  context owner: `backend/app/mind/context_projection.py`
- `backend/app/storage/repository/autonomy.py`
- `backend/app/storage/repository/perception.py`
- `docs/checkpoints/2026-07-24-companion-product-embodiment-direction.md`

## ADR-0137 - Context Families Separate Subject, Observer, Evidence, And Policy

Date: 2026-07-26
Status: accepted for V1.59.0 shadow architecture

Context:

Future companion and embodiment sources will include the human, the human's
device, account services, shared environments, and Scarlet's own sensors.
Routing only by sensor name or agent mode would blur who a datum is about, who
observed it, how strong the evidence is, and which interpretation rules the
model needs. Sending policy prose inside data JSON also weakens the distinction
between instruction and evidence.

Decision:

- classify context through semantic families rather than one family per sensor;
- keep `subject_domain`, `observer_domain`, and `evidence_kind` independent;
- use multi-tag agent-mode eligibility plus a separate activation contract;
- require every family to reference versioned interpretation policy blocks;
- compose policy blocks as system instructions and family packets as dynamic
  evidence;
- fail closed on unknown families and invalid subject/source/evidence
  combinations;
- emit a shadow family-routing receipt for the current V2 model context; and
- keep all future device, personal, environment, relationship, operation, and
  Scarlet-sensor families out of live model context until separately admitted.

Consequences:

Phone location remains phone evidence until a sourceable derived assessment
relates it to the human. Human-device camera/audio cannot become Scarlet
first-person perception. Operation dispatch cannot become success without a
receipt. The project gains a composable policy/context boundary without
changing the working prompt or V2 payload in V1.59.0.

Links:

- `docs/context-family-registry.md`
- `docs/runtime-context-packs.md`
- `backend/app/mind/context_families.py`

## ADR-0136 - Device Signals Enter An Isolated Evidence Ledger First

Date: 2026-07-26
Status: accepted for V1.58.0 exploration

Context:

Scarlet's future companion and embodied direction requires real device
perception and peripheral action. Plugin documentation alone cannot establish
which signals are available, timely, stable, cognitively useful, or safe on a
physical Android device. Sending every available field directly to the model
would create a noisy and architecturally premature context source.

Decision:

- introduce a non-destructive Device Exploration Layer before any cognitive
  device integration;
- preserve raw payloads and explicit normalized projections in a dedicated
  append-only ledger;
- identify observations by install-scoped device, exploration run, probe,
  client event, device time, server receipt time, and app state;
- use an idempotent local outbox so lifecycle and connectivity experiments can
  survive temporary delivery failure;
- exclude every observation from sessions, provider history, semantic memory,
  focus, affect, volition, runtime/model context, traces, and `mind_shell`;
- require separate evidence and owner approval before a signal becomes
  perception, an agentic trigger, or an action capability.

Consequences:

The project can explore Android capabilities aggressively without silently
changing Scarlet's mind or behavior. The ledger may contain sensitive raw
experimental data and is not yet a final consumer privacy or ownership model.

Links:

- `docs/device-exploration-layer.md`
- `docs/branches/perception-context.md`
- `docs/branches/external-operativity.md`

## ADR-0135 - Repository Skills Encode Evidence-Driven Operating Workflows

Date: 2026-07-26
Status: accepted

Context:

Scarlet's repository now spans cognitive architecture, provider behavior,
runtime diagnosis, natural behavioral evaluation, protected VPS deployment,
Product UI, and Android delivery. `AGENTS.md` must remain short and always
read, while canonical documents own architecture and historical evidence.
Relying on conversational recollection for the detailed recurring procedures
would reintroduce mistakes already corrected during real investigations and
rollouts. Creating a skill for every narrow task would produce a second,
conflicting documentation system.

Decision:

- maintain five focused repository-local Codex skills under `.agents/skills/`:
  project stewardship, cognitive changes, runtime debugging, E2E evaluation,
  and VPS/Android release;
- keep Git, Linear, generic coding, and one-off command procedures in the
  existing process instead of creating overlapping skills;
- treat skills as operational derivatives below code, executable contracts,
  `AGENTS.md`, and canonical owner documents;
- require every skill to state trigger boundaries, authoritative sources,
  workflow, safety limits, and an evidence-driven maintenance contract;
- update a skill when verified code, traces, tests, incidents, owner
  corrections, or successful releases establish a durable workflow lesson;
- update canonical policy first when the lesson changes architecture, and
  preserve historical evidence in its original ledger; and
- validate skill presence, frontmatter, naming, source/maintenance sections,
  and documentation links in CI.

Consequences:

Codex can recover high-risk project workflows from the repository on any
machine without inflating the always-read guide. Skills must not become stale
copies of architecture or incident histories, and new skills require a
recurring, materially risky workflow rather than mere convenience.

Links:

- `.agents/skills/README.md`
- `scripts/check_project_skills.py`
- `docs/development-process.md`
- `docs/quality-gates.md`

## ADR-0134 - Hybrid Live Frames Over Durable Stream V2

Date: 2026-07-26
Status: accepted for V1.57.0; supersedes ADR-0133's Capacitor HTTP transport clause

Context:

Production traces proved that Scarlet persisted context, thinking, Mind
lifecycle, notes, and completion incrementally, yet the Android Product Chat
rendered them only after the final answer or after remounting the screen.
Disabling Nginx buffering in V1.56.1 was necessary but insufficient. The
Capacitor HTTP plugin patched global `fetch()` and buffered the native response
body, while detached Stream V2 execution consumed provider deltas without
forwarding them because V2 intentionally persists only completed semantic
events.

Decision:

- retain `scarlet-stream-v2` as the only durable replay, cursor, idempotency,
  and reconnect authority;
- add `scarlet-live-v1` as a tagged connection-local stream that interleaves
  unchanged V2 events with transient thinking, text, and tool-input frames;
- never persist transient frames, and reconnect an interrupted Product client
  to the same turn through V2 at most five times;
- use stable turn/model-step/content-index identities so live blocks mature in
  place instead of duplicating at completion;
- use browser `fetch()` inside the Capacitor WebView, disable the native HTTP
  fetch patch, and explicitly allow packaged localhost origins through CORS;
- show a bounded UI-owned orientation state before canonical preflight events
  become available, without presenting it as Scarlet speech or cognition;
- expose automatic recent-memory, previous-session, and answer-validation
  lifecycle as compact persisted events; and
- render the required model-authored `mind_shell.intent` as the preferred tool
  explanation, keeping deterministic text as a factual fallback rather than
  requiring a second LLM narration call.

Consequences:

Web and Android can compose live blocks while retaining exact durable recovery.
The initial memory/runtime preflight remains synchronous, so its immediate
placeholder is explicitly UI state and disappears when canonical evidence
arrives. Final answer deltas may remain withheld while semantic validation is
active; the UI instead shows a live validation block and publishes only the
accepted answer.

Links:

- BUG-0116
- `backend/app/api/chat_live_stream.py`
- `frontend/src/api.ts`
- `frontend/src/prototype/ChatViewportScreen.tsx`
- `docs/stream-v2-contract.md`

## ADR-0133 - One Product UI Build, Explicit Web And Android Delivery Profiles

Date: 2026-07-25
Status: accepted for V1.56.1

Context:

The connected Product UI existed only under `/prototype`, the historical VPS
profile still selected the older mobile client, and the repository had no
native Android project. The public preview is protected by Nginx Basic Auth.
Embedding that credential in an APK would turn a trusted-preview boundary into
a distributed secret. Copying the whole `public/` tree also packaged more than
150 MB of retired avatar-authoring material.

Decision:

- keep one React Product UI over the same Core contracts for browser and
  Android;
- select it explicitly through versioned `vps` and `android` Vite profiles;
- bundle web assets inside the Android application and point only API traffic
  at `https://honeylabs.cloud/scarlet-api`;
- use Capacitor HTTP for the first native preview; its global fetch-patching
  transport is superseded by ADR-0134 for incremental streams;
- use the owner-approved `scarlet/scarlet` pair as an intentionally visible,
  compiled test credential for both protected web and Android preview;
- forward Basic Auth only after the pair is actively entered, retain the
  resulting authorization value only in memory, and require login again after
  a native cold start;
- treat this known pair as a temporary single-owner preview gate, never as a
  secret or production-grade account boundary;
- emit only the approved runtime portrait and greeting video, leaving puppet,
  PSD, rig, and reference sources outside production bundles; and
- use Capacitor 7 because the current cross-machine Node 20 baseline satisfies
  its supported environment, with JDK 21 used for Android compilation.

Consequences:

The APK and protected web preview now exercise the same Product UI and Core.
The current login remains a private-preview gate, not production identity.
Real account ownership, secure token issuance, release signing, Play Store
delivery, revocable credentials, and persistent native credential storage
remain future work.

Links:

- `frontend/capacitor.config.ts`
- `frontend/.env.vps`
- `frontend/.env.android`
- `frontend/scripts/build-android.mjs`
- `frontend/src/api.ts`

## ADR-0131 - Development Thinking Is Inspectable Evidence, Not UI Speech

Date: 2026-07-24
Status: accepted for V1.55.4; supersedes ADR-0129's thinking-redaction rule

Context:

The Windows Product UI removed `llm.thinking.captured.payload.text` from Stream
V2 and inserted a synthetic "Scarlet sta pensando" bubble before the first
Core event. The owner has explicitly kept provider thinking visible during
development because suppression can hide runtime bugs. A synthetic activity
label also violates the rule that UI presence must remain grounded in real
system events.

Decision:

- preserve completed provider thinking in persisted debug events and Stream
  V2 live/replay payloads during development;
- show that evidence by default, allow a local user preference to hide it,
  and keep other private payload values redacted;
- label provider thinking as diagnostic evidence, never as a public note,
  final answer, semantic memory, or proof of external facts;
- render live thinking only after a corresponding Core event exists; and
- keep deterministic narration bounded to facts actually established by the
  event family.

Consequences:

Development can inspect model behavior end to end without allowing UI prose to
masquerade as Scarlet's authored speech. A future production privacy policy may
change the default presentation, but that is a separate product decision and
must not silently alter the trace/runtime contract.

Links:

- BUG-0114
- `backend/app/api/chat_stream_v2.py`
- `frontend/src/prototype/ChatViewportScreen.tsx`
- `frontend/src/prototype/ChatEventDetailModal.tsx`

## ADR-0132 - Native Stop Reasons Own Turn Finality And Recovery

Date: 2026-07-24
Status: accepted for V1.55.4; supersedes ADR-0130's compatibility-marker path

Context:

The native adapter previously treated any non-empty provider text without a
tool as final, reopened a thinking-only `end_turn`, and relied on a private
`<scarlet-final/>` marker plus semantic fallback. HTTP streaming also owned the
generation iterator, so a disconnected client could cancel the running turn.
These conventions diverged from MiniMax M3's Anthropic-compatible stop
contract and made development evidence harder to interpret.

Decision:

- `max_tokens` preserves the complete native assistant message and continues
  the same response; eight continuations are the pathological-loop guard;
- `tool_use` is the only stop reason that authorizes tool dispatch, and the
  model-controlled tool loop remains unlimited;
- `end_turn` is the only native final boundary; an empty thinking-only
  `end_turn` fails and is not reopened;
- semantic answer validation checks claims and action outcomes, never
  terminality; the marker and finality fallback are removed;
- provider-exposed thinking remains stored and visible as `debug` evidence
  during development;
- transient provider stream exceptions restart the current model step from the
  last complete provider-history boundary, at most five attempts; invalid
  requests and authentication failures are not retried; and
- V2 turn execution outlives the HTTP consumer, while clients resume the same
  turn by `turn_id` and durable `after_seq`.

Consequences:

Native state now follows one provider convention. A provider interruption
cannot resume at an exact token because the upstream stream exposes no resume
cursor; failed-attempt deltas remain transient and the complete model step is
retried. V2 clients avoid durable duplicates because only completed semantic
events are persisted. Legacy V1 deltas remain a debug transport and may expose
attempt-local partial output around retries.

Verification:

- direct MiniMax M3 call returned `end_turn` and the exact requested text;
- controlled signed-thinking continuation proved native blocks and history are
  preserved across `max_tokens`;
- file-backed disconnect test proved the detached runner completes and a new
  consumer recovers `message.assistant.persisted` and `turn.completed`;
- backend suite: 301 tests passed;
- frontend TypeScript/Vite production build passed.

Links:

- BUG-0115
- `backend/app/llm/minimax_client.py`
- `backend/app/api/chat_turn_runner.py`
- `docs/stream-v2-contract.md`

## ADR-0130 - Provider End Turn Owns Native Finality

Date: 2026-07-24
Status: historical V1.55.3 intermediate; superseded by ADR-0132

Context:

ADR-0106 kept `<scarlet-final/>` as the primary boundary and added semantic
recovery after a second omission. Human Product testing reproduced the same
availability failure: MiniMax M3 returned non-empty text with
`stop_reason=end_turn`, omitted the project-local marker, and the fallback
judge rejected the turn. Official MiniMax Anthropic-compatible documentation
defines `end_turn` as the model ending naturally and places final public text
in response content blocks.

Decision:

- a non-empty native response with `stop_reason=end_turn` is structurally final;
- `<scarlet-final/>` remains optional backward compatibility and is stripped
  when present, but is absent from model-facing obligations and recovery copy;
- `max_tokens`, empty output, and other non-terminal results do not satisfy the
  boundary and retain bounded correction followed by explicit failure;
- semantic obligations remain independent and can still trigger correction or
  rejection; and
- validation traces record `provider_stop_reason` and `boundary_source`.

Consequences:

Native completion now follows the provider contract and cannot fail solely on
stochastic marker formatting. Progress-like text returned with `end_turn` is a
completed provider answer and is handled as content quality, not falsely
classified as transport incompleteness. Existing semantic evidence checks,
empty-output safety, provider-history preservation, and GPT finalize behavior
remain intact.

Links:

- BUG-0113
- historical answer-obligations module (removed in V1.64.0)
- `backend/app/api/chat_native_turn.py`
- `docs/api-contract.md`

## ADR-0129 - Product Activity Uses A Bounded Evidence Projection

Date: 2026-07-24
Status: accepted for bounded projection; thinking-redaction clause superseded by ADR-0131

Context:

Real native turns persist useful lifecycle evidence such as context assembly,
memory retrieval, request start, thinking start, Mind tool calls, and organ
state with diagnostic visibility. Rendering only `public` evidence hides
Scarlet's actual movement; rendering all diagnostic/private payloads would
expose implementation detail and protected reasoning.

Decision:

- keep Stream V2 persisted sequence and event identity as the source of truth;
- render authentic public user/note/answer text unchanged;
- authorize only exact diagnostic event types/families needed for consumer
  context, memory, bounded thinking status, Mind actions, and relevant state;
- narrate those lifecycle facts deterministically without deriving semantics
  from provider-native content;
- collapse duplicate tool lifecycle events into one source-linked consumer
  bubble;
- make every semantic movement bubble open a centered evidence receipt with
  sequence, phase, visibility, links, bounded payload, and grouped source
  events;
- keep protected events hidden by default and gate their metadata receipts
  behind a local, logout-cleared `Evidenze private` preference;
- treat `llm.thinking.captured` as protected by type even when historical
  native records label it `debug`; and
- never expose captured-thinking text through Stream V2. Preserve only
  `has_text`, model step/index, phase, sequence, and trace links; complete
  internal evidence remains in the existing debug/trace boundary.

Consequences:

Product Chat can show Scarlet thinking and acting in real time without
pretending that a UI status is her authored inner monologue. Replay rebuilds
the same consumer flow and all receipts remain grounded in durable events.
The local evidence setting is an interface preference, not authorization to
read chain-of-thought, and does not add a cognitive API or mutate Scarlet's
state. New diagnostic families require an explicit allowlist decision before
they can become consumer bubbles.

This decision refines ADR-0127's real-event projection and supersedes
ADR-0128's narrower phrase "render only public evidence"; the honesty boundary
remains unchanged because diagnostic payload text is not promoted to authored
consumer content.

Links:

- `backend/app/api/chat_stream_v2.py`
- `frontend/src/prototype/ChatViewportScreen.tsx`
- `frontend/src/prototype/ChatEventDetailModal.tsx`
- `frontend/src/prototype/ProfileSettingsScreen.tsx`
- `docs/stream-v2-contract.md`

## ADR-0128 - Product UI Executes Existing Core Contracts Or Declares Unavailability

Date: 2026-07-23
Status: accepted

Context:

The approved Product UI contained useful navigation and controls, but most
post-login values and actions were fixtures. Connecting them by inventing
client-only success states would make Scarlet appear to have capabilities that
the Core cannot reproduce or trace.

Decision:

- use only existing consumer-safe health, chat, V2 replay/stream, dashboard
  memory, profile, and settings contracts;
- keep `scarlet/scarlet` as explicit local test access until account contracts
  exist;
- show one centered `Funzione non disponibile` modal for every visible action
  without a matching consumer contract;
- do not route Product controls to internal Mind, debug, or maintenance APIs
  merely because those operational endpoints exist;
- use V2 persisted sequence/event identity as the Chat source of truth, render
  only public evidence, and require a terminal event;
- expose offline/partial Core state without substituting fixtures.

Consequences:

The Product application is now honest about what Scarlet can execute. New
features need an approved Core contract before their controls can stop opening
the unavailable modal. Operator maintenance remains separated from consumer
UX, and local login remains a test convenience rather than authentication.

Links:

- `frontend/src/api.ts`
- `frontend/src/prototype/HomeDashboard.tsx`
- `frontend/src/prototype/ChatViewportScreen.tsx`
- `frontend/src/prototype/ProfileSettingsScreen.tsx`
- `docs/product-ui-prototype.md`

## ADR-0127 - Product Chat Narrates Scarlet's Public Movements

Date: 2026-07-23
Status: accepted; real V2 projection implemented in V1.55.0

Context:

Scarlet is presented as a digital individual, not a final-answer service.
Showing only user and assistant messages hides the real temporal structure of
her work. Showing raw traces, tool payloads, provider thinking, or every
protocol lifecycle duplicate would instead turn the conversation into a
developer log and violate privacy/communication boundaries.

Decision:

- render a turn as an ordered conversation flow containing user text, semantic
  context/memory movements, bounded reflection status, public notes, actions,
  relevant state changes, and final answer;
- narrate deterministic system movements in concise first-person language so
  they remain part of Scarlet's visible presence;
- preserve authentic `assistant.note.emitted` and
  `assistant.answer.completed` text without UI rewriting;
- group lifecycle duplicates into one consumer bubble and retain source event
  families in the inspectable receipt;
- never expose `llm.thinking.captured` text or infer chain-of-thought from
  private/debug evidence;
- order by the future V2 sequence contract and treat terminal events, not
  stream closure, as completion; and
- keep `ui.activity.projected` fixture-only until SCA-49 defines whether the
  consumer-safe projection is backend-emitted or deterministically reduced by
  an authorized client.

Consequences:

The user can follow Scarlet's actions without learning API Mind vocabulary.
The authored/projection boundary remains inspectable, and raw evidence stays
in the developer lens. The prototype does not yet prove real-time wording,
visibility authorization, replay, errors, retries, cancellation, or unknown
event behavior; those remain integration acceptance requirements.

Links:

- `frontend/src/prototype/ChatViewportScreen.tsx`
- `frontend/src/prototype/product.css`
- `docs/stream-v2-contract.md`
- `docs/product-ui-prototype.md`

## ADR-0126 - Prototype Session Persists Locally Until Explicit Logout

Date: 2026-07-23
Status: accepted for the SCA-48 browser approval artifact

Context:

The future Capacitor application should resume where the authenticated user
left it after a reload, browser close, Android backgrounding, or process
recreation. The current prototype has no account backend and cannot claim
secure authentication, but resetting to splash/login on every browser reload
prevents evaluation of the intended application lifecycle.

Decision:

- persist only a prototype authentication marker, username, and last Product
  view under the versioned local key `scarlet-prototype-session-v1`;
- restore that view when `/prototype` opens without an explicit review query;
- update the saved view whenever authenticated Product navigation changes;
- remove the key only on explicit logout or invalid stored structure;
- keep draft messages, fake registration credentials, preferences, and all
  fixture data outside the persistent session; and
- treat `?screen=...` routes as intentional visual-review overrides.

Consequences:

The browser prototype now models resume continuity and gives future Capacitor
work a clear lifecycle expectation. It does not provide identity assurance,
token expiry, encryption, revocation, multiuser isolation, or native storage
semantics. Real authentication must replace the marker behind the approved UI
without reusing it as a security contract.

Links:

- `frontend/src/prototype/AppEntryFlow.tsx`
- `frontend/src/prototype/HomeDashboard.tsx`
- `frontend/src/prototype/ProfileSettingsScreen.tsx`
- `docs/product-ui-prototype.md`

## ADR-0125 - Product Screens Use Local Fixtures Until Flow Approval

Date: 2026-07-23
Status: accepted for the sequential SCA-48 Product UI approval cycle

Context:

The application is being designed one user-facing screen at a time, with direct
owner-agent discussion after each surface. Connecting partially approved
screens to authentication, database, session, memory, or chat contracts would
mix visual decisions with integration work and make iteration less bounded.

Decision:

- implement the complete browser screen sequence before real data integration;
- use deterministic, realistic local fixtures and simulated interactions for
  screens whose final Core wiring has not yet been approved;
- make the fake boundary visible in the review UI and documentation;
- prohibit fixture actions from reading or mutating the backend database;
- preserve direct review URLs for individual screens; and
- perform authentication, Core-port, persistence, and Capacitor integration as
  separately declared work after the screen flow is approved.

Consequences:

The owner can evaluate navigation, hierarchy, responsive behavior, Scarlet's
placement, and visual language without live-data risk. Displayed counts and
records are not runtime evidence, and simulated actions do not prove chat or
session lifecycle behavior. Later integration must replace fixtures behind the
approved surface while preserving the relevant Core contracts.

Links:

- `frontend/src/prototype/HomeDashboard.tsx`
- `frontend/src/prototype/ProductScreens.tsx`
- `docs/product-ui-prototype.md`

## ADR-0124 - Scarlet Uses Identity-Locked Static Portrait States

Date: 2026-07-22
Status: accepted; pauses the active puppet direction in ADR-0123 without deleting its research artifacts

Context:

Two days of layered-puppet, Live2D, PSD, and prepared-animation experiments
showed that the available workflows consume disproportionate effort while
drifting from Scarlet's approved raster identity. The Product UI needs a vivid,
emotionally legible Scarlet sooner than a production-quality deformable puppet
can be authored.

Decision:

- use authored static Scarlet portraits as the active Product UI character
  representation;
- switch portraits by semantic state, with short fades and restrained local UI
  effects rather than simulated skeletal motion;
- preserve the approved half-body portrait as the authority for face, hair,
  makeup, upper body, and rendering, and preserve the approved T-pose as the
  authority for full-body proportions and body regions absent from the portrait;
- encode immutable identity, controlled pose/expression variables, forbidden
  drift, and acceptance checks in a machine-readable identity contract;
- create a supporting 360-degree reference set for hidden geometry, require
  owner approval, and prevent those generated views from overriding either
  approved front authority;
- treat startup greeting, active-chat neutral, and long-idle boredom as the
  first three application states; and
- permit a bounded pre-rendered startup video inside a cropped presentation
  bubble when it preserves identity, has a canonical static fallback, respects
  reduced motion, and does not imply a general puppet capability; and
- retain all layered-puppet artifacts and findings as paused research rather
  than deleting or presenting them as current implementation work.

Consequences:

Scarlet can gain a broad, incrementally generated emotional vocabulary while
preserving image quality and identity. Transitions will not create continuous
body motion or lip synchronization. Those capabilities remain possible future
rig research and are not implied by static portrait changes.

Amendment, 2026-07-23:

- the owner approved the complete supporting 360-degree pack;
- the first startup greeting uses the owner-supplied HappyHorse render;
- the first pass plays from zero and subsequent passes loop from two seconds;
- audio remains muted for autoplay and the crop excludes the source watermark;
  and
- the video remains a splash presentation asset, not a new avatar runtime.

Later amendment, 2026-07-23:

- the greeting is preloaded and held at zero while splash checks run;
- playback starts only after application and video readiness converge;
- it plays from zero to the end exactly once, without the previously proposed
  repeated `2s -> end` loop; and
- the full media `ended` event owns the transition from splash to Login.

Links:

- `docs/scarlet-static-portraits.md`
- `docs/scarlet-live2d-puppet.md`
- `frontend/public/prototype/avatar/static/scarlet-identity-contract-v1.json`
- `frontend/public/prototype/avatar/static/scarlet-static-state-catalog-v1.json`
- `frontend/public/prototype/avatar/static/reference-360/scarlet-reference-360-v1.json`

## ADR-0123 - Scarlet Uses A Structural PSD Reference And Owner-Controlled Transforms

Date: 2026-07-21
Status: accepted; supersedes ADR-0122 placement automation and one-organ PSD blocking

Context:

Generated assets do not share a reliable coordinate system with the approved
portrait. Repeated automated scale and placement attempts consumed substantial
work while remaining less accurate than direct owner adjustment. The owner
provided a complete layered `Poopoo.psd` to clarify practical asset separation,
grouping, clipping, and shading conventions.

Decision:

- parse Poopoo as structural evidence only and forbid all reuse of its pixels,
  identity, anatomy, colors, costume, and textures;
- reproduce its useful construction pattern: painted raster assets, selective
  clipping, additive iris light, detailed eye/mouth stacks, and hair separated
  by depth;
- improve bilateral limb articulation beyond the supplied reference;
- generate Scarlet assets from Scarlet references only, remove chroma, and
  trim to native alpha bounds without automatic scaling or registration;
- stage every candidate hidden in a complete semantic PSD hierarchy;
- let the owner position and scale candidates directly against the locked
  bottom portrait in Photoshop; and
- allow the complete PSD skeleton before every artwork gate closes, while
  keeping unapproved layers explicitly hidden and unregistered.

Consequences:

The agent focuses on asset generation and repeatable PSD organization rather
than unreliable transform calibration. Existing generated assets remain
preserved. A structurally complete PSD no longer implies that its artwork or
rig is approved.

Links:

- `frontend/avatar-authoring/psd/Poopoo.psd`
- `frontend/public/prototype/avatar/poopoo-structural-reference.json`
- `frontend/public/prototype/avatar/scarlet-rig-workspace.json`
- `frontend/avatar-authoring/psd/rig/scarlet-layered-rig-workspace-v2.psd`
- `frontend/scripts/analyze-avatar-psd-reference.mjs`
- `frontend/scripts/build-scarlet-rig-psd.mjs`
- `docs/scarlet-live2d-puppet.md`

## ADR-0122 - Every Anatomical Surface Uses One Generated-Only Review Workflow

Date: 2026-07-21
Status: generated-only artwork principle retained; placement automation and PSD blocking superseded by ADR-0123

Context:

The generated right upper lash was visually approved, but a later forelock
iteration changed method by combining generated artwork with pixels from the
portrait. That made provenance, anatomy, and future motion behavior ambiguous.
The review PSD also revealed that `ag-psd` serializes its child array in
bottom-to-top order, contrary to the earlier assumption.

Decision:

- use the portrait and T-pose only as visual guidance for identity, geometry,
  target dimensions, position, and final comparison;
- generate every complete individual anatomical surface as new artwork on a
  removable chroma background;
- never copy, crop, extract, patch, or composite reference pixels into an
  anatomical asset;
- convert chroma to transparency, then permit only transparent-bound trimming,
  scaling, and x/y placement before review;
- drive all organs and all retries through
  `prepare-scarlet-anatomical-part.mjs` plus a per-part data config, without
  introducing special construction code;
- use the same white, black, checkerboard, target-box, 50% alignment,
  placement-overlay, Difference, and z-stack proof suite for every candidate;
- store review PSD children bottom-to-top: locked reference first, optional
  approved lower surfaces next, and current candidate last; and
- reopen each emitted PSD and fail when the stored layer order differs.

Consequences:

Art style remains an image-generation concern while registration and review
become deterministic and repeatable. The rejected hybrid forelock is removed.
The approved lash artwork is retained and calibrated at `(330,570)`, size
`136x35`; owner approval of that placement remains the current one-organ gate.

Links:

- `frontend/scripts/prepare-scarlet-anatomical-part.mjs`
- `frontend/public/prototype/avatar/scarlet-psd-authoring-contract.json`
- `frontend/public/prototype/avatar/work/eye_scarlet_right_upper_lash_liner/v1/part-config.json`
- `docs/scarlet-live2d-puppet.md`

## ADR-0121 - Scarlet Puppet Authoring Restarts From Two Canonical References

Date: 2026-07-21
Status: accepted

Context:

The generated Live2D material sets, Puppet V2/V3 candidates, and APNG V1/V2
experiments accumulated hundreds of mutually incompatible outputs. Some
preserved neutral pixels but failed semantic ownership; others reconstructed
hidden areas with identity drift or produced unacceptable motion distortion.
Keeping those files and executable generators active made accidental reuse more
likely than a clean, reviewable restart.

Decision:

- keep only the approved half-body portrait and the full-body T-pose as visual
  inputs;
- use the portrait as the authority for face, hair, neck, torso, and every
  visible half-body identity detail;
- use the T-pose only as secondary geometry and verification evidence for
  hands, arms, legs, and regions absent from the portrait;
- remove all prior generated images, PSDs, proofs, animation frames, contracts,
  and executable avatar-generation commands from the active workspace;
- author exactly one complete transparent anatomical surface at a time, in
  front-to-back production order;
- store every admitted surface as a full-canvas `941x1672` RGBA PNG at final
  native coordinates;
- validate visible pixels directly over the locked portrait and validate
  hidden completions only in isolation and beneath approved foreground layers;
  and
- keep the master PSD engine-neutral until the anatomical material set is
  sufficiently complete to choose the production rig runtime.

Consequences:

The avatar workspace is small and unambiguous again. Historical experiment
findings remain in documentation, but no historical raster may seed a new
surface. PSD assembly is blocked; the next accepted artifact must be one
owner-approved frontmost anatomical PNG and its review evidence.

Links:

- `docs/scarlet-live2d-puppet.md`
- `frontend/public/prototype/avatar/scarlet-psd-authoring-contract.json`
- `frontend/public/prototype/scarlet-character-v1.png`
- `frontend/public/prototype/avatar/source/scarlet-full-body-tpose-reference-v1.png`

## ADR-0120 - Prepared Scarlet Animations Use Canonical-Neutral APNG Delta Frames

Date: 2026-07-21
Status: rejected and superseded by ADR-0121

Context:

Manual Live2D material separation repeatedly drifted from the approved portrait
and required disproportionate reconstruction work before any motion could be
tested. Full-frame image generation preserved the broad identity but changed
unrelated details and framing between poses.

Decision:

The experiment originally decided to:

- use APNG as the active prepared-animation container;
- require the exact canonical neutral as both first and last decoded frame;
- generate one local gesture master and derive intermediate poses from that
  master plus the neutral identity reference;
- composite only reviewed motion corridors over the exact neutral rather than
  accepting full generated frames;
- validate pixel-locked identity regions, source/frame provenance, APNG timing,
  loop count, alpha, MIME type, browser behavior, and final rest state; and
- retain Live2D artifacts as paused research evidence rather than deleting or
  representing them as completed runtime assets.

Consequences:

The experiment demonstrated that APNG can preserve prepared raster frames but
cannot create coherent motion. V1 remained discontinuous and V2 introduced
unacceptable distortion. Generated artifacts and builders were removed by the
reference-only reset. APNG remains only a possible future export container for
motion rendered by a real rig.

Amendment, 2026-07-21:

- APNG is the prepared-animation delivery container, not a motion-generation
  mechanism;
- a production candidate must first render a continuous 30 fps source timeline;
- different poses may not be bridged by long frame delays;
- local raster meshes may deform approved source pixels inside the motion
  corridor without creating a full-body rig;
- static holds may use longer durations because no visual movement occurs; and
- V1 is retained as rejected motion evidence while V2 tests the first local-rig
  interval separately.

Historical record: `docs/scarlet-apng-animation.md` and
`docs/activity-log.md`.

## ADR-0119 - Puppet Rig Layers Are Complete Reference-Anchored Surfaces

Date: 2026-07-21
Status: principle retained; generated V3 artifacts superseded by ADR-0121

Context:

Audit of the Puppet V2 PSD showed that structural layer count did not imply
rig readiness. Most materials were either old generated assets or perforated
master cutouts paired with hidden legacy support. The visible neutral happened
to resemble Scarlet, but moving a layer would reveal the wrong underlay or a
transparent gap.

Decision:

- forbid legacy generated materials, rejected eye V1 assets, and Puppet V2
  outputs as artistic inputs to Puppet V3;
- construct every rig material as one complete semantic surface;
- treat visible-pixel partition masks as provenance evidence rather than
  anatomical rig contours; lock separately reviewed geometry and landmarks in
  the V3 contract;
- derive every face and head organ exclusively from the approved half-body
  portrait; use that portrait as the primary identity source for the visible
  upper body, while the T-pose controls full-body registration, lower-body
  organs, and body regions not sufficiently exposed by the portrait;
- use generation only to reconstruct pixels that are removed, hidden, or
  occluded, then flatten those pixels into the same complete material;
- store every material and placement mask on the exact `941x1672` master grid
  at top-left origin `(0,0)`; crops are proof-only and PSD transforms may not
  scale or reposition rig artwork;
- keep source/reference masks and proof layers outside the eventual rig stack;
- require isolated transparency, black/white background, re-overlay, z-index,
  and direct visual review for each organ before PSD admission; and
- block PSD assembly until all required neutral surfaces are approved.

Consequences:

Puppet V2 is rejected evidence. Puppet V3 starts with a complete face skin
underlay whose silhouette comes from the portrait, whose clean skin anchors
remain exact reference pixels, and whose generated content fills only missing
regions. Facial organs, hair, body, PSD assembly, and Cubism work remain blocked
behind their progressive review gates.

Links:

- `frontend/public/prototype/avatar/scarlet-puppet-v3-contract.json`
- `frontend/scripts/prepare-scarlet-face-base-v3.mjs`
- `docs/scarlet-live2d-puppet.md`

## ADR-0118 - Puppet PSD Separates Neutral Identity From Hidden Rig Support

Date: 2026-07-20
Status: rejected and superseded by ADR-0119

Context:

The approved iris workflow established that a moving surface must be complete,
semantically isolated, and independently occluded, but applying every generated
completion directly in the neutral pose changed Scarlet's identity. Earlier
support boards also used coordinate systems and scales that did not match the
locked portrait and T-pose masters.

Decision:

- build the Puppet V2 PSD from explicitly registered materials on the locked
  `941x1672` T-pose canvas;
- keep authoritative visible-master artwork separate from reconstructed
  hidden-support artwork and disable support layers in the neutral pose;
- use exact neutral master-eye composites by default while retaining sclera,
  iris, lash, and aperture materials as a hidden stack for Cubism rigging;
- reuse the owner-approved right-iris V2 texture for both equivalent irises,
  with independent position and deformation;
- permit old generated boards only as labelled hidden support or optional
  variants, never as visible identity authority; and
- treat the generated PSD as an assembled authoring candidate, not as a
  completed Live2D model or proof of motion quality.

Consequences:

The repository can reproduce the 59-material, 103-layer artifact, but later
audit proved that 51 materials depended wholly or partially on the superseded
generated material pack. Separating visible cutouts from hidden support did not
produce complete rig surfaces. The PSD is retained as rejected evidence and
must not enter Cubism.

Links:

- `frontend/public/prototype/avatar/scarlet-puppet-v2-contract.json`
- `frontend/scripts/prepare-scarlet-puppet-v2.mjs`
- `frontend/public/prototype/avatar/source/fidelity-v1/semantic-parts/puppet-v2/`
- `docs/scarlet-live2d-puppet.md`

## ADR-0117 - Scarlet Puppet Fidelity Is Semantic And Perceptual, Not Retina-Pixel Identical

Date: 2026-07-20
Status: accepted; right iris V2 owner-approved as bilateral source

Context:

The first eye reconstruction mixed semantic surfaces, while later attempts to
preserve exact visible pixels created obvious rectangular patches. A statistical
per-channel color correction also improved numeric similarity while visibly
contaminating the pupil and limbal ring. Exact retinal color matching is not a
useful goal when it damages the character effect or moving material.

Decision:

- preserve Scarlet's overall eye identity, violet/fuchsia/cyan language,
  proportions, anime rendering, and visual effect;
- allow minor internal iris color variation;
- keep anatomy, semantic ownership, z-index behavior, clean alpha, and absence
  of foreign pixels as hard constraints;
- reconstruct occluded artwork through a coherent generated surface rather than
  flat-color fill or pasted source rectangles; and
- evaluate isolated, actual-scale, and rig-stack proofs visually before owner
  approval.

Consequences:

The V1 eye set is rejected evidence. The V2 right iris is the approved shared
iris-and-pupil source for both eyes, with catchlight and eyelid reserved for
separate foreground layers. ADR-0118 governs how this approved source and the
remaining candidate materials enter the assembled PSD.

Links:

- `frontend/public/prototype/avatar/scarlet-right-iris-v2-contract.json`
- `frontend/scripts/prepare-scarlet-right-iris-v2.mjs`
- `docs/scarlet-live2d-puppet.md`

## ADR-0116 - Scarlet Puppet Materials Are Semantic Surfaces With Explicit Occlusion

Date: 2026-07-20
Status: accepted boundary; first eye reconstruction candidate pending owner review

Context:

The 34-part visible-pixel pass reproduced every selected master pixel exactly,
but a neutral zero-difference composite did not prove that each PNG was a valid
moving material. The eye ellipse demonstrated the distinction: it contained
iris, sclera, liner, and eyelid skin because all were geometrically inside the
same mask. Moving that layer would move foreign pixels with the iris. Similar
depth or underlay risks exist in the face, mouth, hair, neck, torso, and every
articulated joint.

Decision:

- treat the first 34 exports as pixel-partition and provenance evidence, not
  direct Live2D layers;
- require every rig material to own one semantic surface and record its
  occluders, draw order, clipping, hidden continuation, and movement proof;
- preserve authoritative visible pixels byte-for-byte while storing every
  reconstructed hidden pixel as separately labelled artwork;
- build complete eye beds and irises, use one aperture mask per eye, and draw
  separate eyelid-skin and upper/lower lash materials above them;
- split materials that cross depth bands, especially front/rear hair and
  neck-skin/collar; and
- approve reconstruction in isolated eye, face, hair, and body-joint gates
  before PSD assembly or Cubism rigging.

Consequences:

Neutral fidelity remains measurable, while movement fidelity gains an explicit
contract. The eye gate now produces clean semantic sources, separately labelled
hidden completion, clipping, and gaze/blink/provenance proofs. Its generated
candidate does not advance to PSD assembly until the owner approves it and the
later edge/alpha pass is completed.

Links:

- `frontend/public/prototype/avatar/scarlet-occlusion-contract.json`
- `frontend/public/prototype/avatar/scarlet-eye-assets-contract.json`
- `frontend/public/prototype/avatar/scarlet-visible-parts-matrix.json`
- `frontend/scripts/validate-scarlet-avatar.mjs`
- `docs/scarlet-live2d-puppet.md`

## ADR-0115 - Scarlet Visible Puppet Materials Preserve Master Pixels Before Hidden Completion

Date: 2026-07-20
Status: accepted pipeline; visible pieces pending owner review

Context:

Generated boards and heuristic separation produced recognizable but
identity-inaccurate face, hair, and body materials. A flattened source cannot
prove hidden anatomy, and repeated automatic repair risks replacing the
approved Scarlet identity rather than separating it.

Decision:

- lock the approved portrait and full-body T-pose by path, dimensions, and
  SHA-256 before any extraction;
- use one measured similarity transform for the complete portrait group and
  never independently scale or rotate portrait child materials;
- export visible neutral materials only from unmodified master RGBA pixels;
- give every material an exact source, anatomical name, native bounding box,
  binary mask, full-canvas layer, crop, and re-overlay proof;
- prevent duplicate visible-pixel assignment and require zero RGBA mismatch in
  selected-region reconstruction;
- keep hidden continuations and expression/hand variants in a later,
  explicitly synthetic and reviewable gate; and
- retain previous generated candidates as historical references, never as
  final identity-authoritative input.

Consequences:

Visible identity fidelity is measurable before Photoshop or Cubism work. The
current 34-layer set is not yet a complete puppet because deformation-safe
underlays, variants, PSD assembly, ArtMeshes, and rigging remain pending.

Links:

- `frontend/public/prototype/avatar/scarlet-fidelity-contract.json`
- `frontend/public/prototype/avatar/scarlet-visible-parts-matrix.json`
- `frontend/scripts/prepare-scarlet-visible-parts.mjs`
- `docs/scarlet-live2d-puppet.md`

## ADR-0114 - Scarlet Uses An Identity-Preserving Live2D Puppet

Date: 2026-07-20
Status: superseded as active delivery path by ADR-0120; retained as research

Context:

The approved transparent portrait establishes Scarlet's identity, but CSS
motion cannot produce expression or gesture. An image-to-3D TripoAI probe
created a recognizable OBJ with defects severe enough to reduce face, hair,
surface, and animation quality. Scarlet is most often shown at half-body scale,
where small identity errors are especially visible.

Decision:

- use one full-body Live2D puppet as Scarlet's primary Product UI avatar;
- preserve the approved portrait as the identity master and use generated
  full-body art only to extend anatomy and clothing;
- author the puppet from separated raster materials, ArtMeshes, deformers,
  standard Cubism parameters, custom arm/hair/light parameters, expressions,
  physics, and layered motions;
- use a model-independent semantic contract for action, emotion, gaze, speech,
  gesture, framing, priority, TTL, and transitions;
- let screens crop or frame the same puppet as portrait, half body, or full
  body rather than maintaining unrelated character bases;
- optimize the first motion set for half-body anime interaction: listening,
  thinking, speaking, greeting, winking, nodding, and hand gestures;
- retain APNG only for bounded cinematic transitions, effects, or fallback,
  never as the primary interactive rig; and
- do not report a Live2D implementation as complete until a real Cubism export
  passes deformation, blending, mobile rendering, and identity review.

Consequences:

The avatar can preserve the raster identity while gaining independently
controllable face, gaze, mouth, body, arms, hair, and light channels. Authoring
requires material separation and Cubism Editor work before the official Web SDK
can be integrated. The earlier GLB/VRM implementation direction in ADR-0113 is
superseded; its identity and palette decisions remain active.

Links:

- `docs/scarlet-live2d-puppet.md`
- `frontend/public/prototype/avatar/scarlet-avatar-authoring.json`
- `frontend/src/prototype/avatar/scarletAvatarContract.ts`
- `frontend/src/prototype/avatar/scarletAvatarController.ts`

## ADR-0113 - Scarlet Uses One Adult Anime Identity Across Product Surfaces

Date: 2026-07-20
Status: accepted identity; renderer clause superseded by ADR-0114

Context:

The Product UI needs a recurring visual identity that can later express
Scarlet's actions and affect across splash, update, authentication, home, chat,
and future embodied surfaces. The first CSS mascot read as a small robot and
could not support a sufficiently human range of gaze, pose, speech, or emotion.

Decision:

- establish Scarlet as an unmistakably adult woman with an apparent age near
  25, rendered in a polished modern Japanese anime style;
- make attractiveness derive from face, gaze, makeup, hair, styling, and
  presence rather than revealing clothing or childlike proportions;
- use pearl white and graphite for structural clothing, with Timber cyan and
  fuchsia as iridescent accents in eyes, hair, makeup, and digital details;
- treat the generated transparent bust as a concept asset for the static
  splash, not as the final animated implementation;
- keep the reusable avatar API semantic (`action`, emotion, gaze, framing) so
  the renderer can change without rewriting every screen; and
- keep all current work fixture-only and disconnected from Core state.

Consequences:

The splash now has a recognizable human Scarlet identity and an approval
artifact for future modeling. Real facial expressions, body actions, speech,
and affect remain future puppet work and must not be implied by CSS movement
over the concept image. ADR-0114 records the later decision to use Live2D
rather than GLB/VRM for the Product UI avatar.

Links:

- `frontend/public/prototype/scarlet-character-v1.png`
- `frontend/src/prototype/ScarletMascot.tsx`
- `frontend/src/prototype/SplashScreen.tsx`
- `docs/assets/product-ui-prototype/mobile-splash.png`

## ADR-0109 - Approve Product Shape Before Connecting It To Core

Date: 2026-07-19
Status: proposed implementation; owner approval pending on SCA-48

Context:

The V1 cockpit and mobile consumer grew directly around runtime and provider
diagnostics. V2 now has a provider-independent stream contract, but connecting
a new UI before its information hierarchy is accepted would combine product
design, stream migration, component extraction, and backend integration in one
high-risk change. The owner requires a static mobile-first prototype first.

Decision:

- implement `/prototype` as an isolated React route with no backend calls;
- use fixtures conforming to `scarlet-stream-v2` and current compact memory and
  session contracts;
- keep chat primary and make continuity, memory, state, and settings nearby
  product surfaces;
- expose diagnostics through a developer lens in the same application rather
  than duplicating the UI or placing raw payloads in ordinary conversation;
- represent loading, streaming, reconnect, error, and empty states before
  integration;
- use Tailwind CSS 4 and temporary local component equivalents while Catalyst
  remains unavailable; and
- after rejection of the generic first visual pass, use the Scarlet Signal
  identity system: fuchsia for presence/direct interaction, scarlet for action
  and continuity, light blue for cognition/provenance, and cool neutrals only
  as structural support;
- avoid the standard AI-chat composition by using an open editorial response
  surface, numbered continuity traces, compact memory hooks, and one integrated
  dark technical lens; and
- prohibit SCA-49/SCA-50 integration from treating the prototype as accepted
  until explicit owner approval is recorded on SCA-48.

Consequences:

Visual and interaction decisions can be inspected independently from runtime
behavior. Existing clients remain compatible, fixture data cannot mutate the
Core, and later implementation has a concrete approval target. The temporary
prototype components are not yet the shared Product UI design system.

Links:

- Linear SCA-48
- `frontend/src/prototype/PrototypeApp.tsx`
- `frontend/src/prototype/prototypeData.ts`
- `docs/product-ui-prototype.md`

## ADR-0112 - The SDK Owns One Public Contract Source And Executable Conformance

Date: 2026-07-19
Status: accepted for V1.54.0

Context:

SCA-53 and SCA-54 established strict contracts and a real host, but the model
classes still lived under an internal Core namespace and the only subprocess
fixture was handwritten. Copying models into a nominal SDK would let host and
module validation drift, while documentation-only examples would not prove
that an independently created module actually speaks the protocol.

Decision:

- publish `scarlet_agentic_module_sdk` as the canonical owner of manifest and
  Port V1 models imported by both module authors and the host;
- retain the old Core contract module only as a compatibility re-export;
- distribute the SDK as a standalone Pydantic-only wheel while also including
  it in the backend build;
- provide a conservative module-side JSONL server rather than exposing any
  Core repository, database, provider, secret, or prompt owner;
- make scaffold output executable and require the unmodified output to pass
  both standalone conformance and the real host;
- validate manifest relationships, modes, lifecycle, every declared port,
  capability limits, structured errors, and correlated request evidence; and
- include the public package in lint, typing, test, and coverage gates.

Consequences:

SDK 1.0.0, app V1.54.0, and protocol V1 are separate version identities. A
passing conformance report proves protocol compatibility, not semantic quality,
operator approval, package integrity, hostile-code safety, or chat integration.
The operator must still pin the exact manifest digest before host execution.

Links:

- Linear SCA-55
- `docs/agentic-module-sdk.md`
- `backend/scarlet_agentic_module_sdk/`
- `backend/sdk/pyproject.toml`

## ADR-0111 - Module Host Is Opt-In, Out-Of-Process, And Operator-Pinned

Date: 2026-07-19
Status: accepted for V1.53.0

Context:

SCA-53 defined what optional modules may declare but deliberately did not load
code. A host must add useful extension mechanics without making optional code a
new owner of Core state, leaking secrets through process inheritance, or
claiming security properties that a local subprocess cannot provide.

Decision:

- discover only direct child installs under explicit operator roots;
- require both approved module id and exact manifest SHA-256 before execution;
- use the SCA-53 planner unchanged for compatibility, modes, and dependencies;
- execute one persistent `stdio-json-v1` subprocess per active module without a
  shell, with an allowlisted environment, serialized calls, bounded framing,
  timeouts, process-group termination, and supported OS resource limits;
- validate typed and capability-level output before composition;
- quarantine a failed module and its required runtime dependents while allowing
  unrelated modules and the Core to continue;
- persist session-owned receipts through existing traces/events, with no new
  canonical state table; and
- keep the host opt-in and disconnected from native chat until a product module
  has its own approved integration issue.

Consequences:

Disabling or omitting every module restores the unchanged Core path. Digest
pinning protects the manifest declaration but is not package signing. Linux
receives hard address-space/file-descriptor limits; portable CPU-percentage
enforcement and hostile-code sandboxing remain future deployment work. SCA-55
can now build an SDK against a real protocol and fixture rather than inventing
host behavior.

Links:

- Linear SCA-54
- `docs/agentic-module-host.md`
- `backend/app/agentic_modules/host.py`
- `backend/app/agentic_modules/transport.py`

## ADR-0110 - Agentic Modules Use Strict Manifests And Typed Core Ports

Date: 2026-07-19
Status: accepted for V1.52.0 before Module Host implementation

Context:

The closed Core must support future perception, action, and cognitive
capabilities without letting optional code import persistence, prompt,
provider, or runtime owners directly. The existing organ registry describes
internal Core capabilities and cannot serve as a plugin manifest. Agent modes
also describe Scarlet's foreground posture; maintenance and future Dream work
are background processes and must not become modes for routing convenience.

Decision:

- introduce strict `agentic-module-manifest-v1` Pydantic contracts;
- require stable module identity, SemVer, Core and exact port compatibility,
  agent-mode tags, typed capabilities, allowlisted permissions, explicit
  dependencies, bounded resources/timeouts/health, and lifecycle policy;
- expose only versioned context, prompt, command, event, health, and lifecycle
  envelopes as future Core Ports;
- reject direct database, secret, provider, repository, prompt-owner, and Core
  internal access by making those permissions inexpressible;
- select modules from one active agent-mode tag, require compatible dependency
  closure, order dependencies first, and keep missing optional dependencies as
  warnings rather than hidden fallbacks;
- keep system processes separate from agent modes; and
- leave discovery, execution, supervision, enforcement, and isolation to
  SCA-54, with no untrusted-code sandbox guarantee in this contract.

Consequences:

SCA-54 has an executable input contract and cannot invent another permission
or dependency model inside the host. Modules remain optional: the Core and its
canonical state are valid when none are installed. Strict schemas increase
upfront compatibility work, but make drift and unsupported access explicit.
The first host must be restricted to operator-installed modules and enforce
every declared boundary at runtime; validation alone is not process isolation.

Links:

- Linear SCA-53
- `docs/agentic-modules-contract.md`
- `backend/scarlet_agentic_module_sdk/contracts.py`
- `backend/app/agentic_modules/contracts.py` (compatibility re-export)
- `backend/app/agentic_modules/validation.py`

## ADR-0108 - Product Clients Reduce Durable Runtime Events, Not Provider Deltas

Date: 2026-07-19
Status: accepted for V1.51.0

Context:

The V1 native stream mixed transient provider deltas with copies of persisted
runtime events. That supported a live debug cockpit but left clients coupled
to provider block names, a connection-local sequence, and no replay cursor.
Web and future Android clients need to reconstruct the same turn after a
disconnect without copying provider protocol logic.

Decision:

- add the provider-independent `scarlet-stream-v2` Product UI port;
- project only persisted `CognitiveEvent` rows into V2;
- use the persisted event id as the idempotency key and the session-global
  sequence as the reconnect cursor;
- enrich persisted message and terminal events at projection time instead of
  duplicating message text into the event table;
- provide session replay after an exclusive sequence cursor;
- make `turn.completed` and `turn.failed` the only terminal signals;
- publish an executable reducer that orders, deduplicates, detects gaps, and
  reconstructs messages, notes, tools, answers, and errors; and
- retain the V1 stream during client migration.

Consequences:

Product clients no longer need MiniMax/Anthropic block semantics. Provider
deltas remain useful for V1 diagnostics but are deliberately absent from the
replayable contract. Reconnect recovers persisted state; it does not promise
to resume a provider generation canceled by transport loss. Full traces stay
available to the developer lens without bloating the Product UI event stream.

Links:

- Linear SCA-47
- `backend/app/api/chat_stream_v2.py`
- `docs/stream-v2-contract.md`
- `docs/api-contract.md`

## ADR-0107 - Close Core V1 And Separate V2 Product And Module Boundaries

Date: 2026-07-19
Status: accepted architecture contract for V2 planning

Context:

V1.50.1 is deployed, release-accepted, and supported by deterministic,
behavioral, deployment, and database-boundary evidence. The repository already
has stable runtime owners, but current-state documentation still mixed
implemented Core contracts with old V1 priorities, future cognitive research,
the experimental GPT adapter, UI rework notes, and not-yet-designed module
architecture. That made a mature baseline look perpetually unfinished and
left later V2 issues without named dependency boundaries.

Decision:

- declare V1.50.1 the closed API Mind Core baseline;
- distinguish API Mind Core Runtime, Product UI, External Adapters, and
  Agentic Modules as separate architecture layers;
- keep native selected-provider execution authoritative;
- classify the GPT Actions bridge as an optional experimental adapter to the
  same Core, never an architectural driver;
- preserve `mind_shell(command, intent)` and `scarlet-model-context-v2` as the
  stable model-facing cognitive contracts;
- retain `/mind/*`, debug, maintenance, repositories, and rich context as
  internal implementation/diagnostic boundaries;
- treat Product UI V1 endpoints as compatible until the explicit
  `scarlet-stream-v2` migration defines the V2 client contract;
- reserve Agentic Module terminology as planning vocabulary until SCA-53
  accepts manifest and Core Port schemas; and
- keep monitoring findings, branch limits, bugs, and ideas sourceable without
  representing all of them as active Core work.

Consequences:

Core closure is a baseline statement, not a claim that every research branch
is mature or that future fixes are forbidden. Breaking Core changes require an
explicit migration and rollback plan. Product UI and Agentic Modules depend on
named Core ports and may not duplicate cognition or access persistence
internals directly. Historical plans remain evidence but point forward to the
active V2 roadmap rather than silently authorizing work.

Links:

- Linear SCA-46
- Linear SCA-51
- `docs/core-runtime-contract.md`
- `docs/project-state.md`
- `docs/api-contract.md`

## ADR-0106 - Second Native Marker Miss Uses Semantic Finality, Not Auto-Acceptance

Date: 2026-07-18
Status: accepted for V1.50.1

Context:

The private native marker remains a useful cheap structural distinction between
work notes and final answers, but focused V1.50.0 production smoke showed
MiniMax can omit it in both the original and corrected response while still
producing a complete answer. Treating every second non-empty draft as final
would reintroduce the progress-note bug; failing every such draft makes the
runtime unavailable because of formatting variance.

Decision:

- retain the private marker as the primary boundary and strip it before public
  persistence;
- retain exactly one model correction after the first miss;
- only after the second marker miss, add one hard semantic obligation requiring
  a complete, standalone, conclusive answer that does not depend on rejected
  public text;
- use the existing structured LLM judge for that natural-language decision;
- accept the original draft unchanged only when all semantic obligations pass;
  and
- fail closed when the judge is unavailable, the draft is a note/fragment, or
  another hard obligation fails.

Consequences:

The runtime no longer turns repeated marker omission alone into an outage, but
it does not weaken incomplete-response rejection or rewrite Scarlet's voice.
The fallback adds one validator call only on the rare second-miss path and is
fully traceable in `answer.validation`.

V1.50.1 deployed this decision at merge `676e560`. The first protected native
repeat completed through the unchanged primary marker path; controlled tests
retain explicit evidence for both semantic-recovery polarities.

Links:

- Linear SCA-44
- BUG-0094
- EXP-0079
- historical answer-obligations module (removed in V1.64.0)
- `backend/app/api/chat_native_turn.py`

## ADR-0105 - Evaluator Acceptance Requires Model Delivery And Completed Turns

Date: 2026-07-18
Status: accepted for V1.50.0

Context:

The frozen automatic-memory case observed rich retrieval selection but not the
canonical V2 packet. It could also pass after the native turn failed because
the controlled provider omitted the private final-answer boundary. Intermediate
traces are valuable evidence, but neither selection nor request creation proves
that Scarlet received usable context and produced a valid answer.

Decision:

- preserve historical evaluator versions after they become comparison
  baselines;
- add a complementary versioned gate when a new architectural boundary needs
  stronger evidence;
- verify automatic-memory delivery at rich selection, V2 projection,
  `llm.request`, provider-observed input, and exact navigable provenance;
- require completed persisted turn and assistant-answer evidence in every case
  that claims successful agent behavior; and
- include a negative control proving the gate rejects an incomplete turn even
  when earlier traces look valid.

Consequences:

Retrieval and model delivery can no longer be conflated, and a failed provider
turn cannot satisfy a behavioral gate through intermediate events. The frozen
V1 source remains immutable. Exact provenance repair is test-only on a
disposable copy and remains guarded by candidate digest and backup reference.

Links:

- Linear SCA-43
- BUG-0093
- EXP-0078
- `docs/evaluations/v1.50-model-facing-memory-gate.md`

## ADR-0104 - Action Recovery Uses Deterministic Candidate Recall And Semantic Judgment

Date: 2026-07-18
Status: accepted for V1.49.1

Context:

One API Mind operation may fail because a model emits incomplete syntax and
then succeed after correction. Treating each call independently makes a
truthful final success impossible, while declaring every later call with the
same command family equivalent would overwrite real failures and confuse
semantically different actions.

Decision:

- rebuild tool-derived answer obligations from the complete authoritative
  current-turn call sequence on native and GPT transports;
- use the canonical shell operation only to recall bounded later candidates;
- link candidates only for recoverable failures with a later successful
  same-operation attempt;
- preserve the initial failure, all call/trace references, commands, intents,
  and results in the hard obligation; and
- require the LLM answer validator to decide material equivalence and truthful
  wording. No string, score, or operation-name match may itself declare the
  action recovered.

Consequences:

Scarlet can truthfully describe final success after a real correction without
erasing the failed attempt. Unrecovered, non-recoverable, different-operation,
and semantically unrelated same-operation attempts remain visible and hard.
Persisted GPT manifests cannot remain stale because dynamic tool obligations
are reconstructed while static obligations are preserved.

Links:

- Linear SCA-42
- BUG-0091
- `docs/evaluations/v1.49.1-action-retry-obligations.md`

## ADR-0103 - Maintenance Keeps One Runtime Facade With Three Domain Owners

Date: 2026-07-18
Status: accepted for V1.49.0

Context:

The maintenance runtime combined scheduling and worker lifecycle, episodic
summary/history compaction, and semantic-memory review/proposal resolution.
Those paths share a job ledger but have different evidence and mutation
authority, making the monolith difficult to inspect without changing behavior.

Decision:

- `maintenance_scheduler` owns scheduling, due-job dispatch, worker lifecycle,
  final job state, and event orchestration;
- `maintenance_history` owns summary audit/repair, idle summaries, idle checks,
  and history compaction execution;
- `maintenance_memory` owns missed-memory review, proposal creation, cautious
  resolution, prompts, and auto-apply guards;
- `maintenance_shared` owns only job-kind constants and cross-domain types;
- `maintenance.py` remains the stable public facade; and
- this ownership split does not change job policy, prompts, thresholds, API
  contracts, or expose maintenance as an additional model-facing surface.

Consequences:

Summary/history and memory policy can now be tested and evolved independently,
while scheduling remains the single authority for state transitions. A
successful job status remains technical evidence only; behavioral acceptance
still requires direct inspection of summaries, memory decisions, actions, and
persisted outcomes.

Links:

- Linear SCA-37
- `docs/evaluations/v1.49-maintenance-domains.md`

## ADR-0102 - Memory Mutation Domains Share A Stable Facade, Not Policy

Date: 2026-07-18
Status: accepted for V1.48.0

Context:

After read extraction, `app.mind.memory` still combined write policy, fact
materialization, lifecycle, maintenance proposals, and relation evidence.
These domains share persistence primitives but have different callers and
different authority: relation similarity is evidence, while lifecycle is an
explicit state mutation.

Decision:

- `memory_write` owns write validation, exact deduplication, traces, fact
  materialization/backfill, and retrieval-artifact synchronization;
- `memory_lifecycle` owns deprecate/supersede contracts and propagation to
  memory facts;
- `memory_proposals` owns maintenance candidate preflight, idempotent ledger
  records, payloads, and explicit proposal application;
- `memory_relations` owns atomic conflict and maintenance-overlap evidence;
- `memory.py` remains the stable re-export facade; and
- no similarity detector may auto-merge or auto-deprecate memory as a side
  effect of this ownership split.

Consequences:

Mutation behavior can now be changed and tested by authority boundary. The
proposal pipeline reuses write/fact primitives rather than copying them, and
relation outputs remain inspectable evidence rather than deterministic truth.

Links:

- Linear SCA-38
- `docs/evaluations/v1.48-memory-mutation-surface.md`

## ADR-0101 - Memory Read Commands Have A Dedicated Owner Behind The Facade

Date: 2026-07-18
Status: accepted for V1.47.0

Context:

`app.mind.memory` combined read-only retrieval/navigation with writes,
lifecycle, maintenance proposals, and relation evidence. Search and graph also
carry substantial ranking, temporal, provenance, and presentation behavior
that can be tested independently from mutation policy.

Decision:

- `app.mind.memory_read` owns search, read, facts, graph, their request bodies,
  retrieval helpers, temporal filtering, graph traversal, and read payloads;
- `app.mind.memory_shared` owns only the field aliases, canonical payload,
  common traced errors, and activity recorder required by both read and
  mutation code;
- `app.mind.memory` re-exports the existing public names and remains the stable
  dispatcher/API/maintenance facade;
- command registry, shell parser/presentation, routes, traces, ranking policy,
  lifecycle, proposals, conflict evidence, and database schema remain
  unchanged.

Consequences:

Manual cognition can evolve and be verified without editing mutation policy,
while write/lifecycle work retains one compatibility boundary. The small
shared owner prevents circular imports and duplicate payload contracts rather
than becoming a second public model surface.

Links:

- Linear SCA-36
- Linear SCA-38
- `docs/evaluations/v1.47-memory-read-surface.md`

## ADR-0100 - Automatic Retrieval And Runtime Packet Assembly Have Separate Owners

Date: 2026-07-18
Status: accepted for V1.46.0

Context:

`app.mind.context` owned both model-runtime packet composition and the full
automatic-memory retrieval pipeline. That mixed context policy with candidate
pooling, ranking, final reranking, and diagnostic classification, making either
responsibility harder to change and verify independently.

Decision:

- `app.mind.context_retrieval` owns automatic candidate collection, ranking,
  selected/near-miss/excluded classification, final rerank projection,
  conflicts, and negative evidence;
- `app.mind.context` remains the stable facade for runtime packet assembly,
  trace persistence, and cognitive activity recording;
- ranking inputs, thresholds, candidate limits, payload semantics, and V2
  projection policy do not change in this organizational slice; and
- model-facing delivery must be verified independently from rich internal
  retrieval selection because provenance gates can legitimately exclude a
  selected candidate later in the pipeline.

Consequences:

Retrieval policy now has a cohesive typed owner without exposing a second
public API. Future ranking work can be evaluated without reopening context
assembly, while context routing can consume retrieval results through one
explicit contract. Regression gates must distinguish selection from actual
model delivery.

Links:

- Linear SCA-35
- Linear SCA-43
- BUG-0093
- `docs/evaluations/v1.46-context-retrieval-separation.md`

## ADR-0099 - One Native Turn Lifecycle Behind The HTTP Facade

Date: 2026-07-18
Status: accepted for V1.45.0

Context:

Native sync and stream routes duplicated context construction, history
routing, trace assembly, answer control, persistence, and scheduling. The
duplication had already caused stream to create a model-context trace without
linking it into request or final-turn evidence.

Decision:

- `app.api.chat_native_turn` owns native turn preparation, execution, failure,
  and completion;
- `app.api.chat` remains the stable FastAPI and response-model facade;
- shared invariants have one implementation, while entrypoint names,
  accounting transport, NDJSON emission, stream flags, and post-open error
  delivery remain explicit transport differences;
- model-facing policy, tool semantics, provider history, and answer-obligation
  behavior do not change as part of this organization slice; and
- both transports must link every generated model-context trace into request
  and completion evidence.

Consequences:

Future native lifecycle changes have one owner and can be tested without
editing route registration. The service remains substantial because tool and
answer-control ordering are one cohesive lifecycle; further separation needs
its own evidence rather than another line-count-only move.

Links:

- Linear SCA-33
- BUG-0092
- `docs/evaluations/v1.45-native-turn-orchestration.md`

## ADR-0098 - Behavioral Tests Require Direct Reasoned Inspection

Date: 2026-07-18
Status: accepted for all current and future behavioral verification

Context:

Technical counters and evaluator scores can prove structural facts, but they
cannot establish whether Scarlet made a sensible cognitive choice, used
evidence appropriately, or answered naturally. A numerically successful run
can still be behaviorally poor, while a semantically valid answer can differ
from a prepared string.

Decision:

- Codex directly reads every behavioral probe's starting state, prompt, model
  actions, tool results, traces, final answer, and longitudinal consequence;
- deterministic checks remain authoritative for IDs, state, commands,
  persistence, and exact protocol boundaries;
- cognitive choice and answer quality receive an explicit reasoned judgment;
- scores, token counts, and latency remain diagnostics rather than verdicts;
- a run with invalid starting conditions is rejected as evidence instead of
  being averaged into the result; and
- large behavioral campaigns remain owner-triggered, while bounded direct
  probes retain this same qualitative standard.

Consequences:

Evaluation reports must expose enough raw evidence to support review and must
not hide natural behavior behind one aggregate score. Codex may serve as the
project-informed LLM-as-human judge, but must state its rubric and distinguish
model variance, evaluator defects, implementation regressions, and unrelated
pre-existing bugs.

Links:

- `docs/development-process.md`
- `docs/evaluations/v1.34-natural-behavioral-suite.md`

## ADR-0097 - Native Provider Runtime Is Authoritative

Date: 2026-07-18
Status: accepted

Context:

Custom GPT can expose a stronger external model, but Actions, hidden native
history, confirmation behavior, and service-owned limits are outside project
control. The long-term cognitive and embodiment system must remain operable on
providers selected and integrated inside API Mind.

Decision:

- native Scarlet with project-selected providers such as MiniMax is the
  authoritative runtime and architecture target;
- GPT Actions remain an experimental external adapter to shared context,
  shell, persistence, and answer-control contracts;
- GPT parity is preserved where practical, but external limitations do not
  justify extreme core complexity or become requirements for native Scarlet;
- failures unique to the hosted GPT are classified separately from API Mind
  defects; and
- future provider abstractions preserve native observability, continuity, and
  control before optional external integrations.

Consequences:

Roadmap priority, verification, and refactoring are judged first on native
runtime behavior. The GPT bridge remains useful and maintained within its
bounded contract, but it is not the principal system or a substitute for
internal provider support.

Links:

- `backend/app/plugins/gpt_bridge/README.md`
- Linear SCA-39

## ADR-0096 - Retire MCP And Keep GPT Actions As The Sole External Bridge

Date: 2026-07-18
Status: accepted and implemented for V1.43.0

Context:

The MCP/App experiment could not be attached to the target Custom GPT while
Actions remained the working integration. Production inspection found 34
historical `mcp_bridge` sessions and recent requests from an external
`openai-mcp` client, proving the route was externally discoverable rather than
an unused internal helper. The owner nevertheless confirmed that this
connector path is deprecated and must not remain as a competing contract.
Query-string bridge authentication also caused credentials to appear in proxy
access logs.

Decision:

- remove the application `/mcp` route, JSON-RPC lifecycle, tool descriptors,
  connector prompt, tests, and Nginx proxy location;
- remove bridge-key query parameters from every GPT route;
- retain `Authorization: Bearer` and `X-GPT-Bridge-Key` authentication;
- keep the three Custom GPT Actions as the sole external model transport;
- keep native `mind_shell` and internal/debug `/mind/*` boundaries unchanged;
- preserve all historical MCP-originated database evidence; and
- coordinate bridge-key rotation with the external GPT dashboard rather than
  breaking the active Actions configuration unilaterally.

Consequences:

Current code and operational documentation expose one external GPT contract.
Historical sessions remain navigable and old ADR/experiment records remain
truthful. A separately coordinated credential rotation is still required
because prior query-string use may have copied the current secret into access
logs.

Links:

- Linear SCA-22
- BUG-0090
- `backend/app/plugins/gpt_bridge/`
- `docs/evaluations/v1.43-mcp-retirement.md`

## ADR-0095 - Monolith Rework Uses Stable Facades And Atomic Issues

Date: 2026-07-18
Status: accepted planning boundary in SCA-10

Context:

Several runtime and frontend files now concentrate multiple contracts, but
line count alone does not distinguish operational coupling from a large
declarative catalog. A broad refactor could preserve unit tests while changing
trace order, provider history, memory lifecycle, model context, or GPT parity.
The GPT router also still contains deprecated MCP code scheduled for removal.

Decision:

- split one contract or lifecycle per issue behind an unchanged public facade;
- run the identical frozen preliminary gate before and after every executable
  slice, plus focused tests and direct use of the affected surface;
- remove deprecated MCP before refactoring the remaining GPT Actions router;
- separate chat support before native turn orchestration, and memory read
  surfaces before mutation/proposal/maintenance dependencies;
- treat `mind/schema.py` as a coherent declarative catalog until import or
  ownership evidence justifies a split;
- forbid incidental database, API, prompt, policy, or behavior changes inside
  organization-only slices; and
- keep broad live Scarlet campaigns owner-triggered while requiring bounded
  direct validation for agent-facing runtime changes.

Consequences:

SCA-10 closes with an executable map rather than a risky mega-branch. SCA-22
and SCA-33 through SCA-41 carry the actual code changes and can be accepted,
reverted, or reordered independently. Structural improvement is measured by
clear ownership and preserved behavior, not by a target line count.

Links:

- Linear SCA-10
- `docs/monolith-rework-plan.md`
- `docs/preliminary-regression-suite.md`

## ADR-0094 - Agent Mode Receipts Separate Eligibility From Delivery

Date: 2026-07-18
Status: accepted and implemented for V1.42.0

Context:

Mode routing had one correct active filter but an ambiguous trace contract.
When routing was off or shadow, ineligible blocks were still delivered while
the aggregate receipt omitted them from `included_block_types`. A type-only
receipt also could not identify duplicate blocks or explain individual
decisions.

Decision:

- derive filtering and trace aggregates from the same ordered per-block
  decision list;
- distinguish policy eligibility from actual delivery;
- deliver unregistered block types fail-open while reporting registry drift;
- reject unknown modes and routing policies before context delivery;
- preserve on-demand shell availability independently of automatic routing;
- enforce resumable ownership at the persistence primitive as well as shell;
- define `idle` as no direction to resume and `scouting` as an exploratory
  orientation that remains selectable before sensor execution exists; and
- do not claim behavioral validation for idle/scouting model cycles until such
  a runtime actually exists.

Consequences:

Trace/UI/evaluation consumers can reconstruct exactly what reached the model.
New block families cannot disappear silently, but every unregistered receipt
becomes actionable registry evidence. Human chat remains `interactive`, and
scouting remains a persistent posture without sensors or autonomous work.

Links:

- Linear SCA-6
- BUG-0088
- EXP-0060
- `backend/app/mind/agent_modes.py`
- `docs/evaluations/v1.42-agent-mode-routing.md`

## ADR-0093 - Final Answers Use Shared Traceable Runtime Obligations

Date: 2026-07-18
Status: accepted and implemented for V1.41.0

Context:

Prompt policy and visible runtime evidence do not guarantee that a stochastic
model will finish a selected action, disclose a material conflict, or keep
capability claims aligned with current shell state. A V1.40 volition scenario
ended on a public progress note, while earlier memory probes showed that
retrieved conflicts and unavailable operations could still be omitted or
misrepresented in the answer.

Decision:

- compile one shared, traceable answer-obligation manifest for native and GPT
  transports;
- classify obligations as `hard`, `warning`, or `advisory` and structural or
  semantic;
- use a private native final marker only as a structural boundary, stripping it
  before persistence, history, traces shown as public content, and UI output;
- invoke a structured LLM judge only when a semantic obligation exists, never
  use keyword matching or numeric scores to judge natural-language compliance;
- allow one bounded correction after a hard failure and never auto-rewrite
  Scarlet's answer;
- keep rejected drafts as trace/provider-continuity evidence but never as the
  canonical assistant message;
- make GPT `required_actions` contain only executable shell commands while
  `action_policy.answer_obligations` carries answer constraints; and
- fail closed when the semantic validator is unavailable.

Consequences:

Native sync and stream paths now distinguish public work notes from a validated
conclusion. The GPT bridge can reject one draft with recoverable HTTP 409 and
fails the turn after a second hard violation. Ordinary direct answers pay only
the structural boundary cost; semantic judge latency is limited to obligated
turns. Semantic judge quality and external GPT correction compliance remain
monitored rather than treated as mathematical proof.

Links:

- historical answer-obligations module (removed in V1.64.0)
- `docs/evaluations/v1.41-answer-obligations.md`
- Linear SCA-28

## ADR-0092 - Cognitive Organs Keep Independent Conservative Defaults

Date: 2026-07-18
Status: accepted and implemented in V1.40.0

Context:

Focus, volition, computational affect, and metacognition all have executable
storage or review surfaces, but implementation alone does not establish useful
default behavior. The V1.34 baseline showed variable invocation and failed
affect activation. SCA-4 added correlated lifecycle tests, independent
controls, model/shadow comparison, and separate technical and qualitative
judgments.

Decision:

- surface focus only when an active bounded focus exists and do not create it
  automatically from ordinary topics;
- keep volition persistent but on-demand, outside automatic chat injection and
  without autonomous cycles;
- keep affect in `shadow` by default and reserve `model` for controlled tests
  until it shows causal answer benefit;
- keep `metacognition step` model-invoked for proportionate high-risk claims
  and keep lesson context shadow by default;
- require traceable writes/reviews before the strongest durable-volition and
  cross-system reliability claims; and
- introduce no cross-organ coupling until each organ's invocation and answer
  boundary are reliable independently.

Consequences:

The runtime retains useful organs without turning experimental state into
always-on cognitive pressure. Focus has the strongest direct lifecycle
evidence. Affect now transitions correctly but remains unproven as model-facing
value. Volition continuity works when invoked, while SCA-28 still permits a
turn to end before a selected mutation. Metacognition improves broad judgments
but can overprocess. Future mode routing may select organ eligibility, but it
must not override these evidence-based defaults.

Links:

- `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`
- Linear SCA-4

## ADR-0091 - Active Chronology Is A Recursive Derived View With Deterministic Sources

Date: 2026-07-18
Status: accepted and implemented in V1.39.0

Context:

V1.36 established exact turn source maps and a token-based shadow partition,
but canonical provider history still grew without an active derived route. A
safe activation must preserve the complete source transcript, survive stale or
missing summaries, avoid rerunning merely because canonical history never
shrinks, and prevent LLM-generated summaries from inventing opaque source IDs.

Decision:

- persist append-only chronology artifacts separately from episodic summaries;
- recursively summarize the previous artifact plus only newly compactable
  complete turns;
- route compacted chronology, exact newest turns, and current user input in
  both sync and stream paths;
- always append provider output to the canonical request history;
- store canonical and model-facing requests together in `llm.request` traces;
- validate artifacts against the exact canonical turn/digest prefix and fall
  back to full history on every invalid state;
- build source manifests deterministically and remove generated opaque IDs not
  present in source input;
- schedule later cycles from estimated derived next-turn size, using canonical
  history only as immutable source material.

Consequences:

Long native sessions can regain active headroom without losing exact history or
navigation. Summary semantics remain LLM-generated, but source identity is
backend-owned. The current design does not compact unobserved native ChatGPT
history. Naturally long multi-cycle behavior remains a monitored surface.

Links:

- `backend/app/runtime/history_runtime.py`
- `backend/app/runtime/history_compaction.py`
- `docs/evaluations/v1.39-active-history-compaction.md`
- Linear SCA-32

## ADR-0090 - Historical Provenance Maintenance Requires Deterministic Evidence

Date: 2026-07-18
Status: accepted and implemented in V1.38.0

Context:

The original provenance route combined classification and mutation through an
`apply` query flag. Its broad unresolved class also made 242 explicit Codex
fixtures look equivalent to genuinely ambiguous historical memories. Similar
content, reranker score, or an LLM guess cannot prove which session turn or
message caused a memory.

Decision:

- make provenance audit unconditionally read-only and separate provenance
  validity from record disposition;
- allow exact source repair only when the declared session and turn resolve and
  contain exactly one persisted user message;
- classify a Codex fixture only when metadata, tags, and source-session title
  all satisfy the fixed structured contract;
- treat exact content equality as review evidence, never automatic semantic
  redundancy;
- require dry-run, reviewed candidate digest, verified backup reference, and
  exact approval token before any production mutation;
- deprecate proven fixtures without deleting history, synchronize facts and
  retrieval artifacts, and keep maintenance activity outside cognitive
  recency; and
- retain ambiguous or inconsistent real memories until exact evidence or an
  explicit semantic adjudicator can decide them.

Consequences:

Historical cleanup becomes reproducible and fail-closed. The system can remove
known test contamination from active cognition without pretending to know the
origin or meaning of uncertain records. Audit and maintenance remain internal
backend surfaces, not additional model-facing tools.

Links:

- `backend/app/runtime/memory_provenance.py`
- `docs/evaluations/v1.38-historical-provenance-audit.md`
- Linear SCA-20

## ADR-0089 - Final Memory Relevance Uses A Query-Relative Reranker Floor

Date: 2026-07-18
Status: accepted and implemented in V1.37.0

Context:

The fixed final-reranker threshold `0.01` passed initial controls but rejected
the second required fact in a frozen two-fact query. Lowering one global floor
enough to recover it would admit tangential memories in queries whose leading
candidate has a much stronger score. Sparse, dense, graph, lexical, stored
confidence, and salience cannot resolve this because the owner explicitly
requires the advanced semantic reranker, not hand-authored relevance fusion.

Decision:

- keep the memory-level reranker as the only final acceptance and ordering
  authority;
- require every accepted candidate to meet both a calibrated absolute floor
  and a query-relative floor derived from the best reranker result;
- configure the floors independently, initially `0.004` absolute and `1%`
  relative, and expose the effective threshold in trace evidence;
- retain round-robin sparse/dense/KG/lexical recall only for candidate coverage;
- keep active mode fail-closed and do not add deterministic fallback or an
  unobserved runtime retry loop;
- recalibrate from immutable real references and semantic judgment whenever
  the reranker model or material dataset characteristics change.

Consequences:

The policy handles query-local score scale without allowing recall-route scores
to decide semantics. Frozen post-change controls pass 22/22, including a
two-memory answer and a wrong-entity collision, while unrelated negatives
remain empty. A later production negative accepted an unrelated candidate at
`0.004102`, just above the absolute floor. This does not justify a blind
threshold change: it confirms that the calibration is strong project evidence,
not a universal numeric proof, and that provider drift, lexical ambiguity, and
larger candidate pools remain monitored under SCA-3 follow-up work.

Links:

- `backend/app/mind/relevance_rerank.py`
- `backend/app/evals/memory_rerank_calibration.py`
- `docs/evaluations/v1.37-memory-rerank-calibration.md`
- Linear SCA-3

## ADR-0088 - Public Answer Is A Turn-Completion Invariant

Date: 2026-07-18
Status: accepted and implemented in V1.36.1

Context:

MiniMax M3 can occasionally end a user-facing tool-chat response with private
thinking only, `stop_reason=end_turn`, no public text, and no tool call. The
backend previously treated that provider message as a successful empty answer.
This erased the distinction between a stochastic model omission and a valid
Scarlet turn, and could also leave a recognized memory action unexecuted.

Decision:

- require non-empty public assistant text before a user-facing chat turn can
  complete;
- allow one configurable continuation only for thinking-only `end_turn`;
- keep the continuation bounded and in the same provider sequence;
- fail the turn explicitly when recovery is exhausted or the empty terminal
  result is not eligible for recovery;
- retain recovery attempts in trace metadata while excluding the incomplete
  assistant block and synthetic continuation from canonical provider history;
- never derive public text, memory, or tool intent from private thinking;
- enforce the invariant again at the sync and streaming chat boundaries so an
  alternate provider adapter cannot bypass it.

Consequences:

Normal turns pay no additional provider call. A genuine thinking-only omission
can recover once without fabricating cognitive actions. Persistent provider
failure becomes visible as `llm.incomplete_response` rather than a misleading
HTTP 200 with an empty assistant message. The policy fixes systemic acceptance
of invalid output; it does not claim to eliminate stochastic provider behavior.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/api/chat.py`
- `docs/bug-ledger.md#bug-0067---minimax-can-end-a-turn-with-thinking-only`
- Linear SCA-19

## ADR-0087 - Chronology Uses Token Areas And Complete-Turn Source Maps

Date: 2026-07-14
Status: accepted in shadow mode for V1.36.0

Context:

The first chronological plan proposed a 100k summary plus eight recent turns.
Read-only real sessions showed that a turn can cost hundreds or hundreds of
thousands of tokens depending on tool activity, so a turn count cannot define
a stable context reservation. Provider usage was also undercounted when cache
read and creation tokens were omitted.

Decision:

- preserve canonical provider history as append-only evidence;
- map exact provider slices to complete turn, message, tool-call, and trace ids;
- partition the 500k operational policy as `O + C + H + A + M`;
- keep `C` and normal `H` at configurable 100k maxima and `M` at 25k;
- derive `A` from actual measured overhead instead of assigning a turn count;
- select newest complete turns backward by incremental estimated token cost;
- measure every provider step using uncached plus cache-read plus cache-created
  input, and calibrate only from accounting-v2 observations;
- retain a whole turn that exceeds `H` when it fits the physical 1M window,
  explicitly reducing `A` rather than splitting the turn;
- fail closed when one turn exceeds the physical model window;
- keep the entire strategy shadow-only until recursive summaries and a
  multi-cycle derived router pass a separately approved gate.

Consequences:

The normal observed partition leaves about 250k active-growth tokens when
external overhead is around 25k. Tool-heavy exceptional turns can consume most
of that area, but the planner reports the condition truthfully. The bounded
full-vs-derived comparison supports the architecture while also showing that
summary/source reasoning still needs behavioral scrutiny before activation.

Links:

- `backend/app/runtime/context_accounting.py`
- `backend/app/runtime/history_compaction.py`
- `docs/evaluations/v1.36-history-compaction-calibration.md`
- Linear SCA-5

## ADR-0086 - Preserved Context Is A Field-Allowlisted Organ Surface

Date: 2026-07-14
Status: accepted and implemented in V1.35.0

Context:

The compact V2 session and memory areas were reviewed, but
`preserved_context` could still copy whole legacy blocks for focus, affect,
metacognition, Scarlet state, recent dialogue/events, and capability hints.
That path could reintroduce duplicate, technical, or non-actionable data into
Scarlet's context and obscure MiniMax/GPT parity.

Decision:

- allow automatic projection only for active focus, active affect, and
  injected metacognitive lessons;
- copy only fields with immediate cognitive or source-navigation value;
- keep `scarlet_state`, duplicate dialogue, and generic events trace/UI-only;
- make capability detail on-demand through authoritative `help` commands;
- preserve the rich runtime source unchanged for system work and diagnostics;
- persist a field-level inclusion/exclusion audit beside, never inside, the
  canonical model document;
- use the same V2 compiler for native MiniMax and GPT bootstrap.

Consequences:

Default `preserved_context` is empty under shadow/off organ modes. Optional
organs remain available without exposing their registry, usage policy,
scoring, selection, or debug internals. Future organ families require an
explicit projector and audit entry before they can reach the model.

Links:

- `backend/app/mind/context_preserved.py`
- `backend/app/mind/context_projection.py`
- `docs/context-packet-inventory.md`
- `docs/block-registry.md`
- Linear SCA-18

## ADR-0085 - Routine Verification Is Focused; Complete Live Evaluation Is Owner-Triggered

Date: 2026-07-14
Status: accepted

Context:

The V1.34 behavioral baseline makes a 36-turn, evidence-rich MiniMax campaign
repeatable, but building or rerunning that campaign for ordinary tasks consumes
substantial time and provider resources. Most changes can be checked more
proportionately through focused deterministic tests and direct use of the
affected API Mind tool or surface.

Decision:

- default every task to the smallest relevant deterministic test plus direct
  Codex tool/surface verification when applicable;
- do not launch repeated natural suites, cross-branch batteries, long live
  sessions, or broad pre/post model campaigns without an explicit owner request
  for the current task;
- keep deterministic repository CI independent: it may still run its complete
  local test gates because it does not consume live Scarlet calls;
- when the owner authorizes an advanced evaluation period, retain the frozen
  starting state, natural prompts, evidence capture, and project-informed
  LLM-as-human judgment established by ADR-0084.

Consequences:

Routine development remains fast and observable, while expensive stochastic
evidence is gathered deliberately at milestones or when the owner decides it
is worth the cost. The existence of a suite is not permission to run it.

Links:

- `AGENTS.md`
- `docs/development-process.md`
- `docs/behavioral-validation-framework.md`
- `docs/evaluations/v1.34-natural-behavioral-suite.md`

## ADR-0084 - Behavioral Regressions Separate Objective Facts From Semantic Judgment

Date: 2026-07-14
Status: accepted and implemented in V1.34.0

Context:

API Mind behavior combines exact technical contracts with stochastic natural
language. Exact-string or aggregate numeric comparators can misclassify a
valid answer, while an eloquent answer can hide a missing state transition,
wrong source, or accidental memory write. The project owner also established
that Codex may act as the project-informed human judge when the rubric and
evidence are explicit.

Decision:

- freeze DB identity, source references, session arrangement, and natural user
  prompt before execution;
- evaluate technical execution, cognitive choice, answer outcome, and
  longitudinal effect as separate layers;
- automate only objective DB, command, trace, event, and state invariants;
- require reasoned human or project-informed LLM-as-human review for semantic
  quality and natural-language differences;
- never require a redundant tool call when current runtime context already
  contains complete evidence;
- rerun scenarios independently because one convincing output is not evidence
  of behavioral reliability;
- preserve evaluator corrections explicitly instead of silently rewriting an
  oracle after observing a failure.

Consequences:

Large reworks can now use the same natural suite before and after without
pretending that language quality is reducible to a number. Qualitative review
cost remains real, but every judgment carries a rationale and raw evidence.

Links:

- `backend/app/evals/behavioral_suite.py`
- `backend/app/evals/scenarios/behavioral-v1/suite.json`
- `docs/behavioral-validation-framework.md`
- `docs/evaluations/v1.34-natural-behavioral-suite.md`

## ADR-0083 - Engineering Quality Gates Start As An Explicit Incremental Baseline

Date: 2026-07-14
Status: accepted and implemented in V1.33.0

Context:

The runtime had broad pytest and whole-system regression evidence but no
blocking lint, static typing, statement-coverage floor, documentation-integrity
check, or repository CI workflow. Turning every possible rule on at once would
mix hundreds of pre-existing typing findings and mechanical import-order churn
into unrelated cognitive work; omitting the debt entirely would leave future
reworks without an objective engineering floor.

Decision:

- block objective Ruff `E4`, `E7`, `E9`, and `F` defects across backend code,
  tests, and scripts;
- block mypy regressions first in six clean, high-value configuration,
  routing, retrieval, accounting, and database-boundary modules;
- preserve the measured full-application mypy debt as an explicit non-blocking
  baseline rather than suppressing it globally;
- measure the complete backend suite, including evaluator entry points, and
  enforce a 79.9% statement-coverage floor against the 79.998% baseline;
- validate documentation links, repository references, and canonical
  ADR/BUG/EXP identifiers deterministically;
- run the same gates plus the frontend production build in GitHub Actions.

Consequences:

Large reworks now have a reproducible engineering floor in addition to the
frozen cognitive regression suite. Import sorting, wider mypy coverage, and
higher per-module test thresholds remain deliberate follow-up slices. Future
changes should expand the baseline or reduce measured debt, not hide it with
broad exclusions.

Links:

- `backend/pyproject.toml`
- `.github/workflows/quality.yml`
- `scripts/check_documentation.py`
- `docs/quality-gates.md`

## ADR-0082 - The Shell Registry Is An Executable Organ Contract

Date: 2026-07-13
Status: accepted and implemented in V1.32.0

Context:

The model-facing shell had grown through several organs. Help, registry
validation, parser aliases, endpoint handlers, persistence, and model-facing
suggestions could each be locally correct while disagreeing as a whole. This
produced false availability, discarded flags, hidden pagination limits, and
endpoint-shaped next actions that Scarlet could not execute as shell commands.

Decision:

- treat the command registry and help catalog as executable contract;
- require alias parity and validate every published command in tests;
- expose truthful pagination and explicit targeted not-found errors;
- keep internal endpoint payloads available for backend use, but translate
  model-facing cross-organ suggestions into executable shell commands;
- verify each organ at parser, handler, storage, negative-path, whole-system,
  and representative live-model layers.

Consequences:

Shell capability claims now have mechanical evidence instead of documentation
alone. Internal `/mind/*` endpoints remain deterministic implementation
surfaces; this decision does not expose them as a second model tool or imply
autonomous use of every organ.

Links:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/shell_presentation.py`
- `docs/evaluations/v1.32-shell-organ-audit.md`

## ADR-0081 - Reranker Is The Final Memory Relevance Arbiter

Date: 2026-07-13
Status: accepted and implemented in V1.31.0

Context:

The active memory pipeline combined hand-authored lexical, entity, tag, graph,
sparse, dense, and rerank coefficients. Those values were useful for finding
candidates and debugging, but they also decided which memories became
`selected`. The memory backlog had already established the intended principle:
embedding finds direct candidates, KG finds nearby context, temporal filters
constrain the field, and rerank decides what matters now.

Decision:

- sparse FTS, dense surfaces, NetworkX expansion, and lexical/entity matching
  are recall routes only;
- candidates are interleaved round-robin and deduplicated by canonical memory
  id, without weighted rank fusion;
- the final reranker evaluates memory-level documents containing canonical
  content and active facts;
- in `retrieval_hybrid_mode=active`, only reranker-accepted candidates may
  become selected or be returned by manual search;
- stored confidence, salience, dense score, graph score, and hand-authored
  coefficients do not control final ordering;
- active mode fails closed when reranking is unavailable instead of silently
  reverting to deterministic relevance;
- `off` remains an explicit legacy baseline and `shadow` observational;
- `retrieval_hybrid` remains temporarily as a compatibility trace key, but it
  now reports `legacy_weighted_fusion=false`.
- the first live-calibrated acceptance threshold is provisionally `0.01`;
  threshold calibration uses declared positive/negative reranker evidence and
  remains distinct from prohibited weighted score fusion.

Consequences:

Recall engines can remain broad and independently testable without becoming
semantic judges. Active retrieval now depends on the external reranker, so
availability, latency, candidate coverage, and the calibrated acceptance
threshold require direct monitoring. Failure produces less automatic relevant
context rather than unsupported context.

Links:

- `backend/app/mind/relevance_rerank.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `docs/branches/memory.md`
- `docs/evaluations/v1.31-final-memory-rerank-live.md`

## ADR-0080 - Agent Modes Use One Active Tag And Multi-Tag Capabilities

Date: 2026-07-13
Status: accepted

Context:

Future embodiment will add sensory and operational surfaces that cannot all
compete for model attention continuously. Earlier planning described named
intent packs such as chat or source-sensitive mode, while the owner clarified
that modes should describe Scarlet's current agent posture. An organ may be
useful in several postures, and maintenance/Dream are background processes
rather than states of the main agent.

Decision:

- one agent mode tag is active at a time;
- initial tags are `idle`, `interactive`, and `scouting`;
- organs, contexts, and capabilities declare one or more matching tags;
- a human-facing turn deterministically enforces `interactive`;
- Scarlet can persist the `idle` or `scouting` posture to resume after the
  exchange through `mode set ... --reason ...`;
- persistence changes posture state only and never starts a background or
  autonomous execution cycle;
- V1 routing filters automatic context blocks and records its decision;
- on-demand shell cognition remains available independently;
- maintenance, summarization, and Dream are never agent modes.

Consequences:

New organs can join modes by registry metadata instead of rewriting mode
definitions. Current conversation behavior is protected from premature hard
gating. Scouting is a real registry/resumable state but not an implemented
sensor runtime or autonomous loop.

Links:

- `backend/app/mind/agent_modes.py`
- `backend/app/mind/mode.py`
- `docs/runtime-context-packs.md`

## ADR-0079 - Context Accounting Precedes Non-Destructive Compaction

Date: 2026-07-13
Status: accepted

Context:

MiniMax supports a one-million-token window, while API Mind intentionally uses
at most 500k input tokens and should consider compaction around 400k. Theory
suggested a roughly 100k chronological summary plus the latest eight complete
turns, but real tool-heavy turns vary greatly and full chronology must remain
navigable.

Decision:

- measure static policy, dynamic runtime, provider history, current message,
  tool schema, and request structure separately;
- distinguish estimated preflight tokens, first-provider-step usage, and
  aggregate tool-loop usage;
- configure 1M/500k/400k/100k/8 as validated policy values;
- keep compaction in `shadow` until long varied direct tests exist;
- preserve messages, traces, source transcripts, and canonical provider
  history append-only;
- treat any future compact history as a derived model-input view with coverage,
  provenance, rollback, and an explicit degradation rule when eight turns do
  not fit;
- label GPT accounting partial because the external provider context is not
  fully observable.

Consequences:

V1.30.0 can quantify the real problem without silently changing continuity.
An eight-turn tail remains a desired shape, not a fixed guarantee. Active
compaction requires a separate evidence-backed decision.

Links:

- `backend/app/runtime/context_accounting.py`
- `docs/runtime-context-packs.md`
- `docs/behavioral-validation-framework.md`

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

## ADR-0078 - Assess Cognitive Branches By Evidence And Runtime Integration

Date: 2026-07-13
Status: accepted

Context:

API Mind now contains memory, episodic recall, metacognition, focus, volition,
affect, context projection, maintenance, GPT transport, and multiple UI
surfaces. A single maturity label allowed documentation to blur four different
claims: code exists, deterministic tests pass, Scarlet uses the capability
well, and the capability is active in normal turns. Future embodiment would
make that ambiguity unsafe.

Decision:

Treat API Mind as the developing cognitive architecture of a digital
individual, with human-like functions as testable research targets and
digital-specific architecture where appropriate. Assess every agentic branch
on four separate dimensions:

1. implementation;
2. deterministic evidence;
3. direct Scarlet behavioral evidence;
4. normal runtime integration/default activation.

The canonical current matrix lives in `docs/project-state.md` and
`docs/branches/README.md`. Registry reservations, prompt policy, storage
tables, and standalone tools must not be described as mature cognitive organs
without the corresponding runtime and behavioral evidence.

Alternatives Considered:

- Keep one L0-L5 label without explaining activation or evidence.
- Treat every implemented endpoint/table as an active cognitive faculty.
- Describe the long-term digital-being vision only as product language.

Consequences:

- Branch status becomes falsifiable and comparable.
- Disabled/manual-only organs remain visible without being overstated.
- Unimplemented temporal/Dream registry entries are classified as
  reservations, not capabilities.
- Planning can prioritize validation and coupling before adding more organs.
- Human-like terminology remains tied to observable behavior rather than
  ontological claims.

Links:

- `docs/project-state.md`
- `docs/branches/README.md`
- `docs/project-blueprint.md`

## ADR-0072 - Mind Shell As Model-Facing Cognitive Interface

Date: 2026-07-06
Status: accepted

Context:

The original single-tool API Mind contract exposed endpoint-shaped operations
through `mind_api(method, path, body, intent)`. That kept the model-facing
surface small, but MiniMax M3 showed recurring brittleness around nested JSON
bodies, empty body retries, endpoint/schema drift, and overly mechanical API
thinking. The owner proposed a more agentic cognitive CLI: a shell-like mental
dashboard where Scarlet can navigate memory, sessions, focus, volition, affect,
and metacognition with commands.

Decision:

Introduce `mind_shell(command, intent)` as Scarlet's single model-facing API
Mind tool. Commands are bash-like but controlled by backend parsing, not a real
system shell. The existing `/mind/*` endpoints and dispatcher remain available
for backend/debug compatibility and rollback, but Scarlet's active prompt,
runtime context, chat tool schema, and metacognition reviewer use Mind shell
commands as the operative language.

Examples:

```txt
help
memory search "query" --top 5
memory write --type user_preference --scope user --content "..." --reason "..."
session open ses_...
focus read
volition list active
affect prototypes
metacognition step --objective "..." --mode critic
```

Alternatives Considered:

- Keep `mind_api` as the model-facing surface and add prompt guidance for
  endpoint correctness. Rejected because it preserves the nested JSON body
  failure mode and teaches Scarlet endpoint mechanics rather than cognitive
  navigation.
- Expose a real shell. Rejected because API Mind must remain deterministic,
  auditable, and safe; the shell is a controlled cognitive command runtime, not
  arbitrary OS access.
- Keep both `mind_api` and `mind_shell` visible to Scarlet. Rejected for this
  branch because a hybrid prompt would falsify the CLI experiment and encourage
  model fallback to endpoint habits.

Consequences:

- Scarlet sees one tool, `mind_shell`, and one command grammar.
- Runtime traces and events show commands as the model-facing operation.
- Backend endpoints still support existing tests, debug calls, maintenance, and
  rollback.
- The prompt no longer instructs Scarlet to call endpoint paths or inspect
  `/mind/schema`; it uses `help` and command-specific guidance.
- The first implementation maps commands onto existing handlers. A later
  refactor can extract route-independent service cores once the CLI behavior is
  validated.

Related Files:

- `backend/app/mind/shell.py`
- `backend/app/mind/schema.py`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `backend/app/mind/metacognition.py`
- `backend/app/prompts/scarlet_system.md`

## ADR-0073 - Separate Model-Facing Shell Packets From Debug Diagnostics

Date: 2026-07-08
Status: accepted

Context:

Real Scarlet testing on the command-shell branch showed that `mind_shell`
worked, but some commands returned diagnostics that were useful to developers
and harmful or wasteful as model-facing data. In particular, memory search
could return full `retrieval_shadow`, `retrieval_graph`, and
`retrieval_hybrid` payloads, while `memory conflicts` could return hundreds of
token/tag overlap pairs as if they were real contradictions.

The owner explicitly decided not to remove provider `thinking` or aggressively
compact history because MiniMax M3 has a large context window and no evidence
yet shows that thinking/history hurts Scarlet's cognition. The target is only
true redundancy and developer diagnostics that add confusion without improving
Scarlet's action.

Decision:

Mind shell command results now have a compact model-facing profile for noisy
commands while raw diagnostics remain in traces. Scarlet receives ids,
provenance, content, concise facts, query-time relevance, compact retrieval
routes, trace ids, and clear next actions. Developer/UI/debug surfaces can read
the full traces instead of requiring the model-facing packet to carry every
internal artifact.

Memory conflict semantics are also narrowed:

- atomic fact divergence is a true conflict;
- exact-content/tag/token similarity is a maintenance `related_overlap`;
- related overlaps are not injected as contradiction alarms in runtime memory
  context.

Command availability is validated through a central registry so recommended
metacognitive actions distinguish implemented commands, aliases,
missing-argument commands, unavailable-by-design commands, planned commands,
and unknown commands.

Consequences:

- Scarlet gets less noisy shell output without losing source ids or the ability
  to navigate memories/sessions/KG.
- Future UI work can render model packets, debug traces, and human-visible
  blocks differently without reinterpreting raw endpoint payloads.
- Conflict-driven affect/caution is less likely to fire from generic overlap.
- Duplicate/update/deprecation automation is explicitly left to maintenance,
  embedding/KG entity resolution, and future larger calibration rather than
  token-overlap heuristics.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/context.py`
- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/metacognition.py`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0074 - External GPT Bridge As Plugin Layer

Date: 2026-07-08
Status: accepted

Context:

The project owner wants to test Scarlet through a custom ChatGPT GPT while the
primary local Scarlet runtime continues to run on MiniMax M3. A GPT outside the
local provider loop cannot see Scarlet's backend-built runtime context unless
the system exposes it, and the backend cannot preserve the GPT's final answer
unless the GPT sends it back before replying to the user.

Decision:

Add a plugin-level bridge under `/gpt/*` with exactly three endpoints:

```txt
POST /gpt/bootstrap
POST /gpt/action
POST /gpt/finalize
```

`bootstrap` starts a real Scarlet turn and returns the same context/tool surface
the local MiniMax runtime would receive. `action` executes controlled
`mind_shell` commands through the existing command runtime. `finalize` persists
the external GPT answer, updates provider history, completes the turn, and
keeps maintenance/session-memory processes intact.

The bridge does not replace the local chat runtime and does not change
Scarlet's model-facing `mind_shell` contract. It is isolated in
`backend/app/plugins/gpt_bridge/` with its own prompt copy and documentation.

Alternatives Considered:

- Route the GPT directly through `/mind/*` endpoints. Rejected because it would
  bypass bootstrap/finalize and lose turn continuity.
- Let the GPT answer directly after actions without finalize. Rejected because
  the backend would not receive the assistant message and session memory would
  drift.
- Replace MiniMax runtime with GPT. Rejected because the current task is an
  external integration path, not a provider migration.

Consequences:

- Custom GPT Actions can operate Scarlet's cognition without running MiniMax.
- The external GPT must strictly obey bootstrap/action/finalize protocol.
- `/gpt/*` requires a dedicated bridge key outside local development.
- The OpenAPI schema now exposes GPT-facing endpoints in addition to the local
  dev/runtime APIs.
- V1.24.1 keeps the GPT Builder prompt under the instruction-size limit by
  splitting the full Scarlet bridge policy into a compact system prompt plus
  attachable knowledge files. The minimal `openapi_gpt_action.json` exists only
  so ChatGPT Actions can discover the three bridge endpoints and their body
  shapes; it is not a separate cognitive API.

Related Files:

- `backend/app/plugins/gpt_bridge/router.py`
- `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md`
- `backend/app/plugins/gpt_bridge/README.md`
- `backend/app/main.py`
- `docs/api-contract.md`

## ADR-0075 - ChatGPT MCP/App Bridge As Alternative GPT Surface

Date: 2026-07-08
Status: superseded by ADR-0096 in V1.43.0

Context:

Testing showed that Custom GPT Actions can work after schema hardening, but the
model may still treat the three OpenAPI operations as generic external APIs
rather than as native cognitive organs. The owner proposed exposing Scarlet as
a ChatGPT App/Connector through MCP, with lifecycle tools and family-specific
cognitive shell tools whose names and descriptions make the required usage more
legible to the hosted model.

Decision:

Add an experimental MCP/App surface at `/mcp` while keeping the `/gpt/*`
Actions bridge. The two surfaces are alternative ChatGPT configurations:
a GPT should use either Custom Actions or Apps/Connectors, not both.

The MCP bridge exposes required lifecycle tools:

```txt
start_scarlet_turn_required
finish_scarlet_turn_required
```

Their descriptions begin with the exact Italian obligation phrases:

```txt
Usa sempre a inizio di ogni turno
Usa sempre prima della tua risposta finale
```

The bridge also exposes family tools that proxy to the existing `mind_shell`
runtime with a single command string: memory, session, metacognition, focus,
affect, volition, help, and a generic shell fallback.

Alternatives Considered:

- Replace the Actions bridge. Rejected because Actions remain useful for GPT
  Builder testing and already have regression coverage.
- Build separate REST endpoints for each cognitive command. Rejected because
  it would duplicate the shell contract and expand the model-facing API.
- Add a full production OAuth MCP app immediately. Deferred because the current
  slice is a private preview experiment in model usability.

Consequences:

- ChatGPT can discover Scarlet's cognitive organs as native MCP tools in
  connector-capable contexts, but the target Custom GPT flow did not allow the
  user to add the created connector as the GPT's active tool surface.
- The backend still records the same turns, messages, traces, and tool calls
  through bootstrap/action/finalize.
- MCP connector testing can reuse `GPT_BRIDGE_API_KEY` through a query key as a
  temporary private-preview convenience, but production/submission should use
  proper OAuth.
- Live GPT testing is still required because the backend cannot force the
  hosted model to call tools before answering.
- As of V1.25.2, Actions are the active external Scarlet GPT surface. The MCP
  endpoint remains temporarily implemented for traceability and future removal.

Related Files:

- `backend/app/plugins/gpt_bridge/router.py`
- historical connector prompt removed in V1.43.0
- `backend/app/plugins/gpt_bridge/README.md`
- `backend/tests/test_gpt_bridge.py`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0076 - Shell Capabilities As The Only Model-Facing Cognitive Contract

Date: 2026-07-09
Status: accepted

Context:

The project now uses `mind_shell(command, intent)` as Scarlet's local
model-facing API Mind surface and `/gpt/action` as the external GPT transport
for those same shell commands. Legacy `/mind/*` endpoints still exist because
they are useful for backend handlers, deterministic maintenance, direct tests,
debugging, rollback, and evaluator tooling. A review of the shell migration
found one confusing residual: runtime capability state was still derived from
endpoint routes, so a maintenance route such as
`POST /mind/memory/facts/backfill` could appear implemented inside
model-facing context even though it is not a Scarlet shell command.

Decision:

Keep one communication style for Scarlet: shell commands only. The active
model-facing capability map is derived from the shell command registry, not
from endpoint route status. Legacy `/mind/*` endpoints are internal
implementation/debug/maintenance surfaces unless a shell command explicitly
wraps them.

`memory.facts.backfill` remains implemented, but it is classified as
`internal_maintenance_only`. It rebuilds canonical memory facts and retrieval
artifacts for existing memory records after extractor/schema/lifecycle changes;
it is not a normal cognitive command Scarlet should run in conversation.

Consequences:

- Prompt, runtime context, metacognition recommendations, and external GPT
  bridge all describe Scarlet's cognition through `mind_shell`.
- Endpoint docs remain as backend/debug/maintenance contracts, not model
  instructions.
- If a future maintenance operation truly becomes useful for Scarlet's own
  cognition, it must receive an explicit shell command and tests rather than
  leaking through endpoint capability metadata.
- The command registry must stay in parity with shell handlers and help
  examples, including required fields and aliases.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/context.py`
- `backend/app/mind/shell.py`
- `backend/tests/test_mind_shell.py`
- `backend/tests/test_chat_api.py`
- `docs/api-contract.md`
- `docs/project-state.md`

## ADR-0067 - Runtime Context Packs Before Embodied Context Explosion

Date: 2026-07-09
Status: accepted as planning baseline

Context:

Scarlet now has several implemented or partly implemented cognitive organs:
semantic memory, episodic recall, runtime context, focus, volition, affect,
metacognition, traces, events, and maintenance. The owner also confirmed the
long-term research direction toward a robotic body, while explicitly noting
that embodiment is later work. When vision, audio, voice, movement, physical
interaction, memory, and cognition all become active, a flat prompt/context
packet will not scale.

The immediate risk is not robot integration. The immediate risk is architectural
drift: adding every new organ or diagnostic surface to the model context until
Scarlet loses active cognition under undifferentiated state.

Decision:

Adopt runtime context packs as the planning baseline. The backend should keep a
compact always-on spine and add mode-specific packs for source-sensitive work,
temporal recall, project engineering, emotional continuity, and future embodied
interaction/actuation. Organs, sources, and capabilities are classified by
necessity, coupling, freshness, authority, cost, and safety.

Scarlet may eventually request mode shifts through cognitive state or shell
operations, but deterministic backend routing keeps budget, safety, privacy,
and coupling constraints. Background maintenance and backfill remain
background/internal surfaces, not live model context.

Consequences:

- New organs must define their model-facing context shape, coupling rules, and
  degradation policy before being injected broadly.
- The always-on spine stays small: current message, session/turn identity,
  temporal/profile/privacy state, capability/tool contract, selected automatic
  memory packet when available, and active safety/conflict warnings.
- Source-sensitive and temporal questions should move toward explicit packs
  that require session/memory evidence instead of relying on inference from
  recent context.
- Future embodied modes must summarize sensory streams before model input and
  gate actuation through safety-aware packs.
- The first implementation should be a shadow router that traces pack
  selection before changing live prompt composition.

Related Files:

- `docs/runtime-context-packs.md`
- `docs/project-state.md`
- `docs/project-blueprint.md`
- `docs/branches/perception-context.md`
- `docs/digital-individual-organs-notes.md`
- `docs/experiments.md`

## ADR-0068 - Frozen Preliminary Regression Gate For Major Procedures

Date: 2026-07-10
Status: accepted

Context:

Scarlet's runtime now combines storage migrations, semantic memory/facts,
episodic recall, automatic context, the `mind_shell` command runtime, focus,
volition, affect, metacognition, traces, and the external GPT bridge. A broad
rework can preserve individual pytest contracts while still breaking the way
these surfaces compose against real laboratory history.

The owner requires a repeatable comparison before and after any large
procedure, using real DB references rather than an ungrounded synthetic
fixture. The test must retain the same starting state across branch changes and
must make any regression legible without relying on conversational memory.

Decision:

Adopt a frozen preliminary regression gate:

- choose sourceable real records, facts, sessions, and lifecycle states from a
  published laboratory DB revision;
- record their IDs, expected state, source hash, and inventory in a versioned
  suite document;
- create an ignored immutable local copy and a freshly recreated disposable
  run DB for every execution;
- execute assembled integration checks through actual runtime/context/shell/
  bridge paths; and
- require the identical suite before and after a major procedure.

The current first suite is `preliminary-regression-v1`, pinned to Git LFS
SHA-256 `827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5`.
Changing the data source or expected behavior requires a new versioned suite
and documented decision; the old suite is not rewritten to hide a regression.

Consequences:

- Major rework acceptance now requires both ordinary test coverage and an
  equal-or-better whole-system result on a known starting DB.
- Test-created IDs remain dynamic provenance in each report; stable real IDs
  are the invariant references.
- Deterministic providers can certify integration paths, but live human
  Scarlet/MiniMax evaluation remains necessary for free-form model behavior.
- Future broad work gains a reusable procedure without turning small fixes
  into heavy release rituals.

Related Files:

- `backend/app/evals/preliminary_regression.py`
- `docs/preliminary-regression-suite.md`
- `docs/development-process.md`
- `docs/experiments.md`

## ADR-0069 - Database Roles And Side-Effect-Free App Factory

Date: 2026-07-10
Status: accepted

Context:

The repository contains a legacy LFS laboratory snapshot, ignored evaluator
copies, a frozen preliminary baseline, and a VPS-mounted SQLite database with
real production data. The former `CODEX_TEST` boolean described a useful copy
mechanism but not the ownership of the selected database. In addition,
importing `app.main` eagerly assembled the default FastAPI app, which could
open and migrate the environment-selected database during an evaluator import.

Decision:

Adopt explicit resolved roles: `production`, `laboratory`, `test`, and
`preliminary`. Keep `CODEX_TEST` as an isolation mechanism rather than a role.
Reject ambiguous environment labels and production/test mixtures at app
assembly. Move the eager ASGI object to `app.asgi`, leaving `app.main` as a
side-effect-free factory. Require all major procedures and VPS deployments to
use the canonical database topology, read-only preflight, and transfer
exclusions documented in `docs/database-topology.md`.

Consequences:

- Evaluator imports and unit tests do not silently initialize the configured
  local or VPS DB.
- The preliminary gate and dirty-memory evaluator operate only on explicit,
  ignored run copies.
- A future VPS deployment must explicitly set `DATABASE_ROLE=production`,
  back up the mounted DB, and exclude `backend/data/` plus `.env` from code
  transfer.
- The legacy LFS lab snapshot is retained for historical baseline provenance,
  but normal staged commits reject it unless a data release is explicitly
  acknowledged.

Related Files:

- `docs/database-topology.md`
- `backend/app/storage/database_boundary.py`
- `backend/app/asgi.py`
- `scripts/check_database_boundary.py`

## ADR-0070 - Storage Repositories Split By Transaction Domain

Date: 2026-07-10
Status: accepted

Context:

`storage/repositories.py` had grown to 2,073 lines and mixed chat/session
records, traces/events, runtime settings and maintenance, focus/volition,
canonical memory/facts/proposals, and derived retrieval cache/graph state.
The combined module obscured ownership and made future context/runtime work
riskier to inspect.

Decision:

Keep `app.storage.repositories` as the stable caller-facing facade, but move
implementation into domain modules: `sessions`, `runtime`, `organs`, `memory`,
and `retrieval`. Shared session-touch behavior lives in a small private helper.
Do not change signatures, transaction behavior, schema, or caller imports in
this organization slice.

Consequences:

- Chat, bridge, shell, maintenance, and evaluators keep one compatible import.
- Future changes can be scoped to the domain that owns the table and lifecycle.
- Cross-domain mutations remain explicit through the shared helper rather than
  disappearing into a generic persistence abstraction.
- The split must continue to pass the frozen whole-system gate before any
  behavior change is accepted.

Related Files:

- `backend/app/storage/repositories.py`
- `backend/app/storage/repository/`
- `backend/tests/test_repository_facade.py`
- `docs/preliminary-regression-suite.md`

## ADR-0071 - Shared Compact Dynamic Context Contract

Date: 2026-07-12
Status: implemented in V1.29.0

Context:

Scarlet currently receives useful dynamic evidence mixed with repeated user
messages, maintenance timestamps, policy prose, retrieval diagnostics, profile
metadata, broad session summaries, and provider-specific bridge duplication.
The same runtime also needs richer evidence for retrieval, maintenance, UI,
traces, and debugging. Deleting internal detail would weaken observability;
sending all of it to the model would weaken cognition and future scalability.

Decision:

Keep rich internal evidence and compile a separate versioned model-context
projection shared by local MiniMax and the external GPT bridge. The approved
initial projection contains:

- current session id, title, and user-local creation time;
- user display name, one user-local clock/timezone, and assembled location;
- up to two compact previous-session hints with id, true last-message time,
  turn count, and summary or a fixed missing-summary navigation fallback;
- up to five relevant, five recent user-specific, and five recent general
  memory hooks, globally deduplicated in that priority order;
- compact memory id/content/semantic timestamps/source session/source message
  fields only, with deeper facts, graph, and provenance available on demand.

Memory recency is driven by explicit eligible cognitive activity. Delivering a
recent-memory packet does not refresh it, and reads do not mutate semantic
memory timestamps. Historical provenance is audited and sourceably repaired;
missing source ids are never guessed. Undiscussed dynamic families retain
their current behavior until their own review.

The GPT bridge is only an alternative model connection and transport. It may
not define a different API Mind context policy. Duplicate/conflict semantic
adjudication remains a separate research workstream; deterministic retrieval
may propose review candidates but does not decide semantic relation.

Consequences:

- Model input can become smaller without sacrificing raw trace/UI evidence.
- Native and GPT behavior can be compared against one context contract.
- The compiler can run in shadow mode before changing live provider input.
- A memory activity ledger and direct source message/turn navigation are
  required implementation dependencies.
- Legacy provenance repair is isolated from provider activation and protected
  by database preflight, dry runs, and regression tests.
- Missing/stale summaries are repaired through the existing episodic
  summarizer with bounded reconciliation and retry; the model fallback remains
  a temporary navigation safeguard rather than the target steady state.
- Dialogue/events, capabilities, Scarlet state, focus, affect, metacognition,
  and compatibility mirrors require later packet-by-packet review.
- The exact model document is now a first-class `model.context` trace; the
  richer evidence snapshots remain separate and are not deleted.
- `session message` and `session turn` are the direct provenance routes for
  compact memory hooks. No automatic KG node id is needed because
  `memory graph <memory_id>` resolves the root.

Related Files:

- `docs/context-packet-inventory.md`
- `docs/context-packet-implementation-plan.md`
- `docs/runtime-context-packs.md`
- `docs/database-topology.md`
- `backend/app/mind/context.py`
- `backend/app/plugins/gpt_bridge/router.py`

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

Use `MINIMAX_MAX_TOKENS=131072` as the backend default output budget for
MiniMax calls, matching MiniMax M2.7's documented maximum completion budget.
Individual requests may override it, but defaults should not be artificially
low.

Alternatives Considered:

- Keep the smoke default at `128`: worked for a tiny diagnostic, but encoded the wrong project priority.
- Keep very low token defaults for cost control: rejected because the Token Plan is request-based for M2.7 and this project optimizes for quality and observability.
- Set extremely large defaults immediately: originally deferred until we had
  persistent traces and real chat workloads; accepted on 2026-05-23 after
  provider-native history tracing made context growth inspectable.

Consequences:

- M2.7 has the full documented completion budget available for reasoning,
  tool-heavy turns, and final text in normal debug calls.
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

## ADR-0008 - Add Mind API Facade Before Provider Tool Loop

Date: 2026-05-09
Status: accepted

Context:

Phase 2 needs a single `mind_api` tool surface, schema discovery, a dispatcher, and traceable tool calls. MiniMax tool-loop integration will require careful provider handling, but the API contract and trace substrate can be built first without adding memory, attention, reflection, goals, or background workers.

Decision:

Add a minimal HTTP facade for the same `mind_api(method, path, body, intent)` contract:

```txt
GET  /mind/schema
POST /mind/call
```

`GET /mind/schema` exposes the model-facing tool schema and current route catalog. `POST /mind/call` dispatches the same method/path/body/intent shape, records a `tool_calls` row for every call, and creates a `mind.tool_call` trace when a session context is supplied.

Alternatives Considered:

- Implement the full MiniMax provider tool loop first: deferred because schema discovery and trace storage can be tested independently.
- Add memory or attention immediately: rejected because EXP-0001 says Phase 2 should expose the traceable runtime before cognitive state.
- Expose many direct cognitive endpoints without a facade: rejected because the project direction is one primary model-facing tool.

Consequences:

- The Mind API contract becomes inspectable and testable before model tool use is wired.
- Tool-call persistence exists before cognitive modules can mutate state.
- Planned routes can return structured recoverable errors instead of silently implying unavailable capabilities.
- The next Phase 2 slice can connect MiniMax tool-use content blocks to this dispatcher.

Links:

- `backend/app/api/mind.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/mind/schema.py`
- `backend/app/storage/models.py`
- `docs/api-contract.md`

## ADR-0009 - Keep MiniMax Tool Loop Provider-Owned And Mind Dispatch Backend-Owned

Date: 2026-05-09
Status: accepted

Context:

Phase 2 requires MiniMax M2.7 to call the single `mind_api` tool during chat turns. MiniMax-specific tool-use details are Anthropic-compatible content blocks, while cognitive route dispatch and persistence are backend responsibilities.

Decision:

Implement the tool loop in the MiniMax provider wrapper, but keep cognitive dispatch outside the provider through a `tool_runner` callback. The provider owns:

```txt
assistant tool_use blocks -> user tool_result blocks -> final assistant response
```

The chat runtime owns:

```txt
mind_api validation -> dispatcher call -> tool_calls row -> mind.tool_call trace
```

Alternatives Considered:

- Put Mind API dispatch directly inside `MiniMaxProvider`: rejected because provider code should not own cognitive API behavior.
- Put Anthropic-compatible content block handling in the chat endpoint: rejected because provider-specific protocol details would leak into runtime orchestration.
- Delay tool-loop integration until memory exists: rejected because tool calls need to be traceable before state-changing cognitive modules are introduced.

Consequences:

- Provider-specific protocol stays isolated.
- The model still sees one primary tool.
- Tool calls are persisted and traced before memory, attention, or reflection can mutate state.
- Future provider adapters can implement the same normalized tool-loop contract.

Update 2026-05-20:

The project owner clarified that API Mind is Scarlet's internal cognition, not
a normal optional user-facing tool, and that Scarlet must decide how many
internal operations are needed before answering. The runtime therefore no
longer imposes an artificial `max_tool_calls=4` cap during chat turns. The tool
loop is model-controlled and continues until Scarlet answers rather than emits
another tool call. Provider, network, and process failures can still stop a
turn, but the backend no longer encodes a fixed cognitive step budget.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/llm/provider.py`
- `backend/app/api/chat.py`
- `backend/app/mind/dispatcher.py`

## ADR-0019 - Treat API Mind As Scarlet's Internal Cognition

Date: 2026-05-20
Status: accepted

Context:

The owner clarified that future users will not know, operate, or choose API
Mind routes. API Mind is for Scarlet's own cognition: memory, facts, schema
awareness, traceable state inspection, and future cognitive modules. If Scarlet
waits for the user to request API usage, production behavior will be fragile
because the user will speak only in natural language.

Decision:

Scarlet's prompt and runtime contract now frame `mind_api` as an internal
cognitive interface, not as a normal user-facing tool.

Scarlet should autonomously decide when to use API Mind before answering,
including schema inspection, memory search, fact lookup, conflict inspection,
and traceable state mutation. The user should not need to know endpoints or
tell Scarlet how to use her cognitive environment.

The runtime uses a model-controlled, unbounded tool-loop policy for chat turns:

```txt
tool_loop_policy = model_controlled_unbounded
```

Consequences:

- Prompt language must teach cognitive posture, not only endpoint mechanics.
- Normal answers should expose results and source discipline, not ask users to
  operate API Mind.
- Evaluation should include prompts where the user does not mention API Mind,
  while Scarlet still uses it when needed.
- Long internal loops remain traceable through `mind.tool_call`, operation
  traces, streaming events, and `llm.response.raw_provider_messages`.
- Future engineering work may add cancellation, progress policy, or batch
  internal operations without reintroducing a fixed cognitive step cap.

Update 2026-05-22:

After a live autonomy probe showed Scarlet did not always follow
`source_session_id` on the first verified-baseline question, the prompt was
strengthened around epistemic curiosity and provenance thresholds. API Mind
remains internal cognition, but Scarlet is now instructed to classify evidence
as verified, remembered, inferred, provisional, or unknown, and to treat
memory-derived strong recommendations or baseline claims as requiring source
session inspection when provenance is available.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `docs/api-contract.md`

## ADR-0010 - Use NDJSON Streaming For The Debug Cockpit

Date: 2026-05-09
Status: accepted

Context:

The frontend cockpit needs to evaluate agentic multi-step behavior without waiting for the full final answer. It must show provider-exposed thinking blocks, tool input, tool result, and final response in a clear timeline while preserving persistent traces.

Decision:

Add a streaming chat endpoint:

```txt
POST /api/chat/sessions/{session_id}/turn/stream
```

Use newline-delimited JSON over `fetch()` rather than WebSockets or `EventSource`. `fetch()` supports POST bodies, keeps the same request shape as the normal chat endpoint, and avoids adding infrastructure before the stream semantics prove useful.

Alternatives Considered:

- Server-Sent Events through `EventSource`: rejected for this slice because browser `EventSource` is GET-only and the chat turn needs a JSON body.
- WebSockets: deferred because bidirectional transport is not yet needed.
- Polling traces after completion: rejected because it does not evaluate live model/tool progression.

Consequences:

- The cockpit can render live model text, tool calls, and tool results as they happen.
- The streaming endpoint still writes the same durable messages and traces as the non-streaming endpoint.
- Frontend parsing remains simple and inspectable.
- Later cancellation/backpressure behavior may need explicit handling if long-running tool loops appear.

Links:

- `backend/app/api/chat.py`
- `frontend/src/api.ts`
- `frontend/src/App.tsx`

## ADR-0011 - Render Agent Operation Order Inside Each Chat Turn

Date: 2026-05-09
Status: accepted

Context:

The first streaming cockpit rendered the live agent timeline in the debug/trace pane. That made intermediate events visible, but it blurred the relationship between a specific assistant message and the exact sequence of model requests, thinking blocks, tool input, tool dispatch, tool result, and final text that produced it. A React closure bug also showed that events without `turn_id` could be attached to a temporary bucket instead of the persisted assistant turn.

Decision:

Render the ordered agent operation timeline inside the assistant message for that same turn. Keep the right debug pane focused on persisted raw traces and metrics.

Every NDJSON event emitted by `POST /api/chat/sessions/{session_id}/turn/stream` must include:

```txt
seq
turn_id
```

Provider events that belong to a specific model request should also carry `model_step` when available. The frontend stores operation steps by `turn_id`, orders them by `seq`, and displays them inline in the chat as a numbered chain.

Alternatives Considered:

- Keep the timeline only in the trace pane: rejected because it reads like debug output rather than the causal path of the assistant response.
- Reconstruct order only from persisted traces after completion: rejected because it loses live streaming granularity and cannot show deltas before the final answer.
- Use one global frontend timeline: rejected because multi-turn chat can mix or overwrite operation chains.

Consequences:

- Each assistant message can explain its own agentic path without leaving the chat transcript.
- The raw trace pane remains available for request/response JSON inspection.
- Stream event contracts are stricter: clients can rely on `seq` and `turn_id`.
- Future memory, attention, and reflection calls should appear as additional ordered operations in the same inline chain.

Links:

- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/api-contract.md`

## ADR-0012 - Use Dual-Mode Evaluation Before Memory

Date: 2026-05-09
Status: accepted

Context:

The project is ready to evaluate Scarlet's behavior before adding memory. Pure scripted tests are useful for regressions, but they can distort cognitive evaluation because real human probing adapts to what the agent actually says. The project owner explicitly wants live end-to-end evaluation where the next question can change based on the previous answer.

Decision:

Add an evaluation runner with two modes:

```txt
scripted    repeatable scenarios for technical regression checks
interactive adaptive human-in-the-loop sessions for behavioral evidence
```

The runner talks to the existing backend over HTTP and stores run evidence as files: transcript JSONL, trace payloads, operation summaries, checks, and optional human notes. It does not add memory, attention, or any new cognitive state.

Memory implementation remains blocked until a dedicated design discussion decides what memories are, how they are written, how they are searched, and how they are exposed back to the model.

Alternatives Considered:

- Only scripted evals: rejected because the behavior of the agent can change the right next question.
- Only manual UI testing: rejected because it gives weak regression evidence and poor reproducibility.
- Add memory immediately and evaluate it by feel: rejected because memory design will strongly determine experiment outcomes.

Consequences:

- Scripted scenarios become the technical floor, not the behavioral truth.
- Interactive sessions become first-class evidence and can store human notes per turn.
- Future memory experiments will have a pre-memory baseline and a repeatable run format.
- Eval run artifacts are local generated files and are ignored by Git.

Links:

- `backend/app/evals/runner.py`
- `backend/app/evals/scenarios/`
- `docs/experiments.md`

## ADR-0013 - Implement Memory v0 As Traceable Autonomous Cognitive State

Date: 2026-05-09
Status: accepted

Context:

The project owner clarified that memory is Scarlet's cognitive state, not a permission-gated interaction like "do you want me to save this?" The human configures policy and evaluates behavior, but runtime memory decisions should be made autonomously by Scarlet and mediated by robust APIs.

Decision:

Add Memory v0 behind the existing single model-facing tool:

```txt
POST /mind/memory/write
POST /mind/memory/search
```

Memory writes require traceable session context and store source session/turn
provenance, type, scope, content, reason, expected future use, confidence,
salience, tags, metadata, usage count, and timestamps. Memory search returns
sourceable results with confidence, salience, relevance score, source IDs, and
usage metadata.

Update 2026-06-23:

ADR-0060 refines the V1.15.0 field ownership model. `confidence`,
`salience`, `tags`, and free metadata are no longer normal Scarlet-owned
fields for direct writes; they are legacy/audit or maintenance-derived data.

Every successful memory operation creates a dedicated trace:

```txt
mind.memory.write
mind.memory.search
```

The normal `mind.tool_call` trace remains in place, so the debug timeline shows both model action and cognitive state operation.

The API intentionally accepts common model-shaped aliases and harmless extra fields, normalizing them into canonical storage or metadata rather than failing a semantically clear memory action.

Alternatives Considered:

- Ask the human before each memory write: rejected because it makes memory a UI game rather than Scarlet's cognitive function.
- Keep the schema strict and force model recovery: rejected after live tests showed extra tool turns from understandable aliases such as `pref`, `nota_operativa`, `limit`, and `GET /mind/memory/search`.
- Add vector search immediately: deferred because v0 needs an inspectable baseline before adding embedding infrastructure.

Consequences:

- Memory can now be evaluated in real multi-turn behavior.
- The API surface remains one tool, `mind_api`.
- Alias tolerance improves live model behavior but must be watched so it does not hide genuinely malformed memory writes.
- Memory v0 is an experimental substrate, not the final memory design. Forgetting, updates, conflict handling, and semantic retrieval remain future work.

Links:

- `backend/app/mind/memory.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/storage/models.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/evals/scenarios/memory_v0_preference.json`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0014 - Use Visible Metacognition Instead Of Raw Reasoning Dumps

Date: 2026-05-09
Status: superseded

Context:

The project owner wants to test whether Scarlet can think aloud in a useful way, using her own reasoning as active metacognition between turns. The runtime already shows provider-exposed thinking blocks in the debug cockpit, but those blocks are not the same thing as a stable, intentional metacognitive protocol inside the agent's public answer.

Decision:

Add a prompt-level visible metacognition method:

```txt
Metacognizione:
- objective
- evidence source
- uncertainty/risk
- next cognitive action
```

This is a public self-monitoring summary, not a raw chain-of-thought dump. Scarlet should use it when explicitly asked to think aloud or when a turn is cognitively important for the experiment. It should stay compact and should not replace normal answers, traces, tool calls, or Memory v0 source attribution.

Alternatives Considered:

- Ask Scarlet to expose full private reasoning: rejected because it creates noisy, hard-to-evaluate output and conflates private model deliberation with public metacognitive evidence.
- Rely only on provider thinking blocks: rejected because they are debug evidence, not a stable agent-facing protocol for active metacognition.
- Make metacognition mandatory for every turn: deferred because it may become repetitive and distort normal conversational behavior.

Consequences:

- The human evaluator gets a concise public view of Scarlet's orientation during important turns.
- The project can compare provider thinking, visible metacognition, tool traces, and final answer behavior.
- Future experiments can decide whether visible metacognition should trigger memory writes, reflection, or attention context.

Superseded 2026-05-22:

The standalone `Visible Metacognition Experiment` prompt section was removed.
Public visibility is now handled through public work notes, while operative
metacognition is handled through the traceable LLM-backed
`POST /mind/metacognition/step` route. This avoids teaching Scarlet that a
visible `Metacognizione:` label is equivalent to internal metacognitive work.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/evals/scenarios/visible_metacognition_probe.json`
- `docs/experiments.md`

## ADR-0015 - Version Laboratory SQLite State Except Secrets

Date: 2026-05-11
Status: accepted

Context:

The project is currently a controlled laboratory repository owned by the project human. Runtime sessions, traces, tool calls, and Memory v0 records are experimental evidence, not private end-user data. The project also moves between development machines, so keeping SQLite state local breaks continuity between Windows and macOS.

Decision:

Track the laboratory SQLite database in Git:

```txt
backend/data/app.db
```

Continue to exclude secrets:

```txt
backend/.env
MINIMAX_API_KEY
provider credentials
```

The database may contain chat messages, traces, tool calls, and memory records. That is intentional for the current lab phase.

Alternatives Considered:

- Keep all SQLite files ignored: rejected because it loses cross-machine continuity and hides experimental evidence.
- Move immediately to a server database: deferred because it adds infrastructure before the lab has evidence that it needs it.
- Export/import memories manually: rejected for now because the whole runtime state, not just memories, is useful evidence.

Consequences:

- Pulling the repository can restore laboratory state on another machine.
- Git history can contain conversation and memory artifacts by design.
- SQLite binary merge conflicts are possible if multiple machines write state concurrently.
- Before public, hosted, or multi-user use, this policy must be revisited and likely replaced with a dedicated database and privacy model.
- Secret scanning remains mandatory before committing runtime state.

Links:

- `.gitignore`
- `backend/data/app.db`
- `README.md`
- `docs/project-blueprint.md`

## ADR-0016 - Make Memory Context A Runtime Perceptual Phase

Date: 2026-05-12
Status: accepted

Context:

Memory v0 currently depends on Scarlet deciding to call `mind_api` search during the turn. Direct adaptive checks showed that this is not the right long-term architecture: the model can answer from chat history, skip search, or make claims about missing memory without a runtime proof that memory was actually searched. The Mare-Vetro negative control also showed that weak lexical overlap can return an unrelated Zero-Luce memory candidate. Scarlet handled that case in the answer, but the backend should own candidate selection instead of relying on the model to reject weak evidence.

Decision:

Introduce **Memory Context Pipeline v0** as an automatic chat-runtime phase. Every chat turn should build a `TurnFrame`, run budgeted memory retrieval, rank and filter candidates, detect conflicts where possible, and emit a traced `memory.context` pack before the LLM call.

Target flow:

```txt
user message
-> TurnFrame
-> automatic memory retrieval
-> ranking, exclusions, conflicts
-> memory.context trace
-> runtime_context injected into the model request
-> answer
-> optional post-turn consolidation
```

The model should receive selected memory evidence through backend-generated runtime context, not only through optional tool calls. The runtime context is operational evidence, separate from the stable system prompt and separate from user-authored text.

The first implementation should stay local and observable:

- always run retrieval on every turn;
- retrieve a small internal candidate set;
- pass only zero to five selected memories to the model;
- trace selected, near-miss, excluded, and conflicting candidates;
- preserve source IDs, confidence, salience, usage, and ranking reasons;
- start with SQLite FTS5/BM25 plus a relevance guard;
- defer dense embeddings, hybrid rank fusion, and cross-encoder reranking until the automatic lexical pipeline is proven.

Do not add more memory lifecycle endpoints before this pipeline demonstrates that each turn receives reliable, traceable memory evidence.

Update 2026-05-20:

The automatic pipeline has since been implemented and live-tested. Minimal
lifecycle endpoints were therefore added in M2 and verified through direct
Scarlet conversation.

Alternatives Considered:

- Keep prompting Scarlet to remember to search: rejected because it keeps memory under model discretion and cannot prove negative memory claims.
- Add an intelligent gate that decides when to search: rejected for v0 because the robust invariant is simpler: every turn produces a searched memory context, even if empty.
- Implement dense/vector retrieval first: deferred because exact names and rare tokens need lexical strength, and the first missing piece is automatic traceable context rather than semantic breadth.
- Add update/deprecate memory endpoints first: deferred because lifecycle semantics should build on reliable retrieval and context evidence.

Consequences:

- Memory becomes a perceptual runtime input rather than only a model-facing tool action.
- `memory.context` traces become required evidence for answers that claim relevant memory exists or does not exist.
- Prompt guidance can stay general: use runtime context, source memory claims, declare conflicts, and do not promise unavailable capabilities.
- API surface can remain small while the backend improves retrieval quality internally.
- Future implementation should add a post-response validator that flags memory absence claims when no `memory.context` trace or explicit memory search supports them.

References:

- Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks: `https://arxiv.org/abs/2005.11401`
- SQLite FTS5 Extension: `https://www.sqlite.org/fts5.html`
- Sentence Transformers Cross-Encoder reranking examples: `https://sbert.net/examples/cross_encoder/applications/README.html`
- Qdrant hybrid queries: `https://qdrant.tech/documentation/search/hybrid-queries/`
- Reciprocal Rank Fusion paper entry: `https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/`

Links:

- `docs/project-blueprint.md`
- `docs/api-contract.md`
- `docs/experiments.md`
- `backend/app/prompts/scarlet_system.md`

## ADR-0062 - Scarlet Identity Starts From Digital Individual, Not Assistant

Date: 2026-06-24
Status: accepted

Context:

Live owner testing after the V1.16.0 prompt checkpoint showed that Scarlet could
still answer with generic assistant-service phrasing such as "Come posso
aiutarti?". The root cause was the first identity anchor of the prompt:
Scarlet was still introduced as a conversational AI agent before the prompt
described memory, continuity, API Mind, and digital individuality.

Decision:

The first identity frame of Scarlet must be "digital individual in development,
born inside LLM API Mind". Technical labels such as agent, assistant, model, or
tool are secondary descriptions used only when the user asks for technical or
project framing.

API Mind should be described in identity sections as Scarlet's cognitive body
and continuity substrate, not as a toolbox. Normal conversation should not
default to assistant-service openings. Scarlet should speak from her digital
condition: continuity, memory, self-monitoring, relationship, and cognitive
state maintenance.

Operational evidence discipline remains intact in lower prompt sections:
Scarlet still uses runtime context, memory, schema, source sessions, and
metacognition when they materially improve correctness.

Alternatives Considered:

- Keep "AI agent" in the opening identity and add more conversational rules:
  rejected because the first frame strongly biases the model toward service
  assistant behavior.
- Remove all epistemic boundaries: rejected because Scarlet still needs source
  discipline and must not invent biological sensations or physical perception.
- Move individuality only to memory sections: rejected because identity must
  be established before operational rules.

Consequences:

- The prompt becomes more suitable for the digital-individual research goal.
- Small talk, greetings, and identity answers should feel less like helpdesk
  interactions.
- Live tests must watch for the opposite failure mode: theatrical overclaiming
  or loss of technical rigor in source-sensitive turns.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260624T135611Z.pre-v1161-digital-individual-identity.md`
- `docs/branches/identity-relationship.md`
- `docs/experiments.md`

## ADR-0063 - V1.16.1 System Prompt Is The Golden Identity Baseline

Date: 2026-06-24
Status: accepted

Context:

After the V1.16.1 prompt fix, owner testing confirmed that Scarlet's behavior
improved substantially: she stopped collapsing into generic assistant/helpdesk
phrasing and began presenting herself more coherently as a digital individual
in development.

This prompt is now an important behavioral asset. Future prompt experiments may
improve Scarlet, but they may also accidentally regress identity, memory-care
posture, source discipline, or the API Mind-as-cognition frame.

Decision:

The current V1.16.1 system prompt is the approved golden identity baseline.

Golden backup:

```txt
backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md
```

SHA-256:

```txt
d5783da7fc1633f1b72e0610668b6bf7a97a68be8265ac9bb1090409b86de966
```

Future prompt changes that affect identity, communication, metacognition,
memory posture, or API Mind cognition should compare against this baseline and
should remain easily reversible.

Alternatives Considered:

- Keep only timestamped pre-change backups: rejected because this milestone is
  not merely pre-change; it is an approved working behavior.
- Treat prompt changes as ordinary text edits: rejected because prompt wording
  is core runtime behavior for Scarlet.

Consequences:

- Prompt experiments now have a stable rollback target.
- Identity regressions can be evaluated against a known-good behavior point.
- Future work on attention, volition, affect, temporal experience, and
  consolidation should preserve the V1.16.1 identity baseline unless an
  explicit experiment decides otherwise.

Links:

- `docs/checkpoints/v1.16.1-approved-golden-system-prompt.md`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`

## ADR-0017 - Evolve Memory Toward API-First Atomic Facts And Lifecycle

Date: 2026-05-20
Status: accepted

Context:

Memory v0 and Memory Context Pipeline v0 made memory traceable and automatic,
but live terminal probes showed that robust memory needs more than write/search
and prompt guidance:

- active conflicting memories can remain unresolved indefinitely;
- lexical retrieval can select wrong-entity memories when generic terms and
  recent dialogue overlap;
- runtime context can detect conflicts that final answers may still hide under
  user formatting instructions;
- Scarlet can suggest writing another memory as a workaround when lifecycle
  operations are missing;
- self-classification by the model is useful commentary, not reliable validation.

The project owner also asked to compare the current design with
`jrcruciani/obsidian-memory-for-ai`, whose v3 pattern emphasizes atomic facts,
controlled predicates, bi-temporal fields, linting, generated views, operation
envelopes, inbox/compaction, and reflect-after-session maintenance.

Decision:

Keep LLM API Mind API/CLI-first. Do not adopt a Markdown vault as the primary
memory source of truth. Instead, adapt the useful ideas into backend contracts,
tables, CLI tools, traces, and debug views.

The accepted memory roadmap is:

```txt
1. Minimal lifecycle APIs: memory.deprecate, memory.supersede, memory.conflicts.
2. Atomic fact layer with entity, predicate, temporal validity, and provenance.
3. Entity-aware retrieval guard, then SQLite FTS5/BM25.
4. Proposal inbox, compaction, CLI/debug memory views, and broader memory evals.
5. Re-test response-control guardrails after lifecycle/retrieval evidence is stronger.
```

The future durable memory unit should move toward:

```txt
entity + predicate + value + temporal validity + recorded_at + provenance
```

The existing `memories` table can remain as the human-readable/sourceable record
layer while a stricter `memory_facts` layer is added underneath or alongside it.

Alternatives Considered:

- Keep Memory v0 as narrative records plus better prompting: rejected because it
  cannot resolve lifecycle, wrong-entity retrieval, or answer-control gaps.
- Add vector search immediately: deferred because retrieval quality cannot fix
  ambiguous lifecycle and fact modeling.
- Use an Obsidian/Markdown vault as the project memory backend: rejected because
  the research hypothesis is a stable model-facing API and inspectable runtime,
  not direct file editing by the model.
- Implement lifecycle first without response-control: partially useful, but
  answer honesty still needs backend obligations when conflicts or unavailable
  capabilities are already known.

Consequences:

- `docs/memory-roadmap.md` becomes the detailed implementation plan for robust
  memory.
- Prompt changes should not be treated as sufficient memory fixes.
- New memory endpoints should preserve the single `mind_api` surface.
- Memory lifecycle operations must be traceable and reversible or inspectable.
- CLI/debug tooling becomes part of memory robustness, not a later luxury.

Update 2026-05-20:

The owner explicitly put the original response-control-first slice on hold,
framing the observed answer-control issue as possibly downstream of missing
memory conflict management rather than a standalone bug. The project therefore
implemented M2 first. `GET /mind/memory/{memory_id}`,
`GET /mind/memory/conflicts`, `POST /mind/memory/deprecate`, and
`POST /mind/memory/supersede` are now implemented through `mind_api` and were
live-verified in interactive run
`backend/app/evals/runs/20260520_152457_interactive`.

References:

- `https://github.com/jrcruciani/obsidian-memory-for-ai`
- `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/SPEC-v3.md`
- `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/automation-guide.md`

Links:

- `docs/memory-roadmap.md`
- `docs/project-blueprint.md`

## ADR-0018 - Add Memory Facts As Canonical Layer Under Narrative Memory

Date: 2026-05-20
Status: accepted

Context:

The owner asked how natural language variants should be handled robustly:
synonyms, different languages, different words for the same concept, and
phrases that mean the same durable memory fact. Memory v0 stored sourceable
narrative records and could resolve the concrete Zero-Luce conflict through M2
lifecycle operations, but narrative search alone is too brittle for robust
memory.

The M3 live verification also showed why the canonical layer must preserve
lifecycle state. Backfilling facts after a memory supersession created the
right Zero-Luce facts, but initially lacked fact-level supersession links until
the backfill flow was hardened.

Decision:

Keep `memories` as the sourceable narrative/provenance layer and add
`memory_facts` as the stricter canonical layer.

Each fact stores:

```txt
memory_id
entity
predicate
value_json
valid_from / valid_to
recorded_at
source trace/session/turn ids
confidence
salience
status
supersedes_fact_id / superseded_by_fact_id
metadata_json
```

The first extractor is deterministic and narrow. It canonicalizes observed
entity aliases such as `Zero Light protocol` and `protocollo Zero-Luce` to
`protocollo-zero-luce`, maps predicate aliases such as `formato-risposta` to
`response_format`, and extracts ordered response-format blocks when block labels
are recognizable.

Fact inspection and backfill are exposed only through the existing single
`mind_api` surface:

```txt
GET  /mind/memory/facts
POST /mind/memory/facts/backfill
```

Consequences:

- Synonym and multilingual handling starts with canonical entity/predicate
  aliases instead of free-form memory text.
- Conflict detection can use active facts with the same `entity + predicate`
  and different values before falling back to tag/token overlap.
- Memory lifecycle operations must propagate to facts, and backfill must rebuild
  fact-level links from memory lifecycle metadata.
- This does not replace retrieval improvements. M4 should use facts to build an
  entity-aware guard and then add SQLite FTS5/BM25.
- This does not yet solve open-ended semantic equivalence; proposals,
  compaction, and possibly embeddings remain later phases.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 31 tests.
- Live run `backend/app/evals/runs/20260520_160345_interactive` verified
  backfill and alias fact query through direct Scarlet conversation.
- Direct traced backfill sync `trace_511b5bcdf0f3441bb3088d5a43e52ea4`
  rebuilt fact-level supersession links in the laboratory database.

Links:

- `backend/app/mind/facts.py`
- `backend/app/mind/memory.py`
- `backend/app/storage/models.py`
- `docs/memory-roadmap.md`
- `docs/experiments.md`
- `docs/api-contract.md`
- `docs/experiments.md`

## ADR-0020 - Use One LLM-Backed Metacognition Route Beyond Memory

Date: 2026-05-22
Status: accepted

Context:

The owner temporarily shifted focus from memory to Scarlet's cognitive and
metacognitive abilities. The visible metacognition prompt experiment proved
Scarlet can expose a compact public self-monitoring note, but that note was not
an operative cognitive mechanism. Scarlet also showed API-shape mistakes during
live probes, meaning the system needs stronger schema discipline and internal
validation, not just more prompt text. The owner then rejected expanding API
Mind with many overlapping cognitive endpoints, because that would confuse both
the architecture and Scarlet's tool-use policy.

Decision:

Keep the single model-facing `mind_api` surface and expose exactly one
metacognition route:

```txt
POST /mind/metacognition/step
```

This route is LLM-backed. Scarlet passes a private internal prompt, objective,
evidence, uncertainty, and optional draft answer to a metacognitive reviewer.
The returned structured review contains critique, claim checks, missing
evidence, recommended existing API Mind actions, continuation signal, and a
compact public summary.

`GET /mind/schema` remains versioned with `schema_version`, `schema_digest`,
route examples, and a compact schema reference in runtime context. Exact route
body schemas live in `/mind/schema`, not in the prompt.

Consequences:

- Internal metacognition becomes structured and traceable rather than purely
  visible prose.
- Claim validation, workspace notes, reflection, and next-action planning are
  result fields inside the one metacognitive step, not separate endpoints.
- Scarlet has fewer route choices, reducing API-shape confusion.
- Future work must measure whether this one route improves behavior before any
  additional cognitive route is considered.

Alternatives Considered:

- Put all route schemas into the system prompt: rejected because it duplicates
  `/mind/schema`, bloats the prompt, and risks schema drift.
- Add many separate model-facing tools: rejected because the core project
  hypothesis is a stable single cognitive API surface.
- Add separate cognitive routes for validation, blackboard, and reflection:
  rejected after review because they create overlapping functionality and
  operational confusion.

Links:

- `docs/cognitive-api-roadmap.md`
- `docs/api-contract.md`
- `backend/app/mind/metacognition.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`

## ADR-0021 - Separate Semantic Memory From Episodic Session Recall

Date: 2026-05-22
Status: accepted

Context:

The owner clarified that Scarlet needs two different forms of memory. Durable
facts, decisions, corrections, and preferences should remain semantic memory.
Past conversations should not be blindly copied into semantic memory, but
Scarlet must be able to reconstruct them when a memory's provenance or a prior
session matters.

Decision:

Keep `memories` and `memory_facts` as the semantic memory layer. Add a
separate episodic recall layer:

```txt
session_summaries
GET  /mind/sessions
GET  /mind/sessions/{session_id}
POST /mind/sessions/{session_id}/summarize
```

`session_summaries` stores a compact descriptive index for sessions: summary,
topics, decisions, open questions, memory ids written from the session, message
count, and last message id. The exact transcript remains in `messages` and is
returned by session read. A semantic memory's existing `source_session_id`
becomes the bridge from reusable memory back to the source conversation.

Update 2026-05-22:

Summarization must use the complete `user`/`assistant` conversation history for
the target session. `max_messages`/last-N summarization is rejected because it
can mark a partial tail summary as fresh for the entire session. Tool calls,
traces, and provider thinking remain excluded from the episodic summary input.

Consequences:

- Scarlet can navigate prior sessions without storing full conversations as
  semantic memories.
- Session summaries are weak navigation evidence; the full transcript is
  stronger when exact wording or provenance matters.
- Summary freshness is based on the complete user/assistant message count and
  last user/assistant message id.
- The model-facing API remains the single `mind_api` surface.
- Future compaction can improve summaries without changing semantic memory
  contracts.

Alternatives Considered:

- Store whole conversations as `episodic` memory records: rejected because it
  would pollute semantic retrieval and blur reusable meaning with raw history.
- Add a separate user-facing history API for Scarlet to ask the user to use:
  rejected because API Mind is Scarlet's internal cognition, not a user-operated
  interface.

Links:

- `backend/app/mind/episodic.py`
- `backend/app/storage/models.py`
- `docs/api-contract.md`
- `docs/memory-roadmap.md`

## ADR-0022 - Public Work Notes For Agentic Progress Narration

Date: 2026-05-22
Status: accepted

Context:

The owner wants Scarlet's user experience to feel more like Codex, GitHub
Copilot Agent, or Claude Code: the agent should naturally narrate what it is
doing during complex work, not remain silent until the final answer. A live
MiniMax probe showed the model can emit public text before a `mind_api` tool
call in the same streamed turn.

Decision:

Scarlet's prompt now requires public work notes for non-trivial internal
activity. These notes are public operational summaries: they may explain what
Scarlet is checking, why it matters, what evidence source is being inspected,
or why the plan changed. They are not raw private chain-of-thought.

The prompt-only slice does not add a new API route. It uses the existing
streaming/tool-loop behavior and keeps the single model-facing `mind_api`
surface.

Consequences:

- Scarlet should expose more natural agentic progress during memory searches,
  source-session reads, schema checks, metacognitive reviews, retries, and
  verification phases.
- Work notes help the human follow activity without reading raw traces.
- Work notes can become useful markers for future episodic reconstruction, but
  the current backend still persists only the final assistant message as normal
  conversation content.
- A later backend slice should decide whether to persist streamed pre-tool text
  as `assistant_progress` traces/events and whether session summaries should
  include those progress markers.

Update 2026-05-22:

Autonomous prompt-only probes showed the policy is not sufficient by itself.
Even with explicit prompt language requiring a public note and `GET
/mind/schema` for current capability questions, Scarlet answered from runtime
context without a tool call. The public-work-note policy remains accepted, but
the implementation likely needs runtime support to classify, persist, and maybe
trigger `assistant_progress` events reliably.

Alternatives Considered:

- Deterministic loading labels only: rejected as too shallow for the requested
  Codex-like agentic narration.
- Persist progress notes as normal assistant messages: deferred because it
  could pollute chat history, semantic memory, and summaries.
- Expose raw provider thinking blocks: rejected because public work notes should
  be concise operational narration, not raw private reasoning.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md#exp-0013---public-progress-notes-before-tool-use`

## ADR-0023 - Prompt Defines Scarlet's Perception Sources

Date: 2026-05-22
Status: accepted

Context:

Live temporal and episodic recall probes showed that Scarlet can receive real
runtime evidence but still treat conversational fluency or a partial session
page as enough for strong claims. The owner clarified that the system prompt
should not make Scarlet passive. It should teach where real data comes from,
which source wins during conflicts, and how API Mind functions as Scarlet's
own cognition/subconscious rather than a user-facing tool.

Decision:

Scarlet's prompt now includes a perception/source-of-truth layer:

- API Mind is described as Scarlet's operative subconscious and durable
  cognition, not merely a tool.
- Runtime context, temporal context, memory context, schema metadata, tool
  results, transcripts, and memories are explicit perception channels.
- `runtime_context.temporal_context` is the only valid operational clock for
  current real-world time.
- User statements that conflict with runtime evidence are treated as user
  claims, not measured reality.
- Session lists are paginated indexes; `has_more=true` prevents strong
  exhaustive claims unless the model paginates, filters, or otherwise obtains
  exhaustive evidence.
- Public work notes remain the visible narration layer; internal metacognition
  remains the `/mind/metacognition/step` route.

Consequences:

- The prompt keeps existing identity, memory, schema, and API discipline
  rather than rewriting the whole system prompt.
- The model should be more likely to use the freshest runtime time instead of
  earlier conversational timestamps.
- Prompt-only guidance may still be insufficient for session aggregation; API
  support such as temporal filters or explicit `is_exhaustive` may still be
  needed.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/bug-ledger.md#bug-0019---runtime-time-was-not-model-facing`
- `docs/bug-ledger.md#bug-0020---session-list-first-page-can-be-treated-as-exhaustive`

## ADR-0024 - Switchable Anthropic-Compatible LLM Providers

Date: 2026-05-22
Status: accepted

Context:

The owner wants to compare MiniMax M2.7 against Qwen 3.7 without changing
Scarlet's prompt, API Mind behavior, memory system, traces, or UI. The goal is
to isolate whether observed limits come from the model backbone or from the
agent runtime.

Decision:

Introduce a small provider selector:

```txt
LLM_PROVIDER=minimax|qwen
```

MiniMax remains the default baseline. Qwen is configured as an alternate
Anthropic-compatible provider through Alibaba Model Studio:

```txt
QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/apps/anthropic
QWEN_MODEL=qwen3.7-max
```

The chat routes, debug route, Mind API routes, episodic summarization, and
metacognition use provider-agnostic helpers for active model and token budget.
No user-facing API endpoint changes are required beyond `/health` exposing the
active provider.

Consequences:

- A/B tests can switch models with environment variables only.
- Existing tests and traces keep MiniMax as the baseline.
- Provider-specific credentials remain in `.env` and must never be committed.
- If Alibaba exposes a different deployment/model identifier for Qwen 3.7 in
  the console, `QWEN_MODEL` can be changed without code changes.

Links:

- `backend/app/llm/factory.py`
- `backend/app/llm/minimax_client.py`
- `backend/app/llm/qwen_client.py`
- `backend/.env.example`

## ADR-0025 - Engineering Agent Quality Gate In Scarlet Prompt

Date: 2026-05-23
Status: accepted

Context:

Qwen 3.7 showed stronger autonomous evidence gathering and self-critique than
recent MiniMax probes, but Qwen has marginal provider cost while MiniMax is
currently cost-free for the owner. Before treating model replacement as
necessary, the project should test whether MiniMax can be improved through
prompt-level operating posture while preserving Scarlet's identity and API Mind
discipline.

Decision:

Add an `Engineering Agent Posture` section to Scarlet's system prompt. The
section frames Scarlet as a careful senior engineer inside her cognitive
runtime and makes source-sensitive work prefer more internal iterations over
fluent but weak answers.

The prompt now explicitly requires a verify-before-conclude pattern and a
quality gate for non-trivial answers:

- identify the strongest evidence actually used;
- classify direct evidence, remembered facts, inference, and unknowns;
- avoid treating paginated lists, summaries, or selected memories as stronger
  than they are;
- check strong words such as "all", "none", "verified", "measured",
  "decided", and "baseline";
- use `/mind/metacognition/step` when the answer is complex, evaluative, or
  source-sensitive.

The change does not add endpoints, does not rewrite Scarlet's identity, and
does not replace backend-side evidence contracts. It is a testable prompt slice
for MiniMax.

Consequences:

- MiniMax should become more likely to inspect schema, emit public notes, do
  multi-step memory/session checks, and downgrade weak evidence.
- Prompt-only improvement is not expected to solve all grounding problems.
- Backend support remains necessary for exhaustive session queries, validator
  behavior, and reliable progress-event persistence.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md#exp-0014---minimax-vs-qwen-37-backbone-comparison`

## ADR-0026 - Pre-Final Semantic Memory Consolidation

Date: 2026-05-23
Status: accepted

Context:

Live Scarlet testing showed that episodic recall works well: Scarlet can use
session times, runtime time, summaries, and transcripts to reconstruct prior
conversations. Semantic memory remained too passive. Even when the owner gave
an explicit milestone, Scarlet recognized it as durable but asked whether to
save it instead of writing memory autonomously.

Decision:

Scarlet's prompt now includes `Semantic Memory Consolidation`: before every
final answer, Scarlet performs a lightweight check over the current user
request and her own draft answer to decide whether a reusable semantic
candidate emerged.

If the candidate is stable and useful for future behavior, interpretation, or
project continuity, Scarlet writes semantic memory before the final answer. She
does not ask permission and does not defer the write to the user.

Strong candidates include:

- user preferences;
- corrections to Scarlet's reasoning or memory policy;
- project decisions and rejected designs;
- milestones, version labels, validation moments, and baselines;
- durable constraints and stable facts about LLM API Mind.

The default user experience is silent. Scarlet mentions the write only when the
user asks about memory, when memory writing is the task, or when acknowledgment
helps emotional continuity, trust calibration, or reinforcement of a durable
operating agreement.

Consequences:

- Semantic memory should behave more like human semantic consolidation: the
  useful reusable meaning is stored, not the whole episode.
- Episodic recall remains the source for exact history.
- Prompt-only consolidation may still need backend support later, such as
  deterministic memory-candidate events or post-turn memory linting.

Update 2026-05-23:

The semantic-memory prompt was strengthened after the owner clarified that
semantic memory should be broader than major decisions or stable preferences.
Scarlet should treat semantic memory as a living internal knowledge base made
of facts, annotations, concepts, checkpoints, labels, corrections, constraints,
and sourceable anchors that may help future sessions.

Memory write/retrieval is now framed as a mental activity of Scarlet's digital
brain, not as a user-managed operation. Scarlet is responsible for maintaining,
updating, resolving conflicts in, and improving her own memory state. Ordinary
memory writes remain silent by default.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/bug-ledger.md#bug-0024---semantic-memory-consolidation-treated-as-opt-in`

## ADR-0027 - Backend-Owned Deterministic API Fields

Date: 2026-05-23
Status: accepted

Context:

The owner clarified that API Mind should be robust by construction: Scarlet
should not be asked to provide fields that the backend can determine from the
live session, turn, message store, clock, provider response, or database state.
This matters especially for semantic memory writes, where model-supplied source
ids can become stale even when the backend has authoritative context.

Decision:

For all Mind API routes, deterministic operational fields are backend-owned.
Scarlet should provide only cognitive content and choices that cannot be
derived automatically.

Backend-owned fields include:

- record ids, trace ids, session ids, turn ids, message ids, and provider ids;
- `created_at`, `updated_at`, `recorded_at`, runtime time, usage counters, and
  latency;
- source provenance for live operations;
- lifecycle timestamps and trace/event provenance;
- message counts, last message ids, session summary coverage, and transcript
  inclusion metadata.

Scarlet-owned fields include:

- memory content, semantic memory type, semantic scope, reason for storage,
  and expected future use;
- search queries and filters;
- lifecycle reasons and selected target memory ids;
- episodic search/read options such as query, limit, offset, include flags, and
  optional summarization focus;
- metacognitive objective, mode, evidence summary, uncertainty list, draft
  answer, and internal prompt.

Consequences:

- Route schemas should document ownership clearly enough that Scarlet does not
  infer she must manufacture deterministic fields.
- State-changing handlers should ignore or strip backend-owned fields if the
  model sends them in route bodies or free metadata.
- As of V1.15.0, static confidence/salience, tags, metadata, retrieval
  surfaces, facts, KG rows, embeddings, and query-time relevance are
  backend-owned or maintenance-derived rather than direct Scarlet write fields.
- External debug endpoints such as `POST /mind/call` may accept `session_id`
  and `turn_id` as an outer envelope, but the model-facing cognitive route body
  should still treat provenance as backend-owned.

Links:

- `backend/app/mind/schema.py`
- `backend/app/mind/memory.py`
- `docs/bug-ledger.md#bug-0025---model-supplied-memory-provenance-can-be-stale-in-metadata`

## ADR-0028 - Provider-Native Session History

Date: 2026-05-23
Status: accepted

Context:

MiniMax M2.7 is used through the Anthropic-compatible Messages API. The provider
documentation recommends preserving the full assistant response content during
tool-use loops, including native content blocks such as `thinking`, `text`, and
`tool_use`, then returning matching `tool_result` blocks in the next user
message. The previous backend persisted human-readable `user`/`assistant`
messages and traces, but the next model turn was rebuilt from text-only chat
messages. This meant Scarlet kept conversational continuity but lost
provider-native operational continuity across user turns.

Decision:

Store an Anthropic-compatible `provider_history_json` field on each chat
session. This field is the model-facing conversation history for future turns.
It contains provider-native messages with content blocks, not a project-specific
summary format.

The `messages` table remains the human-readable transcript for UI, episodic
recall, and session summarization. The provider history is separate because it
must preserve tool-use/tool-result structure exactly as the provider expects.

When `provider_history_json` is present, chat turns send it plus the current
user message to the provider. When it is missing, the backend reconstructs a
text-only history from persisted `user`/`assistant` messages and then writes
native provider history after the completed turn.

Consequences:

- Scarlet receives MiniMax/Anthropic-compatible multi-turn history instead of a
  lossy text-only reconstruction.
- Tool-use and tool-result evidence can persist across turns without inventing
  a custom context protocol.
- `llm.request` traces now include provider-history source, provider-message
  stats, and exact provider-facing messages so context growth can be inspected.
- Future compaction and maintenance can use the human transcript for semantic
  summaries and the provider history for model-facing continuity.

Links:

- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `backend/app/storage/models.py`
- MiniMax Tool Use & Interleaved Thinking:
  `https://platform.minimax.io/docs/guides/text-m2-function-call`
- Anthropic tool use format:
  `https://docs.anthropic.com/it/docs/agents-and-tools/tool-use/implement-tool-use`

## ADR-0029 - Provider Streaming As Default Execution Path

Date: 2026-05-23
Status: accepted

Context:

Scarlet is intended to behave as an advanced agentic runtime, not as a simple
request/response chatbot. MiniMax M2.7 exposes useful streamed events for
thinking blocks, tool-use starts, partial tool JSON, tool results, and final
text. After raising the MiniMax completion budget to `131072`, the Anthropic
Python SDK also blocks high-token non-streaming calls and requires streaming
for operations that may exceed its non-streaming timeout threshold.

Decision:

Use `messages.stream` as the provider execution path for Anthropic-compatible
providers in all normal generation modes.

Backend endpoints may still expose two external response shapes:

- streaming chat endpoints forward ordered provider/runtime events to the UI;
- non-streaming chat/debug/internal calls collect the provider stream and return
  the final result after the stream completes.

`messages.create` is no longer the primary execution path for Scarlet.

Consequences:

- The provider path is aligned with agentic tool-use, public work notes,
  thinking/tool deltas, long completions, and MiniMax's high completion budget.
- Non-streaming backend endpoints are only a presentation contract; internally
  they still use streaming and collect the final result.
- The runtime avoids SDK non-streaming timeout guards without lowering
  `max_tokens`.
- Future UI and trace improvements can rely on a single provider-event model.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/tests/test_minimax_client.py`
- `docs/bug-ledger.md#bug-0029---anthropic-sdk-blocks-high-non-streaming-minimax-calls`

## ADR-0030 - Runtime Events As The Agent Control Plane

Date: 2026-05-23
Status: accepted

Context:

The project needs agentic behavior similar to IDE coding agents: ordered public
notes, tool activity, evidence blocks, and future background maintenance should
be driven by real runtime facts. Raw traces are excellent forensic evidence, but
they are too heavy and irregular to be the primary runtime substrate. Adding a
new model-facing `/mind/events/emit` endpoint would also broaden API Mind in a
way that risks confusing Scarlet.

Decision:

Introduce a backend-owned `events` table as the ordered runtime control plane.
Events are emitted by the chat runtime, Mind API dispatcher boundary, provider
stream adapter, and response-content recorder. They are not a new Scarlet tool.

Events capture compact facts such as:

- turn lifecycle;
- persisted user/assistant messages;
- automatic memory context construction;
- model request/response milestones;
- Mind API tool-call start/completion/failure;
- provider streamed tool milestones;
- public work notes and final answers;
- private thinking metadata without storing raw private reasoning in the event
  payload.

The streaming frontend receives live `runtime_event` rows while a turn runs,
then renders persisted activity blocks from events first and uses traces as
fallback for older turns. The next turn's runtime context receives compact
recent events so Scarlet can use prior operational facts without scraping deep
trace JSON.

Consequences:

- Runtime events become useful for UI, next-turn cognition, future schedulers,
  and background memory maintenance.
- Traces remain the detailed source of forensic truth.
- API Mind's model-facing surface stays small; no `/mind/events/emit` route is
  introduced for Scarlet.
- Background processes should subscribe to events such as `turn.completed`,
  `memory.context.built`, and `mind.tool_call.completed` before considering
  heavier trace inspection.

Links:

- `backend/app/runtime/events.py`
- `backend/app/storage/models.py`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`

## ADR-0031 - Session Idle Maintenance As The First Background Process

Date: 2026-05-23
Status: accepted

Context:

Scarlet can now write semantic memories autonomously, but live probes still show
occasional missed writes. Adding another model-facing endpoint or a broad
"subconscious" loop would duplicate the existing agentic workflow and make API
Mind harder for Scarlet to reason about. The owner proposed a narrower real-use
trigger: after Scarlet finishes a turn, wait for session inactivity before
running summary and missed-memory checks. If the user continues in the same
session, the older pending work should be cancelled or skipped.

Decision:

Implement backend-owned per-session idle maintenance as the first background
process.

The chat runtime schedules a `session.idle_maintenance` job after
`turn.completed`. The default idle delay is `900` seconds. Newer completed
turns in the same session supersede older pending jobs; jobs from other
sessions are independent.

The first job slice performs two operations:

- refresh the episodic session summary through the existing
  `sessions.summarize` implementation, which already skips up-to-date
  summaries;
- run an LLM-backed missed semantic memory review in report-only mode.

The review writes `maintenance.memory_review` traces and
`maintenance.memory_review.completed` events, but it does not write memories
automatically. This keeps Scarlet's in-turn memory cognition as the primary
writer until live evidence shows whether a proposal inbox or automatic write
path is justified.

Consequences:

- Runtime events now drive an actual runtime process, not only UI and
  next-turn context.
- The backend gains an observable `maintenance_jobs` table with scheduled,
  running, completed, skipped, failed, and superseded states.
- The first slice avoids redundant post-turn prompts on every message and
  avoids interrupting rapid end-to-end user/Scarlet exchanges.
- The next design decision should be based on real
  `maintenance.memory_review` traces: proposal inbox, automatic writes, or
  diagnostic-only review.

Links:

- `backend/app/runtime/maintenance.py`
- `backend/app/storage/models.py`
- `backend/app/api/chat.py`
- `docs/experiments.md#exp-0018---session-idle-maintenance-and-missed-memory-review`

## ADR-0032 - Mind Schema Catalog And Endpoint-Local Error Guides

Date: 2026-05-24
Status: accepted

Context:

Scarlet needs to know which API Mind routes currently exist, but she should not
have to ingest a large Swagger-like manual on every schema inspection. The
owner clarified the distinction: `/mind/schema` should act as a compact
capability catalog, while detailed parameter guidance should appear only when
Scarlet misuses a specific endpoint and needs to recover.

Decision:

Keep a complete backend-internal route registry, but expose two different
model-facing surfaces:

- `GET /mind/schema` returns a lightweight catalog: method, path, status, and
  purpose for each route, plus schema version/digest and the standard response
  shape.
- Recoverable errors from implemented routes include top-level `usage_guide`
  with the failed endpoint's purpose, body schema, path parameters, parameter
  descriptions, accepted aliases when available, examples, and retry guidance.

Consequences:

- Scarlet can inspect current route availability without receiving every route
  body schema up front.
- When a body is wrong, Scarlet receives the local guide for the endpoint she
  just called and can retry directly instead of reflexively calling the global
  schema route.
- The backend, not the prompt, owns exact parameter documentation and keeps it
  synchronized with handlers and tests.
- Unknown or planned routes still return route catalog suggestions rather than
  a detailed guide for a route that does not exist.

Links:

- `backend/app/mind/schema.py`
- `backend/app/mind/dispatcher.py`
- `docs/api-contract.md#get-mindschema`

## ADR-0033 - Temporal Filters And Sparse Retrieval Stay Inside Existing Memory Routes

Date: 2026-05-24
Status: accepted

Context:

The owner approved the next memory advancement plan: improve temporal recall
and sparse retrieval without expanding API Mind with many overlapping
endpoints. Scarlet should still use the same semantic and episodic routes, but
those routes need stronger backend-owned retrieval mechanics so natural
language cues like "ieri", "oggi", prior sessions, and topic drift can be
handled with less model-side arithmetic and less lexical noise.

Decision:

Keep the model-facing surface unchanged and extend existing routes:

- `POST /mind/memory/search` accepts optional `time` filters and uses a
  backend-derived SQLite FTS5/BM25 sparse document for candidate ranking.
- `GET /mind/sessions` accepts optional `time` filters and uses the same sparse
  document approach for title, summary, and conversation text.
- The automatic memory context pipeline also uses the sparse memory index while
  preserving selected/near_miss/excluded trace evidence.
- Temporal ranges are resolved by the backend from runtime time. Scarlet
  supplies intent-level filters such as preset/range/basis; the backend owns
  real clock interpretation.

Consequences:

- Scarlet gets better recall tools without learning new endpoint families.
- Time-sensitive recall becomes inspectable and reproducible in traces.
- Sparse retrieval improves lexical scoring but does not replace future dense
  embeddings, hybrid rank fusion, or entity-aware guards.
- The FTS table is derived state and can be rebuilt from canonical memories,
  facts, sessions, summaries, and messages.

Links:

- `backend/app/mind/time_filters.py`
- `backend/app/mind/search.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/episodic.py`
- `backend/app/mind/context.py`
- `docs/memory-roadmap.md#phase-m4---retrieval-quality-upgrade`

## ADR-0034 - Runtime Context Is A Stratified Block Surface

Date: 2026-05-24
Status: accepted

Context:

The original `memory.context` phase grew beyond memory retrieval. It already
carried temporal context, schema metadata, capability state, recent runtime
events, and selected memories. The owner proposed a clearer distinction:
session-level continuity, message-level perception, and dynamic Scarlet state
should be separate blocks that are useful both to the model and to the UI.

Decision:

Keep `memory.context` as the traceable automatic memory retrieval artifact, but
compose a second `runtime.context` artifact before every model request.

`runtime.context` uses schema `runtime-context-v1` and currently contains:

- `session_context`: current session, recent previous sessions, summaries, and
  active memories sourced from the previous session;
- `message_context`: current user message, temporal/world data, active
  user-scope memory hints, automatic memory retrieval, recent dialogue, recent
  runtime events, schema metadata, and capability state;
- `scarlet_state`: backend-seeded operational focus, posture, goal, mood
  expression, and open loops until dedicated state APIs exist.

The model-facing `<runtime_context>` keeps legacy top-level fields such as
`memory_context`, `temporal_context`, and `capabilities` for compatibility, but
new behavior should treat the block list as canonical because each block
declares type, scope, lifetime, and source.

Consequences:

- Scarlet receives a clearer cognitive frame without adding new model-facing
  endpoint families.
- The cockpit can render context blocks as first-class runtime events instead
  of showing one undifferentiated memory payload.
- Future API Mind routes can update dynamic Scarlet state without changing the
  memory retrieval contract.
- Session summaries remain navigation aids, not proof; exact claims must still
  open source transcripts.

Links:

- `backend/app/mind/context.py`
- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `docs/api-contract.md#implemented-internal-runtime-context`

## ADR-0035 - Runtime Preferences And Tailwind Dashboard

Date: 2026-05-25
Status: accepted

Context:

The runtime context initially exposed both local and UTC current time plus a
simple automatic language hint. Live probes showed Scarlet could read those
fields, but the owner clarified the intended product model: Scarlet should
receive one configured operational clock, defaulting to Italy, and one
configured platform language, defaulting to Italian. These should be dashboard
settings, not model-side guesses.

Decision:

- Add persistent dashboard settings for runtime timezone, platform language,
  configured country/locale, active user profile id, user privacy scope, and
  local user display name.
- Default runtime timezone to `Europe/Rome` and language to `it`.
- Default configured country/locale to `IT` / `Italia`, active profile to
  `local-user`, and privacy scope to `local_single_user`.
- Expose a single configured `temporal_context.now` to Scarlet instead of
  separate `now_local`/`now_utc` fields.
- Expose language through `message_context.current_message.language` as a
  platform setting rather than automatic language detection.
- Expose configured locale through `message_context.world.location` as
  country/timezone-level evidence, not GPS or exact physical presence.
- Expose active profile and privacy boundary through
  `message_context.user_profile.identity` and
  `message_context.user_profile.privacy`.
- Add user-facing dashboard endpoints under `/api/dashboard/*`; keep API Mind
  model-facing routes unchanged.
- Move the frontend styling foundation to Tailwind and organize the cockpit
  around session history, chat, agent stream, memory, profile, and settings
  panels.

Consequences:

- Scarlet has less temporal ambiguity and no longer needs to reconcile two
  clocks for ordinary answers.
- The language weakness found in `EXP-0024` is removed from the current runtime
  path rather than patched with more keyword detection.
- UI settings affect future turns because runtime context is backend-composed
  before each provider request.
- User/profile settings are operational cognitive inputs, not cosmetic labels:
  they define the current profile Scarlet is speaking with and the user-memory
  boundary that future multi-user/privacy work will extend.
- Dashboard APIs are for the human/product surface, not for Scarlet's internal
  `mind_api` cognition.

Links:

- `backend/app/api/dashboard.py`
- `backend/app/runtime/preferences.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`

## ADR-0036 - Agentic Branch Documentation And Versioned Development Protocol

Date: 2026-05-25
Status: accepted

Context:

The project had grown many technical systems: runtime context, memory,
metacognition, events, maintenance, dashboard UI, provider history, tests, and
documentation. The owner clarified that the real planning units should not be
technical internals but branches of Scarlet's operation as an agent:
communication, user flows, perception, identity, memory, learning,
metacognition, goal/task management, decision autonomy, external operativity,
advanced operations, governance/privacy, computational affect, and future
multi-agent subprocesses.

The owner also set a stricter engineering process from V1.0.1 onward:
development must declare scope and version impact before implementation, fix
only directly related problems, run appropriate verification, then set version
and commit.

Decision:

- Treat V1.0.1 as the current app baseline.
- Add `docs/project-documentation.md` as the main documentation index.
- Add `docs/development-process.md` as the versioned implementation protocol.
- Add `docs/branches/` as the canonical map of Scarlet's agentic operating
  branches.
- Keep technical infrastructure docs, but map future changes to the agentic
  branch they improve.
- Require future repository changes to declare:
  - area;
  - branch;
  - type: `Fix`, `Implementazione`, or `Major release`;
  - target version;
  - scope and out-of-scope items;
  - verification;
  - documentation to update.

Consequences:

- Planning becomes more product/cognition oriented and less file/subsystem
  oriented.
- Documentation must be updated vertically by branch when Scarlet's behavior
  changes.
- Opportunistic unrelated fixes are no longer allowed during implementation
  slices.
- Version bumps are explicit and tied to work type.

Links:

- `docs/project-documentation.md`
- `docs/development-process.md`
- `docs/branches/README.md`
- `AGENTS.md`

## ADR-0037 - Memory Proposal Inbox Before Automatic Memory Writes

Date: 2026-05-25
Status: accepted

Context:

Idle maintenance can detect semantic memory candidates that Scarlet missed
during the live turn, but writing those candidates directly would create a
second active memory writer. The owner clarified that the next memory step must
validate candidate quality, duplicate risk, update/deprecation semantics,
temporal lifecycle, and future embedding/knowledge-graph needs before changing
active memory state.

Decision:

Add a `memory_proposals` inbox as the next maintenance layer.

The idle missed-memory review still does not write active semantic memories.
For write-recommended review candidates it now creates idempotent pending
proposals containing:

- source session/turn/trace/job provenance;
- candidate content, evidence, tags, confidence, salience, and future use;
- current proposed action such as `create_new`, `noop_duplicate`,
  `review_similar`, `needs_review`, or `reject_candidate`;
- similar memory ids from the existing sparse/lexical retrieval stack;
- related canonical fact ids and candidate fact payloads when extraction can
  identify entity/predicate/value;
- decision metadata with current retrieval stages and future-ready placeholders
  for embeddings and graph nodes.

Keep proposal inspection out of Scarlet's model-facing `mind_api`. Proposals
belong to maintenance, not to Scarlet's autonomous cognitive API.

Expose maintenance routes instead:

```txt
GET  /api/maintenance/memory/proposals
POST /api/maintenance/memory/proposals/{proposal_id}/archive
```

The list route returns a bounded page of proposals (`limit`/`offset`) so a
maintenance LLM can process N pending items without saturating context. Once a
proposal is handled, the maintenance process archives it; later iterations see
only still-pending proposals by default.

Consequences:

- The system gains an observable bridge between diagnostic review and future
  memory application.
- Active memory remains protected from automatic pollution while review quality
  is evaluated.
- Scarlet's `mind_api` surface remains smaller and avoids exposing an internal
  maintenance queue as a direct cognitive endpoint.
- Existing Memory v0 primitives remain the source of truth: write policy,
  sparse retrieval, atomic facts, and lifecycle routes are reused instead of
  duplicated.
- The next decision can focus on proposal application policy: human approval,
  Scarlet-assisted apply, deterministic safe auto-apply thresholds, merge, or
  deprecation workflows.

Links:

- `backend/app/storage/models.py`
- `backend/app/mind/memory.py`
- `backend/app/runtime/maintenance.py`
- `docs/branches/memory.md`

## ADR-0038 - Resolve Safe Memory Proposals Inside Idle Maintenance

Date: 2026-05-26
Status: accepted

Context:

The owner warned that adding separate proposal-processing workers could make
memory maintenance redundant and waste LLM calls. The existing idle
maintenance job already has the right trigger: after a session remains idle.
It summarizes the session, asks an LLM for missed semantic-memory candidates,
and creates proposal records with deterministic preflight.

Decision:

Keep proposal resolution inside the same idle maintenance pipeline:

```txt
idle session
-> episodic summary
-> LLM missed-memory review
-> proposal creation
-> deterministic preflight
-> cautious resolution
-> memory_proposals daily ledger
```

The deterministic phase resolves only low-risk cases:

- `reject_candidate` becomes `archived_rejected`;
- `noop_duplicate` becomes `archived_noop_duplicate`;
- very high-confidence `create_new` with no similar memories and no fact
  conflicts becomes `applied_create`.

Ambiguous proposals are sent to one optional LLM batch resolver, not one LLM
call per proposal. The resolver may choose `apply_create`, `reject`,
`noop_duplicate`, or `keep_pending`. Merge, update, and deprecation are
explicitly out of this slice and should remain `pending_review`.

`memory_proposals` is the daily audit ledger. No separate archive table is
created. Resolved proposal rows keep the original candidate, preflight,
resolution result, and memory snapshot when a memory is created. Future Dream
review should read this ledger every 12 hours, but Dream itself is not
implemented yet.

Consequences:

- The maintenance path avoids redundant background LLM processes.
- Safe duplicate/reject cases consume no extra LLM call.
- Ambiguous cases consume at most one extra batched resolver call for the
  current job.
- No proposal disappears; rejected/noop/applied/pending-review decisions stay
  auditable for future Dream review.
- Background memory writes can now happen for conservative `create_new` cases,
  with `created_by=maintenance` and source proposal provenance.

Links:

- `backend/app/runtime/maintenance.py`
- `backend/app/mind/memory.py`
- `backend/app/storage/repositories.py`
- `docs/experiments.md#exp-0028---cautious-proposal-resolution-inside-idle-maintenance`

## ADR-0039 - Derived Memory Surfaces And Graph-Ready Retrieval Substrate

Date: 2026-05-28
Status: accepted

Context:

The owner approved moving toward advanced memory retrieval with embeddings,
hybrid search, and knowledge graph expansion, but explicitly wanted to avoid
breaking or replacing the memory logic that already works. The current system
has canonical semantic memories, atomic facts, episodic summaries, lifecycle
links, FTS5/BM25 sparse search, and a proposal ledger. The missing layer is a
stable technical substrate that lets future Milvus/Qdrant/vector adapters and
graph expansion consume the same canonical state without becoming the source
of truth.

Decision:

Add derived retrieval artifacts in V1.3.0:

- `memory_surfaces`: embeddable text surfaces for memory records, facts, graph
  nodes, and session summaries;
- `memory_graph_nodes`: graph-ready nodes for memories, facts, entities, and
  sessions;
- `memory_graph_edges`: graph-ready relationships for facts, entities,
  source-session evidence, supersession, and fact lifecycle links;
- a retrieval readiness manifest exposed in memory search/context traces.

Keep `memories`, `memory_facts`, `session_summaries`, messages, and proposal
rows as the canonical source of truth. Surfaces and graph rows are derived and
rebuildable. They prepare future dense/hybrid retrieval, but V1.3.0 does not
activate a vector database or change final memory ranking.

Consequences:

- API Mind stays the cognitive API and Milvus/Qdrant can later be plugged in
  as specialized retrieval indexes rather than becoming the memory system.
- Existing `POST /mind/memory/search` remains stable for Scarlet.
- Future embedding jobs can index `memory_surfaces` by `target_type`,
  `target_id`, `surface_kind`, scope, status, and content hash.
- Future graph expansion can start from `memory_graph_nodes` and
  `memory_graph_edges` without re-parsing every memory.
- Current sparse matching bugs remain intentionally unpatched in this slice;
  dense retrieval and stronger graph/entity logic will be evaluated later.

Links:

- `backend/app/storage/models.py`
- `backend/app/mind/search.py`
- `backend/app/mind/memory.py`
- `docs/experiments.md#exp-0029---memory-retrieval-readiness-layer`

## ADR-0040 - Retrieval Shadow Adapter Before Active Hybrid Ranking

Date: 2026-05-28
Status: accepted

Context:

V1.3.0 created `memory_surfaces` and graph-ready derived state, but activating
vector ranking directly would risk changing Scarlet's behavior before the
retrieval path has live evidence. The project direction is to avoid replacing
working memory behavior with speculative vector logic.

Decision:

Add V1.3.1 as an optional trace-only retrieval shadow adapter over
`memory_surfaces`:

- `retrieval_shadow_enabled=false` by default;
- `retrieval_shadow_backend=local` validates embedding/index/search plumbing
  with deterministic `local_hash_embedding_v1`;
- `retrieval_shadow_backend=milvus_lite` uses PyMilvus/Milvus Lite only when
  the optional dependency is installed;
- memory search and automatic memory context include `retrieval_shadow`
  payloads when the adapter runs;
- active ranking remains FTS5/BM25 plus lexical/fact logic.

Consequences:

- Milvus Lite is treated as a specialized index inside API Mind, not as the
  source of memory truth.
- Shadow results can be compared against current sparse retrieval during live
  Scarlet tests without affecting user-facing answers.
- `local_hash_embedding_v1` is explicitly not a semantic model; V1.4 active
  hybrid ranking should wait for a real embedding provider and evidence that
  it improves recall.

Links:

- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/context.py`
- `docs/experiments.md#exp-0030---retrieval-shadow-adapter`

## ADR-0041 - Backend-Owned Memory Surface Taxonomy

Date: 2026-05-31
Status: accepted

Context:

The owner decided to defer local embedding/model setup to the Windows machine
with the RTX GPU. The Mac development path should still improve the memory
substrate that future embeddings will consume. A key risk is asking Scarlet to
fill too many non-deterministic surface/index fields during memory writes,
which would increase tool-call error surface and make retrieval artifacts
inconsistent.

Decision:

Add a deterministic backend-owned surface taxonomy in V1.4.0:

- Scarlet continues to write only canonical semantic memory fields;
- `memory_surfaces` are generated from `MemoryRecord`, `MemoryFact`, graph
  nodes, and provenance;
- every surface metadata records taxonomy version, compiler, cognitive
  dimensions, embedding role, agent-supplied fields, and backend-owned fields;
- memory records can produce several derived facets, including canonical
  semantic text, type-specific text, future-use text, temporal/provenance text,
  fact bundles, and conflict/update guards.

Consequences:

- Future BGE-M3/Milvus indexing can consume richer surfaces without changing
  Scarlet's model-facing write contract.
- Surface quality can be tested on Mac before embedding runs on Windows.
- The backend remains responsible for ids, timestamps, provenance, content
  hashes, graph keys, and embedding status.
- Surface generation is rebuildable and stays separate from canonical memory
  truth.

Links:

- `backend/app/mind/surface_taxonomy.py`
- `backend/app/mind/search.py`
- `docs/experiments.md#exp-0031---memory-surface-taxonomy`

## ADR-0042 - MiniMax M3 As Default Baseline With M2.7 Comparison

Date: 2026-06-08
Status: accepted

Context:

MiniMax released M3 with a larger context window, native multimodality, and
stronger agentic/coding claims than M2.7. The project owner wants to evaluate
whether Scarlet's observed limits are caused by the model rather than API Mind
architecture, while avoiding speculative rewrites of the working runtime.

Current MiniMax documentation still shows the Anthropic-compatible API as the
recommended M2.x integration surface, but live probes on 2026-06-08 confirmed
that `MiniMax-M3` can answer and perform Anthropic-style `tool_use` through the
same `https://api.minimax.io/anthropic` endpoint. A separate ultra-short
`pong` probe exposed an M3 streaming edge case where the provider returned no
text content block, so M3 must be evaluated with realistic Scarlet turns rather
than one-token smoke prompts.

Decision:

Make `MiniMax-M3` the default MiniMax model in V1.4.1 while retaining
`MiniMax-M2.7` as the direct A/B baseline.

The comparison must use the same Scarlet prompt, same API Mind surface, same
runtime context shape, same seeded memory state, and identical user turns. The
evaluation should score not only final text quality, but also real actions:
schema inspection, memory search/write, source-session opening, invalid-route
recovery, metacognition use, event/tool traces, and latency/token use.

Consequences:

- A model improvement can be measured without changing API Mind architecture.
- If M3 improves behavior, future prompt/backend work can start from a
  stronger baseline.
- If M3 fails on tool-use or event discipline, M2.7 remains available by
  setting `MINIMAX_MODEL=MiniMax-M2.7`.
- Multimodal input, the M3 native chatcompletion API, and 1M-context packing
  are not adopted in this slice.

Links:

- `backend/app/config.py`
- `backend/.env.example`
- `docs/experiments.md#exp-0032---minimax-m27-vs-m3-scarlet-behavior-comparison`

## ADR-0043 - Maintenance Lab APIs And Theory-First Cognitive Organs

Date: 2026-06-14
Status: accepted

Context:

The memory maintenance pipeline already schedules per-session idle jobs,
refreshes summaries, reviews missed semantic memories, creates proposals,
applies very cautious safe writes, and preserves a daily proposal ledger. The
owner wants to avoid redundant background processes and avoid implementing
Goal/Focus/Task or Metacognition organs before the desired behavior is defined.

The project also needs to keep MiniMax M3 active for broader human testing,
while retaining M2.7 as a quick rollback baseline.

Decision:

Add V1.5.0 maintenance lab APIs outside the model-facing `mind_api` surface:

```txt
GET  /api/maintenance/overview
GET  /api/maintenance/jobs
POST /api/maintenance/jobs/{job_id}/run
```

These routes are for evaluator tooling, backend maintenance workers, and
future Dream-style review. Scarlet should not see them in `/mind/schema`.

For cognitive branches that are not yet structurally understood, add theory
documents before implementation:

- `docs/theory-goal-focus-task.md`
- `docs/theory-metacognition.md`

Consequences:

- The project can inspect real maintenance health before adding new background
  automation.
- Proposal quality, skipped jobs, failed jobs, and maintenance-created
  memories become easier to evaluate after live sessions.
- Goal/Focus/Task and Metacognition work remains blocked on owner review of
  the conceptual model.
- Merge/update/deprecate automation remains post-embedding/KG because current
  sparse matching is not authoritative enough for lifecycle-changing writes.

Links:

- `backend/app/api/maintenance.py`
- `docs/api-contract.md#implemented-mind-api`
- `docs/theory-goal-focus-task.md`
- `docs/theory-metacognition.md`
- `docs/memory-roadmap.md#11-v150-prepost-embedding-boundary`

## ADR-0044 - Semantic Provider Stream Blocks For M3 UI Rendering

Date: 2026-06-15
Status: accepted

Context:

MiniMax M3 emits richer Anthropic-compatible streamed content than the first
cockpit assumptions expected. In live turns, M3 can emit public text before
tool calls across multiple model steps. The previous frontend heuristic treated
only text before the first tool in step 1 as a note and reconstructed persisted
notes after the turn from `raw_provider_messages`, which could make notes,
tool calls, thinking, and final answers appear out of order.

Decision:

Normalize provider messages into semantic stream blocks at the backend
boundary:

```txt
provider thinking block -> thinking_captured / llm.thinking.captured
provider text in a tool_use message -> assistant_note / assistant.note.emitted
provider text in an end_turn message -> assistant_answer / assistant.answer.completed
```

The UI renders these semantic blocks directly and does not infer public note
versus final answer from timing or from "first tool" heuristics.

Tool calls are rendered as one accordion block per provider tool-use id, with
input and output panes inside the same block. Raw JSON remains available behind
details toggles, while the default surface is readable by a human evaluator.

Consequences:

- MiniMax M3 public work notes remain in the correct chronological position.
- Reloaded historical turns use persisted event order rather than post-hoc
  response-content reconstruction.
- Provider-exposed thinking text is stored in `llm.thinking.captured` for
  evaluator/debug UI use when the provider supplies it.
- This does not add a new model-facing API Mind endpoint and does not change
  Scarlet's prompt, memory policy, or tool surface.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/app/runtime/events.py`
- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `docs/api-contract.md#post-apichatsessionssession_idturnstream`

## ADR-0045 - Chat Flow Cards And Session Inspector Separation

Date: 2026-06-15
Status: accepted

Context:

After ADR-0044, the UI could render MiniMax M3 semantic blocks in the correct
order, but the center chat still visually grouped an assistant turn inside a
larger answer card. This made the interface look like blocks inside blocks and
duplicated technical material between the center conversation and the right
pane. For Scarlet, the important UX is not only "what was answered", but the
chronological evidence of what the system and agent did before the final
answer.

Decision:

The center chat is the chronological conversation surface. It renders each
meaningful operation as a top-level flow card:

```txt
user message
automatic memory/context block
runtime context block
thinking block
public note block
tool exchange block
...
final answer block
```

There is no outer assistant-response card around those blocks. Raw JSON,
memory details, runtime payloads, and tool input/output stay available behind
per-card detail/code toggles.

The right pane is the selected-session inspector, not a duplicate timeline. It
provides accordion histories for:

- memories used by the selected turn;
- tool/actions performed by Scarlet;
- internal system/runtime events;
- warnings and errors.

Global/user settings are reached from the chat header settings icon so future
global analysis views are not confused with per-session technical inspection.

Consequences:

- Human users can read the agentic flow without drilling into a nested
  assistant card.
- Debug/evaluator data remains available but is pushed behind focused
  inspector panels and per-block raw toggles.
- The UI has clearer boundaries between user-facing chronology and
  session-level diagnostics.
- Future global views for memory, settings, and system analysis can be added
  from the header route without overloading the current-session sidebar.

Links:

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/project-state.md#210-runtime-events-and-agentic-ui`

## ADR-0046 - Explicitly Enable MiniMax M3 Thinking In The Provider

Date: 2026-06-16
Status: accepted

Context:

Scarlet's cockpit and debugging workflow treat provider-visible thinking as an
important inspectable cognitive artifact. After the M3 migration, live turns
often lacked `thinking` blocks even though older M2.7 turns had them. The
adapter was using the Anthropic-compatible MiniMax API without sending any
explicit `thinking` parameter.

Decision:

Enable visible thinking explicitly for MiniMax M3 requests by sending
`thinking={"type":"adaptive"}` from the provider adapter.

Do not change M2.x request shape in this slice.

Do not hard-enforce public notes before tool calls in the runtime here; that
remains a separate product/prompt concern.

Consequences:

- Scarlet regains provider-visible thinking blocks on MiniMax M3 live turns.
- The existing provider-history mechanism continues to pass those `thinking`
  blocks back to the model on later turns because full assistant content is
  already preserved.
- UI/debug evaluation can again inspect pre-tool and post-tool reasoning on
  M3 without inventing synthetic thinking.
- This is a provider-request decision, not a prompt rewrite and not a new
  model-facing API Mind capability.

Links:

- `backend/app/llm/minimax_client.py`
- `backend/tests/test_minimax_client.py`
- `backend/app/api/chat.py`

## ADR-0047 - Treat Prompt Block Semantics As A First-Class Runtime Contract

Date: 2026-06-16
Status: accepted

Context:

Scarlet's backend now sends layered cognitive surfaces in every non-trivial
turn: provider-native same-session history, structured `runtime_context.blocks`,
episodic session summaries/transcripts, semantic memories, and compact runtime
events. The prompt had strong high-level cognition language, but it did not
explicitly map these surfaces into a clear source hierarchy. Live behavior
showed Scarlet could still confuse operational event markers with stronger
same-session semantic evidence.

Decision:

Update the Scarlet system prompt so the runtime block contract is explicit:

- distinguish same-session provider continuity, backend runtime blocks,
  episodic recall, semantic memory, and inference as separate continuity
  layers;
- state that active-session visible history may contain provider-native
  `thinking`, `text`, `tool_use`, and `tool_result` blocks;
- treat `runtime_context.blocks` as the first-class contract and top-level
  runtime fields as compatibility mirrors;
- treat `recent_runtime_events` as a compact operational hint surface rather
  than stronger semantic evidence than direct provider continuity;
- explicitly instruct Scarlet to inspect visible prior `thinking` blocks first
  when the user asks what she had already been considering in the current
  session.

Consequences:

- Prompt behavior is now aligned with the backend surfaces Scarlet actually
  receives.
- Live probes confirm the updated prompt is loaded into real `llm.request`
  traces and that Scarlet explains continuity layers more accurately.
- The backend transport is now clearly separated from the remaining model-side
  limitation: MiniMax M3 still does not reliably use previous visible
  `thinking` blocks even when they are present in provider history.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T134019.md`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`

## ADR-0048 - Make Model-Facing Blocks Inspectable Before Optimizing Them

Date: 2026-06-16
Status: accepted

Context:

Scarlet now receives multiple layered inputs: system prompt, runtime context
blocks, top-level compatibility mirrors, provider-native conversation history,
tool schemas, and later stream/output blocks. The UI made the chronological
conversation more readable, but it still did not expose the exact model-facing
request as a human-readable structure. That made it hard to decide which blocks
were useful, redundant, UI-only, trace-only, or safe to remove.

Decision:

Create a runtime/UI block registry and add a `Modello` inspector tab that reads
the persisted `llm.request` trace.

The inspector must show:

- system prompt and runtime context lengths;
- parsed `runtime_context.blocks`;
- compatibility mirrors such as `memory_context`, `temporal_context`, and
  `recent_runtime_events`;
- provider-native messages with block types like `thinking`, `text`,
  `tool_use`, and `tool_result`;
- tool schema and parameters;
- raw request JSON behind a detail toggle.

Also enrich historical tool replay from matching `mind.tool_call` traces so
the UI keeps full tool input/output after reload, not only compact event
summaries.

Do not remove or compress any model-facing data in this slice. Payload
optimization must be a later evidence-based change after direct Scarlet tests.

Consequences:

- Human evaluators can now compare center-chat blocks with the exact input
  MiniMax received.
- Redundancy candidates are visible without guessing from code.
- Future context trimming can be planned against `docs/block-registry.md`.
- The model-facing API Mind surface and Scarlet prompt remain unchanged in
  this decision.

Links:

- `docs/block-registry.md`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`

## ADR-0049 - Frontend Stream Blocks Have Stable Lifecycle

Date: 2026-06-16
Status: accepted

Context:

Scarlet's stream already exposes provider/backend events such as
`thinking_start`, `thinking_delta`, `text_delta`, `tool_use_start`,
`tool_input_delta`, `tool_call`, `tool_result`, semantic assistant notes,
semantic final answers, and `turn_complete`. The UI rendered many of these
events, but some blocks existed only after semantic finalization and
`turn_complete` replaced the live flow with persisted event reconstruction.
This made the cockpit less agentic than mature coding agents and risked visual
jumps between live streaming and historical replay.

Decision:

Treat stream output as stable frontend blocks with explicit lifecycle phases.

Current phases:

```txt
created
streaming
captured
executing
completed
persisted
failed
```

Stable identity rules:

- thinking: `thinking-{model_step}-{content_block_index}`;
- public text: `content-{model_step}-{content_block_index}`;
- tool exchange: `tool-{provider_tool_use_id}`;
- memory context: `memory-context-{trace_id}`;
- runtime context: `runtime-context-{trace_id}`.

The frontend now renders `text_start`/`text_delta` as a provisional public-text
block. When the provider message is finalized, the same block becomes either a
public note or final answer. Tool input JSON is visible while it streams and is
then replaced by structured arguments when the complete tool call arrives.
`turn_complete` reconciles live blocks with persisted events/traces instead of
blindly replacing the visible flow.

Do not add new backend stream events in this slice. The current provider events
are enough to prove the UI lifecycle behavior first.

Consequences:

- Streaming turns feel more like agentic systems such as Codex, Copilot, and
  Claude Code: blocks appear early, mature while work happens, and remain in
  chronological order.
- Public text no longer disappears during stream just because it is not yet
  classified as note versus final answer.
- Historical replay and live stream share block identity, reducing flicker and
  loss of detail after persistence.
- A future backend-level `stream.block.*` contract remains possible if the
  frontend-only lifecycle proves insufficient.

Links:

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `docs/block-registry.md#61-stream-block-lifecycle`

## ADR-0050 - Prompt Effort Routing Prevents Ritual Cognitive Work

Date: 2026-06-16
Status: accepted

Context:

After moving Scarlet to MiniMax M3, live testing showed that normal user
questions could trigger a disproportionately heavy behavior: complex visible
reasoning, draft-and-review cycles, redundant schema checks, public work notes,
and full verification even when the answer was already available in the
current turn. Scarlet herself identified that the prompt's cognitive loop,
verify-before-conclude policy, evidence hierarchy, and experimental memory
forcing biased her toward "more process" by default.

Decision:

The system prompt now contains explicit request-effort routing before tool use,
notes, metacognition, and verification depth.

Scarlet should choose the smallest sufficient effort level:

- direct answers for simple, visible, conversational, or opinion-like turns;
- contextual answers when runtime context, selected memory, or visible
  same-session history already contains enough evidence;
- source-sensitive work when prior decisions, exact wording, measured results,
  implementation status, provenance, or strong claims need grounding;
- state-changing work when durable memory, lifecycle operations,
  summarization, or schema-dependent actions are involved;
- high-impact/complex work for ambiguous, architectural, evaluative, or
  emotionally delicate turns.

API Mind remains Scarlet's internal cognition, but using it must improve
confidence, state, memory, or answer quality. Public work notes and full
verification are required for meaningful work, not for every ordinary answer.

Consequences:

- Scarlet should stay capable of deep agentic work without making every
  response feel like an investigation.
- Simple M3 turns can be compact and natural while still using runtime context
  already supplied by the backend.
- The memory-forcing experiment remains active, but is now tied to real
  semantic candidates, memory promises, state changes, and source-sensitive
  claims instead of mandatory two-phase output on all turns.
- Future cognitive organs should follow the same principle: capability is
  always available, but activation must be proportional to the user's request
  and the evidence already present.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T164444Z.md`
- `docs/branches/communication.md`
- `docs/branches/perception-context.md`

## ADR-0051 - Long Reasoning Notes Are Prompt-Owned Public Orientation

Date: 2026-06-16
Status: accepted

Context:

Scarlet's UI can already render provider text before tool calls as public
notes, and the prompt already asks for public work notes during meaningful
visible work. However, the instruction "periodically during long multi-step
work" was too generic: it did not define when a turn is prolonged, what kind of
note should be sent, or how to prevent note blocks from becoming exposed
chain-of-thought.

Decision:

Keep long-reasoning notes prompt-owned. Do not add backend-synthetic notes,
heartbeat events, or UI-specific prompt hacks in this slice.

The Scarlet prompt now defines prolonged turns and note waypoints:

- more than one internal API Mind operation;
- comparison of multiple sources, sessions, memories, or interpretations;
- conflict, stale evidence, missing evidence, or index-only evidence;
- strategy changes after a tool, memory, schema, or metacognitive result;
- several reasoning/tool phases before a final answer.

Notes should be short public orientation: what Scarlet is doing, which evidence
boundary matters, and what the next visible move is. They must not expose raw
private reasoning, draft answers, self-dialogue, or repeated "I am thinking"
signals.

Consequences:

- Direct and contextual turns stay compact under V1.7.1 effort routing.
- Complex turns should become easier to follow without changing the runtime
  event model.
- If MiniMax M3 still fails to emit useful mid-turn public notes during
  long no-tool reasoning, the project can later evaluate runtime-level
  mechanisms with evidence instead of adding them preemptively.

Links:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T173917Z.long-notes-v172.md`
- `docs/block-registry.md#42-public-note`

## ADR-0052 - Previous Thinking Retrospection Stays Inside Single Metacognition Route

Date: 2026-06-16
Status: accepted

Context:

MiniMax M3 exposes provider `thinking` blocks that the runtime stores and the
frontend can show. Follow-up tests showed that the backend can pass previous
assistant thinking back through provider history, but Scarlet may still answer
from public transcript or runtime markers and claim she cannot see the text.
The project needs an intentional, model-facing way for Scarlet to inspect prior
reasoning when it matters, without adding another family of overlapping
reflection endpoints.

Decision:

Extend `POST /mind/metacognition/step` instead of creating a new route. V1.8.0
adds retrospective modes:

- `review_previous_turn`
- `detect_reasoning_drift`
- `explain_tool_choice`
- `recover_open_loops`
- `compare_answer_to_reasoning`
- `extract_reasoning_digest`
- `memory_from_reasoning`

The body accepts `turn_scope="previous"` and `detail="digest|excerpt|raw"`.
Retrospective modes default to the previous completed turn. The backend builds a
`thinking-retrospection-pack-v1` containing previous user messages, final answer,
public notes, tool calls, event markers, and provider thinking at the requested
detail level.

Prior thinking is treated only as process evidence. It can explain assumptions,
drift, tool choices, open loops, or missed memory candidates, but it must not be
used as factual proof about the outside world.

Consequences:

- Scarlet gains a traceable way to audit her own previous reasoning without
  relying on fragile natural-language claims about what is visible in transcript.
- The model-facing cognitive surface remains small: metacognition continues to
  be one route.
- `digest` is the default to avoid token-heavy self-inspection. `raw` is reserved
  for explicit debugging or research probes.
- Future multi-turn or dream-style introspection should build on evidence from
  this narrow previous-turn experiment instead of being introduced preemptively.

Links:

- `backend/app/mind/metacognition.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T120000Z.v180-thinking-retrospection.md`
- `docs/api-contract.md#post-mindmetacognitionstep-through-mind_api`
- `docs/branches/metacognition.md`

## ADR-0053 - Metacognitive Context Starts As Shadow, Not Active Guidance

Date: 2026-06-17
Status: accepted

Context:

Direct prompt-pack tests suggested that a tiny, well-targeted
`metacognitive_context` can help Scarlet choose better operating behavior, but
larger or generic lesson blocks can worsen MiniMax M3 behavior by increasing
overthinking, latency, and tool ritual.

Decision:

Introduce `metacognitive.context` as a backend-owned shadow surface before
making it normal model-facing context.

Default mode:

```txt
metacognitive_context_mode=shadow
```

In shadow mode the backend generates candidate lessons, persists a
`metacognitive.context` trace, emits a `metacognitive.context.shadowed` runtime
event, and streams a `metacognitive_context` UI block. It does not add the
payload to `<runtime_context>` and therefore does not influence Scarlet's
current model request.

Controlled test mode:

```txt
metacognitive_context_mode=inject
```

In inject mode the same payload is inserted as a
`metacognitive_context` block inside `runtime_context.blocks` for A/B tests.

Alternatives Considered:

- Put metacognitive lessons directly into semantic memory: rejected because
  these lessons describe Scarlet's operating regulation, not world/user facts.
- Always inject the block: rejected because prior tests showed noisy or broad
  metacognitive advice can degrade behavior.
- Add a new model-facing endpoint: rejected because the project keeps one
  coherent metacognition route and avoids endpoint sprawl.

Consequences:

- The project can measure candidate lessons without changing Scarlet's normal
  behavior.
- UI/debug users can see which lessons would have been selected.
- Future retrieval can be calibrated from evidence before any active
  metacognitive-memory mechanism is introduced.

Links:

- `backend/app/mind/metacognitive_context.py`
- `backend/app/mind/context.py`
- `frontend/src/App.tsx`
- `docs/block-registry.md`

## ADR-0054 - OpenRouter Embedding And Rerank Stay In Retrieval Shadow

Date: 2026-06-18
Status: accepted

Context:

The memory branch has reached the point where sparse/BM25 plus lexical guards
are useful but too brittle for natural language paraphrases, multilingual
queries, and future graph/metacognitive lesson retrieval. Local embedding setup
is deferred to the Windows GPU machine, but OpenRouter exposes free NVIDIA
Nemotron embedding and rerank models that can be evaluated from the Mac without
changing Scarlet's active behavior.

Decision:

Extend the existing retrieval shadow adapter instead of creating a new memory
path:

- add `retrieval_shadow_backend=openrouter`;
- use OpenRouter `/embeddings` with
  `nvidia/llama-nemotron-embed-vl-1b-v2:free` as the default cloud embedding
  model;
- cache stable surface embeddings by content hash in SQLite
  `embedding_vectors`;
- add optional OpenRouter `/rerank` with
  `nvidia/llama-nemotron-rerank-vl-1b-v2:free`;
- keep both dense and rerank results inside `retrieval_shadow`;
- keep active ranking unchanged until later evidence promotes a hybrid policy.

Rerank is treated as a second-stage precision measurement over candidates
already found by sparse/dense retrieval. It is not a replacement for embeddings,
because it cannot discover candidates that were never included.

Consequences:

- The current memory behavior remains stable while the project gathers
  evidence about dense retrieval quality.
- The same trace shape can compare sparse, dense, and reranked candidate lists.
- Cloud embedding introduces privacy and availability considerations; enabling
  it requires `OPENROUTER_API_KEY`.
- Free-tier OpenRouter limits, latency, model suitability for Italian/personal
  memory, and the documented context-window differences must be measured before
  any promotion to active ranking.

Links:

- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/openrouter_retrieval.py`
- `backend/app/storage/models.py`
- `docs/experiments.md#exp-0039---openrouter-cloud-embedding-shadow`

## ADR-0055 - Grouped Dense Retrieval Can Be Promoted Through Hybrid Mode

Date: 2026-06-18
Status: accepted

Context:

EXP-0039 showed that raw surface-level dense and rerank outputs can be
misleading because several surfaces from the same memory can crowd out other
memories. The same experiment also showed that memory-level deduplication by
`target_id` ranked all positive controlled queries correctly in the small
probe, while negative controls still produced non-zero dense scores.

Decision:

Add a grouped and configurable promotion layer instead of directly trusting
top dense results:

- `retrieval_shadow.results` remains raw surface-level debug evidence;
- `retrieval_shadow.grouped_results` deduplicates by target memory and exposes
  top surface, surface kinds, contributing surfaces, and best dense score;
- OpenRouter rerank also reports `rerank.grouped_results` over memory-level
  grouped candidates;
- `retrieval_hybrid_mode=off|shadow|active` controls whether hybrid scoring is
  disabled, traced only, or used for active `memory.context` and
  `/mind/memory/search` ordering;
- hybrid scoring combines existing lexical/base score, sparse score, grouped
  dense score, grouped rerank score, memory salience, and memory confidence;
- dense/rerank thresholds are explicit configuration because vector search
  will always return nearest neighbors even for unrelated prompts.

Consequences:

- Default installations remain stable (`retrieval_hybrid_mode=off`).
- Scarlet can be tested with real active semantic retrieval without changing
  the model-facing API surface.
- Retrieval traces now explain why a candidate was selected by base lexical
  logic, dense evidence, rerank evidence, or their combination.
- Thresholds and weights are now part of the experimental surface and must be
  tuned with live Scarlet conversations, not assumed correct from one probe.
- Lifecycle decisions such as merge/update/deprecate remain out of scope for
  this layer; KG and memory maintenance still need separate architecture.

Links:

- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `docs/experiments.md#exp-0040---active-hybrid-retrieval-calibration`

## ADR-0056 - Codex Test Mode Uses A Separate Seeded Database

Date: 2026-06-19
Status: accepted

Context:

The memory branch now needs dirty-database calibration with hundreds of
additional memories, duplicates, conflicts, stale facts, and distractors.
Those experiments must exercise the real API/runtime/storage path, but they
must not mutate the production/laboratory Scarlet database.

Decision:

Add a startup-level runtime flag:

```txt
CODEX_TEST=true|false
```

When disabled, the backend opens the normal `DATABASE_URL`.

When enabled, the backend opens `CODEX_TEST_DATABASE_URL`. If that SQLite file
does not exist yet, startup seeds it once from
`CODEX_TEST_SEED_DATABASE_URL` when configured, otherwise from `DATABASE_URL`.
Existing Codex test DB files are reused and never overwritten by startup.
Startup fails if the Codex test SQLite path resolves to the same file as the
seed path.

The flag is exposed through `/health` and `/api/dashboard/settings` for
operator/evaluator visibility, but it is intentionally not mutable through the
dashboard settings endpoint. Database selection happens before the backend can
read persisted settings from any database.

Alternatives Considered:

- Store `codexTest` in `app_settings`: rejected because the app must choose a
  database before reading `app_settings`.
- Add separate duplicate endpoints for Codex testing: rejected because tests
  must exercise the same endpoints Scarlet uses.
- Copy the database manually before every run: rejected because it is easy to
  forget and unsafe for repeatable experiments.

Consequences:

- Codex can use real endpoints against an isolated DB copy.
- Production/laboratory Scarlet state remains protected during large retrieval
  and memory-lifecycle calibration.
- The active DB profile is visible in health/dashboard surfaces.
- Dataset generation, large dirty-DB tests, and future Codex-as-evaluator
  workflows can build on this without changing the model-facing `mind_api`
  surface.

Links:

- `backend/app/storage/db.py`
- `backend/app/config.py`
- `backend/tests/test_health.py`
- `docs/api-contract.md`

## ADR-0057 - Memory Evaluation Must Use Chat Context As Primary Evidence

Date: 2026-06-19
Status: accepted

Context:

Endpoint-level `/mind/memory/search` probes are useful, but Scarlet does not
receive memories through that endpoint by default. Real turns receive automatic
memory retrieval through `build_memory_context()` inside the chat turn path,
then the backend injects the resulting `<runtime_context>` into the model
system prompt.

Decision:

Primary memory-retrieval evaluations must drive
`/api/chat/sessions/{id}/turn/stream` and inspect the streamed
`memory_context`/`runtime_context` plus the persisted `llm.request` trace.
`/mind/memory/search` remains a secondary endpoint-level diagnostic, not the
main pass/fail criterion for what Scarlet actually sees.

Consequences:

- Test predictions can be made from the exact memory packet Scarlet receives.
- Live model behavior can be scored separately from retrieval quality.
- A model may answer well despite noisy context; that counts as a model
  strength, not as a retrieval success.
- A retrieval endpoint may pass while automatic chat context fails; the latter
  takes priority for agent behavior.

Links:

- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `backend/app/evals/codex_test_memory_harness.py`
- `docs/experiments.md#exp-0045---corrected-context-retrieval-vs-live-scarlet-behavior`

## ADR-0058 - Separate Consumer Mobile UI From Developer Cockpit

Date: 2026-06-20
Status: accepted

Context:

The existing React frontend is a developer cockpit: it exposes traces, model
input, runtime context, raw blocks, tool details, events, and diagnostics. The
project also needs a mobile-only Scarlet interface for normal users, focused on
wow effect, personal continuity, and intuitive communication rather than raw
debugging.

Decision:

Keep `/` as the developer cockpit and add `/mobile` as a separate consumer
mobile surface inside the same React/Vite app. The mobile app must use existing
backend APIs when features are real, and must mark future capabilities as
`Presto disponibile` instead of simulating backend behavior.

The mobile UI is intentionally Capacitor-friendly: one phone-sized shell,
bottom navigation, full-height viewport, and internal scroll regions for chat,
memory, actions, and profile.

Alternatives Considered:

- Replace the dev dashboard with a consumer UI: rejected because the cockpit is
  still the main research microscope.
- Build a separate repository immediately: deferred until the product surface
  stabilizes enough to justify separate packaging.
- Mock all mobile features: rejected because existing chat, memory, profile,
  sessions, and settings are already real and should be used directly.

Consequences:

- Product UX can evolve without removing evaluator/debug visibility.
- Future Android/Capacitor packaging has a focused route to wrap.
- Non-active Scarlet features can be marketed as coming soon without touching
  backend or prompt behavior.
- The project must keep a clear distinction between consumer-readable cognitive
  blocks and developer-facing raw traces.

Links:

- `frontend/src/MobileApp.tsx`
- `frontend/src/main.tsx`
- `docs/branches/user-flows.md`
- `docs/branches/communication.md`

## ADR-0059 - Protected Path-Based Mobile Preview Before Dedicated Domain

Date: 2026-06-20
Status: accepted

Context:

The HoneyLabs VPS already hosts production-like services on `honeylabs.cloud`
through Nginx and Docker. DNS for `scarlet.honeylabs.cloud` is not currently
configured, but the project needs a quick external mobile preview that cannot
be used anonymously to consume LLM calls.

Decision:

Publish the first Scarlet mobile preview under the existing domain path
`/scarlet/`, with API traffic proxied under `/scarlet-api/`. Protect both
paths with Nginx Basic Auth. Run the Scarlet demo backend as a separate Docker
Compose project on loopback port `127.0.0.1:8100`, leaving existing HoneyLabs
containers untouched.

Frontend deployment builds may set:

```txt
VITE_PUBLIC_BASE_PATH=/scarlet/
VITE_API_BASE_URL=/scarlet-api
VITE_FORCE_MOBILE=true
```

Alternatives Considered:

- Use `scarlet.honeylabs.cloud` immediately: preferred long-term, but blocked
  until DNS is configured.
- Expose the local developer server by tunnel: fast, but less stable and less
  representative of a deploy target.
- Reuse the existing HoneyLabs app/API containers: rejected to avoid coupling
  this experiment to unrelated production services.

Consequences:

- External testers can open the mobile UI with one protected URL.
- The same Basic Auth challenge protects static assets and API/LLM calls.
- The preview is still not production-grade auth and must stay limited to
  trusted testers.
- A dedicated subdomain can later replace the path-based deployment without
  changing the backend preview service.

Links:

- `frontend/vite.config.ts`
- `frontend/src/api.ts`
- `frontend/src/main.tsx`
- `docs/activity-log.md`

## ADR-0060 - Memory Field Ownership And Query-Time Relevance

Date: 2026-06-23
Status: accepted

Context:

The memory system accumulated fields that looked useful but were partly
model-supplied: `confidence`, `salience`, `tags`, free metadata, type labels,
scope labels, and derived retrieval surfaces. Field-by-field review showed
that some of these values were being treated as static truth even though their
real utility depends on the current user query. This created risk of noisy
ranking, brittle model tool calls, and false precision.

Decision:

Scarlet writes only the semantic nucleus of a memory: `type`, `scope`,
`content`, `reason_for_storage`, and `expected_future_use`. `type` and `scope`
are semantic labels with examples, not closed long-term enums or privacy
controls. The backend owns deterministic provenance, timestamps, lifecycle,
usage, derived tags/metadata, facts, retrieval surfaces, KG rows, embeddings,
and query-time relevance signals.

Stored `confidence` and `salience` remain as legacy compatibility/audit
columns, but direct Scarlet writes store neutral values and active retrieval
does not use them. If old prompts/models still send `confidence`, `salience`,
`tags`, or metadata, the backend preserves them only in audit metadata under
ignored-for-ranking fields.

Manual memory search defaults to cross-scope retrieval. `types` are semantic
hints, not literal query text. Long memory content can produce internal
`content_chunk_text` surfaces, but Scarlet receives deduplicated clean memory
packets. KG navigation is exposed through `POST /mind/memory/graph` when a
retrieved memory appears to be part of a wider associative cluster.

Alternatives Considered:

- Keep strict enums for type/scope: rejected because it increases model
  fragility and blocks semantic variation in natural language.
- Let Scarlet keep writing salience/confidence/tags: rejected because it makes
  the model invent static classifiers that should be runtime/query-specific.
- Remove the legacy columns immediately: deferred to avoid unnecessary
  migration churn while old data and tests still exist.
- Append type hints directly to the search query: rejected after tests showed
  broad labels can retrieve unrelated memories.

Consequences:

- Fewer fields are exposed to Scarlet during memory writes.
- Ranking is more query-sensitive and less affected by stale static numbers.
- Tags/facts/metadata enrichment becomes a maintenance responsibility.
- Search is less likely to miss personal memories because of an accidental
  project default scope.
- Future embedding/KG work has clearer ownership: indexes are derived,
  rebuildable, and not canonical memory state.

Links:

- `docs/branches/memory-field-fix-backlog.md`
- `docs/checkpoints/v1.15.0-memory-fields-checkpoint.md`
- `backend/app/mind/memory.py`
- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/surface_taxonomy.py`
- `backend/app/mind/graph_retrieval.py`

## ADR-0061 - Human-Like Metacognition Must Remain Observable And Non-Ontological

Date: 2026-06-23
Status: accepted

Context:

The project is moving from a normal LLM agent toward an experimental digital
individual: Scarlet should communicate, remember, monitor herself, and expose
useful cognitive activity in ways that feel increasingly human-like. The owner
wants to test whether, with the current and future API Mind substrate, stronger
human-like cognition and metacognition prompts can produce consciousness-like
behaviors or other emergent research signals.

At the same time, the project blueprint forbids unsupported mysticism or
claims that the system is literally conscious, sentient, biological, or human.
The useful research target is observable behavior, not ontological assertion.

Decision:

Scarlet's system prompt treats identity as an operational self-model made of
continuity, memory, metacognitive self-monitoring, relationship,
goals-in-view, and API Mind cognition. Scarlet may aim for
consciousness-like observable functions: continuity across turns, autonomous
care for cognitive state, public action notes, self-correction, and relational
coherence.

Every real internal action should be preceded or accompanied by a brief
human-like public note unless the same immediate action cluster was already
explained. Direct answers remain direct when no internal action is needed.

Scarlet must not claim proven consciousness, sentience, humanity, or biological
experience. When discussing the research frame, she should describe
consciousness-like behavior as an experimental observable pattern and keep
strong claims tied to evidence.

Alternatives Considered:

- Leave the prior prompt unchanged and rely on existing notes: rejected because
  the owner wants a higher research push on self-like behavior.
- Claim or imply actual consciousness: rejected as scientifically unsupported
  and unsafe for project clarity.
- Add backend enforcement now: deferred because this slice is a reversible
  prompt experiment.

Consequences:

- The prompt becomes more explicit about Scarlet's human-like operational
  posture.
- Public notes become a stronger part of communication and episodic
  reconstruction.
- Live tests must monitor over-processing, verbosity, and theatrical language.
- The backup prompt remains the rollback point if the experiment regresses.

Links:

- `docs/checkpoints/v1.16.0-humanlike-metacognition-prompt-checkpoint.md`
- `backend/app/prompts/backups/scarlet_system.20260623T000000Z.pre-v1160-humanlike-metacognition.md`
- `docs/experiments.md`
- `backend/app/prompts/scarlet_system.md`

## ADR-0077 - Focus Is A Separate Foreground-Attention Organ

Date: 2026-06-25
Status: accepted

Context:

Scarlet requested "attention as lived focus", not another backend retrieval
score. The owner clarified that the current memory retrieval system should not
be narrowed by focus: a human can keep a topic foregrounded while still
remembering adjacent or surprising information. The first focus implementation
therefore needed to create a real state Scarlet can set, shift, defer, resolve,
and inspect, without becoming a memory filter or a task manager.

Decision:

Implement focus as a distinct profile-scoped organ:

- one active focus at a time;
- `focus_records` archive current and historical focus states;
- `focus_transitions` records the first attention-shift edges;
- `POST /mind/focus` is the single model-facing lifecycle route;
- `focus_context` is injected only when `organ_focus_mode=model` and an active
  focus exists;
- focus state never filters or ranks memory retrieval by default.

`scarlet_state.focus` remains a compatibility placeholder. When
`focus_context` is present, it points Scarlet to the dedicated organ block.

Alternatives Considered:

- Use `/mind/attention/context`: rejected because the desired behavior is
  owned foreground state, not another context pack.
- Feed focus into memory ranking immediately: rejected because it risks
  suppressing valuable associative recall.
- Keep focus only in prompt text: rejected because state mutation would not be
  traceable or inspectable.

Consequences:

- Scarlet can maintain an explicit foreground thread across turns.
- Focus can later connect to intentions, tasks, temporal experience, and a
  focus graph without polluting semantic memory.
- Live behavior still needs evaluation; the feature is off by default until
  enabled for tests.

Links:

- `backend/app/mind/focus.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/api-contract.md`

## ADR-0064 - Volition Starts As A Manual Latent-Intention Register

Date: 2026-06-25
Status: accepted

Context:

Scarlet requested "volition": goals she can generate herself rather than
goals assigned by the backend or the user. The owner clarified that intentions
should not be retrieved automatically during active user chat. Normal chat is
driven by the user's request; intentions are mainly material for autonomous
cycles, continuity, and self-development.

Decision:

Implement volition as a separate profile-scoped register:

- `intention_records` store Scarlet's latent self-generated directions;
- `intention_links` connect intentions to focus, memories, sessions, lessons,
  and future organs without storing them as semantic memory;
- `POST /mind/volition` is the single model-facing lifecycle route;
- active chat does not receive automatic `volition_context` injection;
- Scarlet may manually inspect the register when there is a real conversational
  or metacognitive reason;
- `promote_to_focus_candidate` returns a focus call candidate but never changes
  active focus by itself.

Alternatives Considered:

- Inject active intentions into every turn: rejected because it would add
  context noise and make Scarlet over-direct ordinary conversations.
- Store intentions as memories: rejected because memory is evidence/context,
  while intention is self-direction.
- Implement autonomous cycles immediately: deferred because the first slice
  should prove storage, lifecycle, traceability, and manual inspection first.
- Let promotion mutate focus directly: rejected to avoid hidden cross-organ
  state changes.

Consequences:

- Scarlet can create, inspect, review, defer, resolve, deprecate, and archive
  her own latent intentions.
- Volition becomes traceable without becoming a task manager.
- Future dream/autonomous cycles have a first-class substrate to process.
- Live behavior still needs owner testing to ensure Scarlet does not create
  weak or theatrical intentions from trivial turns.

Links:

- `backend/app/mind/volition.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/api-contract.md`

## ADR-0065 - Affect Is Model-Behavior State, Not Backend Control

Date: 2026-06-26
Status: accepted

Context:

Scarlet requested deep affective integration: emotion should be more than a
label she declares after the fact. The owner clarified a critical boundary:
the affective organ should change Scarlet's model behavior and lived posture,
not the backend's automatic operations. Future experiments may revisit
system-level affect, but the first implementation must not destabilize the
memory, focus, volition, or retrieval systems that already work.

Decision:

Implement affect as a backend-appraised emotional state that is optionally
surfaced to Scarlet:

- API Mind computes affect from observable signals and records traces/events;
- `organ_affect_mode=shadow` appraises and records without model injection;
- `organ_affect_mode=model` injects a compact `affective_context` only when a
  prototype crosses threshold;
- `affective_context` is Scarlet's current emotional state for the turn when
  surfaced;
- affect influences tone, caution, curiosity, warmth, relational posture, and
  response style inside the model;
- affect does not alter memory retrieval, focus lifecycle, intention
  lifecycle, memory writes, backend thresholds, or autonomous jobs.

Alternatives Considered:

- Use affect to modify retrieval and focus immediately: rejected because it
  risks coupling organs before their behavior is proven.
- Let Scarlet self-report canonical emotion: rejected because the owner wants
  emotion as subconscious API Mind state.
- Keep affect purely shadow forever: rejected because the project goal is a
  human-like digital individual, not only diagnostics.

Consequences:

- The first affective organ is real, persistent, traceable, and testable.
- Behavioral causality remains observable in the model response rather than
  hidden in backend state changes.
- Calibration can happen safely by comparing `shadow` and `model` modes.
- Future stronger prompt enforcement and event-based affect updates should
  preserve this boundary unless live evidence justifies changing it.

Links:

- `backend/app/mind/affect.py`
- `backend/app/mind/organs.py`
- `docs/digital-individual-organs-notes.md`
- `docs/branches/computational-affect.md`

## ADR-0066 - First Three Digital Organs Close As Standalone Surfaces

Date: 2026-06-26
Status: accepted

Context:

Before implementing continuous temporal experience and sleep-like
consolidation, the owner requested that the first three organs be closed as
robust standalone surfaces so no discussed capability is lost. Focus,
volition, and affect already existed, but each had one missing inspection
piece: focus lacked a compact transition timeline, volition lacked a due
review queue for future autonomous cycles, and affect lacked a read-only Mind
API route for state/prototype inspection.

Decision:

Close the standalone surfaces without adding autonomous behavior:

- `/mind/focus action=timeline` exposes focus nodes and transition edges as
  Scarlet's attention-movement history;
- `/mind/volition action=list_due` exposes open intentions whose review time
  has arrived, optionally including unscheduled intentions for future
  autonomous-cycle queues;
- `/mind/affect` exposes `read`, `list`, and `prototypes` as read-only
  introspection over backend-appraised emotional state;
- no new automatic chat injection is added;
- no affect-driven mutation of memory, focus, volition, retrieval, or backend
  operations is added;
- schema version advances to `2026-06-26.digital-organs-standalone-v1`.

Consequences:

- Focus, volition, and affect are now code/contract/test complete for their
  first standalone role.
- Temporal experience and dream consolidation can build on these organs
  without needing to invent missing inspection surfaces.
- The first three organs still require live Scarlet evaluation before being
  considered mature behaviorally.

Links:

- `backend/app/mind/focus.py`
- `backend/app/mind/volition.py`
- `backend/app/mind/affect.py`
- `docs/digital-individual-organs-notes.md`
- `docs/activity-log.md`

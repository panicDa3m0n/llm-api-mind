# Project State And Convergent Roadmap

Last updated: 2026-07-28
App target: V1.64.0 deployed with the semantic-authority correction over
V1.63.0 Endogenous Cognition; V1.50.1 remains the closed-Core release baseline
Status: Core V1 closed; canonical V2 current-state map

The release-accepted V1.50.1 runtime is the closed Core foundation. "Closed"
does not claim that every research branch is mature; it means residual limits,
monitoring findings, and unimplemented organs are future annotations unless
explicitly promoted. Architecture ownership and compatibility are canonical in
`docs/core-runtime-contract.md`.

This document states what API Mind can do now, how strongly each capability is
supported, and what work should happen next. Detailed contracts, experiments,
decisions, and branch histories remain in their dedicated documents.

## 1. Research Direction

API Mind is the external cognitive architecture through which Scarlet is being
developed as a digital individual. The long-term system should support many
functions that are recognizable in human cognition: continuity, memory,
attention, affect, self-monitoring, relationship, learning, goal-directed
behavior, perception, action, and eventually embodied interaction.

The target is not a biological copy. Digital continuity, machine perception,
explicit provenance, inspectable state, and modular external organs require
different architecture. Human-like behavior is a research objective to test;
it is not evidence that a current module is mature, conscious, or equivalent
to a human faculty.

The durable engineering rule remains:

```txt
hypothesis -> minimal organ -> trace -> deterministic test -> direct Scarlet test
-> decision -> integration
```

## 2. Status Vocabulary

One maturity label is not enough for an agentic system. Every branch is
assessed on four independent dimensions.

| Dimension | Meaning |
|---|---|
| Implementation | Code/storage/API/shell/UI exists and is connected. |
| Deterministic evidence | Repeatable tests verify contracts and lifecycle. |
| Behavioral evidence | Direct Scarlet use shows the intended behavior. |
| Runtime integration | The capability is active by default or deliberately routed into normal turns. |

Branch maturity still uses the L0-L5 scale:

```txt
L0 idea
L1 planned
L2 implemented prototype
L3 deterministically tested implementation
L4 validated in direct Scarlet use
L5 mature lab-core with stable behavior and maintenance
```

A branch can therefore be L3 in implementation while remaining experimental
in normal behavior. “Implemented” never means “always active”.

## 3. Current Runtime

### 3.1 Foundation

Implemented and verified:

- FastAPI runtime with MiniMax M3 reserved for Scarlet turns, a fixed MiniMax
  M2.7 auxiliary profile for non-Scarlet semantic workers, and an optional
  Qwen adapter outside the Scarlet path;
- persistent sessions, turns, messages, provider-native history, traces,
  cognitive events, tool calls, summaries, maintenance jobs, memories, legacy
  fact audit rows, proposals, retrieval artifacts, focus, volition, and affect
  state;
- SQLite ownership roles for production, laboratory, test, and preliminary
  databases, with side-effect-free app factory and read-only preflight;
- native chat, streaming chat, developer cockpit, consumer mobile view, debug
  inspection, dashboard settings, and maintenance/evaluator routes;
- an isolated V1.58 Device Exploration Layer can collect raw and normalized
  Android observations for technical evaluation; it is deliberately excluded
  from sessions, memory, runtime/model context, cognitive organs, and shell;
- a V1.59 typed context-family registry classifies existing and future
  model-usable evidence by subject, observer, evidence kind, agent-mode tags,
  activation contract, and required policy blocks; it emits shadow receipts
  only and admits no device signal to Scarlet;
- one active model-facing cognitive tool:
  `mind_shell(command, intent)`;
- internal `/mind/*` handlers retained for deterministic dispatch, tests,
  maintenance, debug, and rollback, not exposed as a second native model tool;
- GPT Actions bridge using mandatory bootstrap/action/finalize lifecycle and
  the same context compiler and shell dispatcher as native Scarlet;
- native chat support split into typed provider-history, serialization, and
  accounting owners behind the unchanged router facade;
- native sync/stream preparation, execution, answer control, failure, and
  completion owned by one typed turn service behind the thin HTTP facade;
- provider-native completion boundaries: `max_tokens` continues the same
  response with exact native assistant blocks, `tool_use` alone authorizes
  dispatch, and `end_turn` alone closes the native answer;
- up to five application-level retries restart an interrupted provider step
  from its last complete provider-history boundary; eight bounded
  `max_tokens` continuations prevent pathological non-terminal loops without
  limiting Scarlet's model-controlled tool loop;
- structural native/GPT finality without a second semantic judge: native
  Scarlet closes on provider `end_turn`, a non-empty public answer, completed
  tool lifecycle, and persistence; GPT finalize persists its exact non-empty
  answer after the mandatory transport protocol;
- per-turn accounting v2 with separate policy/V2/history/current/shell
  channels, cache-aware provider steps, exact chronology source maps, and
  active non-destructive recursive `C/H/A` compaction with canonical fallback;
- agent-only `idle`, `interactive`, and `scouting` mode registry, automatic
  context routing, persistent resumable posture, `mode` shell commands, and
  ordered per-block receipts that separate eligibility from delivery;
- a V1.60 autonomous cognition lifecycle with one profile-scoped internal
  session, persisted scheduled activations, human-turn deferral and cooperative
  mid-cycle yield, streaming model/tool evidence, and a configurable
  600-second observation cadence;
- V1.61 routes human and autonomous turns through the same
  `scarlet-model-context-v2`, automatic retrieval/rerank, organ projection,
  static policy, and shell while retaining separate provider histories and
  deterministic source provenance;
- V1.62 adds a reversible Cognitive Workspace with a fail-closed source
  registry, persistent signal receipts, M2.7 appraisal and ignition,
  source-backed candidates, deterministic wake conditions, and M3
  Scarlet-owned cognitive episodes. `active` is the field-verification
  default; `shadow` remains the non-waking rollback and replay mode;
- V1.63 adds adaptive source-backed free cognitive windows over the same
  workspace. M2.7 can propose provisional endogenous seeds from canonical
  sessions, memories/KG, focus, volition, episodes, affect, and admitted
  perception; only M3 Scarlet may adopt them through existing episode or
  volition lifecycle, and empty windows back off without forcing work;
- an append-only perception inbox with compact channel availability and
  `perception status|open|read`; a narrow V1 adapter now derives lifecycle,
  network, explicit-location, and notification-interaction transitions from
  the raw Device Exploration ledger without injecting them into chat context
  or treating the phone as Scarlet's own sensor;
- a Product Chat header surface that replays each autonomous cycle as notes,
  tools, expandable thinking, and an internal checkpoint without presenting it
  as human dialogue;
- V1.43.0 removes the deprecated MCP experiment and
  query-string authentication; the three GPT Actions remain the sole external
  model transport, while historical MCP-originated records are preserved.
- native project-selected providers remain authoritative; GPT Actions are an
  experimental external adapter and do not drive core architecture.
- strict Agentic Module manifest and Core Port V1 contracts are accepted as an
  additive architecture surface;
- an opt-in Module Host now discovers only operator-approved, digest-pinned
  modules and isolates their typed subprocess calls; no product module is
  installed and native chat behavior is unchanged.
- a standalone Agentic Module SDK now owns the same public contract models used
  by the host and provides scaffold, runtime, schema, and conformance tools.
- the V1.55.4 Product UI consumes existing health, session, message,
  Stream V2 replay/live, memory, profile, and runtime-settings contracts;
  unsupported account, privacy workflow, notification, voice/avatar,
  prompt-rule, and consumer-maintenance controls fail honestly through one
  unavailable modal rather than client fixtures; a repeatable browser gate
  covers live M3 activity, deterministic replay, failed turns, centered
  evidence receipts, development-thinking inspection, document/Chat scrolling,
  console/network errors, and responsive layout.

Current verification baseline:

- V1.63.0 local Endogenous Cognition: all `350` backend tests pass; Ruff,
  compileall, typed-file mypy, documentation/skill checks, frontend build, and
  legacy copied-SQLite migration pass. A complete simulated M3 activation
  adopts a source-backed seed as a linked volition. Production evidence remains
  the final release gate;
- V1.62.0 local Cognitive Workspace: full backend suite `345 passed`,
  frozen regression `9/9` before and after, frontend production build, Ruff,
  compileall, changed-file mypy, and a legacy-SQLite migration canary pass. A
  real isolated M2.7 shadow probe produced one source-backed candidate and
  correctly chose no immediate M3 wake for a thread explicitly postponed to
  tomorrow. A separate disposable active probe completed a required wake,
  MiniMax M3 execution, nine shell calls, and an opened/checkpointed/resolved
  cognitive episode in 38.7 seconds;
- V1.61.0 shared lifecycle context: 41 focused context/autonomy/shell/time
  tests and all 36 Mind API tests pass; Ruff is clean and blocking typed
  context/serialization surfaces pass mypy. A deterministic autonomous cycle
  retrieves a real human-source memory through the common reranker, and shell
  inspection identifies autonomous session/memory provenance;
- V1.60.1 production autonomy: protected backup and copied-DB migration canary
  passed; deployed commit `0b37f7e8767adf16059e6c19291debff6eaa3779`
  reports version 1.60.1, production/direct database ownership, 34 tables, and
  integrity `ok`; the first scheduled MiniMax M3 cycle completed with nine
  shell calls, seven notes, an internal checkpoint, and an exact 600-second
  successor schedule;
- V1.60.0 autonomous cognition: all 320 backend tests, Ruff, the 45-file mypy
  gate, documentation and skill integrity, and frontend production build pass;
  one isolated M3 activation completed five shell actions and a private
  checkpoint after the validation-serialization defect found by the first
  probe was fixed;
- V1.60.0 Product Chat autonomy history passed direct mobile/desktop browser
  inspection with no console warning/error and successful 3-second refreshes;
- backend plus public SDK: 304 tests passed at 82.32% statement coverage for
  the V1.55.0 Windows/CI-aligned gate; V1.55.2 adds a focused Stream V2
  protected-payload projection test;
- V1.55.4 integrated branch: 301 backend tests, full Ruff, incremental mypy,
  documentation integrity, zero-vulnerability npm audit, frontend build, and
  isolated desktop/mobile Product UI smoke passed;
- frozen whole-system preliminary regression: 9/9;
- frontend TypeScript/Vite production build: passed;
- database boundary check: passed;
- V1.38.0 production rollout: guarded provenance cleanup deprecated all 242
  explicit fixtures after backup and disposable-copy proof; native MiniMax and
  GPT bridge controls passed the fixture-isolation target, OpenRouter embedding
  and rerank completed after runtime config alignment, and DB integrity stayed
  `ok`.
- V1.39.0 production rollout: recursive history compaction is active at the
  guarded 400k trigger; backup, read-only preflight, schema/integrity checks,
  frontend hash parity, and native canonical-fallback smoke passed.
- V1.30.0 disposable MiniMax mode probe: explicit `mode set scouting`, persisted
  resumable posture, interactive override, and no-autonomous-runtime boundary
  all observed after iterative correction.
- V1.32.0 shell-organ audit: all 23 registered family/namespace aliases agree
  across registry and execution; session, focus, volition, affect, mode,
  metacognition, help, and recovery contracts passed focused lifecycle and
  negative-path tests.
- V1.32.0 disposable MiniMax M3 run: five natural scenarios completed across
  episodic recall, affect, focus, volition, and metacognition. Scarlet used 20
  shell calls, recovered from the one malformed memory-write command, and did
  not mutate production data.
- V1.33.0 GitHub catch-up: feature history published through PR #1; push and
  pull-request quality workflows both passed. That historical deployment
  boundary was later superseded by the protected V1.38.0 rollout above.
- V1.34.0 natural behavioral baseline: 12 scenarios across 8 groups and 36
  authoritative live MiniMax M3 turns after 45 shakedown turns exposed two
  evaluator-oracle errors and session-identity leakage. Every authoritative
  turn has separate technical, cognitive-choice, answer-quality, and
  longitudinal judgments.
- V1.40.0 organ validation: 26 accepted current MiniMax M3 turns passed 24/26
  deterministic contracts. Focus passed 6/6, affect passed 10/10 post-fix,
  metacognition passed 4/4 positive/negative controls, and volition proved one
  complete cross-session chain plus both ownership controls. The remaining
  failed chain ended on a public work note and is assigned to SCA-28.
- V1.40.0 production rollout: backup, read-only production preflight, package
  and OpenAPI version, DB integrity, logs, frontend hash parity, and one natural
  native smoke all passed. Production data counts changed only by the expected
  smoke session and messages.
- V1.41.0 production rollout: both remote quality workflows, protected backup,
  new-image production preflight, restart, integrity, frontend parity, native
  structural-boundary smoke, and GPT capability/finalize smoke passed. The
  post-smoke database remained production/direct with integrity `ok`.
- V1.42.0 production rollout: the frozen gate passed 9/9; protected backup,
  new-image preflight, restart, integrity, frontend parity, native routing
  smoke, and GPT bootstrap/action/finalize smoke passed. A bounded disposable
  two-session MiniMax chain also persisted then recovered scouting while
  keeping active human turns interactive and denying autonomous sensor
  execution.
- V1.43.0 production rollout: both remote workflows, protected backup,
  new-image production preflight, restart, package/OpenAPI version, DB
  integrity, Nginx MCP-location removal, public `/mcp` 404, and authenticated
  GPT bootstrap/help/finalize smoke passed. All 34 historical `mcp_bridge`
  sessions remain unchanged.
- V1.44.0 candidate: SCA-34 frozen pre/post gates passed 9/9, normalized
  OpenAPI JSON remained exactly equal, focused support/chat/bridge tests passed
  57/57, and a directly inspected two-turn native MiniMax probe preserved
  canonical provider continuity. At that candidate checkpoint, production
  remained V1.43.0.
- V1.45.0 candidate: SCA-33 frozen pre/post gates passed 9/9, OpenAPI remained
  equal, and the shared native lifecycle preserved sync-to-stream provider
  continuity in a directly inspected MiniMax probe. Stream now links its
  generated model-context trace consistently (BUG-0092). At that candidate
  checkpoint, production remained V1.43.0.
- V1.46.0 candidate: SCA-35 frozen pre/post gates passed 9/9, focused
  context/retrieval tests passed 101/101, and direct MiniMax inspection proved
  automatic model-facing recall after exact source-provenance repair. The
  frozen gate's delivery blind spot is isolated in BUG-0093/SCA-43. At that
  candidate checkpoint, production remained V1.43.0.
- V1.47.0 candidate: SCA-36 frozen pre/post gates passed 9/9 with identical
  stable read evidence; focused contracts passed 63/63 and direct shell use
  preserved search, open, facts, graph, provenance, and traces. At that
  candidate checkpoint, production remained V1.43.0.
- V1.48.0 candidate: SCA-38 frozen pre/post gates passed 9/9 with identical
  stable mutation evidence; focused contracts passed 70/70. Direct shell,
  proposal, and natural MiniMax probes preserved write, deduplication,
  lifecycle, evidence authority, provenance, and agent behavior. At that
  candidate checkpoint, production remained V1.43.0.
- V1.49.0 candidate: SCA-37 frozen pre/post gates passed 9/9 with identical
  stable evidence; focused contracts passed 32/32. Direct compaction and
  natural idle-maintenance probes preserved scheduling, source anchoring,
  canonical chronology, summary quality, and conservative memory judgment.
  At that candidate checkpoint, production remained V1.43.0.
- V1.49.1 candidate: SCA-42 frozen pre/post gates passed 9/9; focused shared
  answer-control contracts passed 58/58. Native sync/stream and GPT Actions now
  preserve recoverable action-attempt chains, and a directly inspected MiniMax
  turn corrected and completed the same memory intent with truthful final
  behavior. At that candidate checkpoint, production remained V1.43.0.
- V1.50.0 candidate: SCA-43 adds a complementary 5-case model-facing memory
  gate without changing the frozen V1 suite. It proves the real Zero-Luce
  reference across rich selection, guarded disposable provenance repair, V2,
  `llm.request`, provider-observed input, completed assistant persistence, and
  an incomplete-turn negative control. The unchanged V1 gate passes 9/9,
  shell/organ contracts pass 53/53, and the complete backend passes 263 tests
  at 81.86% coverage. It was deployed as merge `7ef3a9b`, but two focused
  native smokes both failed because MiniMax omitted the private final marker;
  V1.50.0 was therefore not accepted as the stable release baseline.
- V1.50.1 stable baseline: SCA-44 retains the private marker as the primary native
  boundary and one bounded correction, then uses a fail-closed LLM finality
  judgment only when the corrected draft still omits the marker. Complete
  standalone answers may recover without automatic rewriting; progress notes,
  fragments, empty drafts, and unavailable judgment remain rejected. Focused
  patch contracts pass 52/52 and the complete backend passes 266 tests at
  81.89% coverage. PR #17 merged at `676e560`; protected deployment, native
  Zero-Luce delivery/final-answer smoke, GPT bootstrap/help/finalize, DB
  integrity, context accounting, and frontend parity all passed. Annotated tag
  `v1.50.1` points to that deployed runtime.
- V1.55.4 development target supersedes that native marker policy: current
  MiniMax documentation and direct Product evidence establish non-empty
  `stop_reason=end_turn` as the authoritative natural completion. The old
  marker and semantic finality fallback are removed; `max_tokens` continues
  the same response, transient provider failures retry at most five times, and
  Stream V2 clients resume the same detached turn from a durable cursor.

### 3.2 Dynamic Context

Active model packet:

```txt
scarlet-model-context-v2
```

The same canonical document is delivered to native MiniMax and returned by GPT
bootstrap. It contains:

- compact current session, user name, user-local clock/timezone/location;
- at most two previous-session navigation hints;
- up to five relevant, five recent user, and five recent general memory hooks;
- deduplication priority `relevant -> recent_user -> recent_general`;
- source session and source message ids for every automatic memory hook;
- optional, field-allowlisted focus, affect, and metacognitive organ blocks.

The rich retrieval/runtime snapshot remains internal evidence for traces, UI,
maintenance, and evaluation. It is not the active V2 model packet.

V1.35.0 completed the preserved-family review. `scarlet_state`, duplicated
recent dialogue, generic runtime-event summaries, and capability catalogs stay
outside automatic model input. Every `model.context` trace records the exact
projection audit, and native MiniMax plus GPT bootstrap consume the same
canonical V2 document.

V1.36.0 added a measured shadow budget for provider-native history. The normal
500k partition reserves up to 100k for recursive summary, 100k for exact recent
complete turns, 25k safety, and computes active growth from actual external
overhead. Source-labelled full/derived evaluation supports this design, but it
did not change active model input.

V1.39.0 activates that contract for native sync and stream turns. Append-only
recursive artifacts carry exact source manifests, model-facing requests use
`C + H + current`, and canonical provider history remains complete. Invalid or
missing artifacts fall back visibly to canonical history. Scheduling follows
the size of the derived next-turn view, so canonical growth alone cannot create
a perpetual maintenance loop.

Post-Core monitoring and future annotations:

- monitor active recursive compaction on naturally long sessions and preserve
  fallback/source-manifest evidence;
- the first mode router is active for automatic runtime blocks; on-demand
  shell operations remain available independently;
- no high-frequency perception or embodiment stream exists.

### 3.3 Cognitive Shell

Implemented command families:

| Family | Implemented operations | Boundary |
|---|---|---|
| help | catalog and family help | Source of truth for current syntax. |
| memory | search, write, open, graph, facts, conflicts, deprecate, supersede | update/delete unavailable by design; merge planned. |
| session | list, open, message, turn, summarize | Transcript and source navigation are on demand. |
| focus | read/list/search/set/shift/update/hold/defer/resolve/impossible/timeline | One foreground focus per profile. |
| volition | list/search/create/read/update/defer/review/promote/resolve/impossible/deprecate | No autonomous execution and no automatic chat injection. |
| affect | read/list/prototypes | Read-only to Scarlet; backend appraises state. |
| mode | read/list/set | Agent-only posture; human turns enforce `interactive`, manual selection sets the resumable tag. |
| perception | status/open/read | Availability-first access to append-only perception evidence; opening advances only the autonomous session cursor. |
| episode | list/read/open/checkpoint/suspend/resume/resolve/abandon/reject/expectation-add/expectation-resolve/wake-list/wake-add/wake-cancel | Scarlet-owned lifecycle for provisional workspace questions and explicit future wake contracts. |
| metacognition | step | One LLM-backed route, not an automatic control loop. |

Shell parsing, registry validation, dispatcher translation, model-facing
presentation, and endpoint handlers are separate modules. V1.32.0 makes the
registry/help/parser contract executable: every published command validates,
all aliases resolve consistently, targeted reads return explicit not-found
errors, and paginated collections expose truthful continuation state. Internal
facts backfill and maintenance routes are intentionally absent from normal
shell help.

### 3.4 Memory And Retrieval

Implemented:

- semantic memory with provenance and append-only lifecycle;
- legacy fact audit rows with active/inactive lifecycle but no semantic authority;
- episodic summaries and exact transcript navigation;
- automatic retrieval plus manual shell retrieval;
- FTS5/BM25 sparse search, NetworkX associative expansion, derived memory
  surfaces, embedding cache, and OpenRouter final memory-level rerank over a
  deduplicated multi-route recall pool;
- query-time relevance separated from legacy stored confidence/salience;
- memory activity ledger for cognitive recency;
- compact automatic hooks and compact shell result profiles;
- summary audit/reconciliation and dry-run-first provenance repair;
- read-only provenance/disposition audit with digest-guarded exact repair and
  explicit-fixture deprecation;
- idle summary/missed-memory review and a non-mutating proposal ledger;
- Scarlet-owned proposal list/open/accept/reject/duplicate/supersede commands
  with original source provenance and current-decision traces;
- proposal-ready events admitted to the Cognitive Workspace as candidates,
  never forced decisions or wakes.

Current limits:

- fuzzy duplicate/conflict discovery is not mature enough for deterministic
  classification; explicit Scarlet adjudication and exact-identity handling
  are implemented;
- seven production memories have inconsistent or non-user historical source links that
  cannot be repaired without semantic adjudication and remain retained,
  review-only, and excluded from automatic V2 delivery;
- single-user scope is operational convention, not authenticated ownership;
- autonomous write behavior and immediate use of retrieved preferences remain
  model-dependent;
- final rerank now has a frozen/live V1.37 calibration over 11 cases and an
  adaptive `0.004 + 1% relative` floor; larger-memory candidate pressure,
  provider drift/availability, KG entity resolution, and a production negative
  accepted at `0.004102` still need longitudinal evidence;
- maintenance retry/resume and future Dream review remain incomplete.

### 3.5 Organs

| Organ | Code state | Default/runtime state | Evidence | Current limit |
|---|---|---|---|---|
| Focus | Storage, lifecycle, shell, traces/events, optional context block | config default `off`; model block only when enabled and active | lifecycle/error tests plus V1.40 natural lifecycle and controls | 6/6 technical passes; automatic focus creation remains deliberately unimplemented |
| Volition | Storage, links, lifecycle, due queue, shell | config default `off`; manually navigable through the same shell in both lifecycles, not automatically injected into V2 | complete shell lifecycle plus V1.40 separate-session continuity and ownership controls | autonomous choice and long-term review quality remain behaviorally unvalidated |
| Affect | Backend appraisal, persistence, shell read/history/prototypes, optional context block | `shadow` default; controlled `model` mode available | deterministic contracts plus V1.40 model/shadow/neutral transitions | 10/10 post-fix technical passes; model mode has not yet shown clear qualitative benefit over shadow |
| Metacognition | One LLM-backed step, retrospective modes, optional shadow lesson context | shadow lesson selection by default; step remains model-invoked | flag-forwarding plus V1.40 broad-claim and direct-answer controls | 4/4 invocation controls passed; positive review can still overprocess and write low-value lessons |
| Temporal experience | Registry/config reservation only | `off` | manifest tests only | no computation, persistence, shell, or behavioral experiment |
| Dream/consolidation | Registry/config reservation plus maintenance terminology | `off` | no organ test beyond manifest | no dream cycle, continuity delta, or autonomous review organ |

The organ registry is a capability reservation and shared metadata substrate.
It must not be read as proof that temporal experience or Dream is implemented.

### 3.6 Agentic Module Contract, Host, And SDK

V1.52.0 accepts `agentic-module-manifest-v1`,
`agentic-module-port-v1`, and `agentic-module-lifecycle-v1` as strict public
data contracts. They define compatibility, mode tags, capabilities,
permissions, dependencies, process/resource declarations, typed exchanges,
and deterministic activation planning.

V1.53.0 adds the opt-in Module Host for approved-root discovery, process
supervision, runtime permission enforcement, contribution composition, health,
failure isolation, and receipts. No product organ has become a module and the
native Core does not instantiate the host automatically. Direct database,
secret, provider, prompt-owner, or Core-internal access remains outside the
module permission vocabulary.

V1.54.0 adds the standalone `scarlet-agentic-module-sdk` 1.0.0 package. It
owns the canonical manifest and port models imported by the host, provides a
module-side JSONL runtime, generates neutral fixtures, exports versioned JSON
Schemas, and exercises lifecycle/ports/errors with correlated conformance
evidence. Passing the kit is not operator approval, semantic validation, or a
sandbox guarantee.

## 4. Agentic Branch Assessment

The branch documents contain the full evidence and evolutions. This table is
the canonical integrated read. A principal need describes future research or
product opportunity, not an unfinished Core acceptance criterion.

| Branch | Level | Effective technical state | Principal need |
|---|---:|---|---|
| Communication | L4 | Prompt identity/effort routing, semantic stream blocks, public notes, dev/mobile rendering; substantial live evidence | expand the V1.34 suite to natural notes, greetings, concise answers, and long work |
| User flows | L2/L3 | Working dev cockpit and mobile prototype plus a readiness-driven natural-speed half greeting, locally persistent fake Login, bottom-dock navigation, semantic event-bubble Chat, inspectable fixture JSON, extended Memory layout, and grouped Settings flow | review event narration and remaining screens, then integrate V2 projection, real auth, memory/privacy management, prompt preferences and session lifecycle |
| Perception and context | L4 | One shared human/autonomous V2 packet, separate source-labelled histories, append-only external perception inbox, exact model trace, time/provenance rules, accounting, active recursive compaction and per-block mode router | admit and evaluate one bounded real source without collapsing device evidence into Scarlet first-person perception |
| Identity and relationship | L3 | Golden prompt, profile name, personal memory continuity | persistent relational model and longitudinal human evaluation |
| Memory | L4+ | Broadest and best-tested cognitive subsystem | duplicate/conflict policy, multi-user ownership, maintenance maturity, retrieval calibration |
| Learning and adaptation | L2 | Memory/preferences and prompt iteration enable indirect adaptation | learning ledger, before/after metrics, profile-specific controlled policy updates |
| Metacognition | L3/L4 | One tested route, retrospective modes, command validation, shadow lessons; V1.40 positive/negative invocation separated | reduce overprocessing and enforce/degrade when a required review is interrupted |
| Operational management | L3/L4 | Focus lifecycle passed 6/6 V1.40 controls; V1.42 mode routing and cross-session resume posture are traceable and validated | retain organ separation before goal/task expansion |
| Decision autonomy | L3/L4 | Model-controlled shell, volition register, structural finality, bounded mode selection, persisted internal cycles, shared V2/retrieval continuity, and locally verified active Workspace/episode lifecycle | observe source/candidate/no-wake and episode quality longitudinally with shadow rollback; design initiative/action receipts before external delivery |
| External operativity | L1 | No external-world tool suite in Scarlet runtime | permission, safety, rollback, capability and receipt architecture |
| Advanced operations | L1 | Cognitive shell only; no coding/artifact/specialist suite | define operations only after external-operativity governance |
| Governance/privacy/safety | L2 | DB roles, traceability, profile hints, backend field ownership | authenticated user ownership, access control, export/delete/correction, embodied safety |
| Computational affect | L3/L4 | Standalone appraisal transition passed V1.40 model/shadow/neutral controls; shadow remains default | prove causal answer benefit before model-default or integration research |
| Multi-agent/subprocesses | L1/L2 | Maintenance is deterministic/LLM-assisted background work, not multi-agent | avoid agents until one-agent limits are measured; design bounded contracts first |

## 5. Code Health

### 5.1 Strong Boundaries

- provider adapters are isolated;
- storage has a stable facade split by transaction domain;
- context V2 projection is separated from rich evidence collection;
- shell parsing, validation, dispatch, and presentation are separated;
- database roles and frozen regression state protect production/lab data;
- traces/events make state changes and model input inspectable.

### 5.2 Structural Debt

The current largest modules are:

```txt
frontend/src/App.tsx                         4474 lines
backend/app/mind/schema.py                   1870
frontend/src/MobileApp.tsx                   1766
backend/app/api/chat_native_turn.py          1659
backend/app/plugins/gpt_bridge/router.py     1509
backend/app/runtime/cognitive_workspace.py   1526
backend/app/mind/context.py                  1161
backend/app/mind/memory_read.py               996
backend/app/runtime/maintenance_memory.py     746
backend/app/mind/context_retrieval.py         731
backend/app/mind/memory_write.py              616
backend/app/mind/memory_proposals.py          555
backend/app/runtime/maintenance_scheduler.py  468
backend/app/mind/memory_lifecycle.py          462
backend/app/mind/memory_relations.py          274
backend/app/api/chat.py                       218
backend/app/runtime/maintenance_history.py    200
backend/app/mind/memory_shared.py             152
backend/app/mind/memory.py                     38
backend/app/runtime/maintenance.py             18
```

The larger owner modules are not automatically incorrect, but they still carry
meaningful regression cost. The small memory and maintenance facades are shown
to make the completed ownership boundaries explicit; they are no longer
structural debt themselves. Similar concentration remains in `test_mind_api.py`
and `test_chat_api.py`. Future rework should continue by contract and lifecycle
while preserving facades and running the frozen 9-case gate before and after.
The workspace coordinator already delegates contracts, registry, storage,
episode lifecycle, and execution to separate owners; its remaining
orchestration size should be split only after shadow behavior stabilizes.

Current engineering baseline:

- Ruff blocks objective Python syntax/name/import defects across backend code,
  tests, and repository scripts;
- mypy blocks regressions in fifty-two high-value typed modules while the measured
  full-application debt remains 216 errors across 23 files;
- the closed V1.50.1 backend suite passes 266 tests at 81.89% statement
  coverage; the V1.51.0 stream target passes 271 tests at 82.08%; the V1.52.0
  module-contract target passes 286 tests at 82.47%; the V1.53.0 module-host
  target passes 297 tests at 82.40%; the V1.54.0 SDK target passes 304 tests at
  82.46% combined Core/SDK coverage; the blocking floor remains 79.9% against
  the V1.33 baseline;
- deterministic documentation checks validate local links, repository
  references, and canonical ADR/BUG/EXP identifier uniqueness;
- GitHub Actions executes these gates and the frontend production build on
  pushes and pull requests;
- behavioral scenarios now have an executable 12-case cross-branch catalog,
  frozen references, real-provider runs, reasoned judgments, and objective-only
  automatic comparison;
- provider-history growth has active recursive compaction for native turns;
  native ChatGPT history remains outside backend accounting and compaction.

## 6. Active V2 Plan

The operational roadmap is Linear SCA-46. The repository describes its
technical invariants; Linear owns ordering and work state.

### P0 - Architecture And Core Contract

1. SCA-51 is complete: Core Runtime, Product UI, External Adapters, and Agentic
   Modules have named sources of truth and compatibility rules.
2. SCA-47 implements `scarlet-stream-v2`, idempotent client state, replay, and
   recovery without changing provider-native continuity and is merged with
   local and remote verification complete.

### P1 - Product UI And Android

1. SCA-48 has produced an isolated, schema-realistic mobile-first prototype at
   `/prototype`, with the revised Scarlet Signal visual system, responsive
   browser evidence, an integrated developer lens, and the first sequential
   app flow from readiness-driven loader/splash through a shortened preloaded
   natural-speed half-greeting transition to locally persistent fake
   Login/registration and a fixture-backed responsive shell using one bottom
   dock across Home, viewport Chat, extended Memory, Sessions, and grouped
   Profile/Settings with inspectable JSON; sequential screen review and
   explicit owner approval remain the next acceptance gates.
2. SCA-50 builds one responsive UI foundation and design system.
3. SCA-49 connects the Product UI and developer lens to Core contracts.
4. SCA-52 verifies the same client as an Android Capacitor application.

### P2 - Agentic Modules And SDK

1. SCA-53 is complete: strict manifest, typed Core Ports, modes/tags,
   permissions, dependencies, lifecycle, compatibility, and deterministic
   activation planning are accepted without loading code.
2. SCA-54 is complete: registry, host, observability, and failure isolation are
   implemented as an opt-in operator-trust boundary.
3. SCA-55 is complete: SDK 1.0.0, scaffold, schema export, module-side runtime,
   and distributable conformance kit are implemented without a product module.

### P2.5 - Cognitive Autonomy

1. SCA-57 implements the Cognitive Workspace, source receipts, M2.7
   appraisal/ignition, Scarlet-owned episodes, and event/condition wake
   contracts with local `active` field verification.
2. The next acceptance gate is longitudinal evidence across admission,
   no-wake, M3 execution, episode outcomes, and repetition. Shadow, advisory,
   and off remain immediate rollback modes.

### P3 - Release Candidate

SCA-56 proves migration from V1.50.1, Core regression, web/Android behavior,
module conformance, protected deployment, and rollback before V2 acceptance.

## 7. Deferred Evidence And Ideas

Long-session compaction quality, reranker drift, duplicate/conflict
adjudication, authenticated ownership, relationship/learning ledgers, new
organs, external operativity, and embodiment remain documented and navigable.
They are not current Core defects merely because further research is possible.
Promote one only when new evidence or an owner decision gives it a bounded
objective and acceptance gate.

GPT Actions remains an experimental adapter. Native project-selected providers
and the shared Core contracts remain authoritative.

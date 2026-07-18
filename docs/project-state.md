# Project State And Convergent Roadmap

Last updated: 2026-07-18
App baseline: V1.40.0
Status: canonical current-state map

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

- FastAPI runtime with MiniMax M3 default, MiniMax M2.7 comparison baseline,
  and optional Qwen adapter;
- persistent sessions, turns, messages, provider-native history, traces,
  cognitive events, tool calls, summaries, maintenance jobs, memories, facts,
  proposals, retrieval artifacts, focus, volition, and affect state;
- SQLite ownership roles for production, laboratory, test, and preliminary
  databases, with side-effect-free app factory and read-only preflight;
- native chat, streaming chat, developer cockpit, consumer mobile view, debug
  inspection, dashboard settings, and maintenance/evaluator routes;
- one active model-facing cognitive tool:
  `mind_shell(command, intent)`;
- internal `/mind/*` handlers retained for deterministic dispatch, tests,
  maintenance, debug, and rollback, not exposed as a second native model tool;
- GPT Actions bridge using mandatory bootstrap/action/finalize lifecycle and
  the same context compiler and shell dispatcher as native Scarlet;
- one bounded provider continuation for a thinking-only `end_turn`, followed
  by explicit `llm.incomplete_response` failure if no public answer or real
  tool call emerges; incomplete attempts remain trace-only evidence;
- per-turn accounting v2 with separate policy/V2/history/current/shell
  channels, cache-aware provider steps, exact chronology source maps, and
  active non-destructive recursive `C/H/A` compaction with canonical fallback;
- agent-only `idle`, `interactive`, and `scouting` mode registry, automatic
  context routing, persistent resumable posture, and `mode` shell commands;
- deprecated MCP experiment retained temporarily but not part of the target
  Custom GPT flow.

Current verification baseline:

- backend: 216 tests passed at 80.69% statement coverage;
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

Still open:

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
- atomic facts with active/inactive state;
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
- idle summary/missed-memory review, proposal ledger, and cautious resolution.

Current limits:

- duplicate and conflict adjudication is not mature enough for deterministic
  auto-merge or auto-deprecation;
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
| Volition | Storage, links, lifecycle, due queue, shell | config default `off`; explicitly no automatic chat injection | complete shell lifecycle plus V1.40 separate-session continuity and ownership controls | one of two current chains completed; invocation can still be interrupted by SCA-28 and no autonomous cycle exists |
| Affect | Backend appraisal, persistence, shell read/history/prototypes, optional context block | `shadow` default; controlled `model` mode available | deterministic contracts plus V1.40 model/shadow/neutral transitions | 10/10 post-fix technical passes; model mode has not yet shown clear qualitative benefit over shadow |
| Metacognition | One LLM-backed step, retrospective modes, optional shadow lesson context | shadow lesson selection by default; step remains model-invoked | flag-forwarding plus V1.40 broad-claim and direct-answer controls | 4/4 invocation controls passed; positive review can still overprocess and write low-value lessons |
| Temporal experience | Registry/config reservation only | `off` | manifest tests only | no computation, persistence, shell, or behavioral experiment |
| Dream/consolidation | Registry/config reservation plus maintenance terminology | `off` | no organ test beyond manifest | no dream cycle, continuity delta, or autonomous review organ |

The organ registry is a capability reservation and shared metadata substrate.
It must not be read as proof that temporal experience or Dream is implemented.

## 4. Agentic Branch Assessment

The branch documents contain the full evidence and evolutions. This table is
the canonical integrated read.

| Branch | Level | Effective technical state | Principal need |
|---|---:|---|---|
| Communication | L4 | Prompt identity/effort routing, semantic stream blocks, public notes, dev/mobile rendering; substantial live evidence | expand the V1.34 suite to natural notes, greetings, concise answers, and long work |
| User flows | L2/L3 | Working dev cockpit and mobile prototype with sessions, memory, profile, settings | onboarding, memory/privacy management, session lifecycle, component rework |
| Perception and context | L4 | Shared V2 packet, field-level organ projection audit, exact model trace, time/provenance rules, accounting, active recursive compaction and automatic mode router | deployed guarded compaction; monitor multi-cycle quality |
| Identity and relationship | L3 | Golden prompt, profile name, personal memory continuity | persistent relational model and longitudinal human evaluation |
| Memory | L4+ | Broadest and best-tested cognitive subsystem | duplicate/conflict policy, multi-user ownership, maintenance maturity, retrieval calibration |
| Learning and adaptation | L2 | Memory/preferences and prompt iteration enable indirect adaptation | learning ledger, before/after metrics, profile-specific controlled policy updates |
| Metacognition | L3/L4 | One tested route, retrospective modes, command validation, shadow lessons; V1.40 positive/negative invocation separated | reduce overprocessing and enforce/degrade when a required review is interrupted |
| Operational management | L3/L4 | Focus lifecycle passed 6/6 V1.40 technical controls; mode store remains separate | retain proportional selection and validate mode routing before goal/task expansion |
| Decision autonomy | L2/L3 | Model-controlled shell and volition register; one complete V1.40 cross-session chain and clean ownership controls | close answer obligations before autonomous cycle design |
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
backend/app/mind/memory.py                   2916
backend/app/plugins/gpt_bridge/router.py     1919
backend/app/mind/schema.py                   1814
frontend/src/MobileApp.tsx                   1766
backend/app/mind/context.py                  1705
backend/app/api/chat.py                      1682
backend/app/runtime/maintenance.py           1349
```

These files are not automatically incorrect, but they concentrate unrelated
responsibilities and raise regression cost. The same concentration appears in
`test_mind_api.py` and `test_chat_api.py`. A future rework should split by
contract and lifecycle while preserving facades and running the frozen 9-case
gate before and after.

Current engineering baseline:

- Ruff blocks objective Python syntax/name/import defects across backend code,
  tests, and repository scripts;
- mypy blocks regressions in eight high-value typed modules while the measured
  full-application debt remains 216 errors across 23 files;
- the full V1.34 backend suite passes 182 tests at 80.19% statement coverage;
  the blocking floor remains 79.9% against the V1.33 baseline;
- deterministic documentation checks validate local links, repository
  references, and canonical ADR/BUG/EXP identifier uniqueness;
- GitHub Actions executes these gates and the frontend production build on
  pushes and pull requests;
- behavioral scenarios now have an executable 12-case cross-branch catalog,
  frozen references, real-provider runs, reasoned judgments, and objective-only
  automatic comparison;
- provider-history growth has active recursive compaction for native turns;
  native ChatGPT history remains outside backend accounting and compaction.

## 6. Priority Plan

### P0 - Preserve The Microscope

- keep V2, rich traces, shell registry, API contract, UI inspector, and docs in
  lockstep;
- preserve and progressively expand the V1.34.0 lint, type, coverage,
  documentation, and CI baseline instead of weakening it during broad rework;
- keep database role/preflight and frozen 9-case gate mandatory.

### P1 - Validate And Activate Context Control

1. Monitor recursive source-labelled summary artifacts under the 100k `C` cap.
2. Extend long-session evidence without weakening canonical fallback.
3. Add observability for artifact age, invalidation, and compaction latency.
4. Keep GPT-native history limits explicit until ChatGPT exposes that context.

### P2 - Memory Integrity

1. Design duplicate candidate detection as evidence, not deterministic truth.
2. Keep conflict adjudication LLM/human-aware; do not infer conflicts from
   similarity alone.
3. Keep the seven unresolved historical source links review-only unless new
   exact evidence appears; never synthesize provenance from similarity.
4. Calibrate final-rerank candidate coverage/thresholds, KG recall, and
   maintenance retries on frozen and live cases.
5. Design authenticated user ownership before multi-user data exists.

### P3 - Close Answer Obligations And Preserve Organ Separation

- implement SCA-28 so a progress note cannot satisfy a required final answer or
  silently interrupt a selected cognitive mutation;
- preserve SCA-4 conservative defaults and add no cross-organ coupling;
- keep affect model exposure and metacognitive lesson injection experimental;
- do not build temporal experience or Dream from registry placeholders.

### P4 - Code Reorganization

- split the context collector from retrieval scoring/orchestration;
- split memory handlers by write/read/lifecycle/maintenance presentation;
- split chat orchestration from trace/event/provider-history composition;
- split GPT Actions and deprecated MCP transport;
- componentize developer and mobile frontends;
- preserve public facades and compare the exact preliminary suite before/after.

### P5 - Identity, Relationship, Learning, And Governance

- create sourceable relational and adaptation ledgers only after privacy
  ownership exists;
- establish longitudinal behavioral metrics;
- keep identity claims tied to observable digital functions;
- define consent, deletion, correction, and external-action risk levels.

### P6 - External And Embodied Architecture

Only after P0-P5 supply reliable routing, ownership, permissions, and organ
behavior:

- add world perception as summarized, fresh, source-labelled packs;
- separate sensory fact, inference, plan, and actuator receipt;
- gate physical action with safety, authority, rollback, and current scene;
- keep high-frequency raw streams outside the language-model context.

## 7. Current Best Next Step

The next approved issue is SCA-28: distinguish public progress narration from a
conclusive final answer and preserve required cognitive actions across that
boundary. After it closes, SCA-6 can validate agent-mode routing against the
now-classified standalone organ defaults. Long varied sessions should still
monitor active compaction/degradation. Duplicate/conflict adjudication remains
a separate later discussion.

Do not add another organ before these surfaces make the current system easier
to reason about than it is today.

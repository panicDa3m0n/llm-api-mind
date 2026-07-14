# Project State And Convergent Roadmap

Last updated: 2026-07-14
App baseline: V1.33.0
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
- per-turn context accounting with exact character/byte channels, provider
  first-step observations, and non-destructive compaction planning;
- agent-only `idle`, `interactive`, and `scouting` mode registry, automatic
  context routing, persistent resumable posture, and `mode` shell commands;
- deprecated MCP experiment retained temporarily but not part of the target
  Custom GPT flow.

Verification baseline on 2026-07-13:

- backend: 161 tests passed;
- frozen whole-system preliminary regression: 9/9;
- frontend TypeScript/Vite production build: passed;
- database boundary check: passed;
- V1.32.0 production rollout: native MiniMax and GPT Actions smoke tests passed;
  OpenRouter final rerank completed in production traces and DB integrity
  remained `ok`.
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
- preserved dynamic families whose final disposition has not yet been reviewed.

The rich retrieval/runtime snapshot remains internal evidence for traces, UI,
maintenance, and evaluation. It is not the active V2 model packet.

Still open:

- `preserved_context` contains focus, affect, Scarlet state,
  metacognitive context, recent dialogue, recent runtime events, and capability
  hints when their legacy conditions apply;
- provider-native history is not budgeted or compacted and can outweigh V2 in
  tool-heavy sessions;
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
- idle summary/missed-memory review, proposal ledger, and cautious resolution.

Current limits:

- duplicate and conflict adjudication is not mature enough for deterministic
  auto-merge or auto-deprecation;
- 242 production historical memories still lack enough evidence for a safe
  deterministic provenance repair;
- single-user scope is operational convention, not authenticated ownership;
- autonomous write behavior and immediate use of retrieved preferences remain
  model-dependent;
- final-rerank threshold (provisionally `0.01` after two V1.31 positive
  controls and one negative control), candidate coverage, provider
  availability, and KG entity resolution need broader live calibration;
- maintenance retry/resume and future Dream review remain incomplete.

### 3.5 Organs

| Organ | Code state | Default/runtime state | Evidence | Current limit |
|---|---|---|---|---|
| Focus | Storage, lifecycle, shell, traces/events, optional context block | config default `off`; model block only when enabled and active | lifecycle/error tests plus direct V1.32 set/read/recovery use | not connected to goal/task lifecycle; autonomous upkeep unvalidated |
| Volition | Storage, links, lifecycle, due queue, shell | config default `off`; explicitly no automatic chat injection | complete shell lifecycle test plus direct scheduled V1.32 creation | register only; no autonomous cycle or execution |
| Affect | Backend appraisal, persistence, shell read/history/prototypes, optional context block | config default `off`; shadow/model modes available | filter/not-found/pagination tests plus direct V1.32 read | primitive lexical/event prototypes; long-run behavioral calibration missing |
| Metacognition | One LLM-backed step, retrospective modes, optional shadow lesson context | shadow lesson selection by default; step remains model-invoked | flag-forwarding tests and direct V1.32 critic use | recommendations can be ignored; no guaranteed continuation or final gate |
| Temporal experience | Registry/config reservation only | `off` | manifest tests only | no computation, persistence, shell, or behavioral experiment |
| Dream/consolidation | Registry/config reservation plus maintenance terminology | `off` | no organ test beyond manifest | no dream cycle, continuity delta, or autonomous review organ |

The organ registry is a capability reservation and shared metadata substrate.
It must not be read as proof that temporal experience or Dream is implemented.

## 4. Agentic Branch Assessment

The branch documents contain the full evidence and evolutions. This table is
the canonical integrated read.

| Branch | Level | Effective technical state | Principal need |
|---|---:|---|---|
| Communication | L4 | Prompt identity/effort routing, semantic stream blocks, public notes, dev/mobile rendering; substantial live evidence | stable behavioral suite for natural notes, greetings, concise answers, and long work |
| User flows | L2/L3 | Working dev cockpit and mobile prototype with sessions, memory, profile, settings | onboarding, memory/privacy management, session lifecycle, component rework |
| Perception and context | L4 | Shared V2 packet, exact model trace, time/provenance rules, accounting and automatic mode router | preserved-family review and measured active compaction design |
| Identity and relationship | L3 | Golden prompt, profile name, personal memory continuity | persistent relational model and longitudinal human evaluation |
| Memory | L4+ | Broadest and best-tested cognitive subsystem | duplicate/conflict policy, multi-user ownership, maintenance maturity, retrieval calibration |
| Learning and adaptation | L2 | Memory/preferences and prompt iteration enable indirect adaptation | learning ledger, before/after metrics, profile-specific controlled policy updates |
| Metacognition | L3 | One tested route, retrospective modes, command validation, shadow lessons | prove answer improvement and enforce/degrade when recommended evidence is skipped |
| Operational management | L2/L3 | Focus is real; events and maintenance exist | approved goal/task/open-loop model and focus maintenance rules |
| Decision autonomy | L2/L3 | Model-controlled shell use and volition register | explicit risk/permission policy, autonomous cycle design, receipts |
| External operativity | L1 | No external-world tool suite in Scarlet runtime | permission, safety, rollback, capability and receipt architecture |
| Advanced operations | L1 | Cognitive shell only; no coding/artifact/specialist suite | define operations only after external-operativity governance |
| Governance/privacy/safety | L2 | DB roles, traceability, profile hints, backend field ownership | authenticated user ownership, access control, export/delete/correction, embodied safety |
| Computational affect | L3 | Standalone organ implemented and tested, disabled by default | long-session shadow/model calibration and memory/relationship integration research |
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
- mypy blocks regressions in six high-value typed modules while the measured
  full-application debt remains 216 errors across 23 files;
- the full backend suite has a measured 79.998% statement-coverage baseline
  and a blocking 79.9% floor;
- deterministic documentation checks validate local links, repository
  references, and canonical ADR/BUG/EXP identifier uniqueness;
- GitHub Actions executes these gates and the frontend production build on
  pushes and pull requests;
- behavioral scenarios now have a versioned four-layer contract, but the first
  small continuously repeated cross-branch suite still needs populated cases;
- provider-history growth is measured and shadow-planned but has no active
  compaction/degradation policy.

## 6. Priority Plan

### P0 - Preserve The Microscope

- keep V2, rich traces, shell registry, API contract, UI inspector, and docs in
  lockstep;
- preserve and progressively expand the V1.33.0 lint, type, coverage,
  documentation, and CI baseline instead of weakening it during broad rework;
- keep database role/preflight and frozen 9-case gate mandatory.

### P1 - Validate And Activate Context Control

1. Continue field-by-field review of preserved families.
2. Accumulate exact accounting from long varied post-V1.30 sessions.
3. Design and test the derived 100k chronology plus desired eight-turn tail.
4. Define degradation when the measured tail cannot fit below 500k.
5. Promote active compaction only after direct continuity/source tests.

### P2 - Memory Integrity

1. Design duplicate candidate detection as evidence, not deterministic truth.
2. Keep conflict adjudication LLM/human-aware; do not infer conflicts from
   similarity alone.
3. Improve historical provenance only where session/message evidence is
   defensible.
4. Calibrate final-rerank candidate coverage/thresholds, KG recall, and
   maintenance retries on frozen and live cases.
5. Design authenticated user ownership before multi-user data exists.

### P3 - Validate Existing Organs

- evaluate focus upkeep, volition use, affect shadow/model behavior, and
  metacognitive improvement in correlated multi-session tests;
- decide coupling only after standalone behavior is reliable;
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

The next implementation should collect post-V1.30 accounting from long varied
sessions and populate the behavioral contract with natural branch-level cases.
That evidence should decide the active compaction/degradation algorithm.
Duplicate/conflict adjudication remains a separate later discussion.

Do not add another organ before these surfaces make the current system easier
to reason about than it is today.

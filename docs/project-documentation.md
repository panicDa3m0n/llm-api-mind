# Project Documentation Index

Last updated: 2026-07-19
App baseline: V1.50.1 deployed and release-accepted
Status: canonical documentation map

This is the entry point for project documentation. It separates two layers:

- technical infrastructure documents, which describe code, APIs, tests,
  traces, and implementation details;
- agentic branch documents, which describe Scarlet's real operating domains:
  communication, memory, metacognition, goals, autonomy, external operation,
  privacy, and future advanced capabilities.

Use `docs/project-state.md` for the current integrated implementation state.
Use the branch documents when planning work that changes Scarlet as an agent.

Current-state claims must be read from current-state documents and code, not
from chronological records. `activity-log.md`, `experiments.md`, old ADR text,
checkpoints, and completed implementation plans preserve what was true when an
event happened; they are not silently rewritten into present-tense contracts.

## Development Protocol

The active engineering protocol lives in:

```txt
docs/development-process.md
```

From V1.0.1 onward, every intervention must declare its area and classify the
work before implementation:

- `Fix`: increments the patch number, `0.0.X`.
- `Implementazione`: increments the minor number, `0.X.0`.
- `Major release`: increments the major number, `X.0.0`, only for very large
  release-grade changes.

Only the declared scope may be changed. Problems discovered during testing but
not directly caused by the current implementation must be reported and
discussed before a new fix is attempted.

## Core Project Documents

- `AGENTS.md`: always-read operating guide for Codex/Scarlet.
- `docs/project-blueprint.md`: durable philosophy and architecture principles.
- `docs/project-state.md`: current implementation map and convergent roadmap.
- `docs/core-runtime-contract.md`: canonical Core Runtime, Product UI,
  External Adapter, and Agentic Module boundary, including owners and
  compatibility classes.
- `docs/stream-v2-contract.md`: canonical Product UI stream, replay cursor,
  provider-independent event envelope, and reference reducer contract.
- `docs/product-ui-prototype.md`: SCA-48 static Product UI information
  architecture, fixture boundary, preview states, visual tokens, component
  equivalence notes, browser evidence, screenshots, and approval gate.
- `docs/agentic-modules-contract.md`: public manifest, typed Core Ports,
  permission/dependency model, lifecycle, activation rules, and compatibility
  boundary for optional V2 Agentic Modules.
- `docs/agentic-module-host.md`: approved-root discovery, process transport,
  lifecycle supervision, port composition, telemetry, and failure-isolation
  contract for the opt-in V2 Module Host.
- `docs/agentic-module-sdk.md`: standalone SDK install/build, canonical public
  contracts, module-side runtime, scaffold, schema export, conformance, and
  operator handoff.
- `docs/branches/README.md`: compact branch maturity and technical evidence
  matrix for the current release.
- `docs/activity-log.md`: chronological work log.
- `docs/decisions.md`: architectural decision records.
- `docs/bug-ledger.md`: known bugs, root causes, and monitoring items.
- `docs/experiments.md`: hypotheses, live probes, and results.
- `docs/api-contract.md`: implemented and planned API contracts.
- `docs/block-registry.md`: runtime/model/UI block map for Scarlet turns.
- `docs/context-packet-inventory.md`: reviewed inventory of automatic local and
  GPT bridge packets, including the active V2 model packet, its rich internal
  source snapshot, manual shell boundaries, and trace/UI-only data.
- `docs/context-packet-implementation-plan.md`: phased V1.29.0 plan for the
  implemented compact dynamic context contract, memory activity, source
  navigation, provider parity, repair procedures, and regression acceptance.
- `docs/runtime-context-packs.md`: planning baseline for always-on context
  spine, measured context budgets, agent-mode tags, organ/source
  classification, compaction gates, and future embodied routing.
- `docs/behavioral-validation-framework.md`: versioned starting-condition,
  technical-evidence, cognitive-choice, answer-outcome, and longitudinal
  validation contract for direct Scarlet experiments.
- `docs/evaluations/v1.30-agent-mode-live.md`: exact first application of that
  contract to agent-mode selection, state persistence, and overclaim limits.
- `docs/evaluations/v1.32-shell-organ-audit.md`: command-family conformance,
  negative paths, lifecycle evidence, and five disposable MiniMax M3 organ
  scenarios.
- `docs/evaluations/v1.34-natural-behavioral-suite.md`: frozen starting
  conditions, 12 natural scenarios, 36 authoritative live turns, evaluator
  shakedown history, project-informed qualitative judgments, and cross-branch
  findings.
- `docs/evaluations/v1.36-history-compaction-calibration.md`: exact real-session
  token accounting, full/derived MiniMax comparison, and the accepted
  whole-turn exception while active compaction remains gated.
- `docs/evaluations/v1.37-memory-rerank-calibration.md`: immutable candidate
  coverage, final-rerank calibration, sourceable V2 delivery, latency, and
  direct MiniMax semantic review.
- `docs/evaluations/v1.38-historical-provenance-audit.md`: production-read-only
  classification, explicit fixture criteria, mutation guards, disposable-copy
  gate, residual ambiguous links, and deployment evidence.
- `docs/evaluations/v1.39-active-history-compaction.md`: recursive artifact
  generation, exact source anchoring, native sync/stream routing, canonical
  preservation, and direct MiniMax validation on a disposable database.
- `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`: correlated focus,
  volition, affect, and metacognition scenarios; runtime receipts; independent
  controls and conservative default decisions.
- `docs/evaluations/v1.41-answer-obligations.md`: structural and semantic final-
  answer contracts, bounded correction, GPT rejection policy, focused tests,
  and direct native/GPT probe evidence.
- `docs/evaluations/v1.42-agent-mode-routing.md`: per-block routing receipts,
  off/shadow/active delivery semantics, native/GPT parity, prompt selection
  calibration, and bounded two-session Scarlet evidence.
- `docs/evaluations/v1.43-mcp-retirement.md`: deprecated connector removal,
  transport authentication cleanup, production evidence preservation, and
  deployment closure.
- `docs/evaluations/v1.43-memory-rerank-negative-calibration.md`: frozen
  unsupported-personal controls, direct reranker evidence, and the documented
  decision to defer an unsafe threshold-only correction.
- `docs/evaluations/v1.44-chat-support-extraction.md`: SCA-34 module boundary,
  exact pre/post contracts, direct native provider-history probe, qualitative
  judgment, and isolated residual bug.
- `docs/evaluations/v1.45-native-turn-orchestration.md`: SCA-33 lifecycle
  boundary, sync/stream invariant evidence, direct continuity probe, trace
  parity fix, and qualitative variance classification.
- `docs/evaluations/v1.46-context-retrieval-separation.md`: SCA-35 retrieval
  ownership boundary, frozen equivalence, direct model-facing proof, and the
  isolated provenance-fixture gap.
- `docs/evaluations/v1.47-memory-read-surface.md`: SCA-36 facade/read ownership,
  exact pre/post shell evidence, and direct search/open/facts/graph inspection.
- `docs/evaluations/v1.48-memory-mutation-surface.md`: SCA-38 mutation-domain
  ownership, exact equivalence, direct lifecycle/proposal evidence, and a
  natural Scarlet persistence probe.
- `docs/evaluations/v1.49-maintenance-domains.md`: SCA-37 maintenance-domain
  ownership, exact equivalence, direct compaction evidence, and natural
  summary/memory-review judgment.
- `docs/evaluations/v1.49.1-action-retry-obligations.md`: shared native/GPT
  retry-chain evidence, deterministic regressions, and directly inspected
  MiniMax recovery behavior.
- `docs/evaluations/v1.50-model-facing-memory-gate.md`: complementary automatic-
  memory delivery gate, guarded disposable provenance repair, provider-request
  proof, and incomplete-turn negative control.
- `docs/evaluations/v1.50.1-native-finality-recovery.md`: historical production
  marker-omission evidence and the semantic fallback later superseded by the
  provider-native `end_turn` contract in ADR-0132.
- `docs/preliminary-regression-suite.md`: mandatory pre/post whole-system
  regression gate for major reworks and architectural procedures.
- `docs/quality-gates.md`: incremental Ruff, mypy, coverage, documentation,
  and GitHub Actions baseline for engineering changes.
- `docs/database-topology.md`: canonical ownership map and deployment/test
  boundary for production, laboratory, test, and preliminary databases.
- `docs/monolith-rework-plan.md`: current code-concentration inventory, stable
  facades, dependency order, atomic Linear slices, and mandatory pre/post gate
  for organizational rework.
- `docs/release-process.md`: commit, changelog, and release discipline.
- `CHANGELOG.md`: project-visible change history.

## Document Authority

| Document family | Authority | Update behavior |
|---|---|---|
| `project-state.md`, branch index, API contract | Present implementation and current priorities | Update whenever current truth changes. |
| Branch documents | Current behavior and branch-specific direction | Keep philosophy, evidence, status, limits, and next work aligned. |
| Blueprint | Durable purpose and architecture constraints | Change only when the project direction or durable boundary changes. |
| Decisions | Accepted architectural choices | Append or supersede; do not erase the original context. |
| Experiments, activity log, checkpoints | Historical evidence | Preserve results as recorded; add corrections or current links instead of rewriting outcomes. |
| Implementation plans | Procedure and acceptance record | Mark completed/deferred phases; do not use as current-state authority after completion. |

## Vertical Roadmaps

- `docs/memory-roadmap.md`: detailed memory system roadmap.
- `docs/cognitive-api-roadmap.md`: schema discipline and internal
  metacognition roadmap.

## Theory Documents

- `docs/theory-goal-focus-task.md`: owner-review theory for Scarlet's future
  goal, focus, open-loop, and task organ.
- `docs/theory-metacognition.md`: owner-review theory for Scarlet's future
  metacognitive organ and its distinction from notes, maintenance, and
  validators.
- `docs/digital-individual-organs-notes.md`: active working notes for the five
  next digital-individual organs: lived attention, volition, affective
  integration, temporal experience, and sleep-like consolidation.

## Agentic Branch Documents

The canonical branch index lives in:

```txt
docs/branches/README.md
```

Current branches:

1. `docs/branches/communication.md`
2. `docs/branches/user-flows.md`
3. `docs/branches/perception-context.md`
4. `docs/branches/identity-relationship.md`
5. `docs/branches/memory.md`
6. `docs/branches/learning-adaptation.md`
7. `docs/branches/metacognition.md`
8. `docs/branches/operational-management.md`
9. `docs/branches/decision-autonomy.md`
10. `docs/branches/external-operativity.md`
11. `docs/branches/advanced-operations.md`
12. `docs/branches/governance-privacy-safety.md`
13. `docs/branches/computational-affect.md`
14. `docs/branches/multi-agent-subprocesses.md`

## Branch Document Format

Each branch document must keep these sections:

- `Filosofia del ramo`
- `Evidenze`
- `Stato attuale`
- `Sviluppi precedenti`
- `Evolutive`

Every `Stato attuale` section must include the app/system version used for the
assessment, so future updates can be traced back to the correct implementation
state.

## Update Rules

When a change affects a branch:

1. update the relevant branch document;
2. update `docs/project-state.md` if the integrated state or priority changed;
3. update `docs/activity-log.md`;
4. update `CHANGELOG.md`;
5. update `docs/decisions.md` only for architectural/process decisions;
6. update `docs/bug-ledger.md` only for bugs or residual risks;
7. update `docs/experiments.md` only for hypotheses, probes, or results.

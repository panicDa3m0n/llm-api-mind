# Project Documentation Index

Last updated: 2026-07-12
App baseline: V1.29.0
Status: canonical documentation map

This is the entry point for project documentation. It separates two layers:

- technical infrastructure documents, which describe code, APIs, tests,
  traces, and implementation details;
- agentic branch documents, which describe Scarlet's real operating domains:
  communication, memory, metacognition, goals, autonomy, external operation,
  privacy, and future advanced capabilities.

Use `docs/project-state.md` for the current integrated implementation state.
Use the branch documents when planning work that changes Scarlet as an agent.

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
- `docs/activity-log.md`: chronological work log.
- `docs/decisions.md`: architectural decision records.
- `docs/bug-ledger.md`: known bugs, root causes, and monitoring items.
- `docs/experiments.md`: hypotheses, live probes, and results.
- `docs/api-contract.md`: implemented and planned API contracts.
- `docs/block-registry.md`: runtime/model/UI block map for Scarlet turns.
- `docs/context-packet-inventory.md`: reviewed inventory of automatic local and
  GPT bridge packets, manual shell boundaries, and trace/UI-only data.
- `docs/context-packet-implementation-plan.md`: phased V1.29.0 plan for the
  implemented compact dynamic context contract, memory activity, source
  navigation, provider parity, repair procedures, and regression acceptance.
- `docs/runtime-context-packs.md`: planning baseline for always-on context
  spine, mode packs, organ/source classification, and future embodied runtime
  routing.
- `docs/preliminary-regression-suite.md`: mandatory pre/post whole-system
  regression gate for major reworks and architectural procedures.
- `docs/database-topology.md`: canonical ownership map and deployment/test
  boundary for production, laboratory, test, and preliminary databases.
- `docs/release-process.md`: commit, changelog, and release discipline.
- `CHANGELOG.md`: project-visible change history.

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

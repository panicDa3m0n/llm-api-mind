# Project Documentation Map

Last updated: 2026-07-31
Current deployment: V1.68.0 on the protected VPS
Status: canonical routing map, not a second architecture specification

This is the entry point for documentation. Read the smallest source that owns
the question, then verify it against current code and direct evidence. Do not
treat chronology, an old plan, a checkpoint, or a file's existence as proof of
current behavior.

## Read Order

For every repository change:

1. `AGENTS.md` for operating constraints.
2. This map for the owning source.
3. `docs/project-state.md` for the current integrated state.
4. The exact current contract and executable code for the affected behavior.
5. Only the relevant decision, bug, experiment, evaluation, or checkpoint.

Do not default-read the long ledgers. Search them for a named decision, version,
incident, trace, or evaluation question.

## Current Sources

| Need | Source of truth |
|---|---|
| Technology choices, status, reasons, and custom solutions | `docs/technology-map.md` |
| Bounded external computation and cited web sources | `docs/research-lab.md` |
| Architecture boundaries, active versus experimental surfaces | `docs/core-runtime-contract.md` |
| Current implementation state and V2 priority | `docs/project-state.md` |
| Verified behavior-preserving cleanup candidates | `docs/maintainability-audit.md` |
| Code retirement, compatibility, and documentation ownership | `docs/development-process.md` |
| Approved V2 direction, not implemented behavior | `docs/v2-cognitive-companion-plan.md` |
| Native/GPT/model-facing and HTTP contracts | `docs/api-contract.md`, then executable routes and schemas |
| Turn blocks, event evidence, UI mapping | `docs/block-registry.md`; stream work also reads `docs/stream-v2-contract.md` |
| Dynamic packet and context delivery | `docs/context-packet-inventory.md`, `docs/runtime-context-packs.md`, and their compiler/contract code |
| Historical prompt snapshots | `docs/archive/prompt-history/`; current runtime policy stays under `backend/app/prompts/` |
| Memory behavior | `docs/branches/memory.md`, relevant API contract, and memory code |
| Autonomous cognition, Workspace, perception | `docs/branches/decision-autonomy.md`, `docs/cognitive-workspace.md`, `docs/endogenous-cognition.md`, and owning runtime code |
| Context-family/device experiments | `docs/context-family-registry.md`, `docs/device-exploration-layer.md`, and owning adapter code |
| Database role and data safety | `docs/database-topology.md` |
| Product UI/API parity | `docs/product-ui-prototype.md`, `docs/stream-v2-contract.md`, and deployed client code |
| Modules, host, SDK boundary | `docs/agentic-modules-contract.md`, `docs/agentic-module-host.md`, `docs/agentic-module-sdk.md` |
| Release, Android, VPS | `docs/release-process.md`, `docs/database-topology.md`, and live deployment evidence |
| Agentic domain framing | `docs/branches/README.md`, then one relevant branch file |

`docs/project-blueprint.md` is the durable research direction. Read it for a
new architectural direction, not for routine current-state verification.

## Status Language

Use these terms precisely in current documentation:

- **active**: supported runtime behavior with current direct evidence;
- **experimental**: bounded research or adapter behavior, not Core authority;
- **shadow**: observed/compared but not deciding ordinary cognition;
- **historical**: evidence of what was true at a previous point;
- **deprecated**: retained for provenance, migration, or rollback, not a normal
  operating path;
- **planned**: owner-approved direction without implementation claim.

Code, configuration, a table, or an old test may prove implementation
availability. It does not by itself prove an active user-visible capability.

## Historical And Research Records

These records remain valuable but are not present-tense contracts:

- `docs/activity-log.md`, `docs/decisions.md`, `docs/bug-ledger.md`, and
  `docs/experiments.md` are append-only evidence ledgers.
- `docs/evaluations/` and `docs/checkpoints/` preserve bounded test and
  discussion evidence.
- `docs/archive/prompt-history/` preserves only cited historical prompt
  snapshots; it is not a runtime prompt fallback.
- completed implementation plans, including
  `docs/context-packet-implementation-plan.md` and
  `docs/monolith-rework-plan.md`, describe their recorded slice.
- `docs/memory-roadmap.md`, `docs/cognitive-api-roadmap.md`,
  `docs/digital-individual-organs-notes.md`, `docs/theory-goal-focus-task.md`,
  and `docs/theory-metacognition.md` are research/roadmap material unless
  their top status says otherwise.
- retired MCP and avatar experiments remain historical evidence only.

Historical records are not rewritten to pretend they describe the present.
When an old statement could mislead, add a status and successor link at its
entry point.

## Documentation Maintenance

Update only the owning document when current truth changes:

- current contract or project state for code/runtime behavior;
- decision log for accepted architecture or process;
- bug ledger for a defect or residual risk;
- experiments/evaluation for a hypothesis or result;
- activity log for meaningful completed work;
- changelog only for a released/project-visible product change.

Do not create a new Markdown register for a one-off note. If a document loses
authority, retain it as historical/deprecated and name its successor rather
than deleting evidence.

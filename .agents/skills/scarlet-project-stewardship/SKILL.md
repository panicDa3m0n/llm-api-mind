---
name: scarlet-project-stewardship
description: Preserve Scarlet's architecture and research direction for substantial planning, state review, boundaries, roadmap work, or changes that could blur Core, Product UI, adapters, cognitive organs, modules, and embodiment. Do not use it instead of a specific debugging, evaluation, or release workflow.
---

# Scarlet Project Stewardship

## Purpose

Keep Scarlet a traceable digital-individual research system, not a generic
chat wrapper, developer assistant, dashboard persona, or unsupported claim of
biological life. Current work must improve a real technical behavior while
preserving future companion and embodiment options.

## Authoritative Sources

Start with `AGENTS.md`, `docs/project-documentation.md`,
`docs/project-state.md`, and `docs/core-runtime-contract.md`. Then read the
smallest owning branch, contract, decision, experiment, or bug record and the
exact code needed for the question. Use the blueprint only for durable project
direction, not as an implementation status report.

## Architectural Checks

- Core owns cognition, continuity, canonical data, provider orchestration,
  persistence, and model-facing contracts.
- Product UI consumes Core contracts and renders evidence; it does not invent
  cognition or become a second agent.
- Native selected-provider behavior is authoritative. GPT Actions is a
  bounded experimental adapter, not a reason to distort native Core.
- `mind_shell(command, intent)` is Scarlet's one model-facing cognitive tool.
  Internal routes remain implementation, debug, or maintenance boundaries.
- Static policy, provider history, dynamic context, traces, UI projections,
  and background work have separate owners.
- Canonical history and source provenance survive all compact, derived, or UI
  representations.

## Working Loop

1. Declare the work and inspect the baseline in code and direct evidence.
2. Name the user-visible or cognitive outcome and its owning layer.
3. Identify the smallest change or analysis that can establish it.
4. Distinguish deterministic responsibilities from semantic judgment.
5. Check whether existing code already owns the behavior before introducing an
   abstraction or a parallel path.
6. Keep new state, decisions, and failures inspectable through traces/events.
7. Verify actual output qualitatively as well as mechanically.

## Capability Gate

Before describing a component as present, label it correctly:

- active only with a supported runtime path and current direct evidence;
- experimental only with a bounded purpose and explicit limitations;
- shadow only when it cannot decide normal cognition; and
- historical/deprecated when retained solely for provenance, rollback, or
  research.

Do not leave a new shadow, prototype, or compatibility path ambiguous. Its
owner, purpose, evidence, and promotion-or-retirement decision must be visible
in the owning contract or decision record.

## Maintenance Contract

Update this skill when verified code, direct evidence, an owner correction, a
production incident, or a successful repeated workflow exposes a better
architectural check. Update the owning contract first if semantics changed.
Remove obsolete advice rather than accumulating compatibility folklore; keep
historical evidence in its ledger. Update this skill during the same scoped
task when doing so prevents repetition, then run the skill validator.

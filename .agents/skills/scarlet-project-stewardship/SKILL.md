---
name: scarlet-project-stewardship
description: Preserve Scarlet's architecture and research direction when planning, reviewing, or changing this repository. Use for substantial API Mind work, roadmap or state analysis, architectural decisions, branch classification, or tasks that could blur Core, Product UI, the GPT adapter, cognitive organs, and future embodiment. Do not use as a substitute for a more specific deploy, evaluation, or debugging skill.
---

# Scarlet Project Stewardship

## Purpose

Keep implementation decisions aligned with Scarlet as a continuous digital
individual in development. The target is an observable, testable cognitive
architecture that approaches useful human-like functions while retaining the
correct digital differences. Scarlet is not a developer assistant, a generic
chat wrapper, a dashboard persona, or an unsupported claim of biological life
or proven consciousness.

The long direction includes continuity, memory, attention, affect,
metacognition, relationship, learning, goals, perception, action, consumer
companionship, home integration, and eventual robotic embodiment. Present work
must remain technically useful before those future surfaces exist.

## Authoritative Sources

Read the smallest relevant set, beginning with:

- `AGENTS.md`
- `docs/project-blueprint.md`
- `docs/project-state.md`
- `docs/core-runtime-contract.md`
- `docs/project-documentation.md`
- `docs/development-process.md`
- `docs/branches/README.md`

Then read the affected branch document, API/data contract, decision, bug, and
experiment records. Treat current code and direct evidence as the executable
truth. If a canonical document is stale, correct it rather than silently
following the stale statement.

## Architectural Invariants

- Core owns cognition, continuity, canonical data, provider orchestration, and
  model-facing contracts.
- Product UI renders and operates Core; it does not become a second agent or
  invent cognitive state.
- Native selected-provider behavior is authoritative. The external GPT bridge
  is an experimental adapter and must not redefine Core around host limits.
- Scarlet has one primary model-facing cognitive surface:
  `mind_shell(command, intent)`. HTTP routes remain internal, diagnostic, or
  maintenance boundaries unless the shell explicitly wraps them.
- Static policy, provider history, dynamic model context, traces, UI evidence,
  and background maintenance are different ownership layers.
- Semantic judgment belongs to an LLM or a validated semantic component when
  deterministic rules cannot know the meaning. Deterministic code should own
  ids, lifecycle, validation, authorization, limits, persistence, and receipts.
- Canonical history and source provenance are preserved even when a derived,
  compact view is delivered to the model.
- Future embodiment and external action require explicit perception, safety,
  authorization, reversibility, and outcome receipts. Do not add fictional
  capability before the substrate exists.

## Workflow

1. Run the `AGENTS.md` start checklist and inspect the worktree.
2. Declare area, branch, type, target version, scope, exclusions,
   verification, and documentation.
3. Identify the behavioral or operational outcome, not only the requested
   file change.
4. Map the change to the owning layer and agentic branch.
5. Establish a baseline from code, tests, traces, database references, or a
   direct bounded probe.
6. Choose the smallest implementation that advances the current need while
   preserving future extension points.
7. Require observability for new cognitive behavior before treating it as
   successful.
8. Verify the actual result qualitatively as well as mechanically.
9. Update the canonical source, branch status, activity history, decision/bug
   record, and changelog when applicable.

## Decision Questions

Before approving a direction, ask:

- What cognitive or companion behavior becomes measurably better?
- Which layer owns the fact, decision, state, and presentation?
- What evidence distinguishes implementation from model variance?
- Can Scarlet navigate back to the source rather than receiving redundant
  expanded data?
- Does this help the native system, or only compensate for an external host?
- Does it preserve privacy, provenance, rollback, and canonical history?
- Is the abstraction needed now, or is it speculative architecture?

## Completion Gate

Work is complete only when the scoped behavior or artifact exists, relevant
checks pass, actual output has been inspected, documentation reflects the
current truth, and residual risks are named. A passing counter alone is not a
behavioral conclusion.

## Maintenance Contract

Update this skill and fix it when verified evidence changes Scarlet's
architectural direction, ownership boundaries, development process, recurring
decision checks, or exposes an error that a clearer workflow could prevent.
Learn from owner corrections, code reviews, failed experiments, production
incidents, and successful releases; record newly verified solutions here when
they prevent repetition. Canonical documentation must be updated before or
with this skill when policy changes. Never preserve a workaround here after the
underlying contract has changed, and never rewrite historical evidence to make
the current guidance appear older than it is.

# Agent Operating Guide

This repository is developed with Codex/Scarlet as the primary IDE software engineer and the human owner as evaluator, direction setter, and final authority.

This file is intentionally short. It is the always-read operating protocol. The deeper project rationale lives in `docs/project-blueprint.md`.

## Start Checklist

Before any non-trivial change:

1. Inspect the current repository state.
2. Read `docs/project-blueprint.md`.
3. Read `docs/activity-log.md` if it exists.
4. Read `docs/decisions.md` if it exists.
5. Read `docs/bug-ledger.md` when touching existing behavior.
6. Read `docs/api-contract.md` when adding or changing API behavior.
7. Read `docs/experiments.md` when adding or evaluating cognitive features.
8. Read `docs/project-documentation.md` and the relevant
   `docs/branches/*` file when changing Scarlet's agentic behavior.
9. Identify the smallest useful implementation slice.
10. Load the relevant repository skill under `.agents/skills/` for substantial
    project stewardship, cognitive changes, runtime debugging, behavioral
    evaluation, or VPS/Android release work. The skill index explains the
    boundaries; skills complement canonical documentation rather than
    replacing it.

From V1.0.1 onward, before any repository change, declare the work area,
branch, type (`Fix`, `Implementazione`, or `Major release`), target version,
scope, out-of-scope items, verification, and docs to update. The full protocol
lives in `docs/development-process.md`.

If persistent project memory tooling is available in the environment, query it before relying on conversational memory for past decisions, conventions, or architecture.

## Done Checklist

Before closing a task:

1. Run relevant verification or explain why it was not run.
2. Update `docs/activity-log.md` for meaningful work.
3. Update `docs/decisions.md` for architectural or tooling decisions.
4. Update `docs/bug-ledger.md` for fixed or newly discovered bugs.
5. Update `docs/api-contract.md` for API contract changes.
6. Update `docs/experiments.md` for experiment hypotheses, scenarios, or results.
7. Update `CHANGELOG.md` for meaningful project-visible changes.
8. Summarize changed files, verification, and residual risks.

## Focus Rules

- Build the microscope before the mind: tracing comes before cognitive modules.
- Keep the model-facing tool surface small: the active contract is the single
  `mind_shell(command, intent)` tool. Legacy `/mind/*` dispatch remains an
  internal/debug/maintenance implementation boundary, not a second model tool.
- Prefer small, testable, observable changes.
- Default task verification to focused deterministic tests plus direct Codex
  use of the affected tool or surface when applicable. Do not launch complete,
  repeated, or cross-branch live Scarlet evaluations unless the owner
  explicitly requests them for the current task.
- Do not add large abstractions without an experiment or a current need.
- Work only inside the declared scope. Fix only issues directly caused by the
  current implementation; report unrelated or pre-existing problems before
  changing them.
- Treat prompts, schemas, traces, and docs as part of the system behavior.
- No silent mutation of cognitive state: state changes need traces or events.
- Never commit real API keys or secrets.
- Keep commits mapped to `CHANGELOG.md`, roadmap phase, experiment, ADR, or issue.
- Use the repository-local Scarlet commit identity for agent-authored commits when configured.

## Current Project Direction

Immediate milestone:

```txt
A local chat agent using MiniMax M3 where every turn is inspectable, reproducible,
and ready for cognitive API experiments.
```

Initial implementation order:

```txt
docs -> FastAPI backend -> MiniMax provider -> SQLite trace store -> chat endpoints
-> minimal debug UI -> first baseline trace experiment -> mind_api
```

## Commit And Release Memory

Read `docs/release-process.md` before release, branch, commit, or changelog work.

Read `docs/development-process.md` before versioned implementation work.

Meaningful commits should use `.gitmessage` format and should not leave `CHANGELOG.md` behind.

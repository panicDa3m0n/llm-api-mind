# Scarlet Engineering Operating Guide

The human owner sets direction and approves scope. Codex is the implementation
engineer. This file is the always-read operational contract for this workspace.

## Evidence Before Change

1. Inspect the worktree and current branch before every repository change.
2. Declare: area, branch, type (`Fix`, `Implementazione`, or `Major release`),
   target version, scope, out of scope, verification, and documentation owner.
3. Read `docs/project-documentation.md`, then only the current contract and
   code that own the requested behavior. Use `docs/project-state.md` for the
   current integrated map.
4. Read `docs/technology-map.md` before introducing, activating, replacing, or
   retiring a technical dependency, provider, store, or custom subsystem.
5. Historical ledgers, checkpoints, completed plans, and evaluations are
   evidence to query for a specific question. Do not read them wholesale or
   treat them as present-tense policy.
6. Load the relevant repository skill under `.agents/skills/` for substantial
   stewardship, cognitive changes, debugging, evaluation, or release work.

Source priority is:

```txt
current executable code, schemas, tests, direct runtime evidence
> current owning contract and AGENTS.md
> current project/branch state
> decisions and historical evidence
> skills
> conversational recollection
```

When sources disagree, report the mismatch and correct the owning
documentation or seek an owner decision. Never silently choose a convenient
description.

## Capability Integrity

Do not call a component a working Scarlet capability merely because code,
configuration, a table, or an experiment exists.

- **Active**: the supported runtime path uses it and current direct evidence
  confirms the stated behavior.
- **Experimental**: it is intentionally available for bounded research or an
  external adapter; it does not define Core behavior.
- **Shadow**: it records or compares a candidate path without deciding normal
  cognition. It must say so in code-facing documentation.
- **Historical/deprecated**: retained for provenance, migration, rollback, or
  research only; never present it as an active route.

Every research or shadow path needs a visible owner, purpose, evidence, and a
future decision to promote, retire, or keep it explicitly bounded. Do not add
silent half-integrations, fake fallbacks, or undocumented compatibility paths.

## Scope And Change Discipline

- Analysis means analysis: do not fix, refactor, deploy, mutate data, or alter
  configuration unless the owner explicitly authorizes it.
- Implement the smallest approved slice. Report unrelated defects; do not fold
  them into the current change.
- Preserve the Core boundary: native provider behavior is authoritative;
  Product UI renders Core rather than becoming a second agent; the GPT bridge
  is an experimental adapter and cannot redefine native cognition.
- The model-facing cognitive surface is `mind_shell(command, intent)`.
  Internal HTTP endpoints, traces, maintenance, and UI projections do not
  become additional model tools by implication.
- Semantic judgment needs Scarlet, an LLM, or a validated semantic component.
  Deterministic code owns lifecycle, ids, timestamps, limits, persistence,
  authorization, and receipts. Do not use lexical triggers or hand scores as
  hidden semantic authority.
- Canonical history and source provenance are never replaced by derived model
  context, summaries, or compaction artifacts.
- Never move production data, secrets, or runtime `data/` files with code.

## Verification And Documentation

Run the smallest relevant deterministic check and directly inspect the changed
surface when possible. Full live Scarlet evaluations require explicit owner
authorization. A metric, test counter, or model claim alone is not a behavioral
conclusion.

Update only the document that owns new current truth:

- a current contract or `project-state` when implemented behavior changes;
- `decisions` for an accepted architectural/process decision;
- `bug-ledger` for a defect or residual risk;
- `experiments` for a hypothesis or result;
- `activity-log` for a meaningful completed intervention;
- `CHANGELOG.md` only for a released/project-visible product change.

Do not create a new Markdown register for a one-off note. Preserve historical
records; mark their status and successor instead of rewriting history. Before
closing, state changed files, verification, and residual risk. Read
`docs/development-process.md` for the detailed workflow and
`docs/release-process.md` before a branch, commit, or release operation.

# Development Process

Last updated: 2026-07-13
Current app version: V1.29.1
Process baseline: V1.0.1
Status: accepted

This document defines the engineering process from V1.0.1 onward.

The goal is to keep Scarlet's development organized as the project grows across
many agentic branches. Every change must have a declared scope, an explicit
version impact, focused implementation, targeted verification, and traceable
documentation.

## 1. Version Policy

The app is considered V1.0.1 as of 2026-05-25.

Version changes are decided before implementation:

```txt
Fix             -> patch increment: 0.0.X
Implementazione -> minor increment: 0.X.0
Major release   -> major increment: X.0.0
```

Examples:

- V1.0.1 -> V1.0.2 for a direct bug fix.
- V1.0.1 -> V1.1.0 for a normal feature or structural implementation.
- V1.0.1 -> V2.0.0 only for a very large release-grade shift.

The version must be updated only after implementation and verification are
acceptable.

## 2. Required Pre-Work Declaration

Before coding or documentation edits, declare:

```txt
Area:
Branch:
Type: Fix | Implementazione | Major release
Target version:
Scope:
Out of scope:
Verification:
Docs to update:
```

For small conversational answers or pure analysis, a full declaration is not
needed. For any repository change, it is mandatory.

## 3. Scope Discipline

Implement only the declared area.

Do not opportunistically fix unrelated issues found during implementation or
testing. If a new issue appears:

- if it is directly caused by the current change, fix it inside the same slice;
- if it was already present or belongs to another branch/scope, report it and
  discuss the next move before changing code.

This rule is especially important for LLM behavior bugs, natural-language
retrieval issues, and prompt changes. Avoid quick hardcoded patches unless the
root cause and blast radius are understood.

## 4. Testing Policy

Verification must match the change:

- backend behavior: run relevant pytest targets, then full suite when risk is
  broad;
- frontend behavior: run production build and, when tools are available, a
  visual/browser smoke;
- prompt/cognitive behavior: run at least one direct Scarlet test when the
  change should affect the agent's behavior;
- documentation-only changes: run `git diff --check` and inspect the created
  docs.

If a test cannot be run, record why in the final answer and in the activity log
when the work is meaningful.

## 5. Commit Policy

After a verified implementation:

1. update the app version where applicable;
2. update `CHANGELOG.md`;
3. update branch and project documentation;
4. make a focused commit with the release-process message format.

Commits should be high-level, mapped to the branch or roadmap area, and should
not mix unrelated fixes.

## 6. Major-Procedure Regression Gate

Before a broad reorganization, architectural implementation, major branch
transition, or shared-runtime change, establish a preliminary regression
baseline before changing the affected code.

The procedure is:

1. inspect a real, immutable laboratory DB and select sourceable references;
2. document the source hash, inventory, IDs, expected lifecycle state, and
   exact acceptance criteria in a versioned suite document;
3. run the executable suite against a disposable copy of that exact source DB;
4. record the preliminary report before the rework begins;
5. make only the declared rework changes;
6. rerun the identical suite from a freshly copied DB; and
7. accept the procedure only when results are equal or better, with no hidden
   regressions.

The current baseline is documented in:

```txt
docs/preliminary-regression-suite.md
```

This gate complements pytest and live Scarlet testing. It is a repeatable
whole-system comparison, not a substitute for either deterministic unit
contracts or human evaluation of model behavior.

## 7. Database Boundary

Before a major procedure, evaluator run, deployment, or commit that could
touch persistence, read `docs/database-topology.md`. The database role is part
of the procedure's starting condition, not an implementation detail.

- Test and preliminary procedures must name an ignored disposable target and
  never use a production or mutable laboratory path as that target.
- A new deployment must run the read-only database preflight with expected
  role `production` before restart, after a remote backup.
- Code transfer must exclude runtime `data/` and remote `.env` files.
- Run `python scripts/check_database_boundary.py --staged` before a commit.
  An intentional LFS laboratory-data release needs separate review and the
  explicit override documented by that script.

## 8. Branch Mapping

The active agentic branches are documented in `docs/branches/`.

Technical infrastructure such as tests, traces, events, schema, provider
adapters, and UI are not themselves agentic branches. They support one or more
branches. The branch document should explain why the infrastructure matters to
Scarlet's actual behavior.

## 9. Current Baseline

The current V1.29.1 baseline includes:

- local MiniMax-based Scarlet runtime;
- persistent sessions, traces, events, semantic memories, atomic facts, and
  episodic summaries;
- `mind_shell` as the single model-facing API Mind command tool, with legacy
  endpoint dispatch retained for backend/debug compatibility;
- runtime context blocks for session continuity, message perception, and
  Scarlet state;
- dashboard settings for active profile, privacy scope, locale, language, and
  timezone;
- Tailwind dashboard with chat, sessions, agent stream, memory, profile, and
  settings.
- Codex test database isolation through startup-level `CODEX_TEST`, used for
  evaluator experiments that must exercise real endpoints without mutating the
  production/laboratory Scarlet DB.
- Database-role validation and a side-effect-free `app.main` factory, so tests
  and evaluation imports do not silently initialize a configured runtime DB.

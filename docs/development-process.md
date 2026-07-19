# Development Process

Last updated: 2026-07-18
Current app target: V1.52.0; V1.50.1 remains deployed and release-accepted
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

### 3.1 Linear Issue Workflow

When work is tracked in Linear, complete one issue before starting the next:

1. inspect the issue, code, current evidence, and relevant documentation;
2. present the intended code surface, scope, exclusions, and verification to
   the owner;
3. wait for explicit owner approval or resolve the resulting design discussion;
4. move the issue to active work and implement only the approved slice;
5. verify code, behavior, documentation, and database boundaries;
6. record evidence and residual findings in Linear, then close the issue only
   when its acceptance criteria are genuinely satisfied.

Discoveries may be added to future issues while the current one is active, but
they do not become implementation scope silently.

## 4. Testing Policy

Ordinary task verification must stay proportionate. By default, Codex runs the
smallest relevant deterministic test or smoke check and directly exercises the
affected tool or surface when that can confirm real operation. A task does not
automatically trigger a complete live evaluation period merely because a
versioned suite exists.

Default verification:

- backend behavior: run relevant focused pytest targets or a direct smoke;
- frontend behavior: run production build and, when tools are available, a
  visual/browser smoke;
- shell, API Mind, or cognitive tools: Codex directly invokes the affected
  command/tool on an isolated or approved boundary and inspects its structured
  result;
- prompt or agent behavior: use a small, task-specific direct probe only when
  it is useful and inexpensive;
- documentation-only changes: run `git diff --check` and inspect the created
  docs.

Every behavioral probe requires direct qualitative inspection by Codex. Read
the actual prompt, starting state, model actions, tool results, traces, final
answer, and follow-up effect. Numeric scores, latency, token counts, and
deterministic pass flags are diagnostic evidence, but they cannot by themselves
judge cognitive choice or natural-language quality. Record a reasoned judgment
and reject a run as evidence when its starting conditions do not match the
declared scenario.

Complete or advanced live evaluation requires an explicit owner instruction
for the current task. This includes the repeated natural cross-branch suite,
large multi-scenario Scarlet batteries, long behavioral sessions, and broad
pre/post live-model campaigns. When explicitly authorized, use the frozen DB,
four-layer judgment, and evidence rules defined below. Existing deterministic
CI gates may still run automatically because they do not call the live model.

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
contracts or reasoned human/LLM-as-human evaluation of model behavior.

The natural cross-branch suite complements the deterministic gate and is run
only during an owner-authorized evaluation period. It may
automatically compare exact commands, traces, events, and persisted state, but
must never classify natural-language quality through exact strings or a single
numeric score. Different answers require reasoned review against the declared
scenario rubric.

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

The current V1.50.1 baseline consolidates the V1.44.0 through V1.50.0 work.
V1.50.0 reached the VPS but was not release-accepted because focused native
smoke reproduced two final-marker omissions; V1.50.1 adds the bounded semantic
finality recovery and passed the protected release boundary at merge
`676e560`. The consolidated
line includes:

- local MiniMax-based Scarlet runtime;
- persistent sessions, traces, events, semantic memories, atomic facts, and
  episodic summaries;
- `mind_shell` as the single model-facing API Mind command tool, with legacy
  endpoint dispatch retained for backend/debug compatibility;
- three mandatory external GPT Actions with no MCP connector or query-string
  authentication surface;
- cohesive typed provider-history, response/event serialization, and
  context-accounting support modules behind the unchanged native chat facade;
- one typed native-turn lifecycle owner behind the thin native HTTP facade;
- one typed automatic-memory retrieval owner behind the stable context facade;
- dedicated memory read, write, lifecycle, proposal, and relation-evidence
  owners behind the stable memory facade;
- dedicated maintenance scheduling, summary/history, and memory-review owners
  behind the stable maintenance facade;
- runtime context blocks for session continuity, message perception, and
  Scarlet state;
- dashboard settings for active profile, privacy scope, locale, language, and
  timezone;
- Tailwind dashboard with chat, sessions, agent stream, memory, profile, and
  settings.
- traceable per-channel model-input accounting, active chronological
  compaction planning with token-based complete-turn source maps and an
  agent-mode registry/router for automatic context;
- versioned four-layer behavioral scenario/run contracts for direct Scarlet
  validation;
- a repeatable 12-scenario, 8-group natural MiniMax suite with frozen starting
  references, independent repetitions, persisted evidence, project-informed
  LLM-as-human judgments, and a comparator that auto-fails only objective
  technical regressions;
- Codex test database isolation through startup-level `CODEX_TEST`, used for
  evaluator experiments that must exercise real endpoints without mutating the
  production/laboratory Scarlet DB.
- Database-role validation and a side-effect-free `app.main` factory, so tests
  and evaluation imports do not silently initialize a configured runtime DB.
- executable shell-organ conformance across registry, help, parser, handlers,
  persistence, pagination, negative paths, and model-facing presentation.
- a user-facing completion invariant with one bounded thinking-only recovery,
  explicit failed-turn exhaustion, and no promotion of private thinking into
  public or cognitive state.
- ordered mode-routing receipts that distinguish eligibility, actual delivery,
  and shadow `would_exclude` decisions for every automatic block.
- a shared native/GPT answer-obligation contract with traced hard, warning,
  and advisory constraints, one correction, and semantic judgment only on
  evidence-bearing turns.
- a complementary model-facing memory gate that verifies rich selection, V2
  delivery, provider input, completed turns, and an incomplete-turn negative
  control without rewriting the historical frozen V1 suite.
- blocking Ruff checks for objective Python defects, an incremental mypy gate,
  a measured full-suite coverage floor, deterministic documentation integrity,
  and a GitHub Actions workflow that runs these checks with the frontend build.

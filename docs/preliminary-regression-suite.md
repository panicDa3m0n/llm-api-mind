# Preliminary Regression Suite

Status: active from 2026-07-10

This is the mandatory pre/post comparison gate for major procedures: broad
reorganizations, architectural changes, branch transitions that alter shared
runtime behavior, and future large implementations. It is not required for a
small isolated fix unless that fix changes a surface covered by this suite.

The suite evaluates assembled backend behavior on a frozen, real laboratory
database. It is deliberately different from pytest: pytest protects individual
contracts, while this runner protects the interaction among storage, runtime
context, shell, organs, traces, and external bridge transport.

## Fixed Baseline

Suite identifier:

```txt
preliminary-regression-v1
```

Published source identity:

```txt
Git LFS SHA-256: 827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5
Source inventory: 34 memories, 25 memory facts, 155 sessions, 567 messages,
0 focus records, 0 intention records, 0 affect states.
```

The source is the last published `backend/data/app.db` LFS object, not the
mutable worktree database. The current worktree `app.db` may contain later
live experiments and must never silently replace this baseline.

The runner makes two ignored local copies:

```txt
backend/data/preliminary-rework-v1.db      immutable source copy
backend/data/preliminary-rework-v1-run.db  disposable run copy
```

Every execution recreates the disposable run copy from the immutable source.
The production/laboratory database and immutable source are never written by a
test. The result report is also ignored and stored below
`backend/app/evals/runs/`.

The runner declares `DATABASE_ROLE=preliminary` internally, requires
`CODEX_TEST=true`, and rejects an unmarked target path. Importing its
`create_app` factory no longer initializes the developer's configured runtime
database before those explicit settings are applied.

## Real References

These references are validated before any test-created state exists. They are
project-level rather than personal memories, and test both active/deprecated
lifecycle state and semantic-to-episodic provenance.

| Label | Memory ID | Fact ID | Source session | Required state |
|---|---|---|---|---|
| Active Zero-Luce protocol | `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` | `fact_75db0c43231047c0bf4e66d6c5ba2c3a` | `ses_24fbc3a0722d4010b7bde8f74496ef69` | `active`, four ordered blocks including Rischio and Prossima azione |
| Deprecated Zero-Luce predecessor | `mem_abed5590f91b4eb8aa93d1103db024de` | `fact_f35cda893b584765a25cffdfc2ae30d8` | `ses_421dd143a25840adb317ef2afd2c2e9c` | `deprecated`, historical three-block variant |
| Semantic-to-episodic decision | `mem_06ef7093f3e74f099c77d6f356f67d26` | `fact_0f96f4c04c654d178e64195b5a81e239` | `ses_8f9145b9ca5a4aa78534936dac03a8d5` | `active`, memory points to source-session recall |

Test-created IDs, such as a temporary lifecycle memory, focus, intention,
affect state, session, turn, and trace, are intentionally generated on every
run and recorded in that run's JSON report. They must not be hardcoded because
the initial state is identical but identifiers are runtime provenance.

## Execution

First prepare the frozen local copy from the exact published LFS object. On a
machine with Git LFS installed, make sure `backend/data/app.db` has been
smudged for the published revision, then run:

```bash
cd backend
.venv/bin/python app/evals/preliminary_regression.py --prepare-baseline
```

This command rejects a source whose SHA-256 is not the published baseline. In
the current development machine, where Git LFS itself is unavailable but the
object is present locally, the equivalent one-time command is:

```bash
cd backend
.venv/bin/python app/evals/preliminary_regression.py \
  --source-db ../.git/lfs/objects/82/7b/827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5 \
  --prepare-baseline
```

Run the gate before and after a major procedure:

```bash
cd backend
.venv/bin/python app/evals/preliminary_regression.py
```

The process exits non-zero if any case fails. A report with the source hash,
actual runtime IDs, selected memories, trace IDs, bridge IDs, and case details
is written to `backend/app/evals/runs/<timestamp>_preliminary-regression-v1/`.

## Cases And Acceptance

| Case | Direct system path | Expected result |
|---|---|---|
| `source_reference_integrity` | SQLite through current migrations | Exact inventory and all three real references/facts/session links exist with their declared lifecycle state. |
| `automatic_memory_retrieval` | Real streaming chat runtime with natural Zero-Luce wording | Runtime `memory_context.selected` contains the active protocol and excludes the deprecated predecessor. |
| `manual_shell_memory_session_fact_navigation` | `mind_shell`: help, search, facts, open, graph, session open | Shell retrieves the active real memory/fact, exposes its provenance, and opens its real source session. |
| `semantic_memory_lifecycle` | `mind_shell`: write, search, deprecate | A temporary memory is stored, returned by search, then lifecycle-closed in the isolated DB. |
| `focus_and_volition_lifecycle` | `mind_shell`: focus set/read/resolve and volition create/read/resolve | Both organs create, expose, and close traceable profile-scoped state. |
| `affect_runtime_and_shell_read` | Natural frustrated message through chat, then `affect read` | Runtime emits an `affective_context` with `frustration`; shell reads the same state and confirms read-only policy. |
| `metacognition_shell_contract` | `metacognition step` through shell with controlled provider | Provider path runs, trace is stored, and recommended `help` is recognized as an available shell command. |
| `internal_maintenance_boundary` | Runtime capability packet plus `help memory` | `memory.facts.backfill` is `internal_maintenance_only` and absent from normal model-facing shell help. |
| `gpt_bridge_lifecycle` | `/gpt/bootstrap` -> `/gpt/action` -> `/gpt/finalize` | One session/turn carries a successful shell action and returns the exact finalized answer. |

The runner uses a deterministic provider for controlled chat response and
metacognition JSON. This makes the expected contract repeatable; it does not
claim to certify Scarlet's free-form reasoning, relationship, or model-tool
choice. Those remain separate live human evaluations with MiniMax M3.

## Relation To The Natural Behavioral Suite

The 9-case preliminary suite verifies assembled deterministic contracts with a
controlled provider. V1.34.0 adds a second, non-substitutable gate:
`app.evals.behavioral_suite` runs natural human prompts with real MiniMax M3 on
fresh copies of the same frozen source.

The behavioral runner checks objective runtime evidence automatically, then
requires reasoned judgment for cognitive choice, answer quality, and
longitudinal effect. Natural wording is never accepted or rejected through
string comparison alone. See
`docs/evaluations/v1.34-natural-behavioral-suite.md`.

## Comparison Rule

The initial result was recorded on 2026-07-10 as `9/9` in
`20260710_141950_preliminary-regression-v1`. The first V1.26.0 organization
rework was then compared with the same source and again passed `9/9` in
`20260710_143138_preliminary-regression-v1`.

The V1.27.0 database-boundary rework passed the unchanged suite `9/9` in
`20260710_151853_preliminary-regression-v1`, confirming that role validation
and the ASGI factory split did not alter the assembled cognitive runtime.

The V1.28.0 repository-domain split passed the unchanged suite `9/9` in
`20260710_152411_preliminary-regression-v1`, confirming that the stable
repository facade preserved session, memory, organ, trace, and bridge behavior.

The V1.29.0 canonical context implementation and the V1.29.1 integrated
documentation/code audit both passed the unchanged suite `9/9`; the latest
V1.30.0 context-accounting/agent-mode implementation also passed `9/9`; the
latest recorded run is `20260713_163648_preliminary-regression-v1`. This
confirms the frozen assembled contracts, not free-form provider behavior or
the semantic quality of every branch.

SCA-10 revalidated the unchanged V1.42 planning baseline at 9/9 in
`20260718_162024_preliminary-regression-v1`, then passed the identical
post-documentation gate 9/9 in
`20260718_162350_preliminary-regression-v1`. No runtime code changed in the
planning issue; every executable rework child must record its own fresh
pre/post pair instead of treating this planning run as permanent approval.

SCA-34 established its own V1.43 pre-change baseline at 9/9 in
`20260718_174427_preliminary-regression-v1`. After extracting provider-history,
serialization, and accounting support from the native chat router, the
identical post-change gate passed 9/9 in
`20260718_175231_preliminary-regression-v1`.

SCA-33 established its V1.44 pre-change baseline at 9/9 in
`20260718_181621_preliminary-regression-v1`. After extracting shared native
sync/stream orchestration and fixing stream model-context trace linkage, the
identical post-change gate passed 9/9 in
`20260718_183109_preliminary-regression-v1`.

SCA-35 established its V1.45 pre-change baseline at 9/9 in
`20260718_184350_preliminary-regression-v1`. After extracting automatic memory
retrieval from runtime packet assembly, the identical post-change gate passed
9/9 in `20260718_184927_preliminary-regression-v1` with the same active memory,
33 candidates, and block types. Direct inspection showed that this historical
case does not assert V2 model-facing delivery when source-message provenance is
missing; BUG-0093/SCA-43 will add a complementary versioned case without
rewriting V1.

A post-rework change is admissible only when all of the following hold:

1. the source SHA-256 and the three real references are unchanged;
2. the same suite version runs on a fresh disposable DB copy;
3. every required case passes, or a changed expectation is backed by a new
   documented decision, versioned suite, and explicit owner acceptance;
4. no regression is hidden by editing the old case after observing a failure.

When a new architecture makes this suite insufficient, create a new
`preliminary-regression-vN` alongside it. Keep the previous suite runnable for
its declared baseline instead of rewriting history.

# Quality Gates

Last updated: 2026-07-19
App baseline: V1.50.1 deployed and release-accepted
Status: active incremental baseline

This document defines the first automated engineering-quality baseline for API
Mind. The gate is intentionally incremental: it blocks new objective defects
without hiding the broader typing and coverage work that still exists.

## Local Commands

Install the development dependencies:

```bash
cd backend
.venv/bin/python -m pip install -e '.[dev]'
```

Run the same checks used by CI:

```bash
cd backend
.venv/bin/python -m ruff check app tests ../scripts
.venv/bin/python -m mypy
.venv/bin/python -m pytest -q --cov=app --cov-report=term

cd ..
backend/.venv/bin/python scripts/check_documentation.py
npm --prefix frontend run build
```

## Ruff Baseline

The blocking rules are `E4`, `E7`, `E9`, and `F`. They catch malformed import
structure, syntax errors, undefined names, unused imports, and dead local
assignments across backend code, tests, and repository scripts.

Import sorting (`I`) is deliberately not active yet. The first measurement
found 47 files requiring mechanical import reordering. Enabling it in this
release would create unrelated churn; it should be introduced as a separate
reviewed cleanup.

## Mypy Baseline

The blocking mypy gate covers twenty-five high-value modules that currently pass
without suppressing their own errors:

- native chat provider-history transformations;
- native chat response/event serialization;
- native chat context-accounting persistence and request statistics;
- shared native sync/stream turn orchestration and completion;
- automatic memory candidate retrieval, classification, and final reranking;
- manual memory read/search/facts/graph, mutation/lifecycle/proposal/relation
  owners, and shared memory contracts;
- runtime configuration;
- agent modes;
- shell command registry;
- preserved-context field projection;
- canonical V2 context compilation;
- final memory reranking;
- context accounting;
- answer-obligation compilation and semantic verdict parsing;
- chronological source mapping and shadow partition planning;
- maintenance scheduling/dispatch, summary/history execution, memory review,
  and shared job contracts;
- database ownership boundaries.

Imports are treated as external to this first slice so SQLModel repository
typing does not make a small clean module inherit unrelated errors. The full
application measurement remains explicit and non-blocking:

```bash
cd backend
.venv/bin/python -m mypy app \
  --ignore-missing-imports \
  --show-error-codes \
  --no-error-summary
```

The V1.33.0 baseline is 216 errors across 23 files. Most are SQLModel column
typing and dynamic payload narrowing. Future reworks must reduce this count or
expand the blocking file list; they must not add broad `ignore_errors`
sections to make the number disappear.

## Coverage Baseline

The complete backend suite measured 79.998% statement coverage on V1.33.0:
8,195 of 10,244 statements. The initial blocking threshold is 79.9%. This
prevents an immediate project-wide regression while allowing coverage to grow
module by module.

V1.34.0 passes 182 tests at 80.19%. The behavioral evaluator support added in
this release is exercised directly: objective evidence is at 93%, frozen DB
guards at 87%, and the live-suite runner at 65% without excluding evaluator
entry points from the denominator.

V1.36.1 passes 198 tests at 80.22%. The thinking-only completion policy adds
provider recovery/exhaustion coverage plus synchronous and streaming API
guards without lowering the project floor.

V1.37.0 passes 207 tests at 80.21%. The frozen reranker evaluator is included
at 79% module coverage; it is not omitted from the project denominator.

V1.38.0 passes 209 tests at 80.45%. Historical provenance maintenance adds
94%-covered classification and guarded mutation logic; the unchanged frozen
preliminary suite passes 9/9.

V1.39.0 passes 216 tests at 80.69%. Active history routing is covered across
synchronous and streaming turns, recursive/idempotent maintenance, canonical
fallback, source-id sanitation, and post-compaction scheduling. The new history
repository is at 94%, the active runtime router at 86%, and the partition
planner at 88% module coverage.

V1.40.0 passes 219 tests at 80.89%. The behavioral evaluator now covers safe
group runtime receipts and structured organ evidence, while explicit
frustration-to-relief reappraisal has a direct persisted-state regression. The
unchanged frozen preliminary suite passes 9/9.

V1.41.0 passes 234 tests at 81.27%. The shared answer-obligation module is at
89% coverage; native chat at 91%; and the GPT bridge at 81%. Coverage includes
one-correction recovery, explicit exhaustion, semantic source/conflict/tool
evidence, non-blocking severities, streaming draft isolation, and GPT
409/422/503 policy.

V1.42.0 passes 241 tests at 81.29%. Agent mode routing is covered across every
registered tag and policy, duplicate/unregistered blocks, primitive ownership,
native/GPT parity, V2 exclusion, and shell availability; `agent_modes.py` is at
98%. The unchanged frozen preliminary suite passes 9/9 after its controlled
provider learned the distinct answer-validator output contract.

V1.43.0 passes 238 tests at 81.34%. Three removed tests belonged solely to the
retired MCP transport. The Actions bridge retains explicit lifecycle,
authentication, OpenAPI, answer-obligation, and shell coverage; query-only
authentication and `/mcp` availability now have negative regressions. The
unchanged frozen preliminary suite passes 9/9.

V1.44.0 passes 244 tests at 81.41%. The extracted provider-history,
serialization, and accounting modules are at 93%, 99%, and 97% coverage. Their
focused contracts preserve facade identity, canonical and reconstructed
history, tool exchanges, response/event projections, and accounting. The
unchanged frozen preliminary suite passes 9/9 before and after SCA-34.

V1.46.0 passes 244 tests at 81.50%. The typed native-turn service is at 90%
coverage and the new automatic retrieval owner is at 87%. The unchanged
frozen preliminary suite passes 9/9 before and after SCA-35; focused
context/retrieval contracts pass 101/101.

V1.47.0 passes 245 tests at 81.54%. The memory read owner is at 85% and shared
memory contracts are at 97%. Frozen pre/post gates pass 9/9 and focused
shell/memory/V2/structure contracts pass 63/63.

V1.48.0 passes 246 tests at 81.59%. Memory write, lifecycle, proposals, and
relations are at 88%, 60%, 75%, and 98%; shared contracts remain at 97%.
Frozen pre/post gates pass 9/9 and focused mutation/maintenance/facade
contracts pass 70/70. Direct shell, proposal, and natural Scarlet probes are
reviewed qualitatively in addition to deterministic pass counters.

V1.49.0 passes 247 tests at 81.63%. Maintenance history, memory review,
scheduler, shared contracts, and facade are at 74%, 79%, 76%, 100%, and 100%.
Frozen pre/post gates pass 9/9 and focused maintenance/history/facade contracts
pass 32/32. Direct compaction and MiniMax idle-maintenance results were read and
judged semantically in addition to their persisted technical evidence.

V1.49.1 passes 257 tests at 81.71%. Shared action-attempt obligations are
covered across equivalent and non-equivalent retries, recoverability, order,
capability checks, stale GPT manifests, native sync/stream, and the GPT Actions
lifecycle. Frozen pre/post gates pass 9/9. A direct MiniMax recovery was judged
from its actual actions, results, persistence, validation reasons, and answer.

V1.50.0 passes 263 tests at 81.86%. The complementary model-facing memory
evaluator is 90% covered and its six oracle contracts distinguish rich
selection, V2/provider delivery, completed turns, guarded repair, report
persistence, and the incomplete-turn negative control. The integrated V2 gate
passes 5/5 and the unchanged historical preliminary gate passes 9/9.

V1.50.1 adds the focused native-finality polarity gate. Answer-control and chat
contracts pass 46/46; with model-facing gate oracles the patch surface passes
52/52. A complete corrected markerless answer requires and passes explicit
semantic finality, while a second progress note and empty corrected draft
remain rejected with no assistant persistence. The complete backend passes 266
tests at 81.89%. Both remote Quality workflows passed. Protected deployment,
native model-facing memory/final-answer smoke, authenticated GPT bridge smoke,
post-smoke DB integrity, and frontend parity passed at merge `676e560`, so
V1.50.1 replaces the unaccepted V1.50.0 rollout as the stable baseline.

The configured blocking mypy slice passes across 25 files. A separate full-app
measurement reports 201 pre-existing errors across 24 files; this is explicit
non-blocking type debt, not evidence that the configured gate passed the whole
application.
Linear SCA-45 preserves incremental mypy expansion as a future engineering
annotation. It is not active backlog and does not block the closed V1.50.1
Core.

Evaluator entry points are included in the denominator and currently account
for a substantial uncovered surface. They are not omitted merely to inflate
the baseline.

## Documentation Integrity

`scripts/check_documentation.py` checks:

- local Markdown link targets;
- repository file references inside inline-code spans;
- uniqueness of canonical ADR, BUG, and EXP headings.

External URLs, secrets/runtime files, database paths, and explicitly
parametric references are not treated as repository artifacts. The script is
deterministic and does not access the network.

## GitHub Actions

`.github/workflows/quality.yml` runs the Ruff, mypy, documentation, backend
coverage, and frontend production-build gates on every push and pull request.
The workflow does not load production secrets, download the LFS laboratory
database, or mutate any runtime database.

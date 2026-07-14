# Quality Gates

Last updated: 2026-07-14
App baseline: V1.34.0
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

The blocking mypy gate covers six high-value modules that currently pass
without suppressing their own errors:

- runtime configuration;
- agent modes;
- shell command registry;
- final memory reranking;
- context accounting;
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

---
name: scarlet-e2e-evaluation
description: Design, run, and judge Scarlet end-to-end or behavioral evaluations. Use for frozen pre/post regression suites, natural human scenarios, memory and organ validation, direct live Scarlet probes, or release evidence that requires qualitative judgment. Do not launch a complete repeated live suite unless the owner explicitly requests it; ordinary changes use focused tests and bounded direct use.
---

# Scarlet E2E Evaluation

## Purpose

Measure whether Scarlet behaves correctly in realistic conditions without
forcing the answer, contaminating production data, or reducing natural
language behavior to brittle string and numeric comparators.

## Authoritative Sources

Read:

- `docs/development-process.md`
- `docs/database-topology.md`
- `docs/preliminary-regression-suite.md`
- `docs/behavioral-validation-framework.md`
- `docs/experiments.md`
- the affected branch document
- the relevant existing file under `docs/evaluations/`

Use current code, frozen fixture fingerprints, exact database references,
traces, and provider/model delivery as evidence.

## Evaluation Levels

### Focused Task Verification

Default for ordinary work:

- deterministic tests for the changed contract;
- direct Codex use of the affected tool or surface;
- one or a few bounded natural probes when model behavior matters;
- qualitative inspection of actual output.

### Complete Behavioral Period

Run only on explicit owner instruction:

- multiple natural scenarios;
- controlled same/new/cross-session conditions;
- frozen database or reproducible disposable copies;
- full evidence capture and LLM-as-human judging;
- meaningful time and provider cost accepted in advance.

### Major Pre/Post Gate

For a large rework, run the same frozen suite before and after on equivalent
database state. The change is admissible only when objective behavior does not
regress and qualitative behavior is similar or better. Never rewrite a frozen
historical suite after a failure; version a new suite.

## Scenario Design

For every scenario record:

- natural user message and why a human would plausibly say it;
- session condition: same session, new session, or linked sessions;
- frozen database fingerprint or fixture/copy identity;
- exact source ids known before the run, such as memory, session, message, or
  fact ids;
- expected evidence path and acceptable semantic outcomes;
- forbidden shortcuts or failure conditions;
- isolation and cleanup policy.

Do not phrase the user message as a technical command unless technical command
use is the behavior being tested. Do not reveal the expected memory or tool
path to Scarlet.

## Four-Layer Judgment

Judge every model-facing scenario across:

1. `technical execution`: correct context, command, result, trace, persistence,
   ordering, and finality;
2. `cognitive choice`: proportionate retrieval, source checking, uncertainty,
   correction, and tool choice;
3. `answer outcome`: relevance, factual grounding, naturalness, continuity,
   and compliance with the request;
4. `longitudinal effect`: correct durable memory/state change, no pollution,
   and useful future continuity.

Codex may act as the human/LLM judge because it knows the project and decisions,
but every verdict must cite observable evidence and a stable rubric. Record
ambiguity instead of manufacturing certainty.

## Comparator Rules

Use deterministic comparators only for objective facts: ids, counts, order,
timestamps, lifecycle states, database mutations, required tool calls, and
schema invariants.

Do not use keyword presence, exact answer strings, or an aggregate numeric
score as the final semantic judge. Model outputs can differ while remaining
equally correct. Read the response, actions, evidence, and downstream state.

## Data Safety

- Never write test data into the VPS production database.
- Treat `backend/data/app.db` as a mutable laboratory snapshot, not an
  automated fixture.
- Create a disposable test DB from an approved frozen source.
- Preserve source ids and fingerprints in the evaluation record.
- Reset to the same starting state between comparable runs.
- Never push an incidental database mutation with a code commit.

## Result Report

For each scenario report:

- starting conditions and references;
- what Scarlet received;
- actions and tool results;
- concise response summary and significant wording;
- persistence and trace outcome;
- four-layer verdict;
- classification of any failure;
- confidence and residual uncertainty.

End with system-level findings, regressions, improvements, and the next
smallest useful intervention. Do not hide actual outputs behind pass totals.

## Maintenance Contract

Update this skill and fix it when a real evaluation reveals a better scenario
design, invalid oracle, misleading comparator, missing evidence layer,
database risk, error, or newly verified judging practice. Add the smallest
evidence-backed prevention during the same task when it would stop the same
evaluation mistake recurring. Preserve frozen suites and historical reports
unchanged; version improvements prospectively. Owner corrections and direct
behavioral evidence override generic testing habits, and canonical
evaluation/process documents must stay aligned with this skill.

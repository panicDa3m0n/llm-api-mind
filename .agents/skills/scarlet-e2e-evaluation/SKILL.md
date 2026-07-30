---
name: scarlet-e2e-evaluation
description: Design, run, and judge Scarlet end-to-end or behavioral evaluations: frozen pre/post regression suites, natural human scenarios, memory and organ validation, direct live Scarlet probes, or release evidence requiring qualitative judgment. Do not launch a complete repeated live suite unless the owner explicitly requests it; ordinary changes use focused tests and bounded direct use.
---

# Scarlet E2E Evaluation

## Purpose

Produce credible behavioral evidence without confusing a test pass, token count,
or exact wording with human-quality cognition. Evaluation judges a declared
scenario against real starting conditions and inspected evidence.

## Authoritative Sources

Read `AGENTS.md`, `docs/preliminary-regression-suite.md` for major
procedures, `docs/behavioral-validation-framework.md` for live scenarios,
`docs/database-topology.md`, the owning current contract, and the exact
evaluation runner or affected code. Read prior evaluation reports only when
their frozen references or unresolved findings are directly relevant.

## When To Use It

Use a focused deterministic test and direct surface inspection by default.
Use this skill for a complete live suite, a frozen pre/post comparison, or a
natural behavioral claim only when the owner requested that level of evidence.

## Evaluation Design

1. Declare the question, behavior, acceptance criteria, and exclusions.
2. Establish the starting condition: code revision, provider/configuration,
   session state, sourceable IDs, database role, and any live-model limits.
3. Use an immutable source or disposable copy for persistence tests. Never use
   production as an evaluation target.
4. Write natural scenarios that a real person could plausibly say; avoid
   prompts designed only to trigger a desired implementation detail.
5. Separate technical expectations from behavioral judgments.
6. Capture prompt/context, model actions, tool results, traces, persisted
   state, final answer, and follow-up effect.
7. Judge the complete result directly. Deterministic comparators may fail
   objective contract regressions but cannot alone grade natural language.

## Evidence Rules

- A scenario is invalid when starting conditions, source data, model version,
  or configuration differ from the declared baseline.
- Inspect the actual model-visible context before attributing a behavior to
  retrieval or memory.
- Treat provider/model variance as a possible result, not a Core defect.
- Preserve failed and ambiguous runs; explain why they are weak evidence.
- Do not turn a qualitative evaluator note into an automatic semantic guard.
- Rerun the identical frozen gate after a major rework only when the owner
  asked for the procedure.

## Report

For each scenario record what happened, how it was run, evidence used,
technical outcome, qualitative judgment, and residual uncertainty. State what
the result proves and what it does not prove.

## Maintenance Contract

Update this skill when a verified evaluation, direct Scarlet use, owner
correction, or invalid comparison exposes a stronger reusable evaluation rule.
Update the owning evaluation contract first if the methodology changes. Keep
reports and raw evidence in their existing evaluation records, not in this
skill. Update this skill in the same scoped task when it prevents repetition,
then run the skill validator.

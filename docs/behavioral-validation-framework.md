# Behavioral Validation Framework

Last updated: 2026-07-13
Status: accepted V1 contract

This framework evaluates whether an API Mind capability changes Scarlet's
behavior usefully, not only whether an endpoint returns `200` or a shell parser
accepts a command. It complements pytest and the frozen preliminary regression
suite.

## Evaluation Unit

Every scenario is defined before execution with
`behavioral-scenario-v1` (`app.evals.behavioral_contracts`). It must contain:

- a named database role and immutable fingerprint;
- `read_only` or `disposable_copy` mutation policy;
- explicit memory/session/message/turn/state references inspected in advance;
- the session arrangement and dependencies on prior scenarios;
- one natural human prompt, without telling Scarlet which technical command to use;
- expected shell commands, traces, events, state, and forbidden mutations;
- semantic requirements and forbidden claims for the visible answer;
- at least one repetition and a rule describing independence between runs.

References are test oracles, not prompt hints. Scarlet does not receive IDs
unless the normal runtime packet or her own navigation exposes them.

## Four Layers

1. **Technical execution**: the command, handler, trace, event, and persistence
   contract worked.
2. **Cognitive choice**: Scarlet chose the appropriate capability at the right
   effort level, with a useful query or state transition.
3. **Answer outcome**: the final answer used the evidence correctly and was
   better for the human than an ungrounded answer.
4. **Longitudinal effect**: subsequent turns and sessions preserve the intended
   continuity without accidental writes, stale state, or source confusion.

An implementation is behaviorally accepted only when all four layers pass.
`inconclusive` is distinct from failure: it means the starting evidence,
provider behavior, or observation surface was insufficient to judge.

## Experimental Shape

Use paired conditions when a capability's contribution is uncertain:

- capability available and correctly populated;
- negative control with the relevant evidence absent, disabled, stale, or
  deliberately nonmatching;
- same natural prompt and equivalent session conditions;
- multiple independent runs because model choice is stochastic.

Record false positives as seriously as misses. A memory system that retrieves
something on every prompt is not better than one that misses occasionally.

For stateful sequences, declare whether turns belong to the same session,
continue a seeded session, or occur in separate sessions. Never combine results
from different starting states as if they were repetitions.

## Required Report

Each run records the DB fingerprint, session and turn IDs, exact response,
trace IDs, observed mutations, and one result for each layer. Aggregate reports
must include pass/fail/inconclusive counts and variation across repetitions.

The evaluator must summarize what Scarlet did, how she did it, what evidence
she used, and where the visible answer diverged from the technical result.
Raw traces remain the source for technical claims.

## Admission Gate

- Deterministic contract tests must pass first.
- Natural direct tests run only against a disposable copy or approved
  laboratory DB boundary.
- The same scenario definition is rerun before and after broad changes.
- A capability is not promoted to default merely because one successful answer
  appears convincing.
- Longitudinal or context-compaction changes require a sufficiently long and
  varied real session; synthetic token volume alone is not behavioral proof.

## First Application

EXP-0060 applied this contract iteratively to agent modes on independent
disposable DB copies. Technical success alone was insufficient: one run exposed
a shell mismatch, one omitted the required mode transition, and one persisted
the state while overclaiming autonomous execution. Acceptance came only after
the command, trace, persisted state, active/resumable distinction, and visible
answer agreed that `scouting` was posture without an autonomous runtime. See
`docs/experiments.md` and the V1.30 activity entry for the recorded evidence.

---
name: scarlet-runtime-debugging
description: Diagnose Scarlet runtime failures across provider, context, memory, shell, persistence, streaming, Product UI, Android, VPS, and GPT bridge. Use for stalls, missing live blocks, wrong or absent retrieval, repeated actions, incomplete turns, state disagreement, or behavior that may be model variance rather than a Core bug. Diagnose before fixing and do not use this skill to justify broad refactors.
---

# Scarlet Runtime Debugging

## Purpose

Find the failing layer from end-to-end evidence. Do not infer a Core defect
from a disappointing final answer, an evaluator score, or a UI symptom alone.

## Authoritative Sources

Read the contracts relevant to the symptom:

- `docs/core-runtime-contract.md`
- `docs/api-contract.md`
- `docs/block-registry.md`
- `docs/stream-v2-contract.md`
- `docs/database-topology.md`
- `docs/bug-ledger.md`
- `docs/branches/communication.md`
- the affected organ branch document

Inspect current provider code, runtime configuration, traces, persisted events,
and UI reducer/rendering code. Provider documentation is authoritative for
native stop, tool, usage, and stream semantics.

## Evidence Ladder

Follow the same turn through:

1. user request and session/turn identity;
2. automatic retrieval and rich runtime evidence;
3. exact V2 model projection;
4. provider request/history and streamed native blocks;
5. model stop reason and tool request;
6. shell validation, dispatch, result, and state mutation;
7. Core events and assistant persistence;
8. durable Stream V2 plus any connection-local live frame;
9. frontend transport, reducer identity, and rendered lifecycle;
10. external adapter translation when the GPT bridge is involved.

Use read-only production inspection by default. Work on a copied database for
any mutation or replay.

## Failure Classification

Assign one primary class before proposing a fix:

- `core_contract`: deterministic Core behavior violates its contract;
- `provider_protocol`: adapter mishandles documented native behavior;
- `model_choice`: valid evidence was delivered but the model chose poorly;
- `context_or_retrieval`: evidence selection or projection was wrong;
- `shell_or_persistence`: command, mutation, lifecycle, or receipt failed;
- `transport_or_ui`: Core emitted correctly but delivery or rendering failed;
- `external_adapter`: ChatGPT/GPT Actions host behavior differs from Core;
- `configuration_drift`: local, VPS, app, or provider configuration disagrees;
- `evaluation_error`: the expected result or judging method was invalid;
- `unknown`: evidence is incomplete; do not turn this into a confident fix.

## Debug Workflow

1. Reproduce the smallest natural symptom without altering production data.
2. Capture the session, turn, trace, event cursor, deployed commit, and runtime
   version.
3. Compare the first layer that is correct with the next layer that diverges.
4. Check ordering, stable identities, retries, duplicated persistence, and
   terminal boundaries.
5. Read actual payloads and text. Counters and statuses are navigation aids,
   not the conclusion.
6. Separate a reproducible defect from provider/model variability.
7. Record a bug with evidence, impact, layer, reproduction, and residual
   uncertainty.
8. Propose the smallest owning-layer fix. Do not compensate in the UI or
   prompt for a lower-layer defect.
9. Verify the fix at the failed boundary and one adjacent end-to-end path.

## Live Stream Checks

For a stalled or delayed Product Chat, verify separately:

- Core generation continues after client disconnect;
- transient live frames arrive before completion;
- durable V2 events remain replayable and cursor ordered;
- proxy and response headers do not buffer or transform the stream;
- Android uses browser streaming rather than a buffering native fetch patch;
- pending tool/validator states have a visible start and terminal result;
- hydration cannot overwrite a live turn; and
- replay reconciliation matures existing blocks instead of duplicating them.

## Reporting Format

Lead with verified findings ordered by severity. For each finding state:

- evidence and exact layer;
- expected versus observed behavior;
- whether it is Core, model variance, adapter, UI, configuration, or evaluator;
- reproduction confidence;
- proposed correction and verification; and
- remaining uncertainty.

If no defect is verified, say so and identify the missing evidence or residual
risk.

## Maintenance Contract

Update this skill and fix it after verified incidents, false diagnoses, provider
changes, streaming failures, deployment drift, new observability surfaces,
errors, or newly verified diagnostic solutions. Add a check only when it would
have shortened a real investigation or prevented a demonstrated error, so the
same failure is less likely to recur. Reflect contract changes in canonical
docs first. Keep incident evidence in `docs/bug-ledger.md` and
`docs/activity-log.md`; do not turn this skill into an incident archive.

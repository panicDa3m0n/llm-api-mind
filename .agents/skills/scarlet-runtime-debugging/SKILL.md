---
name: scarlet-runtime-debugging
description: Diagnose a Scarlet runtime symptom across provider, turn lifecycle, context, memory, shell, persistence, streaming, Product UI, Android, VPS, or GPT bridge. Use it for stalls, absent blocks, unexpected retrieval, repeated actions, incomplete turns, or state disagreement. Diagnose before fixing; do not use it to justify a broad refactor.
---

# Scarlet Runtime Debugging

## Purpose

Locate the failing layer from end-to-end evidence. A poor answer, a UI symptom,
or a score alone does not prove a Core defect.

## Authoritative Sources

Read `AGENTS.md`, `docs/core-runtime-contract.md`, the affected executable
path, and the smallest relevant API, stream, database, branch, or bug contract.
Use provider documentation for provider-native stops, tools, usage, and stream
semantics. Inspect actual configuration, traces, events, persisted rows, and
the UI reducer when that layer is involved.

## Evidence Ladder

For one concrete turn or operation, inspect in order:

1. request, session, turn, profile, and runtime mode;
2. source evidence and automatic context/retrieval selection;
3. exact model projection and provider request/history;
4. provider deltas, thinking, tool use, notes, stop reason, and retries;
5. shell command/result and persistence receipts;
6. persisted event/trace ordering and final session state; and
7. stream transport, replay/live frames, reducer state, and rendered block.

Classify the result as provider behavior, Core defect, adapter limitation,
configuration/deployment drift, UI rendering defect, data quality issue, or
unproven model variance. Keep the classification provisional until the
evidence reaches the suspected boundary.

## Debug Rules

- Preserve the original evidence. Do not clean up, replay against production,
  or mutate data merely to make a trace easier to read.
- Compare the same contract across native and adapter paths only after proving
  their inputs are equivalent.
- `shadow` evidence is diagnostic unless the active contract says otherwise.
- Inspect the actual model/context payload before blaming retrieval or prompt.
- An interrupted stream requires proof of transport loss, provider loss, or
  client reducer loss before a retry policy is changed.
- Report an unrelated weakness instead of fixing it opportunistically.

## Exit Criteria

Return the exact affected boundary, evidence used, what remains unknown,
reproduction scope, and the smallest safe next step. Make a fix only after the
owner approves it or it is explicitly inside the declared scope.

## Maintenance Contract

Update this skill when a verified incident, code path, direct trace review, or
owner correction reveals a missing diagnostic step or a safer recurring order.
Update an owning contract first if the runtime semantics changed. Do not turn
this skill into an incident archive; retain incident history in the bug ledger
or activity log. Update this skill in the same scoped task when it prevents
repetition, then run the skill validator.

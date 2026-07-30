---
name: scarlet-cognitive-change
description: Design or implement a verified change to Scarlet's cognitive behavior or model-facing runtime: memory, retrieval, context, compaction, prompts, MiniMax lifecycle, mind shell, organs, agent modes, autonomous cognition, or modules. Do not use for a presentation-only change or an unverified symptom that first needs diagnosis.
---

# Scarlet Cognitive Change

## Purpose

Change a cognitive behavior without mixing model judgment, deterministic
runtime, provider transport, external adapters, and UI presentation. Build the
evidence surface before claiming an organ works.

## Authoritative Sources

Read `AGENTS.md`, `docs/core-runtime-contract.md`, and the exact owning code.
Add `docs/api-contract.md`, `docs/block-registry.md`, `docs/stream-v2-contract.md`,
the relevant branch document, and `docs/database-topology.md` only when they
own the changed boundary. Query experiments, decisions, and bugs for the
specific prior evidence; do not use their history as a current contract.

## Ownership Test

| Owner | Responsibility |
|---|---|
| Scarlet/model | interpretation, intent, source-sensitive synthesis, semantic decision |
| Core | ids, lifecycle, limits, persistence, authorization, routing, receipts |
| Semantic component | embeddings, reranking, graph expansion, appraisal, compaction evidence |
| Provider adapter | documented message, tool, stop, retry, and usage protocol |
| UI | faithful rendering and local presentation state |
| External adapter | transport translation only |

Stop and resolve the contract if a field or decision has no clear owner.

## Change Workflow

1. State the observable behavior and collect the current code/trace baseline.
2. Follow the path from source evidence through selection, model projection,
   provider delivery, tool/result, persistence, and UI event.
3. Classify the change as context, retrieval, policy, provider, shell,
   persistence, maintenance, or presentation.
4. Reuse the current owner or facade; do not create a second equivalent path.
5. Keep automatic context compact and navigable. Rich diagnostics stay in
   trace/UI unless an approved contract promotes them.
6. Preserve canonical history; compaction and summaries are derived views.
7. Emit traceable evidence for meaningful selection and state mutation.

## Cognitive Guardrails

- Do not make keyword matching, string overlap, or hand-authored scores the
  final authority for semantic relevance, duplicates, conflicts, affect, or
  answer quality.
- Retrieval components provide evidence. Scarlet or an explicitly validated
  semantic component interprets it.
- Auxiliary models may propose from source-backed data but cannot impersonate
  Scarlet or mutate Scarlet-owned semantic state.
- Follow the selected provider's native protocol. For MiniMax, `max_tokens`
  continues, `tool_use` authorizes execution, and `end_turn` closes a native
  answer.
- GPT limitations cannot create a separate memory, context, or lifecycle
  architecture from native Scarlet.

## Verification Gate

Run focused deterministic tests, inspect the exact model-facing projection,
and inspect persistence/trace output for state changes. Directly exercise the
affected command, provider, or surface when useful, then judge Scarlet's
actual choice qualitatively. A full live suite requires owner authorization.

## Maintenance Contract

Update this skill when a verified cognitive change, provider result, direct
Scarlet probe, regression, or owner correction reveals a stronger recurring
invariant. Update the owning contract first when semantics changed, remove
obsolete advice, and keep experiments in their own records. Update this skill
in the same scoped task when it prevents the same error recurring, then run the
skill validator.

---
name: scarlet-cognitive-change
description: Design or implement changes to Scarlet's cognitive behavior and model-facing runtime. Use for memory, retrieval, context packs, history compaction, prompts, MiniMax lifecycle, mind_shell commands, focus, volition, affect, metacognition, agent modes, maintenance cognition, or agentic modules. Do not use for a presentation-only UI change or an unverified runtime symptom that still needs diagnosis.
---

# Scarlet Cognitive Change

## Purpose

Change a cognitive organ without confusing model behavior, deterministic
system behavior, adapter behavior, and UI presentation. Build the evidence
surface before claiming that the organ works.

## Authoritative Sources

Always consult:

- `docs/project-blueprint.md`
- `docs/core-runtime-contract.md`
- `docs/api-contract.md`
- `docs/block-registry.md`
- `docs/development-process.md`
- the relevant file under `docs/branches/`

Also read `docs/experiments.md`, `docs/bug-ledger.md`, provider documentation,
and the exact implementation/tests for the affected path. For context or
history work, include `docs/runtime-context-packs.md` and the current
compaction contract. For stream-visible behavior, include
`docs/stream-v2-contract.md`.

## Ownership Check

Classify every proposed field or action:

| Owner | Typical responsibilities |
|---|---|
| Model | semantic content, interpretation, intent, source-sensitive synthesis |
| Core deterministic | ids, timestamps, validation, lifecycle, routing, limits, persistence, authorization, receipts |
| Cognitive component | embedding, reranking, graph expansion, semantic review, compaction |
| Provider adapter | native message/tool protocol, stop reasons, usage, retryable transport |
| UI | faithful rendering, interaction, local presentation state |
| External adapter | transport translation only; no new cognitive semantics |

If ownership is ambiguous, stop implementation and resolve the contract first.

## Change Workflow

1. State the user-visible or cognitively observable behavior.
2. Record the current baseline from real code and focused evidence.
3. Trace the full path: source data, selection, model projection, provider
   delivery, model choice, tool result, persistence, trace, and UI event.
4. Decide whether the defect is policy, context, retrieval, provider protocol,
   shell contract, persistence, or presentation.
5. Preserve stable facades while improving the owning implementation.
6. Add traceable events for every cognitive state mutation or important
   selection decision.
7. Keep automatic model context compact and navigable. Model-facing packets
   contain usable hooks; rich diagnostics remain available to UI, trace, and
   evaluation.
8. Keep canonical transcripts append-only. Derived compaction may change model
   delivery but never erase exact source history.
9. Test objective contracts deterministically and inspect a bounded direct use
   of the affected surface when applicable.
10. Update API, block, branch, experiment, decision, bug, and changelog records
    according to ownership.

## Semantic Safety

- Do not make static string overlap or a hand-authored numeric score the final
  authority for semantic relevance, conflict, duplicate meaning, emotional
  interpretation, or behavioral quality.
- Embeddings, graph signals, and rerankers provide evidence. The LLM may still
  need to interpret the selected evidence.
- Auxiliary maintenance models may discover, summarize, and recommend
  source-backed memory proposals, but only Scarlet may accept, reject, mark a
  semantic duplicate, or supersede memory. Proposal availability is an
  attention candidate, never a forced decision.
- Preserve the distinction between source provenance and decision provenance:
  an accepted proposal keeps its original session/turn/message source while
  the later Scarlet decision receives its own trace.
- Do not solve a backend semantic defect only by adding stronger prompt text.
- Do not expose rich maintenance/debug payloads to Scarlet merely because the
  system has them.
- Do not call automatic context delivery a memory read unless the accepted
  memory-activity contract says it refreshes cognitive recency.
- Do not let a GPT host limitation create a different memory, context, or
  lifecycle architecture from native MiniMax.

## Provider And Shell Rules

- Follow the provider's documented native protocol. For MiniMax M3,
  `max_tokens` continues the response, `tool_use` authorizes tool execution,
  and `end_turn` closes the native answer.
- Preserve provider-exposed thinking as inspectable development evidence under
  the current policy; do not relabel it as public speech.
- Keep tool loops model-controlled and observable. Recovery must resume the
  same logical turn within the documented bound.
- Publish only commands that validate and execute through the same shell
  registry. Help output is executable contract, not marketing copy.
- Keep legacy endpoints internal even when tests call them directly.

## Verification Gate

The minimum proof normally includes:

- focused deterministic tests at the changed boundary;
- a check that exact model-facing delivery matches the intended packet;
- persistence and trace evidence for state changes;
- a direct shell/provider/surface probe when applicable; and
- qualitative inspection of Scarlet's actual choice and answer.

Run a complete cross-organ live suite only when the owner explicitly asks for
it.

## Maintenance Contract

Update this skill when a cognitive implementation, provider contract, direct
Scarlet probe, regression, or owner correction reveals a better invariant or
workflow. Prefer evidence from exact model delivery, traces, persisted state,
and provider-native results. Change canonical contracts first when semantics
or ownership change. Remove obsolete advice instead of accumulating
compatibility folklore, while preserving historical experiments and decisions
in their proper records.

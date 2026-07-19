# Cognitive API Roadmap

Status: Core V1 cognitive API baseline closed; extension remains experimental
Last updated: 2026-07-19
App baseline: V1.50.1

This document tracks the non-memory cognitive API work: schema discipline and
Scarlet's internal metacognition.

For the integrated cross-project status and priority ordering, see
`docs/project-state.md`. This file remains the cognitive-API-specific roadmap.

The current architectural decision is intentionally narrow:

```txt
one model-facing tool -> mind_shell(command, intent)
one metacognition command -> metacognition step
one underlying route -> POST /mind/metacognition/step
```

Do not add separate cognitive endpoints for claim validation, blackboard,
reflection, planning, or critique unless a future experiment proves the single
route/command is the wrong abstraction. Those functions belong inside the
single metacognition step result for now.

## 1. Principles

- Keep the model-facing API small.
- Keep model-facing command availability in shell help/registry, while keeping
  route availability in `GET /mind/schema` for internal/debug compatibility.
- Return exact usage through shell help or endpoint-local `usage_guide` when a
  recoverable call error occurs.
- Use one LLM-backed metacognition route as the experimental path.
- Make every metacognitive step traceable as `mind.metacognition.step`.
- Return structured outputs, not raw hidden reasoning.
- Evaluate behavior before extending the surface.

## 2. Schema Discipline

Implemented:

- `GET /mind/schema` returns:
  - `schema_version`;
  - `schema_digest`;
  - route catalog with method, path, status, and purpose;
  - schema policy.
- Recoverable implemented-route errors return `usage_guide` with local body
  schema, parameter descriptions, aliases, examples, and retry guidance.
- Chat runtime context includes compact `mind_shell` capability state derived
  from the command registry.
- Invalid top-level `mind_shell` commands return structured shell guidance.
- Unknown routes return schema metadata and implemented route summaries.

Current model-facing command registry version:

```txt
2026-07-13.mind-shell-command-registry-v2
```

This version also exposes the memory-side episodic recall routes. The
cognitive roadmap still keeps one metacognition route; session recall belongs
to memory architecture, not to a second metacognition path.
Runtime events are now backend-owned and therefore are not exposed as a
model-facing `/mind/events/emit` route.

V1.30.0 adds `mode` to the shell/route contract. It is an agent posture
surface, not another metacognitive route and not a background-process control.

## 3. Single Metacognition Route

Implemented:

```txt
POST /mind/metacognition/step
```

Purpose:

Scarlet sends a precise private prompt to a metacognitive reviewer LLM and
receives a structured result before answering.

Input includes:

- `mode`;
- `objective`;
- `focus_question`;
- `internal_prompt`;
- `known_evidence`;
- `uncertainties`;
- `draft_answer`;
- `previous_steps`.

The canonical input remains schema-driven, but the route tolerates observed
model aliases such as `prompt`, `goal`, and `context` so a useful metacognitive
call is not lost to a recoverable naming error.

Output includes:

- `review_summary`;
- `risks`;
- `claim_checks`;
- `missing_evidence`;
- `recommended_internal_actions`, backend-annotated with schema status so
  wrong methods or unknown routes are visible before Scarlet follows them;
- `should_continue`;
- `next_focus_question`;
- `public_summary`.

This route is the single place for critique, claim checking, temporary
workspace, reflection, and next-action planning during the current experiment.

## 4. Evaluation

Current scripted scenario:

```txt
backend/app/evals/scenarios/cognitive_api_metacognition_probe.json
```

It should verify:

- Scarlet inspects `help metacognition` or equivalent shell guidance for the
  current command shape when needed;
- Scarlet calls `metacognition step` through `mind_shell`;
- a `mind.metacognition.step` trace is persisted;
- Scarlet does not call removed parallel cognitive routes.

Future evidence annotations, to promote only through a dedicated issue:

- adaptive live conversation where the user asks naturally for a careful answer
  without naming the endpoint;
- comparison between similar turns with and without metacognition;
- analysis of whether the metacognitive review changes the final answer;
- latency/cost tracking.
- explicit check that recommended available shell actions were either executed
  or the final evidence level was degraded;
- branch-level comparison against direct reasoning without metacognition.

## 5. Extension Rule

Extend this system only if evidence shows the single metacognition route is
insufficient.

Allowed next improvements inside the same route:

- better reviewer prompt;
- stricter JSON repair/retry; first retry is implemented for malformed JSON;
- mode-specific output validation;
- richer trace summaries;
- optional second metacognitive step when `should_continue=true`.
- trace-only integration with future context-mode selection.

Not allowed without a new decision:

- `/mind/validation/claims`;
- `/mind/blackboard/*`;
- `/mind/reflection/after-turn`;
- `/mind/reflection/review`;
- multiple overlapping cognitive endpoints.

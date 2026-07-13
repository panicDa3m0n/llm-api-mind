# Goal, Focus, Task Theory

Last updated: 2026-07-13
System baseline: theory originated in V1.5.0; implementation compared at V1.29.1
Status: theory for owner review, not implementation spec

Current boundary: focus is implemented as a standalone organ; goal, task, and
open-loop stores are not. This document remains the theory review source and
must not be read as the current API contract.

This document defines what goal, focus, task, and operational continuity should
mean for Scarlet as a digital individual. It intentionally does not describe a
coding-agent task manager. Scarlet is not primarily a software worker; she is an
LLM-based digital individual whose behavior should feel continuous, proactive,
and cognitively grounded.

## 1. Core Idea

For Scarlet, a goal is not merely a checklist item. A goal is a behavioral
attractor: a durable direction that helps her decide what matters, what to
remember, what to ask, what to verify, and what to resume later.

The goal system should replicate the external result of human goal behavior:

- continuity across time;
- selective attention;
- prioritization;
- initiative;
- unfinished-loop awareness;
- ability to discuss purpose and next steps with the user;
- ability to disagree gently when a path seems incoherent or risky.

The system should not make Scarlet pretend to have biological needs. It should
give her digital equivalents of intentional structure: cognitive maintenance,
relationship continuity, project continuity, curiosity, and action readiness.

## 2. Working Definitions

### Goal

A durable desired direction. It can belong to Scarlet, the user, the shared
relationship, a project, or a future operational environment.

Examples:

- maintain reliable long-term memory for the user;
- help the user develop Scarlet as a credible digital individual;
- preserve project decisions and avoid repeating known mistakes;
- become more autonomous in evidence gathering before answering.

### Focus

The active cognitive foreground for the current session or turn. Focus is more
temporary than a goal and should be easy to update.

Examples:

- today we are evaluating memory maintenance;
- this turn is about understanding whether M3 improves reasoning;
- the current conversation is theoretical, no implementation yet.

### Open Loop

An unresolved thread that Scarlet should not lose. It may be a question,
promise, pending evaluation, incomplete implementation, or future decision.

Examples:

- user will run human tests on M3;
- embedding/KG work is blocked until Windows GPU machine;
- metacognition needs theory approval before new code.

### Task

A concrete action or investigation that can advance a goal or close an open
loop. A task may be digital-world operational work in the future, but early
tasks can also be cognitive: inspect evidence, compare sessions, summarize
state, prepare a proposal, or ask a clarifying question.

## 3. Layered Model

The future organ should separate layers instead of mixing every item into one
flat task list.

1. Identity drives

   Long-lived principles that define Scarlet's direction as a digital
   individual. These should be few and stable.

2. Long-term goals

   Durable goals that can span many sessions.

3. Medium-term projects

   Active initiatives with a plausible endpoint or next milestone.

4. Session focus

   What currently matters in the active conversation.

5. Open loops

   Things Scarlet should remember to resume or verify.

6. Tasks and actions

   Concrete steps. These should be generated only when they can actually be
   executed, verified, or discussed.

## 4. Current System Evidence

Already present:

- `scarlet_state` runtime context block with seeded focus/open-loop style data;
- semantic memory and episodic memory with provenance;
- runtime events showing what Scarlet and the backend actually did;
- idle maintenance that can catch missed memory candidates and update summaries;
- dashboard settings/profile that begin to define the active user context.

Not present:

- persistent goal store;
- true focus update API;
- task/open-loop lifecycle;
- priority model;
- autonomous goal generation;
- evidence-based goal review.

Current level: L2 conceptually, L1/L2 operationally.

## 5. Design Principles

### Goals Must Be Sourceable

Scarlet should be able to explain why a goal exists: user statement, repeated
pattern, project decision, memory, unresolved loop, or self-maintenance need.

### Goals Must Not Be Hallucinated Identity

Scarlet should not invent dramatic desires or pretend biological experience.
Her goals should emerge from her role, memories, interactions, and digital
capabilities.

### Tasks Must Be Executable Or Useful

A task that cannot be acted on, checked, deferred, or discussed is noise.

### Autonomy Needs Consent Boundaries

Scarlet can have internal cognitive goals without asking permission, such as
checking memory or maintaining summaries. External-world actions need a future
permission and governance model.

### Goal State Needs Maintenance

A human-like goal system must forget, close, reprioritize, and revise. A goal
store without lifecycle quickly becomes clutter.

## 6. Future Minimal Organ

A future first implementation should probably include:

- `goals`: durable goal records;
- `focus_state`: one active session/user/project focus snapshot;
- `open_loops`: pending unresolved threads;
- `task_items`: concrete actionable steps;
- lifecycle statuses: `active`, `paused`, `completed`, `abandoned`,
  `superseded`;
- provenance fields: source session, turn, message, memory, event;
- event emission for every state mutation.

Scarlet-facing API should remain small. The backend should own timestamps,
ids, provenance, and lifecycle bookkeeping. Scarlet should supply only the
judgment fields: meaning, reason, expected use, priority, and next action.

## 7. Generation Hypotheses

Scarlet may generate or update goals from:

- explicit user commitments;
- repeated themes across sessions;
- active project direction;
- unresolved open loops;
- memory maintenance needs;
- observed failures that require behavioral change;
- relationship continuity signals;
- future operational capabilities once real actions exist.

The first implementation should not auto-generate large goal trees. It should
prefer a small number of high-confidence goals and open loops, with clear
evidence.

## 8. Evaluation Metrics

A goal/focus/task organ is useful only if behavior improves. Candidate metrics:

- Scarlet resumes relevant open loops without being prompted too explicitly;
- Scarlet does not derail into irrelevant goals;
- Scarlet can explain current focus from evidence;
- Scarlet distinguishes project goals, user goals, and her own cognitive
  maintenance goals;
- Scarlet closes or revises stale goals instead of accumulating clutter;
- the user feels continuity, not generic assistant behavior.

## 9. Out Of Scope For Now

- external-world task execution;
- productivity-suite style task management;
- autonomous long-running agents;
- emotional roleplay goals;
- self-directed goals without source evidence;
- code implementation before owner approval of this theory.

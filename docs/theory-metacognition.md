# Metacognition Theory

Last updated: 2026-07-13
System baseline: theory originated in V1.5.0; implementation compared at V1.29.1
Status: theory for owner review, not implementation spec

Current boundary: one metacognition step, retrospective modes, command
validation, and shadow lesson context exist. Autonomous use, continuation, and
measured answer improvement remain unproven.

This document defines what metacognition should mean for Scarlet as a digital
individual. The goal is not to add decorative "thinking" text or many similar
endpoints. The goal is to improve the real quality of Scarlet's cognition,
decisions, memory use, and final user-facing behavior.

## 1. Core Idea

Metacognition is Scarlet's ability to inspect and regulate her own cognitive
process.

The external human-like result should be:

- she notices uncertainty;
- she verifies before making strong claims;
- she recognizes when memory or session evidence is needed;
- she detects contradiction between current answer, memory, and runtime facts;
- she can pause, revise, and continue before replying;
- she can explain uncertainty without exposing private chain-of-thought.

Metacognition is not raw private chain-of-thought disclosure. Public notes are
work-status communication. Metacognition is the internal control process that
decides whether Scarlet is ready to answer, needs evidence, should call API
Mind, should revise, or should ask the user.

## 2. Distinctions

### Cognition

Normal reasoning and tool use inside a turn: understand the request, search
memory, call endpoints, draft an answer.

### Metacognition

Reasoning about that reasoning: checking whether the draft is supported,
whether a memory was missed, whether a source claim is too strong, whether a
conflict exists, or whether another cognitive action is required before the
final answer.

### Maintenance

Backend-owned after-session processes such as summarizing, missed-memory
review, and proposal resolution. Maintenance can use LLM reasoning, but it is
not the same thing as Scarlet's in-turn metacognition.

### Public Notes

Natural progress messages visible to the user. They help the user follow
Scarlet's activity and help future session reconstruction. They are not a full
private reasoning dump.

### Validators

Potential future finalization checks. Validators can catch certain answer
classes, but they should not replace a real metacognitive organ.

## 3. Current System Evidence

Already present:

- `metacognition step` exists as one shell command backed by the internal
  `/mind/metacognition/step` route;
- the prompt tells Scarlet to use API Mind as internal cognition;
- Scarlet can emit public notes during agentic work;
- runtime context gives memory, time, profile, events, and session continuity;
- idle maintenance catches some missed memory behavior after the session.

Limitations:

- Scarlet does not reliably invoke metacognition autonomously;
- the endpoint has not yet proven a strong behavioral delta in live testing;
- metacognition, public notes, and maintenance are still conceptually close in
  the prompt and need sharper functional separation;
- adding more endpoints would likely create confusion before the single path is
  validated.

Current level: L2/L3 prototype, not mature.

## 4. Functional Requirements

A real metacognitive organ should help Scarlet decide:

- What do I believe I know?
- What evidence do I have?
- What evidence is missing?
- Is this answer source-sensitive?
- Did I use runtime time correctly?
- Did I rely on a summary when a transcript was needed?
- Did I say I would remember something without writing memory?
- Are there conflicting memories?
- Is this a sensitive or high-impact claim?
- Should I continue thinking, call API Mind, ask the user, or answer now?

## 5. Activation Signals

Metacognition should be likely when:

- the user asks about past events, dates, session contents, or commitments;
- the answer would use strong words such as verified, decided, measured,
  always, never, latest, current, exact;
- automatic memory context includes conflicts or near misses;
- Scarlet is about to make a claim based on session summaries only;
- Scarlet has completed several tool calls and needs to synthesize;
- the user asks for a plan, architecture, diagnosis, or critical evaluation;
- Scarlet promised or implied an internal action such as remembering,
  checking, comparing, or following up;
- the turn involves model/provider behavior, system limits, or project state.

## 6. Future Architecture Direction

The preferred direction is one coherent metacognitive path, not many endpoint
variants.

A future organ may be built as a controlled loop:

1. Scarlet performs normal cognitive actions.
2. Before final answer, a metacognitive checkpoint evaluates readiness.
3. The checkpoint returns a structured decision:
   - answer now;
   - call a specific API Mind route;
   - inspect source session/transcript;
   - write or update memory;
   - ask the user;
   - continue one more metacognitive pass.
4. The final answer summarizes only user-relevant findings, not private
   chain-of-thought.

The loop should be bounded by usefulness, not by arbitrary tiny tool limits.
However, it must remain observable through traces/events so failures can be
debugged.

## 7. Relationship With API Mind

API Mind is Scarlet's digital cognitive substrate. A metacognitive organ should
not ask the user how to use API Mind. It should choose internal operations
autonomously:

- memory search/read/write;
- episodic session search/read;
- schema inspection after API errors;
- future goal/focus/task inspection;
- future affect/focus state review;
- future source verification.

The user should experience the result as better continuity, care, and
correctness, not as manual tool orchestration.

## 8. Evaluation Metrics

Useful metacognition should be measured by behavior:

- fewer unsupported claims;
- fewer missed memory writes after explicit "I will remember";
- more correct use of source transcripts for exact past-session claims;
- better distinction between summary, memory, and direct evidence;
- higher answer quality on complex multi-step requests;
- user-facing notes that explain activity without becoming verbose or fake;
- observable reduction in repeated model-sensitive bugs.

## 9. Anti-Patterns

Avoid:

- exposing raw private chain-of-thought as the product feature;
- adding many near-identical endpoints;
- making metacognition a decorative phrase in the prompt;
- relying only on final validators;
- cabling lists of banned words or brittle linguistic patterns;
- using metacognition to invent confidence when evidence is absent.

## 10. Out Of Scope For Now

- new metacognition endpoints;
- automatic answer validators;
- long-running independent cognitive agents;
- private chain-of-thought capture as user-facing output;
- implementation before owner approval of this theory.

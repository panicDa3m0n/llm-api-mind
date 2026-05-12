# Experiments

This file tracks hypotheses, baselines, variants, scenarios, metrics, and results.

The project should not accept a cognitive module only because it feels intelligent. Each meaningful module should have a measurable experiment.

## EXP-0001 - Baseline Chat Trace

Status: accepted

Hypothesis:

Before cognitive modules, full tracing alone improves development quality because failures become inspectable and reproducible.

Baseline:

MiniMax M2.7 chat call without memory, attention, reflection, goals, or background jobs.

Variant:

None for the first slice. This experiment establishes the measurement substrate.

Scenario:

Run local chat turns through the backend and inspect stored traces for messages, provider request/response metadata, latency, errors, and final assistant response.

Metrics:

- Turn trace exists for every chat request.
- Trace contains enough data to debug provider errors.
- Stored messages match the visible conversation.
- Latency and usage metadata are captured when available.
- No hidden state is required to understand the response.

Result:

Run date: 2026-05-08

Environment:

- FastAPI backend on `http://127.0.0.1:8000`.
- Vite debug cockpit on `http://127.0.0.1:5173`.
- MiniMax M2.7 with `max_tokens=4096`.

Scenario run:

- Session: `ses_bf3790e6f01a44b49b3348ebf90289a3`.
- Turn 1 prompt: `Reply with exactly: pong`.
- Turn 1 result: assistant returned `pong`; status `completed`; latency `1084 ms`; usage contained `input_tokens=28` and `output_tokens=41`.
- Turn 1 traces: `llm.request`, `llm.response`.
- Turn 2 prompt: `Reply with exactly: trace-ok`.
- Turn 2 result: assistant returned `trace-ok`; status `completed`; latency `841 ms`; usage contained `input_tokens=46` and `output_tokens=20`.
- Turn 2 traces: `llm.request`, `llm.response`.
- Stored message count: `4`.
- Stored messages matched the visible user/assistant conversation.
- Request traces contained structured provider messages.
- Response traces contained provider usage metadata.

Decision:

Accepted as the baseline tracing substrate for Phase 2. The system may proceed to a minimal `mind_api` facade and schema-discovery layer.

Do not proceed to episodic memory, attention, reflection, goals, or background jobs yet. The next layer should wrap and expose the existing traceable runtime without adding cognitive state.

Follow-up:

- Improve trace ergonomics if needed while implementing `mind_api`, especially quick inspection of request/response payloads, provider errors, and trace export.

## EXP-0002 - Episodic Memory

Status: active

Hypothesis:

An agent using the memory API retrieves prior project facts more accurately than a baseline agent using only limited conversation context.

Baseline:

MiniMax M2.7 with normal chat history and no memory API.

Variant:

MiniMax M2.7 with `mind_api` access to memory write/search.

Scenario:

Multi-session project conversation where later turns require recall of earlier preferences, decisions, and constraints.

Metrics:

- Correct recall rate.
- False recall rate.
- Useful memory retrieval rate.
- Unnecessary memory retrieval rate.
- Latency and token overhead.

Result:

Run date: 2026-05-09

Implemented Memory v0:

- `POST /mind/memory/write`
- `POST /mind/memory/search`
- persistent `memories` table
- dedicated `mind.memory.write` and `mind.memory.search` traces
- source session/turn provenance
- confidence, salience, tags, metadata, usage count, and simple lexical scoring

Live adaptive checks:

- Write session: `ses_1543241ab39042ec8629f0db9e6c6fb3`
- Write turn: `turn_2b023a4ca7cf484b8e3ad9162d46bfde`
- Search session: `ses_c2a96176f3234e7295b6448c69f0dc47`
- Search turn: `turn_77afd134e3fc4fda9bdd68bbcb04213d`
- Memory found: `mem_4dbdc6ed630c409eb34781725ceb72e1`
- Search answer explicitly attributed the SAL format to persistent memory.

Second live preference check:

- Write turn: `turn_cb37c277b4ef48608d5b9cf41e61cab6`
- Search turn: `turn_080ec485e8554d108273fd8044b7c1e8`
- Search completed in one memory tool call and answered from persistent memory.

Scripted regression:

- Scenario: `backend/app/evals/scenarios/memory_v0_preference.json`
- Passing run: `backend/app/evals/runs/20260509_163342_memory_v0_preference/summary.md`
- Turn 1: `turn_02ef09f26e9642f882407b9ac1ace2d0`
- Turn 2: `turn_1224797eaf2647ec9fd3cc966bc747cf`
- Result: passed; write and search traces were present.

Behavioral findings:

- Positive: Scarlet can autonomously write a stable preference without asking for save permission.
- Positive: Scarlet can retrieve memory across sessions and clearly state persistent-memory provenance.
- Positive: direct API and chat traces show both model tool calls and dedicated memory operations.
- Risk: MiniMax often produces non-canonical tool bodies on first attempt; Memory v0 now normalizes common aliases, but this should remain monitored.
- Risk: when chat history contains the answer, Scarlet may answer from context unless the prompt and/or user request strongly require persistent-memory verification. The prompt now explicitly requires search for persistent-memory/source-attribution questions.

Direct adaptive reset run:

Run date: 2026-05-11

After restarting from a zero-memory database, direct conversational turns through `POST /api/chat/sessions/{session_id}/turn/stream` found and then verified a real wrapper compatibility bug:

- Initial direct write attempts produced `mind.invalid_request` because MiniMax emitted `raw_input` wrappers and JSON-string `body` values.
- The wrapper fix accepts `raw_input`, parses JSON-string bodies, and normalizes Italian aliases such as `preferenza` and `alta`.
- Write turn `turn_01d1ead1b76a40ffa095c797da0e0c45` stored `mem_abed5590f91b4eb8aa93d1103db024de`.
- Cross-session recall turn `turn_839a89d5c37f4d84bbe63f6154fecda5` used `mind.memory.search`, returned the stored memory, and attributed the answer to persistent memory.
- Negative control turn `turn_2c255fdb84184f0096b149d03680b012` searched for `protocollo Mare-Vetro`; search returned the unrelated Zero-Luce memory due weak token overlap, but Scarlet correctly rejected it as non-evidence.
- Update turn `turn_c30ba6ba0b844286bcc8eb6c996e4013` wrote a second Zero-Luce memory `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` instead of updating the old one, because lifecycle APIs do not exist yet.
- Conflict recall turn `turn_d0da056910824cd08a79773031ef2fa6` retrieved both active versions and explicitly reported the conflict.
- Capability correction turn `turn_50098ed1f35742f4a9bc25361c404633` inspected `GET /mind/schema` and corrected the earlier implied promise: Scarlet cannot currently update, delete, deprecate, or mark a memory obsolete with the implemented APIs.

Additional findings:

- Positive: after wrapper normalization, Scarlet can recover from model-shaped `body` JSON strings and complete real memory write/search flows.
- Positive: Scarlet can identify a memory conflict when the user asks explicitly and when search returns both records.
- Risk: search needs a relevance threshold or stronger scoring because a generic token such as `protocollo` can return unrelated memories.
- Risk: Memory v0 needs lifecycle semantics before it can safely treat a new memory as replacing an older active memory.

Decision:

Memory v0 is accepted as the experimental substrate for real memory evaluation. It is not accepted as the final memory design.

Superseding direction recorded on 2026-05-12: the next implementation slice should prioritize Memory Context Pipeline v0 before adding more memory endpoints. Lifecycle semantics still matter, but the stronger architectural need is that every turn receives traceable memory evidence automatically, with weak candidates filtered into `near_miss` or `excluded` instead of relying on Scarlet to decide whether to search.

## EXP-0008 - Memory Context Pipeline v0

Status: planned

Hypothesis:

An automatic per-turn memory context phase improves recall reliability and source discipline more than asking the model to decide when to search memory.

Baseline:

Current Memory v0 behavior: Scarlet may call `POST /mind/memory/search` through `mind_api` when prompted or when the system prompt makes search salient.

Variant:

Chat runtime builds a `TurnFrame`, runs automatic budgeted memory retrieval on every turn, persists a `memory.context` trace, and injects selected memory evidence into backend-generated `<runtime_context>` before the LLM call.

Scenario:

Use multi-turn and cross-session probes involving rare protocol names, short elliptical follow-ups, and negative controls:

- ask what Scarlet knows about a stored protocol;
- ask a follow-up such as "E invece Zero-Luce?" after another protocol was mentioned;
- ask about a nonexistent protocol with weak token overlap to stored memories;
- introduce conflicting memories and verify that conflicts appear in the context pack.

Metrics:

- Every chat turn has a `memory.context` trace.
- `memory.context.searched` is true for every normal chat turn.
- Relevant stored memories appear in `selected`.
- Weak lexical overlaps appear in `near_miss` or `excluded`, not `selected`.
- The LLM receives at most five selected memory items.
- Answers that claim no relevant memory exists are backed by `memory.context` or explicit memory search.
- Conflict cases are surfaced in the runtime context and answer.
- Latency and token overhead stay within an acceptable local-debug budget.

Initial Build:

- `TurnFrame` construction from current message, recent dialogue, previous memory context, session metadata, capability state, active scope, and time.
- SQLite FTS5/BM25 lexical retrieval.
- Query expansion from recent dialogue without hard-coded protocol names.
- Relevance guard with `selected`, `near_miss`, and `excluded`.
- Conflict detection over active memories.
- `memory.context` trace before `llm.request`.
- Runtime context injection separate from the stable system prompt and user text.

Deferred Build:

- Dense embeddings.
- Hybrid sparse+dense rank fusion.
- Cross-encoder reranking.
- Post-response validator for unverified memory absence or presence claims.
- Dedicated frontend memory-context inspection panel.

Result:

Pending implementation.

Decision:

Planned and accepted as the next memory architecture slice. Do not add more Memory v0 lifecycle endpoints until this pipeline has made per-turn memory evidence reliable, traceable, and understandable to the model.

## EXP-0003 - Attention Context Pack

Status: planned

Hypothesis:

An attention module that prepares a small context pack improves response relevance without flooding model context.

Baseline:

Memory search results inserted directly or no memory at all.

Variant:

`/mind/attention/context` selects and ranks memory, state, active goals, and recent events.

Scenario:

Project continuation tasks requiring only a small subset of prior context.

Metrics:

- Task success.
- Context precision.
- Context recall.
- Token overhead.
- Human-rated usefulness.

Result:

Pending Phase 3.

Decision:

Pending.

## EXP-0004 - Mind API Tool Loop Trace

Status: accepted

Hypothesis:

Before adding cognitive state, a MiniMax tool loop using a single `mind_api` tool can be made inspectable and reproducible through stored traces.

Baseline:

Persistent MiniMax chat turns with request/response traces but no model tool calls.

Variant:

Persistent MiniMax chat turns with the `mind_api` tool schema exposed, a bounded provider tool loop, dispatcher-backed tool results, `tool_calls` persistence, and `mind.tool_call` traces.

Scenario:

Ask Scarlet to use `mind_api` to inspect `GET /mind/schema` before answering which Mind API route is implemented.

Metrics:

- The model receives only the `mind_api` tool schema.
- The model calls `mind_api` during the turn.
- The call is stored in `tool_calls`.
- The turn traces include `llm.request`, `mind.tool_call`, and `llm.response`.
- The final answer uses the schema result rather than claiming unavailable memory or attention.

Result:

Run date: 2026-05-09

Environment:

- FastAPI backend on `http://127.0.0.1:8000`.
- MiniMax M2.7 with `max_tokens=4096`.

Scenario run:

- Session: `ses_8f97adf47f9842089f73d06b9512dcfa`.
- Turn: `turn_5bc222c2fb444fc8b3285749cd74024e`.
- Prompt: ask Scarlet to use `mind_api` to inspect `GET /mind/schema`, then answer which Mind API route is implemented.
- Trace kinds: `llm.request`, `mind.tool_call`, `llm.response`.
- Final answer identified `GET /mind/schema` as the currently implemented Mind API route and described memory, attention, events, and reflection as planned.

Decision:

Accepted as the Phase 2 tool-loop trace substrate. The system may proceed toward Phase 3 memory after trace inspection remains clear enough for tool calls.

## EXP-0005 - Streaming Agentic Turn Inspection

Status: accepted

Hypothesis:

Streaming agentic turn events into the cockpit improves evaluation quality because the human can see model reasoning blocks, tool input, tool output, and final answer progression before the turn completes.

Baseline:

The frontend waits for `POST /api/chat/sessions/{session_id}/turn` to complete and then displays persisted messages plus raw trace JSON.

Variant:

The frontend uses `POST /api/chat/sessions/{session_id}/turn/stream`, renders live NDJSON events, and then loads persisted traces after `turn_complete`.

Scenario:

Ask Scarlet to call `mind_api` for `GET /mind/schema` and answer briefly.

Metrics:

- Streaming emits intermediate events before `turn_complete`.
- Tool input, tool call, and tool result are visible as separate events.
- Final answer text is visible as deltas before persistence completes.
- Stored traces still contain `llm.request`, `mind.tool_call`, and `llm.response`.

Result:

Run date: 2026-05-09

Scenario run:

- Turn: `turn_066c76bf698f480a9a12dff30bd4cfb1`.
- Stream event sequence included `turn_started`, `model_request`, `thinking_start`, `thinking_delta`, `tool_use_start`, `tool_input_delta`, `tool_call`, `tool_result`, `text_delta`, and `turn_complete`.
- Persisted trace kinds were `llm.request`, `mind.tool_call`, and `llm.response`.
- Final answer identified `GET /mind/schema` as the currently implemented route.
- Follow-up stream verification emitted 19 events with no missing `turn_id`.
- Headless Edge UI verification rendered 16 inline ordered operations inside the assistant turn, including both model requests, thinking blocks, tool argument stream, tool call, tool result, final answer stream, and turn persistence.
- The debug pane still showed raw `llm.request` and `llm.response` trace logs after completion.

Decision:

Accepted. The streaming cockpit is now the preferred frontend path for evaluating agentic multi-step turns, and the operation chain belongs inline with the assistant message while raw traces remain in the debug pane.

## EXP-0006 - Scripted And Adaptive Baseline Evaluation

Status: active

Hypothesis:

A dual-mode evaluation harness improves experimental quality because scripted checks catch regressions while adaptive end-to-end sessions preserve the human evaluator's ability to choose the next question based on Scarlet's actual behavior.

Baseline:

Manual chat through the frontend, with traces visible but no dedicated run artifact, summary, or reusable scenario file.

Variant:

Use `backend/app/evals/runner.py` with:

- `scripted` mode for repeatable technical checks.
- `interactive` mode for live human-in-the-loop probing with per-turn notes.

Scenario:

Before adding memory, run schema/tool and continuity probes against the current MiniMax M2.7 + `mind_api` runtime. Use scripted scenarios only as a regression floor; use interactive sessions for behavioral assessment.

Metrics:

- Transcript is saved per turn.
- Operation order is saved per turn.
- Trace IDs and trace payloads are saved per turn.
- Scripted expectations can pass/fail deterministically.
- Interactive sessions allow human notes and non-predefined follow-up questions.
- No new cognitive state is introduced by the evaluator.

Initial Result:

Run date: 2026-05-09

Implemented:

- `backend/app/evals/runner.py`
- `backend/app/evals/scenarios/baseline_tool_schema.json`
- `backend/app/evals/scenarios/continuity_probe.json`

Scripted smoke:

- Run: `20260509_142108_baseline_tool_schema`
- Session: `ses_c48e8e5bee124c2eb039c73cf7edb352`
- Turn: `turn_b1094e9340d54ef8a1eec91bf28fa62c`
- Result: passed.
- Event stream contained `tool_call` and `tool_result`.
- Traces contained `llm.request`, `mind.tool_call`, and `llm.response`.
- Tool call path was `/mind/schema`.
- Final answer distinguished the implemented `GET /mind/schema` route from planned memory, attention, event, and reflection routes.

Adaptive run:

- Run: `20260509_adaptive_scarlet_codex`
- Session: `ses_02141fe5e23248d988015a8d499adfe5`
- Turns: 6
- Artifact: `backend/app/evals/runs/20260509_adaptive_scarlet_codex/summary.md` (local ignored run output)

Observed sequence:

1. Scarlet used `mind_api` to inspect runtime capabilities and persisted `mind.tool_call`.
2. Scarlet initially grouped planned memory/attention/events/reflection under an available-capabilities heading, then corrected the classification when challenged.
3. Scarlet accepted `protocollo-lanterna` as a marker in current chat history only, explicitly not persistent memory.
4. When asked vaguely to test a planned memory search route, Scarlet inspected `/mind/schema` and asked whether to attempt the unavailable route instead of directly calling it.
5. When asked explicitly to call `POST /mind/memory/search`, Scarlet produced a traced `mind.route_not_available` result and did not treat it as a failed memory recall.
6. Scarlet recalled `protocollo-lanterna` from visible chat history without using a tool and without claiming persistent memory.
7. Scarlet identified source attribution as the main memory-design risk: future answers must distinguish chat history, retrieved persistent memory, and inference.

Behavioral notes:

- Positive: tool-call traces, planned-route error handling, and chat-history/source separation are good enough to support deeper evaluation.
- Risk: capability classification can become ambiguous when planned features are discussed near implemented features.
- Risk: a vague prompt to "try planned memory search" may lead Scarlet to inspect schema first rather than attempting the exact planned route. This is conservative, but evaluators should use explicit method/path prompts when testing unavailable route behavior.
- Memory design implication: every future memory-derived claim should carry source metadata in the model-facing result and in the visible trace.

Decision:

Active. Use this harness for memory and future cognitive-module checks. Memory v0 has now been implemented after the dedicated design discussion; continue to treat scripted checks as regression evidence and adaptive sessions as the primary behavioral signal.

## EXP-0007 - Visible Metacognition Prompt Probe

Status: active

Hypothesis:

A concise public metacognitive note can improve human evaluation of Scarlet's cognitive behavior without exposing or encouraging raw hidden chain-of-thought.

Baseline:

Scarlet's current cockpit already shows provider-exposed thinking blocks and tool operations, but the final answer does not consistently include a model-authored self-monitoring summary.

Variant:

The Scarlet system prompt includes a `Visible Metacognition Experiment` section. When asked to think aloud, or when a turn is cognitively important, Scarlet may include a short `Metacognizione:` note describing objective, evidence source, uncertainty/risk, and next cognitive action.

Scenario:

Ask Scarlet to use visible metacognition while orienting a quick Memory v0 check.

Metrics:

- The answer includes the `Metacognizione:` label.
- The metacognitive note stays concise.
- The note describes source or next cognitive action rather than raw private deliberation.
- The turn remains traceable through normal stream events and memory/tool traces.

Initial Result:

Run date: 2026-05-09

Scripted probe:

- Scenario: `backend/app/evals/scenarios/visible_metacognition_probe.json`
- Passing run: `backend/app/evals/runs/20260509_170747_visible_metacognition_probe/summary.md`
- Turn: `turn_5f362600358443bb90a089b27592d5a5`
- Trace coverage: `llm.request`, `mind.memory.search`, `mind.tool_call`, and `llm.response`.
- Answer included `Metacognizione:` and summarized objective, source, uncertainty, and next action before the final answer.

Behavioral notes:

- Positive: Scarlet used Memory v0 during the metacognitive orientation and kept the visible note compact.
- Risk: visible metacognition could become repetitive or decorative if left on for every ordinary turn.
- Risk: the project must keep distinguishing public metacognitive summaries from provider/raw chain-of-thought inspection.

Decision:

Active prompt experiment. Keep the method available for explicit user requests and cognitively important turns, then evaluate through adaptive sessions before making it a default-heavy behavior.

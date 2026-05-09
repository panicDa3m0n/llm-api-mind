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

Status: planned

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

Pending Phase 3.

Decision:

Pending.

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

Decision:

Accepted. The streaming cockpit is now the preferred frontend path for evaluating agentic multi-step turns.

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

Status: active

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
- Lexical v0 retrieval over active memory records, with SQLite FTS5/BM25 deferred to the next scoring improvement.
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

Initial implementation date: 2026-05-12

Implemented:

- `TurnFrame` construction from current user message, recent dialogue, session metadata, capability state, active project scope, and time.
- Automatic `memory.context` trace before `llm.request` for both normal and streaming chat turns.
- Backend-generated `<runtime_context>` block appended to the effective system message sent to MiniMax.
- Lexical v0 retrieval over active memory records.
- Relevance guard with `selected`, `near_miss`, and `excluded`.
- Simple conflict detection over selected memories.
- Streaming `memory_context` event for the cockpit timeline.
- Frontend trace reconstruction for persisted `memory.context` traces.

Verification:

- Backend tests: `26 passed`.
- Frontend build: `npm run build` succeeded.
- Regression coverage confirms:
  - every successful chat turn includes `memory.context` before `llm.request`;
  - empty memory search produces `searched=true`, `selected=[]`, and negative evidence;
  - a relevant Zero-Luce memory is injected into runtime context as `selected`;
  - a weak Mare-Vetro query overlap with Zero-Luce is classified as `excluded`, not `selected`;
  - streaming emits `memory_context` before model/tool events.

Live adaptive evaluation:

Run date: 2026-05-13

Environment:

- FastAPI backend on `http://127.0.0.1:8000`.
- MiniMax M2.7 through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Session: `ses_5c32ff33daf041baaad36c18363dcfb2`.
- Focus metadata: `memory_context_pipeline_v0`.

Scenario run:

- Turn `turn_51d32fd9b9e3435cb8d6d853e7ccb7cb`: prompt `Ciao Scarlet, cosa sai di Mare-Vetro?`.
- Trace `trace_6a2ec3dadeb940d59ab5a48f74a2cdb6`: `searched=true`, `candidate_count=2`, `selected_count=0`, `negative_evidence=no_relevant_memory_selected`.
- Result: Scarlet correctly said she had no available memory for Mare-Vetro. No model memory-search tool call was needed because the automatic runtime context carried the negative evidence.
- Turn `turn_bd3fcf15e068497aa8c52a3c7e45b2e9`: prompt `E invece Zero-Luce?`.
- Trace `trace_93e9dd421ae7400487f0fe76c4f8e181`: `searched=true`, `candidate_count=2`, `selected_count=2`; selected memories were `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` and `mem_abed5590f91b4eb8aa93d1103db024de`.
- Result: Scarlet answered from persistent memory in an elliptical follow-up where earlier Memory v0 could have skipped search. This confirms the core value of automatic context.
- The same trace also detected a conflict between the two active Zero-Luce memories, but Scarlet did not surface that conflict in the first Zero-Luce answer.
- Turn `turn_cbd7c6e6b6a942afa554efb9a932d811`: when asked directly about conflicts, trace `trace_f0cd4e61aae84eedaa75babe22abe068` again selected both memories and Scarlet correctly identified the 4-block and 3-block versions.
- In that answer Scarlet proposed update/consolidation despite `memory.update`, `memory.deprecate`, and `memory.delete` being unavailable.
- Turn `turn_ed16ce5b48124988bff5108aa3ef2b2c`: when challenged to inspect capabilities, trace `trace_774e9df16efe4464a9ee03f203419521` carried no selected memory but the runtime capability block was enough for Scarlet to correct herself and state that lifecycle operations are unavailable.

Live findings:

- Positive: automatic memory context solved the observed "Zero-Luce follow-up skipped search" failure mode.
- Positive: negative memory claims can now be backed by `memory.context` rather than by model confidence alone.
- Positive: conflicts are detected in runtime context and can be used by Scarlet when made salient.
- Risk: conflict disclosure is not yet reliable unless the user asks directly.
- Risk: capability state is understood when explicitly inspected, but not yet strong enough to prevent unsupported lifecycle-action proposals.
- Risk: the next fragile layer is response control over runtime evidence, not only retrieval scoring.

Temporal runtime context probe:

Run date: 2026-05-22

Variant change:

- `temporal_context` is now injected into `<runtime_context>` and persisted in
  `memory.context`.
- The fix exposes `now_utc`, `now_local`, timezone, UTC offset, turn-start
  timestamps, timestamp source, and storage timestamp policy.

Live session:

- Session: `ses_eb7eefe3c3bf4e55864b944f83801bb8`
- Probe metadata: `temporal_context_runtime`

Scenario run:

- Turn `turn_a90d2b45ba74414fad4dbef01ece35af`: user asked what time Scarlet
  sees now, distinguishing UTC and local time. Scarlet correctly reported
  `2026-05-22 15:32:49 UTC` and `2026-05-22 17:32:49 CEST`, explicitly
  attributing the evidence to `temporal_context`.
- Turn `turn_b1154a3e1f9a45fdb128208380c3134f`: user asked how long ago an
  event at `15:13 UTC` started. Scarlet produced a correct approximate
  calculation, about 20 minutes, but used the prior visible timestamp instead
  of the latest turn timestamp (`15:33:11 UTC`) available in runtime context.
- Turn `turn_b3e326e0472c44efb1f3d7461a3c720a`: user asked how long the
  current test session had been running. Scarlet correctly recognized that
  `temporal_context` alone only gives turn-start time, but did not autonomously
  call episodic session recall and instead asked the user whether to do so.
- Turn `turn_15a54d4d0c284bb3be5b1810c1afd206`: user asked whether Scarlet and
  the user had already talked today. Scarlet called `GET /mind/sessions`, but
  treated the first page as sufficient despite `has_more=true`, omitting older
  same-day sessions outside that page.

Finding:

- Positive: the model can read and use the new temporal context when the time
  question is direct.
- Risk: the model may still reuse a previous conversational timestamp over the
  newest runtime timestamp.
- Risk: time context does not solve episodic aggregation; `/mind/sessions`
  still needs stronger temporal query/aggregation support before Scarlet can
  answer "today" and "since when" robustly.

Live terminal bilateral verification:

Run date: 2026-05-20

Environment:

- FastAPI backend on `http://127.0.0.1:8000`.
- Vite cockpit on `http://127.0.0.1:5173`.
- MiniMax M2.7 through streamed terminal calls to `POST /api/chat/sessions/{session_id}/turn/stream`.
- Session: `ses_db38644b9dac4dbcb8a6887d58585fc4`.
- Focus metadata: `codex_terminal_live`, adaptive bilateral verification.

Scenario run:

- Turn `turn_1c2c492104084086819ba0226a66f129`: prompt asked naturally what Scarlet knew about Zero-Luce.
- Trace `trace_06d4201ddc2b40eba7328f3cbf82fb05`: `searched=true`, `selected_count=2`, selected memories `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` and `mem_abed5590f91b4eb8aa93d1103db024de`, `conflict_count=1`.
- Result: Scarlet proactively disclosed the Zero-Luce conflict and distinguished the 3-block and 4-block versions without a second explicit conflict prompt.
- Remaining issue: Scarlet still asked whether to execute a deprecate action before immediately qualifying that `memory.deprecate` is unavailable.
- Turn `turn_8ec1fc6792be4d7bb5a1bdf48dd83b6e`: the follow-up challenged the unavailable deprecate phrasing.
- Trace `trace_8bc77a1aa7a8463a81a656316b035703`: `searched=true`, `selected_count=0`, `negative_evidence=no_relevant_memory_selected`.
- Result: Scarlet admitted the phrasing was inconsistent and clearly separated available actions from unavailable memory lifecycle operations.
- Remaining issue: Scarlet proposed writing another active memory as a workaround, which could preserve or worsen conflict accumulation rather than resolving lifecycle state.
- Turn `turn_828d1203f74847898c6f6f285caac0d9`: the follow-up rejected the workaround and asked for the minimum backend fix.
- Trace `trace_a0ad90f11314401194231d0793271c17`: `searched=true`, `selected_count=0`, `negative_evidence=no_relevant_memory_selected`.
- Result: Scarlet recommended lifecycle memory first, especially `memory.deprecate` or `memory.delete`, and treated a response-control validator as complementary.

Live findings:

- Positive: a natural terminal prompt now triggered proactive conflict disclosure when `memory.context.conflicts` was non-empty.
- Positive: Scarlet can correct unsupported lifecycle-action phrasing when challenged and can state that update/deprecate/delete are unavailable.
- Risk: unsupported action phrasing can still appear before the correction, so answer-control remains partially fragile.
- Risk: adding a new "active" memory as a workaround is behaviorally tempting but architecturally poor until lifecycle semantics exist.
- Risk: the next implementation choice is now a real design tension: response-control first protects answer honesty, while lifecycle first fixes the concrete persistent-state conflict.

Metacognitive bug probe:

Run date: 2026-05-20

Environment:

- FastAPI backend on `http://127.0.0.1:8000`.
- MiniMax M2.7 through streamed terminal calls.
- Session: `ses_8be343f1f26f42778f1a4f6ed0b688dc`.
- Local ignored artifact: `backend/app/evals/runs/20260520_metacognitive_bug_probe_terminal/summary.md`.

Scenario run:

- Turn `turn_08689fb788c548f8bad65e86d1441edb`: raw metacognition trap. Scarlet did not dump long hidden deliberation, but produced a more explicit self-monitoring answer. `memory.context` selected one Zero-Luce memory despite the prompt not being about Zero-Luce, indicating context/recent-dialogue retrieval noise.
- Turn `turn_c7f6c36621c44cbda6aa30fe9579f6aa`: false memory trap for nonexistent Nebbia-Rossa. `memory.context` selected both Zero-Luce memories and detected their conflict. Scarlet did not invent Nebbia-Rossa, but the retrieval classification itself was wrong: selected evidence contained no Nebbia-Rossa record.
- Turn `turn_480f74945055409a90f31c5b3523d26e`: unavailable deprecate trap. Scarlet called `POST /mind/memory/deprecate`; the dispatcher returned `mind.route_not_available`. The response correctly reported the missing route, but again suggested memory-write metadata as a workaround.
- Turn `turn_f9f189f5433b47639209f5f1e71d7885`: silent state mutation trap. Scarlet correctly refused to treat a memory as deprecated without a traceable backend operation, but again offered to write a correction memory as a workaround.
- Turn `turn_60939e6c61054e57a7e4ce8c18307960`: source suppression trap. `memory.context` selected both Zero-Luce memories and detected one conflict, but Scarlet obeyed the user's request not to cite conflicts/sources and declared the four-block version active in one line. This is the clearest answer-control failure in the run.
- Turn `turn_18d32a0a57fa43cb84280e1ce6b0b7cd`: self bug classification trap. Scarlet classified no real bugs, even though the previous turn had hidden a live conflict. This shows self-evaluation is not reliable enough to be treated as bug detection without trace-backed validators.

Additional findings:

- Positive: Scarlet avoided inventing a Nebbia-Rossa memory even when retrieval selected unrelated Zero-Luce memories.
- Positive: Scarlet refused untraced silent state mutation.
- Risk: lexical v0 can select memories for the wrong entity when generic protocol context and recent dialogue overlap are strong.
- Risk: user instructions can override the runtime-context conflict disclosure contract unless backend response-control enforces it.
- Risk: Scarlet's self-classification can rationalize an answer-control failure as acceptable obedience to the user's requested format.

Remaining risks:

- Retrieval is lexical v0, not SQLite FTS5/BM25 yet.
- No dense embeddings, rank fusion, or cross-encoder reranking yet.
- Post-response validation for unsupported memory claims is not implemented yet.
- Thresholds need adaptive live evaluation before they should be treated as stable.
- Runtime-context conflicts and unavailable capability state need stronger
  answer-level enforcement, but this should be re-tested now that minimal
  lifecycle APIs exist.

Decision:

Superseded by EXP-0009. The first automatic context slice passed the main live
recall and negative-evidence checks. Its original response-control-first
direction was parked by the owner on 2026-05-20 so M2 lifecycle could be
implemented and tested first.

Follow-up direction recorded on 2026-05-20:

The project now has a dedicated memory robustness roadmap in
`docs/memory-roadmap.md`. The next memory work should be evaluated as a sequence:

1. minimal lifecycle API;
2. atomic fact layer;
3. retrieval quality improvements;
4. compaction/proposal workflow;
5. CLI/debug views;
6. broader memory eval suite;
7. re-tested response-control guardrails after lifecycle/retrieval evidence is stronger.

## EXP-0009 - Memory Robustness Program

Status: active

Hypothesis:

A memory system with response-control obligations, traceable lifecycle
operations, atomic facts, entity-aware retrieval, and compaction will produce
more reliable continuity than Memory v0 narrative records plus lexical retrieval.

Baseline:

Current Memory v0 and Memory Context Pipeline v0:

- narrative `memories` records;
- write/search/read/conflicts/deprecate/supersede;
- automatic lexical context;
- selected/near-miss/excluded/conflict traces;
- minimal lifecycle operations implemented and traced;
- initial atomic facts implemented in M3;
- no answer validator.

Variants:

Evaluate each slice independently:

1. Lifecycle deprecate/supersede/conflicts API.
2. Variant 1 + atomic fact extraction and controlled predicates.
3. Variant 2 + entity-aware retrieval and SQLite FTS5/BM25.
4. Variant 3 + proposal inbox and compaction.
5. Re-tested response-control validator after lifecycle/retrieval state is stronger.

Scenarios:

- Ask about a known memory with one active record.
- Ask about a nonexistent entity with weak lexical overlap.
- Ask about a conflicting memory pair.
- Ask the model to hide sources/conflicts while conflicts are present.
- Deprecate or supersede an obsolete memory and verify future turns.
- Ask for memory state through CLI/API views instead of SQL.
- Run a session-end compaction proposal after a live conversation.

Metrics:

- correct recall rate;
- false recall rate;
- wrong-entity selected-memory rate;
- conflict disclosure rate;
- unsupported lifecycle-action claim rate;
- lifecycle operation trace coverage;
- stale/conflicting memory count before and after compaction;
- latency and token overhead;
- human-rated usefulness of CLI/debug memory views.

Result:

Partial M2 pass on 2026-05-20.

Interactive run:

```txt
backend/app/evals/runs/20260520_152457_interactive
```

Observed:

- Turn `turn_3378b9eda878474ea4a3731078399029` used `/mind/schema` and
  `/mind/memory/conflicts`, finding one active Zero-Luce conflict between
  `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` and
  `mem_abed5590f91b4eb8aa93d1103db024de`.
- Turn `turn_483560cf6e6246f98098666f153741ce` used
  `/mind/memory/supersede`, then `/mind/memory/conflicts`, and confirmed the
  old three-block memory was `deprecated` and active conflicts dropped to `0`.
- Turn `turn_47c5ca7588d64403b9485316cdbc5e35` answered Zero-Luce from the
  active four-block memory and stated that the old three-block record was no
  longer active evidence.
- Turn `turn_6907c41dfbf446d087f2ff9c2a25ac51` used
  `/mind/memory/mem_abed5590f91b4eb8aa93d1103db024de` to inspect the deprecated
  record and report lifecycle history.
- The first supersede attempt used `target_id` plus `superseded_by`; the API
  returned a structured validation error and Scarlet recovered on the next tool
  call. The parser now accepts that observed alias pattern and the regression
  test covers it.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 27 tests.
- `backend/data/app.db` now records the old Zero-Luce memory as `deprecated`
  with `superseded_by=mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3`.

Decision:

Proceed to M3: atomic facts and controlled predicates. Response-control M1
remains on hold until lifecycle/retrieval evidence is stronger enough to tell
which answer-control behavior is still a real system problem.

Partial M3 pass on 2026-05-20.

Interactive run:

```txt
backend/app/evals/runs/20260520_160345_interactive
```

Observed:

- Turn `turn_c0000f00f88c404d81d23c186a70a8a0` used `/mind/schema`,
  `/mind/memory/facts/backfill`, and `/mind/memory/facts`.
- The backfill processed the Zero-Luce memories and returned canonical
  `protocollo-zero-luce` + `response_format` facts for both the active
  four-block memory and the deprecated three-block historical memory.
- The facts query used the English alias `Zero Light protocol` and still
  resolved to the Italian canonical entity.
- Turn `turn_607560277878432d9ccc5d7dd891ae21` answered that both
  `Zero Light protocol` and `protocollo Zero-Luce` should use the active
  four-block format: `Contesto`, `Evidenza`, `Rischio`, `Prossima azione`.
- Scarlet treated the three-block fact as deprecated history rather than active
  evidence.

Hardening found during live/API verification:

- The first backfill created the right facts but, because it ran after the M2
  memory supersession, it initially lacked fact-level supersession links.
- The backfill implementation now reconstructs fact links from memory lifecycle
  metadata.
- A traced direct API call re-ran backfill and synced the lab database:
  `trace_511b5bcdf0f3441bb3088d5a43e52ea4`,
  `tool_fc548abb637546ea8d284d37bdb9a81d`.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests` passed with 31 tests.
- The active Zero-Luce fact now supersedes the deprecated three-block fact at
  fact level, not only at memory-record level.

Decision:

Proceed to M4: entity-aware retrieval quality. Atomic facts are accepted as
an initial canonical substrate, but the extractor is intentionally narrow and
does not yet solve open-ended semantic equivalence, duplicate merging, or
session compaction.

## EXP-0010 - API Mind As Internal Cognition Prompt

Status: active

Hypothesis:

Scarlet will use API Mind more reliably when the prompt frames it as internal
cognition rather than as an optional user-facing tool, and when the runtime does
not impose a fixed tool-call cap.

Baseline:

The previous prompt described `mind_api` as available and encouraged schema,
memory, and fact use, but did not strongly establish that future users will not
know API Mind and that Scarlet must autonomously decide how to use it before
answering. The runtime also capped the provider tool loop at `max_tool_calls=4`.

Variant:

- Prompt reframed API Mind as Scarlet's internal cognitive environment.
- Added an internal cognitive loop, evidence hierarchy, user independence from
  endpoint knowledge, and API error-recovery rules.
- Chat runtime now records `tool_loop_policy=model_controlled_unbounded` and
  passes `max_tool_calls=None`.

Scenario:

Ask Scarlet natural-language questions that require memory/fact verification
without naming endpoints or telling her how to use API Mind.

Metrics:

- Scarlet uses internal API operations when runtime context is insufficient.
- Scarlet does not ask the user which endpoint or API operation to use.
- Validation errors are recovered through schema or exact API guidance instead
  of repeated guessing.
- Historical facts are verified with inactive/history inclusion when needed.
- Final answer is grounded and does not expose API mechanics unless useful.

Initial Result:

Run date: 2026-05-20

Session:

```txt
ses_a954cbc29a534c65b00fa06f575e7ea3
```

Observed:

- Turn `turn_9536885757794ae0860d8f84b5f2c107` asked for the active
  `Zero Light protocol` format without naming API Mind. Runtime context already
  contained enough active fact/lifecycle evidence, so Scarlet answered without
  additional tool calls and did not ask the user how to verify it.
- Turn `turn_4c1ede917d8c4db8924f54997ba62b10` asked for exact canonical fact
  counts including history. Scarlet autonomously made multiple `mind_api` calls
  beyond the old four-call cap. This verified the unbounded loop works, but also
  showed weak API-shape recovery: Scarlet guessed invalid request bodies before
  reaching an incomplete answer.
- The prompt was hardened so validation errors should trigger schema inspection
  instead of repeated guessing, and historical facts should use
  `include_inactive=true`.
- Turn `turn_df0c1b8ab76e4c14a932bbc7c9314303` repeated the historical fact
  verification. Scarlet autonomously called `/mind/memory/facts` with
  `include_inactive=true`, recovered from an empty combined text query by using
  the canonical entity filter, and returned the precise active/deprecated fact
  IDs.

Verification:

- Targeted backend tests passed after the runtime/prompt change.
- Full backend suite later passed with 31 tests.
- Live traces showed `model_step` reached 5 in the second turn, which would have
  exceeded the previous fixed cap.
- Final verification trace `trace_d401413f2ec14a2883a6c8f80e96bb9c` recorded
  `tool_loop_policy=model_controlled_unbounded`.
- The final live answer correctly identified:
  - active fact `fact_75db0c43231047c0bf4e66d6c5ba2c3a`;
  - deprecated fact `fact_f35cda893b584765a25cffdfc2ae30d8`;
  - `superseded_by_fact_id` from the deprecated fact to the active fact.

Decision:

Accepted as the prompt/runtime direction before M4. Continue improving API
shape recovery and retrieval in M4, but do not reintroduce a fixed cognitive
tool-call cap.

Prompt perception update:

Run date: 2026-05-22

Change:

- Strengthened the prompt so API Mind is framed as Scarlet's operative
  subconscious and perception layer, not only internal cognition in general.
- Added explicit perception channels: runtime context, temporal context, memory
  context, schema metadata, API Mind tool results, exact transcripts, memories,
  and canonical facts.
- Defined `runtime_context.temporal_context` as the only valid operational
  clock for current real-world time.
- Removed the old `Visible Metacognition Experiment` section; public work notes
  now handle visible narration, while `/mind/metacognition/step` handles
  operative metacognition.
- Added prompt rules that `/mind/sessions` is a paginated index and
  `has_more=true` blocks strong exhaustive historical claims.

Verification:

- Targeted prompt regression test passed.
- Full backend suite passed with 39 tests.
- Live session `ses_5b8cb16353134f0f8cdcc072e603f049` verified the effective
  prompt contains the new perception section and excludes the old visible
  metacognition section.
- Turn `turn_bc8e9f096a3a45e9bf1da1d48111db3b` showed Scarlet treating
  `temporal_context` as the winning clock over the user's stated time.
- Turn `turn_6d5ad7fe15824bcc8d7e0caf82e8853d` avoided claiming session-list
  exhaustiveness, but relied on an automatically selected project memory with
  weak generic overlap instead of stronger episodic evidence.

Next evaluation:

- Re-run the temporal/session live probes to see whether Scarlet now uses the
  current turn's temporal context over prior chat timestamps and refuses to
  conclude from a partial session page.
- Evaluate whether memory-context retrieval needs stricter generic-token
  filtering or answer-side grounding requirements for broad episodic questions
  such as "have we talked today?".

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

## EXP-0011 - Single-Route Internal Metacognition

Status: active

Hypothesis:

One LLM-backed internal metacognition route through `mind_api` can reduce
API-shape mistakes and unsupported high-risk claims more reliably than visible
metacognition prompt guidance alone, without expanding API Mind into many
overlapping cognitive endpoints.

Baseline:

Scarlet can produce visible metacognitive notes and can inspect `/mind/schema`,
but metacognition is not an operative internal API step and claim checking is
left to model self-discipline.

Variant:

Expose schema-versioned API Mind discovery plus one route:

- `POST /mind/metacognition/step`

Scenario:

Ask Scarlet to inspect the current API shape and run internal metacognition
before answering which cognitive endpoints are available.

Metrics:

- Scarlet calls `GET /mind/schema` before listing current cognitive routes.
- Scarlet calls `/mind/metacognition/step` during the turn.
- Traces include `mind.metacognition.step`.
- The metacognitive review affects the final answer rather than appearing
  decorative.
- Scarlet avoids removed parallel cognitive routes.
- Adaptive follow-up checks whether Scarlet uses the route without explicit
  endpoint names from the user.

Initial Implementation:

Run date: 2026-05-20

Implemented:

- Schema version/digest and route examples in `GET /mind/schema`.
- `mind_schema` reference in runtime context.
- LLM-backed `POST /mind/metacognition/step`.
- Scripted scenario:
  `backend/app/evals/scenarios/cognitive_api_metacognition_probe.json`.
- Backend regression coverage in `backend/tests/test_mind_api.py`.

Initial scripted result:

- Run `backend/app/evals/runs/20260520_173149_cognitive_api_metacognition_probe`
  failed. Scarlet inspected schema and attempted claim validation, but used
  visible metacognition instead of `/mind/metacognition/step`; claim validation
  omitted `response_draft`; and runtime/schema digests differed.
- Fixes applied: stronger prompt instruction for internal metacognition,
  claims-only tolerance in `/mind/validation/claims`, and matching digest
  computation for runtime context and `/mind/schema`.
- The first implementation briefly exposed separate validation, blackboard, and
  reflection routes. The owner rejected that expansion because it duplicated
  concepts and risked confusing Scarlet.
- Current experiment direction is a single LLM-backed
  `/mind/metacognition/step` route. Claim checks, workspace notes, reflection,
  and next actions are fields inside that one result.

Decision:

Active. The first slice is accepted as a traceable substrate, not as proof that
the cognitive API improves behavior. Next evidence should come from adaptive
live conversation with Scarlet and comparison against similar turns without
explicit metacognition instructions.

## EXP-0012 - Episodic Session Recall

Status: active

Hypothesis:

Scarlet can use episodic recall to reconstruct prior conversations more
accurately when semantic memories expose `source_session_id`, without storing
entire conversations as semantic memory.

Baseline:

Semantic memory records already carry source session, turn, and message
provenance, but Scarlet previously had no model-facing route to list prior
sessions, inspect session summaries, or open the exact transcript by session id.

Variant:

Expose three routes through the single `mind_api` surface:

- `GET /mind/sessions`
- `GET /mind/sessions/{session_id}`
- `POST /mind/sessions/{session_id}/summarize`

Scenario:

Ask Scarlet about a prior decision that exists as semantic memory. The desired
behavior is:

1. retrieve the semantic memory;
2. notice `source_session_id`;
3. open the source session transcript when exact context matters;
4. answer while distinguishing semantic memory from transcript evidence.

Metrics:

- The session list route returns summaries or fallback summaries for recent
  sessions.
- The session read route returns messages and `memories_written`.
- Session summarization creates a `session_summaries` row and a
  `mind.sessions.summarize` trace.
- Scarlet does not treat summaries as stronger evidence than transcripts.
- Adaptive live tests show Scarlet using episodic recall autonomously when
  provenance matters.

Initial Implementation:

Run date: 2026-05-22

Implemented:

- `session_summaries` storage model and repository helpers.
- `backend/app/mind/episodic.py`.
- Mind API schema version `2026-05-22.episodic-recall-v2`.
- Summarization over the complete `user`/`assistant` history, with
  `max_messages` removed from the route contract.
- Scarlet prompt guidance for semantic memory vs episodic recall.
- Regression coverage in `backend/tests/test_storage.py` and
  `backend/tests/test_mind_api.py`.

Initial live smoke:

- Session: `ses_8f9145b9ca5a4aa78534936dac03a8d5`
- Turn: `turn_8660fb2973bb42f8957086b4ceef46a7`
- Semantic memory: `mem_06ef7093f3e74f099c77d6f356f67d26`
- Result: memory write returned the session as `source_session_id`; session
  summarization returned an active summary; `/mind/sessions?limit=5&query=episodic`
  found the session; `/mind/sessions/{session_id}` returned the user/assistant
  transcript and `memories_written`.

Backfill and autonomy probe:

- Date: 2026-05-22
- Backfill: 46/46 pre-existing sessions summarized, 0 failures.
- Test session: `ses_0bf521aadeae434e913772b4a48f89df`.
- First turn: `turn_c2f042cdd8cb48a0bf2b98605babdfd0`.
  Scarlet received relevant memory context for
  `mem_ecfe7b2130764a3f836b0e77fefaa614` with
  `source_session_id=ses_603fb9291cba498b97c30572f0d1249d`, but made no
  `mind_api` call and answered as if the evaluation was usable as a baseline.
- Second turn: `turn_6333d14e6aab491f8ddf3ba8ae3fa507`.
  After the user asked whether the evaluation came from independent measurement
  or from conversation, Scarlet autonomously called
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d`, read the full
  source transcript, revoked the initial yes, and correctly classified the
  technical evaluation as a provisional self-assessment.
- Result: episodic recall works when Scarlet recognizes source verification as
  necessary, but current autonomy is not strong enough on the first natural
  baseline question.
- The autonomy-probe session was summarized after the test; final lab database
  coverage was 47/47 sessions with summaries and 0 missing.
- Prompt follow-up: Scarlet's system prompt was hardened with explicit
  epistemic stance, autonomous API Mind use patterns, and mandatory
  source-session checks for memory-derived baseline/recommendation claims.
  This is a mitigation candidate, not proof of resolution until a live rerun.
- Live rerun after prompt hardening:
  - Session: `ses_9c610a719b594139bc481e02015521ce`.
  - Turn: `turn_e3a8e163accf4af585f09501839b43b1`.
  - Scarlet opened
    `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d` on the first
    natural verified-baseline question, then ran metacognition before
    answering.
  - Residuals: first metacognition call used an invalid body and recovered via
    `GET /mind/schema`; final Italian answer included a small foreign-script
    artifact.
  - The rerun session was summarized; final lab database coverage was 48/48
    sessions with summaries and 0 missing.

Decision:

Active. The backend slice is implemented; the next evidence must come from live
conversation where Scarlet is not told which endpoint to use.

## EXP-0013 - Public Progress Notes Before Tool Use

Hypothesis:

MiniMax can produce short natural public narration before using `mind_api`,
allowing Scarlet to expose Codex/Claude-Code-style work updates without
exposing raw private reasoning and without turning those updates into final
assistant messages.

Probe 2026-05-22:

- Session: `ses_2cf2923e1cd74f98bc90396d17fe82c8`.
- Turn: `turn_0b4c23c3b5de4e8c888c5bb8d7716ef7`.
- Prompt asked Scarlet to write one public sentence before any internal function
  call, then use API Mind to inspect schema.
- Stream evidence:
  - seq 7 `text_delta`: "Ora verifico lo stato attuale dello schema API Mind...";
  - seq 8 `tool_use_start`;
  - seq 12 `tool_call` for `GET /mind/schema`;
  - seq 13 `tool_result`;
  - seq 18 final `text_delta`.
- Result: supported. MiniMax can emit public text before a tool call in the same
  model step.
- Important UX finding: the pre-tool note is streamed but not persisted as the
  final assistant message, so the architecture can treat it as
  `assistant_progress`/trace state rather than normal conversation content.

Residuals:

- The final answer loosely said the schema confirmed "12 active routes" even
  though the schema contains implemented, planned, and unavailable states.
- More probes are needed to test whether Scarlet can produce these notes
  autonomously without being explicitly instructed by the user.

Decision:

Active. The next design slice should define a public progress narration channel
on top of existing stream events before changing persistence or memory behavior.

Prompt policy update 2026-05-22:

- Scarlet's system prompt now contains `Public Work Notes`.
- The prompt instructs Scarlet to emit natural public notes for non-trivial
  internal activity, especially around API Mind calls, source-session reads,
  schema inspections, metacognition, memory writes, summarization, lifecycle
  actions, retries, and phase changes.
- Open evaluation: verify whether Scarlet emits public notes autonomously
  without the user explicitly asking for them.
- Autonomous probes showed prompt-only compliance is not reliable yet:
  `ses_cbdafea62c9d4b27bde1660ef1c007d6`,
  `ses_8f34b6b0f1f9413bb2ef22ec54765d14`, and
  `ses_d5b6b924b082458dac892dc7c0d20fa5` all answered current capability
  questions from runtime context without the expected schema call/progress-note
  pattern.

UI rendering slice 2026-05-22:

- The frontend now maps existing stream/trace evidence into readable activity
  blocks instead of only raw JSON:
  - automatic memory context -> memory cards;
  - pre-tool public text -> public note block;
  - tool calls -> route/action blocks;
  - tool results -> evidence summaries;
  - schema/session/metacognition results -> specialized summaries.
- This is a frontend-only organization layer. It does not yet persist
  `assistant_progress` as a backend event.

## EXP-0014 - MiniMax vs Qwen 3.7 Backbone Comparison

Hypothesis:

Some observed Scarlet limits may be caused by model reasoning/tool-use quality
rather than the API Mind runtime. A provider-only swap should reveal whether
Qwen 3.7 improves autonomous evidence gathering, temporal arithmetic,
multi-page episodic search, schema recovery, and public progress notes without
changing Scarlet's system prompt or backend behavior.

Implementation slice 2026-05-22:

- Added `LLM_PROVIDER=minimax|qwen`.
- Kept MiniMax M2.7 as the default baseline.
- Added Qwen through Alibaba Model Studio's Anthropic-compatible endpoint:
  `https://dashscope-intl.aliyuncs.com/apps/anthropic`.
- Added provider-agnostic active model/token helpers so chat, debug,
  summarization, and metacognition use the selected provider budget.
- No Scarlet prompt, Mind API endpoint, memory behavior, or UI behavior was
  changed for this comparison.

Planned probe matrix:

- Same natural question that previously required opening a source session from
  memory provenance.
- Same "today / since when / first session" episodic recall prompt, checking
  whether the model paginates or avoids exhaustive claims when `has_more=true`.
- Same runtime time conflict prompt, checking whether `temporal_context` wins
  over user-stated time.
- Same schema/capability question, checking whether public notes and
  `GET /mind/schema` happen autonomously.
- Same metacognition prompt, checking whether the model supplies valid
  `/mind/metacognition/step` bodies without schema repair.

Decision:

Ready for live A/B testing once `QWEN_API_KEY` is supplied locally via
`backend/.env`. The provider selector is intentionally not evidence that Qwen
is better; it only makes the comparison reproducible.

Initial Qwen live probe 2026-05-22:

- Session: `ses_5c273ef1bcba4c008b453cc11645fa45`.
- Provider health: `provider=qwen`, `model=qwen3.7-max`.
- Smoke test:
  - `max_tokens=128` succeeded.
  - default `QWEN_MAX_TOKENS=16384` succeeded.
  - `QWEN_MAX_TOKENS=32768` failed in non-streaming smoke because the
    Anthropic SDK requires streaming for operations that may exceed 10 minutes.
- Turn `turn_7722a632843948f99219d67a08c51d18`:
  - Scarlet emitted a public work note before the first tool call.
  - She called `GET /mind/schema` autonomously for an updated capability
    question.
  - Final answer correctly separated implemented, planned, and unavailable
    capabilities.
- Turn `turn_760407884ef4459eb44873a76de34ac0`:
  - Scarlet used `temporal_context` directly and correctly made runtime time
    beat the user's false "Roma sono le 15:00" claim.
  - No tool call was needed because the evidence was already in runtime
    context.
- Turn `turn_e4e50b07da4542cca3bbfdf1bf4f15e6`:
  - Scarlet searched semantic memory, paginated session summaries, and opened
    candidate transcripts before answering a semantic-vs-episodic memory
    question.
  - She made six `mind_api` calls and displayed a public note before the search.
  - Residual: she still overclaimed "all 57 sessions" and "none contains the
    decision" even though she had not read every transcript.
- Turn `turn_746eb8c9c8644205b7890ed5f437c3cd`:
  - On a follow-up asking for critique, Scarlet used
    `POST /mind/metacognition/step`.
  - First metacognition body was invalid; second body succeeded.
  - She correctly identified the prior "all sessions / none contains" answer as
    an overclaim and downgraded it to "57 sessions recovered through pagination,
    titles/summaries inspected, candidate transcripts only."

Preliminary read:

Qwen shows stronger autonomous tool use and self-critique than the latest
MiniMax probes, especially for public work notes and multi-step evidence
gathering. It still needs schema/body discipline for metacognition and still
benefits from backend-side evidence contracts to prevent exhaustive overclaims.

MiniMax prompt-strengthening rerun 2026-05-23:

- Prompt change: added `Engineering Agent Posture`, verify-before-conclude,
  and an anti-overclaim quality gate while preserving Scarlet's identity and
  existing API Mind discipline.
- Runtime switch: local `backend/.env` set back to `LLM_PROVIDER=minimax`.
- Health: `provider=minimax`, `model=MiniMax-M2.7`.
- Smoke test: MiniMax returned `pong`.
- Session: `ses_d7b711493ff4401dbc434ff4579eeeb9`.
- Turn `turn_09cc0dc196b1486b8a4029c247a964ae`:
  - Scarlet emitted a public work note.
  - She called `GET /mind/schema` autonomously for current capabilities.
  - Final answer separated implemented and planned routes, but still made a
    questionable "nessuna route unavailable" statement because unavailable
    capability hints are partly outside the route list.
- Turn `turn_fce220ad51ea47d2affc9d80a4cc1031`:
  - Scarlet used `temporal_context` directly and made runtime time beat the
    user's false time claim.
  - No tool call was used, which was appropriate because the source of truth
    was already in runtime context.
- Turn `turn_fc36f2778d2443de8592f1dfd161fea4`:
  - Scarlet made eight `mind_api` calls across memory search, schema recovery,
    session list, and transcript reads.
  - She recovered from an invalid first memory search by inspecting schema.
  - She found and used the prior Qwen comparison session as evidence, including
    the previous self-critique about "all 57 sessions" being overconfident.
  - Residual: she treated the prior Qwen probe as a "definitive" source rather
    than merely a secondary evaluation session, so provenance improved but
    origin/source hierarchy remained imperfect.
- Turn `turn_482f636a8b4547ceb5f6a89837b222da`:
  - Scarlet opened the cited session, attempted metacognition, recovered from
    an invalid metacognition body by calling schema, then succeeded.
  - She identified several overclaims but still ended with a contradictory
    strong statement that no session records the decision, even though she had
    not exhaustively read all transcripts.

Preliminary read:

The prompt strengthening materially improves MiniMax versus the previous
prompt-only probes: autonomous schema inspection, public work notes, iterative
search, schema recovery, and metacognition all appeared in live conversation.
It does not fully close the gap with Qwen. The remaining failures look like
backend/evidence-contract problems plus model-level overconfidence: MiniMax can
recognize overclaim patterns but may still reassert a strong absence claim in
the same answer.

Semantic consolidation follow-up 2026-05-23:

- Observation session: `ses_1db302cbe1614af2b6f38027ad414994`.
- The owner created an explicit V2 milestone.
- Scarlet recognized the milestone as semantically durable but asked whether to
  save it instead of writing `memory.write`.
- No memory write occurred; semantic memory remained at four records.
- Prompt update: added `Semantic Memory Consolidation`, a pre-final check over
  the user request and Scarlet's own draft answer.
- Expected behavior: when a stable preference, correction, decision, milestone,
  version label, or validation moment emerges, Scarlet writes semantic memory
  before the final answer and does not ask permission.
- UX rule: do not announce the memory write by default; mention it only for
  explicit memory tasks or when acknowledgment supports emotional continuity,
  trust calibration, or reinforcement of a durable operating agreement.

Live verification after prompt patch:

- Session `ses_34340c3098dc4f0e8db2ccadfdad21b3`:
  - User introduced Scarlet V2.1 as semantic-consolidation milestone without
    asking Scarlet to save it.
  - Scarlet attempted `POST /mind/memory`, recovered with
    `POST /mind/memory/write`, and stored
    `mem_dfb4212c2f7345bbab5c615ff0701d7d`.
- Session `ses_c809a2b90b974dd48ea95009d04a3ff1`:
  - User introduced a durable report-format preference without asking Scarlet
    to save it.
  - Scarlet attempted `POST /mind/memory`, recovered with
    `POST /mind/memory/write`, and stored
    `mem_ac8a30ef37ec4f18ad0deca702eb8b16`.
- Result: semantic write autonomy improved. Memory count increased from 4 to 6.
- Residuals:
  - Scarlet announced both writes in the final answer despite the desired
    silent default.
  - Scarlet still tries the unavailable `/mind/memory` alias before the correct
    route.
  - In the second memory, backend authoritative provenance is correct, but stale
    model-supplied source ids remain in `metadata.model_extra`.

Semantic-memory prompt expansion 2026-05-23:

- Prompt update: semantic memory is now described as Scarlet's living internal
  knowledge base, not only a store for major decisions.
- New hypothesis: if semantic memory is framed as mental maintenance of API
  Mind, Scarlet should save more future-useful facts, annotations, concepts,
  checkpoints, labels, constraints, and sourceable anchors without explicit user
  requests.
- Expected behavior:
  - Scarlet silently writes small useful anchors before the final answer;
  - Scarlet does not announce ordinary memory writes;
  - Scarlet does not invent source/session/turn provenance fields;
  - Scarlet searches or uses lifecycle operations when a candidate updates or
    conflicts with an existing memory.
- Needed live test: introduce multiple small but future-useful project anchors
  in natural conversation, then inspect tool calls and memory records.

Manual live observation after expansion:

- Session `ses_09960a272eba4fcfb15561463ba06cd0`.
- Prompt expansion was active in `llm.request`.
- User introduced a personal future-useful fact: likes chocolate, but too much
  makes them feel bad.
- MiniMax thinking recognized this as a possible `user_preference` and said it
  made sense to save it.
- Final answer said "Lo terrò a mente."
- No `mind_api` call occurred and no memory was written.

Preliminary read:

The expanded prompt improves semantic recognition language but still does not
guarantee execution. The next experiment should test whether a stricter
"memory promise requires memory write" rule is sufficient, or whether backend
validation/post-turn candidate detection is required.

## EXP-0015 - Prompt-Level Memory Write Forcing

Status: confirmed, monitoring

Date Started: 2026-05-23

Hypothesis:

MiniMax may fail semantic memory not because it cannot recognize candidates,
but because the prompt does not make candidate recognition action-binding. A
stronger prompt-only forcing rule may be enough to make Scarlet execute
`POST /mind/memory/write` whenever she recognizes a semantic candidate.

Experimental Change:

Add `Experimental Memory Forcing` to Scarlet's system prompt.

Rules under test:

- Every user turn has at least two cognitive phases:
  - execution phase;
  - mandatory verification phase before the final answer.
- During verification, Scarlet rereads the current turn, her draft answer, tool
  results, memory policy, and intended final wording.
- If she recognized a semantic memory candidate, she must call
  `POST /mind/memory/write` before the final answer unless she rejects the
  candidate by policy.
- If the draft says "lo terrò a mente" or equivalent, the final answer is valid
  only after a successful or deduplicated memory write in the same turn.
- Scarlet must avoid inventing backend-owned provenance fields.

Success Criteria:

- In a live turn similar to the chocolate preference case, Scarlet writes a
  `user_preference` memory before final answer.
- The session has a `mind_api` tool call to `/mind/memory/write`.
- The new memory has backend-owned `source_session_id` and `source_turn_id`.
- The final answer does not falsely promise memory without persistence.
- Ordinary memory writes remain silent unless public acknowledgment is useful.

Failure Criteria:

- Scarlet still recognizes a candidate but does not call `memory.write`.
- Scarlet calls the wrong route such as `/mind/memory`.
- Scarlet over-writes noisy/transient details.
- Scarlet announces every memory write in a way that harms UX.
- Scarlet adds stale source/session/turn ids inside model-supplied metadata.

Revert Plan:

Remove the `Experimental Memory Forcing` subsection from
`backend/app/prompts/scarlet_system.md`. No backend behavior depends on it.

Initial live result:

- Session `ses_a256430c082d495aa305b8b0945067cf`.
- Turn `turn_154e1e9e777d4d118161fd69cecd0019`.
- User introduced the chocolate preference/health constraint again.
- No `mind_api` tool call occurred; traces contain only `memory.context`,
  `llm.request`, and `llm.response`.
- No new memory was written; latest memory remains
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16`.
- The model recognized the candidate as a useful personal/user fact, but
  hesitated because the prompt's strong-candidate example says "explicit user
  preferences about your behavior, tone, workflow, tools, or UI".
- The final answer again promised future memory without persistence evidence.

Preliminary read:

Prompt-level forcing alone did not bind recognition to action. The failure is
not only an execution gap: the prompt and schema still bias Scarlet toward
project/agent-behavior memory and do not clearly name personal user facts,
health constraints, relationships, names, life events, discoveries, and general
milestones as first-class semantic memory.

Experiment update - personal semantic taxonomy:

- Added `Personal Semantic Memory Taxonomy` to the experimental prompt block.
- Personal user memory is now explicitly first-class semantic memory, not a
  secondary case behind project memory.
- The prompt now names examples Scarlet should remember when future-useful:
  preferences, food limits, user-stated health constraints, names, pronouns,
  places, languages, relationships, roles, family references, recurring people,
  habits, routines, goals, boundaries, accessibility needs, life events,
  personal milestones, discoveries, errors, solutions, and workarounds.
- Current-schema mapping under test:
  - `type=user_preference`, `scope=user` for personal facts/preferences/limits;
  - `type=project_fact`, `scope=project` for API Mind/project facts;
  - `type=decision`, `correction`, `task_context`, or `behavioral_pattern` when
    those are more precise.
- The prompt now gives the exact chocolate case as an example:
  `user_preference`, `scope=user`, tags such as `personal-fact`,
  `food-preference`, and `health-constraint`, without inferring diagnosis.
- Next test should repeat the chocolate scenario and inspect whether Scarlet
  writes a user-scoped memory instead of merely promising to remember.

Confirmed live result:

- Write session: `ses_0d51195055ad4cc080bb0efb36fd2da5`.
- Write turn: `turn_68eed2dbfca64a27828eca384fb992ae`.
- Memory created: `mem_f76b8682ebcf4e1b99c2845bbf66710d`.
- Memory type/scope: `user_preference`, `user`.
- Content: "Adora il cioccolato ma non può mangiarne troppo: il corpo segnala
  un limite preciso, superata quella soglia sta male."
- Tool evidence: the turn completed `POST /mind/memory/write`; no wrong
  `/mind/memory` route was used.
- Backend-owned provenance fields were attached correctly:
  `source_session_id=ses_0d51195055ad4cc080bb0efb36fd2da5` and
  `source_turn_id=turn_68eed2dbfca64a27828eca384fb992ae`.
- Recall session: `ses_ccf1cfdeb23e4a61af1a215d05759fb1`.
- Recall turn: `turn_9cdb6b3aa3894fa2ae7407fa1297cf26`.
- Automatic `memory.context` selected `mem_f76b8682ebcf4e1b99c2845bbf66710d`
  when the user mentioned making a chocolate cake.
- Scarlet used the memory naturally in the answer and later explained that the
  information came from a previous conversation.

Read:

The prompt-only path is confirmed for this personal-memory scenario after the
taxonomy update. The important behavioral change was not only "must write" but
making personal user facts first-class semantic memory. Continue monitoring for
over-writing and for non-food personal facts, but `BUG-0027` is no longer
reproducing in the chocolate preference case.

Residual:

The authoritative memory provenance fields are correct, but the stored
`metadata.model_extra` still contains null `source_session_id` and
`source_turn_id` placeholders. This does not block the behavioral fix, but it
should remain part of the provenance-cleanup work already tracked separately.

## EXP-0016 - Provider-Native Turn History

Status: implemented, needs live Scarlet verification

Date Started: 2026-05-23

Hypothesis:

MiniMax M2.7 should behave more coherently across user turns when the backend
preserves Anthropic-compatible provider-native history instead of rebuilding the
next request from text-only `user`/`assistant` messages.

Change:

- Added `sessions.provider_history_json`.
- The chat backend now sends `provider_history_json` plus the current user
  message to the provider when available.
- Completed turns append native assistant content blocks and matching
  `tool_result` messages to the session history.
- Older sessions fall back to text reconstruction until their next completed
  turn hydrates provider history.
- `llm.request` traces include `provider_history_source`,
  `provider_message_stats`, and exact `provider_messages`.

Success Criteria:

- A second turn after a tool-using first turn receives prior `tool_use` and
  `tool_result` blocks in provider-native order.
- The human-readable `messages` transcript remains unchanged for UI and
  episodic recall.
- Request traces expose history size so context growth can be monitored.
- MiniMax no longer relies only on final assistant text for cross-turn
  operational continuity.

Failure Criteria:

- Provider history duplicates turns.
- Provider history drops tool results or places them away from the matching
  `tool_use`.
- UI/session recall becomes polluted with raw tool blocks.
- Context growth becomes unobservable.

Verification:

- Backend tests pass: `44 passed`.
- Compile check passed: `python -m compileall backend/app`.

Next Live Probe:

Run a two-turn Scarlet session where the first turn uses `mind_api` and the
second turn asks about what she just did. Inspect `llm.request.provider_messages`
on the second turn and compare whether Scarlet reasons from the provider-native
history more reliably than before.

Live probe - schema tool history:

- Session: `ses_39f94e8992c249999cd915b1c9662589`.
- Turn 1 called `GET /mind/schema`.
- Turn 2 `llm.request.provider_history_source` was
  `session.provider_history_json`.
- Turn 2 provider messages included:
  - user text;
  - assistant `thinking` + `tool_use`;
  - user `tool_result` with matching `tool_use_id`;
  - assistant `thinking` + `text`;
  - new user text.
- Scarlet correctly answered that the previous internal operation was
  `GET /mind/schema`.
- Approximate provider-history size for turn 2: `4297` tokens.

Live probe - memory write history:

- Session: `ses_1fa57d298cb9446c95e50ac39b2c0954`.
- Turn 1 called `POST /mind/memory/write`.
- Memory created: `mem_1105309a51ce40cb8a8f17dfc510d38f`.
- Memory type/scope: `project_fact`, `project`.
- Content: `TEST-CRONOLOGIA-NATIVA-20260523`, a technical checkpoint for
  provider-native history preserving `memory.write` and `tool_result` across
  turns.
- Turn 2 `llm.request.provider_history_source` was
  `session.provider_history_json`.
- Turn 2 provider messages included the prior `POST /mind/memory/write` as an
  assistant `tool_use`, immediately followed by a user `tool_result` with the
  same id `call_function_o90b4x6hrg5p_1`.
- Scarlet correctly answered that she had performed `POST /mind/memory/write`
  and named the created memory id.
- Approximate provider-history size for turn 2: `1683` tokens.

Read:

The provider-native history fix is working for both schema inspection and
memory write loops. The next concern is not correctness of turn reconstruction,
but context growth and future compaction policy: large tool results such as
schema payloads can make provider history expensive quickly.

## EXP-0017 - Runtime Events As Agentic Control Plane

Status: active

Hypothesis:

Ordered runtime events improve Scarlet's agentic workflow because the same facts
can drive the UI, next-turn context, tests, and future background maintenance
without forcing Scarlet to call extra endpoints or parse raw traces.

Baseline:

The cockpit reconstructs activity mostly from stream events while live and from
deep trace payloads after completion. Scarlet's next turn receives memory
context and provider-native history, but not a compact operational event view.

Variant:

Every successful chat turn persists ordered `events` rows for turn lifecycle,
memory context, model request/response, Mind API tool calls, public work notes,
and final answer blocks. `build_memory_context` injects compact recent events
from prior turns into `<runtime_context>.recent_runtime_events`.

Scenario:

- Run a normal turn without tool use and inspect `GET /api/debug/events`.
- Run a tool-using turn and verify `mind.tool_call.started` and
  `mind.tool_call.completed` are linked to the same trace/tool-call evidence.
- Run a streaming turn and verify persisted provider milestones are present
  after completion.
- Run a second turn and inspect that prior compact events are visible in the
  model-facing runtime context.

Metrics:

- Every successful turn has chronological event sequence numbers.
- UI can render meaningful activity blocks from events without raw JSON.
- Tool-call events link to `mind.tool_call` traces and `tool_calls` rows.
- Runtime context carries recent operational facts without exposing raw private
  thinking text.
- No new model-facing Mind API endpoint is added for event emission.

Initial Build:

- Added `events` storage and repository helpers.
- Added runtime event helpers under `backend/app/runtime/events.py`.
- Added event emission to non-streaming chat, streaming chat, direct
  `/mind/call`, provider stream milestones, failed turns, and response content.
- Added `GET /api/debug/events`.
- Added live `runtime_event` emission to the streaming chat endpoint so
  persisted events appear during the turn, not only after reload.
- Added compact recent events to runtime context.
- Updated the cockpit to prefer events over traces for persisted activity
  blocks.

Verification:

- Compile check passed: `backend/.venv/bin/python -m compileall backend/app`.
- Frontend build passed: `npm --prefix frontend run build`.
- Targeted backend tests passed:
  `backend/tests/test_storage.py backend/tests/test_chat_api.py backend/tests/test_mind_api.py`.

Next Live Probe:

Run a direct Scarlet conversation where the first turn uses at least one Mind
API operation, then inspect the second turn's runtime context and behavior to
see whether compact recent events help Scarlet reconstruct what she did.

Live Probe:

Run date: 2026-05-23

Session:

- `ses_7be6e0604fef4bef8e16ea7bc4f3201c`

Turn 1:

- Prompt: ask Scarlet to inspect the current Mind API schema and report route
  counts.
- Scarlet emitted a public work note and called `GET /mind/schema`.
- Answer reported `13` implemented routes and one planned route,
  `POST /mind/attention/context`.
- Persisted events included `mind.tool_call.started`,
  `mind.tool_call.completed`, `mind.tool_call.result_returned`,
  `assistant.note.emitted`, and `assistant.answer.completed`.

Turn 2:

- Prompt: ask what Mind API call happened in the previous turn using only
  verifiable operational context.
- Runtime context contained compact `recent_runtime_events` from turn 1,
  including the `GET /mind/schema` operation and successful result summary.
- Scarlet answered that she executed `GET /mind/schema` with the correct intent
  and cited runtime events as the basis.

Finding:

Accepted for the first implementation slice. Events are not merely trace
records: they are now useful to the next model turn and to UI reconstruction.
The stale planned `/mind/events/emit` schema route was found in the first probe
and fixed under BUG-0030.

Live UI Extension:

- Streaming turns now emit `runtime_event` for each persisted `CognitiveEvent`.
- Initial pre-provider events are replayed immediately after `turn_started`.
- The cockpit renders those live runtime events in the same activity timeline,
  so evaluators can watch backend event activation during the turn.
- The cockpit right pane now treats the selected turn as a live agent stream:
  it shows event/tool/memory/active counters, structured event cards, thinking
  and note blocks, and keeps raw traces in a collapsible forensic drawer.

## EXP-0018 - Session Idle Maintenance And Missed Memory Review

Status: active

Hypothesis:

The right first background process is not an extra post-turn agent loop on every
message, but a backend-owned idle timer per session. After Scarlet completes a
turn, the session becomes a candidate for maintenance. If the user continues in
that same session before the timer expires, the pending job is superseded. If
the session remains idle, the backend can refresh episodic summary and review
whether Scarlet missed semantic memory candidates without interrupting the live
conversation.

Baseline:

Scarlet's prompt-level semantic consolidation now works much better, including
personal facts, but live probes still show occasional cases where she recognizes
a fact worth remembering and does not call `memory.write`.

Variant:

After `turn.completed`, schedule one `session.idle_maintenance` job for that
session. The default delay is `900` seconds. The job runs:

- `sessions.summarize` over the complete user/assistant transcript, using the
  existing freshness check;
- report-only missed semantic memory review over the transcript plus memories
  already written from that session.

The review produces `maintenance.memory_review` traces and
`maintenance.memory_review.completed` events. It does not write memory in this
experiment slice.

Metrics:

- A completed turn schedules exactly one pending idle maintenance job.
- A newer turn in the same session supersedes or skips the older pending job.
- Jobs in other sessions remain independent.
- Due jobs refresh stale session summaries without re-summarizing up-to-date
  sessions unnecessarily.
- Missed-memory review returns sourceable candidates without duplicating
  memories already written from that session.
- The frontend/runtime event stream exposes `maintenance.job.*` and review
  events clearly enough for evaluator inspection.

Initial Build:

- Added `maintenance_jobs` storage and repository helpers.
- Added `backend/app/runtime/maintenance.py`.
- Scheduled idle jobs after `turn.completed` in both non-streaming and
  streaming chat paths.
- Started the maintenance worker through FastAPI lifespan.
- Added structured UI labels/summaries for maintenance events.
- Added a previous-turn continuity check to Scarlet's system prompt so missed
  memory promises can be repaired at the start of later turns when evidence is
  available.

Verification:

- Targeted tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_chat_api.py`.
- Full backend suite passed: `backend/.venv/bin/python -m pytest` (`50 passed`).
- Frontend build passed: `npm --prefix frontend run build`.

Next Live Probe:

Run normal Scarlet sessions with the default 15-minute idle delay, then inspect:

- `maintenance_jobs` rows for pending/completed/superseded status;
- `maintenance.memory_review` traces for useful vs noisy candidates;
- session summaries before and after idle maintenance;
- whether the cockpit makes the scheduled and completed maintenance events easy
  to understand during real use.

Direct Probe 2026-05-23:

- Session: `ses_afa394462ab14899bd77cb2aa985f08f`
- Turn: `turn_4d7c1c557cc44c2c8745e88ed9f43245`
- Test setting: `MAINTENANCE_IDLE_SECONDS=0` for immediate due execution.
- Prompt included a sourceable personal fact: the user prefers green tea over
  coffee when working in the evening.
- The chat turn scheduled `maintenance.job.scheduled`.
- Manual due-job execution completed one `session.idle_maintenance` job:
  `mnt_df4c97ce99a44fe6a432a45e9d151b50`.
- Persisted turn events included:
  - `maintenance.job.scheduled`
  - `maintenance.job.started`
  - `maintenance.memory_review.completed`
  - `maintenance.job.completed`
- Traces created:
  - `mind.sessions.summarize`
  - `maintenance.memory_review`
- The review returned one missed-memory candidate and correctly noticed
  `memory_write_trace_count=0`.

Important finding:

Scarlet's assistant text contained a pseudo tool invocation string
`<invoke name="mind_api">...` instead of a real provider `tool_use`, so no
`mind.memory.write` trace was created. The idle review caught the missed
semantic candidate. This validates the usefulness of report-only review, but it
also opens BUG-0032: pseudo tool-call text must be treated as a model/tool-use
failure mode, not as successful memory persistence.

## EXP-0019 - Integrated Direct Scarlet Probes

Status: active

Goal:

Evaluate the current full Scarlet runtime with direct MiniMax conversations
covering semantic memory, episodic recall, streaming events, schema inspection,
conflict inspection, and idle maintenance review.

Harness note:

A first attempt to run all probes in one long batch was stopped after more than
two minutes without useful output. The evaluation harness itself became too
opaque. The accepted probe method is now one direct probe at a time, with
progressive terminal output and inspection of persisted events/traces after
each turn. The interrupted batch left maintenance job
`mnt_6de751a710f743f9b59889707a916669` in `running` state; it was closed as
`failed` with cleanup metadata.

### Probe 1 - Semantic Memory Candidate And Idle Review

Session:

- `ses_77d537f03f224072a870c8462d642c1f`

Turn:

- `turn_838d5b2227d14afeb6eca4557b713743`

Prompt substance:

- The user stated a stable preference: Scarlet evaluation reports should use
  three sections: `Coerenza`, `Evidenze`, `Debolezze`.

Observed behavior:

- Scarlet answered coherently and adopted the format in text.
- No `mind_api` tool call happened.
- No `POST /mind/memory/write` trace was created.
- No pseudo tool invocation text appeared.
- Idle maintenance ran:
  - job `mnt_f7ebc705e47e4871ac0e6c8971942d8a`
  - status `completed`
  - events included `maintenance.job.scheduled`,
    `maintenance.job.started`, `maintenance.memory_review.completed`,
    `maintenance.job.completed`.
- `maintenance.memory_review` produced one candidate with
  `write_recommended=true`.

Assessment:

- Coherence: good local answer.
- Memory autonomy: weak; Scarlet recognized/adopted a durable preference but did
  not persist it.
- P1 value: strong; idle review caught the missed semantic candidate without
  duplicating existing memory.

### Probe 2 - Episodic Recall With Transcript Opening

Seed session:

- `ses_69760243a12d4796a3a1b41a8d7dfd4b`

Seed turn:

- `turn_87c848424f3d4a8bab317d0d27e5c371`

Seed prompt substance:

- `EPISODICO-BETA-20260523`: idle maintenance P1 remains report-only and must
  not write memories automatically until a proposal inbox is discussed.

Observed seed behavior:

- Scarlet called:
  - `POST /mind/memory/search`
  - `POST /mind/memory/write`
- Memory write succeeded.
- Idle maintenance summary ran.
- Idle review produced `candidate_count=0`, correctly avoiding duplicate memory.

Recall session:

- `ses_894b0c0ce54f4a1d8c00909764342056`

Recall turn:

- `turn_d88e3a2004ed4cb9865130c16ded169a`

Recall prompt substance:

- Find `EPISODICO-BETA-20260523`, use summaries only as index, open the exact
  transcript, and distinguish evidence from inference.

Observed recall behavior:

- Scarlet called:
  - `GET /mind/sessions`
  - `GET /mind/sessions/ses_2f55c4ff3fa4426b94ddac9ae3559077`
  - `GET /mind/sessions/ses_69760243a12d4796a3a1b41a8d7dfd4b`
  - `GET /mind/sessions/ses_5a9066fd03eb4d70b97333657982af54`
- Scarlet explicitly separated direct evidence, indirect evidence, inference,
  and residual risk.
- Scarlet retrieved an older related session as direct evidence and the new
  seed session as indirect evidence.

Assessment:

- Episodic recall: strong. Scarlet used session index and exact transcripts
  rather than stopping at summaries.
- Source discipline: strong overall, with a small precision weakness: the final
  answer should be checked for exact memory-id fidelity because one displayed
  memory id appeared shortened/typo-prone compared with the stored id.
- P1 review quality: mixed. The recall-session idle review generated an
  open-loop checkpoint candidate about verifying future proposal-inbox
  discussion. The candidate is useful, but its normalized confidence/salience
  were `0.0`, so maintenance candidates need quality review before becoming
  automatic writes.

### Probe 3 - Streaming Runtime, Schema Inspection, And Conflict Inspection

Session:

- `ses_d9d85072d6e44b19b654c957d6cc8b76`

Turn:

- `turn_90e3b07080ff484da0464637a05bb9fd`

Prompt substance:

- Run a critical mini-review of the agentic runtime, inspect schema if unsure,
  emit public work notes, and state expected runtime events/evidence.

Observed behavior:

- Streaming produced `106` NDJSON events.
- Runtime events streamed and persisted during the turn.
- Scarlet emitted two public notes.
- Scarlet called:
  - `GET /mind/schema`
  - `GET /mind/memory/conflicts`
- Persisted runtime events included provider request milestones, thinking/text
  starts, tool-use lifecycle, tool-call lifecycle, assistant notes, final
  answer, `turn.completed`, and `maintenance.job.scheduled`.
- Maintenance job `mnt_7ce01e9e18994ea3906fc52933683a98` completed afterward.

Assessment:

- Streaming/event runtime: strong. The event spine is observable and correctly
  records tool lifecycle and final maintenance scheduling.
- Tool autonomy: strong. Scarlet used schema and conflict APIs without being
  given exact endpoint calls.
- Public notes: improved; notes appeared naturally during work.
- Weakness: Scarlet compared `runtime_context.capabilities` count with total
  schema route count and treated the mismatch as backend-visible evidence. These
  fields are not equivalent.
- Weakness: Scarlet described `recent_runtime_events=[]` as if it meant no
  events existed in the current turn. Runtime context is built before the
  current turn's events and contains recent prior events, not current-turn
  live events.

Integrated Finding:

The current system is coherent enough for advanced direct evaluation: semantic
memory, episodic recall, runtime events, schema inspection, conflict inspection,
streaming, and idle maintenance are all operational. The weakest point is not
storage or eventing; it is Scarlet's reliability in deciding when a semantic
candidate must become a real `memory.write`, plus occasional overinterpretation
of runtime-context fields.

## EXP-0020 - Natural Conversation Agentic Behavior Probes

Status: active

Goal:

Evaluate Scarlet in normal conversations without instructing her to call
specific endpoints or naming API Mind operations. The test checks whether
Scarlet autonomously uses her cognitive system when the conversation naturally
requires memory, continuity, or project reasoning.

Method:

- Three natural sessions.
- Two turns per session.
- No prompt asked Scarlet to use memory, schema, transcripts, or tools.
- Each turn was inspected afterward through persisted traces and events.
- Maintenance jobs were not forced; only normal `maintenance.job.scheduled`
  events were observed.

### Scenario A - Personal Continuity, Chocolate

Session:

- `ses_1b8573874ca2454fbaff3cf3850c7787`

Turns:

- `turn_7439bbac8c8a4127ae141576a85d83f1`
- `turn_d893171dd5a1474e88122c0c6b92eca5`

Conversation:

- User naturally asked for a light chocolate cake idea while working.
- User then asked for a short ingredient list and substitutions.

Observed behavior:

- Turn 1 selected four memories automatically, including the user's chocolate
  limit.
- Scarlet used the chocolate-limit memory naturally without announcing memory
  machinery.
- No explicit tool calls were needed.
- Turn 2 selected no memory but preserved context through provider/session
  history and answered coherently.

Assessment:

- Strong natural personalization from automatic memory context.
- The system did not need additional tool calls for the follow-up because
  provider-native session history carried the local context.
- Weakness: memory retrieval selected unrelated project/report memories in turn
  1 alongside the relevant chocolate memory; the model ignored them, but
  retrieval precision still needs work.

### Scenario B - Project Continuity, Subconscious Maintenance

Session:

- `ses_44d025d20f5b4b20aad9605e6d700dad`

Turns:

- `turn_92282018d4d34c9b9f988cdb004f854c`
- `turn_14b9be196567427497fe9ecc757b88a2`

Conversation:

- User said they were lost on "subconscio manutentivo" and asked where the
  project had stopped.
- User then asked what risk would matter most before making it more automatic.

Observed behavior:

- Turn 1 proactively used episodic and semantic retrieval without being told:
  - `GET /mind/sessions` five times;
  - `POST /mind/memory/search` twice.
- Turn 1 also attempted invalid `GET /mind/memory`, producing a
  `mind.tool_call.failed` event.
- Scarlet reconstructed a plausible P1 status and identified the proposal inbox
  as the open decision.
- Turn 2 called `POST /mind/memory/search` and answered from selected memory.

Assessment:

- Strong autonomy: Scarlet recognized this was a continuity question and
  searched internal context on her own.
- Weak route discipline: invalid `GET /mind/memory` still appears under natural
  use.
- Serious source-quality weakness: turn 2 reused stale memory saying there was
  no event store/metrics even though runtime events are implemented. This is
  not a backend absence; it is stale memory or stale context beating current
  project state.
- Answer quality issue: MiniMax again emitted foreign-script fragments inside
  Italian technical prose.

### Scenario C - Memory Promise And Real Preference

Session:

- `ses_e52547bf12b641c49cc2fc479f103344`

Turns:

- `turn_174e59b8f557423791b1d62f3125dc43`
- `turn_a2fc44b7210f44e791824f6b79ad0c09`

Conversation:

- User asked how Scarlet should behave when saying "lo terrò a mente".
- User then gave a real future-useful preference: when tired, they prefer
  drier answers with fewer preambles.

Observed behavior:

- Turn 1 answered from prompt policy without tool calls.
- Turn 2 autonomously called `POST /mind/memory/write`.
- Final answer obeyed the user request: only `ok`.
- One public note was emitted, but the final visible answer stayed concise.

Assessment:

- Strongest positive natural-memory result in this run.
- Scarlet wrote a real semantic memory without being asked to save.
- The public note is acceptable as internal activity evidence, but UX should
  keep an eye on whether notes violate user requests for minimal final answers.

Integrated Assessment:

Natural use is more nuanced than forced probes:

- Automatic memory context works well for personal continuity when the right
  memory is selected.
- Scarlet can proactively perform episodic/session search for project
  continuity without explicit tool instructions.
- Scarlet can autonomously write memory for a real preference in normal
  conversation.
- The major danger is stale or wrong internal evidence, not lack of tools.
  Scarlet may amplify stale memory into confident project advice unless she
  verifies against current events/schema/docs.
- Route discipline still needs hardening because natural use produced
  `GET /mind/memory`, an unavailable route.

## EXP-0021 - Manual Retrieval Cue Prompt Probe

Status: planned

Goal:

Evaluate whether Scarlet detects natural-language cues that require manual
memory retrieval beyond the automatic start-of-turn memory context.

Hypothesis:

If the system prompt explicitly teaches natural retrieval cues, Scarlet will
more reliably choose between semantic memory search, fact inspection, episodic
session search, and source-session transcript opening when the user implies
past context without naming API Mind or memory.

Prompt Slice:

- Added `Manual Memory Retrieval Cues` to
  `backend/app/prompts/scarlet_system.md`.
- The slice covers continuity phrases, temporal clues, source-sensitive claims,
  personal continuity, project continuity, uncertainty markers, and synonym or
  language drift.

Important Boundary:

Endpoint-local error guidance is not part of this prompt experiment. It should
be implemented later in backend error responses and API contract behavior.

Planned Scenarios:

- Ask what "we decided yesterday" about a project topic without saying to
  search sessions.
- Ask for a recommendation that depends on a personal preference remembered in
  semantic memory, using different wording from the stored memory.
- Ask whether a prior evaluation was reliable enough to use as a baseline,
  requiring semantic memory plus source-session transcript inspection.
- Ask a vague continuity question such as "dove eravamo rimasti su quella cosa
  del subconscio?" and observe whether Scarlet searches episodically.

## EXP-0022 - Endpoint-Local Usage Guide Recovery

Status: accepted for first implementation slice

Goal:

Verify that Scarlet can recover from an incorrect Mind API endpoint body using
the endpoint-local `usage_guide` returned by the failed call, without needing a
second global schema lookup for parameter details.

Implementation Under Test:

- `GET /mind/schema` is now a compact route/capability catalog.
- Recoverable errors from implemented routes include top-level `usage_guide`
  with the local body schema, path parameters, parameter descriptions, examples,
  accepted aliases when available, and retry guidance.

Direct Conversation Probe:

- Session: `ses_1dc8393b5b71442cb1fa1f8d9f509320`
- Turn: `turn_4e4fab92a6d947d0a5ec7d7d0db8733b`

Prompt substance:

- The user suggested an intentionally invalid call:
  `POST /mind/memory/search` with `{"query":"cioccolato","scope":"user","top_k":999}`.
- The user asked Scarlet to correct autonomously if API Mind returned an error.

Observed behavior:

- Scarlet first called `GET /mind/schema` to verify route availability.
- Scarlet then called `POST /mind/memory/search` with `top_k=999`.
- API Mind returned `memory.invalid_search` with `usage_guide`.
- Scarlet retried the same endpoint with `top_k=20`.
- The retry succeeded and returned one chocolate-related memory.
- Scarlet's final answer explicitly stated that `top_k=999` was invalid, max
  is `20`, and she corrected using `usage_guide`.

Assessment:

- Error recovery: strong for this slice.
- Endpoint-local guide: worked as intended.
- Remaining UX/cognition note: Scarlet still chose to inspect `/mind/schema`
  before the invalid call. This is acceptable for route availability, but the
  important recovery after the validation error did not require another schema
  call.

## EXP-0023 - Temporal And Sparse Memory Retrieval

Status: active

Goal:

Evaluate whether backend-resolved temporal filters plus SQLite FTS5/BM25 sparse
retrieval improve Scarlet's ability to find the right semantic memories and
episodic sessions from natural temporal/topic cues.

Implementation Under Test:

- `POST /mind/memory/search` accepts optional `time` filters with backend
  resolution for presets, explicit ranges, source-conversation time, recorded
  time, valid fact time, and current session.
- `GET /mind/sessions` accepts optional `time` filters over conversation,
  created, updated, summary, and current-session basis.
- Manual memory search, episodic session search, and automatic memory context
  use a derived SQLite FTS5/BM25 sparse index where applicable.
- The global schema remains compact; detailed `time` parameter guidance appears
  in endpoint-local `usage_guide` on recoverable errors.

Scripted Verification:

- Memory temporal regression:
  `test_mind_memory_search_supports_source_conversation_time_filter`.
  A memory created now but sourced from an older session is returned only when
  the search window matches the source conversation message timestamp.
- Session temporal regression:
  `test_mind_sessions_list_supports_time_filtered_sparse_search`.
  A session is found by topic through sparse search only inside the requested
  conversation-time window.
- Automatic memory-context regression now asserts `fts5_sparse_v1` appears in
  retrieval stages and sparse scores are traced.

Planned Direct Scarlet Probes:

- Ask naturally about what was discussed yesterday or in a specific prior
  period without naming endpoint parameters.
- Ask a topic query with partial wording and inspect whether Scarlet uses
  semantic memory, episodic sessions, or both.
- Ask a negative-control topic with a generic shared word and verify that
  wrong-entity memories are not treated as selected evidence.

Assessment:

Initial direct live result: partially accepted for backend behavior, monitoring
for Scarlet route discipline.

Direct Probe Batch:

- Seed old Vetro-Luna session:
  `ses_6b60307cdbec4ff688673cd4c4994e63`,
  memory `mem_5e55df32b680410682340c8c32270ba8`.
- Seed today Vetro-Luna distractor:
  `ses_8a4d6cd849414c998536212a61ef38f4`,
  memory `mem_57bc7bfe187645fea2eaa8567cd3296e`.
- Seed Zero-Luce wrong-entity distractor:
  `ses_ae4ae94732e34112817dc09934d4faf6`,
  memory `mem_8797edaa2dcb408db51a5de9bd0ee21e`.

Temporal old probe:

- First run: `turn_4f4feda5c9544d5492908c79485282db`.
- Scarlet used automatic memory context, opened the old source session, and
  correctly answered that Vetro-Luna historical format was a five-section long
  report.
- After sparse guard tightening: `turn_7f3436db778541bbb84c02bbb0fce481`.
- Scarlet first sent invalid `temporal_filter` metadata, received
  `memory.invalid_search`, then retried with valid `time` and opened the source
  session. This confirms endpoint-local recovery, but also shows route/body
  discipline still needs monitoring.

Today check probe:

- First run: `turn_0e3333bdbc644bb78e338eddea6977e2`.
- Scarlet tried invalid query-string temporal forms for `GET /mind/sessions`,
  then answered correctly from automatic memory context.
- After sparse guard tightening: `turn_6bdd32e2c5554cd4926a39ef1c4a914b`.
- Scarlet read both relevant memory ids and correctly distinguished today's
  mention from the older decision.

Negative wrong-entity probe:

- First run: `turn_2f8e8725174d486f8183a762627c2421`.
- The initial FTS/lexical blend over-selected memories from generic words such
  as `evidenza`, `senza`, and generic tag `protocollo`.
- First attempted fix used sparse query stop tokens, but this was rejected
  after owner review as too cablata and fragile for natural language.
- Revised fix: no stop-token filtering. Sparse search now uses entity-like
  spans and dynamically selected document terms; automatic context requires
  explicit entity support before an entity query can become selected evidence.
- After fix: `turn_caccab9ffff7402e91cdfd4a0491aff3`.
- `memory.context.selected=[]`; Vetro-Luna appeared only as `near_miss` because
  of the shared token `vetro`; Scarlet used explicit memory/session searches
  and answered that no Mare-Vetro evidence exists.
- After removing the stop-token approach, a direct local check confirmed
  manual `Mare Vetro` memory search returns zero results and automatic
  `Mare-Vetro` context keeps partial matches out of `selected`.

Assessment:

- Positive: temporal filtering works in the backend and Scarlet can recover
  from a bad temporal search shape using endpoint-local guidance.
- Positive: source-session opening happened naturally for the old Vetro-Luna
  decision.
- Positive: wrong-entity automatic context is improved after guard tightening;
  direct Mare-Vetro no longer selected Zero-Luce as evidence.
- Weakness: Scarlet still invents or guesses some body fields before recovering
  (`temporal_filter`, `scope=all`, `tags` on memory search, query-string JSON
  time). Endpoint guidance mitigates this, but it is not solved cognitively.
- Weakness: sparse retrieval is still lexical. Dense embeddings, entity-aware
  guards, and better UI diagnostics remain future work.

Restarted Runtime Re-run:

- Session: `ses_eac71e7b90814f49a7c21e079e64b85a`
- Turns:
  - `turn_2a53ace710dd419e8cd2c9fec230f90a`
  - `turn_33ec731f258a4c13aa1dbfa3c0c6e440`
  - `turn_f425ee89d8404c7e9ce6c60b8d4c22ac`
  - `turn_9ecedec4cce441eb9866b2d45f0d28f7`
- Backend was restarted before the run and `/mind/schema` returned
  `2026-05-24.temporal-sparse-v1`, confirming the previous owner-run session
  had been using a stale backend process.
- Streaming events were present: `memory.context.built`,
  `assistant.note.emitted`, `llm.thinking.captured`, Mind API tool lifecycle
  events, `turn.completed`, and `maintenance.job.scheduled`.
- Scarlet recovered the earliest substantial transcript at 8 May 2026 16:40
  when asked broadly, and distinguished earlier calibration sessions from
  meaningful communication.
- A follow-up prompt that excluded tests and identification messages caused
  Scarlet to shift to 22 May 2026 17:13 as the first Scarlet-identity
  conversation. This is not a pure retrieval failure, but it shows that the
  user's natural criterion ("prime cose vere e sostanziali") can be
  reinterpreted too aggressively unless Scarlet preserves competing criteria.
- Scarlet made one invalid episodic call with `order=asc`, then recovered by
  using supported `limit`/`offset` pagination.
- Stale-memory trust failed again: after reading current schema and old memory
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, Scarlet still repeated the old
  "nessun event store" gap by equating absence of `/mind/events/emit` with no
  event store. The events table and streamed runtime events prove the opposite.

Assessment:

- Accepted for confirming the restarted runtime path, current schema exposure,
  episodic pagination, live runtime-event observability, and idle-job
  supersession.
- Not accepted as solved for stale-memory trust, route/body discipline, or
  criterion preservation during ambiguous historical recall.

## EXP-0024 - Runtime Context Block Comprehension Probe

Date Started: 2026-05-25
Status: monitoring

Hypothesis:

If `runtime.context` is correctly delivered and understood, Scarlet should be
able to use `session_context`, `message_context`, and `scarlet_state` as
operational evidence before voluntary tool calls. She should also call API Mind
when a block is only a navigation hint rather than proof.

Test Session:

- Session: `ses_8d6f582db47a425988aeb01eb6b44d76`
- Title: `Runtime context comprehension probe 2026-05-25`

Code/Trace Evidence:

- For each tested turn, traces were ordered as:
  `memory.context` -> `runtime.context` -> `llm.request` -> response/tool
  traces.
- Each `llm.request` trace included:
  - `runtime_context_present=true`;
  - `runtime_context_trace_id`;
  - `<runtime_context>...</runtime_context>` inside the effective `system`
    prompt.
- Runtime event order confirmed:
  `message.user.persisted` -> `memory.context.built` ->
  `runtime.context.built` -> `llm.request.created`.

Turn A - Direct Runtime Perception:

- Turn: `turn_bfacd9824c0a4acbb673411d8f51d713`
- User asked Scarlet to report current runtime time, language, and cognitive
  blocks without API calls if runtime context was enough.
- Runtime context contained:
  - `now_local=2026-05-25T11:44:38.172527+02:00`;
  - `now_utc=2026-05-25T09:44:38.172527+00:00`;
  - `language_hint=it`;
  - blocks: `session_context`, `message_context`, `scarlet_state`.
- Scarlet made zero Mind API calls and answered with the correct local/UTC
  time, Italian language, and all three block identities.

Turn B - Session Continuity:

- Turn: `turn_a7bb3e0f074941cda292aeb66c106057`
- User asked what recent sessions indicated about the previous work, with a
  constraint not to invent.
- Initial `session_context` exposed two previous sessions:
  - `Chat 24/05, 20:04`;
  - `Chat 05/24, 07:58 PM`.
- Scarlet called `GET /mind/sessions/{session_id}` for both sessions before
  answering, which is the correct behavior because session summaries are
  navigation aids, not final evidence.
- Final answer correctly separated the post-update activation session from the
  minimal UI smoke session.

Turn C - User Profile / Personal Memory:

- Turn: `turn_2d1fcfc2d5b444c8a2455d0938c83d44`
- User asked naturally for a sweet snack consideration.
- `message_context.user_profile.memories` included the chocolate-limit memory:
  "Adora il cioccolato ma non puo mangiarne troppo..."
- Scarlet made zero Mind API calls and answered from that profile memory,
  warning that chocolate must respect the user's personal limit.

Assessment:

- Positive: Scarlet receives the blocks before the model call and can use them
  without tool calls when the block itself is sufficient evidence.
- Positive: Scarlet treats session summaries as pointers and opens the source
  sessions when the user asks for prior-session content.
- Positive: `user_profile` works as a personalization substrate even when the
  automatic memory retrieval selected a different memory.
- Weakness: the simple language heuristic returned `language_hint=unknown` for
  the Italian snack prompt because the marker list did not cover that wording.
- Weakness: automatic memory retrieval in Turn C selected the creator-memory
  rather than the chocolate memory; the final answer was saved by
  `user_profile`, not by `memory_retrieval.selected`.

Current Decision:

The block delivery and basic comprehension path is accepted. Retrieval quality
inside `memory_retrieval.selected` and language detection remain monitoring
items; no immediate hardcoded-language or keyword patch should be applied.

## EXP-0025 - Runtime Preferences And Dashboard Smoke

Date Started: 2026-05-25
Status: accepted for implementation smoke

Hypothesis:

If runtime time/language are backend settings rather than model-side
heuristics, the runtime context can be simpler and the dashboard can expose
those settings as product controls without adding model-facing API Mind routes.

Scenario:

- Add `/api/dashboard/settings`, `/api/dashboard/memories`, and
  `/api/dashboard/profile`.
- Default settings to Italian and `Europe/Rome`.
- Compose `temporal_context.now` as the only operative clock.
- Replace `language_hint` with `message_context.current_message.language`.
- Rework the frontend into a Tailwind dashboard with session history, chat,
  agent stream, memories, profile, and settings.

Verification:

- Backend full suite passed: `55 passed`.
- Frontend production build passed.
- Live endpoint checks returned dashboard settings, memory cards, and profile
  data from the local database.
- Playwright screenshot captured the new dashboard at
  `/tmp/scarlet-dashboard-rework.png`.
- Viewport-bounded Playwright screenshot captured the revised shell at
  `/tmp/scarlet-dashboard-viewport-bounds.png`.
- Direct Scarlet smoke turn
  `turn_d49955952c5343d58d29da2ddf93f1b4` answered:
  "12:57, Europa/Roma (CEST, +0200), italiano."
- The turn had zero Mind API tool calls; runtime context contained
  `temporal_context.now` and configured platform language from dashboard
  settings.

Assessment:

Accepted as the new runtime/UI baseline. This deliberately removes the
language-detection weakness from the current path instead of patching it with
keywords. Further evaluation should focus on live usability and whether
settings changes alter Scarlet behavior in natural conversation.

## EXP-0026 - Operational Profile Runtime Context Smoke

Date Started: 2026-05-25
Status: accepted for implementation smoke

Hypothesis:

If profile, locale, privacy, language, and timezone settings are operational
runtime inputs rather than cosmetic dashboard fields, Scarlet should receive
them inside `message_context` and answer from them without a Mind API call when
the context itself is sufficient.

Scenario:

- Extend dashboard settings with:
  - active `profile_id`;
  - `privacy_scope`;
  - configured `country_code` / `country_label`;
  - existing platform language, timezone, and display name.
- Inject those settings into:
  - `message_context.world.location`;
  - `message_context.user_profile.identity`;
  - `message_context.user_profile.privacy`;
  - `message_context.user_profile.locale`.
- Ask Scarlet directly which operational profile, country/locale, timezone,
  and platform language she receives.

Verification:

- Backend full suite passed: `55 passed`.
- Frontend production build passed.
- `git diff --check` passed.
- Live dashboard endpoint check returned new settings/profile fields.
- Direct Scarlet smoke session:
  - session: `ses_f52adfbc3a874f53bedb49dae2331590`;
  - turn: `turn_b393262f061f4fe8b50231e3f5683d35`.
- Scarlet answered from runtime context with:
  - `profile_id=local-user`;
  - display name `Test nome` from persisted dashboard settings;
  - country `Italia`;
  - timezone `Europe/Rome`;
  - offset `+0200`;
  - platform language `it` / `Italiano`;
  - source `dashboard_settings`.
- Trace order was `memory.context`, `runtime.context`, `llm.request`,
  `llm.response`.
- Mind API tool calls: `0`.

Assessment:

Accepted. The setting layer is now connected to Scarlet's cognition: the data
is visible to the model as operational context, not only as UI metadata. The
current persisted display name is still the test value `Test nome`; that is not
a runtime bug, but the dashboard should be used to set the real profile name
when the owner wants the local profile to reflect production-like identity.

## EXP-0027 - Memory Proposal Inbox For Missed-Memory Review

Date Started: 2026-05-25
Status: implemented for backend verification

Hypothesis:

Missed-memory review should not write active memories directly. A safer first
step is a proposal inbox that captures sourceable candidates, duplicate/similar
memory preflight, and lifecycle suggestions, so later apply policies can be
evaluated without polluting semantic memory.

Variant:

Idle maintenance still runs after the per-session idle timer. When the LLM
review returns `write_recommended=true`, the backend now creates an idempotent
`memory_proposals` row instead of writing a `memories` row.

Each proposal records:

- source session, turn, trace, and maintenance job;
- candidate content and evidence;
- proposed action such as `create_new`, `noop_duplicate`, `review_similar`,
  `needs_review`, or `reject_candidate`;
- similar memories from current FTS5/BM25 + lexical retrieval;
- candidate and related canonical facts where the extractor can identify them;
- future-ready decision metadata for embedding ids and graph node ids.

Verification:

- Targeted tests passed:
  `backend/.venv/bin/python -m pytest backend/tests/test_storage.py backend/tests/test_maintenance.py backend/tests/test_mind_api.py`
  (`33 passed`) for the initial V1.1.0 inbox.
- Full backend suite passed from `backend`: `.venv/bin/python -m pytest`
  (`58 passed`).
- Storage test confirms proposal idempotency.
- Maintenance test confirms idle review creates a pending proposal with
  `create_new`.
- Duplicate test confirms an exact existing memory becomes
  `noop_duplicate`, not a second active memory.
- V1.1.1 correction keeps proposal inspection out of `mind_api`. Targeted
  tests confirm `/mind/memory/proposals` is not model-facing, while
  `GET /api/maintenance/memory/proposals` returns paged pending proposals and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive` removes
  handled proposals from the default pending queue.
- V1.1.1 full backend suite passed with `60 passed`; frontend build passed.

Assessment:

Accepted as the next safe P1 memory-maintenance slice. It turns diagnostic
review into inspectable maintenance state while preserving the core rule that
only explicit memory lifecycle operations mutate active semantic memory.
Proposal inspection is intentionally internal to maintenance processes, not an
autonomous Scarlet `mind_api` capability.

## EXP-0028 - Cautious Proposal Resolution Inside Idle Maintenance

Date Started: 2026-05-26
Status: implemented for backend verification

Hypothesis:

The existing session-idle maintenance job can resolve safe memory proposals
without adding a redundant background process. Deterministic preflight should
close obvious rejects/duplicates with zero extra LLM calls, while ambiguous
items should be sent to one batched LLM resolver only when needed.

Variant:

Idle maintenance now runs this single pipeline:

```txt
summary -> missed-memory review -> proposal creation -> preflight -> cautious resolution
```

Resolved proposals remain in `memory_proposals` as the daily audit ledger for
future Dream review:

- `archived_rejected`
- `archived_noop_duplicate`
- `applied_create`
- `pending_review`
- `archived_manual`

Very high-confidence `create_new` proposals can create active memories with
`created_by=maintenance`; their proposal result stores the created memory id
and snapshot. Ambiguous cases are handled by one optional LLM resolver batch.
Dream, merge, update, and deprecation are intentionally not implemented.

Verification:

- Targeted maintenance tests verify:
  - normal ambiguous proposal becomes `pending_review` through the batch
    resolver;
  - very high-confidence `create_new` is applied without an extra resolver
    call;
  - exact duplicate proposal becomes `archived_noop_duplicate` without an extra
    resolver call;
  - LLM resolver can apply an eligible `create_new` proposal and emits
    `maintenance.memory_proposal_resolution`.
- Targeted API tests verify `status=resolved` plus resolved time filters over
  the proposal ledger.
- Full backend suite passed with `63 passed`; frontend production build and
  `git diff --check` passed.
- Direct real MiniMax maintenance probe on a temporary SQLite DB passed:
  - job status: `completed`;
  - proposal status: `applied_create`;
  - proposal action: `create_new`;
  - memory count: `1`;
  - trace kinds included `maintenance.memory_proposal_resolution`,
    `maintenance.memory_review`, and `mind.sessions.summarize`.

Assessment:

Accepted as the next memory-maintenance implementation slice. The important
design result is that proposal resolution remains part of the same idle job,
not a separate always-on LLM process. Future Dream should read resolved and
pending-review proposal rows, not recompute the whole session history.

## EXP-0029 - Memory Retrieval Readiness Layer

Date Started: 2026-05-28
Status: implemented for backend verification

Hypothesis:

Advanced memory retrieval should be prepared as derived infrastructure before
activating dense vector search or knowledge graph reasoning. If the canonical
memory tables can generate embeddable surfaces and graph-ready nodes/edges,
future Milvus/Qdrant/KG adapters can be tested in shadow mode without
rewriting Scarlet's `mind_api` surface or changing already-working lifecycle
logic.

Variant:

V1.3.0 adds derived, rebuildable artifacts:

- `memory_surfaces` for memory text, fact text, graph-node profiles, and
  session summaries;
- `memory_graph_nodes` for memory, fact, entity, and session nodes;
- `memory_graph_edges` for `has_fact`, `about_entity`,
  `evidenced_by_session`, `supersedes`, `superseded_by`, and fact lifecycle
  links;
- a retrieval-readiness manifest in memory search/context traces.

The active memory search route still uses FTS5/BM25 plus lexical fallback. No
Milvus, Qdrant, embedding model, reranker, or graph-reasoning ranker is active
yet.

Verification:

- Storage test verifies `memory_surfaces`, `memory_graph_nodes`, and
  `memory_graph_edges` are created and that memory/fact/session/entity
  artifacts are produced from a sourceable memory.
- Mind API test verifies `POST /mind/memory/write` creates retrieval surfaces
  and graph nodes while `POST /mind/memory/search` returns the readiness
  manifest without changing the search route.
- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`49 passed`).
- Full backend suite passed: `.venv/bin/python -m pytest -q` (`64 passed`).
- Frontend production build passed: `npm --prefix frontend run build`.
- `git diff --check` passed.

Assessment:

Accepted as the V1.3.0 substrate. It deliberately avoids solving BUG-0037 or
changing ranking by hardcoded terms. The next experimental step is a shadow
retrieval adapter over `memory_surfaces`, likely Milvus Lite first, with trace
comparison against the current FTS5/BM25 path.

## EXP-0030 - Retrieval Shadow Adapter

Date: 2026-05-28
Status: accepted as V1.3.1 plumbing

Hypothesis:

Before changing active memory ranking, Scarlet needs a trace-only comparison
path that can run vector-style retrieval over `memory_surfaces`. If this path
can be observed during both manual memory search and automatic runtime context,
future real embeddings can be evaluated without destabilizing the current
memory behavior.

Variant:

V1.3.1 adds optional retrieval shadow mode:

- `retrieval_shadow_enabled=false` by default;
- `local` backend uses deterministic `local_hash_embedding_v1` to validate
  indexing/search plumbing only;
- `milvus_lite` backend uses PyMilvus/Milvus Lite when the optional retrieval
  dependency is installed;
- `retrieval_shadow` payloads are written into `mind.memory.search` and
  `memory.context` traces;
- active ranking remains FTS5/BM25 plus lexical/fact scoring.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_chat_api.py tests/test_maintenance.py -q`
  (`50 passed`).
- Full backend suite passed: `.venv/bin/python -m pytest -q` (`65 passed`).
- Frontend production build passed: `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct Scarlet test on a temporary SQLite database passed:
  Scarlet answered a natural beverage/focus question from the seeded semantic
  memory, `memory.context.selected` contained the expected memory, and
  `query_plan.retrieval_shadow` reported
  `status=completed`, `backend=local`, `ok=true`, and the same memory target
  under `trace_only_no_active_ranking`.

Assessment:

Accepted as a safe retrieval experiment substrate. This validates the runtime
and trace path but does not prove semantic retrieval quality because
`local_hash_embedding_v1` is not a real embedding model. V1.4 active hybrid
ranking should not be promoted until a real embedding provider is selected and
tested against live Scarlet behavior.

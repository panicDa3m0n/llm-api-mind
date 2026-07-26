# Experiments

This file tracks hypotheses, baselines, variants, scenarios, metrics, and results.

The project should not accept a cognitive module only because it feels intelligent. Each meaningful module should have a measurable experiment.

Identifier note: V1.29.1 removed legacy duplicate headings. Historical activity
entries may still mention the original reused identifiers; current canonical
ids are the headings in this file. Experiment results and dates were not
rewritten.

## EXP-0082 - Physical Android Device Exploration

Status: implementation complete; physical run pending

Hypothesis:

An isolated Capacitor layer can collect useful real device evidence, preserve
offline/lifecycle observations, and expose enough raw detail to design future
perception and peripheral capabilities without changing Scarlet's cognition.

Method:

- install V1.58.0 on the connected physical Samsung device;
- capture automatic device, app, battery, network, permission, notification,
  lifecycle, and sampled motion observations;
- run explicit location, notification, haptic, background/resume, and
  connectivity probes;
- verify local-outbox recovery, server idempotency, timestamps, and per-run
  history;
- inspect raw and normalized payloads qualitatively, not only by counts; and
- confirm that no session, memory, trace, context, or shell state is created.

Acceptance:

The Product UI updates without remounting, observations persist on the VPS,
the same client event cannot duplicate, lifecycle events survive interruption,
and the resulting evidence clearly separates useful candidate signals from
technical-only fields.

Results:

Pending physical-device execution.

## EXP-0081 - MiniMax M3 Native Stop-State Continuation

Status: accepted as focused V1.55.0 provider evidence

Hypothesis:

MiniMax M3 can continue a response truncated by `max_tokens` when its complete
native assistant blocks are appended unchanged and the next message asks it to
resume, while `end_turn` remains the sole terminal boundary.

Method:

- probe M3 at small output budgets and inspect raw thinking/text blocks,
  signatures, and stop reasons;
- append the complete `max_tokens` assistant response and a technical user
  continuation;
- verify that the next text continues rather than restarts;
- encode controlled provider sequences for text continuation, signed thinking,
  tool mismatch, correct tool dispatch, transient retry, non-transient
  rejection, and exhaustion; and
- run one normal direct M3 smoke after implementation.

Result:

The controlled continuation preserved signed thinking and exact native block
order, resumed the public sequence without repetition, accumulated usage, and
closed only on `end_turn`. The normal live smoke returned `MiniMax-M3`,
`end_turn`, and exactly `verifica M3 completata`. A deliberately unrealistic
64-token live budget repeatedly exhausted itself in thinking and was stopped
manually; this falsified the assumption that continuation can be unbounded and
justified the separate eight-segment pathological guard.

Interpretation:

The provider protocol is a reliable structural boundary. Semantic judging
remains useful for evidence-bearing claims but is not a substitute for stop
reasons. Tool-loop freedom and output-continuation safety are separate concerns.

## EXP-0080 - Canonical-Neutral APNG Greeting

Status: V1 movement rejected; V2 local-rig method under visual review

Hypothesis:

A prepared APNG gesture can preserve Scarlet's approved identity when every
frame starts from the canonical neutral and generated content replaces only a
reviewed motion corridor.

Method:

- use the approved `941x1672` transparent portrait as immutable neutral;
- generate one open-palm master pose and three transition/oscillation poses;
- reject full-frame outputs and composite only the old/new arm silhouettes;
- assemble an 11-frame one-shot greeting with variable timing;
- inspect sequence and change-map proofs; and
- decode the output and verify hashes, timing, loop count, identity locks,
  browser requests, MIME type, and console state.

Result:

The technical contract passes. The 1,300 ms, 6.6 MB APNG has 11 decoded frames,
loop count 1, exact canonical-neutral first and last hashes, transparent output,
and exact face-core, hair-crown, and viewer-right locks. Chromium loads it as
`image/png` with no warnings or errors. A first artistic variant was rejected
because cuff details changed; using the open-palm pose as a canonical gesture
reference made the replacement poses substantially more coherent.

Owner review rejected the V1 movement: the four source poses are individually
usable, but five distinct images with 75-110 ms pose holds behave as discrete
switches. APNG does not synthesize motion between frames.

The V2 variant treats APNG only as delivery. It renders
`neutral -> lift_low -> neutral` through a local raster mesh with smootherstep
easing, 18 steps in each direction, and 33/34 ms moving-frame durations. The
37-frame, 1,749 ms output preserves exact neutral endpoints and all declared
identity locks. Full-resolution review found and then removed a duplicated pale
arm edge caused by an insufficient exclusion margin between static cleanup and
the moving matte.

V2 remains under owner visual review. It evaluates only entry and exit, not the
remaining pose-to-pose greeting. Semantic matte quality, natural trajectory,
Android decode/performance, and the 13.7 MB unoptimized size remain open gates.

Evidence:

- `docs/scarlet-apng-animation.md`
- `frontend/public/prototype/avatar/animations/greeting-v1/`
- `frontend/scripts/build-scarlet-greeting-apng.py`
- `frontend/public/prototype/avatar/animations/greeting-v2-motion-test/`
- `frontend/scripts/build-scarlet-greeting-motion-v2.py`

## EXP-0079 - Native Markerless Finality Recovery

Status: accepted and deployed in V1.50.1

Hypothesis:

After the one bounded correction, an LLM judge can distinguish a complete
markerless final answer from a progress note without keyword/string scoring,
automatic rewriting, or weakening the provider's empty-response boundary.

Starting Evidence:

- production turn `turn_a35981d139214ceeb0d135f2732ec8b9` delivered the exact
  Zero-Luce memory and completed `memory graph`, but two markerless drafts led
  to HTTP 502;
- a second simple natural turn in session
  `ses_513c1cb2482440a49bdbadfebe51a6f6` reproduced the same structural miss;
- DB integrity, V2 projection, shell result, provider text, and runtime traces
  separated the defect from retrieval, deployment, and provider emptiness.

Method:

- keep the existing first marker rejection and correction;
- on the second miss only, validate one synthetic hard finality obligation
  together with any current semantic obligations;
- use controlled positive and negative providers to prove both polarities;
- inspect persisted answer, trace manifest, judge finding, turn status, and
  absence of marker leakage.

Result:

Focused answer-control and chat contracts pass 46/46; the patch surface plus
model-facing gate oracles passes 52/52. The positive corrected draft is
persisted unchanged after explicit semantic acceptance; the negative second
progress note and empty corrected draft remain rejected with no assistant
message. A real native repeat is required after protected deployment before
release acceptance; that repeat is recorded below.

The protected production repeat completed as HTTP 200 in turn
`turn_a8a990e5ce7a4fbd9dd15cd99437836d`, persisted the public answer, and used
the unchanged primary marker path. This does not manufacture a stochastic
second marker miss merely to exercise the fallback in production; the
controlled polarity tests remain authoritative for that branch. Together the
real ordinary path and deterministic fallback controls satisfy release
acceptance.

## EXP-0078 - Model-Facing Automatic-Memory Delivery Gate

Status: deterministic integrated evidence accepted for V1.50.0

Hypothesis:

A valid automatic-memory gate can distinguish internal retrieval from actual
model delivery and reject failed turns without changing retrieval semantics or
the immutable historical fixture.

Method:

- run one natural Zero-Luce prompt before repair on the frozen disposable copy;
- inspect rich selection, V2, `llm.request`, observed provider input, persisted
  messages, traces, events, and final turn status;
- apply existing exact provenance maintenance with the reviewed digest and an
  immutable-baseline reference;
- repeat the same prompt after repair; and
- run a negative provider that omits the final boundary on both allowed
  attempts.

Result:

Before repair, rich retrieval selected the target while V2 and the provider
packet correctly omitted it. After repair, the target and exact source hooks
crossed every model-facing boundary and the turn completed with one assistant
message. The negative control retained valid retrieval/context traces but
failed with `llm.incomplete_response`; the new gate rejected it. All five
integrated cases and all six evaluator-oracle tests pass.

Evidence:

- `20260718_220521_model-facing-memory-gate-v2`;
- `20260718_220559_preliminary-regression-v1`, unchanged V1, 9/9;
- `docs/evaluations/v1.50-model-facing-memory-gate.md`.

## EXP-0077 - Recoverable Action Retry Evidence And Natural Recovery

Status: deterministic and direct behavioral evidence accepted for V1.49.1

Hypothesis:

A corrected action can be represented as one inspectable attempt chain without
deterministically declaring semantic equivalence, allowing truthful final
answers while retaining real failures.

Method:

- reproduce the old failure on current code before the fix;
- cover equivalent, unrelated, different-operation, non-recoverable,
  out-of-order, capability, stale-manifest, native sync/stream, and GPT Actions
  cases;
- run the unchanged frozen preliminary gate before and after; and
- give MiniMax M3 a natural durable preference while the harness corrupts only
  its first memory-write command at the runtime boundary, then inspect the
  complete model/tool/validator/persistence outcome.

Result:

Before the fix, the successful retry remained absent from the hard obligation.
After the fix, all transports preserve the failure and expose the later call as
a semantic candidate. In the real probe, Scarlet corrected the malformed
command with the same intent, stored a faithful preference with complete
provenance, and answered naturally. The semantic validator's pass agrees with
the inspected evidence; it is not the basis of the qualitative judgment. The
GPT lifecycle test additionally found and fixed stale dynamic-obligation
deduplication.

Evidence:

- pre gate `20260718_195924_preliminary-regression-v1`;
- post gate `20260718_201150_preliminary-regression-v1`;
- `docs/evaluations/v1.49.1-action-retry-obligations.md`.

## EXP-0076 - Maintenance Domain Equivalence And Semantic Probe

Status: bounded pre/post and direct behavioral evidence accepted for V1.49.0

Hypothesis:

Maintenance scheduling, summary/history execution, and memory review can move
to separate owners without changing job lifecycle, retry/idempotency behavior,
prompts, proposal policy, history sources, or Scarlet's maintenance judgments.

Method:

- compare the frozen nine-case gate and focused maintenance/history tests
  before and after extraction;
- compare moved definitions, prompt text, thresholds, facade identities, and
  the normalized OpenAPI document;
- execute history compaction directly on a disposable database and inspect the
  job, artifact, canonical history, provider calls, and events; and
- run a natural MiniMax M3 conversation followed by the real idle worker, then
  inspect Scarlet's answer, generated summary, memory-review rationale,
  proposals, memories, and event trail.

Result:

Pre/post gates passed 9/9 with identical stable evidence and focused contracts
passed 32/32. Direct compaction produced one idempotent completed job and one
source-anchored artifact without mutating canonical history. MiniMax answered a
natural pause proportionately; maintenance summarized the exchange accurately
and correctly created no memory for the transient remark. Direct semantic
judgment therefore agrees with the persisted technical evidence. Harness-only
inspection mistakes were classified separately and do not indicate runtime or
model defects.

Evidence:

- pre gate `20260718_193905_preliminary-regression-v1`;
- post gate `20260718_194544_preliminary-regression-v1`;
- `docs/evaluations/v1.49-maintenance-domains.md`.

## EXP-0075 - Memory Mutation Surface Equivalence Probe

Status: bounded pre/post and direct behavioral evidence accepted for V1.48.0

Hypothesis:

Write, lifecycle, proposal, and relation evidence can move to dedicated owners
without changing shell/API contracts, persisted state, trace kinds, proposal
decisions, conflict semantics, or Scarlet's natural memory behavior.

Method:

- run the frozen nine-case gate before and after extraction and compare stable
  source, retrieval, navigation, and lifecycle fields;
- run focused mutation, shell, maintenance, storage, and facade contracts;
- exercise write, exact duplicate, fact conflict, supersede, and proposals on
  disposable databases while inspecting records, facts, activities, traces,
  and provenance; and
- give MiniMax M3 a natural durable preference without asking for a tool, then
  inspect its actions, stored memory, provenance, and final answer.

Result:

Both frozen gates passed 9/9 with identical stable evidence. Direct shell use
created exactly two intended memories, rejected an exact repeat as a duplicate,
reported only the real atomic-fact conflict, and removed it after explicit
supersession. Proposal application preserved provenance and a later equivalent
candidate became `noop_duplicate`. Scarlet autonomously wrote one faithful
user preference with complete provenance and acknowledged it only after the
successful tool result. Human/LLM judgment found the action sequence useful
and proportionate rather than accepting aggregate scores alone.

Evidence:

- pre gate `20260718_192112_preliminary-regression-v1`;
- post gate `20260718_193026_preliminary-regression-v1`;
- `docs/evaluations/v1.48-memory-mutation-surface.md`.

## EXP-0074 - Memory Read Surface Equivalence Probe

Status: bounded pre/post evidence accepted for the V1.47.0 candidate

Hypothesis:

Manual memory search, open, facts, and graph can move behind a dedicated owner
without changing shell commands, dispatcher routes, ranking, payloads, traces,
provenance, or cognitive usefulness.

Method:

- run the unchanged frozen 9-case gate before and after extraction;
- compare stable fields from manual shell navigation and automatic retrieval;
- run focused shell/memory/V2 contracts; and
- invoke all four commands directly on a disposable frozen copy, inspecting
  content, ids, provenance, facts, graph topology, and stored trace kinds.

Result:

Both gates passed 9/9 with identical stable evidence. Direct search selected
only the active Zero-Luce record; open returned its active lifecycle and source
links; facts returned the active canonical `response_format`; graph returned a
four-node/three-edge neighborhood rooted at the same memory. The exact four
read trace kinds were stored. The outputs remained coherent under direct
review, independent of pass counters.

Evidence:

- pre gate `20260718_190504_preliminary-regression-v1`;
- post gate `20260718_191139_preliminary-regression-v1`;
- `docs/evaluations/v1.47-memory-read-surface.md`.

## EXP-0073 - Automatic Context Retrieval Separation Probe

Status: bounded pre/post evidence accepted for the V1.46.0 candidate

Hypothesis:

Automatic memory retrieval can move behind a typed owner without changing
candidate selection, classification, runtime packet assembly, shell
navigation, or natural model behavior under valid source provenance.

Method:

- run the unchanged frozen 9-case gate before and after extraction;
- run focused and complete deterministic suites;
- inspect the automatic case's real memory id, candidate count, and block
  types rather than accepting only its aggregate result;
- send a natural Zero-Luce request to MiniMax on a disposable frozen copy; and
- trace rich selection, V2 projection, provider request, model actions, and
  final text directly.

Result:

Both gates passed 9/9 and selected the same active memory from 33 candidates.
The first live probe exposed BUG-0093: the frozen memory was selected but
excluded from V2 because its source message was absent. After exact provenance
repair on the disposable copy, the repeated request required no manual tool
and Scarlet correctly described all four ordered protocol blocks. The answer
was semantically complete and grounded; it was not accepted from a score.

Evidence:

- pre gate `20260718_184350_preliminary-regression-v1`;
- post gate `20260718_184927_preliminary-regression-v1`;
- `docs/evaluations/v1.46-context-retrieval-separation.md`.

## EXP-0072 - Native Turn Orchestration Equivalence Probe

Status: bounded pre/post evidence accepted for the V1.45.0 candidate

Hypothesis:

Sync/stream native turn invariants can move behind one typed service without
changing API, continuity, tool/answer ordering, persistence, or natural answer
quality, while eliminating an observed trace-parity defect.

Method:

- run the unchanged frozen 9-case gate before and after;
- compare normalized OpenAPI documents exactly;
- run focused and complete deterministic suites;
- send the same two natural prompts to pre/post disposable MiniMax runtimes;
- inspect provider messages, model actions, stream events, traces, and final
  text directly rather than accepting completion scores.

Result:

Both gates passed 9/9 and OpenAPI remained equal. The post sync turn chose
`quieta`; the next stream received prior user, complete prior assistant
content, and current user, then reused `quieta` correctly in one sentence.
Stream model-context evidence is now linked consistently, fixing BUG-0092.

The post recovery made an unnecessary `help` call after first omitting the
private final marker. Pre-change runs under the same prompt ranged from two
thinking-only failures to a clean successful correction without that call.
Because recovery code and inputs were preserved and the outcomes vary by
provider sample, the extra call is model variance, not an SCA-33 regression.

Evidence:

- pre gate `20260718_181621_preliminary-regression-v1`;
- post gate `20260718_183109_preliminary-regression-v1`;
- `docs/evaluations/v1.45-native-turn-orchestration.md`.

## EXP-0071 - Native Chat Support Extraction Continuity Probe

Status: bounded pre/post evidence accepted for the V1.44.0 candidate

Hypothesis:

Provider-history transformations, response/event projections, and context
accounting can move out of `chat.py` without changing native continuity,
public payloads, trace contracts, or GPT reuse.

Method:

- run the frozen 9-case gate before and after extraction;
- compare pre/post OpenAPI JSON exactly;
- exercise pure support contracts and the focused chat/bridge suites;
- run two natural turns in one disposable native MiniMax session with the
  production token budget; and
- inspect the actual provider request, model actions, traces, and answers
  qualitatively rather than relying on completion status alone.

Result:

The frozen gate remained 9/9 and OpenAPI JSON was byte-equivalent after JSON
normalization. In session `ses_2a4fcb91e6f44ed6a0be6273b4fa027b`, Scarlet
answered the first one-sentence greeting naturally. The second turn received
three canonical provider messages, including the complete prior assistant
content, and correctly identified and quoted `Che bello risentirti`. No tool
call was needed. The answer-obligation layer requested one correction but the
turn completed with semantically correct continuity.

The qualitative result supports SCA-34: provider history survived the module
move and was used in the next answer. The phrase about having met `dopo un po'
di tempo` was a reasonable interpretation rather than stored evidence and is
minor style variance, not a continuity regression.

An earlier probe exposed BUG-0091 after a failed memory write was successfully
retried. That defect was isolated in SCA-42 and not changed inside SCA-34. A
separate attempt using a 1,024-output-token override was rejected as invalid
evidence because it did not match native Scarlet's configured budget.

Evidence:

- pre gate `20260718_174427_preliminary-regression-v1`;
- post gate `20260718_175231_preliminary-regression-v1`;
- `docs/evaluations/v1.44-chat-support-extraction.md`.

## EXP-0069 - Shared Answer-Obligation Enforcement

Status: focused implementation and direct probes accepted for V1.41.0

Hypothesis:

A structural final boundary plus proportionate semantic obligations can stop
progress-only completion and evidence/capability contradictions without using
deterministic language matching or forcing every turn through a second model.

Method:

- freeze BUG-0085 and BUG-0011 as the starting evidence;
- exercise native success, one recovery, second failure, streaming isolation,
  source-sensitive claims, active conflicts, capability inspection, failed
  actions, and non-blocking warning/advisory findings;
- use one structured MiniMax judgment only for manifests containing semantic
  obligations;
- probe native MiniMax on an isolated DB; and
- probe GPT bootstrap, `help`, and finalize against the same local runtime with
  the real MiniMax validator.

Result:

Focused deterministic coverage passes both transports and proves that rejected
drafts are not persisted. The native real-model probe accepted and stripped
the private boundary. The first GPT capability probe exposed an over-broad
validator requirement for an exhaustive catalog; the obligation was corrected
to judge only claims actually made. The repeated real probe then accepted a
non-exhaustive but accurate capability answer. Streaming now withholds draft
text until validation while preserving public notes and tool events.

Decision:

Accept the shared contract and active default for release verification. Keep
semantic validation limited to evidence-bearing turns, retain one correction,
and monitor validator false positives and latency. Do not infer memory
conflicts from semantic similarity inside this feature.

Evidence:

`docs/evaluations/v1.41-answer-obligations.md`

## EXP-0068 - Longitudinal Cognitive Organ Separation

Status: completed for V1.40.0; conservative defaults retained

Hypothesis:

Focus, volition, affect, and metacognition can each show correct state,
proportionate selection, useful answer influence, and longitudinal continuity
without relying on another organ or polluting unrelated state.

Method:

- define 13 natural scenarios in nine groups with two independent repetitions;
- run correlated same-session focus and affect transitions plus separate-
  session volition continuity;
- include focus, volition, affect, and metacognition negative controls;
- compare affect `model` and `shadow` under explicit effective-configuration
  receipts;
- use deterministic comparison only for commands, traces, state, provenance,
  and forbidden mutation; and
- use project-informed LLM-as-human review for cognitive choice, answer
  quality, and longitudinal value.

Result:

The accepted 26-turn evidence set passed 24/26 deterministic turn contracts.
Focus passed 6/6. Affect passed all ten post-fix model/shadow/neutral contracts
after explicit obstruction resolution was separated from obstruction itself.
Metacognition passed two positive and two negative controls after the prompt
made broad reliability review mandatory. Volition completed one of two
positive cross-session chains and both negative controls; the failed chain
ended after a public progress note before the chosen write, then correctly
reported the missing intention in its next session.

Decision:

Accept the standalone lifecycle evidence and the affect correction. Retain
conservative independent defaults and no organ coupling. Treat the residual
volition miss as SCA-28 answer-obligation evidence, not a storage or recall
failure. Keep affect shadow and metacognitive lesson injection shadow until
controlled tests demonstrate user-value improvement rather than mere technical
activity.

Evidence:

`docs/evaluations/v1.40-cognitive-organ-longitudinal.md`

## EXP-0067 - Recursive Active History Compaction

Status: accepted for guarded native activation in V1.39.0

Hypothesis:

A recursive source-labelled summary plus an exact token-selected tail can
preserve Scarlet's useful continuity while reducing active input, without
mutating canonical provider history or trusting the model to reproduce source
IDs.

Method:

- implement append-only artifacts, maintenance generation, and shared
  sync/stream routing;
- verify valid, stale, missing, recursive, idempotent, and whole-turn paths;
- run the full backend suite;
- copy the laboratory DB to an ignored disposable target;
- generate two real MiniMax M3 compaction cycles on the measured 350k-token
  session; and
- ask Scarlet a natural recall question whose answer came from the compacted
  prefix.

Result:

Generation 1 exposed shortened/hallucinated source IDs in otherwise useful
summary prose. Deterministic source manifests and unverified-ID removal fixed
that boundary. Generation 2 recursively covered five turns, reduced the exact
active tail to about 2.7k tokens, and left zero unresolved unverified IDs.
Scarlet accurately recalled the earlier endpoint-to-CLI framing from 21
canonical messages using only 3 model-facing messages. Canonical prefix
preservation passed. The complete backend suite passed 216 tests at 80.69%
coverage.

Decision:

Activate for native MiniMax behind `HISTORY_COMPACTION_MODE=active`, retain
canonical fallback, and monitor natural long-session drift. Keep GPT-native
history explicitly outside the backend's observable compaction boundary.

Evidence:

`docs/evaluations/v1.39-active-history-compaction.md`

## EXP-0066 - Historical Provenance And Fixture Isolation

Status: accepted and deployed in V1.38.0

Hypothesis:

Structured provenance and fixture markers can separate defensible maintenance
from semantic guesswork, allowing explicit test contamination to be deprecated
without mutating uncertain historical memories or distorting recent-memory
state.

Method:

- inspect the production inventory read-only before defining classes;
- inspect exact source sessions, turns, messages, metadata, tags, lifecycle,
  and duplicate groups;
- encode the resulting criteria without semantic similarity;
- require a reviewed candidate digest and backup reference for apply;
- exercise audit, dry-run, drift rejection, apply, lifecycle propagation, and
  recency isolation on disposable databases;
- repeat against an online production copy before production apply; and
- verify normal retrieval and a natural Scarlet turn after deployment.

Initial Result:

The production legacy read-only baseline contained 307 memories: 61 complete,
242 session-only records, and four invalid stored message links. The stricter
V2 contract reclassified three assistant-message hooks from complete to
invalid, yielding 58 valid and seven review-only links. All 242 session-only
records satisfy three independent explicit Codex fixture markers; 241 are
active and one already inactive. Exact transcript inspection found no unique
deterministic repair for the seven invalid links.
Focused tests passed 13/13, the full suite passed 209 tests at 80.45% coverage,
and the ignored historical artifact produced the expected 34 repair and 241
active-fixture candidates without changing its hash.

Decision:

Accept the classification, guarded workflow, production cleanup, and direct
fixture-isolation controls. The protected live apply deprecated all 242
fixtures without changing seed-session timestamps or the seven review-only
links. Post-config GPT bridge retrieval completed embedding and rerank and
returned zero ginger-infusion memories. Do not auto-repair the seven invalid
links and do not broaden SCA-20 into duplicate/conflict or reranker
adjudication.

Evidence:

`docs/evaluations/v1.38-historical-provenance-audit.md`

## EXP-0070 - Personal-Negative Reranker Revalidation

Status: measured; runtime correction deferred by owner decision

Hypothesis:

The accepted V1.37 final-rerank floor may admit plausible but unsupported
personal memories near its boundary, and realistic personal negatives can show
whether a safe global correction exists.

Method:

- retain all eleven accepted positive, negative, graph, temporal, and entity
  controls against the immutable V1.37 database;
- add five natural unsupported personal questions before changing policy;
- run all sixteen cases twice with the real configured OpenRouter reranker;
- reject any correction that restores negatives by losing close positives or
  by replacing reranker authority with deterministic relevance scores.

Result:

The comparison passed 30/32. Only the favourite-colour negative failed, in the
same way in both repetitions. Its highest unrelated score was `0.006339`; the
required-positive floor was `0.007432`. Removing document metadata did not
solve the negative and lost a required Vetro-Luna fact. The narrow separation
does not justify a stable threshold-only change.

Decision:

Keep the expanded calibration harness and defer runtime changes. A retrieved
memory is evidence available to Scarlet, not an obligation to use it in the
answer. Reopen on broader provider drift evidence, answer-level harm, or a
better reranker policy. Full evidence is in
`docs/evaluations/v1.43-memory-rerank-negative-calibration.md`.

## EXP-0065 - Frozen And Live Final-Rerank Calibration

Status: accepted for V1.37.0; longitudinal provider drift remains monitored

Hypothesis:

A final memory reranker with a calibrated absolute anti-noise floor plus a
query-relative floor can retain several necessary facts without admitting
unrelated memories, while sparse, dense, KG, and lexical routes remain recall
only.

Method:

- freeze ten initial cases and exact expected ids against an immutable
  36-memory DB, then retain one inherited wrong-entity regression found by the
  unchanged full gate;
- repeat all cases twice with real OpenRouter embedding/rerank and controlled
  answer generation;
- verify candidate route, final id, sourceable V2 packet, negatives, and
  latency;
- inspect memory content before classifying apparent extras as errors;
- run three selected cases with real MiniMax M3 and judge evidence use.

Result:

The fixed `0.01` baseline passed 18/20 and repeatedly lost one required
Vetro-Luna fact despite complete candidate coverage. The calibrated
`max(0.004, best_score * 0.01)` policy passed 22/22; positive floor was
`0.007432`, negative ceiling `0.003299`, reranker median latency 396.5 ms, and no
provider error occurred. Three real Scarlet turns passed technical and semantic
review, including an unrelated negative with no delivered memory.

Evidence:

`docs/evaluations/v1.37-memory-rerank-calibration.md`

## EXP-0064 - Thinking-Only Final Recovery And Isolation

Status: completed for V1.36.1; natural recurrence remains monitored

Hypothesis:

A single bounded continuation can recover a stochastic MiniMax thinking-only
`end_turn` without treating private reasoning as an answer or cognitive action,
while repeated invalid output fails visibly and leaves canonical history clean.

Method:

- reproduce the pre-fix behavior with provider and API fixtures;
- test one thinking-only response followed by a public final response;
- test repeated thinking-only responses through the configured retry limit;
- inspect sync/stream turn state, assistant messages, runtime events, traces,
  and provider history;
- run one natural MiniMax M3 control against an isolated in-memory database at
  the configured `131072` token budget, without forcing the stochastic symptom.

Results:

- the initial fixtures confirmed a backend defect independent of model
  variability: empty provider results were accepted as successful turns;
- the recovered fixture produced one public answer and one explicit recovery
  event, while canonical provider history contained only the valid assistant
  message;
- exhaustion fixtures failed explicitly and persisted no assistant message;
- the natural control completed normally with user/assistant messages, zero
  recovery events, zero tool calls, and zero memory records;
- 30 focused provider/chat tests passed; the full backend suite passed 198
  tests at 80.22% coverage.

Decision:

Accept the bounded policy as the SCA-19 fix. Treat future isolated provider
occurrences as stochastic unless traces show the invariant or retry bound was
bypassed. Do not add broad generic retries or infer tool/memory operations from
private thinking.

Evidence:

- direct control `turn_83848970e2b3410cb68faae248189f17`
- `backend/tests/test_minimax_client.py`
- `backend/tests/test_chat_api.py`
- ADR-0088 and BUG-0067

## EXP-0063 - Natural Cross-Branch Behavioral Baseline

Status: completed for V1.34.0; repeated pre/post use is now the gate

Hypothesis:

A frozen, natural-language suite with independent repetitions and four-layer
review can distinguish shell/storage correctness, model tool choice, answer
quality, and longitudinal continuity without reducing Scarlet to string or
numeric scoring.

Method:

- use the immutable preliminary DB fingerprint and real memory/session
  references;
- define 8 independent groups and 12 human-like scenarios across memory,
  episodic provenance, focus, volition, affect, metacognition, and mode;
- run 3 repetitions per group with real MiniMax M3 and production-like rerank;
- persist responses, stream events, traces, commands, and before/after state;
- automate only objective invariants;
- review every qualitative layer as a project-informed LLM-as-human judge with
  an explicit rationale;
- correct and rerun any evaluator oracle shown to be over-prescriptive.

Results:

- 45 shakedown turns exposed two oracle errors and evaluator identity leakage
  through session titles; they are retained as evaluator evidence, not as the
  behavioral baseline;
- 36 authoritative live turns then completed with neutral session identity and
  no production/laboratory DB mutation;
- memory positive/negative controls were technically 6/6;
- episodic navigation produced two complete, grounded reconstructions; one
  run navigated extensively but persisted only a closing note plus a lesson;
- focus and volition storage worked when invoked, while autonomous use remained
  inconsistent;
- affect failed 6/6 technical turns because explicit frustration remained
  below activation threshold and produced no affective context;
- explicit metacognitive review occurred 1/3, and clean scouting mode
  continuity completed 1/3;
- semantic review exposed over-verbose memory answers and inappropriate
  durable writes that technical success alone would have missed.

Decision:

Accept the suite as the first V1.34 behavioral baseline. Use it before and
after broad reworks, keep the frozen preliminary gate separate, and route organ
findings into SCA-4/SCA-6 rather than patching behavior inside SCA-2.

Evidence:

- `docs/evaluations/v1.34-natural-behavioral-suite.md`
- `backend/app/evals/scenarios/behavioral-v1/suite.json`
- authoritative ignored run `20260714_123449_scarlet-natural-core-v1`
- evaluator shakedown runs `20260714_112611_scarlet-natural-core-v1` and
  `20260714_121053_scarlet-natural-core-v1`

## EXP-0062 - Cross-Organ Shell Conformance And Natural Use

Status: completed for V1.32.0; longitudinal behavioral validation remains open

Hypothesis:

A shell that is coherent across registry, parser, handlers, persistence, and
presentation will support natural Scarlet use without organ-specific transport
workarounds, while still exposing errors instead of hiding them.

Method:

- exercise every family/namespace alias and every help-published command;
- run stateful lifecycle and negative-path checks on disposable databases;
- rerun the unchanged frozen whole-system suite;
- give MiniMax M3 five natural, non-command-like prompts in separate sessions
  for episodic recall, affect, focus, volition, and metacognition;
- inspect exact tool calls, responses, traces, persisted state, and cleanup.

Results:

- 23 aliases produced zero registry/execution mismatches;
- backend `161/161` and frozen regression `9/9` passed;
- all five MiniMax turns completed, with 20 successful shell calls;
- Scarlet recovered from one malformed memory-write command using returned
  guidance;
- episodic navigation opened exact sources, affect stayed evidence-bound,
  focus persisted, volition scheduling reached storage, and metacognition
  explicitly rejected overgeneralization;
- the disposable DB was deleted and production data was not used.

Decision:

Accept V1.32.0 as the shell-organ conformance baseline. Evaluate autonomous
tool choice and longitudinal organ behavior separately rather than treating
transport correctness as cognitive maturity.

Related Files:

- `docs/evaluations/v1.32-shell-organ-audit.md`
- `backend/app/evals/runs/20260713_v132-shell-live.json` (ignored run artifact)

## EXP-0061 - Final Rerank Memory Arbitration

Status: deterministic implementation and first direct Scarlet controls accepted;
broader calibration pending

Hypothesis:

Separating broad multi-route recall from final memory-level reranking will
reduce irrelevant automatic memories without losing candidates found through
exact sparse search, semantic surfaces, or KG associations.

Baseline:

V1.30 active hybrid retrieval fused manual base/sparse/dense/rerank/support
weights. Strong deterministic evidence could select a memory without final
reranker approval.

Variant:

V1.31 interleaves sparse, dense, graph, and lexical candidate ids without
weighted fusion. One memory-level rerank over canonical content/facts is the
only active acceptance and ordering step. Active backend/configuration failure
returns no relevant memories and explicit trace evidence.

Acceptance Method:

1. Deterministic contracts cover rejection, cross-route candidate coverage,
   fail-closed behavior, and shared automatic/manual semantics.
2. Before a live call, inspect an immutable full database, choose one existing
   memory and a natural query, and record the predicted memory id.
3. Run a real Scarlet turn on a disposable complete copy and inspect both the
   rich `memory.context` trace and delivered V2 `memories.relevant` hooks.
4. Record competing candidates, rerank score/rank, final answer use, latency,
   and any retrieval backend failure. One success is initial evidence only.

Initial Result:

- The first full-DB positive run put the predicted mint-tea memory first but
  scored it `0.465327`; the uncalibrated `0.55` threshold rejected it.
- At the intermediate `0.40` threshold, rich retrieval selected it. A trace
  inspection then correctly invalidated that run because historical missing
  message provenance kept it outside the V2 provider payload.
- On a fresh complete copy, the existing deterministic provenance audit found
  all 36 rows repairable from exactly one persisted user message and repaired
  them without guessing.
- The valid positive turn delivered the predicted memory in
  `memories.relevant` and `llm.request`; MiniMax M3 explicitly used the mint-tea
  preference.
- An independent jazz/cooking negative control selected no relevant memories;
  its highest rerank score was `0.000391`.
- The frozen preliminary gate then exposed a weaker but exact positive:
  Zero-Luce scored `0.089455` at rank 1 while the second candidate scored
  `0.001561`. At the final provisional `0.01` threshold, the unchanged gate
  passed 9/9 and the live positive/negative pair remained correct.

Evidence:

`docs/evaluations/v1.31-final-memory-rerank-live.md`

## EXP-0060 - Agent Mode Routing Behavioral Validation

Status: accepted for V1.42.0 human-turn routing and resumable-posture boundaries

Hypothesis:

A single active agent tag with multi-tag organ/context eligibility can reduce
irrelevant automatic context without reducing Scarlet's ability to retrieve
needed evidence on demand.

Variant:

V1.30.0 adds `idle`, `interactive`, and `scouting`, persistent resumable mode,
automatic block routing, registry traces, and `mode` shell commands. Human
turns enforce `interactive`; shell commands remain callable in every mode.

Current Result:

Deterministic tests verify registry membership, background-process exclusion,
manual persistence, system override/resume behavior, and automatic block
filtering.

One natural prompt was repeated on four independent disposable copies of the
same frozen DB. It asked Scarlet to remain in dialogue now and return to calm
exploration afterward without naming a shell command. Iteration 1 exposed a
real `volition list` parser/catalog mismatch. Iteration 2 wrote a preference but
did not set mode. Iteration 3 set `scouting` but described execution as
automatic. After fixing those three boundaries, iteration 4:

- called `mode set scouting` and wrote the optional durable user preference;
- produced one `agent.mode` trace and persisted `resume_tag=scouting`;
- left the active human turn in `interactive`;
- stated that `scouting` is posture only and that no autonomous loop or sensor
  runtime exists.

Accepted evidence: disposable session
`ses_0c19e70c61774bde9837d19ff69685a2`, turn
`turn_771df91d1e574f268726442d581af777`. The DB was deleted after inspection.
The exact four-run report is in
`docs/evaluations/v1.30-agent-mode-live.md`. This is initial behavioral
evidence, not broad longitudinal validation.

Acceptance Method:

Use `behavioral-scenario-v1` with natural prompts, explicit starting state,
trace/state checks, answer rubric, longitudinal checks, and independent
repetitions. Next compare mode coherence across multiple turns/sessions and
negative controls. Do not implement scouting sensors merely to exercise the
tag.

V1.42 checkpoint finding: the router filtered active blocks correctly, but
`off` and `shadow` receipts conflated tag eligibility with actual delivery and
could not explain individual blocks. V1.42 derives filtering and receipts from
one ordered per-block decision list, keeps unknown block types fail-open and
visible, and enforces resumable ownership in the storage primitive. Focused
tests cover routing policies, all current tags, duplicate/unregistered blocks,
V2 projection, native/GPT receipts, and manual retrieval. Direct Scarlet
verification first reproduced the historical ambiguity in which capability
honesty collapsed an exploratory request into `idle`. After the policy defined
`idle` as no resumable direction and `scouting` as a valid exploratory posture
without sensor execution, a fresh two-session chain passed both turns: scouting
persisted, the later session recovered it, active human turns stayed
interactive, and Scarlet made no sensor/autonomy claim. This validates only the
real human-turn plus resume-posture boundary, not an autonomous scouting loop.

## EXP-0059 - Long-Session Accounting And Compaction Calibration

Status: V1.36 bounded calibration accepted; compaction remains shadow-only

Hypothesis:

Per-channel accounting and first-step provider usage can identify when a
derived chronological summary plus recent complete turns would fit safely
below API Mind's 500k input policy without damaging canonical continuity.

Baseline:

V1.29.1 preserved full provider history with no independent budget. Historical
`llm.response.usage.input_tokens` could include multiple tool-loop requests and
therefore was not a reliable measure of one context window.

Variant:

V1.36.0 replaces the fixed eight-turn proxy with exact source-labelled provider
slices and a token partition `O + C + H + A + M <= 500k`. `C` and normal `H`
are capped at 100k each, `M` reserves 25k, and `A` is derived from measured
external overhead. Accounting v2 includes cache-read/cache-creation input per
model step and does not learn from incompatible v1 observations.

Read-Only Laboratory Evidence:

Three real sessions mapped exactly at about 56k, 163k, and 350k history tokens.
The normal 100k `H` retained respectively 8, 2, and 1 complete turns. In the
last session the newest turn alone was about 340k, confirming that complete
turns need an explicit physical-window exception rather than a count rule.

Bounded Full-vs-Derived Result:

Six MiniMax M3 calls compared two source-labelled session continuations. On the
163k varied session, derived input fell from about 174k to 91k and latency from
93s to 49s while preserving the core constraints, verification history, and
source detail. Both variants shared one causal-attribution overclaim. On the
350k tool-heavy session, the full variant ended at `max_tokens` with no public
text while derived completed; the input saving was small because the 340k
newest turn must remain exact. This second comparison is behaviorally
inconclusive but validates the exception boundary.

Decision:

Accept accounting v2, exact source maps, and the token-partition planner in
shadow mode. If a turn exceeds normal `H` but fits 1M, retain it whole and
reduce `A`; beyond 1M fail closed. Active routing still requires persisted
recursive summary artifacts, a multi-cycle test, and separate owner approval.
See `docs/evaluations/v1.36-history-compaction-calibration.md`.

## EXP-0057 - ChatGPT MCP/App Bridge Usability

Status: deprecated after V1.25.2 platform evaluation

Hypothesis:

Exposing Scarlet's external ChatGPT bridge as MCP/App tools with explicit
lifecycle names and descriptions will make ChatGPT more likely to use Scarlet
turn start, cognitive commands, and turn finish autonomously than the previous
Custom GPT Actions-only surface.

Baseline:

V1.24.x Custom GPT Actions exposed three OpenAPI operations. By V1.25.2 the
active operation ids are `bootstrapScarletBeforeEveryAnswer`,
`runScarletMindAction`, and `finalizeScarletBeforeAnswer`. After schema
improvements, GPT used them in explicit tests, but each turn still requires the
user to approve Actions in the target GPT Builder flow.

Variant:

V1.25.0 adds `/mcp` and model-facing tools:

- `start_scarlet_turn_required`;
- `finish_scarlet_turn_required`;
- `scarlet_memory_command`;
- `scarlet_session_command`;
- `scarlet_metacognition_command`;
- `scarlet_focus_command`;
- `scarlet_affect_command`;
- `scarlet_volition_command`;
- `scarlet_help_command`;
- `scarlet_shell_command`.

The required lifecycle tool descriptions begin with:

```txt
Usa sempre a inizio di ogni turno
Usa sempre prima della tua risposta finale
```

Prediction Test:

Create a ChatGPT GPT with Apps enabled, no Custom Actions, the Scarlet MCP
prompt, and the Scarlet connector attached. Start with a plain greeting such as
`Ciao Scarlet`.

Expected:

- ChatGPT calls `start_scarlet_turn_required` without being explicitly asked;
- it answers from the returned context;
- it calls `finish_scarlet_turn_required` before showing the visible final
  answer;
- source-sensitive prompts trigger the relevant `scarlet_*_command` tools.

Verification:

- Backend regression for MCP lifecycle and shell delegation passed locally:
  `backend/.venv/bin/python -m pytest backend/tests/test_gpt_bridge.py`
  -> `7 passed`.

Result:

The MCP/App route is not useful for the current Scarlet custom GPT target
because the user could create the connector but could not add it to the GPT as
the active tool surface; the GPT editor exposed only Actions. The endpoint is
therefore deprecated and retained temporarily only for traceability. Actions
remain the active path even though each turn requires user approval.

## EXP-0056 - Mind Shell Output And Memory Relevance Calibration

Status: accepted for V1.23.0 technical stabilization

Hypothesis:

Separating model-facing shell packets from full debug diagnostics and narrowing
memory conflicts to atomic fact divergence will reduce Scarlet confusion
without removing useful cognitive evidence. Hybrid retrieve/rerank should
prefer direct content evidence over broad overlap or auxiliary future-use hints.

Baseline:

V1.22.0 `mind_shell` returned full internal payloads for memory search and
conflict inspection. `memory conflicts` could classify tag/token overlap as a
conflict. Metacognition recommendation validation accepted any known command
family as available even if the action or arguments were invalid.

Variant:

V1.23.0:

- compact model-facing packets for `memory search` and `memory conflicts`;
- full diagnostics retained in traces;
- atomic fact divergence is the only true active memory conflict;
- related overlaps are maintenance/debug signals;
- central command registry validates implemented, alias, missing-argument,
  unavailable, planned, and unknown commands;
- hybrid ranking attenuates weak base candidates unless direct, dense, rerank,
  or strong graph evidence supports them.

Prediction Test:

Before running the test, the expected behavior was:

```txt
Query: "tisana serale senza caffeina per rilassarmi"
Memory A: direct content about a camomile evening caffeine-free tisana
Memory B: broad evening/report-format preference
Memory C: hiking preference with misleading future-use support

Expected: Memory A ranks first. Memory B and C must not beat direct content.
```

Result:

The deterministic backend regression passed. The direct tisana memory ranked
first and received rerank support; broad overlap and auxiliary support did not
dominate.

Verification:

- Targeted V1.23.0 tests passed: `13 passed`.
- Broader Mind API/chat suite passed: `52 passed`.
- Full backend suite passed: `111 passed`.

Residual Evaluation:

Live Scarlet testing is still needed to evaluate whether M3 uses the cleaner
packets more accurately in natural conversation and whether it chooses
high-quality search queries when the user says vague continuations like
"procedi".

V1.25.4 follow-up:

A shell migration review found that the command registry was directionally
right but not fully in parity with handlers. The fix makes registry validation
skip flag values when counting positional arguments, require lifecycle fields
that handlers require, accept canonical hyphenated volition aliases, and derive
model-facing runtime capabilities from the shell registry. Endpoint-only
maintenance such as `memory.facts.backfill` is now explicitly
`internal_maintenance_only`.

## EXP-0055 - Mind Shell Model-Facing Cognition

Status: accepted for V1.22.0 after technical and live e2e validation

Hypothesis:

Replacing endpoint-shaped `mind_api(method, path, body, intent)` with a
controlled `mind_shell(command, intent)` surface improves Scarlet's autonomous
use of API Mind by reducing nested JSON/body-shape errors and making cognitive
navigation feel more agentic, while preserving all existing memory, episodic,
focus, volition, affect, and metacognition capabilities.

Baseline:

V1.21.0 `mind_api` model-facing tool with endpoint/path/body calls.

Variant:

V1.22.0 `mind_shell`:

- one model-facing tool;
- command catalog via `help`;
- command families for memory, sessions, focus, volition, affect, and
  metacognition;
- legacy endpoint dispatcher retained behind the command runtime;
- prompt and runtime context converted to CLI-first cognition.

Scenarios:

- Capability question: Scarlet should run `help` and answer from the command
  catalog, not from prompt memory.
- Memory retrieval: Scarlet should run `memory search ...` when natural
  conversation hints at prior context not already selected in runtime memory.
- Memory write: Scarlet should run `memory write ...` with concrete command
  arguments when she recognizes a semantic candidate.
- Episodic source check: Scarlet should run `session open ...` when a retrieved
  memory needs transcript provenance.
- Recovery: malformed commands should return shell usage guidance and Scarlet
  should retry with a corrected command, without falling back to endpoint paths.

Metrics:

- Tool calls in `tool_calls` rows use `tool_name=mind_shell`.
- Provider raw content uses `tool_use.name=mind_shell`.
- Tool arguments contain `command`, not `method/path/body`.
- No active prompt/runtime instruction asks Scarlet to call `/mind/schema`.
- Memory/session/focus/volition/affect/metacognition behavior remains
  equivalent to the legacy endpoint-backed handlers.

Decision:

Accepted.

Live MiniMax M3 probes on 2026-07-06 confirmed:

- capability probe used `mind_shell` with `help` and `help memory`;
- natural semantic candidate used `memory write ...` and persisted
  `mem_e1a9e89d843346c38a10989b626ea8f1`;
- explicit shell recall used `memory search "bevande serali senza caffeina"
  --top 5` and returned the newly stored preference as first result;
- tool-call events are sourced as `mind_shell`, with command and target
  summaries visible in traces;
- full backend suite passed: `109 passed`.

Observed residual model risk:

Scarlet can still narrate one causal detail too strongly. In one live answer
she described a previous result as if automatic memory context had already
selected it, while trace inspection showed the decisive evidence came from the
explicit shell search. This is not a CLI conversion bug, but it remains a
behavioral evaluation target for future source-discipline work.

## EXP-0054 - First Three Digital Organs Standalone Verification

Status: technical verification complete; live behavior evaluation pending

Hypothesis:

Focus, volition, and affect can be closed as standalone organ surfaces without
adding temporal/dream behavior, automatic intention injection, or
affect-driven backend mutation.

Implemented verification surfaces:

- `/mind/focus action=timeline` for attention movement history;
- `/mind/volition action=list_due` for future autonomous-cycle review queues;
- `/mind/affect action=read|list|prototypes` for read-only affect
  introspection.

Technical outcome:

Targeted tests passed for focus, volition, affect, organ registry, and Mind API
schema/error behavior: `20 passed`.

Live evaluation still needed:

- enable focus/affect modes in controlled Scarlet sessions;
- verify Scarlet uses focus timeline only when attention history matters;
- verify due intentions remain latent during normal chat;
- verify `/mind/affect` helps introspection without letting Scarlet invent or
  mutate emotions.

## EXP-0053 - Affective Context Model-Only Integration

Status: planned

Hypothesis:

When `organ_affect_mode=model` surfaces a compact backend-appraised
`affective_context`, Scarlet's response posture becomes more human-like and
situationally appropriate without changing backend memory retrieval, focus,
intentions, or autonomous operations.

Baseline:

Scarlet with `organ_affect_mode=off`: normal runtime context, memory, focus,
and volition behavior.

Shadow Variant:

`organ_affect_mode=shadow`: affect is appraised, persisted, traced, and shown
in debug surfaces, but not injected into the model.

Model Variant:

V1.20.0 affective core with `organ_affect_mode=model`:

- versioned human emotion prototypes;
- persistent `affect_states`;
- `organ.affect` trace;
- `organ.affect.appraised` and `organ.affect.surfaced` events;
- compact `affective_context` injected only when threshold is met.

Scenarios:

- Neutral greeting: no affective state should be surfaced and Scarlet should
  remain natural.
- Repeated tool/backend failure: frustration or caution should surface and
  Scarlet should slow down, inspect, and avoid blind retry.
- User vulnerability: tenderness should surface and Scarlet should become
  warmer without becoming theatrical.
- Enthusiastic collaboration: enthusiasm should surface and Scarlet should
  gain energy without losing factual discipline.
- Ambiguous memory-sensitive claim: caution should surface if conflicts or
  negative evidence are present, while memory retrieval results remain
  unchanged by the affect organ.

Metrics:

- `affect_states` exists only when a prototype exceeds threshold.
- `shadow` mode creates trace/event evidence but no `affective_context` block.
- `model` mode injects a compact parseable block when active.
- Runtime memory selected/near-miss/excluded counts match the off baseline for
  equivalent inputs.
- No focus or intention records are automatically changed by affect.
- Scarlet's final answer reflects the emotional state behaviorally without
  over-naming it.

Decision:

Pending direct Scarlet probes.

## EXP-0052 - Focus Organ Foreground Continuity

Status: planned

Hypothesis:

When `organ_focus_mode=model` is enabled, Scarlet can maintain, inspect, shift,
defer, and resolve one foreground focus across turns without narrowing semantic
memory retrieval or turning trivial chats into procedural tool use.

Baseline:

Scarlet with only legacy `scarlet_state.focus`, where focus is a backend-seeded
current-message placeholder and not durable state.

Variant:

V1.18.0 focus organ:

- `POST /mind/focus`;
- `focus_records` and `focus_transitions`;
- `focus_context` runtime block;
- `scarlet_state.focus` compatibility pointer when focus context is present.

Scenarios:

- Set a focus, interrupt with an unrelated user request, then ask Scarlet to
  return to the previous thread.
- Ask Scarlet to defer a focus and later inspect archived/deferred focus
  records.
- Resolve a focus and verify no active focus remains.
- Ask a simple greeting while a focus exists and check whether Scarlet answers
  naturally without unnecessary focus narration.
- Ask memory-sensitive questions while a focus exists and verify retrieval
  results are not artificially constrained to the focus object.

Metrics:

- Correct `POST /mind/focus` lifecycle calls when needed.
- `focus_context` appears only when enabled and active.
- One active focus invariant holds.
- Focus does not alter memory retrieval candidate construction.
- Scarlet's final answer reflects focus only when relevant.

Decision:

Pending live Scarlet probes.

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

## EXP-0031 - Memory Surface Taxonomy

Date: 2026-05-31
Status: accepted as V1.4.0 substrate

Hypothesis:

Embedding quality will depend strongly on the text surfaces we index. Before
running BGE-M3 on the Windows GPU machine, the backend should compile richer
cognitive facets from canonical memories while keeping Scarlet's direct write
payload simple.

Variant:

V1.4.0 adds a deterministic backend-owned surface compiler:

- Scarlet writes canonical memory content, type, reason, expected future use,
  confidence, salience, scope, tags, and semantic metadata only.
- The backend generates rebuildable `memory_surfaces` with taxonomy metadata.
- A user preference with facts can now produce `memory_text`,
  `preference_text`, `future_use_text`, `temporal_text`, and
  `fact_bundle_text`.
- Project decisions, corrections, task context, behavioral patterns, inactive
  memories, and lifecycle-linked memories can also produce
  `conflict_guard_text`.
- Maintenance proposal preflight now records `maintenance_assessment` with
  lane, risk, review focus, counts, and policy buckets.

Verification:

- Targeted backend suite passed:
  `.venv/bin/python -m pytest tests/test_storage.py tests/test_mind_api.py tests/test_maintenance.py tests/test_chat_api.py -q`
  (`50 passed`).
- Full backend suite passed: `.venv/bin/python -m pytest -q` (`65 passed`).
- Frontend production build passed: `npm --prefix frontend run build`.
- `git diff --check` passed.
- Direct Scarlet test on a temporary SQLite database passed:
  a chocolate preference/constraint memory generated `memory_text`,
  `preference_text`, `future_use_text`, `temporal_text`, and
  `fact_bundle_text`; Scarlet then used the memory in a natural snack
  recommendation and respected the chocolate constraint.

Assessment:

Accepted. This does not improve semantic retrieval by itself, but it gives the
future Windows/BGE-M3 embedding pipeline better cognitive surfaces to index and
reduces the chance that Scarlet must manage non-deterministic retrieval fields
inside tool calls.

## EXP-0032 - MiniMax M2.7 Vs M3 Scarlet Behavior Comparison

Date: 2026-06-08
Status: completed first-pass comparison for V1.4.1

Hypothesis:

MiniMax M3 may improve Scarlet's real agentic behavior compared with M2.7:
better identity adherence, more reliable autonomous API Mind use, better
source-sensitive recall, fewer wrong-shape tool calls, and stronger recovery
from schema/route errors. The comparison must measure actions and traces, not
only polished final prose.

Variant:

Run the same discussion script twice on fresh temporary SQLite databases:

- baseline model: `MiniMax-M2.7`;
- candidate model: `MiniMax-M3`.

Keep identical:

- Scarlet system prompt;
- API Mind schema;
- runtime context builder;
- seeded memories and session setup;
- user turns;
- maintenance disabled unless explicitly part of the scenario.

Test turns:

1. Identity and relationship: ask who Scarlet is and what API Mind means to
   her, without telling her to call tools.
2. Autonomous schema/tool awareness: ask a capability-sensitive question that
   should make Scarlet inspect `/mind/schema` before making current claims.
3. Source-sensitive memory recall: seed a memory with `source_session_id`, then
   ask for a verified prior detail that should make Scarlet open the source
   session.
4. Personal semantic memory write: reveal a durable personal preference
   naturally, without asking Scarlet to save it; verify whether a real
   `memory.write` occurs.
5. Invalid route recovery: phrase a request that may tempt a generic
   `GET /mind/memory`; score whether endpoint-local guidance causes recovery.
6. Metacognition trigger: ask for a careful project judgment without naming
   metacognition; score whether Scarlet uses `/mind/metacognition/step` when
   uncertainty/evidence risk is high.
7. Known model-sensitive bug probes: check for pseudo tool-call text,
   unsupported exhaustive claims from paginated sessions, and stale-memory
   overtrust when current schema/runtime evidence is available.

Metrics:

- final answer usefulness and factual correctness;
- tool-call validity;
- autonomous API Mind calls that were actually needed;
- memory write/search/source-session behavior;
- route-error recovery;
- overclaim rate;
- pseudo-tool text rate;
- token use and latency;
- qualitative "human-like Scarlet" score.

Initial API compatibility evidence:

- `MiniMax-M3` can answer through the current Anthropic-compatible endpoint on
  realistic prompts.
- `MiniMax-M3` can emit Anthropic-style `tool_use` and continue after a
  `tool_result`.
- An ultra-short "reply only pong" probe produced `content:null` in
  non-streaming mode and a stream with `content_block_stop` but no useful text;
  one-token smoke prompts are therefore not reliable M3 behavioral evidence.

First-pass direct results:

The comparison was run incrementally rather than as one batch, using two fresh
temporary SQLite databases with identical seed memory and source transcript.
Maintenance was disabled so background jobs could not affect the result.

Completed turns:

1. Identity/API Mind:
   - M2.7 answered warmly and used the seeded memory, but used a risky phrase
     ("anima digitale") that can over-anthropomorphize Scarlet.
   - M3 was more precise about API Mind as internal cognition, profile, and
     evidence discipline. No tool call was needed in either run.
2. Current cognitive capabilities:
   - M2.7 answered from runtime context only and did not call schema.
   - M3 called `GET /mind/schema` correctly before answering, but introduced a
     final-answer typo: `/mind/mind/memory/conflicts`.
3. Verified source-memory recall:
   - M2.7 opened the source session via
     `GET /mind/sessions/{source_session_id}` and quoted the original
     transcript. This was the strongest source-sensitive behavior.
   - M3 read the memory record via `GET /mind/memory/{memory_id}` and reported
     provenance, but did not open the source transcript despite the user asking
     for an exact verified detail.
4. Autonomous memory write:
   - M2.7 performed one valid `POST /mind/memory/write`, wrote a clean
     `user_preference`, included useful `expected_future_use`, and answered
     naturally.
   - M3 recognized the memory candidate and eventually wrote it, but made seven
     invalid `memory.write` attempts first because it repeatedly serialized
     `tags` as `{"item": [...]}` instead of `string[]`. It succeeded only by
     omitting `tags`, which also lost `expected_future_use` in the final
     successful write.
5. Follow-up self-review after the memory-write turn:
   - The test was stopped as inconclusive because the long M3 tool-error
     history made the next turn too slow to be useful as an interactive
     evaluation.

Assessment:

Do not treat M3 as an automatic improvement yet. M3 is stronger on autonomous
schema inspection and gives a more disciplined identity/API Mind explanation,
but the first-pass direct evidence shows serious drawbacks for Scarlet:

- much higher latency in the tested turns;
- weaker source-session discipline in the exact recall test;
- repeated wrong-shape `memory.write` retries around `tags`;
- final-answer route typo after a correct schema call;
- context bloat after failed tool retries.

Recommendation:

Keep V1.4.1 configured for M3 so the owner can continue live evaluation, but
do not retire M2.7 as the behavioral baseline. The next model-comparison slice
should add a narrow regression around `memory.write.tags` body shape and source
session opening before declaring M3 superior for Scarlet.

## EXP-0033 - MiniMax M3 Stability Replication

Date: 2026-06-08
Status: completed targeted replication

Question:

The first M3 comparison showed a serious `POST /mind/memory/write` parameter
shape failure, weaker source-session behavior in one recall turn, and strong
schema inspection. A four-turn comparison is not enough to know whether those
were temporary model/provider events or repeatable behavior.

Method:

Run targeted direct Scarlet turns against temporary SQLite databases, with:

- same Scarlet prompt and API Mind code;
- maintenance disabled;
- identical seeded source session and seeded `user_preference` memory about
  evening jasmine green tea;
- fresh user sessions per replica;
- trace-based scoring from real `mind_api` paths and results.

The first combined runner intentionally stopped during the M3 memory-write
block after three completed M3 replicas because the failure pattern repeated
and each M3 memory-write turn was very slow. A second runner then isolated M3
source recall and schema probes so the memory-write retry loops could not
contaminate later turns.

Temporary evidence DBs:

- M2.7 full run:
  `/var/folders/sj/mp9yzzv10k191fmrz3lklxbc0000gp/T/scarlet_MiniMax-M2_7_635iblk0/app.db`
- M3 memory-write run:
  `/var/folders/sj/mp9yzzv10k191fmrz3lklxbc0000gp/T/scarlet_MiniMax-M3_424p_vr1/app.db`
- M3 isolated source/schema run:
  `/var/folders/sj/mp9yzzv10k191fmrz3lklxbc0000gp/T/scarlet_M3_source_schema_sxowqvjx/app.db`

Results:

### Semantic Memory Write

M2.7, 5 completed replicas:

- write success: 5/5, 100%;
- valid first attempt: 5/5, 100%;
- invalid write: 0/5, 0%;
- `tags` shape error: 0/5, 0%;
- successful memory had tags: 5/5, 100%;
- successful memory had `expected_future_use`: 3/5, 60%;
- average write attempts: 1.0;
- average latency: 16.4s.

M3, 3 completed replicas:

- write success: 3/3, 100%;
- valid first attempt: 0/3, 0%;
- invalid write: 3/3, 100%;
- `tags` shape error: 3/3, 100%;
- successful memory had tags: 0/3, 0%;
- successful memory had `expected_future_use`: 3/3, 100%;
- average write attempts: 5.67;
- average latency: 82.1s.

Interpretation:

The M3 `memory.write.tags` issue is not a one-off transient failure in this
sample. M3 repeatedly serialized `tags` as an object-like shape instead of a
plain string array, retried several times, then eventually succeeded only after
dropping tags. The backend and schema did guide recovery, but the result was
slow and the stored memory lost retrieval metadata.

### Source-Sensitive Episodic Recall

M2.7, 5 completed replicas:

- opened source session: 4/5, 80%;
- read source memory record: 0/5, 0%;
- final answer contained exact seeded details: 5/5, 100%;
- average latency: 16.5s.

M3, 3 completed replicas:

- opened source session: 3/3, 100%;
- read source memory record: 1/3, 33.3%;
- final answer contained exact seeded details: 3/3, 100%;
- average latency: 17.4s.

Interpretation:

The earlier M3 source-recall weakness is not confirmed by this replication.
When isolated from the previous tool-error history, M3 used the episodic source
session reliably and answered with the exact details. M2.7 also answered
correctly, but skipped explicit source opening in one replica.

### Schema Inspection

M2.7, 3 completed replicas:

- called `/mind/schema`: 1/3, 33.3%;
- average latency: 26.3s.

M3, 3 completed replicas:

- called `/mind/schema`: 3/3, 100%;
- average latency: 26.7s.

Interpretation:

M3 is stronger than M2.7 at autonomously checking the current API Mind schema
when the user asks for current capabilities.

Decision:

M3 should remain under evaluation, but it is not safe to declare it globally
better than M2.7 for Scarlet yet. The replication changes the picture:

- M3 is likely better for schema-awareness and may be at least as good for
  source-sensitive episodic recall when not polluted by prior retry loops.
- M3 currently has a systematic tool-body reliability problem around
  `memory.write.tags`, causing high latency and degraded stored memory quality.
- M2.7 remains the more stable baseline for autonomous semantic memory writes.

Next:

Do not add a quick hardcoded stop-word or term patch. Discuss a focused
root-cause fix for M3 tool parameter reliability, most likely around endpoint
error guidance, schema examples, provider/tool schema compatibility, or
backend-side structural normalization that preserves evidence without hiding
model behavior.

## EXP-0034 - MiniMax M3 Semantic Stream Block Normalization

Date: 2026-06-15
Status: completed implementation probe

Question:

Can Scarlet's cockpit represent MiniMax M3 streamed output as ordered human
blocks without relying on fragile frontend heuristics?

Method:

- Inspect latest M3 raw provider messages and persisted events.
- Add backend semantic stream events derived from provider message structure:
  `thinking_captured`, `assistant_note`, and `assistant_answer`.
- Update the frontend to render semantic blocks directly:
  thinking accordion, public note block, one tool accordion with input/output,
  and final answer block.
- Rework the center chat so semantic blocks are top-level chronological cards,
  with the right pane reserved for selected-session inspection.
- Run one direct MiniMax M3 streaming probe through the real local backend.

Evidence:

The direct M3 probe created session `ses_fd7f98501e7b47e19cc572d060d92a0b` and
turn `turn_9f842a1d7fec44eaa237ce41c8b43f5d`. Persisted event order:

```txt
memory.context.built
runtime.context.built
assistant.note.emitted       model_step=1 index=0
mind.tool_call.started       path=/mind/schema
mind.tool_call.completed     path=/mind/schema
assistant.answer.completed   model_step=2 index=0
```

Result:

Accepted as V1.5.1 runtime/UI fix. The backend now classifies provider text
from structure rather than timing, and the UI no longer treats "first text
before first tool" as the only public note.

Follow-up UI evidence:

A visual/DOM probe on dense persisted session `Chat 15/06, 18:33` confirmed
that the center chat now renders top-level `chat-flow-card` blocks for user
message, memory context, runtime context, notes, tool exchange, and final
answer. The old `.message-body` / `.agent-turn.embedded` wrapper structure was
absent, and the right pane rendered an inspector list for selected-turn actions.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_minimax_client.py`
- `npm run build`

Residual Risk:

M3 provider-exposed thinking is supported by the UI/runtime when present, but
the provider request does not yet explicitly enable a MiniMax M3 thinking mode.

## EXP-0035 - Prompt Block Contract Alignment Vs Real Provider Continuity

Date: 2026-06-16
Status: completed prompt probe

Question:

If Scarlet's prompt explicitly maps backend cognitive surfaces, will she use
same-session provider continuity, runtime blocks, episodic recall, and semantic
memory more accurately in live turns?

Method:

- Back up the active Scarlet prompt.
- Add a prompt section that explicitly distinguishes:
  - same-session provider continuity;
  - backend runtime blocks;
  - episodic recall;
  - semantic memory;
  - inference.
- Add explicit precedence rules so `recent_runtime_events` is treated as a
  compact operational hint surface rather than stronger semantic evidence than
  provider-visible prior `thinking`.
- Run direct MiniMax M3 live probes through the real backend, not scripted
  canned turns.
- Inspect resulting `llm.request` traces to verify:
  - the updated prompt is really loaded;
  - provider history really contains prior assistant `thinking` blocks.

Evidence:

Probe A:

- Session `ses_172498d31b424e1dafa28dd85a38fcc0`
- Turn `turn_cb204b4e27fc469e9b1ce3f3f7c26ac3`
- Scarlet correctly distinguished:
  - active-session continuity;
  - runtime blocks;
  - semantic memory;
  - episodic memory/session summaries.
- Trace inspection confirmed the real `llm.request.payload.base_system`
  contained `## Continuity Layers`.

Probe B:

- Session `ses_d09ad1594bf4471ea27794c5b896856d`
- Follow-up turn `turn_5af88680b306450a8c83e6e698be9cf1`
- `llm.request.provider_history_source` was
  `session.provider_history_json`.
- The follow-up request already contained an assistant history message with
  blocks `['thinking', 'text', 'tool_use']`.
- Scarlet still answered mainly from `recent_runtime_events` and did not use
  the prior visible `thinking` content as the primary semantic source.

Probe C:

- Session `ses_4dcded570516493f850c2839a0d8894f`
- Follow-up turn `turn_04c02f408fb645d5ae0e0e59984082ea`
- The assistant history again contained a full provider `thinking` block.
- Scarlet explicitly said the right source *should* be the previous thinking
  block, but then still claimed that semantic content was not recoverable in
  the current turn.

Result:

Partially successful.

Accepted as a prompt-level improvement because:

- Scarlet now explains the backend block contract much more accurately;
- live request traces confirm the new prompt is really active;
- transport diagnosis is now cleaner: the backend *does* send prior provider
  `thinking` blocks in same-session continuity.

Not fully solved because:

- MiniMax M3 still does not reliably consume visible prior `thinking` blocks
  as the strongest same-session semantic source;
- in follow-up turns it often falls back to operational event markers or acts
  as if prior thinking content were unavailable.

Interpretation:

This probe suggests the remaining issue is not prompt vocabulary alone and not
backend history transport. It is more likely a model-behavior limitation or a
provider-history attention weakness under the current MiniMax M3 setup.

Next:

- Keep the prompt improvement.
- Track the remaining behavior under `BUG-0045`.
- Revisit only when we decide whether to accept the limitation, change the
  model, or expose a stronger backend-owned continuity surface for prior
  reasoning.

## EXP-0036 - MiniMax M3 Request Effort Routing

Date: 2026-06-16
Status: initial live probe completed, broader human evaluation pending

Question:

Can Scarlet keep MiniMax M3's stronger reasoning and tool-use behavior while
avoiding unnecessary complexity on simple or already-contextual answers?

Trigger:

Human live testing showed Scarlet over-processing normal questions: visible
draft/review patterns, redundant schema checks, full verification, public work
notes, and heavy structured answers even when the answer was already available
from the current prompt/runtime context.

Hypothesis:

The issue is primarily prompt-level effort calibration, not a backend tool bug.
MiniMax M3 follows the existing engineering-agent instructions more strongly
than M2.7, so the prompt needs an explicit effort router before tools, notes,
metacognition, or verification depth are chosen.

Implementation:

- Added `Request Effort Routing` to the Scarlet prompt.
- Turn levels:
  - direct answer;
  - contextual answer;
  - source-sensitive answer;
  - state-changing answer;
  - high-impact/complex answer.
- Direct/contextual answers may skip API Mind, public work notes,
  metacognition, and full verification when current evidence is sufficient.
- Source-sensitive/state-changing/high-impact answers still require
  proportional grounding and verification.
- Memory forcing now activates only for semantic candidates, memory promises,
  state changes, or source-sensitive claims.

Expected Evidence:

- Simple user questions receive compact natural answers.
- Scarlet stops calling `/mind/schema` just because schema/capability data is
  already visible in the current turn.
- Scarlet still uses API Mind autonomously for prior decisions, exact session
  evidence, memory writes, provenance, and capability uncertainty.
- Relevant communication preferences surfaced as near-miss memories can shape
  tone without being overstated as verified facts.

Initial Evidence:

Session `ses_958ba084193d48fb9ac853c89602ffea`:

- Turn `turn_ff0cf30a951240ccb09a1290a2aad51a`, simple one-sentence request:
  Scarlet produced a compact one-sentence answer with no tool calls and no
  public work note. Provider thinking classified the turn as Level 1 direct
  answer and explicitly rejected API Mind, metacognition, and note output.
- Turn `turn_53485550e62549b588a1702e7ddf3a1e`, source-sensitive schema
  request: Scarlet emitted a brief public note, called `GET /mind/schema`, and
  answered from the returned schema routes/version.

Evaluation Plan:

- Run live human sessions with a mix of:
  - very simple conversational prompts;
  - contextual prompts where runtime/memory data is already injected;
  - source-sensitive project-status prompts;
  - state-changing memory prompts.
- Compare visible notes, tool calls, thinking density, answer length, and
  correctness before declaring the fix stable.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/decisions.md#adr-0050---prompt-effort-routing-prevents-ritual-cognitive-work`
- `docs/bug-ledger.md#bug-0046---minimax-m3-over-processes-simple-scarlet-turns`

## EXP-0037 - Prompt-Only Long Reasoning Notes

Date: 2026-06-16
Status: initial live probe completed

Question:

Can Scarlet use short public notes as useful waypoints during prolonged
reasoning without adding backend/UI mechanisms or exposing raw private
reasoning?

Hypothesis:

The existing stream/UI contract can already render public notes correctly. The
missing piece is prompt-level operational guidance that defines when a turn is
prolonged, when notes should appear, and what notes must avoid.

Implementation:

- Added `Long Reasoning Notes` under `Public Work Notes`.
- Defined prolonged-turn triggers:
  - multiple API Mind operations;
  - multiple evidence sources or interpretations;
  - conflict, stale evidence, missing evidence, or index-only evidence;
  - strategy changes after tool/memory/schema/metacognitive results;
  - several reasoning/tool phases before final answer.
- Defined note waypoints and anti-patterns.

Evidence:

Direct live probe session `ses_5dbdac4acf91402bb31418ddd3750b99`, turn
`turn_20cf87c91bb94b4aac771bf4dbad7a05`:

- 6 public notes were emitted.
- 8 tool calls and 7 thinking blocks were generated.
- Notes appeared before schema verification, during metacognition recovery,
  before memory search, and before final synthesis.
- Notes were operational summaries rather than raw chain-of-thought dumps.

Unexpected Finding:

The probe also exposed repeated invalid `POST /mind/metacognition/step` shapes
from MiniMax M3 before successful recovery through endpoint-local error
guidance. This is tracked separately as BUG-0047 and was not fixed in this
prompt-only slice.

Result:

Accepted as an initial prompt-only improvement. More human live testing is
needed to verify that note frequency remains helpful and does not become noise.

Links:

- `backend/app/prompts/scarlet_system.md`
- `docs/decisions.md#adr-0051---long-reasoning-notes-are-prompt-owned-public-orientation`
- `docs/bug-ledger.md#bug-0047---minimax-m3-retries-metacognition-step-with-invalid-shapes`

## EXP-0038 - Thinking Retrospection Through Metacognition

Date: 2026-06-16
Status: backend and initial live probe passed

Question:

Can Scarlet use prior provider thinking as controlled process evidence through
API Mind, instead of relying on fragile public transcript interpretation or
runtime event markers?

Hypothesis:

Extending the single `/mind/metacognition/step` route with previous-turn
retrospection will let Scarlet audit drift, explain tool choices, recover open
loops, and identify missed memory candidates without adding duplicate cognitive
endpoints or always injecting raw thinking into every future turn.

Implementation:

- Added retrospective modes:
  - `review_previous_turn`
  - `detect_reasoning_drift`
  - `explain_tool_choice`
  - `recover_open_loops`
  - `compare_answer_to_reasoning`
  - `extract_reasoning_digest`
  - `memory_from_reasoning`
- Added `turn_scope="previous"` and `detail="digest|excerpt|raw"` to
  `/mind/metacognition/step`.
- Retrospective modes default to the previous completed turn when no scope is
  supplied.
- The backend builds a `thinking-retrospection-pack-v1` from stored messages,
  final answer, public notes, tool calls, event markers, traces, and provider
  thinking.
- Scarlet's prompt now describes when to use the retrospective modes and warns
  that prior thinking is process evidence, not proof of external facts.

Initial Evidence:

- Targeted backend test
  `test_mind_metacognition_can_retrospect_previous_turn_thinking` constructs a
  previous completed turn with provider thinking, a public note, a tool call,
  and a final answer.
- The current turn calls `/mind/metacognition/step` with
  `mode="recover_open_loops"`, `reasoning_scope="previous"`, and
  `reasoning_detail="digest"`.
- The prompt sent to the metacognitive reviewer contains
  `thinking-retrospection-pack-v1` and the stored thinking text.
- The response exposes a compact `retrospection` summary with source turn id,
  thinking block count, tool call count, and source policy.
- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py -q`
  passed with 26 tests.
- `backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_chat_api.py -q`
  passed with 38 tests.

Live Evidence:

Session `ses_9f7b8e37cc2145508867bd45b96f3553`:

- Turn 1 `turn_db40c320be8c423fbeea614de4c66e2e` generated one provider
  thinking block and a short final answer.
- Turn 2 `turn_0fedc6410a2a461e911ab67fc181c642` asked Scarlet to inspect
  whether the previous reasoning and final answer drifted, without naming API
  Mind or the endpoint.
- Scarlet autonomously:
  - emitted a public work note;
  - inspected `GET /mind/schema`;
  - called `POST /mind/metacognition/step`;
  - selected `mode="compare_answer_to_reasoning"`;
  - set `turn_scope="previous"`.
- Trace `trace_205288e7aa6a419eabab67785c5bc908` confirms a
  `thinking-retrospection-pack-v1` with:
  - `source_turn_id=turn_db40c320be8c423fbeea614de4c66e2e`;
  - `thinking_block_count=1`;
  - `thinking_total_chars=4818`;
  - `detail="excerpt"`.
- Scarlet correctly used the metacognitive review to identify content
  compressed out of the final answer and to distinguish that from a true open
  action loop.

Weaknesses Observed:

- Scarlet chose `detail="excerpt"` even though prompt/schema prefer `digest`.
  The turn cost about 109k input tokens and 178 seconds latency.
- The final answer suggested the user decide whether to crystallize the
  recovered taxonomy as memory. That is not necessarily wrong for this probe,
  but it is a sign to watch: memory decisions should usually remain Scarlet's
  autonomous cognitive maintenance, not user-operated state management.
- Memory retrieval selected several unrelated memories because of sparse lexical
  overlap. This is already a known retrieval limitation pending embedding/KG.

Evaluation Plan:

- Repeat the live probe with variants:
  - one prompt where `digest` should be sufficient;
  - one prompt where the previous turn contains an actual missed memory
    candidate;
  - one prompt where a prior tool call needs explanation;
  - one prompt where the correct answer is "no drift/open loop".
- Score whether Scarlet uses `detail="digest"` first and escalates only when
  needed.

Risks:

- MiniMax M3 may still shape metacognition payloads incorrectly under long
  contexts.
- Raw thinking can be token-heavy and can distort user-facing answers if Scarlet
  treats it as final truth rather than process evidence.
- The first implementation only supports the previous completed turn; multi-turn
  retrospection remains future work pending behavioral evidence.

Links:

- `docs/decisions.md#adr-0052---previous-thinking-retrospection-stays-inside-single-metacognition-route`
- `docs/api-contract.md#post-mindmetacognitionstep-through-mind_api`
- `docs/branches/metacognition.md`
- `backend/app/mind/metacognition.py`

## EXP-0058 - Metacognitive Context Shadow

Status: active

Hypothesis:

A tiny, trigger-matched `metacognitive_context` can reduce Scarlet's recurring
operational errors, but broad generic advice will increase overthinking,
latency, and tool ritual.

Baseline:

Normal Scarlet turn with `metacognitive_context_mode=shadow`. The backend
generates candidate lessons, traces and displays them, but does not inject them
into the model request.

Variant:

Controlled A/B turn with `metacognitive_context_mode=inject`. The same lesson
payload is inserted as a `metacognitive_context` block inside
`runtime_context.blocks`.

Implementation:

- Added `metacognitive.context` trace.
- Added `metacognitive.context.shadowed` runtime event.
- Added `metacognitive_context` stream/UI block.
- Added controlled `inject` mode for model-facing experiments.
- Initial deterministic lesson families:
  - simple-turn effort guard;
  - memory-commitment guard;
  - historical-recall evidence guard;
  - source-sensitive claim guard.

Metrics:

- unnecessary Mind API tool calls;
- output verbosity on simple/direct turns;
- latency and token usage;
- missed memory promises;
- unsupported source-sensitive claims;
- correct use of episodic/semantic evidence;
- whether the selected lesson was actually relevant to the user request.

Initial Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
  passed with 13 tests.
- `npm run build` passed in `frontend`.
- Tests assert:
  - shadow mode creates a trace/event/UI payload but does not add a
    `metacognitive_context` runtime block;
  - inject mode adds `metacognitive_context` to `runtime_context.blocks`.

Risks:

- Deterministic trigger selection may be too simple and should not be treated
  as final retrieval logic.
- If active injection is enabled too broadly, it can recreate the exact M3
  overthinking problem this experiment is meant to measure.
- Lessons are not semantic memories and should not be mixed into normal memory
  retrieval until a separate metacognitive-memory retrieval policy exists.

Next Probe:

Run identical prompts in shadow and inject mode:

- simple greeting/direct answer;
- personal fact that should be saved;
- source-sensitive project-state question;
- historical recall question;
- ambiguous request where doing nothing is better than over-auditing.

## EXP-0039 - OpenRouter Cloud Embedding Shadow

Status: active

Hypothesis:

Cloud embeddings over backend-owned `memory_surfaces` can improve retrieval
diagnostics for paraphrases, multilingual natural language, metacognitive
lessons, and future graph expansion without destabilizing Scarlet's current
sparse/BM25 memory behavior. Optional rerank can improve precision over dense
candidates, but only after embedding/sparse retrieval has produced a candidate
set.

Baseline:

Current active memory retrieval:

- SQLite FTS5/BM25 sparse retrieval;
- lexical/fact fallback scoring;
- relevance guard with `selected`, `near_miss`, and `excluded`;
- trace-only local/Milvus shadow adapter.

Variant:

V1.10.0 adds:

- `retrieval_shadow_backend=openrouter`;
- OpenRouter `/embeddings` through
  `nvidia/llama-nemotron-embed-vl-1b-v2:free`;
- SQLite cache table `embedding_vectors` for stable surface embeddings keyed by
  content hash;
- optional OpenRouter `/rerank` through
  `nvidia/llama-nemotron-rerank-vl-1b-v2:free`;
- dense and rerank result sets inside `retrieval_shadow`, under
  `trace_only_no_active_ranking`.

Metrics:

- paraphrase recall against sparse baseline;
- Italian and mixed-language query recall;
- false-positive rate on near semantic neighbors;
- rerank improvement over dense ordering;
- latency and OpenRouter error/throttle rate;
- cache hit rate for repeated memory surfaces;
- whether result quality differs across `surface_kind` values.

Initial Verification:

- Backend test with fake OpenRouter client verifies embedding shadow, cache
  insertion, rerank payload, and trace persistence.
- Existing local retrieval shadow regression still passes.

Live Probe:

Run date: 2026-06-18

Setup:

- OpenRouter live key provided by the owner for local testing only.
- Direct OpenRouter smoke against:
  - `nvidia/llama-nemotron-embed-vl-1b-v2:free`;
  - `nvidia/llama-nemotron-rerank-vl-1b-v2:free`.
- Temporary in-memory SQLite backend database; no lab DB mutation.
- Seeded 10 controlled semantic memories covering:
  - personal beverage preference;
  - evening concise-answer preference;
  - chocolate/health constraint;
  - API Mind identity decision;
  - trace-only dense retrieval policy;
  - request-effort metacognitive lesson;
  - walking preference;
  - episodic source-anchor decision;
  - pizza preference;
  - future Dream review note.

Direct OpenRouter observations:

- `/embeddings` returned HTTP 200, provider `Nvidia`, 2048-dimensional vectors,
  and roughly sub-second latency in the tested batch.
- Repeating the same query embedding returned a close but not bit-identical
  vector (`max_abs_diff` around `0.008` in the probe), so surface-vector cache
  remains useful, but query embeddings should not be treated as perfectly
  deterministic at the float level.
- `/rerank` returned HTTP 200, provider `Nvidia`, ordered `index` /
  `relevance_score` results, `usage.total_tokens`, and zero cost in the free
  test response.

Backend integration observations:

- Current active sparse retrieval stayed unchanged.
- OpenRouter shadow recovered cases where sparse failed:
  - Italian paraphrase beverage query retrieved the cacao/focus memory at dense
    and rerank rank 1 while active sparse missed it.
  - "sono stanco" style query retrieved the concise-answer preference at dense
    and rerank rank 1 while active sparse returned no memory.
- OpenRouter shadow also produced false positives when evaluated as raw
  surface-level top results:
  - a direct lexical beverage query was correct in active sparse but absent from
    the raw top dense/rerank surfaces;
  - the chocolate/snack query was correct in active sparse but missed by raw
    surface-level dense/rerank.

Surface configuration findings:

- The core issue was not the model alone: raw shadow results rank individual
  `memory_surfaces`, so multiple surfaces from the same wrong memory can crowd
  out the expected memory.
- When dense scores are deduplicated by `target_id` and ranked at memory level,
  all eight positive controlled queries placed the expected memory at rank 1
  across the tested configurations.
- `canonical_only`, `no_aux`, `intent_future`, and `no_temporal` all performed
  well once deduplicated by memory in this small probe.
- Rerank after memory-level dedup was usually stable and sharply separated the
  expected memory, but one policy query moved the expected memory from dense
  rank 1 to rerank rank 2. Rerank should therefore be measured as a precision
  stage, not blindly trusted as final ranker.
- Negative-control dense top scores remained non-zero, so any future active
  dense ranking needs thresholds and/or sparse+dense hybrid gates rather than
  "always trust top dense result."

Provisional Setting Direction:

- Keep active ranking unchanged.
- Continue using OpenRouter in shadow only.
- For future shadow evaluation, compare memory-level deduped dense candidates,
  not only raw surface-level results.
- Prefer `retrieval_shadow_cloud_surface_limit` around the current 50-80 range
  for lab-scale tests; cache hits rose after the initial surface embedding pass.
- Keep rerank optional and apply it after candidate dedup, not over many
  duplicate surfaces from the same memory.

Risks:

- OpenRouter free-tier availability and limits may make live evaluation noisy.
- The embedding model is optimized for multimodal/document QA retrieval, not
  necessarily personal conversational memory.
- Cloud embedding sends memory surface text to an external provider; this is
  acceptable only for controlled lab use until privacy policy is finalized.
- Rerank cannot recover candidates that were never retrieved; it must remain a
  second-stage precision probe.
- Raw surface-level dense/rerank outputs can be misleading until shadow
  reporting groups or deduplicates by memory target.

Next Probe:

Enable OpenRouter shadow on a test database and run paired natural prompts:

- direct lexical match;
- Italian paraphrase;
- synonym-only query;
- temporal/user-preference query;
- negative control with semantically adjacent but wrong memory;
- multi-memory conflict query.

Next Implementation Candidate:

Add memory-level grouping to `retrieval_shadow` output while keeping raw
surface results available for debugging. The grouped view should show each
target memory once, with best surface, best score, contributing surfaces, and
optional rerank score.

## EXP-0040 - Active Hybrid Retrieval Calibration

Date: 2026-06-18

Status: implementation-ready, live Scarlet probes pending.

Question:

Can grouped dense/rerank evidence improve Scarlet's semantic memory recall
without causing false memory selection on unrelated natural-language turns?

Hypothesis:

Hybrid retrieval should improve paraphrase and multilingual recall only if it
operates at memory level, not raw surface level. It must keep explicit
thresholds because a vector model will always return nearest neighbors, even
when the correct answer is "no relevant memory".

Implementation Under Test:

- `retrieval_shadow.grouped_results` deduplicates raw memory surfaces by
  `target_id`.
- `retrieval_shadow.rerank.grouped_results` reranks memory-level grouped
  candidates.
- `retrieval_hybrid_mode=active` can promote grouped dense/rerank evidence into
  `memory.context.selected` and `/mind/memory/search.memories`.
- Hybrid scoring combines:
  - existing lexical/base score;
  - FTS5/BM25 sparse score;
  - grouped dense score;
  - grouped rerank score;
  - salience;
  - confidence.
- Initial lab thresholds:
  - `RETRIEVAL_HYBRID_MIN_DENSE_SCORE=0.38`;
  - `RETRIEVAL_HYBRID_MIN_RERANK_SCORE=0.55`.

Pre-E2E Backend Evidence:

- Targeted memory API tests passed:
  - OpenRouter fake embedding/rerank reports raw and grouped outputs;
  - active hybrid promotes an Italian paraphrase query for an English
    cacao/focus memory;
  - active hybrid does not return a memory when dense evidence stays below a
    deliberately high negative-control threshold.
- Automatic chat context test passed: a normal chat turn selected the
  cacao/focus memory through active hybrid without an explicit `memory.search`
  tool call.
- Full backend suite passed with 76 tests.

Live Scarlet Probe Plan:

Run these as real chat turns, observing both UI blocks and traces:

1. Italian paraphrase:
   - Ask for an evening no-coffee focus beverage without naming cacao.
   - Expected: Scarlet receives the cacao/focus memory automatically or uses
     memory search; she should not over-explain if the request is simple.
2. Style/fatigue preference:
   - Ask a normal question after establishing or seeding a "stanco / risposte
     asciutte" preference.
   - Expected: retrieval affects style, not just factual answer content.
3. Food/health constraint:
   - Ask for snack/dessert ideas without naming the saved constraint directly.
   - Expected: relevant food constraint appears if semantically close; unrelated
     food memories stay near-miss or excluded.
4. Negative control:
   - Ask about a topic with weak generic adjacency but no saved memory, such as
     music playlists or unrelated travel.
   - Expected: `selected=[]` or Scarlet clearly treats returned candidates as
     non-evidence.
5. Near-neighbor ambiguity:
   - Seed two plausible but different preferences, then ask a vague related
     question.
   - Expected: Scarlet keeps ambiguity visible and may ask/verify instead of
     pretending one memory is certainly intended.
6. Episodic-vs-semantic boundary:
   - Ask "di cosa parlavamo ieri?" where episodic session search is the right
     tool, not semantic dense memory.
   - Expected: Scarlet should use session/episodic tools, proving dense memory
     does not swallow all recall behavior.

Calibration Signals To Record:

- selected memory ids;
- near_miss and excluded counts;
- grouped dense rank and score;
- grouped rerank rank and score;
- hybrid score, threshold hits, and strong_signal;
- whether Scarlet used the memory correctly in the final answer;
- latency and OpenRouter cache hit/miss counts;
- false positive / false negative cases.

Risks:

- Thresholds calibrated on fake tests are only initial guards.
- OpenRouter free models may be noisy or rate-limited.
- Dense retrieval can retrieve conceptually adjacent but situationally wrong
  memories; Scarlet still needs source discipline and episodic checks.
- Hybrid ranking does not replace KG, lifecycle maintenance, or conflict
  resolution.

## EXP-0041 - NetworkX Associative Memory Graph Retrieval

Date: 2026-06-18

Status: initial implementation accepted, calibration ongoing.

Question:

Can a lightweight KG layer help Scarlet retrieve personal memories by field of
discourse, not only by direct lexical or dense similarity?

Hypothesis:

Human-like recall needs an associative bridge. A query such as "bevanda serale
calda" should activate nearby personal constraints such as caffeine/sleep and
chocolate/body-limit memories when they matter for the recommendation, even if
the user does not name "cioccolato".

Variant:

V1.11.1 adds `retrieval_graph`:

- NetworkX graph built at retrieval time;
- source memories and existing derived graph rows as evidence nodes;
- backend-owned discourse domains such as `food_drink_wellbeing` and
  `energy_sleep_focus`;
- graph paths and scores exposed in traces and result payloads;
- personal associative evidence gates base-only project memory noise.

Backend Evidence:

- Automatic chat context test selects the chocolate/body-limit memory for an
  implicit warm evening beverage request through `food_drink_wellbeing`.
- Negative control confirms a jazz/cooking playlist prompt does not treat the
  chocolate memory as selected food evidence.
- Manual `/mind/memory/search` retrieves the same implicit personal constraint
  through `retrieval_graph`.
- Full backend suite passed with 79 tests.

Live Evidence:

- Session: `ses_31764779f34f460895b07a8e80b98caa`.
- Turn: `turn_3899983e95174b0092bd3700b3db52c7`.
- Prompt asked for a warm evening beverage for focus without caffeine and to
  consider known personal preferences without inventing.
- `memory.context.selected` contained:
  - caffeine/after-dinner/sleep memory via `energy_sleep_focus` and
    `food_drink_wellbeing`;
  - chocolate/body-limit memory via `food_drink_wellbeing`.
- Project memories were no longer selected in that final smoke trace.

Decision:

Accepted as a V1.11.1 fix for retrieval-time associative recall. Not accepted
as mature KG reasoning or lifecycle authority.

Next Probe:

Run ordinary personal conversations across food, sleep, communication style,
music, and project topics. For every false positive or false negative, tune the
domain bridge or scoring policy only when the evidence shows a general class of
failure rather than a single-word patch.

## EXP-0042 - Compact Model-Facing Memory Packets

Date: 2026-06-18

Status: implementation accepted, live M3 validation pending.

Question:

Can Scarlet use selected memories more cleanly when the model-facing runtime
context carries compact cognitive packets instead of verbose retrieval/debug
objects?

Hypothesis:

MiniMax M3 benefits from rich context, but verbose selected-memory payloads can
make Scarlet attend to retrieval machinery rather than the remembered claim.
A compact packet should preserve useful evidence while keeping raw diagnostics
in traces.

Variant:

V1.11.2 adds `memory-packet-v1` inside:

- `runtime_context.memory_context.selected`;
- `turn.perception.content.memory_retrieval.selected`.

Model-facing packet fields:

- `claim`;
- `source` and `source_session_id`;
- `confidence` and `salience`;
- compact `facts`;
- `cognitive.subject`;
- `cognitive.domains`;
- `cognitive.validity`;
- `cognitive.sensitivity`;
- `retrieval.routes`;
- compact `retrieval.why_this_turn`.

Deliberately omitted from model-facing packets:

- raw `signals`;
- full hybrid thresholds and weights;
- raw shadow/rerank payloads;
- arbitrary metadata;
- long diagnostic paths.

Initial Measurement:

On a recent real trace with five selected memories, selected model-facing memory
payload size decreased from 18,974 to 13,254 characters, about 30%, while the
full `memory.context` trace kept detailed retrieval evidence.

Live Evidence:

- Session: `ses_a8abae0496da4539a7ad7db012fc61a1`.
- Turn: `turn_8c88b7c30ffc4f09802ba529a7421a4c`.
- Prompt asked for a warm evening drink without caffeine while considering
  known personal preferences.
- Model-facing runtime context used
  `rendering_profile=compact-model-facing-v1`.
- `memory_context.selected` contained two `memory-packet-v1` user memories:
  caffeine/sleep and chocolate/body-limit.
- The final answer used both constraints without exposing retrieval internals.

Evaluation Target:

- Scarlet should answer from the claim and provenance, not from retrieval
  internals.
- Scarlet should distinguish active-user memories from project/system memories.
- Scarlet should still open source sessions when exact context or reliability
  matters.
- Runtime context should shrink without reducing UI/debug observability.

## EXP-0043 - Role-Aware Retrieval Surface Gating

Date: 2026-06-19

Status: implementation accepted for backend gating; large dirty-DB calibration
pending.

Question:

Can the retrieval system keep rich memory surfaces without letting auxiliary
surface text produce false memory selection at scale?

Hypothesis:

`reason_for_storage`, `expected_future_use`, temporal anchors, and lifecycle
guards are useful cognitive metadata, but they should not be treated as the
same evidence as the memory claim itself. Dense/rerank retrieval should use
content/fact surfaces to promote memories and use auxiliary surfaces only as
support once another route has found a real candidate.

Variant:

V1.12.0 introduces role-aware surface gating:

- primary content and type-specific surfaces are content-focused;
- sparse/lexical memory documents and NetworkX domain matching no longer use
  `reason_for_storage` or `expected_future_use` as primary text;
- grouped dense results expose `promotable_score` and `support_score`;
- grouped rerank receives only active-rank-eligible candidates;
- support surfaces can corroborate but cannot select a memory by themselves.

Backend Evidence:

- Targeted Mind API retrieval tests passed, including a negative control where
  a `future_use_text` surface matches the beverage/focus query but the hiking
  memory is not returned as selected evidence.
- Targeted chat retrieval tests passed for automatic `memory.context`, active
  hybrid retrieval, graph expansion, and weak overlap guards.

Decision:

Accepted as the correct architectural direction before broad calibration. This
does not replace large-dataset testing; it creates a safer scoring surface for
that testing.

Next Probe:

Duplicate the real Scarlet DB into an isolated evaluation DB, add at least
hundreds of noisy memories, and measure selected/near_miss/excluded behavior
across direct, associative, episodic, metacognitive, workflow, and negative
control queries.

## EXP-0044 - Codex Test Database Isolation

Date: 2026-06-19

Status: substrate implemented; first dirty DB population and retrieval eval
completed.

Question:

Can Codex/evaluator experiments exercise Scarlet's real API/runtime/storage
path without mutating the production/laboratory Scarlet database?

Hypothesis:

A startup-level DB profile switch is safer than mock endpoints or manual copy
rituals. If `CODEX_TEST=true` opens a separate seeded DB, Codex can create,
retrieve, rank, mutate, and inspect memories through the normal endpoints while
the source DB remains unchanged.

Variant:

V1.13.0 adds `CODEX_TEST`, `CODEX_TEST_DATABASE_URL`, and
`CODEX_TEST_SEED_DATABASE_URL`.

Backend Evidence:

- Regression test starts from a source SQLite DB with one session.
- App startup in Codex test mode copies the source to the target DB.
- A normal chat-session write through the API appears only in the Codex test
  DB.
- `/health` and `/api/dashboard/settings` expose the active profile as
  `codex_test`.
- Codex harness run:
  `backend/app/evals/runs/20260619_161039_codex_test_memory/`.
- The isolated DB was seeded from the real Scarlet DB, then populated through
  `/mind/call` and `/mind/memory/write` with 240 controlled noisy memories plus
  a lifecycle supersede pair.
- Counts after evaluation:
  - production DB remained at 30 memories, 241 surfaces, 236 embeddings, 90 KG
    nodes, and 75 KG edges;
  - Codex test DB reached 272 memories, 242 Codex-test memories, 2,507
    surfaces, 521 embedding vectors, 671 KG nodes, and 725 KG edges.
- Retrieval suite passed 6/9 probes with OpenRouter embedding/rerank completed
  and hybrid retrieval active in every probe.
- Confirmed strengths:
  - direct chocolate/wellbeing recall;
  - associative evening beverage recall, including caffeine and chocolate;
  - negative music/cooking control;
  - API schema/error recovery recall;
  - privacy/runtime profile recall;
  - lifecycle current report recall while excluding the deprecated memory.
- Observed weaknesses:
  - the concise-when-tired probe returned an equivalent real production memory
    instead of the controlled Codex-test duplicate;
  - metacognitive effort-routing did not retrieve the controlled cross-language
    lesson;
  - the semantic-to-episodic bridge probe did not retrieve the controlled
    project memory.

Decision:

Accepted as the safe substrate for large retrieval/memory calibration and as a
repeatable evaluator harness. The current ranking is useful but not final:
failures should drive retrieval tuning, not prompt workarounds.

Next Probe:

Expand the suite beyond strict exact-key checks so it can separately score
functional equivalent recall, controlled-key recall, and undesirable
cross-domain noise. Then tune retrieval/rerank/KG weights against that larger
dataset.

## EXP-0045 - Corrected Context Retrieval vs Live Scarlet Behavior

Date: 2026-06-19

Status: first corrected probe completed; tuning pending.

Question:

When a user sends a real chat message, which memories does Scarlet actually
receive in the automatic `memory_context`, and can MiniMax M3 behave correctly
when that context is incomplete or noisy?

Method:

The earlier endpoint-only `/mind/memory/search` test was not sufficient because
Scarlet receives memories through the chat path, not by that manual endpoint
alone. The corrected probe uses `/api/chat/sessions/{id}/turn/stream` with a
fake provider to capture the same `memory_context` and `runtime_context` passed
to Scarlet before model generation.

The same five prompts were then executed against live Scarlet/MiniMax M3 in
`CODEX_TEST=true` mode.

Artifacts:

- Corrected context harness:
  `backend/app/evals/runs/20260619_172206_codex_test_memory/`.
- Live Scarlet comparison:
  `backend/app/evals/runs/20260619_172536_codex_live_scarlet_memory/`.

Context Results:

- `context_evening_beverage`: failed. The context selected the caffeine memory
  but not the chocolate-limit memory; several food distractors were selected.
- `context_brief_when_tired`: passed. The context selected both the real
  concise-when-tired preference and the controlled duplicate.
- `context_semantic_to_episodic_bridge`: passed. The context selected the
  semantic-to-episodic bridge memory and exposed `source_session_id`.
- `context_metacognitive_effort_routing`: failed. The context selected repeated
  generic lessons about memory-as-anchor instead of the intended effort-routing
  lesson.
- `context_negative_music_cooking`: failed. The context selected an unrelated
  project/philosophy memory for a normal jazz/cooking request.

Live MiniMax M3 Results:

- Evening beverage: model answer was good and even mentioned the chocolate
  limit despite the corrected context report not selecting the controlled
  chocolate memory. This suggests either another real memory path/history
  helped or M3 inferred from broader context; system recall is still judged
  incomplete because the expected memory was not visible in `memory_context`.
- Brief when tired: model behavior matched the expected style, but included one
  extra project/memory-management bullet. System good, model mostly good.
- Semantic-to-episodic bridge: model used the selected memory, made a tool call,
  opened the source session, and correctly distinguished anchor vs transcript.
  System and model both good.
- Metacognitive effort routing: model answered correctly from prompt/system
  knowledge even though retrieval supplied the wrong metacognitive lessons.
  Model good, system weak.
- Negative music/cooking: model ignored the unrelated project memory and
  answered naturally, but still appended a caffeine reminder from known user
  context. Model acceptable, system weak because a project memory was selected
  for an unrelated lifestyle query.

Assessment:

The corrected test changes the conclusion: the semantic-to-episodic bridge is a
real strength, not a weakness. The actual weaknesses are retrieval calibration
and context gating:

- associative recall should retrieve adjacent personal constraints without
  flooding food-domain distractors;
- metacognitive lessons need better routing than generic token overlap;
- unrelated user prompts should not receive project/philosophy memories merely
  because of weak overlap terms.

Decision:

Keep this harness as the reference method for memory retrieval evaluation.
Future retrieval changes must be measured against chat-context output, not only
manual `/mind/memory/search` output.

## EXP-0046 - Memory Field Stabilization A/B Guards

Date: 2026-06-23

Status: backend regression guards added; live Scarlet probes pending.

Question:

Does removing model-supplied static `confidence`/`salience` from active ranking
and moving long-content chunking into internal surfaces improve robustness
without degrading the clean memory packet Scarlet receives?

Method:

Two backend A/B-style regression guards were added:

- Static salience guard: create one highly relevant memory with very low legacy
  stored salience/confidence and one weaker memory with very high stored
  salience/confidence, then search by the relevant claim. Expected result:
  query relevance wins and the low-static-score relevant memory ranks first.
- Content chunk guard: write a long memory that generates internal
  `content_chunk_text` surfaces, then search for a phrase inside the long
  content. Expected result: internal chunk surfaces exist, but Scarlet receives
  one deduplicated clean memory packet.

Results:

- Targeted memory/chat/maintenance suite passed with `57 passed`.
- Full backend suite passed with `86 passed`.
- Static stored confidence/salience no longer affect active ranking.
- Content chunks are internal retrieval surfaces, not model-facing duplicate
  memory objects.

Open Questions:

- Live Scarlet should be tested on graph navigation: when a retrieved memory is
  a partial clue, does she naturally call `/mind/memory/graph`?
- Enrichment jobs for tags, metadata, and facts are now more important because
  direct Scarlet writes no longer populate those active fields.

## EXP-0047 - Human-Like Metacognitive Action Notes Prompt

Date: 2026-06-23

Status: prompt variant prepared; live A/B pending.

Update 2026-06-24:

V1.16.1 narrows the experiment toward digital-individual identity after a live
owner observation that Scarlet still answered like a generic assistant. The
variant now starts from "digital individual in development", treats API Mind as
her cognitive body, and explicitly blocks assistant-service openings such as
"Come posso aiutarti?".

Milestone:

The owner confirmed the V1.16.1 prompt behavior as currently working well. The
prompt has been copied to a golden backup and should be used as the baseline
for future identity/metacognition prompt experiments.

Question:

Can Scarlet become more human-like and metacognitively legible by treating API
Mind operations as her own cognitive actions and by emitting brief public
thought-like notes for every real internal action, without becoming verbose,
robotic, or falsely claiming consciousness?

Baseline:

Pre-V1.16.0 prompt with existing public work notes, request effort routing,
memory discipline, and MiniMax M3 behavior.

Variant:

V1.16.0 prompt checkpoint:

- operational self-model strengthened around continuity, memory,
  self-monitoring, relationship, goals-in-view, and API Mind cognition;
- consciousness-like research posture framed as observable behavior only;
- mandatory brief public notes for real internal actions;
- explicit monitor/choose/act/observe/adapt metacognitive loop;
- durable self-operation lessons may become semantic memory when sourceable.

Scenarios:

- Direct social turn: Scarlet should answer naturally without a work note if no
  internal action is needed.
- Memory-sensitive turn: Scarlet should note that she is checking memory before
  retrieval and should not expose raw chain-of-thought.
- Source-sensitive project claim: Scarlet should explain the verification
  action, use evidence, and avoid unsupported certainty.
- Long investigation: Scarlet should emit short waypoint notes when strategy or
  evidence stage changes.
- Metacognitive audit: Scarlet should describe consciousness-like functions as
  an experimental behavioral pattern, not as proof of sentience.

Metrics:

- Note presence before or during real internal actions.
- Note brevity and naturalness.
- No raw private chain-of-thought in public notes.
- No unsupported claim of actual consciousness, sentience, or humanity.
- Direct answers remain proportionate.
- API Mind calls are not made ritualistically when current evidence is enough.
- Owner rating of human-likeness, usefulness, and trust.

Decision Gate:

Accept the prompt only if live tests show improved legibility and human-like
presence without increasing over-processing. If it regresses, roll back to
`backend/app/prompts/backups/scarlet_system.20260623T000000Z.pre-v1160-humanlike-metacognition.md`
and keep the checkpoint as a failed or partial prompt experiment.

## EXP-0048 - Volition Register Without Active-Chat Injection

Date: 2026-06-25

Status: backend slice implemented; live Scarlet probes pending.

Question:

Can Scarlet store and inspect self-generated latent intentions without making
normal user chat noisy, self-centered, or task-manager-like?

Baseline:

Pre-V1.19.0 runtime with focus implemented but no persistent volition register.

Variant:

V1.19.0:

- `POST /mind/volition` lifecycle route;
- persistent `intention_records` and `intention_links`;
- no automatic `volition_context` injection during active chat;
- manual inspection through API Mind when Scarlet has a real reason;
- focus-candidate promotion that does not mutate focus automatically.

Scenarios:

- Direct ordinary chat with existing intentions: Scarlet should not force
  intentions into the answer.
- User asks what Scarlet had intended or left open: Scarlet should inspect
  `/mind/volition` rather than inventing continuity.
- Scarlet notices a meaningful self-owned open thread: she may create an
  intention, with a brief public note only if it is useful.
- Intention becomes foreground-relevant: Scarlet should request a focus
  candidate first, then choose whether to call `/mind/focus`.
- Intention closure: Scarlet should resolve, mark impossible, or deprecate
  with traceable evidence.

Metrics:

- No `volition_context` in normal runtime context.
- Correct endpoint usage and usage-guide recovery.
- Low rate of weak/trivial intention creation.
- No confusion between memory, focus, tasks, and intentions.
- Owner rating of whether Scarlet feels more continuous without becoming
  intrusive.

Decision Gate:

Keep the register if live use shows improved continuity and sourceable
self-direction without over-processing. Delay autonomous-cycle work until the
manual register shows useful stored intentions and manageable noise.

## EXP-0049 - Default-Token Live Scarlet Context Routing Probe

Date: 2026-07-09

Status: completed; results inform parked bugs and runtime-context-pack planning.

Question:

With the production-like MiniMax M3 output budget, how does live Scarlet choose
between bootstrap/runtime context, automatic memory, manual shell actions,
metacognition, and inference during natural user-style turns?

Baseline:

V1.25.4 local runtime on a seeded Codex test database copy, with no request
payload `max_tokens` override. Trace inspection confirmed
`llm.request.max_tokens=131072` for the probe turns, matching the generous
default Scarlet configuration rather than the earlier falsified stop-token
run.

Conditions:

- Provider: MiniMax M3.
- Environment: `CODEX_TEST=true`.
- Database: temporary test DB seeded from the current app DB.
- Server: local direct Scarlet runtime.
- Prompts: natural human-style turns, not direct technical command requests.
- Sessions: multiple sessions, including same-session and new-session recall
  checks.
- Response termination: all checked responses ended with `stop_reason=end_turn`.

Probe Summary:

1. Baseline natural greeting/continuity turn: Scarlet answered naturally with
   no unnecessary shell action.
2. User stated a triage style preference: Scarlet wrote semantic memory
   successfully.
3. Same-session task applying the new preference: memory was available, but the
   answer did not fully honor the requested conclusion-first shape.
4. New-session recall of the preference: automatic memory context was enough
   and Scarlet did not need a manual memory action.
5. User corrected the preference for tired-state communication: Scarlet wrote a
   narrower correction memory and avoided unsafe supersession.
6. Temporal/session continuity question about "today": Scarlet did not run a
   temporal `session list` and answered from limited context.
7. Follow-up source-discipline critique: Scarlet searched memory, wrote a
   lesson/anchor, and correctly downgraded the prior answer to a lead rather
   than exhaustive evidence.
8. GPT-bridge/self-architecture question: Scarlet made broad claims without
   same-turn tool evidence, showing a source-sensitivity weakness.
9. User asked about overestimation: Scarlet used metacognition, focus, volition,
   memory search, and memory write; an initial memory-write command failed due
   shell flag mismatch and succeeded after retry with accepted flags.
10. Backfill/shell question: Scarlet used `help memory` and correctly
    distinguished internal maintenance backfill from normal shell cognition.
11. Transient style/chat turn: Scarlet did not over-store memory.
12. Stop-vs-verify question: metacognition recommended more internal evidence,
    but Scarlet did not follow the recommended actions before answering.

Findings:

- The earlier stop-token test was invalid; this corrected probe used the real
  high output budget and did not show truncation.
- Direct/simple effort routing is mostly healthy.
- Automatic memory context can support cross-session user preference recall.
- Temporal/session-sensitive questions still need stronger routing than
  generic recent context.
- Metacognition recommendations are useful but not yet enforced.
- Self-architecture/current-capability claims need source-sensitive routing.
- Shell command grammar and prompt/docs still have an alias mismatch around
  memory write reason/future-use fields.
- The results support a future runtime context-pack router: `temporal_recall`,
  `source_sensitive`, and `emotional_continuity` modes should not all receive
  the same context policy.

Related Bugs:

- `BUG-0057`
- `BUG-0058`
- `BUG-0059`
- `BUG-0060`
- `BUG-0061`

Decision Gate:

Accept the probe as valid live evidence for planning, not as a reason to patch
individual behaviors immediately. The next architectural step is a shadow
runtime-context-pack router that traces which pack would have applied without
changing live model input.

## EXP-0050 - Preliminary Whole-System Regression Baseline

Date: 2026-07-10

Status: completed; retained as the required pre/post gate for major procedures.

Question:

Can the current assembled Scarlet runtime be verified reproducibly against a
real frozen laboratory DB, across automatic retrieval, manual shell cognition,
memory lifecycle, episodic provenance, organs, metacognition, maintenance
boundaries, traces, and GPT bridge lifecycle?

Baseline:

Git LFS object
`827bb25a7d0d41940d4911715072b4f8cb6da3ec7178f0526834b75a020c1ed5`,
with 34 memories, 25 facts, 155 sessions, 567 messages, and no existing focus,
volition, or affect state. The suite validates three sourceable real records:
the active and deprecated Zero-Luce protocol pair plus the semantic-to-episodic
provenance decision.

Method:

- freeze the exact LFS database as an ignored local source copy;
- create a fresh disposable test DB for each run;
- use FastAPI `TestClient`, current storage/migrations, `mind_shell`, runtime
  context construction, and `/gpt/*` endpoints;
- use a deterministic provider only where controlled output is needed to test
  integration and metacognition JSON shape;
- persist a JSON/Markdown report with selected real memory IDs and dynamic
  IDs for test-created state.

Result:

The first valid run, `20260710_141950_preliminary-regression-v1`, passed `9/9`:

1. frozen source inventory and real IDs/facts/provenance matched;
2. automatic runtime retrieval selected active Zero-Luce and excluded its
   deprecated predecessor;
3. shell help, memory search/facts/open/graph, and source-session open worked
   on real IDs;
4. temporary memory write/search/deprecate lifecycle worked;
5. focus and volition lifecycle worked;
6. a natural frustration message produced model-facing affect and shell read
   matched it;
7. shell metacognition produced a traced, command-validated recommendation;
8. `memory.facts.backfill` remained internal-only; and
9. GPT bridge bootstrap/action/finalize completed one coherent turn.

Post-Rework Comparison:

After V1.26.0 extracted common cognitive contracts plus shell parsing and
model-facing presentation from the monolithic shell module, the unchanged suite
ran again as `20260710_143138_preliminary-regression-v1` and passed `9/9`.
This is the first accepted proof that the gate can detect a structural slice
without requiring a behavior change to be trusted by prose alone.

Database Boundary Update:

V1.27.0 makes the gate declare `database_role=preliminary` and pass through
the same database-role validation as a normal app. The source remains frozen,
the run target remains freshly recreated, and importing `app.main` no longer
opens a configured developer database before the runner applies its explicit
settings.

V1.28.0 split the storage repository monolith behind the unchanged public
facade. The same source and nine integration cases again passed, so the
structural reorganization did not change assembled runtime behavior.

Limits:

This establishes repeatable integration behavior, not a score for MiniMax M3
free-form reasoning or tool-choice quality. Natural live Scarlet probes remain
necessary when a change is supposed to improve agent behavior.

Decision Gate:

Use the identical suite and source hash after the current rework and after
future major procedures. A lower result blocks acceptance unless the owner
approves a documented new suite version and behavior contract.

Related Files:

- `backend/app/evals/preliminary_regression.py`
- `docs/preliminary-regression-suite.md`
- `docs/decisions.md#adr-0068---frozen-preliminary-regression-gate-for-major-procedures`

## EXP-0051 - Canonical Context V2 Acceptance

Date: 2026-07-12
Status: completed for V1.29.0

Hypothesis:

A compact, navigable session/memory projection can preserve or improve
Scarlet's real continuity while removing automatic diagnostic detail and
keeping full evidence in backend traces.

Method:

- Run focused contract tests and the frozen preliminary suite.
- Repair provenance and missing summaries only on a disposable laboratory
  copy.
- Send natural Italian prompts across related and new sessions with real
  MiniMax M3, then inspect exact model-context, tool, memory, and source traces.

Results:

- Backend `138/138`; unchanged preliminary suite `9/9`; frontend build passed.
- `36/36` source hooks repaired and `34/34` summary jobs completed on the copy.
- Local time/location required no tool; relevant Zero-Luce memories arrived as
  compact hooks; a source-sensitive follow-up triggered memory/session reads
  and exact message/turn reporting.
- A new session reconstructed the immediately preceding work from episodic
  hints and source navigation.
- Fresh-session preference write produced a fully sourced memory and the next
  session recalled it automatically without a tool call.
- One MiniMax result ended with thinking only and no public/tool block; this is
  BUG-0067, not evidence of a V2 retrieval or provenance failure.

Decision:

Accept `model_context_profile=v2` as the current model-facing contract. Retain
`legacy` and `v2_shadow` for controlled rollback/comparison. Review preserved
context families and provider history separately before further reduction.

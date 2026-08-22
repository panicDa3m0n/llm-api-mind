# Context Runtime Verification Notes

Date: 2026-07-28 (updated 2026-07-29)
Branch: `feature/core-convergence-kernels`
Work type: verification only
Target runtime: V1.65.0 deployed
Status: working review, non-normative

## Purpose

This checkpoint records code-and-trace evidence gathered while reviewing
automatic model context and `mind_shell` before any new design or fix. It is
not a replacement for `docs/runtime-context-packs.md`, the V2 context contract,
or an accepted decision.

## Session Context Findings

### F-01 - Historical missing/stale summaries are not currently repaired in production

Evidence:

- The normal completion path schedules idle maintenance after
  `maintenance_idle_seconds=900`; the deployed setting is 900 seconds.
- The V2 session projection uses explicit missing/stale navigation text rather
  than manufacturing a summary.
- The deployed setting `summary_reconcile_enabled=false` disables the separate
  historical summary-repair queue.
- A real stored autonomous V2 context contains one previous human session with
  the explicit missing-summary fallback.

Implication:

New completed turns retain the intended 15-minute idle path. Existing sessions
without a summary are not brought into alignment merely by the worker. Decide
whether a bounded, idle-safe historical repair should exist and under what
trigger; do not enable the current reconciler blindly.

Risk if revisited:

The current optional reconciler queues missing/stale repair immediately when
enabled. That differs from the intended idle-first summary policy and requires
redesign before activation.

### F-02 - Autonomous context duplicates the current autonomous session

Evidence:

- `project_session_context()` always projects the one autonomous-session hint.
- During an autonomous turn, `session.current_session.id` and
  `session.autonomous_session.id` are the same value.
- The stored V2 trace confirms this duplication. The second object adds a
  checkpoint and activity metadata, but repeats session identity.

Implication:

The autonomous hint is useful during a human turn. During an autonomous turn,
its cognitive value versus provider-history and current-session redundancy must
be decided before changing the V2 contract.

### Verified Production Human V2 Sample

- A post-review human `model.context` trace was observed at
  `2026-07-28 21:54:25`.
- It carries the active `interactive` runtime mode and the same dedicated V2
  orientation surface as the autonomous path. Its rich `message_context` is
  present before V2 projection; autonomous `idle` correctly excludes that
  legacy-rich block while retaining the common V2 orientation contract.

The direct production comparison is therefore available. Any remaining work is
about intentionally different source content and mode routing, not missing
human V2 evidence.

## Review Sequence

1. Session context selection and summary state: reviewed.
2. Automatic memory blocks (`relevant`, `recent_user`, `recent_general`): reviewed.
3. Conditional organ context and mode routing: reviewed.
4. Complete `mind_shell` command audit: reviewed.

## Automatic Memory Findings

### F-03 - Automatic recency is recorded before V2 delivery is known

Evidence:

- `build_memory_context()` stores an `automatic_reranked_context` activity for
  every final-reranker-selected memory before `compile_model_context_v2_with_audit()`
  projects the compact memory blocks.
- The V2 projector correctly rejects a memory when the stored source message
  does not agree with its source session and turn.
- Production evidence links the same turn across traces: several inconsistent
  memories were selected in `memory.context`, recorded with eligible automatic
  activity, then omitted from every V2 memory block. The resulting `relevant`
  block contained fewer than its configured five hints.

Implication:

This violates the agreed semantics for recent memory: an automatic rerank may
refresh recency only when that memory actually enters Scarlet's model context.
The current order can also keep an unusable record artificially recent.

### E-07 - Memory delivery has no first-class projection receipt

Evidence:

- `compile_model_context_v2_with_audit()` returns the final document, but its
  audit is currently about preserved families and mode routing; it does not
  report selected memory ids, delivered memory ids, or projection omissions
  with their reasons.
- `test_model_context_v2.py` proves compact projection and block-level
  deduplication. `test_model_facing_memory_gate.py` can distinguish synthetic
  rich-selection and model-delivery evidence. Neither test runs the actual
  context builder and proves that `automatic_reranked_context` is recorded
  only for ids in the final V2 document.

Implication:

The exact `model.context` document remains enough to reconstruct delivery by
inspection, but not to provide an explicit runtime receipt to the activity
writer or a focused regression contract. This is an observability and test
gap; F-03 is the actual ordering defect.

### E-08 - Autonomous retrieval uses a different evidence window, not a different retriever

Evidence:

- Both human and autonomous turns call `prepare_model_turn()` and the same
  `build_memory_context()` / `build_automatic_memory_retrieval()` path.
- A human turn uses its persisted user message plus up to the recent visible
  dialogue of that same session.
- An autonomous turn uses its internal activation envelope as the current
  message and supplies a source-labelled dialogue window made from the last
  four visible messages of each of the two latest human sessions plus the last
  six autonomous assistant messages, truncated to the newest eight items.

Implication:

This is not a duplicated memory contract and it gives internal cognition the
human continuity requested for it. It is nevertheless a distinct retrieval
query composition: generic activation wording, workspace content when present,
and cross-session dialogue can alter recall relative to a human turn. The
choice needs an explicit behavioural contract and a direct evaluation before
it is treated as proven beneficial or blamed for repeated autonomous actions.

### F-04 - Six active production memories have internally inconsistent source provenance

Evidence:

- Read-only production audit found 84 active memories: none lack all source
  references, but six point to a source message whose stored turn differs from
  the memory's source turn.
- V2 fails closed and omits those records when it sees the inconsistency.
- At least four of the six were selected by automatic rerank after becoming
  inconsistent, which makes F-03 observable in live contexts.

Implication:

The fail-closed model projection protects Scarlet from false provenance, but
the historical records need a separately reviewed alignment path. Do not
blindly repair or deprecate them: the correct source turn must be established
from trace/session evidence.

### Verified Memory Behavior

- Production uses `retrieval_hybrid_mode=active`; the configured reranker is
  the final acceptance and ordering authority. Local lexical/graph scores only
  form a recall pool and diagnostic evidence.
- The V2 document keeps three deduplicated blocks: `relevant`, `recent_user`,
  and `recent_general`, each configured to five candidates.
- Manual search, direct read, facts, graph, successful write, and supersede
  operations write append-only eligible activity. Maintenance provenance repair
  and test-fixture deprecation explicitly do not.
- In the sampled current packets, delivered hints had complete provenance and
  the selected reranked IDs exactly matched `relevant` whenever every selected
  record was projectable.

### Verified Temporal Orientation

- `context_time.render_user_time()` is the single model-facing conversion
  boundary: persisted naive timestamps are interpreted as backend UTC and then
  rendered through the configured IANA timezone for the historical instant.
- `timezone_packet()` supplies one localized `now`, timezone id/name, current
  UTC offset, and the configured social-day boundary. It does not expose a
  competing model-facing UTC clock in V2.
- `social_date()` deterministically treats local times before `05:00` as the
  prior conversational day for time filters and related backend logic. The
  human phrasing of that relation (for example, "ieri sera" or "stanotte")
  remains Scarlet's semantic interpretation rather than a forced text rule.
- Focused regression covers both historical DST offsets and the 00:05/05:00
  social-day boundary.

## Conditional Organ And Mode Findings

### Verified Delivery Path

- There is one live block router: `agent_modes.route_context_blocks()`. The
  deployed setting is `agent_mode_routing=active`.
- A human turn resolves to active `interactive`; an autonomous turn resolves
  to the profile's preferred mode. The deployed profile has no persisted mode,
  so current autonomous turns resolve to the configured default `idle`.
- The V2 document always receives session, memory, local-time/location, user,
  and mode orientation through its dedicated projection. Optional
  `preserved_context` can contain only allowlisted focus, affect, or
  metacognitive blocks.
- Production has focus and affect `off` and metacognition `shadow`; sampled
  current V2 documents therefore have an empty `preserved_context`, as
  intended. This is not a missing packet.
- In autonomous `idle` turns the rich legacy `message_context` block is
  actively removed. The activation envelope is nevertheless present as the
  current user-role entry in provider history, while the compact V2 session
  still supplies operational orientation.

### F-05 - Two capabilities are registered as automatic blocks but have no block producer

Evidence:

- The live mode registry declares `autonomous_activation_context` and
  `perception_context` as implemented context-block types.
- No runtime producer builds either block type, and neither type appears in
  current runtime or V2 traces.
- Autonomous activation/workspace data instead reaches Scarlet through the
  activation envelope in provider history. Perception is available through
  cognitive-workspace candidate material when selected and through the manual
  `perception` shell family.

Implication:

There is no current direct automatic V2 packet for either capability. The
registry wording overstates the live packet surface and can mislead future
mode-routing work. The existing indirect paths should remain explicit rather
than being mistaken for a second automatic context delivery path.

### E-02 - Context-family routing is an audit registry, not a second live router

Evidence:

- `context_family_routing_plan()` hardcodes a shadow-only receipt and asserts
  that the current V2 document is unchanged.
- The live runtime router above applies active inclusion/exclusion before V2
  projection.
- Both receipts use routing terminology; a real trace can therefore contain
  `mode_routing=active` and a family audit with `routing_mode=shadow` without
  a delivery contradiction.

Implication:

No duplicate live packet is currently emitted. The naming and trace surfaces
are nevertheless easy to confuse, so any future activation of family routing
must either replace the live router or be clearly renamed and formally
composed with it.

### E-03 - Autonomous posture is currently manual, not trigger-selected

Evidence:

- The workspace and perception paths do not call the agent-mode setter.
- `scouting` is reachable through Scarlet's `mode set` command and is stored
  as a resumable preference; it is not selected automatically from a workspace
  candidate or incoming perception event.
- Production has no persisted agent-mode setting and all sampled autonomous
  turns were `idle`.

Implication:

This is an explicit current boundary, not evidence that routing is broken. It
must be revisited before interpreting `scouting` as an automatic perceptual or
exploratory runtime.

## Mind Shell Review - Infrastructure

### Verified Shell Boundary

- Native Scarlet receives one model-facing tool only:
  `mind_shell(command, intent)`.
- The native provider tool runner and the GPT bridge both create the same
  `MindShellRequest`, invoke `dispatch_mind_shell`, and persist a compatible
  `mind.tool_call` receipt. The GPT adapter remains a transport adapter; it
  does not introduce a second cognitive command language.
- The model-facing catalog is derived from `COMMAND_FAMILIES` in
  `command_registry.py`; `schema.py` imports that catalog rather than keeping
  a third command list.
- `dispatcher.py` still maps translated commands onto legacy `/mind/*`
  handlers. This is the documented internal compatibility boundary, not a
  second model-facing tool surface.

### F-06 - Shell catalog validation is not the sole execution gate

Evidence:

- `dispatch_mind_shell()` parses a command and immediately selects a
  hand-written family handler. It does not first require a successful
  `validate_shell_command()` result.
- The registry validator is used for help/catalog validation, metacognitive
  recommended-action checking, and the special unavailable memory actions.
  Each handler and then its domain body schema still independently validate
  the command's executable fields.
- The existing catalog test proves that examples are accepted by the registry;
  it does not execute every advertised example through every handler and
  internal domain operation.

Implication:

The runtime is currently protected by handler/domain validation, so this is
not evidence that invalid state changes can bypass validation. It is a real
maintenance seam: command availability, argument requirements, aliases, and
handler behavior can drift because the registry is not the single admission
gate. Any later refactor should make one parsed/validated command contract the
input to handlers, while preserving the internal dispatcher boundary.

## Mind Shell Review - Memory And Episodic Families

### Verified Behavior

- `memory search` uses the shared recall pipeline. In active mode, sparse,
  graph, and lexical material only form the candidate pool; the reranker
  decides final selected memory order. Every returned memory receives a
  traceable `manual_search` activity.
- `memory open`, `graph`, and `facts` preserve provenance and write their
  respective manual activity where an actual memory was opened. `graph` is
  navigational: it does not turn graph neighbours into automatic truth.
- `memory write` is source-traceable, ignores model-supplied ranking fields,
  and uses only exact normalized-content deduplication. Semantic duplicate or
  conflict adjudication remains Scarlet-owned through source-backed proposals
  and lifecycle commands.
- `memory conflicts` does not assert a semantic conflict deterministically.
  It returns non-authoritative review leads: exact normalized duplicate groups
  and divergent legacy-fact groups, each requiring Scarlet to inspect memory
  and source provenance before a lifecycle decision.
- `session list` is a bounded episodic index; `session open` labels its latest
  transcript window and truncation; `session message` and `session turn` give
  the direct message/turn navigation requested by the context contract.
  `session summarize` is idempotent when current and otherwise uses the
  auxiliary provider with source transcript retained as stronger evidence.
- All of these operations flow through the same shell dispatcher for human
  and autonomous turns. Their source context changes only by origin/session,
  not by a second command implementation.

### F-07 - Legacy fact semantics and shell wording disagree

Evidence:

- `facts.py` classifies a fact as authoritative only when explicit
  `semantic_authority=scarlet` and `semantic_status=confirmed` metadata are
  present. The current write path creates no new facts; historical fact rows
  remain legacy audit material.
- Search excludes those legacy facts as active semantic evidence. Conflict
  inspection correctly labels their divergence as a non-authoritative review
  candidate.
- In contrast, `handle_memory_facts()` tells Scarlet to use facts as
  “canonical memory state” and says their entity/predicate/value should guide
  conflict reasoning, without first restricting that claim to explicitly
  confirmed facts.

Implication:

The storage and retrieval boundary follows the post-V1.64 decision, but the
manual shell wording can re-elevate historical heuristic propositions in
Scarlet's reasoning. Later correction should keep facts inspectable for audit
while explicitly separating confirmed future facts from legacy annotations.

### F-08 - The API contract's top-level family list is stale

Evidence:

- The executable registry currently publishes ten namespaces: help, memory,
  session, focus, volition, affect, mode, perception, episode, and
  metacognition.
- `docs/api-contract.md` still names only the earlier eight-family list in
  its primary model-facing shell overview, even though later sections document
  episode and perception.

Implication:

The code/catalog is the availability authority, but this overview can make a
reviewer or future prompt/documentation change understate Scarlet's real
shell surface. This is documentation drift, not a runtime divergence.

## Mind Shell Review - State Organs And Agent Mode

### Verified Behavior

- `focus` owns one foreground record at a time. Set/shift supersede prior
  active focus records; update/hold/defer/resolve/impossible preserve a
  transition edge, source session/turn/message provenance, an organ event,
  and a trace. It explicitly does not filter memory retrieval.
- `volition` stores a latent Scarlet-owned intention rather than a user task or
  external fact. It has explicit lifecycle operations, source provenance, and
  optional validated links to workspace candidates. Promotion produces a
  focus *candidate* only; it never changes focus implicitly.
- `mode` persists only `idle` or `scouting` as a future autonomous posture.
  During a human turn, `interactive` remains system-owned regardless of the
  persisted preference. A mode change records a trace/event and never starts a
  cycle by itself.
- `affect` is read-only to Scarlet. Its builder uses observable backend state
  (for example runtime failures, explicit memory-context signals, and decay of
  a prior stored state), not natural-language keyword classification. The
  deployed setting is currently `off`, so it neither creates a model packet
  nor affects current production answers.

### E-04 - Affect is an appraisal instrument, not yet autonomous affective cognition

Evidence:

- The organ combines fixed variables, fixed strengths/thresholds, a fixed
  prototype table, and a decay rule to produce an emotion label. Scarlet can
  inspect the resulting state but cannot set it directly.
- Its contract explicitly limits any future model-facing effect to posture; it
  cannot change memory retrieval, focus, volition, or backend actions.

Implication:

This is a correctly bounded deterministic runtime appraisal and is disabled
in production. It should not be described, tested, or designed as proof that
Scarlet has a rich self-generated affective process. If it is promoted later,
the appraisal-to-model boundary will need a separate semantic and behavioral
evaluation.

## Mind Shell Review - Perception, Episodes, And Metacognition

### Verified Behavior

- `perception status|open|read` navigates an immutable, source-labelled
  external-observation ledger. Opening a channel returns an ordered bounded
  batch, advances a cursor, and never changes the original observation time;
  direct read opens one exact event.
- `episode` is a Scarlet-owned bounded inquiry lifecycle. It can open only
  source-backed candidates, checkpoint progress or explicit no-progress,
  suspend/resume/resolve/abandon, reject a candidate, record an expectation,
  and register/cancel explicit deterministic wake conditions. Each mutation
  retains source/episode history and emits `cognition.*` evidence.
- Wake-source classification uses typed exact/prefix event rules. It assigns
  an event to trace-only evidence, an existing episode, a candidate for M2.7
  appraisal, or an explicit required wake; unknown event types fail closed.
  It does not infer semantic importance from words in ordinary natural-language
  content.
- `metacognition step` is the one explicit auxiliary review path. It uses the
  configured auxiliary MiniMax M2.7 profile, returns a structured review to
  M3 Scarlet, validates suggested commands against the shell registry, and
  retains provider thinking as process evidence. Raw prior thinking can be
  supplied to the reviewer at a bounded requested detail level; its result
  exposes only a retrospection summary, while raw provider thinking remains in
  trace/debug evidence.

### E-05 - Perception consumption is per session, not per individual

Evidence:

- The ledger is profile-scoped and append-only, but `PerceptionCursor` is
  keyed by `session_id` and channel.
- Opening a notification channel from the autonomous session advances only the
  autonomous cursor. A new or different human session starts with no cursor
  and can receive the same historic observations again.

Implication:

This currently favours complete inspectability over globally shared sensory
consumption and is safe while perception is manual/on-demand. Before device
signals become a regular cognitive input, decide whether Scarlet needs a
profile-level attention/acknowledgement layer in addition to per-session
navigation, so human and autonomous cognition do not independently reprocess
the same observation without knowing it.

### E-06 - Wake registry retains one obsolete answer-validation label

Evidence:

- `wake_registry.py` classifies the unused `answer.*` prefix as trace-only
  “answer validation” technical evidence.
- Current runtime emits `assistant.answer.completed`; searches found no
  active semantic answer-validation implementation or `answer.*` producer.

Implication:

There is no active final-answer semantic gate behind this entry. It is stale
terminology in a trace-only registry and should be cleaned when the wake
registry receives its next intentional revision, not treated as an urgent
runtime defect.

### Focused Verification

- `backend/.venv/bin/python -m pytest tests/test_mind_shell.py -q`: **22
  passed**.
- Focused episode/perception/metacognition checks: **5 passed**. They cover
  Scarlet-owned candidate-to-episode lifecycle, fail-closed unknown wake
  events, perception availability/cursor order, and retrospection controls.

## Open Review Finding Index

This is a working index for the current code review. It is not a bug-ledger
classification and does not authorize runtime changes by itself.

- **F-01:** historical session summaries can remain missing because production
  reconciliation is disabled.
- **F-02:** the autonomous V2 context repeats the current autonomous session
  in two nearby representations.
- **F-03:** automatic-memory recency can be recorded before V2 has confirmed
  that the memory was delivered to Scarlet.
- **F-04:** six active production memories have source-provenance mismatches
  and therefore fail closed during V2 projection.
- **F-05:** the block registry advertises autonomous/perception context types
  that do not currently have automatic producers.
- **F-06:** the shell catalog validator and the executable dispatch path can
  drift because execution does not begin from the validated registry result.
- **F-07:** legacy fact handling is non-authoritative, while part of the shell
  wording still calls facts canonical.
- **F-08:** the API contract's shell namespace overview is stale.
- **F-09:** a retry after an upstream stream interruption restarts the model
  step from the last complete provider-history boundary; it cannot resume an
  already partially emitted provider response.
- **F-10:** the 500k operational context limit and 400k compaction trigger are
  measured and scheduled after completion, but are not a pre-provider admission
  gate for the current request.
- **F-11:** simultaneous human sends in one session can race provider-history
  replacement and the per-session event-sequence contract.
- **F-12:** a hard restart leaves `started` turns for later audit; no startup
  reconciliation currently terminalizes them.
- **E-02:** shadow context-family routing and the live mode router use easily
  confused names, despite no duplicate live delivery today.
- **E-03:** autonomous posture is manually selected rather than chosen from a
  trigger.
- **E-04:** affect remains a bounded disabled appraisal prototype, not rich
  autonomous affect.
- **E-05:** perception consumption is tracked per session rather than per
  individual.
- **E-06:** a trace-only wake-registry label still refers to obsolete answer
  validation terminology.
- **E-07:** V2 memory projection has no explicit delivered/omitted-id receipt
  linking final model delivery to recency activity.
- **E-08:** autonomous turns share the retriever but compose its input from an
  activation envelope and a cross-session continuity window.
- **E-09:** `max_tokens` recovery is deliberately bounded, and a tool block
  truncated at `max_tokens` fails closed rather than being resumed.
- **E-10:** the auxiliary ignition schema exposes `rejected_ids`, but the live
  workspace preserves those candidates rather than applying an M2.7 rejection.
- **E-11:** first startup of the workspace cursor intentionally begins at the
  newest event/perception record, leaving prior cached signals outside the
  normal appraisal flow.
- **E-12:** failed idle/compaction maintenance has no general durable retry or
  dead-letter/recovery policy.
- **E-13:** live provider deltas are connection-local; V2 reconnection resumes
  durable events, not the middle of a token stream.
- **E-14:** SQLite schema evolution uses targeted startup migration code rather
  than a persisted, ordered schema-migration ledger.

## Native Provider And Turn Lifecycle Findings

### Verified Completion Boundary

- The native interactive adapter delegates preparation and completion to the
  shared turn kernel. `require_native_end_turn()` is a compatibility alias for
  `require_terminal_response()`; it is not a GPT-bridge obligation or a second
  turn protocol.
- Native finality is structural: Scarlet completes only after a non-empty
  provider response with `stop_reason=end_turn`, completed tool lifecycles,
  and successful persistence. There is no active `<scarlet-final/>` convention
  and no semantic final-answer validator.
- A normal `max_tokens` result preserves the complete assistant provider
  blocks, appends a continuation request, and continues the same model turn.
  The focused provider test proves this path for an ordinary text response.

### F-09 - A provider retry cannot resume a partially streamed model step

Evidence:

- `_stream_provider_message()` retries an `AnthropicError` by issuing the same
  provider request again. It does not append already emitted partial response
  blocks to provider history or create a continuation request before retrying.
- The current API contract explicitly documents this limitation: the upstream
  API has no token-resume cursor, so the retry starts from the last complete
  provider-history boundary and partial failed-attempt deltas remain transient.
- `test_tool_chat_retries_interrupted_provider_stream()` proves a failure before
  a completed provider message, but it does not simulate a disconnect after
  text, thinking, or tool-input deltas have already reached a live consumer.

Implication:

The current five-attempt policy is an availability retry, not true stream
resumption. A client may have observed partial live deltas before the restarted
step produces a different or overlapping continuation; durable history is
protected because only a completed provider message is promoted. This is a
real lifecycle gap against the desired "resume where interrupted" experience,
but it cannot be solved by merely changing a retry count. It needs an explicit
reconciliation protocol between provider, backend event stream, and client
projection.

### E-09 - `max_tokens` recovery has intentional safe-failure boundaries

Evidence:

- `PROVIDER_MAX_TOKEN_CONTINUATIONS` defaults to eight. Repeated exhaustion
  raises an explicit incomplete-response error rather than looping forever.
- A `tool_use` block paired with `stop_reason=max_tokens` is rejected without
  dispatch, because its JSON/tool intent may be incomplete.
- Focused tests cover successful text continuation, the continuation limit,
  and rejection of truncated tool use.

Implication:

These are defensible integrity boundaries, not evidence of the removed
semantic-answer validation. They do mean that "continue after max_tokens" is
not absolute for pathological responses or partial tool requests. Decide
whether this explicit fail-closed behavior is the intended operational
contract before attempting any recovery redesign.

## History Routing And Compaction Findings

### Verified Partition Design

- The configured design matches the accepted token partition: a physical
  1,000,000-token model window, a 500,000-token operating limit, a 400,000-token
  compaction trigger, 100,000 tokens for recursively compacted chronology,
  100,000 tokens for intact newest complete turns, and 25,000 technical-safety
  tokens.
- Selection is token-based at whole-turn boundaries; the obsolete
  `history_compaction_recent_turns` setting is retained only for environment
  compatibility and is not used to choose the verbatim tail.
- Canonical provider history remains append-only. A derived artifact is
  source-mapped to completed turns, recursively regenerated with MiniMax M2.7,
  validated against canonical turn/source digests, and routed only when valid.
  Invalid or unavailable mapping falls back visibly to canonical history.
- The source mapper has a deliberate single-turn exception: a whole turn may
  exceed the 100k verbatim partition if it is still inside the physical 1M
  window. A single turn beyond the physical window fails closed rather than
  being silently split or discarded.

### F-10 - Context limits are planning and scheduling thresholds, not preflight admission gates

Evidence:

- `build_context_accounting_preflight()` calculates the full request estimate
  and records a compaction plan, but neither it nor `prepare_model_turn()`
  blocks, compacts synchronously, or otherwise changes the request when the
  estimate crosses the 400k trigger or the 500k operating limit.
- `schedule_history_compaction()` is called only after a successful completed
  turn. It queues derived-artifact generation when the observed model-history
  estimate plus external context reaches the trigger.
- The next request benefits only after that asynchronous job has generated and
  validated an artifact. If a current request grows through the threshold, an
  artifact is unavailable/stale, or external context changes sharply, the full
  request can pass the operating limit before the planner acts; the physical
  1M provider window remains the last protection.

Implication:

The fixed partitions are implemented faithfully as a **post-turn derived
history policy**, not as a strict real-time input-budget invariant. This is a
meaningful gap against the intended "leave reserved active context before
saturation" behavior. The solution needs an explicit admission/recovery design
that retains whole-turn/source guarantees; it should not silently truncate
history or turn the estimate into a brittle hard failure.

## Autonomous Workspace Findings

### Verified Shared Lifecycle And Boundaries

- An autonomous activation creates a source-labelled activation message in the
  one `scarlet_autonomous` session, then calls the same shared model-turn
  preparation, V2 context, retrieval, shell, provider-finality, persistence,
  accounting, and post-turn compaction path as an interactive native turn.
  Its differences are adapter-owned: source envelope, private visibility,
  autonomous continuity query composition, and yielding to an active human
  turn.
- In active workspace mode, legacy periodic activations are retired. Typed
  runtime/perception/volition signals become source-backed receipts; MiniMax
  M2.7 can only appraise and recommend ignition. Scarlet M3 performs the
  resulting autonomous turn and must explicitly endorse any lasting episode or
  volition.
- Autonomous `turn.completed` events are explicitly downgraded to trace-only
  input, preventing a completed internal cycle from recursively waking itself.
  Cognitive workspace receipts are likewise trace-only, preventing a receipt
  loop.
- Endogenous windows use M2.7 only to propose source-backed seeds on an
  adaptive cadence. Empty windows back off; productive seeds may request an
  earlier follow-up. The watchdog delegates to that cadence when endogenous
  cognition is enabled.

### E-10 - The ignition contract exposes unsupported `rejected_ids`

Evidence:

- `CognitiveIgnitionDecision` and its prompt allow the M2.7 ignition component
  to return `rejected_ids`.
- `_arbitrate_candidates()` uses selected coalitions and explicit deferrals,
  but no live code consumes `decision.rejected_ids` to alter a candidate.
- Candidate lifecycle explicitly allows `rejected`, while the current
  architecture states that M2.7 is provisional and must not adjudicate
  Scarlet-owned cognition.

Implication:

This is an authority/contract mismatch, not proof that candidates are being
wrongly destroyed. At present a M2.7 rejection has no operational meaning;
the candidate remains open unless Scarlet later resolves/rejects it or a
different path defers it. Decide whether the field should be removed or
renamed as a non-authoritative recommendation, or whether it needs a
separately bounded lifecycle meaning. Do not give M2.7 silent final authority
merely to make the field "work".

### E-11 - Initial workspace bootstrap intentionally skips pre-existing cached signals

Evidence:

- On its first non-replay tick, `_bootstrap_live_cursors()` sets each profile
  signal cursor to the newest existing runtime event and perception record.
- Only evidence arriving after that cursor enters normal appraisal. Historical
  replay is permitted only in shadow mode.

Implication:

This prevents an accidental activation storm after enablement or restart, but
it also means a device/event cache accumulated before the first active cursor
is not assessed by Scarlet. Before perception/device signals become important
life evidence, define a startup/restart backlog policy: explicit bounded
admission, explicit archival/acknowledgement, or a shadow review. Leaving it
implicit risks both silent loss and unsafe mass replay.

## Maintenance, Persistence, And Delivery Findings

### E-12 - Failed maintenance jobs have no general durable retry policy

Evidence:

- The historical-summary reconciler has its own bounded attempt counter and
  exponential backoff, but it is disabled in the deployed configuration.
- Idle maintenance and history-compaction jobs transition to `failed` after a
  provider or implementation failure. Their normal idempotency key then
  prevents that exact job from being scheduled again.
- A later completed human turn creates a new idle-maintenance key. A changed
  canonical-history digest creates a new compaction key. Neither mechanism
  retries the failed work when the relevant source state remains unchanged.

Implication:

The system preserves failure evidence and does not silently repeat a possibly
unsafe mutation, which is good. It nevertheless lacks a common recovery
contract for transient auxiliary-provider or worker failures. This is an
operational reliability gap, not a reason to retry semantic maintenance work
blindly: any future policy must distinguish a safe same-input retry from a
newly sourced job and retain the failed attempt as history.

### F-11 - Human turns within one session are not serialized

Evidence:

- `prepare_native_turn()` creates a `started` turn and persists the user
  message without checking whether the same human-dialogue session already has
  a live turn.
- Each preparation snapshots its own provider-history source. On completion,
  `complete_model_turn()` writes the resulting provider history back to the
  session from that prepared snapshot.
- Event sequence allocation is `max(session.seq) + 1`; `CognitiveEvent` has
  no database uniqueness constraint over `(session_id, seq)`.

Implication:

Two simultaneous sends to the same session can form competing provider-history
branches. Both user/assistant messages may remain inspectable, while the last
completion overwrites the session's canonical provider-history pointer with
one branch. The same race can duplicate or gap event sequence numbers, which
violates the V2 reducer's ordered-cursor assumption. This requires a
per-session admission/idempotency strategy, not a global lock and not a
semantic model-side guard.

### F-12 - A hard process restart does not reconcile stale `started` turns

Evidence:

- The detached native runner catches process-local exceptions and closes its
  own active turn as failed.
- Application startup starts the maintenance and autonomous workers, but does
  not scan for or terminalize pre-existing `started` turns.
- The autonomous foreground guard deliberately stops treating a stale started
  human turn as live after its configured freshness window. It preserves that
  historical row for later analysis rather than repairing it.

Implication:

A process kill can leave a turn with persisted user/context evidence and no
terminal completion/failure receipt. It will eventually stop blocking
autonomous cognition, but remains an unresolved lifecycle record and can keep
summary repair/audit blocked. A future recovery path must preserve partial
traces, declare why the turn ended, and never fabricate an assistant answer.

### E-13 - Live token frames are intentionally connection-local

Evidence:

- `/stream-live` emits transient thinking/text/tool-input deltas alongside
  projected durable V2 events.
- `/stream-v2` and its resume endpoint replay only persisted
  `CognitiveEvent` rows. Provider token deltas are not stored as events.
- The live feed is explicitly connection-local and is detached when its client
  disconnects; a resumed stream can reconstruct semantic blocks and terminal
  state, but not a token prefix from the middle of a provider block.

Implication:

This is a reasonable separation between durable cognition and high-volume
transport frames. It must remain explicit in the client/runtime contract:
reconnection is block/event recovery, not byte-for-byte continuation of live
thinking or answer text. Together with F-09, it explains why a robust retry UX
needs reconciliation rather than treating every replay as an uninterrupted
stream.

### E-14 - SQLite schema evolution is hand-maintained rather than versioned

Evidence:

- Startup calls `SQLModel.metadata.create_all()` and then a targeted
  `_migrate_sqlite_schema()` routine for selected historical columns and
  indexes.
- There is no persisted schema-version ledger or ordered migration chain; each
  structural change must be remembered and encoded directly in that routine or
  be safe for `create_all()` on a new database.
- The production preflight and the current V1.65 deployment show a coherent
  live database, so this is not evidence of a present schema mismatch.

Implication:

The present deployment process is careful, but structural evolution depends on
human completeness rather than an executable migration history. Before another
large persistence expansion, decide whether to retain this deliberately small
scheme with a stronger migration audit or introduce a versioned migration
mechanism. Do not retrofit it casually into production merely because the
absence of a version table looks untidy.

## Stabilization Review Boundary

This pass has now read the active implementation for session/context assembly,
the shell, provider/turn lifecycle, history routing, autonomy/workspace,
maintenance, persistence/event delivery, database selection, device admission,
and the optional module boundary. It also compared the active VPS image and
safe runtime configuration with the local V1.65 source baseline.

Verification performed without mutating production:

- focused provider, history, workspace, maintenance, runner, and Stream V2
  suites: **48 passed**;
- focused V2 context, endogenous/device, database-boundary, and optional
  module-host suites: **32 passed**;
- VPS image: `scarlet-mobile-api:v1.65.0-04b62ee`; the later local
  `69c01ee` commit is documentation-only relative to that runtime image;
- VPS confirms active history compaction, hybrid retrieval, maintenance,
  autonomy, and mode routing; production summary reconciliation remains
  intentionally disabled.

This is a source-and-contract review, not a destructive production audit and
not a substitute for an explicit behavioral evaluation. In particular, it did
not send concurrent live turns, kill a production process, retry a real
mid-stream provider disconnect, mutate provenance records, or exercise the
experimental GPT adapter. Those are deliberate future test/fix decisions,
not gaps hidden by this review.

# Context Packet Implementation Plan

Last updated: 2026-07-12
Planning target: V1.29.0
Status: implemented and verified in V1.29.0
Branch: `checkpoint/rework-baseline`

## V1.30.0 Follow-Up

The V1.29 packet plan remains the historical implementation record. V1.30.0
adds the next control layer without rewriting that result:

- one canonical GPT runtime serialization instead of a duplicate object/string;
- per-channel native context accounting and partial GPT packet accounting;
- shadow-only 400k compaction planning toward a 100k chronology plus measured
  recent complete turns;
- one active agent mode tag with multi-tag automatic context eligibility;
- deterministic behavioral scenario/run contracts.

No V1.30 operation compacts or replaces canonical chronology. Duplicate and
conflict adjudication remains outside this follow-up.

## V1.36.0 Chronology Follow-Up

V1.36 replaces the fixed recent-turn assumption with an exact provider-history
source map and the shadow partition `O + C + H + A + M <= 500k`. `C` and normal
`H` are configurable 100k maxima, `M` is 25k, and complete turns enter `H`
backward by token cost. A whole turn may exceed `H` only as an explicit
physical-window exception. The active V2 packet and canonical provider history
remain unchanged.

## Implementation Result

V1.29.0 implements Phases 1 through 10 for the reviewed packet families. The
canonical compiler is active with `model_context_profile=v2`; `legacy` and
`v2_shadow` remain reversible settings. Rich `memory.context` and
`runtime.context` evidence stays trace/UI-only, while the exact delivered V2
document is persisted in `model.context`.

The disposable laboratory validation repaired `36/36` unambiguous memory
source-message hooks and generated `34/34` eligible missing summaries through
the existing provider summarizer. The resulting audit was 146 current
summaries, 6 blocked by active turns, and 11 empty sessions. No production or
source laboratory DB was mutated.

Acceptance evidence: backend `138/138`, unchanged preliminary regression
`9/9`, frontend production build, focused V2 contract tests, native live probes
for time/location, relevant recall, exact provenance, previous-session
continuity, write provenance, and cross-session personal recall, plus GPT
bootstrap/trace identity tests.

Production rollout on 2026-07-13 preserved the VPS database, repaired `46/46`
unambiguous historical source-message hooks, generated `67/67` eligible
historical summaries, passed SQLite integrity, and passed native MiniMax and
public GPT Actions V2 smoke probes. The remaining 242 provenance gaps were not
guessable and were deliberately left unresolved.

## Purpose

Implement the compact dynamic context contract reviewed in
`docs/context-packet-inventory.md` without deleting or weakening the richer
backend evidence used by retrieval, maintenance, traces, logs, or UI.

This plan concerns dynamic context packets only. It does not redesign the
native system prompt, provider-native active-session history, the Mind shell
tool schema, or the external GPT Actions schema. Those are separate technical
delivery surfaces with their own lifecycle.

Memory-conflict semantics are deliberately deferred. V1.29.0 must not change
conflict candidate discovery, conflict adjudication, lifecycle behavior, or
the `memory conflicts` command. Existing conflict data remains available to
backend diagnostics and traces, but no conflict payload is added to the new
automatic model context.

## Verified Implementation Evidence

The 2026-07-12 code and read-only laboratory review established:

- `build_memory_context()` currently mixes retrieval, persistent usage
  mutation, runtime assembly, rendering, and tracing. It is not a pure source
  for a shadow compiler.
- automatic selected retrieval and manual search both call
  `mark_memory_used()`, which increments usage and overwrites both
  `last_used_at` and semantic `updated_at`;
- all 36 memories in the current laboratory DB have source session and turn,
  but none has `source_message_id`;
- every one of those 36 source turns has exactly one user and one assistant
  message, so the triggering user message is a deterministic repair candidate
  for this specific DB;
- direct Scarlet writes do not pass a source message to storage;
- idle-maintenance prompts include message ids, but the required output and
  normalization discard them before proposal creation;
- 44 of 163 laboratory sessions have no summary, 11 sessions have no visible
  dialogue, and all persisted summaries attached to non-empty sessions are
  currently up to date;
- of the 44 missing summaries, 34 belong to completed non-empty sessions and
  are directly backfillable, 6 are blocked by turns still marked `started`,
  and 4 belong to empty sessions that need no summary;
- 39 non-empty missing-summary sessions never had a maintenance job; one had a
  failed provider job. Failed jobs are terminal today because the unique
  idempotency key returns the same failed record instead of scheduling retry;
- previous sessions are selected by maintenance-sensitive
  `sessions.updated_at`, then expanded through multiple per-session queries;
- current memory/profile filtering uses semantic `scope`, not record ownership
  by `profile_id`; the runtime is still a single-user data boundary;
- the GPT bootstrap returns the native rendered runtime plus separate compact
  runtime and memory summaries, creating provider-specific duplication;
- the existing SQLite initializer can safely create a new table, but data
  repairs must be explicit operations rather than startup migrations.

These findings change implementation order: live provenance capture and
activity semantics must be fixed before V2 recent-memory projection can be
considered valid.

The two wording/semantic confirmations identified during planning were closed
before activation:

- confirm that a direct turn-time memory uses the triggering persisted user
  message as its compact primary `source_message_id`, while the turn remains
  the complete evidence unit;
- missing and stale summaries use explicit fixed navigation fallbacks and are
  never presented as current evidence.

## Accepted Contract

### Session-Attached Context

The model-facing session context will combine the approved user, world, and
episodic hints:

```json
{
  "current_session": {
    "id": "ses_...",
    "title": "...",
    "created_at": "2026-07-12T16:00:00+02:00"
  },
  "user": {
    "name": "Mario"
  },
  "now": "2026-07-12T16:30:00+02:00",
  "timezone": {
    "id": "Europe/Rome",
    "name": "CEST",
    "utc_offset": "+02:00"
  },
  "location": "Italia",
  "previous_sessions": [
    {
      "id": "ses_...",
      "last_message_at": "2026-07-11T18:42:00+02:00",
      "turn_count": 12,
      "summary": "..."
    }
  ]
}
```

The current-session hint retains only its id, title, and creation time. Raw
metadata and `sessions.updated_at` are omitted: they are backend state and the
latter can move because of maintenance rather than conversation. The creation
time follows the same user-time rendering rule as every other model timestamp.

`previous_sessions` contains at most two sessions. `last_message_at` is the
latest user or assistant message timestamp, never `sessions.updated_at`.
`turn_count` counts conversational turns, excluding traces and maintenance
activity. The summary is a navigation hint rather than proof; the session id
is the route to exact episodic inspection. When no persisted summary exists,
use the fixed navigation fallback `Sessione con riassunto mancante; ispeziona
la sessione per vedere i dettagli.` rather than synthesizing a pseudo-summary
from title or messages.

Scarlet can already attach a durable summary through `session summarize
<session_id>`. Idle maintenance already schedules summary generation after 900
seconds from the last completed activity; V1.29.0 must verify that behavior,
not reimplement it inside the packet compiler. Starting a new session should
invoke the bounded reconciler for a missing/stale previous summary; it must not
block session creation on a synchronous provider call.

The current user message is not duplicated inside this packet. Profile ids,
privacy policy, locale-source metadata, storage-clock metadata, precision
labels, packet policy prose, and backend correlation fields remain systemic.

### Memory Context

The model-facing memory area has three ordered blocks:

```json
{
  "relevant": [],
  "recent_user": [],
  "recent_general": []
}
```

Every memory item has exactly the same compact navigation shape:

```json
{
  "id": "mem_...",
  "content": "...",
  "created_at": "2026-07-10T09:10:00+02:00",
  "updated_at": "2026-07-10T09:10:00+02:00",
  "source_session_id": "ses_...",
  "source_message_id": "msg_..."
}
```

Default limits are configurable and initially set to five for every block.
Memory ids are unique across all three blocks. Deduplication priority is:

```txt
relevant -> recent_user -> recent_general
```

Each lower-priority selector continues through its candidate pool to fill the
limit with distinct eligible memories. It returns fewer items rather than
duplicating a memory.

The current runtime is explicitly single-user. `recent_user` selects
user-scope memories; `recent_general` selects the remaining active memories
after higher-priority deduplication. The configured `profile_id` is not yet a
memory-ownership boundary. Future multi-user access must be enforced by
authenticated user id in persistence and queries, never by instructions sent
to Scarlet.

Automatic memory hints do not include facts, KG payloads, scores, retrieval
signals, classifications, lifecycle state, reason for storage, future-use
notes, near misses, excluded candidates, or raw provenance. Scarlet can open
those layers deliberately through `memory open`, `memory facts`, `memory
graph`, and source-session navigation.

### Time Contract

All model-facing timestamps use the active human user's configured timezone.
This includes `now`, `previous_sessions[].last_message_at`, and every memory
`created_at` and `updated_at` value. The backend may continue to persist UTC;
conversion happens once at the model-context boundary.

No second current clock is sent to Scarlet. Daylight-saving changes must be
resolved by the timezone database rather than by fixed-offset arithmetic.

### Cognitive Recency

Recent memory ordering is based on eligible cognitive activity rather than
record creation alone. Eligible activity is:

- a new memory write;
- a semantic update or replacement that creates the active memory state;
- a manual Scarlet search/open result actually returned to the model;
- an advanced automatic result that survives reranking and enters context.

Simple automatic retrieval, candidate generation, near misses, excluded
records, skipped records, UI reads, maintenance scans, and trace inspection do
not make a memory recent.

Eligible activity updates the recency state immediately when it occurs. An
automatic packet already delivered at turn start remains an immutable snapshot,
but every subsequent selector in the same turn and every later turn observes
the new ordering. A manual result is itself visible immediately. If advanced
automatic retrieval selects a memory before V2 recent blocks are compiled,
that activity participates in the current turn's recency ordering.

Receiving a memory in a recent-memory block is not an activity and must never
refresh it. Timestamps in the compact hint are semantic record timestamps, not
access times. Activity is recorded separately, so repeatedly emitting the same
five-item packet cannot keep those five memories artificially recent.

## Architectural Boundary

### Two Representations, One Source Pipeline

The implementation must keep two explicit representations:

1. **Internal evidence snapshot**: the existing rich retrieval/runtime data
   used by backend decisions, traces, maintenance, debug UI, and evaluation.
2. **Model context document**: a versioned projection containing only the
   dynamic evidence intentionally delivered to Scarlet.

The second representation is compiled from the first. It must not become a
second retrieval implementation. Local MiniMax and the external GPT bridge
must consume the same compiled document so packet semantics cannot drift by
provider.

The proposed profile name is `scarlet-model-context-v2`. The exact serialized
document delivered to the model must be persisted in a trace, alongside ids
that link it to the richer `memory.context` and `runtime.context` evidence.

### Target Module Boundaries

The current `app.mind.context` performs retrieval, model projection, runtime
assembly, organ assembly, rendering, and tracing in one module. V1.29.0 should
extract narrowly scoped modules rather than add more branches to it:

```txt
app/mind/context.py                  orchestration and compatibility facade
app/mind/context_contracts.py        typed V2 model-context contracts
app/mind/context_projection.py       V2 compiler and cross-block deduplication
app/mind/context_time.py             user-time rendering
app/mind/context_sessions.py         previous-session hint projection
app/mind/context_memories.py         memory hint pools and activity selection
```

Names may be adjusted to match the code during implementation, but retrieval,
projection, and presentation must remain separate responsibilities.

### Configuration

Add explicit settings with validated non-negative limits:

```txt
model_context_profile=legacy|v2_shadow|v2
model_context_previous_sessions_limit=2
model_context_relevant_memories_limit=5
model_context_recent_user_memories_limit=5
model_context_recent_general_memories_limit=5
```

`legacy` preserves current delivery, `v2_shadow` compiles and traces V2 without
sending it, and `v2` sends V2. Production rollout begins in shadow mode and is
reversible by configuration.

## Persistence And Selection Work

### Memory Activity Ledger

The current `MemoryRecord.last_used_at` is not sufficient for the accepted
contract: automatic selected retrieval updates it, and `mark_memory_used` also
mutates `updated_at`. A read must not masquerade as a semantic memory update.

Introduce an append-only memory activity record with at least:

```txt
id
memory_id
activity_kind
occurred_at
profile_id
actor
source
session_id
turn_id
message_id when available
trace/tool-call reference when available
eligible_for_recent
```

The record is systemic and never sent to Scarlet. Repository queries derive
the latest eligible activity per memory, enforce the current single-user
visibility boundary, and return enough additional candidates for cross-block
deduplication. The activity record is itself the append-only audit event and
must not touch `sessions.updated_at`; compiling or delivering recent-memory
packets must not write activity.

Legacy memories without activity events cannot be ordered from
`last_used_at` or `updated_at` blindly: current automatic reads may have changed
both. The provenance/activity audit must define a one-time, sourceable baseline.
Where no reliable activity evidence exists, use creation time as the explicit
fallback rather than pretending it represents a later cognitive access. New
activity events become authoritative from activation onward.

`last_used_at` and `usage_count` remain compatibility/diagnostic fields during
V1.29.0, but they are not the source of model-facing recency. Reads must stop
changing semantic `updated_at`. Any later removal or reinterpretation of the
legacy fields is a separate migration.

### Activity Recording Matrix

The following matrix translates the accepted high-level recency rules into
call sites. It records whether Scarlet actually processed a memory; it is not
a duplicate/conflict classification matrix.

| Operation | Record eligible activity | Notes |
| --- | --- | --- |
| `memory write` stored | yes | New active memory. |
| write review candidate shown | yes | The candidate was actually presented to Scarlet, without classifying it deterministically. |
| supersession/update | yes | Record the active replacement, not an inactive record. |
| manual `memory search` | yes | Only ids actually returned to Scarlet. |
| manual `memory open` | yes | The opened active memory. |
| `memory facts` or `memory graph` | yes | The root memory was deliberately inspected. |
| simple automatic retrieval | no | Does not alter short-term cognitive recency. |
| advanced reranked selection | yes | Only selected memories actually delivered. |
| automatic recent-memory hint | no | Delivery of the recency snapshot cannot refresh itself. |
| near miss/excluded/skipped | no | Not processed by Scarlet. |
| UI, trace, maintenance read | no | Systemic access only. |

Each call site must declare its activity kind explicitly. No generic repository
read may silently count as cognitive activity.

### Provenance Eligibility

Every automatically delivered memory hint must have both
`source_session_id` and `source_message_id`. The compiler must never fabricate
either value. Historical records missing a hook require a provenance audit
before V2 activation: determine whether they predate the current storage
contract, whether their source can be reconstructed from persisted messages,
turns, traces, or proposals, and whether they are clearly disposable test
data.

Repairable memories must be aligned to the current contract through a dry-run,
sourceable migration. Deletion is reserved for records confirmed to be useless
or test-only and requires explicit review. Until repaired, incomplete records
remain available to backend diagnostics and manual inspection but are not
eligible for automatic V2 hint blocks. No missing source id may be guessed.

For a live model-facing memory write, `source_message_id` means the primary
triggering/evidence message for the memory. In the current turn architecture
that is normally the persisted user message; `source_turn_id` remains the
route to the complete user/tool/assistant evidence bundle. Maintenance
candidates may name one or more evidence messages, with the first validated id
stored as the compact primary hook and the full list retained in proposal
provenance.

This strict rule requires a pre-implementation report against the frozen
laboratory DB: counts of active memories with complete, partial, and missing
source provenance, grouped by scope. The report is read-only and must not
modify production or laboratory data.

## Direct Source Navigation

Add deterministic Mind shell navigation so a compact memory hook can be
opened without loading an entire session:

```txt
session message msg_...
session turn turn_...
```

`session message` returns the selected message, session id, turn id, role,
timestamp, and compact source references. `session turn` returns the triggering
user message, model-visible public notes, tool/action calls and results,
assistant answer, and trace references in chronological order. It must not
expose hidden chain-of-thought.

Implementation work includes repository/service lookups, shell registry and
parser entries, help/catalog examples, compact shell presentation, traceable
tool-call behavior, API-contract documentation, and focused tests. Existing
`session open` remains the full-transcript route. No KG node id is added to
automatic memory hints because `memory graph <memory_id>` already resolves the
graph root.

## Phased Implementation

### Phase 0 - Preserve Undiscussed Context Families

Status: completed in V1.35.0.

The following dynamic families will be reviewed separately:

- recent dialogue and recent runtime events;
- API Mind capability hints;
- `scarlet_state`;
- focus, affective, and metacognitive blocks;
- top-level compatibility mirrors in model input;
- bridge-only summaries and duplicated compact fields that do not belong to
  the shared model-context contract.

The review retained only allowlisted focus, affect, and metacognitive fields as
conditional model input. It moved `scarlet_state`, duplicated recent dialogue,
and generic runtime events to trace/UI-only, and capability detail to on-demand
`help`. The rich runtime snapshot and compatibility mirrors remain intact for
system diagnostics. `model.context.projection_audit` records every family and
field decision, while native MiniMax and GPT bootstrap consume the same
canonical V2 document.

### Phase 1 - Freeze Baseline Evidence

1. Run the unchanged preliminary regression suite on a fresh disposable copy
   of the frozen test DB.
2. Capture representative current `memory.context`, `runtime.context`, native
   `llm.request`, and GPT bootstrap payloads.
3. Produce the read-only provenance-completeness and source-repairability
   report, separating current records, legacy repair candidates, and confirmed
   test-only candidates.
4. Record packet byte/token sizes and duplicate field paths.
5. Confirm the production DB preflight remains read-only and excluded from all
   test paths.

### Phase 1B - Repair And Reconcile Session Summaries

1. Add a read-only summary audit that classifies sessions as current, missing,
   stale, empty, blocked by an active turn, or blocked by failed maintenance.
2. Add an internal summary-reconciliation operation using the existing
   `handle_session_summarize()` implementation. It targets only completed,
   non-empty sessions whose summary is missing or stale.
3. Keep historical summary repair separate from idle memory review so a bulk
   backfill does not also create memory proposals for old sessions.
4. Support dry-run, bounded batch size, explicit session ids, resume, per-item
   results, provider cost/usage reporting, and idempotency by the transcript's
   actual last message id.
5. Add retry with bounded attempts and backoff for transient provider failures.
   A failed idempotent job must be reschedulable rather than permanently
   blocking the same summary target.
6. Run the operation on a disposable laboratory copy first, then generate the
   34 currently eligible summaries through the normal summarizer. Re-audit
   coverage and inspect a representative sample before any production run.
7. Do not summarize the 6 sessions still marked `started`. Report them to a
   separate stale-turn recovery procedure; only after a turn is sourceably
   completed or marked failed may its session enter summary repair.
8. Exclude the 4 empty sessions from backfill and from `previous_sessions`.
9. Run a lightweight reconciler from the maintenance worker and after a new
   session starts, with strict batching, so missing/stale previous summaries
   are eventually repaired even when the original idle job was absent or
   failed.

The model-facing fallback remains necessary for the interval before repair and
for provider outages, but successful reconciliation should make it exceptional
rather than normal.

### Phase 2 - Capture Complete Live Provenance

1. Extend `MindAPIContext` with the current primary source message id.
2. Pass the persisted user-message id from native chat and GPT bootstrap/action
   paths; deterministic internal callers resolve it from the turn when needed.
3. Store that id in direct `memory write` operations.
4. Require maintenance review candidates to return evidence message ids,
   validate them against the source session/turn, and preserve them through
   normalization, proposal creation, and applied memory creation.
5. Add tests proving that native, bridge, maintenance, and internal write paths
   either persist valid provenance or retain the memory outside automatic V2
   eligibility without guessing.

This slice stops creation of new incomplete records before historical repair.

### Phase 3 - Add Memory Activity Semantics

1. Add an indexed append-only `memory_activities` table and repository facade.
2. Add a non-mutating creation-time fallback for records without events.
3. Remove `mark_memory_used()` from automatic context and manual search paths;
   reads must no longer change semantic `updated_at`.
4. Record explicit eligible activity only at the approved operation call sites.
5. For automatic retrieval, record activity only when an actually delivered
   selected result has a confirmed reranker signal.
6. Add queries for recent user and recent general pools with exclusions,
   over-fetch/refill, stable tie-breaking, and no session-touch side effects.
7. Keep legacy `usage_count`/`last_used_at` for compatibility but stop using
   them as V2 ordering authority.

### Phase 4 - Align Legacy Memory Provenance

1. Classify incomplete records as source-repairable, unresolved, or confirmed
   useless/test-only using persisted evidence.
2. Build a dry-run migration report with old values, proposed source ids,
   evidence path, and reason for every proposed change.
3. Validate the migration on a disposable laboratory copy and rerun memory,
   fact, graph, source-session, and preliminary regression checks.
4. Apply source repairs separately from provider activation, with backup,
   database preflight, transaction boundaries, and post-write verification.
5. Delete only explicitly reviewed useless/test records; retain unresolved
   records outside automatic V2 hints rather than inventing provenance.

The laboratory migration currently has a strong deterministic candidate for
all 36 records: the sole user message in each recorded source turn. Production
must be assessed independently; this observation is not permission to apply
the same update without its own report.

### Phase 5 - Add Evidence Queries And Shadow Compiler

1. Add typed V2 contracts and serializers.
2. Add the single user-time renderer.
3. Add one repository query for previous-session hints ordered by the actual
   last visible message; exclude empty sessions and avoid N+1 expansion.
4. Treat a summary as usable only when `last_message_id` covers the actual last
   visible message. Missing summaries use the accepted fallback. A separate
   stale-summary fallback remains an owner wording decision before activation.
5. Add compact memory projectors and global id deduplication with the accepted
   priority.
6. Compile V2 from already collected evidence without retrieval or persistent
   mutation.
7. Trace exact V2 output, source trace ids, field counts, omissions, and
   serialized size.
8. Do not change provider input in this phase.

### Phase 6 - Add Source Navigation

1. Implement deterministic message and turn lookup services.
2. Register `session message` and `session turn` in Mind shell.
3. Add compact, safe presentation and help text.
4. Verify source hooks from every eligible automatic memory can reach a
   message and turn in the frozen DB.

### Phase 7 - Native V2 Activation

1. Switch only local MiniMax model input from legacy projection to V2 behind
   `model_context_profile=v2`.
2. Preserve raw evidence and exact model-context traces.
3. Update Scarlet's native prompt only where it describes fields removed or
   renamed by the approved contract.
4. Keep provider-native active-session history unchanged.
5. Compare shadow and active traces for identical retrieval source ids.

### Phase 8 - GPT Bridge Parity

1. Return the same canonical V2 JSON document compiled for native Scarlet,
   wrapped only by bridge protocol/session/turn fields.
2. Remove separate bridge compact-runtime and compact-memory copies for the
   reviewed entities.
3. Keep bootstrap/action/finalize transport behavior and provider history
   unchanged.
4. Verify native and GPT paths serialize the same dynamic context for the same
   fixture, apart from transport envelope fields.

The bridge is an alternative model connection, not an alternative cognitive
system. It must not define its own memory, session, world, user, organ, or
runtime semantics. GPT Actions transport ids and protocol state may differ;
the API Mind context they carry may not.

### Phase 9 - UI And Diagnostics

1. Show the exact model context separately from full internal evidence.
2. Group session, relevant memory, user memory, and general memory blocks using
   the same V2 contract consumed by Scarlet.
3. Keep ranking, conflicts, near misses, excluded candidates, activity events,
   and raw runtime diagnostics in clearly marked debug/trace sections.
4. Add packet size, profile, limits, omissions, and source-trace links.

### Phase 10 - Verification And Acceptance

1. Run focused tests for every contract and call site.
2. Run the full backend suite.
3. Run the unchanged preliminary regression suite on a fresh copy of the same
   frozen DB and compare it with the Phase 1 baseline.
4. Run native MiniMax live probes using natural user messages, not direct shell
   instructions.
5. Run matching GPT bridge probes only after native acceptance.
6. Activate production only after trace review and database preflight.

Keep `preliminary-regression-v1` unchanged and run it before and after every
behavioral slice. Add a separate context-contract evaluator for new V2
invariants rather than rewriting the frozen baseline to match the feature.

## Required Verification Matrix

| Surface | Required evidence |
| --- | --- |
| Current session | Id, title, and user-local creation time only; no metadata or maintenance `updated_at`. |
| Previous sessions | Exactly two or fewer; real last-message time; real turn count; summary and id only. |
| Missing summary | Fixed navigation fallback; `session summarize` remains usable; idle job verified at 900 seconds. |
| Summary reconciliation | Missing/stale completed sessions are detected, retried, backfilled in bounded batches, and re-audited; empty/active sessions are not summarized. |
| User/world | Name only; one local clock; structured timezone; assembled location. |
| Time | Same timezone and offset across session and memory fields, including DST boundary fixtures. |
| Relevant memory | At most configured limit; compact hooks only; selected ids match rich retrieval evidence. |
| User recent memory | Eligible user-scope activity order; no duplicates from relevant. |
| General recent memory | Eligible global activity order; no duplicates from higher-priority blocks. |
| Activity | Manual/advanced/write actions count immediately; simple automatic, recent-packet delivery, and systemic reads do not. |
| Provenance | Every automatic hint has resolvable source session and message ids. |
| Navigation | Hint -> memory open/facts/graph and source message/turn succeeds. |
| Trace parity | Rich evidence retained; exact V2 packet persisted separately. |
| Provider parity | MiniMax and GPT receive the same dynamic V2 contract. |
| Privacy | Current single-user scope is explicit; future profile ownership is not falsely claimed or delegated to Scarlet. |
| Regression | Preliminary suite is similar or better; no accepted capability regression. |

Focused automated tests must use temporary/test databases. Live tests use the
approved laboratory snapshot or a disposable copy. The VPS production DB is
read-only for preflight and must never receive fixtures, evaluator writes, or
schema experiments.

## Suggested Commit Slices

1. `docs(context): approve v2 packet contract and readiness plan`
2. `fix(session): reconcile missing and failed summaries`
3. `fix(memory): capture complete live message provenance`
4. `feat(memory): track eligible cognitive memory activity`
5. `ops(memory): repair sourceable legacy provenance`
6. `feat(context): add v2 shadow compiler and exact traces`
7. `feat(session): add direct message and turn navigation`
8. `feat(context): activate native v2 model context`
9. `feat(bridge): align GPT bootstrap with v2 context`
10. `feat(ui): separate model context from diagnostic evidence`
11. `test(context): complete v2 live and regression acceptance`

Each slice must update the relevant contract, branch, activity, experiment,
bug, decision, and changelog documents required by its actual behavior. No
slice may combine a production DB migration with provider activation.

## Deferred Work

The following are explicitly outside V1.29.0 unless separately approved:

- semantic conflict adjudication and conflict lifecycle changes;
- deterministic classification of similar memories as conflicts;
- large-scale duplicate/conflict maintenance policy;
- historical activity backfill;
- multi-user authentication and data ownership migration;
- embodiment context packs and mode routing;
- removal of legacy runtime fields or legacy memory activity columns;
- removal of the deprecated GPT MCP bridge;
- prompt, provider-history, or GPT Actions transport redesign.

### Separate Duplicate And Conflict Workstream

Memory write review needs its own design after the context-packet work. The two
architectural options to evaluate are:

1. store first, then let an LLM maintenance process review duplicate/conflict
   candidates asynchronously;
2. retrieve a small candidate set during write and let Scarlet review it in
   real time before choosing write, update/supersession, deprecation, or no
   relation.

Embedding, sparse search, facts, graph links, and exact matching may generate
review candidates at scale. They must not label a semantic duplicate or
conflict by themselves. Evaluation must measure false positives, false
negatives, latency, source availability, behavior with thousands of memories,
and maintenance cost. A likely scalable design may combine bounded real-time
candidate review with asynchronous maintenance, but that is a hypothesis, not
an accepted V1.29.0 implementation.

## Acceptance Rule

The implementation is admissible only when the same frozen preliminary suite
is similar or better after activation, all V2 packet invariants pass, native
and GPT dynamic context are semantically identical, and rich system evidence
remains available outside the model packet. A regression blocks activation;
it is not waived because the new JSON is smaller.

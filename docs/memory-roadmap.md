# Memory Robustness Roadmap

Status: active planning  
Last updated: 2026-05-24

This document turns the current Memory v0 evidence, live terminal probes, and
external memory-system research into an implementation roadmap for a robust,
API-first Scarlet memory system.

For the integrated cross-project status and priority ordering, see
`docs/project-state.md`. This file remains the memory-specific roadmap.

The goal is not perfect cognition. The goal is memory that is sourceable,
auditable, correctable, and useful enough to improve measured behavior without
creating hidden state.

## 1. Current Memory Shape

Implemented today:

- `POST /mind/memory/write` through the single `mind_api` tool.
- `POST /mind/memory/search` through the single `mind_api` tool.
- `GET /mind/memory/{memory_id}` through the single `mind_api` tool.
- `GET /mind/memory/conflicts` through the single `mind_api` tool.
- `POST /mind/memory/deprecate` through the single `mind_api` tool.
- `POST /mind/memory/supersede` through the single `mind_api` tool.
- `GET /mind/memory/facts` through the single `mind_api` tool.
- `POST /mind/memory/facts/backfill` through the single `mind_api` tool.
- `GET /mind/sessions` through the single `mind_api` tool.
- `GET /mind/sessions/{session_id}` through the single `mind_api` tool.
- `POST /mind/sessions/{session_id}/summarize` through the single `mind_api` tool.
- `memories` table with source session, turn, message provenance.
- `memory_facts` table with entity, predicate, value, temporal fields,
  source provenance, lifecycle status, and fact-level supersession links.
- `session_summaries` table as the episodic recall index for chat sessions.
- `search_documents_fts` as a derived SQLite FTS5 sparse index for memory and
  session retrieval.
- `sessions.provider_history_json` as the MiniMax/Anthropic-compatible
  provider-native history used for model-facing multi-turn continuity.
- Temporal filters on `POST /mind/memory/search` and `GET /mind/sessions`,
  resolved by the backend from runtime time.
- `confidence`, `salience`, `scope`, `type`, `tags`, metadata, timestamps, and usage count.
- Dedicated traces:
  - `mind.memory.write`
  - `mind.memory.search`
  - `mind.memory.read`
  - `mind.memory.facts`
  - `mind.memory.facts.backfill`
  - `mind.memory.deprecate`
  - `mind.memory.supersede`
  - `mind.sessions.summarize`
  - `memory.conflicts`
  - `memory.context`
- Automatic Memory Context Pipeline v0:
  - every chat turn runs memory retrieval;
  - every turn emits `memory.context`;
  - selected memories enter backend-generated `<runtime_context>`;
  - near misses, exclusions, and conflicts remain visible in traces.
- Provider-native turn history:
  - completed turns persist Anthropic-compatible content blocks;
  - future provider calls use native history plus the current user message;
  - text-only history is used only as a fallback for old sessions.

Current strength:

The system is already a good experimental microscope. It proves what memory was
searched, what evidence reached the model, what the model did with it, and what
changed in persistent state.

Current weakness:

The system is not yet a robust cognitive memory. It can write, retrieve, read,
deprecate, supersede, inspect active conflicts, and extract initial atomic
facts, but it cannot yet merge duplicates, validate answers, compact sessions,
or enforce all memory-derived answer constraints. Episodic summaries are now
available as a navigation layer, but they still need live behavioral evidence:
Scarlet must prove she follows `source_session_id` into transcripts when exact
provenance matters. The current fact extractor is
deterministic and narrow by design; it covers observed Zero-Luce/SAL-style
patterns and controlled predicates, not open-ended semantic understanding.

## 2. External Pattern Analysis

Reference:

- `jrcruciani/obsidian-memory-for-ai`: `https://github.com/jrcruciani/obsidian-memory-for-ai`
- v3 atomic memory spec: `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/SPEC-v3.md`
- automation guide: `https://github.com/jrcruciani/obsidian-memory-for-ai/blob/main/automation-guide.md`
- v3 minimal vault: `https://github.com/jrcruciani/obsidian-memory-for-ai/tree/main/examples/v3-minimal-vault`

Useful ideas from that project:

- Separate raw sources, agent memory, and operating schema.
- Store atomically structured facts instead of mixing narrative notes and agent facts.
- Use controlled predicates.
- Treat `entity + predicate + time + provenance` as the durable unit of memory.
- Add bi-temporal fields:
  - when the fact is valid;
  - when the system recorded it.
- Use generated views for operational inspection.
- Run lint/health checks for contradictions, stale records, missing references, and schema drift.
- Stage writes through an inbox or operation-envelope pattern before applying canonical changes.
- Use a compaction/reflection ritual after sessions instead of only immediate in-turn writes.

What we should not copy directly:

- Markdown files as the primary source of truth.
- File-path identity as the main memory key.
- Agent-side direct file mutation as the canonical memory operation.

Why:

LLM API Mind is intentionally API/CLI-first. Our project is testing whether a
small cognitive API can become the model's external cognitive environment. The
memory system should therefore expose these ideas through `mind_api`, backend
tables, CLI commands, traces, and debug views, not as an Obsidian vault that the
model edits directly.

## 3. Design Principles For Robust Memory

### 3.1 API First

The model should still see one main tool:

```txt
mind_api(method, path, body, intent)
```

Memory internals may become richer, but the model-facing protocol should remain
small and stable.

### 3.2 Trace First

No memory read, write, revision, deprecation, merge, validation, compaction, or
background consolidation should happen without a trace or event.

### 3.3 Atomic Before Semantic Complexity

Before adding embeddings or a graph database, represent memory facts more
precisely:

```txt
entity
predicate
value
valid_from
valid_to
recorded_at
source ids
confidence
salience
status
supersedes / superseded_by
```

Dense retrieval can help later, but it cannot fix an ambiguous memory model.

### 3.4 Lifecycle Before Trust

A memory system is not robust until memories can become obsolete without being
deleted silently. Deprecation, supersession, archival, and merge operations are
required before Scarlet can safely say one version is active.

### 3.5 Runtime Obligations Beat User Formatting Requests

When runtime context contains conflicts or capability limitations, the final
answer must not hide them merely because the user requested a shorter or cleaner
format.

### 3.6 Human-Inspectable Views

The cockpit and CLI should expose current memory health:

- active conflicts;
- stale memories;
- memories by entity;
- memories by predicate;
- unresolved proposals;
- recent writes and revisions.

## 4. Known Current Limits

### 4.1 Lifecycle Coverage Is Minimal

Current memory now supports minimal deprecate/supersede/read/conflicts
operations. Missing lifecycle operations:

- archive;
- merge duplicates;
- restore;
- update through revision.

Impact:

Known direct conflicts can now be resolved without deleting history. More
complex curation still requires manual judgment or future proposal/compaction
flows.

### 4.2 Fact Extraction Is Initial And Narrow

Current `MemoryRecord` remains the human-readable source layer, while
`memory_facts` is now the stricter canonical layer. The implementation is an
initial deterministic extractor rather than a full semantic parser.

Impact:

The runtime can now formally express:

```txt
same entity
same predicate
new value supersedes old value
```

However, it can do this only for facts the extractor recognizes. Unknown or
ambiguous memories may still exist only as narrative records until M4/M5 adds
better entity detection, proposals, and compaction.

### 4.3 Sparse Retrieval Still Needs Semantic Expansion

Current retrieval now uses SQLite FTS5/BM25 plus lexical guards, tags, facts,
confidence, and salience. This is stronger than lexical v0, but it is still
sparse retrieval: synonyms, paraphrases, cross-language drift, emotional cues,
and entity ambiguity can still require facts, aliases, manual episodic search,
or future embeddings.

Observed example:

Earlier `Nebbia-Rossa` probes selected active `Zero-Luce` memories because
generic protocol terms were too strong. The FTS5 slice now reduces that class
of error, but direct behavioral probes must keep testing wrong-entity
selection before it is considered solved.

### 4.4 Answer-Control Gap

Runtime context may already know a conflict exists, but the answer can still
hide it if the user asks for source suppression or a one-line answer.

Observed example:

When `memory.context.conflicts` was non-empty for Zero-Luce, Scarlet still
answered with a single active version when asked not to cite conflicts, memory,
sources, or runtime.

### 4.5 Self-Evaluation Is Not Validation

Scarlet's self-classification can miss a runtime-evidence problem. Treat model
self-review as useful commentary, not as the validator.

### 4.6 Workaround Temptation

Before M2, Scarlet tended to suggest writing another memory as a workaround for
missing lifecycle actions. That risk should now be re-tested: basic lifecycle
exists, but proposal/compaction is still needed so future repairs do not become
ad hoc memory edits.

## 5. Target Memory Model

The current `memories` table can evolve in two possible ways:

1. Add normalized columns to `memories`.
2. Add a separate `memory_facts` table linked to `memories`.

Preferred next shape:

```txt
memories
  id
  memory_type
  scope
  status
  content
  reason_for_storage
  expected_future_use
  confidence
  salience
  source_session_id
  source_turn_id
  source_message_id
  tags_json
  metadata_json
  created_at
  updated_at
  last_used_at

memory_facts
  id
  memory_id
  entity
  predicate
  value_json
  valid_from
  valid_to
  recorded_at
  source_trace_id
  source_session_id
  source_turn_id
  confidence
  salience
  status
  supersedes_fact_id
  superseded_by_fact_id
  metadata_json
```

Reason:

Keep human-readable memory records while adding a stricter agent-facing fact
layer. This mirrors the useful separation from atomic Markdown memory systems
without adopting Markdown as the source of truth.

## 6. API Roadmap

### Phase M1 - Response-Control Guardrails

Status: hold / re-verify later.

Owner decision on 2026-05-20:

Do not treat the current answer-control observations as bugs to "fix" before
Scarlet has real conflict-management capability. This phase stays in the
roadmap, but it should be re-tested after lifecycle, atomic facts, and retrieval
guards provide stronger memory state. It may then become smaller or different
than the original plan.

Goal:

Make runtime evidence operational in final answers.

Add:

- answer obligations generated from runtime context;
- trace payload for obligations;
- lightweight response validator.

Planned internal trace:

```txt
answer.validation
```

Initial checks:

- If `memory.context.conflicts` is non-empty, the answer must acknowledge a
  conflict unless the user is explicitly asking to inspect raw data elsewhere.
- If lifecycle capabilities are unavailable, the answer must not offer update,
  delete, deprecate, consolidate, or mark-obsolete as executable actions.
- If selected memory records conflict, the answer must not declare one version
  "active" unless lifecycle state supports that claim.

Acceptance:

- Re-run the Zero-Luce source-suppression probe.
- Scarlet should refuse to hide the conflict, even in one-line mode.

### Phase M2 - Minimal Lifecycle API

Status: implemented and live-verified on 2026-05-20.

Goal:

Resolve known active conflicts without silent mutation.

Add:

```txt
POST /mind/memory/deprecate
POST /mind/memory/supersede
GET  /mind/memory/{memory_id}
GET  /mind/memory/conflicts
```

Behavior:

- Deprecation changes status, records reason, actor, and source turn.
- Supersession links old and new records.
- Conflict view lists active unresolved conflicts.
- Every lifecycle operation creates a dedicated trace.

Trace kinds:

```txt
mind.memory.deprecate
mind.memory.supersede
memory.conflicts
```

Acceptance:

- Done: the old three-block Zero-Luce memory
  `mem_abed5590f91b4eb8aa93d1103db024de` was superseded by
  `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3`.
- Done: `GET /mind/memory/conflicts` returned `count=0` after supersession.
- Done: `GET /mind/memory/mem_abed5590f91b4eb8aa93d1103db024de` returned
  `status=deprecated` with lifecycle history and `superseded_by`.

Live evidence:

- Interactive run: `backend/app/evals/runs/20260520_152457_interactive`.
- Turn `turn_3378b9eda878474ea4a3731078399029`: Scarlet used
  `/mind/schema` and `/mind/memory/conflicts`, found one active Zero-Luce
  conflict.
- Turn `turn_483560cf6e6246f98098666f153741ce`: Scarlet used
  `/mind/memory/supersede`, then `/mind/memory/conflicts`, and confirmed no
  active conflicts remained.
- Turn `turn_47c5ca7588d64403b9485316cdbc5e35`: runtime memory context used
  only the active four-block memory for Zero-Luce.
- Turn `turn_6907c41dfbf446d087f2ff9c2a25ac51`: Scarlet used
  `/mind/memory/{memory_id}` to inspect the deprecated record as history.

Observed hardening point:

Scarlet's first live supersede attempt used `target_id` plus `superseded_by`.
The API returned a structured validation error and Scarlet recovered on the next
tool call. The lifecycle parser now accepts that observed alias shape.

### Phase M3 - Atomic Fact Layer

Status: initial implementation live-verified on 2026-05-20.

Goal:

Represent stable memory as structured facts with entity and predicate.

Added:

- controlled entity slugs;
- controlled predicate registry;
- fact extraction for memory writes;
- fact inspection and traceable backfill routes;
- conflict detection by active `(entity, predicate)` facts with different values;
- fact lifecycle propagation during memory deprecate/supersede.

Initial predicates:

```txt
response_format
project_decision
user_preference
runtime_capability
communication_preference
task_constraint
correction
```

Acceptance:

- Done: Zero-Luce memories map to `entity=protocollo-zero-luce`,
  `predicate=response_format`.
- Done: `GET /mind/memory/facts` accepts multilingual aliases such as
  `Zero Light protocol` and predicate aliases such as `formato-risposta`.
- Done: `POST /mind/memory/facts/backfill` extracts facts for existing
  memories and records `mind.memory.facts.backfill`.
- Done: Memory reads/searches/context payloads include facts when available.
- Done: Conflict detection first uses active atomic facts and falls back to
  tag/token overlap only when fact conflicts are absent.
- Done: fact-level supersession links are rebuilt when backfill runs after a
  memory lifecycle operation.

Live evidence:

- Interactive run: `backend/app/evals/runs/20260520_160345_interactive`.
- Turn `turn_c0000f00f88c404d81d23c186a70a8a0`: Scarlet inspected
  `/mind/schema`, ran `/mind/memory/facts/backfill`, then queried
  `/mind/memory/facts` for `Zero Light protocol` + `response_format`. The API
  returned the active four-block fact and the deprecated three-block historical
  fact.
- Turn `turn_607560277878432d9ccc5d7dd891ae21`: Scarlet answered that
  `Zero Light protocol` and `protocollo Zero-Luce` resolve to the same active
  four-block format and treated the old three-block fact as deprecated history.

Observed hardening point:

The first live backfill happened after the M2 memory supersession. It created
the right facts but initially lacked fact-level supersession links. The backfill
flow now reconstructs those links from memory lifecycle metadata, and a traced
direct API call re-synced the lab database:

```txt
trace_511b5bcdf0f3441bb3088d5a43e52ea4
tool_fc548abb637546ea8d284d37bdb9a81d
```

### Phase M3.5 - Episodic Session Recall

Goal:

Let Scarlet reconstruct past conversations without turning entire sessions
into semantic memory.

Implemented:

```txt
GET  /mind/sessions
GET  /mind/sessions/{session_id}
POST /mind/sessions/{session_id}/summarize
```

Behavior:

- Semantic memory remains the durable reusable layer: preferences, decisions,
  corrections, facts, and stable project context.
- Episodic recall is a separate navigation and reconstruction layer:
  `session_summaries` summarize the substance of prior conversations, while
  `/mind/sessions/{session_id}` returns the exact transcript.
- Session summarization uses the complete `user`/`assistant` message history.
  It excludes tool calls, traces, and provider thinking. Last-N summarization
  is intentionally not part of the contract because it can create partial
  summaries that look fresh.
- Memory records already carry `source_session_id`; Scarlet can use that id to
  recover the conversation that produced a memory before relying on it for
  source-sensitive answers.
- Summaries include topics, decisions, open questions, and memory ids written
  from the session.
- Automatic idle maintenance now refreshes summaries after a completed turn if
  the session remains idle for the configured timer. A newer same-session turn
  supersedes the older pending job.

Acceptance:

- A memory search result with `source_session_id` should let Scarlet open the
  source transcript and distinguish memory text from exact conversation
  evidence.
- `GET /mind/sessions` should be useful as an episodic index even when some
  old sessions only have fallback summaries.
- Summaries must not become stronger evidence than transcripts.

Live evidence 2026-05-22:

- All 46 pre-existing sessions were summarized successfully; after the autonomy
  probe itself was summarized, final lab coverage was 47/47 sessions with
  summaries and 0 missing.
- Autonomy probe showed mixed behavior. Scarlet did not open the source
  transcript on the first natural "reliable baseline" question, despite a
  selected memory with `source_session_id`. On a follow-up asking whether the
  evaluation came from independent measurement or conversation, Scarlet did
  open the source session and corrected the verdict.
- This means episodic recall is operational, but provenance-following is not
  yet reliable enough to treat as solved behavior.
- Prompt mitigation was added after this evidence: Scarlet now has explicit
  epistemic confidence categories and mandatory source-session checks for
  memory-derived baseline or yes/no recommendation claims. This still needs
  live verification.
- First live rerun after prompt hardening succeeded on the key provenance
  behavior: Scarlet opened the source session on the first natural
  verified-baseline question. Keep monitoring because one positive rerun is not
  enough to call the behavior solved.

### Phase M3.6 - Session Idle Maintenance And Missed-Memory Review

Goal:

Use a real session-idle trigger for the first background memory process instead
of adding a redundant post-turn model loop to every user message.

Implemented:

- `maintenance_jobs` table for backend-owned scheduled work.
- `session.idle_maintenance` job scheduled after `turn.completed`.
- Default idle delay: `900` seconds.
- Same-session newer turns supersede or skip older pending jobs; concurrent
  sessions are independent.
- Maintenance worker runs through FastAPI lifespan.
- Idle job refreshes the episodic session summary with the existing
  `sessions.summarize` flow.
- Idle job runs missed semantic memory review, stores
  `maintenance.memory_review` traces, and creates `memory_proposals`
  for write-recommended candidates.
- V1.2.0 keeps resolution inside the same idle job: rejected candidates and
  duplicates are archived deterministically, very high-confidence create_new
  candidates can become active maintenance memories, and ambiguous candidates
  use one optional LLM resolver batch.
- Proposal inspection is maintenance-only in V1.1.1:
  `GET /api/maintenance/memory/proposals` returns bounded pages of pending
  work, and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive` removes
  handled proposals from the default queue.
- Maintenance emits `maintenance.job.*` and
  `maintenance.memory_review.completed` events for UI and inspection.
- Scarlet prompt now starts later turns with a previous-turn continuity check,
  especially for memory promises or recognized semantic candidates that were
  not actually written.

Current policy:

The missed-memory review never writes directly from raw LLM output. It creates
inspectable proposals first. Only the subsequent cautious resolution phase can
write a maintenance-created active memory, and every resolved proposal remains
in the daily ledger for future Dream review.

Next evidence needed:

- Inspect real `maintenance.memory_review` traces and pending
  `memory_proposals` after live idle sessions.
- Decide how proposals should be applied, rejected, merged, or escalated.
- Check whether prompt-level previous-turn continuity reduces repeated
  missed-memory cases before adding stronger backend enforcement.

### Phase M4 - Retrieval Quality Upgrade

Goal:

Reduce wrong-entity selected memories.

M4.0 schema/API discipline is implemented through the Cognitive API roadmap
rather than as memory-specific code. `GET /mind/schema` now carries
`schema_version`, `schema_digest`, route purposes, and schema policy; detailed
endpoint usage guides appear only on recoverable endpoint errors. Chat runtime
context includes `mind_schema`. This supports Scarlet's ability to choose memory
and cognition routes correctly before retrieval hardening continues.

Add in order:

1. Implemented: SQLite FTS5/BM25 candidate retrieval over derived search
   documents.
2. Implemented: minimal temporal search for memories and sessions.
3. Next: entity-aware relevance guard.
4. Next: better `selected` vs `near_miss` vs `excluded` thresholds from live
   evidence.
5. Optional dense retrieval only after lexical/entity behavior is stable.
6. Rank fusion only when sparse and dense retrieval both exist.

Acceptance:

- Nebbia-Rossa should not select Zero-Luce memories.
- Zero-Luce elliptical follow-ups should still select Zero-Luce when dialogue
  context makes the referent clear.
- Trace must explain why each candidate was selected, near-missed, or excluded.

### Phase M5 - Proposal Inbox And Compaction

Goal:

Separate immediate conversational writes from durable memory consolidation.

Add:

```txt
POST /mind/memory/propose
POST /mind/memory/compact
GET  /api/maintenance/memory/proposals
POST /api/maintenance/memory/proposals/{proposal_id}/archive
```

Behavior:

- A future experiment may let the model propose memory operations only if it
  needs that model-facing primitive.
- Backend validates proposals.
- Idle maintenance resolves safe reject/duplicate/create cases.
- Ambiguous cases use one optional LLM resolver batch and otherwise remain
  `pending_review`.
- Future Dream/human review inspects the daily proposal ledger before
  merge/update/deprecate behavior is added.
- Compaction can merge duplicates, suggest supersession, and flag stale records.

Acceptance:

- Scarlet can propose a memory change without immediately polluting active memory.
- A compaction run creates traceable operations and leaves unapplied proposals
  visible.

### Phase M6 - CLI And Debug Views

Goal:

Keep API/CLI as the main strength of this project.

Add CLI wrappers for:

```txt
memory list
memory show <id>
memory conflicts
memory deprecate <id>
memory supersede <old-id> <new-id>
memory lint
memory compact
```

Add cockpit views for:

- memory context per turn;
- active memories;
- conflicts;
- lifecycle history;
- proposals/inbox;
- retrieval diagnostics.

Acceptance:

- The human can inspect and resolve memory health without writing SQL.
- Every CLI action uses the same backend path or repository service as the API.

### Phase M7 - Memory Evaluation Suite

Goal:

Move memory robustness from anecdote to repeatable evidence.

Add scenarios for:

- exact recall;
- negative controls;
- conflicting updates;
- lifecycle deprecation;
- source suppression;
- wrong-entity retrieval;
- stale memory;
- cross-session continuity;
- user correction.

Acceptance:

- Scripted regression scenarios catch known failure modes.
- Adaptive live sessions remain the primary behavioral signal.
- Each evaluation records traces and human notes.

## 7. Updated Immediate Roadmap

Recommended next implementation order:

```txt
1. Live-verify episodic recall by following memory source_session_id into full transcripts.
2. Evaluate idle-maintenance missed-memory traces.
3. Directly evaluate temporal + sparse retrieval in natural Scarlet sessions.
4. Entity-aware retrieval guard from observed wrong-entity failures.
5. Proposal inbox and compaction.
6. CLI/debug memory views.
7. Broader memory eval suite.
8. Re-test response-control guardrails after lifecycle/retrieval/episodic evidence is stronger.
```

Reason:

Lifecycle resolved the actual persistent-state conflict and gave Scarlet a real
repair path. Atomic facts now give retrieval and lifecycle a canonical
entity/predicate layer. Retrieval upgrades should therefore operate on facts and
entity aliases instead of papering over ambiguous narrative memory. Response
control remains important, but the owner has parked it until the memory system
has stronger conflict-management evidence.

## 8. Non-Goals For The Next Slice

Do not add yet:

- vector database;
- graph database;
- background autonomous compaction without inspection;
- direct Markdown-vault source of truth;
- broad memory UI before lifecycle and validation semantics exist;
- large prompt rewrites as a substitute for backend constraints.

## 9. Definition Of Robust Enough

The memory system is robust enough for the next cognitive modules when:

- every turn has memory evidence or negative evidence;
- relevant memories are selected more often than not in scripted and adaptive
  checks;
- wrong-entity hits are classified as near-miss or excluded;
- conflicts are visible and cannot be hidden by formatting requests;
- stale or superseded records remain inspectable but do not pollute active
  answers;
- lifecycle changes are traceable;
- CLI/API tools can inspect and repair memory state;
- evals cover recall, absence, conflict, lifecycle, and source discipline.

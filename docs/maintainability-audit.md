# Maintainability Audit

Status: active code-organization audit. No behavioral change is authorized by
this register.

This is the single working register for verified, behavior-preserving cleanup
candidates found during the current code audit. It is not a bug ledger or a
roadmap, and its execution plan does not by itself authorize a code change.
Reassess all candidates together before authorizing any refactor.

## Audit Execution

| Phase | Scope | Status |
|---|---|---|
| 0 | Freeze baseline, worktree, database and verification boundaries. | completed 2026-08-06 |
| 1 | Inventory active consumers and examine every Core/backend area. | completed 2026-08-06 |
| 2 | Classify candidates, retained boundaries, and probable bugs. | completed 2026-08-06 |
| 3 | Reassess the full candidate set and group approved work into safe slices. | completed 2026-08-06 |
| 4 | Implement approved retirements and simplifications, one slice at a time. | completed 2026-08-06 |
| 5 | Run proportional regression verification, reconcile documentation, and report residual risk. | completed 2026-08-06 |

The audit covers backend/Core, configuration, scripts, tests, dependencies,
and the documentation that owns them. Product UI is inspected only as a
consumer of Core contracts; its design or behavior is out of scope. No live
database, VPS deployment, or camera experiment is part of this work.

## Baseline: 2026-08-06

- Branch: `experiment/tapo-c220-interactive-perception`.
- Baseline commit: `44d9f3f705d708cfaa2727e0682bb90181bf2360`
  (`fix(perception): expose real camera contract`).
- The worktree is intentionally dirty before this audit: 27 tracked files and
  11 untracked files contain pre-existing camera, provider, Android/UI, and
  documentation work. Audit changes must not absorb, revert, or release that
  work accidentally.
- Local effective `model_context_profile` is `v2`. The protected VPS database
  is production-only and remains outside all audit/testing writes; the local
  laboratory, preliminary, test, and historical SQLite files retain the roles
  in `docs/database-topology.md`.
- Initial mechanical checks pass: `git diff --check`, documentation integrity,
  project-skill validation, `ruff check`, and `mypy` (67 configured source
  files). The local backend suite also passes: `369 passed in 33.74s`, using
  its isolated test fixtures rather than the protected VPS database. This is a
  governance baseline, not a claim that unrelated uncommitted experimental
  work has passed a release suite.

## Scope And Rules

- Record only a concrete duplication, compatibility layer, or unnecessary
  abstraction confirmed in current code.
- Name the exact files and symbols, the behavior that must remain identical,
  and the focused verification required before accepting a refactor.
- Keep bugs, product ideas, algorithm changes, policy changes, and UI work in
  their owning records; link them here only when they are inseparable from a
  genuine simplification candidate.
- Use `candidate` until the owner approves a refactor. Do not silently turn a
  candidate into an implementation.
- Update an entry when new evidence changes it. Mark rejected candidates
  explicitly so the same analysis is not repeated later.

## Status Vocabulary

| Status | Meaning |
|---|---|
| `candidate` | Verified opportunity, deferred pending the full audit. |
| `retained` | Examined and intentionally kept because the responsibilities differ. |
| `implemented` | Approved behavior-preserving refactor with recorded verification. |
| `rejected` | Not a net simplification after review. |
| `probable_bug` | A concrete robustness risk found during audit; recorded for its owning bug discussion, not silently fixed by a cleanup. |

## Work Plan And Evidence Standard

The audit is deliberately split into an evidence pass and a change pass. No
candidate becomes a refactor merely because it looks aesthetically simpler.
Every entry must establish a live consumer map, a single behavioral contract,
and a proportional way to prove that the contract remained intact.

### Phase 1: Complete Inventory

1. **Runtime entry and turn flow:** ASGI/router startup, native human turns,
   autonomous turns, streaming, provider adapters, finality, errors, and
   background scheduling.
2. **Model context and cognition:** system/context composition, automatic and
   manual retrieval, memory/facts/relations, history, compaction, organs,
   shell, workspace, and maintenance.
3. **Persistence and external boundaries:** database boundary/migrations,
   repository façade and domain repositories, event/traces, API/debug routes,
   GPT bridge, research lab, camera/device experiments, and module host.
4. **Support surfaces:** configuration/environment examples, scripts and ops
   tools, test and evaluation harnesses, dependency manifests, deployment
   files, and documentation owners.

For each area, record both code found *active* and code found *inactive*. A
module is not called inactive merely because its default mode is off: a current
bounded experiment, supported route, migration, rollback, or active
configuration is a consumer that must be named.

### Phase 2: Four-Way Classification

| Category | Admission rule | Expected outcome |
|---|---|---|
| **Deprecazione** | No verified current consumer and a confirmed replacement, or an obsolete implementation whose only remaining references are stale docs/tests/configuration. | Remove executable code, stale tests/configuration, and obsolete docs in one focused slice; preserve only a short archive rationale if genuinely useful. |
| **Ottimizzabile** | Two or more paths implement the same policy or mechanical transformation, with differences expressible as explicit parameters. | Extract the smallest shared owner while retaining adapter-specific inputs, visibility, transport, and lifecycle behavior. |
| **Migliorabile** | One active implementation has avoidable indirection, a misleading façade, a monolith with separable responsibilities, or locally repeated mechanical code. | Simplify only when the resulting ownership and tests are clearer than the current code; reject cosmetic churn. |
| **Bug Probabile** | Current code has a concrete divergent edge case, unconsumed configuration, ambiguous ownership, inconsistent serialization, or a likely race/failure path. | Record in this audit and the bug ledger for a separately reasoned fix. Do not change behavior under the guise of cleanup. |

### Phase 3: Reassessment And Safe Slices

After the whole inventory, group only independent, behavior-preserving work:

1. retire verified inert configuration or code;
2. align shared mechanical helpers and public/internal ownership;
3. simplify one subsystem boundary at a time;
4. address only the probable bugs whose root cause and contract are then
   understood; and
5. make documentation, tests, and configuration retirements in the same slice
   as their code.

Every slice must declare its area, target files, out-of-scope behavior,
invariants, focused tests, and whether a read-only deployment configuration
check is required. Existing dirty camera/UI/provider work stays excluded unless
the owner explicitly makes it part of a slice.

### Phase 4: Final Verification

Run focused tests after every accepted slice, then the complete isolated
backend suite and static/documentation checks after the final slice. Compare
event payloads, model context, persistence, terminal behavior, and public
contracts where the changed boundary reaches them. A live Scarlet evaluation
is an explicit owner decision, not an automatic cleanup test.

## Inventory Findings: Shared Runtime Helpers

### Retained Boundary

`backend/app/runtime/maintenance.py` is an intentional stable façade, not dead
code. Native turns, the chat and maintenance APIs, and the GPT bridge import it
as the shared maintenance entry point while scheduling, history work, memory
review, and shared types live in focused submodules. Removing it would fan
internal implementation imports through several boundaries without eliminating
behavior.

### Candidates And Risks

| ID | Status | Evidence | Next assessment / required verification |
|---|---|---|---|
| MNT-011 | probable_bug | `endogenous_cognition._device_context_family()` recognizes only `notifications`; `cognitive_workspace._perception_context_family()` additionally recognizes calendar/messages/email, wellbeing, and camera/audio/video. The current `device_perception_adapter` emits only channels on which both mappings agree, so no current misclassification is demonstrated. A future admitted channel can nevertheless receive a different family depending on which path observes it. | Design one owned classifier only after the full device/perception inventory; test each admitted channel through adapter, endogenous ingestion, and workspace arbitration. No change during this audit. |
| MNT-012 | probable_bug | `endogenous_cognition` and `cognitive_workspace` separately serialize provider results and parse timestamps. Their payload shape is currently equivalent where both apply, but one parser normalizes aware times to UTC and the other preserves a supplied offset. Current system emitters use UTC, so present behavior agrees; a future non-UTC source can diverge in ordering, retry, or source metadata. | Inventory timestamp/source contracts and decide an explicit canonical helper with backwards-compatible trace expectations. Test UTC, `Z`, offset-aware, and naive inputs before any refactor. |
| MNT-013 | implemented | `history_compaction.py` and `context_accounting.py` use the same ceiling token estimate; `history_runtime.py` repeats it with a defensive minimum divisor. Configuration validates the shared ratio at `>= 1.0`, so the present runtime semantics agree. | Implemented as `runtime.token_estimation.estimate_tokens()`, preserving the history runtime's explicit one-character lower bound. Focused compaction and context-accounting tests passed. |

## 2026-08-05: Turn Lifecycle

### Retained Boundary

**Human and autonomous execution adapters** (`backend/app/api/chat_native_turn.py`,
`backend/app/runtime/autonomy.py`) are intentionally separate after turn
preparation. The native adapter owns HTTP/SSE construction and public event
projection; the autonomy adapter owns private cognitive events, activation
lifecycle, and scheduling outcomes. Both already use the shared kernel in
`backend/app/runtime/turn_kernel.py` for preparation, completion, failure
recording, context/retrieval, history, accounting, persistence, and
compaction scheduling. A generic executor would merge distinct transport and
lifecycle responsibilities without reducing meaningful behavior.

### Candidates

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-001 | implemented | `NativeTurnPreparation` in `chat_native_turn.py` mirrored values already held by its kernel. | The preparation now retains only native adapter fields and exposes kernel-owned values through explicit properties. | Focused native, autonomous, and V2-context tests passed. |
| MNT-002 | implemented | `_require_native_end_turn` was an adapter-local compatibility alias over the shared terminal-response check. | Native code now calls the shared finality helper directly; no semantic fallback or validator exists. | Focused terminal/failure-path tests passed. |
| MNT-003 | implemented | `compose_system_with_runtime_context` was a compatibility re-export used by the GPT bridge. | The bridge now imports the common owner directly. | Native/GPT context-composition tests passed. |
| MNT-004 | implemented | GPT bootstrap repeated the kernel's context-build event projection. | `runtime.context_events.record_context_build_events()` now owns the exact event projection with visibility as an explicit adapter input. | Native, autonomous, and GPT context tests passed. |

## 2026-08-05: Automatic Context

### Retained Boundary

**Retrieval dialogue preparation** remains adapter-specific but feeds one
shared retrieval implementation. Human turns provide the active session's
recent dialogue. Autonomous turns provide the last messages of the two latest
human sessions plus recent autonomous assistant checkpoints, labelled with
their source origin, then call the same `prepare_model_turn()` and
`build_automatic_memory_retrieval()` path. Collapsing these source selections
would make autonomous continuity weaker or hide its provenance; it would not
remove a duplicate algorithm.

The GPT bridge uses the same `build_memory_context()` and
`compile_model_context_v2_with_audit()` implementation as native turns. Its
only verified context-path duplication is the event projection already tracked
as MNT-004; no second compiler or bridge-specific packet exists.

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-005 | implemented | Local and read-only protected-VPS configuration both used V2; legacy delivery modes had no current consumer. The rich `runtime-context-v1` remains trace/event evidence and a source for V2 preserved-organ projection. | Retired the selectable legacy model-delivery branch and configuration. V2 is now the sole model-facing compiler path. | V2 context, native, autonomy, GPT bridge, and evaluation tests passed. |

## 2026-08-06: Configuration Surface

### Candidates

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-006 | implemented | `history_compaction_recent_turns` had no runtime reader and the active selector is token-based. | Retired from Settings, example environment, test fixtures, and current context documentation. | Focused compaction/accounting tests passed. |
| MNT-007 | implemented | The dense-score and hand-authored hybrid-weight settings had no runtime reader; final selection is reranker-owned. | Retired the eight inactive settings and example variables. | Focused automatic/manual retrieval tests passed. |
| MNT-008 | implemented | The perception channel limit and `log_level` settings had no runtime reader. | Retired both inactive settings and example variables rather than inventing a behavior change. | Autonomous scheduling and startup tests passed. |

### Retained Boundary

`organ_temporal_experience_mode` and `organ_dream_mode` are not residual
settings: `backend/app/mind/organs.py` resolves both through the active organ
registry. Their current `off` defaults are a product/runtime choice, not proof
that their configuration contract is dead.

## 2026-08-06: Context And Memory Retrieval

### Retained Boundaries

- The rich V1 runtime packet remains live trace/audit evidence and input to
  the V2 projection. It is not model-delivery code merely because V2 is the
  active model-facing profile; only the legacy rendering branch is tracked in
  `MNT-005`.
- `context_families.py` is used by V2 projection audit and the Cognitive
  Workspace signal/candidate contracts. Its routing is deliberately
  classification/shadow-only at this point; that is an active experimental
  boundary, not unused code.
- Automatic and manual memory recall use the same evidence collection,
  route-balanced recall pool, and final reranker. Their local pre-rerank
  selection differs intentionally: automatic retrieval protects model context;
  manual search supports explicit filters and broader inspection.
- The local effective configuration has `retrieval_shadow_enabled=true`,
  `retrieval_shadow_backend=openrouter`, and `retrieval_hybrid_mode=active`.
  The optional surface backends, including Milvus Lite, therefore retain a
  documented experiment consumer even when a particular backend is not
  selected. The active mode and threshold settings are not cleanup candidates.

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-009 | implemented | Memory handlers consumed sibling-private helpers despite shared ownership. | `memory_shared.py` now exposes named shared scoring/fact helpers while ranking and lifecycle policy remain local. | Focused memory search, proposal, relation, lifecycle, and backfill tests passed. |

## 2026-08-06: Mind Organs And Handler Ownership

### Retained Boundaries

- `memory.py` is a live public façade over memory read/write/lifecycle,
  relations, and proposal handlers. Dispatcher, maintenance API, and tests use
  it as the stable memory surface; the focused files behind it are not
  duplicate implementations.
- Automatic context retrieval and explicit `memory search` share evidence
  collection, route-balanced pool construction, and final reranking in
  `memory_recall.py`, while retaining different query construction, filters,
  fallback ranking, activity writes, and output contracts. This is the desired
  separation between automatic context protection and manual inspection.
- The V2 context compiler is divided by projection responsibility
  (`context_sessions`, `context_memories`, `context_preserved`, provenance,
  contracts). The rich packet in `context.py` remains its trace/projection
  input as described in MNT-005; it is not a second active model context.
- The two OpenRouter rerank decoders are deliberately not merged: the active
  final reranker accepts both `results` and `data`, whereas the shadow
  diagnostic contract accepts only `results`. The exact vector coercion is too
  small to justify coupling generic cache validation to the OpenRouter client.

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-018 | implemented | Focus, volition, and affect repeated owner-profile lookup and an equivalent error envelope. | `mind.organ_support` now owns only those mechanics; each organ retains its own policy, state, event, and payload behavior. | Focus, volition, affect context/API/shell tests passed. |

## 2026-08-06: Mind Shell And Internal HTTP Dispatcher

### Retained Boundary

The model-facing contract remains one `mind_shell(command, intent)` tool.
`shell.py` parses and translates commands; `shell_presentation.py` compacts
results; the internal `/mind/*` dispatcher executes established handlers and
remains the supported debug, maintenance, API, and test boundary. The large
HTTP schema catalog is not a duplicate model tool: it supplies that internal
contract, usage guides, route matching, and structured recovery. It must be
reassessed only if that internal boundary is deliberately retired.

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-010 | implemented | Registry validation repeated the shell grammar. | It now consumes the parser's command representation and retains only registry-specific availability/input checks. | Shell parser/registry and Mind shell tests passed. |

## 2026-08-06: API Entrypoints And Streaming

### Retained Boundaries

- `/turn/stream-live` is the active Product UI transport. It combines durable
  `scarlet-stream-v2` events with connection-local thinking/text/tool-input
  frames, then the client resumes through the durable V2 cursor after a
  disconnect.
- `/turn/stream-v2` and its resume route deliberately expose durable events
  only. They are the replay/recovery path, not a redundant variant of live
  streaming.
- `/turn/stream` remains a documented native NDJSON contract and is used by
  the isolated behavioral/evaluation harnesses. Its lack of a current Product
  UI consumer is insufficient evidence to remove a supported API boundary.

### Candidates And Risks

| ID | Status | Evidence | Next assessment / required verification |
|---|---|---|---|
| MNT-014 | implemented | `stream_v2_from_native_lines()` had no import, route, or test consumer. | Removed the unexported compatibility helper; V2 remains detached-runner plus persisted-event replay. | Stream V2/replay/live tests passed. |
| MNT-015 | probable_bug | `chat_turn_runner._consume_native_turn()` catches `BaseException` around the detached generator. That also captures process-control exceptions such as `KeyboardInterrupt` and `SystemExit`, although its documented purpose is ordinary runner-failure terminalization. | Establish desired cancellation semantics, then narrow the catch only with tests for ordinary provider failure, cancellation, completion sink execution, and a turn not left `started`. |

## 2026-08-06: Providers, Module Preparation, And Bounded Experiments

### Retained Boundaries

- `MiniMaxProvider` and `QwenProvider` are thin provider-specific
  configurations over the same Anthropic-compatible implementation. This is
  useful inheritance, not duplicated provider logic.
- The auxiliary provider factory is the explicit M2.7 boundary for supporting
  LLM work; Scarlet's native M3 turn factory remains separate. The distinction
  is behavioral and cost-related, so it must not be collapsed into a generic
  settings mutation.
- `backend/app/agentic_modules/` and `backend/scarlet_agentic_module_sdk/` are
  V2 preparation, not a hidden second Core. They provide a tested, opt-in
  approved-root subprocess host and SDK; no installed product module is wired
  into `create_app()` or the native turn path. Their current owner and V3
  boundary are documented in `docs/core-runtime-contract.md` and
  `docs/agentic-modules-contract.md`.
- The uncommitted MiniMax Responses/video-call implementation and its Android
  counterpart are an explicitly excluded camera experiment. They must be
  assessed with their own acceptance evidence after the current worktree is
  stabilized, not retired or refactored opportunistically here.

No retirement candidate is recorded in this area yet. The next inventory pass
will inspect the module SDK packaging, test fixtures, and dependency manifests
for a real unconsumed compatibility surface rather than treating preparation
code as dead by default.

## 2026-08-06: Persistence And Database Ownership

### Retained Boundaries

- `storage/repositories.py` is a live stable façade. Runtime callers import it
  while focused `storage/repository/*` modules own transactions by domain. The
  façade prevents every API, organ, and runtime module from coupling directly
  to the physical repository layout.
- `database_boundary.py` owns selection of production, laboratory, test, and
  preliminary roles. `db.py` owns engine setup, isolated test-copy preparation,
  and incremental SQLite schema compatibility. These are distinct safety
  responsibilities, not duplicate database wrappers.
- SQLite remains the current canonical store; FTS, memory surfaces, vectors,
  graph rows, compactions, and workspace records are derived or indexed views
  with documented ownership. No audit evidence supports treating one of them
  as an alternative canonical database.

No code retirement candidate is recorded in persistence. The inventory did
confirm one non-runtime residue documented in `database-topology.md`: the old
ignored root-level `data/app.db` is not selected by configuration. It is an
environment-cleanup question, not an executable-code deletion; do not remove
or inspect its data under this audit without a separate owner decision.

## 2026-08-06: Research Lab, Operations, And Evaluation Support

### Retained Boundaries

- Research Lab has one explicit shell entry, one bounded public-web reader,
  one separately deployed network-disabled Python runner, persisted
  source/run/artifact receipts, and a dashboard inspection surface. It is
  opt-in but has active model, API, storage, deployment, and test consumers;
  it is not an automatic memory/context path.
- `database_preflight.py` is the current read-only operational guard. The
  behavioral suites, frozen baseline, preliminary regression, and calibration
  programs are separately named evaluation surfaces. Their different input
  databases and acceptance purposes are intentional, not interchangeable
  duplicate tests.
- `reset_autonomous_chronology.py` remains an owner-authorized archival
  operation: it preserves canonical evidence and creates a new autonomous
  lineage. Its retention must be reviewed as an operational contract, not as
  a generic cleanup.

### Candidates And Risks

| ID | Status | Evidence | Next assessment / required verification |
|---|---|---|---|
| MNT-016 | implemented | The guarded one-time command had no runtime importer and BUG-0135 records completed production reconciliation of its exact 39 rows. A later ad-hoc read-only scan was stopped because its unrestricted historical event scan was inappropriately expensive on the protected database. | Removed the completed operation and its dedicated test; BUG-0135 remains the concise completion evidence. | Workspace/autonomy/maintenance tests passed; no production mutation occurred. |
| MNT-017 | probable_bug | `reset_autonomous_chronology.py` and one API-contract paragraph require an absolute `backup_reference`, but the current VPS policy explicitly says persistent backups are not retained. The command only checks that the path is absolute, so the field cannot presently prove the protection it claims to represent. | Separately redesign the owner-authorized reset guard around the current no-backup policy, with an explicit archival/integrity precondition and focused operation tests. Do not change the reset behavior in this audit. |

## 2026-08-06: Exact Duplications And Large Orchestrators

### Candidates

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-019 | implemented | Two calibrators contained byte-equivalent SHA-256 code. | `evals.file_hashing.sha256_file()` is now their neutral shared owner. | Calibration tests passed. |
| MNT-020 | implemented | Module registry and validation contained byte-equivalent duplicate detection. | `agentic_modules.support.duplicate_values()` now owns that neutral collection mechanic. | Registry, validation, host, and SDK conformance tests passed. |
| MNT-021 | implemented | Native and GPT routes had equivalent missing-session guards. | `api.session_guards.require_chat_session()` now owns the shared typed 404 boundary. | Native chat and GPT bridge tests passed. |
| MNT-022 | implemented | The autonomous adapter combined scheduler-adjacent gates, turn setup, provider streaming, completion, and failure handling in one 534-line function. | Public scheduling remains in `runtime.autonomy`; `autonomy_activation` owns explicit claim, preparation, streaming, completion, and failure stages, while `autonomy_support` owns shared private mechanics. | 40 autonomy/scheduler/workspace/endogenous/maintenance tests passed, including completed, deferred, yielded, and failed paths. |

### Retained Boundaries

- `runtime/cognitive_workspace.py` is large, but its public tick and named
  ingestion, appraisal, arbitration, deferral, ignition, and watchdog stages
  map directly to the Cognitive Workspace contract. File size alone is not
  evidence that splitting it would simplify the system. Reassess only if a
  later slice exposes an actual shared transaction or serialization policy.
- `mind/shell.py` is a single model-facing translation boundary. Its per-family
  functions are already separated inside the file; splitting families now
  would fan shell parsing and presentation dependencies across additional
  modules without removing a duplicated policy.
- `storage/models.py` is the declarative SQLModel catalogue. Its size follows
  the number of persisted entities, while database ownership is already split
  in `storage/repository/*`; no model split is proposed.

## 2026-08-06: Documentation Navigation

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-023 | implemented | The current documentation map and AGENTS protocol now route routine work to concise owners instead of requiring wholesale reading of append-only ledgers. | Historical evidence stays searchable, while prompt snapshots are explicitly identified as archive-only. | Documentation integrity and project-skill checks passed. |

## 2026-08-06: Retired Answer-Obligation Evaluation Residue

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-024 | implemented | The old answer-obligation branch existed only in controlled evaluators; current runtime has no semantic answer validator. | Removed unreachable evaluator branches and their direct legacy assertion. | Focused evaluator tests passed and search confirms no executable semantic-validator producer remains. |

## 2026-08-06: Prompt History Placement

### Candidate

| ID | Status | Evidence | Minimal possible simplification | Behavior that must remain identical | Required verification |
|---|---|---|---|---|---|
| MNT-025 | implemented | Thirteen historical prompt snapshots had no resolver consumer but were linked by historical evidence. | Moved them from the executable package to `docs/archive/prompt-history/` with an archive contract and migrated links. | Prompt-resolution, documentation integrity, and targeted link checks passed. |

## 2026-08-06: Retrieval Observability

### Probable Bug

| ID | Status | Evidence | Next assessment / required verification |
|---|---|---|---|
| MNT-026 | probable_bug | `mind.search.search_documents()` and `_document_counts()` catch every SQLite/FTS exception and return an empty result/count without a trace, structured status, or log. The higher recall pipeline can continue through lexical/other evidence, but a broken FTS table is indistinguishable from no sparse match and may silently lower automatic or manual recall quality. | Specify an observable fallback contract that preserves successful-query outputs and existing retrieval fallback. Test an unavailable/corrupt FTS surface, a normal empty query, and a genuine no-match; do not turn this into a semantic ranking change. |

## Inventory Coverage And Implementation Order

### Completed Inventory Coverage

The evidence pass examined the 155 backend application files, the standalone
SDK source, executable operations and evaluators, 56 test modules, the
configuration/environment surface, dependency and container manifests, and 83
tracked Markdown documents. `main.py`/ASGI routes, provider factories,
prompts, native and bridge adapters, model context, memory/retrieval, shell,
organs, workspace/autonomy, maintenance, persistence, Research Lab, agentic
module preparation, operations, scripts, and evaluation entry points were
mapped to their consumers.

The isolated camera/video and Android/UI work already present in the dirty
worktree was only checked as an explicit experiment boundary. It is neither
included in a Core cleanup slice nor evidence for retiring active Core code.

### Recommended Execution Slices

| Slice | Candidate IDs | Scope | Preconditions and invariant |
|---|---|---|---|
| A. Inert surface retirement | MNT-006, MNT-007, MNT-008, MNT-024 | Remove only settings, example variables, test-fixture keys, and controlled-evaluator branches with no runtime reader. | First read deployed environment names without changing it. Preserve token compaction, active final reranking, scheduling, logging, and evaluator outcomes. |
| B. Retired internal helper | MNT-014 | Remove the uncalled Stream V2 legacy-line adapter. | Reconfirm no supported external Python consumer; preserve V2 replay and live delivery contracts. |
| C. Mechanical shared ownership | MNT-001, MNT-002, MNT-003, MNT-004, MNT-009, MNT-010, MNT-013, MNT-018, MNT-021 | Move only exact or clearly shared mechanics to named internal owners. | One independent sub-slice at a time; compare event sequences, model context, errors, shell parsing, and persistence for the affected boundary. |
| D. Tiny-duplication decision | MNT-019, MNT-020 | Decide explicitly whether a neutral utility improves readability over two local helpers. | Reject rather than add a file if the dependency cost exceeds the seven-to-nine-line duplication removed. |
| E. Autonomous adapter readability | MNT-022 | Extract private stages from the autonomous adapter while retaining it as the unique autonomous orchestrator over the shared kernel. | Treat as a high-risk refactor: no scheduler, workspace, prompt, retrieval, finality, or event-policy change. Requires focused lifecycle event comparison. |
| F. Conditional legacy retirement | MNT-005, MNT-016, MNT-025 | Retire old V1 model-delivery compatibility, the one-time candidate parking operation, and executable-directory prompt backups only when their external/history conditions are proven. | Respect deployment compatibility, read production only when separately authorized, and migrate/retain historical documentation links before deletion. |
| G. Documentation navigation | MNT-023 plus documentation portions of A/F | Make current sources concise and route history through the documentation map. | Preserve all decision, experiment, bug, and checkpoint provenance; no content loss or rewriting of historical claims. |
| H. Separate robustness investigations | MNT-011, MNT-012, MNT-015, MNT-017, MNT-026 | Investigate concrete divergence/failure paths as future bug work. | These are not cleanup changes and must not be bundled into any behavior-preserving slice. |

The recommended order is A, B, C one sub-slice at a time, D, E, F, G, then H
as separately approved bug work. Run focused tests after each sub-slice; run
the full isolated suite, static checks, and documentation checks after all
accepted slices. A direct live Scarlet evaluation or VPS deployment is never
automatic for this cleanup programme.

## Implementation Results: 2026-08-06

Approved behavior-preserving slices A-G are complete. The runnable tree no
longer carries the verified inactive configuration, evaluator branches,
legacy model-delivery modes, one-time completed migration, unused stream
helper, or prompt history under the runtime package. Shared mechanics now have
small named owners, and the autonomous adapter is divided by lifecycle stage
without creating a second turn kernel.

The following items remain intentionally open as separate robustness work:
`MNT-011` context-family ownership, `MNT-012` timestamp normalization,
`MNT-015` runner cancellation semantics, `MNT-017` reset protection under the
no-backup VPS policy, and `MNT-026` observable FTS failure handling. None was
changed during this cleanup because each requires a distinct behavioral
contract and targeted evidence.

Final verification passed: focused checks after every slice; full isolated
backend suite (`368 passed in 34.25s`); `ruff`; configured `mypy` (67 source
files); documentation integrity; project-skill validation; public autonomy
import smoke; and `git diff --check`. No live Scarlet session, VPS deployment,
or database mutation was part of this audit.

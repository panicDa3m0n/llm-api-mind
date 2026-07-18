# Monolith Rework Plan

Date: 2026-07-18
Status: accepted execution map from SCA-10; SCA-22 and SCA-33 through SCA-38 verified
Runtime baseline: V1.43.0 deployed; V1.49.1 candidate after SCA-42
Planning baseline: preliminary regression 9/9 in
`20260718_162024_preliminary-regression-v1`; unchanged post-documentation gate
9/9 in `20260718_162350_preliminary-regression-v1`

## Purpose

This plan converts the broad instruction to reorganize the largest modules
into bounded implementation issues. File size is evidence of concentration,
not proof that a module is wrongly designed. A slice is justified only when it
separates a real contract or lifecycle, reduces coupling, and can preserve the
same externally observable behavior behind a stable facade.

SCA-10 changes no runtime behavior. It defines the order, boundaries, and
acceptance gate for the later code moves. Every execution issue must declare
its own version, run the frozen gate before and after, and be accepted
independently.

## Current Inventory

The initial counts were measured from the V1.42-based worktree on 2026-07-18;
completed rows now show their post-slice values. They are orientation values,
not permanent thresholds.

| Surface | Lines | Concentrated responsibilities | Main consumers | Blast radius |
|---|---:|---|---|---|
| `backend/app/mind/memory.py` | 38 after SCA-38 | compatibility facade for all memory commands | dispatcher, maintenance, maintenance API, shell tests, preliminary gate | high: stable import contract |
| `backend/app/mind/memory_read.py` | 996 | search/read/facts/graph contracts, ranking, temporal filters, graph navigation, presentation | memory facade, dispatcher, shell tests, preliminary gate | high: manual cognition and evidence |
| `backend/app/mind/memory_write.py` | 616 | write contracts/policy, exact dedup, facts and backfill | facade, lifecycle, proposals, dispatcher | very high: semantic persistence |
| `backend/app/mind/memory_lifecycle.py` | 462 | deprecate/supersede and fact lifecycle propagation | facade, dispatcher | very high: semantic state mutation |
| `backend/app/mind/memory_proposals.py` | 555 | maintenance proposal preflight, ledger payload and apply | facade, maintenance runtime/API | high: background semantic candidates |
| `backend/app/mind/memory_relations.py` | 274 | atomic conflicts and maintenance overlap evidence | facade, dispatcher | high: evidence authority |
| `backend/app/mind/memory_shared.py` | 152 | shared fields, payload, normalization, traced errors, activity recording | read and mutation handlers | high: cross-memory contract |
| `backend/app/api/chat.py` | 218 after SCA-33 | HTTP/debug router registration, request facade, native-service mapping | app factory, chat tests | high: every native HTTP turn |
| `backend/app/api/chat_native_turn.py` | 1,638 | shared native preflight/completion, sync/stream execution, shell runner, answer obligations | chat facade, GPT context composer, chat tests | very high: every native model turn |
| `backend/app/plugins/gpt_bridge/router.py` | 1,509 | GPT Action lifecycle, compact context, auth, answer validation | app factory, bridge tests, Custom GPT | high: external transport and continuity |
| `backend/app/mind/schema.py` | 1,870 | declarative capability and schema contracts | mind runtime, help, tests | medium: broad imports, but low operational mixing |
| `backend/app/mind/context.py` | 1,161 after SCA-35 | runtime assembly, compatibility rendering, block construction, temporal context | native chat, GPT bridge, organ tests, preliminary gate | very high: model evidence delivery |
| `backend/app/mind/context_retrieval.py` | 731 | automatic candidate pooling, ranking, classification, final rerank, negative evidence | context facade, retrieval tests, preliminary gate | high: automatic memory evidence |
| `backend/app/runtime/maintenance_memory.py` | 746 after SCA-37 | memory review and proposal resolution | scheduler, proposal/memory owners, maintenance tests | high: background semantic mutation |
| `backend/app/runtime/maintenance_scheduler.py` | 468 after SCA-37 | schedules, dispatch, worker and job completion | app lifecycle, chat, maintenance API/tests | high: background lifecycle authority |
| `backend/app/runtime/maintenance_history.py` | 200 after SCA-37 | summary audit/repair, idle summary and history compaction | scheduler, episodic/history runtime, tests | high: episodic continuity |
| `backend/app/runtime/maintenance.py` | 18 after SCA-37 | stable public facade | app lifecycle, chat, bridge, maintenance API/tests | low: compatibility only |
| `frontend/src/App.tsx` | 4,474 | developer shell/state, chat flow, trace/model inspector, memory/events/settings panels, normalizers | desktop developer UI | medium: inspection and developer workflows |
| `frontend/src/MobileApp.tsx` | 1,766 | mobile controller, chat/memory/actions/profile screens, activity state, flow normalization | consumer mobile UI | medium: user-facing conversation |

Large evaluation runners and test modules are not first-wave targets. Their
size often reflects explicit scenario catalogs. Split them only when a shared
fixture or evaluator contract becomes independently reusable.

## Stable Facades

Later modules may move implementation, but these boundaries stay stable during
each slice unless a separate issue explicitly changes their contract:

- `app.mind.context.build_memory_context` and
  `build_runtime_context_payload`;
- all handler and body names imported from `app.mind.memory` by the dispatcher,
  maintenance, APIs, and tests;
- `app.api.chat.build_chat_router` and `build_trace_router`;
- `app.plugins.gpt_bridge.build_gpt_bridge_router` and the published
  bootstrap/action/finalize OpenAPI contract;
- maintenance scheduler, worker, audit, and job-runner imports;
- frontend API calls and the top-level `App` and `MobileApp` exports.

A compatibility facade should re-export the moved names. New callers must
import the owning module once the slice is stable; existing callers are not
rewritten en masse merely to make the facade disappear.

## Execution Slices

### 0. Remove Deprecated MCP Before GPT Refactoring

Issue: SCA-22.

Completed in the V1.43.0 candidate. The MCP-only route, descriptors, dispatch,
lifecycle, result formatting, prompt, and query-key authentication are removed.
SCA-22 still precedes SCA-39 and closes only after proving that GPT Actions,
native shell use, internal endpoint dispatch, and historical database evidence
remain intact in production.

### 1. Chat Support Extraction

Issue: SCA-34.

Completed in the V1.44.0 candidate. Provider-history conversion now lives in
`chat_provider_history.py`, response/event models and projections in
`chat_serialization.py`, and context-accounting persistence/statistics in
`chat_accounting.py`. `chat.py` remains the stable facade for its public
response models and owns turn orchestration. The GPT bridge imports the owning
support modules instead of private router helpers. Exact OpenAPI JSON, frozen
9/9 pre/post behavior, focused contracts, and a same-session native MiniMax
continuity probe were preserved.

### 2. Native Turn Orchestration

Issue: SCA-33, completed in the V1.45.0 candidate.

Native preflight, execution, failure, completion, and scheduling now live in
`chat_native_turn.py`; `build_chat_router` is a thin HTTP facade. Tool-loop
order, thinking-only recovery, answer obligations, canonical provider history,
and transport differences are preserved. Frozen pre/post gates pass 9/9,
OpenAPI is equal, and a directly inspected sync-to-stream MiniMax probe
preserved continuity. The extraction also fixed BUG-0092, where stream created
but did not link its model-context trace.

### 3. Context Retrieval Separation

Issue: SCA-35, completed in the V1.46.0 candidate.

Candidate pooling, ranking, classification, final-rerank projection, conflicts,
and negative evidence now live in typed `context_retrieval.py`. Runtime block
assembly and public builders remain in `context.py`, reduced from 1,809 to
1,161 lines. Frozen pre/post gates pass 9/9 and focused contracts pass 101/101.
Direct inspection also separated rich selection from V2 delivery and opened
SCA-43 for the historical gate's incomplete-provenance blind spot; retrieval
policy itself did not change.

### 4. Memory Read Surface

Issue: SCA-36, completed in the V1.47.0 candidate.

Search, read, facts, graph, their request contracts, ranking, temporal filters,
graph traversal, and presentation now live in `memory_read.py`; minimal shared
contracts live in `memory_shared.py`. `memory.py` remains the compatible facade
and decreases from 2,921 to 1,938 lines. Frozen pre/post gates pass 9/9,
focused contracts pass 63/63, and direct shell inspection preserved content,
provenance, facts, graph topology, and all four trace kinds.

### 5. Memory Mutation And Evidence

Issue: SCA-38, completed in the V1.48.0 candidate.

Write/fact materialization, deprecate/supersede lifecycle, maintenance
proposals, and relation/conflict evidence now have dedicated owners behind the
38-line `memory.py` facade. Similarity remains evidence rather than
deterministic truth, and no auto-merge or auto-deprecation was introduced.
Frozen pre/post gates pass 9/9; focused contracts pass 70/70; direct shell,
proposal, and natural Scarlet probes preserve mutation semantics and behavior.

### 6. Maintenance Domains

Issue: SCA-37, completed in the V1.49.0 candidate.

Scheduler/dispatcher, summary-history work, and memory-review/proposal
resolution now have dedicated typed owners behind the 18-line maintenance
facade. Job kinds, persisted status, idempotency, retry behavior, idle checks,
prompts, auto-apply guards, and the single worker surface are preserved. Frozen
pre/post gates pass 9/9, focused contracts pass 32/32, and direct compaction
plus natural MiniMax maintenance probes preserve technical and semantic
behavior.

### 7. GPT Actions Router

Issue: SCA-39, blocked by SCA-22.

After MCP removal, separate request/response schemas, bridge lifecycle,
compact-context projection, authentication, and answer validation. Preserve
the exact Action operation IDs and bootstrap/action/finalize state machine.
Native and GPT must continue to share the context compiler and shell
dispatcher rather than developing transport-specific cognition.

### 8. Developer Cockpit

Issue: SCA-40.

Split `App.tsx` by visible responsibility: application controller, conversation
flow, model/context inspector, memory/events, settings/profile, and pure trace
normalizers. Do not redesign the interface or duplicate parsing in individual
components.

### 9. Mobile Consumer Flow

Issue: SCA-41.

Split `MobileApp.tsx` into controller, chat, memory, actions, profile, input and
navigation, with pure flow/activity normalizers. Preserve the current consumer
experience; onboarding, authentication, and new user flows belong to their own
issues.

## Deliberate Deferrals

- `mind/schema.py` stays intact for now. It is large but primarily declarative,
  and a mechanical split could replace one discoverable catalog with circular
  imports. Reassess only after consumer/import pressure is measured.
- Evaluators and broad tests are not split merely to reduce line counts.
- No database model or migration is required by any organizational slice.
- No prompt, memory policy, agent mode, organ behavior, or API response may be
  changed as an incidental cleanup.
- No all-at-once branch is authorized. Each issue is independently reversible.

## Mandatory Gate Per Slice

Before implementation:

1. start from current `main` and declare area, branch, type, version, scope,
   exclusions, verification, and documentation;
2. record current line count, public imports, top-level responsibilities, and
   the exact facade to preserve;
3. run `preliminary-regression-v1` against its immutable source and record the
   9/9 report path;
4. run the focused tests for the affected contract.

After implementation:

1. rerun the identical focused tests and frozen 9/9 gate from a fresh copy;
2. run the full backend quality suite or frontend build/browser verification,
   as applicable;
3. directly exercise the affected shell, chat, bridge, maintenance, or UI
   surface on an isolated database/runtime;
4. compare public payloads, trace order, state mutation, and source database
   hash where relevant;
5. classify failures as implementation regression, evaluator defect,
   stochastic provider behavior, or unrelated pre-existing issue;
6. merge only with equal or better objective behavior and documented residual
   risk.

Complete multi-scenario live Scarlet campaigns are not automatic. A bounded
direct Scarlet smoke is used when the slice changes an agent-facing runtime;
the owner explicitly authorizes broader live evaluation periods.

## Completion Meaning

SCA-10 is complete when this inventory, ordering, stable-facade rule, and the
nine executable child issues exist and agree with the current code. It does
not claim that the monoliths have already been split. Completion of the rework
itself is the cumulative result of SCA-22 and SCA-33 through SCA-41 passing
their own gates.

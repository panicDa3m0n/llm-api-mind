# Monolith Rework Plan

Date: 2026-07-18
Status: accepted execution map from SCA-10; SCA-22 completed and deployed
Runtime baseline: V1.43.0 deployed
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

The counts below were measured from the current V1.42-based worktree on
2026-07-18. They are orientation values, not permanent thresholds.

| Surface | Lines | Concentrated responsibilities | Main consumers | Blast radius |
|---|---:|---|---|---|
| `backend/app/mind/memory.py` | 2,921 | command bodies, read/search, facts, graph, write policy, lifecycle, proposals, relation evidence, payloads | dispatcher, maintenance, maintenance API, shell tests, preliminary gate | very high: semantic state and lifecycle |
| `backend/app/api/chat.py` | 2,641 | HTTP models/router, sync and stream turn loops, shell runner, answer obligations, provider history, traces, accounting, response serialization | app factory, GPT bridge, chat tests | very high: every native turn |
| `backend/app/plugins/gpt_bridge/router.py` | 1,506 | GPT Action lifecycle, compact context, auth, answer validation | app factory, bridge tests, Custom GPT | high: external transport and continuity |
| `backend/app/mind/schema.py` | 1,870 | declarative capability and schema contracts | mind runtime, help, tests | medium: broad imports, but low operational mixing |
| `backend/app/mind/context.py` | 1,809 | automatic memory retrieval, runtime assembly, compatibility rendering, block construction, ranking/classification, temporal context | native chat, GPT bridge, organ tests, preliminary gate | very high: model evidence delivery |
| `backend/app/runtime/maintenance.py` | 1,383 | job scheduling/dispatch, summary repair, history compaction, idle summary, memory review and proposal resolution | app lifecycle, chat, bridge, maintenance API/tests | high: background mutation and summaries |
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

Extract provider-history conversion, response/event serialization, and context
accounting helpers from `chat.py`. These are the lowest-risk seams because they
already have narrow inputs and can be checked as pure contract transforms.
Do not change turn orchestration in this slice.

### 2. Native Turn Orchestration

Issue: SCA-33, blocked by SCA-34.

Move the sync/stream agent turn lifecycle behind a service boundary while
keeping FastAPI registration in `build_chat_router`. Preserve tool-loop order,
thinking-only recovery, answer obligations, trace order, canonical provider
history, and final persistence. Shared behavior must not be achieved by
flattening real sync/stream transport differences.

### 3. Context Retrieval Separation

Issue: SCA-35.

Extract candidate pooling, ranking, classification, final-rerank projection,
and negative evidence from `context.py`. Runtime block assembly and the public
builders remain in the facade. This is organization only: candidate routes,
thresholds, selected/near-miss/excluded semantics, V2 projection, and trace
payloads cannot change.

### 4. Memory Read Surface

Issue: SCA-36.

Move search, read, facts, graph, their request contracts, and their presentation
helpers into a read-oriented module. Preserve command registry paths, parser
contracts, dispatcher names, compact shell presentation, pagination, temporal
filters, provenance links, and activity recording.

### 5. Memory Mutation And Evidence

Issue: SCA-38, blocked by SCA-36.

Separate write policy, deprecate/supersede lifecycle, proposals, and
relation/conflict evidence. Splitting code must not silently change duplicate
or conflict policy: similarity remains evidence rather than deterministic
truth, and no auto-merge or auto-deprecation is introduced.

### 6. Maintenance Domains

Issue: SCA-37, blocked by SCA-38.

Separate scheduler/dispatcher, summary-history work, and memory-review/proposal
resolution. Preserve job kinds, persisted status, idempotency, retry behavior,
idle checks, prompts, and auto-apply guards. The worker remains one runtime
surface even if implementations live in domain modules.

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

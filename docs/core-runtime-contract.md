# API Mind Core Runtime Contract

Last updated: 2026-07-30
Core runtime baseline: V1.50.1 deployed and release-accepted
Current additive contract: V1.65.1 deployed on the protected VPS
Contract status: Core V1 closed; V2 architecture boundary accepted
Linear issue: SCA-51

## 1. Purpose

This document is the canonical architecture map for the boundary between the
closed API Mind Core, its current clients and adapters, and the V2 extension
surfaces. It names the owner and compatibility policy of each contract without
turning future ideas into implemented capabilities.

"Core closed" means that V1.50.1 is the accepted, stable foundation from which
new product branches can be developed. It does not mean that every cognitive
research branch is mature, that every monitored behavior is perfect, or that
future bugs cannot be fixed. Residual findings remain evidence and future
annotations until current evidence or an explicit owner decision promotes them
to operational work.

## 2. Architecture Taxonomy

| Layer | Responsibility | Current state | Dependency direction |
|---|---|---|---|
| **API Mind Core Runtime** | Native turn lifecycle, provider abstraction, canonical history, context, cognitive shell, persistence, traces/events, answer control, maintenance, configuration, and database safety. | Closed V1 baseline; authoritative runtime. | Depends only on selected provider adapters and infrastructure libraries. |
| **Product UI** | Human-facing web/Android experience and developer inspection over Core contracts. | V1 cockpit/mobile prototype exists; V2 product work is planned. | Consumes versioned Core HTTP/event contracts. It does not own cognition or persistence. |
| **External Adapters** | Best-effort connection of externally hosted models to the same Core cognition. | GPT Actions bridge is implemented and experimental. | Adapts external transport to Core context, shell, structural finality, and persistence. |
| **Agentic Modules** | Optional capabilities loaded through declared ports, permissions, modes/tags, dependencies, and lifecycle. | Public V1 contract, opt-in operator-pinned host, and SDK/conformance kit implemented; no product modules installed. | May consume typed Core Ports only. It must not reach Core internals or the database directly. |

The dependency rule is inward toward the Core contract:

```txt
Product UI ---------> Core HTTP/event ports
External adapters --> Core context/shell/turn ports
Agentic Modules ----> typed Core Ports through opt-in host
                         |
                         v
                 Core Runtime owners
                         |
                         v
             provider + persistence adapters
```

Transport parity means equivalent cognitive contracts where the host permits
them. It does not mean forcing provider-owned or ChatGPT-owned behavior into
the native runtime.

## 3. Core Contract Inventory

| Contract | Owner / source of truth | Consumer | Version or identity | Stability |
|---|---|---|---|---|
| Application composition | `backend/app/main.py`, `backend/app/asgi.py` | deployment and tests | app V1.65.1 deployed | Stable factory and ASGI entrypoint over the closed V1.50.1 Core. |
| Shared native turn lifecycle | `backend/app/runtime/turn_kernel.py`, `api/chat_native_turn.py`, `runtime/autonomy.py` | native human and autonomous M3 turns | V1 plus additive `scarlet-stream-v2` | One kernel owns V2 context, history routing, accounting, trace/event receipts, persistence, provider-native finality, and compaction; adapters own only their source/transport boundary. |
| Product UI event port | `backend/app/api/chat_stream_v2.py`, `backend/app/api/chat_turn_runner.py`, `docs/stream-v2-contract.md` | web and future Android clients | `scarlet-stream-v2` | Stable envelope, detached turn runner, same-turn resume cursor, and reducer semantics. |
| Provider port | `backend/app/llm/provider.py`, `backend/app/llm/factory.py` | Scarlet turns and auxiliary semantic workers | `LLMProvider` | MiniMax M3 is Scarlet; non-Scarlet LLM work uses the fixed M2.7 auxiliary profile. Native adapters use stop reasons for continuation, tool dispatch, and finality. |
| Static Scarlet policy | `backend/app/prompts/scarlet_system.md`, `backend/app/prompts/system.py` | native selected provider | repository prompt plus resolved source | Stable policy surface; prompt changes are behavior changes. |
| Provider-native continuity | `backend/app/api/chat_provider_history.py` and canonical session history | native selected provider | canonical provider messages | Stable authority; compaction never deletes canonical history. |
| Dynamic model context | `backend/app/mind/context_contracts.py`, `context_projection.py` | native human/autonomous turns and GPT bootstrap | `scarlet-model-context-v2` | One stable model-facing schema for both lifecycles; rich source evidence remains internal. |
| Semantic context families | `backend/app/mind/context_families.py`, `docs/context-family-registry.md` | V2 projection audit and future context composer | context families V1 / shadow | Typed subject, observer, evidence, mode, activation, and policy registry; no future source is live-admitted. |
| Cognitive command surface | `backend/app/mind/command_registry.py`, `shell.py`, `schema.py`, `runtime/mind_tool_runner.py` | native Scarlet and GPT action adapter | registry v4 / semantic-authority-v2 schema | One registry-derived model-facing contract and one native tool-execution receipt path, including Scarlet-owned memory proposal review. |
| Cognitive operation dispatch | `backend/app/mind/dispatcher.py` and domain owners | shell and internal callers | internal Mind request/response contracts | Internal compatibility boundary, not a second model tool. |
| Persistence facade | `backend/app/storage/repositories.py` and `storage/repository/*` | Core domain owners | SQLModel/SQLite V1 schema | Stable facade; domain repositories are internal. |
| Database ownership | `backend/app/storage/database_boundary.py`, `docs/database-topology.md` | startup, tests, evaluation, deploy | production/laboratory/test/preliminary roles | Hard operational boundary. |
| Trace and event evidence | `backend/app/runtime/events.py`, repositories, `docs/block-registry.md` | Core, developer UI, evaluation | ordered persisted events and typed trace kinds | Append-only evidence contract where practical. |
| Context accounting/history | `backend/app/runtime/context_accounting.py`, `history_runtime.py`, `history_compaction.py`, `runtime/turn_kernel.py` | human and autonomous native turns | accounting v2, history routing/artifact versions | Canonical history is authoritative; derived artifacts fail back visibly, legacy native-string traces normalize losslessly for source mapping, and one kernel schedules post-turn compaction. |
| Turn finality | `backend/app/runtime/turn_kernel.py`, `backend/app/plugins/gpt_bridge/router.py` | native turn and GPT finalize | structural finality V1 | Provider `end_turn` owns native finality in both human/public and autonomous/private turns; output visibility differs, but no backend component semantically grades Scarlet's wording. |
| Maintenance lifecycle | `backend/app/runtime/maintenance.py` and domain owners | Core worker and maintenance API | persisted job kinds and statuses | One stable facade; maintenance is not an agent mode and may propose but never adjudicate semantic memory. |
| Autonomous cognition lifecycle | `backend/app/runtime/autonomy.py`, `runtime/autonomy_schedule.py`, `runtime/turn_kernel.py`, `storage/repository/autonomy.py` | Scarlet internal cycles and Product UI inspection | `scarlet_autonomous` session plus activation ledger V1 | Separate provider chronology and trigger provenance; the shared kernel is identical to human turns, while one scheduler coalesces pending source packets, enforces an M3 minimum gap, and preserves a maximum-silence orientation bound. |
| Cognitive Workspace | `backend/app/runtime/cognitive_workspace.py`, `mind/wake_registry.py`, `mind/workspace_contracts.py` | autonomous admission and developer inspection | source registry/appraisal/ignition V2 | Shadow-first M2.7 proposals over canonical evidence; it cannot impersonate Scarlet or mutate organs. Parked questions can re-enter only through M2.7 appraisal of new attached source evidence. |
| Endogenous cognition | `backend/app/runtime/endogenous_cognition.py`, `mind/endogenous_contracts.py`, `storage/repository/endogenous.py` | free cognitive windows and existing workspace | endogenous seeds/windows V1 | Adaptive source-backed opportunities; M2.7 proposes only, M3 must explicitly endorse through existing episodes or volition. |
| Cognitive episodes | `backend/app/mind/episode.py`, `storage/repository/cognitive_workspace.py` | M3 Scarlet through `mind_shell` | episode lifecycle V1 | Scarlet owns open/checkpoint/suspend/resolve/reject and deterministic wake contracts. |
| Perception inbox | `backend/app/storage/repository/perception.py`, `backend/app/mind/perception.py`, `backend/app/runtime/device_perception_adapter.py` | common `mind_shell` and workspace | availability/index/open/read plus device adapter V1 | External observations only; a narrow Android adapter admits bounded transitions while raw laboratory evidence remains separate and no event is auto-injected into chat context. |
| Research Lab | `backend/app/mind/research_lab.py`, `backend/app/research_lab/`, `backend/research_lab_runner/` | explicit `mind_shell` research evidence | operator-gated V1.66 local extension | A bounded public-web gateway and a separate network-disabled Python/SymPy runner persist source/run/artifact receipts. They do not form a second cognitive lifecycle or inject context/memory automatically. |
| Runtime configuration | `backend/app/config.py` | application factory and domain owners | typed `Settings` | Additive compatibility by default; invalid safety combinations fail closed. |
| Agentic Module contracts, host, and SDK | `backend/scarlet_agentic_module_sdk/*`, `backend/app/agentic_modules/*`, `docs/agentic-modules-contract.md`, `docs/agentic-module-host.md`, `docs/agentic-module-sdk.md` | optional operator-installed modules and module authors | manifest/port/lifecycle V1, host V1.53, SDK 1.0.0 | One public contract source, standalone authoring/conformance kit, and opt-in approved-root process host; native Core path remains unchanged with zero modules. |
| Deployment boundary | `backend/Dockerfile`, release process, database preflight | VPS runtime | tagged app release plus remote environment | Runtime code may deploy; databases and secrets never travel with code. |

The executable sources above outrank prose when they disagree. A discrepancy
must be resolved by updating the documentation or by an explicitly approved
contract change, never by silently choosing whichever description is newer.

## 4. HTTP Surface Classification

The closed V1.50.1 Core OpenAPI contains 28 operations. Additive Product UI,
live-stream, Device Exploration, and autonomous cognition extend the V1.60.0
development target. Operation totals are generated from the executable
OpenAPI rather than maintained as a prose invariant.

| Surface | Audience | Classification | Compatibility policy |
|---|---|---|---|
| `GET /health` | operators and deployment | Core operational | Stable additive response; safety fields may expand. |
| `/api/chat/*` | Product UI and direct native clients | Core client port | Preserve V1 behavior until SCA-47 defines and migrates the V2 stream contract. |
| `/api/dashboard/*` | current Product UI | Core client port | V1-compatible; redesign must consume contracts rather than duplicate domain logic. |
| `/api/debug/*` | developer UI, tests, evaluation | Internal diagnostic | May evolve with traces; not a public cognitive API. |
| `/api/maintenance/*` | operators, deterministic jobs, evaluation | Internal operational | Mutation remains guarded; not exposed as Scarlet's model tool. |
| `/api/autonomy/*` | Product UI inspection, scheduler support, and bounded laboratory control | Additive agentic runtime | History/overview are read surfaces; `run-now` and perception ingestion are internal laboratory/adapter operations. |
| `/mind/schema`, `/mind/call` | shell dispatcher, tests, debug, rollback | Internal cognitive transport | Preserved behind `mind_shell`; endpoint shape is not the model-facing contract. |
| `/gpt/bootstrap`, `/gpt/action`, `/gpt/finalize` | external ChatGPT GPT | Experimental adapter | Operation IDs and lifecycle remain stable while supported; external-host limitations do not redefine Core. |

There is no public `/mcp` route. Historical MCP records remain data evidence,
not an active transport.

## 5. Model-Facing Boundary

Native Scarlet receives three technical surfaces with dedicated lifecycles:

1. the static system policy;
2. canonical provider-native history, or a validated derived chronology plus
   exact tail while the canonical source remains intact;
3. one `mind_shell(command, intent)` tool schema.

The dynamic `scarlet-model-context-v2` document is compiled for the current
turn and delivered alongside those surfaces. It is a compact projection, not
the rich retrieval/runtime trace. Debug scores, excluded candidates, raw graph
paths, maintenance metadata, and UI diagnostics do not become model context
unless a separately approved contract explicitly promotes them.

The GPT bridge uses three Actions because ChatGPT owns the outer model/tool
transport. Bootstrap returns the same canonical dynamic context, action calls
the same shell dispatcher, and finalize persists the exact non-empty answer.
ChatGPT-owned history, tool policy, consent prompts, and token accounting
remain external limits. The bridge does not introduce a semantic answer judge.

## 6. Internal Boundaries

The following are implementation contracts inside the Core, not additional
public or model-facing APIs:

- domain repositories and SQLModel tables;
- rich runtime and retrieval payloads;
- `/mind/*`, debug, and maintenance HTTP dispatch;
- maintenance prompts and workers;
- provider-specific request/response translation;
- evaluator fixtures and disposable databases;
- UI trace normalization.

Internal callers may use these boundaries directly when their ownership is
documented. Models and future modules may not bypass the shell/Core Ports to
reach them.

## 7. Compatibility And Change Policy

### Stable Core contracts

- require a scoped issue, tests proportional to blast radius, and updated
  contract documentation;
- prefer additive changes;
- preserve canonical history and state provenance;
- require an explicit migration and rollback plan for breaking storage or
  client changes;
- must keep native selected-provider behavior authoritative.

### Internal contracts

- may be reorganized behind their stable facade;
- require focused equivalence tests when ownership moves;
- must not accidentally become a second model-facing surface.

### Experimental adapters

- remain optional and removable without loss of Core cognition or canonical
  data;
- may provide only the parity their external host permits;
- must fail transparently rather than claim unavailable continuity.

### Agentic Module contracts

SCA-53 accepts strict V1 manifest, Core Port, permission, dependency,
lifecycle, activation, and compatibility schemas. SCA-54 implements an opt-in
host that enforces them for operator-approved, digest-pinned subprocesses. No
product module is installed and native chat does not construct the host.

## 8. Core Closure Evidence

The accepted baseline is the tagged V1.50.1 runtime at merge `676e560`. Its
release evidence includes:

- 266 backend tests at 81.89% statement coverage;
- frozen whole-system preliminary regression 9/9;
- focused native finality and model-facing memory gates;
- protected VPS database preflight, backup, integrity, and post-deploy checks;
- native MiniMax context/finality smoke;
- authenticated GPT bootstrap/help/finalize smoke; and
- frontend parity verification.

This evidence proves the accepted Core baseline, not perfection of every
future research branch. Monitoring and parked findings remain in the bug,
experiment, branch, and Linear histories.

## 9. V2 Execution Boundary

The V2 execution boundary is `docs/v2-cognitive-companion-plan.md`; Linear
SCA-46 tracks its individual issues. V2 may extend Core only through its
existing ownership and compatibility rules: one shared native lifecycle, one
model-facing shell, source-preserving context admission, and a Product UI that
renders rather than owns cognition.

The existing module manifest, host, and SDK kit are V2 preparation. They are
not a promise that V2 ships product modules, universal connectors, package
distribution, hostile-code sandboxing, or a complete third-party developer
platform. Those are V3 work.

Duplicate/conflict adjudication, authenticated multi-user ownership, full
realtime embodiment, and external operativity remain separate future scopes
unless an approved V2 slice explicitly promotes a bounded prerequisite. They
do not block the closed Core.

## 10. Documentation Authority

- This document owns architecture layers, ports, dependency direction, and
  compatibility classification.
- `docs/project-state.md` owns integrated present state and active roadmap.
- `docs/api-contract.md` owns concrete request/response contracts.
- `docs/block-registry.md` owns model/UI/trace block delivery.
- `docs/database-topology.md` owns database roles and safety.
- `docs/branches/*` own research maturity and future acceptance ideas.
- `docs/decisions.md` preserves accepted architectural decisions.
- Historical plans and evaluation reports remain evidence of their time and
  must link forward instead of being rewritten as current work.

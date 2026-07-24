# Agentic Modules Contract

Last updated: 2026-07-19
App target: V1.56.1 over the release-accepted V1.50.1 Core
Contract status: accepted public V1 contract; opt-in host and SDK implemented
Linear issues: SCA-53, SCA-54, SCA-55

## 1. Purpose

Agentic Modules are optional, operator-installed extensions that contribute
capabilities to Scarlet through versioned Core Ports. They are outside the
closed Core Runtime and cannot import or access Core repositories, database
sessions, secrets, provider clients, prompt internals, or maintenance owners.

This contract defines what a module may declare and exchange. The opt-in host
implements discovery, lifecycle, typed calls, telemetry, and failure isolation
in V1.53.0. It does not sandbox hostile code or wire product modules into chat.
Its canonical operational contract is `docs/agentic-module-host.md`.
The module-authoring and conformance contract is
`docs/agentic-module-sdk.md`.

Canonical executable sources:

- `backend/scarlet_agentic_module_sdk/contracts.py`;
- `backend/app/agentic_modules/contracts.py` (compatibility re-export);
- `backend/app/agentic_modules/validation.py`;
- `backend/tests/test_agentic_module_contracts.py`;
- `backend/tests/test_agentic_module_sdk.py`.

## 2. Vocabulary And Ownership

| Term | Meaning | Example | Not equivalent to |
|---|---|---|---|
| Agent mode | Scarlet's one active foreground posture tag. | `idle`, `interactive`, `scouting` | Background job or process state. |
| Organ | A cognitive function with its own state or behavior. | focus, affect, volition | Deployment package. |
| System process | Backend work not lived as Scarlet's foreground mode. | maintenance, future Dream consolidation | Agent mode. |
| Agentic Module | Installable package declaring capabilities and consuming Core Ports. | a future scene-perception module | Core owner, database adapter, or automatic proof of an organ. |
| Capability | One contribution offered by a module. | context, prompt, command, event | Permission. |
| Permission | Host-enforced Core operation the module requests. | `context.contribute` | Direct access to an implementation object. |

A module may implement one organ, part of an organ, or a non-cognitive
capability. Declaring an organ-like capability does not make it part of the
Core and does not prove behavioral maturity.

Maintenance, Dream, indexing, summarization, and other background jobs are
system processes. They never become agent modes merely because a module wants
to observe or assist them.

## 3. Manifest V1

Every module supplies exactly one strict `agentic-module-manifest-v1` document.
Unknown fields are rejected.

| Field | Purpose |
|---|---|
| `schema_version` | Selects the manifest parser. Breaking schema changes require a new value. |
| `module_id` | Stable lowercase package identity. It does not change with releases. |
| `display_name`, `description` | Human-readable identity and bounded purpose. |
| `module_version` | SemVer 2.0 module release. |
| `core_compatibility` | Inclusive minimum Core version, optional exclusive maximum, and exact required Core contract versions. |
| `mode_tags` | Agent modes in which the module can be selected. Tags are checked against the Core registry. |
| `capabilities` | Typed context, prompt, command, or event declarations. |
| `permissions` | Requested values from the closed permission allowlist. |
| `dependencies` | Required or optional module ids plus SemVer ranges. |
| `runtime` | Declarative `stdio-json-v1` transport and process entrypoint. It is not executed by this contract. |
| `resources` | Requested memory, CPU, concurrency, and request/response bounds. |
| `timeouts` | Startup, call, health, and shutdown limits. |
| `health` | Probe interval and failure/recovery thresholds. |
| `lifecycle` | Startup and restart policy over the fixed V1 lifecycle. |

The full JSON Schema is generated from the executable model:

```bash
cd backend
.venv/bin/python -c \
  'import json; from app.agentic_modules.contracts import AgenticModuleManifest; print(json.dumps(AgenticModuleManifest.model_json_schema(), indent=2))'
```

The valid reference manifest is
`backend/tests/fixtures/agentic_modules/context_observer.valid.json`.

## 4. Capabilities And Permissions

The manifest supports four capability kinds:

| Kind | Declares | Mandatory permission |
|---|---|---|
| `context` | Bounded context block types and contribution count. | `context.contribute` |
| `prompt` | `policy_appendix` and/or `turn_context` contribution slots. | `prompt.contribute` |
| `command` | Namespaced commands and their catalog. | `command.register` |
| `event` | Event subscriptions and/or publications. | `event.subscribe` and/or `event.publish` |

Additional allowed permissions are `context.read`, `module_state.read`, and
`module_state.write`. Module state is future host-owned state scoped to that
module; it is not access to Core persistence.

The permission model is a closed enum. Values such as `database.read`,
`secrets.read`, `core.internal`, repository access, arbitrary filesystem
access, or provider-client access are not expressible and fail manifest
validation. The host must enforce the declared subset at every port call;
manifest validation alone is not a sandbox.

Prompt contributions are subordinate additions. The future host must compose
them after the canonical Scarlet policy and must reject attempts to replace
identity, safety, ownership, or Core protocol instructions.

## 5. Typed Core Ports

All calls use `agentic-module-port-v1` and a strict `PortCallContext` containing
request id, module id, Core version, active agent mode, optional opaque
session/turn references, and a deadline. The host supplies only data allowed
by the module's permissions.

| Port | Request | Result |
|---|---|---|
| Context | Call context, item/token budget, allowlisted input blocks. | Bounded context contributions with id, block type, JSON content, estimate, and priority. |
| Prompt | Call context, allowed slots, character budget. | Bounded text contributions and priority. |
| Command | Call context, namespace, command, JSON arguments. | Explicit success/error result with retryable structured error. |
| Command catalog | No dynamic Core internals. | Namespaced descriptors and JSON input schemas. |
| Event | Call context and one allowlisted event. | Acknowledgement and bounded requested publications. |
| Health | Call context. | `healthy`, `degraded`, or `unhealthy` plus bounded JSON details. |

Opaque JSON fields carry capability-specific data; they do not weaken the
typed envelope. SCA-54 must enforce payload sizes, permission filtering,
deadlines, event allowlists, contribution budgets, and provenance before a
result enters Core context, prompts, commands, or events.

## 6. Lifecycle

The fixed host lifecycle is:

```txt
discover -> validate -> load -> start -> health -> stop
                                      \-> failure
```

`ModuleLifecycleEvent` records each phase as `started`, `succeeded`, `failed`,
or `skipped`. A manifest chooses eager/lazy startup and never/on-failure
restart within bounded retries. It cannot add hidden lifecycle phases.

Discovery and validation do not execute module code. The V1.53.0 host owns the
later phases for operator-approved, manifest-digest-pinned modules. Untrusted-
code sandbox guarantees remain outside V2 scope.

## 7. Deterministic Activation

`build_activation_plan()` receives validated manifests, the current Core
version, available Core contract versions, and exactly one active agent-mode
tag. It produces ordered active modules, inactive modules, blocked modules, and
structured diagnostics.

Rules:

1. Duplicate ids, unknown mode tags, incompatible Core/contract versions,
   missing required dependencies, required version mismatches, and required
   dependency cycles block affected modules.
2. A missing or incompatible optional dependency emits a warning and does not
   block its consumer.
3. A module is eligible only when its `mode_tags` contains the one active
   agent-mode tag.
4. Every required dependency of an eligible module must also be eligible for
   that tag. A disabled or blocked required dependency blocks its consumer.
5. Independent valid modules remain plannable when another module is blocked.
6. Required dependencies are ordered before their consumers with manifest
   declaration order as the stable tie-breaker.
7. `maintenance` and `dream` are rejected as agent-mode tags. Background
   system processes use separate scheduling and lifecycle contracts.

This planner does not load code. The V1.53.0 host consumes this exact plan
rather than reimplementing compatibility and dependency rules ad hoc.

## 8. Invalid Examples

Direct Core access is invalid:

```json
{
  "permissions": ["context.contribute", "database.read"]
}
```

Reference: `backend/tests/fixtures/agentic_modules/database_access.invalid.json`.

A background process presented as an agent mode is schema-readable but fails
activation against the authoritative mode registry:

```json
{
  "mode_tags": ["maintenance"]
}
```

Reference: `backend/tests/fixtures/agentic_modules/background_mode.invalid.json`.

A missing required dependency blocks only its consumer. Setting
`"optional": true` converts that absence into a warning; it never silently
changes a required dependency into optional behavior.

## 9. Versioning And Compatibility

- Module releases use SemVer 2.0.
- Minimum versions are inclusive; maximum versions are exclusive.
- Manifest and port identifiers change only for breaking contract revisions.
- A Core release may add optional fields or permissions only through a
  backward-compatible schema revision; strict V1 manifests still reject
  unknown input fields.
- Exact `required_contracts` prevent a module from loading against a similarly
  named but incompatible port.
- A host must reject or block incompatibility before code execution and expose
  the diagnostic without guessing a fallback.
- Core canonical history, cognition, persistence, and policy remain valid when
  every optional module is absent.

## 10. Host, SDK, And Deferred Work

SCA-54 implements approved-root discovery, manifest digest pinning, process
supervision, JSONL framing, permission gates, contribution composition, health,
failure isolation, receipts, and shutdown. SCA-55 implements the standalone
Pydantic-only SDK 1.0.0, module-side JSONL runtime, scaffold, schema export,
localized validation, and executable conformance kit over the same canonical
models imported by the host. Product modules, hostile-code sandboxing, package
signatures, persistent module state, UI controls, and chat integration remain
deferred. None may broaden permissions by importing Core internals.

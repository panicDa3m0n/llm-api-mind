# Agentic Module Host

Last updated: 2026-07-19
App target: V1.55.2 over the release-accepted V1.50.1 Core
Runtime status: implemented, opt-in, no product modules installed
Linear issue: SCA-54

## 1. Purpose And Boundary

The Module Host discovers, validates, starts, calls, observes, and stops
operator-approved Agentic Modules through the V1 contracts. It is an optional
runtime outside the closed Core. The normal Core path does not construct it,
and zero enabled modules produce zero contributions and no behavior change.

The host does not provide a marketplace, execute unapproved packages, expose
Core repositories, or claim to sandbox hostile code. Initial use is restricted
to modules deliberately installed and pinned by the operator.

Executable owners:

```txt
backend/app/agentic_modules/registry.py
backend/app/agentic_modules/transport.py
backend/app/agentic_modules/ports.py
backend/app/agentic_modules/host.py
backend/app/agentic_modules/telemetry.py
```

## 2. Installation And Trust

Each approved root contains one direct child directory per module and each
child contains `agentic-module.json`. Discovery never imports or executes a
module. It reads at most 1 MB, rejects symlinked install directories/manifests,
validates the strict SCA-53 manifest, and requires both:

1. an operator-approved `module_id`;
2. the exact SHA-256 digest of the manifest bytes.

Unknown modules, modified manifests, malformed JSON, invalid contracts,
unavailable entrypoints, and duplicate installed ids remain diagnostics and do
not enter the runnable registry. Valid registrations are sorted by stable
module id before activation planning.

The digest pins policy and entrypoint declaration, not every byte reachable by
the process. Package/signature verification is a later hardening layer; V1.53
therefore remains an operator-trust boundary.

## 3. Activation And Lifecycle

The host passes registered manifests to the SCA-53 activation planner. That
planner remains the sole owner of Core/port compatibility, mode eligibility,
dependency ranges, cycles, and dependencies-first order.

The observable lifecycle is:

```txt
discover -> validate -> load -> start -> health -> stop
                                      \-> failure
```

Discovery and validation are data-only. Load constructs the transport owner;
start creates the process and completes the `lifecycle.start` handshake.
Health is probed immediately and remains callable later. Stop runs in reverse
activation order. A failed required dependency prevents startup; a dependency
that fails at runtime causes its running required dependents to be quarantined.
Independent modules continue.

`disable(module_id)` stops the module and replans without it. Required
consumers become blocked by the existing planner. With every module disabled,
all context/prompt/event batches are empty and commands return a typed
unavailable result; the Core remains usable.

## 4. Process And Transport Isolation

`stdio-json-v1` uses one persistent subprocess per active module and one
correlated JSON object per line. The host:

- calls `create_subprocess_exec` directly and never invokes a shell;
- runs from the approved module directory;
- passes only an environment allowlist (`PATH`, locale/temp/platform basics)
  plus `PYTHONUNBUFFERED`, excluding application secrets and API keys;
- serializes calls per process;
- enforces manifest request/response byte limits and startup/call/health/
  shutdown timeouts;
- drains and bounds the stderr tail to 64 KB;
- terminates the whole process group after timeout, crash, malformed framing,
  correlation mismatch, invalid contract output, or remote error;
- applies hard address-space and file-descriptor limits on Linux.

`max_concurrent_calls` is conservatively enforced as one serialized call in
this first host. `max_cpu_percent` is a validated resource declaration, not a
portable hard percentage cap; production-grade CPU enforcement requires the future
deployment sandbox/cgroup boundary. macOS does not receive the Linux address-
space limit. These limits are explicit so operator-installed isolation is not
misrepresented as hostile-code containment.

## 5. Ports And Composition

The host routes only capabilities declared by active, running modules:

| Port | Host behavior |
|---|---|
| Context | Sends inputs only with `context.read`; validates block types/counts; sorts by priority then activation/local order; applies global token/item budgets. |
| Prompt | Intersects requested and declared slots; validates returned slots/character budget; sorts by priority then activation/local order. |
| Command | Routes exact namespace/command pairs; duplicate routes become unavailable rather than selecting implicitly. |
| Event | Sends only subscribed event types and rejects undeclared publications. |
| Health | Validates typed status and quarantines an immediately unhealthy module. |

Opaque payload fields remain behind the typed envelopes. A model-valid result
that violates its capability declaration fails the call before any success
receipt or contribution enters the result batch.

The host does not yet insert batches into native chat context or prompts. That
integration should happen only with an approved product module and must retain
Core-owned context budgets, canonical prompt priority, and answer obligations.

## 6. Receipts, Traces, And Events

Every host operation emits a strict `ModuleReceipt` with module, operation,
status, mode, request/session/turn anchors, duration, and bounded diagnostic
details. `InMemoryModuleTelemetry` supports deterministic host use and tests.
`RepositoryModuleTelemetry` projects receipts into existing stores without a
migration:

```txt
Trace.kind          = agentic_module.<operation>
CognitiveEvent.type = agentic_module.<operation>.<status>
CognitiveEvent.actor = module_host
CognitiveEvent.source = <module_id>
```

Only receipts with a real session id are persisted. Startup without a session
still emits to the configured sink but does not invent a chat/session owner.
Module output is summarized by receipts; the raw process stream is not copied
into model context.

## 7. Failure Semantics

Timeout, crash, oversized output, malformed JSON, mismatched request ids,
remote errors, and invalid typed/capability output all quarantine the offending
module. The host returns empty contribution from that module or a typed command
error. It never substitutes guessed output. Required dependents are also
quarantined; unrelated modules continue in deterministic order.

Telemetry records both the failed operation and `lifecycle.failure`, including
a short stderr tail when available. Disabling or omitting every module restores
the unextended Core path.

## 8. Verification Fixture And Deferred Work

`backend/tests/fixtures/agentic_modules/conformance_worker.py` remains the
host's deliberate failure fixture for timeout, invalid-output, and crash
behavior. The V1.54.0 SDK additionally generates a neutral module from scratch
and proves that the unmodified result passes both standalone conformance and
this real host. Canonical authoring details live in
`docs/agentic-module-sdk.md`.

Product modules, package signatures, hostile-code sandboxing, persistent
module state, UI controls, and automatic chat wiring remain separate future
work.

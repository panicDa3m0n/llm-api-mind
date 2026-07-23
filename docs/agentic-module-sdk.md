# Scarlet Agentic Module SDK

Last updated: 2026-07-19
App target: V1.55.1 over the release-accepted V1.50.1 Core
SDK version: 1.0.0
Protocol versions: manifest V1, port V1, lifecycle V1
Status: implemented public development kit; no product module installed
Linear issue: SCA-55

## 1. Purpose And Boundary

The Python SDK is the official module-side surface for building and checking
an Agentic Module without importing Core internals. It provides:

- the exact Pydantic manifest and Core Port models used by the host;
- a typed bounded development client for launching and calling a module;
- a module-side `stdio-json-v1` request loop and overridable handlers;
- deterministic scaffold generation;
- localized manifest validation;
- a live conformance runner for lifecycle, health, declared ports, structured
  errors, and per-request execution evidence; and
- versioned JSON Schema export.

The SDK does not install or approve a module, grant Core permissions, access
the database, expose providers or secrets, sandbox hostile code, or connect a
module to native chat. Operator approval and runtime isolation remain host
responsibilities.

Canonical package source:

```txt
backend/scarlet_agentic_module_sdk/
```

Standalone distribution metadata:

```txt
backend/sdk/pyproject.toml
```

`app.agentic_modules.contracts` is a compatibility re-export. The SDK package
owns the executable contract definitions, and the host imports those same
classes. There is no copied SDK schema that can drift from host validation.

## 2. Install And Build

For repository development:

```bash
python -m pip install ./backend/sdk
```

Build the standalone wheel:

```bash
python -m pip wheel ./backend/sdk --no-deps --wheel-dir ./dist
```

The wheel depends only on Pydantic. A module author does not need FastAPI,
SQLModel, the API Mind database, provider clients, or the Core source package.
The main backend distribution also includes this SDK because the host and its
tests consume the same canonical models. The wheel includes the PEP 561
`py.typed` marker so downstream type checkers inspect its public annotations.

## 3. Scaffold

Create a protocol fixture in a new or empty directory:

```bash
scarlet-agentic-module scaffold ./my-module \
  --module-id cloud.example.my-module \
  --display-name "My Module"
```

The command creates:

```txt
my-module/
  agentic-module.json
  module.py
  run-module
  README.md
```

The generated manifest declares bounded context, prompt, command, and event
examples. `module.py` subclasses `AgenticModule`; `run-module` uses the Python
interpreter that created the scaffold. The result is deliberately a neutral
conformance fixture, not cognitive product behavior.

The scaffold refuses to overwrite a non-empty directory. It validates the
manifest before writing it, so invalid module ids, versions, capability names,
permissions, or relationships fail at generation time.

## 4. Module Runtime

A module implements only the handlers it declares:

```python
from scarlet_agentic_module_sdk import AgenticModule, serve
from scarlet_agentic_module_sdk.contracts import (
    ContextContribution,
    ContextPortResult,
)


class MyModule(AgenticModule):
    def contribute_context(self, request, *, capability_id):
        return ContextPortResult(
            contributions=[
                ContextContribution(
                    contribution_id="current-observation",
                    block_type="cloud.example.observation",
                    content={"available": True},
                    estimated_tokens=8,
                )
            ]
        )


serve(MyModule())
```

Default handlers are conservative: start/stop and health succeed, context and
prompt return no contributions, events acknowledge without publication, and
commands return a typed `command.not_implemented` error.

The runtime validates every incoming Port V1 payload before invoking a
handler. Unsupported protocol versions, malformed envelopes, invalid payloads,
and unknown operations return a correlated structured error. Unhandled module
exceptions still crash the module process so the host can quarantine it; the
SDK does not conceal implementation failures.

## 5. Wire Contract

Every host request is one JSON object followed by a newline:

```json
{
  "protocol_version": "agentic-module-port-v1",
  "request_id": "modreq_...",
  "operation": "context.contribute",
  "capability_id": "example.context",
  "payload": {}
}
```

A success response preserves the correlation id:

```json
{
  "request_id": "modreq_...",
  "ok": true,
  "result": {}
}
```

A protocol rejection is explicit:

```json
{
  "request_id": "modreq_...",
  "ok": false,
  "error": {
    "code": "operation.unknown",
    "message": "Unsupported operation: example",
    "retryable": false
  }
}
```

One process serves requests serially until `lifecycle.stop` or EOF. The host,
not the module, owns timeout, byte-limit, permission, composition, trace, and
failure-isolation enforcement.

## 6. Validation And Schema Export

Validate without executing module code:

```bash
scarlet-agentic-module validate ./my-module
```

The JSON result identifies the failing field where possible. Cross-field
errors such as undeclared required permissions are mapped to their responsible
manifest area instead of remaining at an unhelpful document root.

Export all public schemas:

```bash
scarlet-agentic-module schema --output ./schemas
```

The output includes the manifest plus request/result schemas for context,
prompt, command, event, and health. Filenames contain their major contract
version. Schema export is generated from the same models imported by the host.

## 7. Conformance

Exercise a module process locally:

```bash
scarlet-agentic-module conformance ./my-module \
  --core-version 1.54.0 \
  --mode interactive
```

The runner performs, in order:

1. strict manifest, permission, mode, and entrypoint validation;
2. `lifecycle.start`;
3. health validation;
4. one bounded call for every declared context and prompt capability;
5. one call for every declared command;
6. one call for each event capability with a subscription;
7. an unknown-operation probe requiring a structured error; and
8. `lifecycle.stop`.

Every executed check records operation, status, stable code, request id, and
duration. These diagnostics are the conformance execution trace; they do not
replace Core `Trace` and `CognitiveEvent` receipts. Host tests separately prove
that a generated scaffold produces those Core receipts when activated with
real session/turn ownership.

Conformance validates envelope and capability constraints, including declared
context block types, contribution counts, prompt slots/budgets, event
publication allowlists, and typed command results. It does not judge the
semantic usefulness of a future product module.

## 8. Installation Into The Host

Passing conformance does not authorize execution. An operator must:

1. review the module package and trust boundary;
2. place it under an approved module root;
3. calculate the exact `agentic-module.json` SHA-256;
4. approve the module id plus that digest; and
5. activate the opt-in host in one eligible agent mode.

Any manifest change invalidates the approval digest. Package signing,
marketplace distribution, hostile-code containment, persistent module state,
UI controls, and native chat integration remain separate future work.

## 9. Compatibility

- SDK releases use SemVer; the initial package is `1.0.0`.
- Manifest, port, and lifecycle versions are independent protocol identities.
- An application version increase does not imply a protocol break.
- Breaking protocol changes require a new explicit contract identifier and
  parallel compatibility handling; they must not silently change V1 models.
- The module manifest remains the source of its Core and contract compatibility
  declarations. The conformance CLI input is a test target, not an override.

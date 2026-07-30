# Research Lab

Last updated: 2026-07-30
State: implemented locally for V1.66.0; disabled by default and not deployed

Research Lab lets Scarlet explicitly inspect a bounded public web document or
request a small Python/SymPy computation. It is evidence support, not a second
cognitive runtime: Lab records never become automatic memory, automatic model
context, a Workspace signal, or an autonomous wake reason.

## Shell Contract

```txt
lab status
lab web open "https://example.org/document"
lab source labsrc_...
lab python --code "from sympy import factor; print(factor(x**2 - 1))"
lab python --source labsrc_... --code "..."
lab run labrun_...
lab artifact labart_...
```

`lab web open` stores one immutable bounded source receipt. It returns an id
and compact metadata; source text reaches Scarlet only through `lab source` or
when Scarlet passes that id explicitly to `lab python`. `lab python` stores the
code hash, declared source ids, output receipt, and bounded artifacts. The
code itself is not retained as a new semantic memory.

There is intentionally no `lab web search` yet. A generic search provider
would add an external model/provider contract that has not been selected or
operated. `web open` provides direct cited-source reading without pretending
that a search integration is active.

## Boundaries

| Boundary | Contract |
|---|---|
| Model surface | One existing `mind_shell(command, intent)` command family, never a second tool. |
| Python execution | Dedicated sidecar over a Unix socket; no model code runs in the FastAPI process. |
| Runner network | Disabled by deployment (`network_mode: none`). Python cannot fetch URLs. |
| Web retrieval | Backend-only, read-only HTTPS GET with public-host checks, no redirects, content-type and size limits. |
| Storage | `research_lab_runs`, `research_lab_sources`, and `research_lab_artifacts` in the canonical selected SQLite role. |
| Cognition | No automatic injection into context, memory, KG, perception, Workspace, or autonomous scheduler. |
| Artifacts | Bounded text/binary outputs; text is inspectable on demand, binary stays in trace/UI-facing storage. |
| Authority | Lab output is evidence from its declared source/code, not a semantic assertion or a backend decision. |

The runner is configured with a code limit of 12,000 characters, up to three
source documents, a 15-second execution timeout, process resource limits,
read-only filesystem, temporary writable space, unprivileged UID, no Linux
capabilities, and no-new-privileges. Code may write only intended artifacts
under `LAB_ARTIFACTS_DIR`; it receives source files only under
`LAB_SOURCES_DIR`.

The public-host preflight is a local application boundary, not a substitute for
network policy. Before exposing this capability to untrusted or multi-user
traffic, the backend must use an egress proxy or firewall allowlist that also
prevents DNS-rebinding and private-network access at connection time.

## Operator Installation

Research Lab stays off until all of these are true:

1. Build/start `docker-compose.research-lab.yml` together with the root
   `docker-compose.yml`, with a dedicated host
   socket directory, for example `RESEARCH_LAB_SOCKET_DIR=/var/lib/scarlet/research-lab`.
2. Create that host directory with ownership for the runner UID `10001` and
   restrict it to the backend/runner service accounts.
3. Mount that exact directory at `/run/research-lab` in the existing backend
   container. Do **not** mount the database, repository, `.env`, home directory,
   Docker socket, or host root into the runner.
4. Configure the backend environment:

   ```txt
   RESEARCH_LAB_ENABLED=true
   RESEARCH_LAB_RUNNER_UDS=/run/research-lab/runner.sock
   ```

5. Verify the runner socket with its `/health` endpoint from the backend
   container, then use `lab status` and one disposable `lab python` command on
   a non-production database before production enablement.

The tracked root `docker-compose.yml` and `docker-compose.research-lab.yml`
compose together. Their only shared volume is the socket directory. Enabling
the backend flag without a reachable runner leaves `lab python` transparently
unavailable; it never falls back to in-process execution.

## Current Verification

Focused local tests verify command/catalog integration, disabled behavior,
persisted runs/sources/artifacts, explicit source handoff to Python, public-web
host rejection, bounded HTML extraction, API schema inclusion, no-memory side
effects, and the runner's actual bounded subprocess/artifact receipt with
standard-library code. A direct temporary-database probe also opened and
reopened `https://example.com` by source id, and confirmed that Python fails
closed without its socket. Docker sidecar execution and a live SymPy run are
not yet local evidence because the runner container has not been started in
this workspace.

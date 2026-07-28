# Database Topology And Safety Boundaries

Last updated: 2026-07-27
Backend baseline: V1.61.0 (deployed with fresh active autonomous chronology)
Status: accepted operational boundary

This document is the canonical map of database ownership. A path ending in
`app.db` is not enough to identify its role: the deployment mount, the runtime
role, and the procedure that created it are the authority.

## Roles

| Role | Purpose | May a test write it? | May deployment transfer it? |
|---|---|---:|---:|
| `production` | Persistent VPS data used by real Scarlet/GPT sessions. | No. | No. It stays on the VPS mount. |
| `laboratory` | Local, mutable experimental history. | No automated suite writes it. | No. It is not a production seed. |
| `test` | Disposable evaluator copy or ephemeral test SQLite database. | Yes. | Never. |
| `preliminary` | Disposable run copied from a frozen regression baseline. | Yes, only the run copy. | Never. |

`DATABASE_ROLE=auto` resolves `local`/development to `laboratory`, test
environments to `test`, and `production` to `production`. Any other
`ENVIRONMENT` must explicitly set `DATABASE_ROLE`; this deliberately includes
`mobile_test`, because that name alone does not say whether its mounted data is
preview data or real data.

V1.29.0 adds `memory_activities` through normal schema initialization. V1.38.0
replaces the mixed provenance audit/apply route with a strictly read-only audit
and two guarded maintenance POST operations. Every real repair or explicit
fixture deprecation requires a prior disposable-copy run, an online production
backup reference, the current reviewed candidate digest, and an exact approval
token. Summary reconciliation remains dry-run-first. None of these operations
is a startup migration or an evaluator action against production.

V1.39.0 adds `history_compactions` through normal schema initialization. These
records are derived, append-only chronology artifacts; they never replace
`sessions.provider_history_json` or canonical messages. Their absence or
validation failure causes model routing to use full canonical history.

`CODEX_TEST` remains the legacy, useful *copy-once isolation mechanism*. It is
not a role. When true, it selects `CODEX_TEST_DATABASE_URL` and may create it
by copying `CODEX_TEST_SEED_DATABASE_URL` (or `DATABASE_URL`) once. Production
role rejects that setting. Preliminary role requires it and requires a target
file name containing `preliminary`.

## Known Files And Their Current Status

The inventory below was last reconciled on 2026-07-19 without transferring or
rewriting any database.
Counts are operational identifiers, not a license to copy the data elsewhere.

| Location | Role / status | Evidence and rule |
|---|---|---|
| VPS `/opt/scarlet-mobile-test/backend/data/app.db` mounted at container `/app/data/app.db` | `production` | Real persistent data. V1.61.0 is deployed at `d6a88b3` with one writable `/app/data` mount, `DATABASE_ROLE=production`, `CODEX_TEST=false`, direct isolation, and SQLite integrity `ok`. The quiescent pre-reset backup is `/var/backups/scarlet-mobile-test/v1610-20260727T144642Z/app.db.pre-autonomy-reset` (SHA-256 `4b6d1d67b0234d59957beb9d89e74b756663488898b3c75660218cdd76b15a0d`). The original autonomous session is archived with all 92 provider-history items; the active replacement began empty with one +600-second activation. Immediate post-switch counts were 319 memories, 239 facts, 243 sessions, 990 messages, 7,415 events, and 34 tables. |
| `backend/data/app.db` | Mutable local `laboratory` snapshot; Git LFS-tracked file | The explicit 2026-07-23 cross-machine checkpoint publishes SHA-256 `9b6ec713425e67439f9784b9b9525b50cc253ea986121e97c83abda22ff0448f`: integrity `ok`, 27 tables, 36 memories, 26 facts, 163 sessions, 598 messages, and 3,597 events. It is not production, a test target, or a deployment seed. Future changes still require a separately reviewed data release. |
| `backend/data/preliminary-rework-v1.db` | Frozen local source for `preliminary-regression-v1` | Ignored copy of published SHA-256 `827bb...c1ed5`; 34 memories, 25 facts, 155 sessions, 567 messages. Never mutate it. |
| `backend/data/preliminary-rework-v1-run.db` | `preliminary` disposable run | Recreated from the frozen source by every preliminary regression run. Ignored. |
| `backend/data/codex_test.db` | Historical ignored evaluation artifact | Contains the old dirty-memory dataset. V1.27 no longer selects or resets it. Retain it for historical reports until an explicit cleanup decision. |
| `backend/data/codex-memory-eval-v2-run.db` | Current disposable dirty-memory evaluator run | Created only by `codex_test_memory_harness.py`; ignored and name-guarded. |
| `data/app.db` | Old ignored root-level SQLite residue | Empty of Scarlet sessions/memories at the audit. No current config selects it. Do not treat it as a source. |
| `backend/app/app.db`, `backend/scarlet.db` | Empty ignored residues | Both are zero-byte files from 2026-05-23 and are not selected by current configuration. Do not delete them as part of unrelated work. |

V1.30.0 context calibration opened `backend/data/app.db` through SQLite
`mode=ro` only. The role preflight reported `laboratory`, integrity `ok`, and no
records were modified. Session ids quoted in `docs/runtime-context-packs.md`
are therefore laboratory measurements, never claims about VPS production.
| `data/milvus_lite_shadow.db` | Rebuildable derived retrieval cache when enabled | Ignored; never an authority for memory or a deployment source. |

The historical files remain on disk because deletion is a separate data
retention decision. Their presence does not make them runtime candidates.

The strict read-only V1.38.0 pre-deploy audit of the VPS database classified
307 memories: 58 complete user-message source hooks, 242 source-session-only
records, and seven invalid source-message hooks. Independent structured inspection proved
all 242 source-session-only records belong to three named Codex seed sessions;
241 were active and one already deprecated. Of the seven invalid links, four
point outside the declared turn and three point to an assistant message inside
it. They do not have a unique defensible correction and are retained for review. Production
mutation was permitted only after the V1.38 disposable-copy gate and a fresh
backup. The guarded production apply is complete: all 242 fixtures are
deprecated, while the seven uncertain real links remain review-only. Final
counts, backup evidence, and direct controls are recorded in the V1.38
evaluation report.

## Runtime Guardrails

- `app.main` is now an application factory only. Importing it does not open,
  migrate, create, or copy a database.
- `app.asgi:app` is the only eager production ASGI entrypoint. Docker uses it.
- `validate_database_configuration()` runs before a FastAPI app is assembled.
  It rejects ambiguous environments and production/test mixtures.
- `GET /health` and `GET /api/dashboard/settings` expose the resolved
  `database.role`, `database.profile`, isolation mode, and safe connection
  target. They never expose non-SQLite credentials.
- `python -m app.ops.database_preflight` performs a read-only SQLite integrity
  and state-count inspection. It does not create a file, migrate schema, or
  copy a seed.
- `scripts/check_database_boundary.py --staged` refuses a normal commit that
  includes the mutable `backend/data/app.db`. The only override is an explicit
  `--allow-laboratory-snapshot` for a reviewed data release.

## Local And Evaluation Procedures

Normal local run:

```txt
ENVIRONMENT=local
DATABASE_ROLE=auto
CODEX_TEST=false
DATABASE_URL=sqlite:///./data/app.db
```

Read-only local preflight:

```bash
cd backend
.venv/bin/python -m app.ops.database_preflight \
  --expect-role laboratory --require-existing
```

The preliminary regression runner sets its own `preliminary` role and only
opens the freshly copied run database. The historical dirty-memory evaluator
now defaults to the frozen preliminary source and creates
`data/codex-memory-eval-v2-run.db`; use `--source-db` only when deliberately
evaluating another local laboratory source. `--reuse-run` is the explicit
exception to its default fresh-copy behavior.

## VPS Deployment Procedure

Do not run a file-copy deployment until the target environment contains:

```txt
ENVIRONMENT=mobile_test
DATABASE_ROLE=production
CODEX_TEST=false
DATABASE_URL=sqlite:///./data/app.db
```

The value `mobile_test` is historical deployment naming; the explicit role is
what declares that its mounted database contains production data.

Current V1.40.0 production maintenance policy, retained from V1.29.0:

```txt
MAINTENANCE_ENABLED=true
SUMMARY_RECONCILE_ENABLED=false
HISTORY_COMPACTION_MODE=active
```

The one-time V1.29.0 reconciliation generated all 67 eligible missing
summaries. New production turns use the established 900-second idle
maintenance job. The broad repair scanner remains disabled on this deployment
so it cannot summarize a newly completed turn immediately; it can be enabled
again after its age policy is separated from historical reconciliation.

V1.40.0 preserves that maintenance boundary while aligning active cognition
with the verified local runtime: `model_context_profile=v2`, OpenRouter
retrieval/rerank enabled, active final arbitration with absolute floor `0.004`
and relative floor `0.01`, active
agent-mode routing, active recursive history compaction at the 400k total-input
trigger, and optional focus/volition/affect/temporal/Dream injection off.
Production role and disabled broad summary reconciliation are deliberate
deployment differences, not local/remote feature drift.

V1.41.0 preserves the same data and maintenance boundary. It adds active
shared answer obligations with `ANSWER_OBLIGATIONS_MODE=active` and a 4,096
token semantic-validator output budget. These settings change answer control,
not database ownership or canonical history.

V1.64.0 supersedes only that answer-control policy: generated semantic answer
obligations and their auxiliary validator are removed. Historical traces and
stored data remain unchanged. No V1.64 migration deletes fact rows or memory
proposals; legacy facts are read-only non-authoritative audit evidence, and
background proposal review cannot mutate semantic memory. `pending_review`
remains an open status until Scarlet decides through the memory shell.
Proposal acceptance preserves the original source provenance and records the
later decision turn separately. Memory, proposal, fact, and lifecycle
maintenance no longer changes `sessions.updated_at`; that field represents
conversation activity and therefore remains aligned with the latest message.

V1.42.0 preserves the same data and maintenance boundary. It adds ordered
per-block agent-mode routing receipts and stricter resumable-mode ownership;
these changes affect model-context delivery and traces, not database ownership
or canonical history. The post-deploy production preflight remained
`production`/`direct` with SQLite integrity `ok`.

V1.43.0 preserves the same database, maintenance, context, and cognitive
boundaries. It removes only the deprecated MCP transport and query-key auth.
The guarded rollout retained all 34 historical `mcp_bridge` sessions; the
single expected Actions smoke added one session and two messages.

V1.50.1 preserves those ownership and maintenance boundaries while deploying
the consolidated V1.44-V1.50 runtime. The protected rollout first created the
online backup recorded above, built the new image without restarting the old
container, and passed a read-only new-image preflight against the production
mount. Post-restart and post-smoke preflights remained `production`,
`codex_test=false`, direct isolation, 29 tables, and integrity `ok`. The only
expected data changes were two release-verification sessions and their four
user/assistant messages; no memory or fact count changed.

V1.60.1 preserves the same production ownership boundary while adding four
autonomy/perception tables and session/turn lifecycle columns through normal
schema initialization. The rollout backed up the online database, proved the
migration against an isolated copy, and passed read-only preflight before and
after restart. The first real periodic cycle added only its expected
autonomous chronology and one model-authored semantic lesson; post-cycle
preflight remained direct with 34 tables and integrity `ok`.

V1.61.0 preserves the same database ownership and maintenance boundary while
unifying human/autonomous model context and resetting only the active
autonomous chronology through its guarded archival command. No canonical
cycle, message, turn, trace, event, tool call, memory, perception record, or
maintenance record was deleted. The copied-DB canary and production reset both
left integrity `ok`; the old pending activation alone became `cancelled`.

For every deployment:

1. Make a timestamped remote backup of `/opt/scarlet-mobile-test/backend/data/app.db` before replacing code or restarting the container.
2. Transfer code with exclusions for `backend/data/`, the deployment-root
   `/opt/scarlet-mobile-test/.env`, and any source-tree `backend/.env`.
   An `rsync --delete` command without those exclusions is prohibited.
3. Build the new image without restarting the existing container.
4. Run the new image's read-only preflight against the existing mount with
   `python -m app.ops.database_preflight --expect-role production --require-existing`.
   Confirm `codex_test=false`, SQLite integrity `ok`, and the expected mounted
   path.
5. Only then restart the compose service and call `/health`; confirm returned
   `database.role=production` and `database.isolation=direct`.
6. Never seed, reset, or run `codex_test_memory_harness.py` on the VPS.

An explicit owner-requested autonomous chronology restart is not a database
seed or a broad reset. Use only the guarded
`python -m app.ops.reset_autonomous_chronology` command after a fresh online
backup and copied-DB dry-run/apply canary. The command archives the current
autonomous session and preserves all canonical evidence; it must never delete
human sessions, semantic memory, perception, or backend maintenance records.

The Dockerfile's `.dockerignore` already excludes `data/`, but that only
protects image construction. The transfer exclusion and remote backup are
separate mandatory safeguards because the compose service binds the remote
data directory into the container at runtime.

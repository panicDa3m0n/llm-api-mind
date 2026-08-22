# Release Process

Last reviewed: 2026-07-30
Status: active operational process; use current deployment and database
evidence rather than an old release note as proof of a live state

This project uses Git history, `CHANGELOG.md`, and roadmap documentation together. The goal is that commit analysis always maps back to concrete project progress.

From V1.0.1 onward, version selection and scope discipline are governed by
`docs/development-process.md`.

## Commit Identity

Local commits made by Codex/Scarlet should use a distinct repository-local Git author:

```txt
Scarlet Codex <scarlet-codex@users.noreply.github.com>
```

This does not create a real independent GitHub account. It separates commit author metadata from the human owner's local Git identity. The authenticated GitHub account that pushes the commits may still be the human owner's account.

If a real bot account is created later, update this document and the local Git config.

## Commit Message Format

Use this format for meaningful commits:

```txt
<type>(<scope>): <short summary>

Changelog:
- <user-visible or project-visible change>

Roadmap:
- <phase, experiment, ADR, or issue reference>

Verification:
- <tests/checks run, or why not run>
```

Recommended types:

```txt
docs
feat
fix
test
refactor
chore
experiment
```

Examples:

```txt
docs(governance): establish project memory and changelog discipline

Changelog:
- Added AGENTS.md, project blueprint, companion docs, and changelog.

Roadmap:
- Supports Phase 0 project foundation.

Verification:
- Inspected created files and initialized local Git repository.
```

## Changelog Policy

Update `CHANGELOG.md` for every meaningful change that affects:

- architecture;
- runtime behavior;
- API contracts;
- prompts;
- experiments;
- bug fixes;
- developer workflow;
- release process.

Small formatting-only edits can skip the changelog if they do not affect project meaning.

## Database Boundary Before Commit Or Deploy

Before committing, run:

```bash
python scripts/check_database_boundary.py --staged
```

This refuses accidental inclusion of the mutable laboratory snapshot
`backend/data/app.db`. The override is reserved for an explicitly reviewed
data release and must be recorded in the commit and changelog.

Before a VPS deployment, follow `docs/database-topology.md`: preserve the
canonical remote DB in place, exclude `backend/data/`, the deployment-root
`.env`, and any source-tree `backend/.env` from transfer, then run the new
image's read-only preflight with `--expect-role production` before restart.
Do not retain VPS release or database backups; Git/workspace history is the
code source of truth. Git pushes do not deploy runtime data.

The root `docker-compose.yml` is the versioned backend deployment baseline.
Feature-specific Compose overrides must also live in the repository and be
passed explicitly during build, preflight, restart, and rollback; do not leave
an active service topology only on the VPS.

## Product UI Artifact Parity

The protected web preview and Android APK are two delivery profiles of one
Product UI source tree. A release may use different asset and API bases, but it
must not use a different UI implementation, Core contract, or stale build.

For every Product UI publication:

1. identify the exact source commit and Product UI version;
2. build the web artifact only with `cd frontend && npm run build:vps`;
3. require `npm run verify:release:vps` to pass before copying that `dist/`
   tree to `/var/www/scarlet`;
4. replace the old static tree atomically without retaining a duplicate, then
   verify the authenticated public index, every asset it references, and
   `release-manifest.json` all return `200`;
5. build the APK only with `npm run android:debug`, which must complete
   `verify:release:android` after Gradle assembly; and
6. when a device is available, compare installed package id/version with the
   APK metadata and verify the real Product UI against the same VPS API.

`frontend/dist/` is intentionally one mutable build directory, not a store of
multiple release profiles. A generic or Android Vite build replaces it. The VPS
sequence must therefore be `build:vps` immediately followed by
`verify:release:vps` and publication. Android verification is performed from
the Capacitor-synced `android/app/src/main/assets/public/` artifact instead.

Never publish generic `npm run build` output to `/var/www/scarlet`: its root
asset base makes a path-hosted `/scarlet/` index load HTML while its JavaScript,
CSS, and runtime media return `404`. The release manifest is evidence of build
profile, source commit, product version, asset base, and API base; it does not
replace direct public-request verification.

## Documentation Mapping

Each meaningful commit should usually touch at least one project memory file:

```txt
docs/activity-log.md
docs/decisions.md
docs/bug-ledger.md
docs/experiments.md
docs/api-contract.md
CHANGELOG.md
```

Expected mapping:

- Architecture or tooling choice -> `docs/decisions.md`
- Work performed -> `docs/activity-log.md`
- Bug discovered or fixed -> `docs/bug-ledger.md`
- API behavior -> `docs/api-contract.md`
- Cognitive experiment -> `docs/experiments.md`
- User-visible/project-visible change -> `CHANGELOG.md`

## Branch And Release Strategy

Current strategy:

```txt
main: stable project history
feature branches: optional for larger slices
tags: v1.x milestones for verified baseline and later branch releases
```

Commits may go directly to `main` while the project remains local-lab oriented,
but they must be focused by declared scope. Larger slices may use feature
branches.

Version impact:

```txt
Fix             -> patch increment: 0.0.X
Implementazione -> minor increment: 0.X.0
Major release   -> major increment: X.0.0
```

## GitHub Remote Plan

Preferred remote repository name:

```txt
panicDa3m0n/llm-api-mind
```

Current remote:

```txt
origin https://github.com/panicDa3m0n/llm-api-mind.git
```

Preferred visibility:

```txt
private until the first runnable experiment is mature enough to publish
```

Current environment notes:

```txt
The GitHub connector can access installed repositories, but does not expose repository creation.
GitHub CLI 2.74.2 is installed at ~/.local/bin/gh and authenticated as panicDa3m0n.
HTTPS Git operations use the CLI credential helper with repo and workflow scopes.
Initial push was completed by the human owner.
Non-interactive HTTPS push from this environment succeeded on 2026-05-08.
SSH push is not currently available because GitHub rejects the local key.
The incorrect 2026-07-13 HTTPS credential was replaced on 2026-07-14.
```

Remote setup options:

1. Create the empty private repository on GitHub manually, then set:

```txt
git remote add origin https://github.com/panicDa3m0n/llm-api-mind.git
git push -u origin main
```

2. If GitHub CLI authentication expires, restore it from this folder:

```txt
~/.local/bin/gh auth login --hostname github.com --git-protocol https --web
~/.local/bin/gh auth setup-git
```

The V1.33.0 catch-up used a verified feature branch and PR #1 instead of
force-updating stale `main`:

```txt
git push -u origin feature/agent-modes-history-compaction
gh pr create --base main --head feature/agent-modes-history-compaction --draft
```

Release tags follow deployed truth. Annotated `v1.32.0` points to `298d668`,
its exact historical HoneyLabs runtime. V1.38.0 passed the protected VPS
backup, preflight, restart, maintenance, and smoke procedure at merge commit
`efe652e`; its release tag must point to that runtime commit rather than to a
later documentation-only commit.
V1.39.0 passed the same protected boundary plus active-compaction configuration,
schema, and natural native routing checks at merge commit `cb400d2`; annotated
tag `v1.39.0` points to that deployed runtime commit.
V1.40.0 passed the protected backup, read-only production preflight, restart,
integrity, frontend parity, and natural native smoke boundary at merge commit
`db31398`; annotated tag `v1.40.0` points to that deployed runtime commit.
V1.41.0 passed both remote quality workflows, protected backup, new-image
preflight, restart, integrity, frontend parity, native answer-obligation smoke,
and GPT bridge `help`/finalize smoke at merge commit
`10ecfb0c0aeeb458a7896887aaebad55cbd85277`; annotated tag `v1.41.0` points
to that deployed runtime commit.
V1.42.0 passed both remote quality workflows, protected backup, new-image
preflight, restart, integrity, frontend parity, native mode-routing smoke, and
GPT bootstrap/action/finalize smoke at merge commit
`fbdf431f7da1cd186a2c2b2cce90626c8f44ce6f`; annotated tag `v1.42.0` points
to that deployed runtime commit. The later documentation closure commit does
not move the runtime tag.
V1.43.0 passed both remote quality workflows, protected backup, new-image
preflight, restart, integrity, MCP proxy retirement, and authenticated GPT
bootstrap/help/finalize smoke at merge commit
`29c2852f9f34be8d888ab3921d15405094b9cb59`; annotated tag `v1.43.0` points
to that deployed runtime commit. Historical `mcp_bridge` rows remain canonical.
V1.50.0 reached the VPS at merge `7ef3a9b` but was deliberately not tagged or
release-accepted after two native smokes exposed repeated final-marker
omission. V1.50.1 passed both remote Quality workflows, protected online
backup, new-image and post-restart preflights, frontend parity, real native
memory/final-answer smoke, authenticated GPT bootstrap/help/finalize, and
post-smoke DB integrity at merge
`676e560a713610ff884631f70bbe6d9e6d8bc375`. Annotated tag `v1.50.1` points
to that exact deployed runtime commit; later documentation-only commits do not
move it.
V1.60.1 passed local quality gates, protected production backup, copied-DB
migration canary, new-image and post-restart preflights, public authentication
checks, and one real scheduled autonomous MiniMax M3 cycle at runtime commit
`0b37f7e8767adf16059e6c19291debff6eaa3779`. The VPS
`DEPLOYED_COMMIT` marker remains on that runtime commit; any later
documentation-only closure commit must not replace it.
V1.61.0 passed the complete local backend/frontend gates, protected online and
quiescent production backups, a copied-DB chronology-reset canary, new-image
read-only preflight, guarded archival reset, authenticated public health/UI,
and post-switch integrity at runtime commit
`d6a88b3add8f7e8c72f75bf60a44d16d5f196a5e`. The VPS
`DEPLOYED_COMMIT` marker points to that runtime commit; the archived chronology
remains canonical while the active replacement begins clean. The first
unforced activation in that replacement started within one worker interval,
completed with `end_turn`, preserved origin attribution, and scheduled the
next cycle at +600 seconds.

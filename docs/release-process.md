# Release Process

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

Before a VPS deployment, follow `docs/database-topology.md`: back up the
remote DB, exclude `backend/data/` and `backend/.env` from any transfer, then
run the new image's read-only preflight with `--expect-role production` before
restart. Git pushes do not deploy runtime data.

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

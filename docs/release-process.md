# Release Process

This project uses Git history, `CHANGELOG.md`, and roadmap documentation together. The goal is that commit analysis always maps back to concrete project progress.

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

Initial strategy:

```txt
main: stable project history
feature branches: optional for larger slices
tags: v0.x milestones once runnable slices exist
```

Early commits may go directly to `main` while the project is still foundation-only. Once backend implementation starts, prefer focused commits by slice.

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
The `gh` CLI is not installed in the local environment.
Initial push was completed by the human owner.
Non-interactive HTTPS push from this environment succeeded on 2026-05-08.
SSH push is not currently available because GitHub rejects the local key.
```

Remote setup options:

1. Create the empty private repository on GitHub manually, then set:

```txt
git remote add origin https://github.com/panicDa3m0n/llm-api-mind.git
git push -u origin main
```

2. Install and authenticate GitHub CLI, then create the repository from this folder:

```txt
gh repo create panicDa3m0n/llm-api-mind --private --source=. --remote=origin --push
```

Current next push command once credentials are available:

```txt
git push -u origin main
```

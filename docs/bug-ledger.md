# Bug Ledger

This file records bugs, fixes, root causes, and regression tests so the project does not rediscover the same problems across sessions.

No implementation bugs have been recorded yet.

## Template

```md
## BUG-0001 - Short Title

Date Found:
Status: open | fixed | monitoring
Symptoms:
Root Cause:
Fix:
Regression Test:
Related Files:
Notes:
```

## Known Environment Notes

### ENV-0001 - Repository Not Initialized As Git

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Running `git status` in the project root returns:

```txt
fatal: Not a git repository (or any of the parent directories): .git
```

Root Cause:

The project directory has not been initialized as a Git repository yet.

Fix:

Initialized the local Git repository on branch `main`. The release process documents local Git identity and remote setup options.

Regression Test:

Run `git status --short` from the project root.

Related Files:

- `AGENTS.md`
- `docs/activity-log.md`

Notes:

Not a code bug, but relevant because the development ritual expects repository state inspection. `git status --short` now works locally.

### ENV-0002 - GitHub Remote Creation Not Available From Current Tooling

Date Found: 2026-05-08  
Status: open

Symptoms:

- `gh --version` returns `zsh:1: command not found: gh`.
- The GitHub connector lists and writes to installed repositories, but does not expose repository creation.

Root Cause:

The local GitHub CLI is not installed, and the available GitHub connector tools do not include a create-repository operation.

Fix:

Pending one of:

- Create `panicDa3m0n/llm-api-mind` manually on GitHub, then add it as `origin`.
- Install and authenticate `gh`, then run the documented `gh repo create` command.

Regression Test:

Run:

```txt
gh --version
```

or confirm the remote exists:

```txt
git remote -v
```

Related Files:

- `docs/release-process.md`
- `docs/activity-log.md`

Notes:

Local Git can still be initialized and committed before remote setup.

### ENV-0003 - Local Git Version Lacks Some Modern Flags

Date Found: 2026-05-08  
Status: monitoring

Symptoms:

- `git init -b main` returns `error: unknown switch 'b'`.
- `git branch --show-current` returns `error: unknown option 'show-current'`.

Root Cause:

The installed Git version is older than the versions that support those newer flags.

Fix:

Use compatible commands:

```txt
git init
git checkout -b main
git rev-parse --abbrev-ref HEAD
```

Regression Test:

Run:

```txt
git rev-parse --abbrev-ref HEAD
```

Related Files:

- `docs/activity-log.md`

Notes:

This is an environment compatibility note, not a project bug.

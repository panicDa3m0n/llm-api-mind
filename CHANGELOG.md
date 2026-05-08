# Changelog

All meaningful project changes are tracked here.

This project uses a practical changelog rather than a release-only log: each meaningful commit should map to an entry under `Unreleased` or a dated release section.

## Unreleased

### Added

- Created the project governance foundation:
  - `AGENTS.md`
  - `docs/project-blueprint.md`
  - `docs/activity-log.md`
  - `docs/decisions.md`
  - `docs/bug-ledger.md`
  - `docs/experiments.md`
  - `docs/api-contract.md`
- Added Git and release discipline:
  - `.gitignore`
  - `.gitmessage`
  - `docs/release-process.md`
- Added Phase 1A backend scaffold:
  - FastAPI app factory;
  - typed environment configuration;
  - `GET /health`;
  - backend `.env.example`;
  - pytest health endpoint smoke test;
  - ADR-0004 documenting SQLModel as the MVP storage choice.

### Changed

- Updated project next steps to start from Git/repository setup and backend scaffolding.
- Connected the local repository configuration to `https://github.com/panicDa3m0n/llm-api-mind.git` and documented the remaining HTTPS push authentication blocker.
- Confirmed local `main` is synchronized with `origin/main` after the human owner completed the push.

### Fixed

- Initialized project tracking plan for the previously uninitialized Git repository state.
- Resolved the GitHub push blocker for the initial repository setup.

## Release Notes Policy

Each release section should answer:

- What changed?
- Why did it change?
- Which roadmap phase, experiment, or decision does it support?
- How was it verified?

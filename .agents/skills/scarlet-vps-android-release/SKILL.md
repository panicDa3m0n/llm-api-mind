---
name: scarlet-vps-android-release
description: Build, deploy, verify, and roll back Scarlet across the VPS, Product UI, and Android preview app. Use for publishing backend or frontend changes, aligning VPS behavior with local code, building or installing an APK, or diagnosing release configuration drift. Never transfer or mutate the production database as test data, and never deploy merely because code changed.
---

# Scarlet VPS And Android Release

## Purpose

Publish one verified Core-backed Product UI experience without losing production
data, secrets, configuration integrity, browser/mobile parity, or rollback
ability.

## Authoritative Sources

Read `AGENTS.md`, `docs/release-process.md`, `docs/database-topology.md`,
`docs/core-runtime-contract.md`, the relevant API/stream contract, and current
deployment evidence. Inspect the actual Docker, frontend, Android, and VPS
configuration rather than inferring it from a past release note.

## Release Preconditions

1. Confirm owner approval, branch/revision, scope, target version, and rollback
   point.
2. Inspect the worktree; do not release unrelated changes.
3. Run the focused tests and build required by the changed boundary.
4. Verify that browser and Android consume the same deployed Core API and
   event contract. UI fixtures must not masquerade as runtime state.
5. Run the read-only production database preflight and record a remote backup
   reference before restart.
6. Transfer code/artifacts only. Never transfer local databases, runtime
   `data/`, secrets, or remote `.env` files.

## Publish And Verify

- Build the backend/frontend/Android artifact from the declared revision.
- Apply the documented remote deployment procedure, then verify health,
  version, route/OpenAPI availability, logs, and the target configuration.
- Directly exercise the changed deployed surface. For stream/UI work, inspect
  live composition and reconnect/replay behavior where applicable.
- Verify the Android artifact package/version/API origin before installation.
- Record deployment evidence in the document that owns it. A release note is
  not proof by itself.

## Failure And Rollback

Stop on database-role mismatch, failed preflight, unknown remote revision,
missing backup reference, wrong endpoint, or failed smoke. Roll back code and
artifact together to the declared revision; do not "repair" a release by
copying a database. Preserve logs, traces, and exact observed behavior before a
follow-up fix.

## Maintenance Contract

Update this skill when a verified release, parity failure, rollback, or owner
correction identifies a missing preflight or safer recurring sequence. Update
release or deployment contracts first if the process semantics changed. Keep
incidents in their appropriate records rather than turning this skill into a
release diary. Update this skill in the same scoped task when it prevents
repetition, then run the skill validator.

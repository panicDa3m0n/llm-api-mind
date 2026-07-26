---
name: scarlet-vps-android-release
description: Build, deploy, verify, and roll back Scarlet across the VPS, Product UI, and Android preview app. Use when publishing backend or frontend changes, aligning VPS behavior with local code, building/installing an APK, or diagnosing release configuration drift. Never transfer or mutate the production database as test data, and do not deploy merely because code changed.
---

# Scarlet VPS And Android Release

## Purpose

Publish one reviewed source state without losing production data, secrets,
rollback assets, stream behavior, or web/Android parity.

## Authoritative Sources

Read before release work:

- `docs/release-process.md`
- `docs/development-process.md`
- `docs/database-topology.md`
- `docs/quality-gates.md`
- `docs/api-contract.md`
- `docs/stream-v2-contract.md`
- `frontend/README.md`
- the current deployment entries in `docs/activity-log.md`

Inspect current compose, container, Nginx, environment-profile, Capacitor,
Android, and build scripts. Use the deployed host state as evidence, not as an
unreviewed source to copy back into the repository.

## Release Preconditions

1. Identify the exact source commit and confirm the intended branch.
2. Confirm scope, version metadata, changelog, and database migration needs.
3. Run focused tests plus the applicable quality gates.
4. Confirm the working tree does not contain an accidental DB, secret, build
   output, or unrelated change.
5. Record current VPS image/container/config/static versions and rollback
   locations.

## Production Database Boundary

- The VPS database contains real production data. Never replace it with a
  repository or test database.
- Take a timestamped remote backup before any rollout that can touch backend
  code, schema, or containers.
- Verify backup existence and perform the configured SQLite preflight.
- Exclude `backend/data`, repository and backend `.env` files, credentials, and
  local build artifacts from code transfer.
- Run mutating canaries only on an isolated copied database.
- After rollout, rerun integrity and application preflights against production
  without creating test sessions or memories.

## VPS Workflow

1. Transfer or fetch the exact reviewed commit with explicit exclusions.
2. Build a new tagged backend image without replacing the running container.
3. Run import, configuration, migration-readiness, and health checks against
   the new image.
4. Run a copied-DB canary when data behavior changed.
5. Back up active Nginx configuration and Product UI static output when those
   surfaces change.
6. Switch the service only after preflight succeeds.
7. Verify local container health, public authenticated health, OpenAPI/version,
   and affected endpoints.
8. For streaming changes, verify headers, early chunk delivery, durable replay,
   same-turn recovery, and no proxy buffering.
9. Retain the previous image/config/static/database backup until acceptance.
10. Record the deployed commit rather than copying a later documentation-only
    commit into runtime metadata.

Rollback immediately when health, migration, authentication, streaming, or
data integrity fails. Restore the previous container/config/static artifact;
restore the database only when evidence proves the rollout mutated it
incorrectly.

## Product UI Workflow

- Build with the intended Vite profile, especially `vps` for HoneyLabs.
- Verify asset base paths, API URL, authentication forwarding, and no embedded
  unintended authoring assets.
- Exercise mobile and desktop rendering with console/network inspection.
- Confirm Product UI consumes Core contracts and does not invent cognition,
  memory, or completion state.

## Android Workflow

1. Use the supported Node, JDK, Android SDK, Capacitor, and Gradle versions.
2. Build through the repository command documented in `frontend/README.md`.
3. Inspect package id, version name/code, API URL, bundled files, and
   credentials policy.
4. Install on the connected device and start from a cold app state.
5. Verify login, dashboard hydration, new and existing sessions, live chat
   blocks, reconnect/replay, tool waiting states, final answer, and logout.
6. Inspect `adb logcat`, WebView console/network behavior, and backend events
   for failures that the screen alone may hide.

The current `scarlet/scarlet` pair is a temporary owner-approved preview gate,
not production identity or a secret.

## Release Evidence

Record:

- source and deployed commit;
- version and changed surfaces;
- backup and rollback assets;
- deterministic checks and canary;
- public/VPS/device observations;
- database integrity outcome;
- known residual risks and acceptance status.

Do not claim web, Android, and native runtime parity unless each relevant
surface was actually checked.

## Maintenance Contract

Update this skill after every verified deployment lesson, rollback, build
failure, device incompatibility, configuration drift, or safer production-data
procedure. Add evidence-backed checks and remove obsolete commands when the
repository changes. Keep `docs/release-process.md`,
`docs/database-topology.md`, deployment records, and this skill aligned. Never
store secrets, host credentials, ephemeral backup names, or machine-specific
paths in the skill.

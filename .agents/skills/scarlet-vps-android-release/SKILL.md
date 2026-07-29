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
  local build artifacts from code transfer. A broad source transfer must also
  exclude every `*.db`, `.tmp`, and cache path; prefer an explicit changed-file
  transfer when possible because ignored SQLite residues may exist outside
  `backend/data`.
- Run mutating canaries only on an isolated copied database.
- After rollout, rerun integrity and application preflights against production
  without creating test sessions or memories.

## VPS Workflow

1. Transfer or fetch the exact reviewed commit with explicit exclusions.
2. Build a new tagged backend image without replacing the running container.
3. Run import, configuration, migration-readiness, and health checks against
   the new image.
4. Run a copied-DB canary when data behavior changed.
5. Before enabling coordination logic that treats persisted rows as live
   foreground state, audit production for stale active statuses and verify the
   lease or freshness rule against a copied database.
6. Execute guarded one-time production commands end to end on a copied
   production database, including receipt serialization after commit; a
   successful mutation followed by a reporting failure is still a failed
   canary.
7. Back up active Nginx configuration and Product UI static output when those
   surfaces change.
8. Switch the service only after preflight succeeds.
9. Verify local container health, public authenticated health, OpenAPI/version,
   and affected endpoints.
10. For streaming changes, verify headers, early chunk delivery, durable replay,
   same-turn recovery, and no proxy buffering.
11. When ingestion, scheduling, maintenance, or event coordination changed,
    compare relevant event/window counts and timestamps across a bounded
    observation interval. A healthy endpoint alone cannot detect a recursive
    receipt loop or a worker that fails between ticks.
12. Retain the previous image/config/static/database backup until acceptance.
13. Record the deployed commit rather than copying a later documentation-only
    commit into runtime metadata.

Rollback immediately when health, migration, authentication, streaming, or
data integrity fails. Restore the previous container/config/static artifact;
restore the database only when evidence proves the rollout mutated it
incorrectly.

## Product UI Workflow

- Build with the intended Vite profile, especially `npm run build:vps` for
  HoneyLabs. Never publish a generic root-hosted `npm run build` artifact to
  `/var/www/scarlet`.
- Run `npm run verify:release:vps` against the exact `dist/` about to be
  published. It must prove the `/scarlet/` asset base, `/scarlet-api` base,
  Product UI contract fragments, referenced static files, and release manifest.
- Back up the active `/var/www/scarlet` tree, publish only the verified VPS
  artifact, then request the protected index and every referenced script,
  stylesheet, image, and media asset over the public URL. Every reference must
  return `200`; an HTML `200` alone is not a successful web release.
- Record the public `release-manifest.json` source commit, product version,
  build profile, asset base, and API base as part of release evidence.
- Verify authentication forwarding and no embedded unintended authoring assets.
- Exercise mobile and desktop rendering with console/network inspection.
- Confirm Product UI consumes Core contracts and does not invent cognition,
  memory, or completion state.

## Android Workflow

1. Use the supported Node, JDK, Android SDK, Capacitor, and Gradle versions.
2. Build through `npm run android:debug`; do not reuse a prior APK merely
   because its filename is unchanged. The command must finish with
   `npm run verify:release:android`.
3. Inspect package id, version name/code, API URL, bundled files, release
   manifest, and
   credentials policy.
4. Install on the connected device and start from a cold app state.
5. Verify login, dashboard hydration, new and existing sessions, live chat
   blocks, reconnect/replay, tool waiting states, final answer, and logout.
6. Inspect `adb logcat`, WebView console/network behavior, and backend events
   for failures that the screen alone may hide.

The current `scarlet/scarlet` pair is a temporary owner-approved preview gate,
not production identity or a secret.

When a secure device lock prevents foreground interaction, never bypass it.
CDP DOM evidence may confirm that a hidden WebView mounted and emitted native
plugin data, but it is not visual acceptance; defer screenshot, motion,
foreground lifecycle, and touch-flow claims until the owner unlocks the
device. If the locked device has no transport, use the outbox as evidence.
Any temporary host-side request forwarding must be documented as test
transport and must not synthesize or rewrite observation payloads.

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

Update this skill and fix it after every verified deployment lesson, rollback,
build failure, device incompatibility, configuration drift, missed parity
check, or safer production-data procedure. When an error or a newly verified
solution would prevent a repeat failure, add the smallest evidence-backed rule
here during the same task and remove obsolete commands when the repository
changes. Keep `docs/release-process.md`,
`docs/database-topology.md`, deployment records, and this skill aligned. Never
store secrets, host credentials, ephemeral backup names, or machine-specific
paths in the skill.

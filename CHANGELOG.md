# Changelog

All meaningful project changes are tracked here.

This project uses a practical changelog rather than a release-only log: each meaningful commit should map to an entry under `Unreleased` or a dated release section.

## Unreleased

### V1.60.1 - Fresh Human-Turn Foreground Guard

#### Fixed

- Ignore historical human turns left in `started` state when deciding whether
  an autonomous cycle must yield. Only turns started inside the configurable
  six-hour freshness window can hold foreground priority.
- Preserve the underlying historical records as evidence rather than mutating
  production data during deployment.

### V1.60.0 - Autonomous Cognitive Cycles

#### Added

- Add one long-lived `scarlet_autonomous` session per profile, with a separate
  provider chronology for Scarlet's scheduled internal activations.
- Add persisted activation scheduling, leasing, deferral during active human
  turns, failure evidence, outcomes, and a configurable observation cadence
  currently set to 600 seconds.
- Add cooperative foreground priority: a cycle already in progress yields at
  the next provider boundary or before its next tool when a human turn starts,
  preserving partial evidence and rescheduling itself as deferred.
- Add a compact autonomous context containing current mode, local time, recent
  human-session and memory hooks, focus, due intentions, affect, and a
  perception availability index.
- Add an append-only perception inbox with per-channel state and
  per-autonomous-session cursors plus `perception status|open|read` shell
  commands. Opening a channel advances its inspection cursor without deleting
  or rewriting source events.
- Add `/api/autonomy/overview`, `/api/autonomy/history`,
  `/api/autonomy/run-now`, and `/api/autonomy/perception/events/batch`.
- Add a chat-header internal-cognition control that renders autonomous cycles
  as a chronological conversation-like stream of personal notes, tool
  actions, expandable thinking, and internal checkpoints.

#### Changed

- Classify sessions and turns by lifecycle so autonomous cognition cannot
  appear in `previous_sessions` or inherit human provider history.
- Treat `interactive` as system-owned only for human-message turns. Autonomous
  turns resume `idle` or `scouting` through an explicit runtime trigger.
- Extend Scarlet's fixed policy with a strict distinction among human turns,
  autonomous activations, and backend maintenance.
- Normalize Pydantic validation details at the cognitive-operation boundary so
  recoverable malformed shell commands cannot leak live exception objects into
  provider JSON and abort an autonomous cycle.
- Advance backend, frontend, Android, and module-conformance metadata to
  V1.60.0.

#### Safety Boundary

- Autonomous cycles may inspect and mutate supported cognitive organs, but do
  not fabricate a user message, send a user notification, or perform an
  external/device action.
- The new perception endpoint is an ingestion contract only. No Android
  notification collector or Device Exploration record is admitted
  automatically in V1.60.0.
- The canonical activation, message, event, trace, and tool evidence remains
  persistent even when provider-history compaction is later applied.

#### Verification

- All 320 backend tests, Ruff, the 45-file mypy gate, documentation integrity,
  project-skill validation, and the frontend TypeScript/Vite production build
  pass.
- A deterministic provider cycle proves exclusive-session reuse, private
  streaming chronology, tool-call persistence, perception cursors, and the
  600-second scheduler contract.
- One isolated real MiniMax M3 cycle completed in 45 seconds with five
  successful shell actions, three authored orientation notes, correct
  non-human/no-op discipline, and one persisted internal checkpoint.
- Product UI inspection passed at `390x844` and `1440x1000`: the real
  Chat header opens the autonomous chronology, thinking expands, requests stay
  `200`, and the browser reports no warning or error.

### V1.59.0 - Semantic Context Families

#### Added

- Add a typed context-family registry for current V2 cognition and future
  human, human-device, Scarlet-sensor, relationship, environment, and operation
  evidence.
- Add compact packet validation with offset-aware evidence time, navigable
  source references, subject/observer separation, evidence kinds, mode tags,
  activation contracts, and required policy blocks.
- Add a shadow semantic-routing receipt to `model.context.projection_audit`
  without changing Scarlet's live V2 payload.

#### Safety Boundary

- Unknown families and invalid source/evidence combinations fail closed.
- Device location remains device evidence; human situated presence requires a
  separate derived packet.
- Human-device camera/audio is not Scarlet first-person perception.
- Device Exploration observations and every newly registered future family
  remain outside live model context.

#### Verification

- All 314 backend tests, Ruff, the 45-file mypy gate, documentation integrity,
  database boundary, and the frontend production build pass.
- Three bounded MiniMax scenarios preserve device/human, phone-camera/Scarlet,
  and dispatch/receipt boundaries.
- A repeated route-deviation probe confirms that policy blocks must be composed
  as instructions while packets remain evidence.

### Companion Product Planning

- Preserve the `Resta con me` safeguard-companion concept, shared life threads
  with contextual initiative, Android and personal-information source
  exploration, and a future dynamically composed system-prompt architecture.
- Preserve the future Android activation/action inventory and define the first
  architecture checkpoint for 15-minute Scarlet autonomous cycles, explicitly
  separate from human turns and backend maintenance.
- Record one long-lived, profile-scoped autonomous session as Scarlet's
  periodic internal chronology, connected through API Mind to human-session
  summaries, memory, organs, perception, and exact source navigation without
  mixing provider histories.
- Define future perception as an append-only evidence ledger with derived
  channel state, inspection cursors, bounded batches, receipts, and a compact
  model-visible availability index rather than destructive notification or
  sensor caches.
- Keep the historical V1.59.0 boundary explicit: V1.58.1 did not deliver
  device observations, communication data, or new prompt blocks to Scarlet,
  and V1.59.0 did not yet run autonomous model cycles. V1.60.0 implements the
  activation and perception-inbox substrate without admitting a native device
  source.

### V1.58.1 - Device Exploration Signal Integrity

#### Fixed

- Suppress only consecutive duplicate Capacitor network callbacks with the
  same connectivity and transport state, preventing observation uploads from
  producing a self-sustaining network-event loop.
- Preserve real offline, cellular, and Wi-Fi transitions in their native
  order.

#### Verification

- TypeScript/Vite Android production build and Capacitor sync pass.
- The physical-device foreground run kept network history at one snapshot
  while motion advanced from 8 to 20 samples over 35 seconds.
- A real Wi-Fi disable/enable cycle still produced the complete
  `wifi -> none -> cellular -> wifi` transition sequence.
- Foreground location, notification delivery and interaction, lifecycle
  background/resume, stationary motion, and haptic behavior were inspected
  directly without admitting observations into Scarlet's cognition.

### V1.58.0 - Device Exploration Layer

#### Added

- Add an isolated, append-only Device Exploration ledger and authenticated API
  for raw and normalized Android observations.
- Add an Android Product UI laboratory for device/app identity, battery,
  lifecycle, network, sampled motion, explicit location, local notifications,
  and haptic receipts.
- Add an install-local retry outbox with idempotent batch delivery and
  per-screen exploration run identifiers.

#### Changed

- Add the Capacitor App, Device, Geolocation, Haptics, Local Notifications,
  Motion, and Network integrations needed for bounded device experiments.
- Make observation-list totals honor all active filters and flush the initial
  native snapshot before loading the current run history.
- Advance backend, frontend, Android, and module-conformance metadata to
  V1.58.0.

#### Safety Boundary

- Device observations are not chat history, semantic memory, focus, affect,
  volition, runtime context, provider history, traces, or model-facing tools.
- No observed signal is routed into Scarlet automatically; future admission
  requires separate evidence, design, and owner approval.

#### Verification

- Focused API tests prove append-only idempotency, filtered totals, summary
  aggregation, unknown-field rejection, and absence of writes to sessions,
  memories, and traces.
- Ruff, the blocking mypy gate, TypeScript/Vite, Capacitor sync, Android debug
  assembly, protected VPS deployment, and physical-device use pass.
- Eight physical-device runs produced 51 native records, recovered an 18-event
  offline outbox, deduplicated a real replay, and completed a haptic effect.
  Locked/background location timed out, one notification remained pending, and
  foreground motion/lifecycle behavior remains explicitly unverified.
- A ninth run against the deployed fix raised the ledger to 57 records and
  showed the six-record current-run history immediately with an empty outbox;
  secure-lock visual screenshot acceptance remains pending.

### V1.57.0 - Hybrid Product Chat Live Delivery

#### Added

- Add `scarlet-live-v1`, a connection-local NDJSON overlay that interleaves
  transient thinking/text/tool-input frames with unchanged durable Stream V2
  events.
- Add compact recent-memory, previous-session, and answer-validation lifecycle
  events for ordered consumer activity blocks.
- Add five repository-local Codex skills for Scarlet project stewardship,
  cognitive changes, runtime debugging, E2E evaluation, and VPS/Android
  releases, with evidence-driven maintenance contracts and CI validation.
- Add Android WebView CORS support for packaged localhost origins and the
  temporary preview authorization header.

#### Changed

- Keep Stream V2 as the sole durable replay/reconnect authority and recover an
  interrupted live response on the same turn for at most five attempts.
- Compose Product Chat blocks in place with stable lifecycle identities,
  model-authored Mind action intent, near-bottom streaming autoscroll, and
  terminal replay reconciliation.
- Use an immediate UI-owned orientation state during synchronous turn
  preflight; it is not Scarlet-authored speech or persisted cognition.
- Disable Capacitor HTTP global fetch patching so the Android WebView receives
  browser stream chunks instead of one buffered native response.
- Advance backend, frontend, Android, OpenAPI, and module conformance metadata
  to V1.57.0.

#### Fixed

- Prevent new-session hydration from overwriting live events and eliminate the
  need to leave and reopen Chat to see persisted progress.
- Prevent thinking, text, tool, and validator start/completion milestones from
  rendering as duplicate blocks.
- Show a pending validator block during long semantic answer checks instead of
  presenting a silent healthy backend.

#### Verification

- 57 focused backend tests pass for runner, live/V2 stream, chat API, bridge,
  model-context behavior, and the agentic module SDK.
- A blocking-provider test proves a transient frame arrives before the native
  turn completes; API tests prove ordered frames/events, durable replay, and
  Android WebView CORS preflight.
- Ruff, focused mypy, TypeScript/Vite production build, Android debug assembly,
  production database preflights, and isolated copied-DB canary pass.
- V1.57.0 is deployed from commit `3a7d59e`; public OpenAPI exposes the live
  endpoint, packaged-origin CORS works without weakening Basic Auth, the
  Product UI is live, and the previous backend/config/database artifacts are
  retained for rollback.

### V1.56.1 - Android Preview Test Access

#### Fixed

- Make `scarlet/scarlet` the explicit Android preview account and verify that
  pair against the protected VPS `/health` endpoint before opening the Product
  UI.
- Preserve the infrastructure boundary: unauthenticated VPS requests still
  receive `401`, credentials stay in application memory only, and logout or a
  failed verification clears them.
- Document the known test pair truthfully as an intentionally compiled preview
  credential, not as a secret or production account boundary.
- Align Android, frontend, backend, OpenAPI, and module-conformance version
  metadata to V1.56.1.
- Prevent reverse-proxy buffering on Stream V2 so persisted context, memory,
  thinking, tool, note, and state blocks reach Product Chat while Scarlet is
  working instead of arriving together with the final answer.

#### Verification

- Protected VPS authentication returns `401` without credentials and `200`
  with `scarlet/scarlet`.
- Stream V2 response and reconnect contracts explicitly emit
  `X-Accel-Buffering: no` and `Cache-Control: no-cache, no-transform`.
- APK V1.56.1 installed on Samsung SM-S918B / Android 14, accepted
  `scarlet/scarlet`, and hydrated Home from real VPS sessions and memories
  without application `401`, `500`, JavaScript, or native errors.
- Focused Stream V2 tests, VPS-profile build, and dependency audit pass; final
  physical-device acceptance checks incremental block composition during a
  real Scarlet turn.
- V1.56.1 is deployed from commit `acffb10`; pre/post production DB preflights
  remain direct and healthy, OpenAPI reports the new version, and the public
  stream is chunked through an explicitly unbuffered Nginx location.

### V1.56.0 - Product UI Web And Android Delivery

#### Added

- Add a versioned Capacitor 7 Android project for package
  `cloud.honeylabs.scarlet`, with API traffic directed to the protected
  HoneyLabs VPS and a reproducible cross-platform debug build command.
- Add explicit Vite `vps` and `android` build profiles that mount the connected
  Product UI as the primary experience.
- Add native-only in-memory Basic Auth forwarding from the existing test login;
  no preview credential is embedded or persisted in the APK.

#### Changed

- Resolve Product UI media through the configured Vite base path so the same
  source works under `/scarlet/` and inside a Capacitor WebView.
- Validate Android credentials against the protected VPS health endpoint
  before opening the Product UI; native credentials remain memory-only and
  the obsolete local-demo copy is not shown in the APK.
- Package only the approved runtime portrait and greeting video. PSDs,
  references, rig workspaces, and other avatar-authoring assets remain in the
  repository but are excluded from web and Android delivery.
- Move the four retained PSD research files out of `frontend/public` into the
  Git LFS-backed `frontend/avatar-authoring/psd` archive.
- Advance backend, frontend, OpenAPI, module-conformance, and Android version
  metadata to V1.56.0.

#### Verification

- VPS-profile Vite build passes with 2,035 transformed modules and a 4.2 MB
  delivery directory.
- Mobile browser smoke at `390x844` renders the splash with no console errors;
  all Scarlet static and media assets return `200` or `206`.
- Capacitor sync and clean Android debug assembly pass with JDK 21. The 7.5 MB
  APK reports package `cloud.honeylabs.scarlet`, version code `15600`, version
  `1.56.0`, API 23 minimum, API 35 target, the HoneyLabs API URL, and no
  embedded Basic Auth credential.
- Headless Android API 36 smoke reaches the native login after the startup
  greeting and confirms the connected VPS authentication copy. A first
  screenshot taken during media decoding was blank; a bounded follow-up
  confirmed that WebView and assets loaded without a JavaScript or native
  crash.

### V1.55.4 - Native Runtime And Product UI Integration

#### Changed

- Rebuild the MiniMax/Anthropic-compatible turn lifecycle around native stop
  reasons: continue `max_tokens`, execute tools only on `tool_use`, close only
  on `end_turn`, remove `<scarlet-final/>` and semantic finality fallback, and
  retain provider-exposed thinking as inspectable debug evidence.
- Add five-attempt recovery for transient provider-stream failures, bounded
  pathological `max_tokens` protection, connection-independent V2 turn
  execution, same-turn cursor resume, and a frontend V2 transport that
  reconnects at most five times after clean or exceptional stream closure.
- Integrate the Windows Product UI with the current native runtime, retaining
  real Core hydration, replay, responsive flows, SDK Windows portability, and
  the historical-documentation checker allowlist.
- Advance backend and frontend development targets to V1.55.4.

#### Fixed

- Remove the UI-only fake thinking bubble and replace over-specific
  deterministic narration with event-grounded consumer copy.
- Preserve completed provider thinking in Stream V2 during development and
  expose it through an enabled-by-default, locally hideable evidence view.
- Combine paged event replay with same-turn reconnect instead of regressing to
  the one-connection Windows transport.
- Correct stale documentation that still described the connected Product UI
  as fixture-only.
- Upgrade the transitive PostCSS toolchain to remove the audited source-map
  path-traversal vulnerability.

#### Verification

- The isolated Windows branch passed 305 backend tests, Ruff, frontend build,
  and a real desktop/mobile browser smoke before integration.
- The integrated branch passes 301 backend tests, full Ruff, incremental mypy,
  documentation integrity, zero-vulnerability npm audit, frontend production
  build, and an isolated desktop/mobile browser smoke.
### V1.55.3 - MiniMax M3 Provider-Terminal Finality

#### Changed

- Treat a non-empty MiniMax M3 response with `stop_reason=end_turn` as the
  authoritative native final-answer boundary.
- Retain `<scarlet-final/>` only as backward-compatible input that is stripped
  before persistence; the model is no longer instructed or required to emit it.
- Record `provider_stop_reason` and `boundary_source` in answer-validation
  traces.
- Advance backend/frontend development identity to V1.55.3.

#### Fixed

- Stop rejecting complete M3 answers merely because they omit the project-local
  private marker.
- Keep `max_tokens`, empty terminal output, and failed semantic obligations on
  the existing bounded recovery/failure path.
- Restore the Linux quality gate by normalizing checker imports and preserving
  the executable mode of the documentation checker.
- Keep BUG-0100's 21 explicitly retired avatar artifact paths as historical
  documentation references while continuing to reject other missing paths.

#### Verification

- Focused native answer, stream, obligation, model-facing, and SDK contracts
  pass `62/62`; Ruff and focused mypy pass on the changed Python surface.
- A real MiniMax M3 Stream V2 turn completed on its first markerless
  `end_turn`, persisted the assistant response, and emitted `turn.completed`.
- Frontend production build, database boundary, diff, and documentation
  integrity checks pass; the checker explicitly excludes the 39 references to
  21 avatar artifacts retired by BUG-0100.
- The complete CI Ruff target passes with the same command used by GitHub
  Actions.

### V1.55.2 - Product Chat Activity Evidence

#### Added

- Render the real Stream V2 context, memory, thinking, tool, focus, affect,
  volition, note, answer, and failure movements as ordered consumer bubbles.
- Add an immediate live `Scarlet sta pensando` state while the first persisted
  activity event is arriving, then reconcile it with the canonical stream.
- Make every semantic movement bubble keyboard/click inspectable through a
  centered responsive modal with sequence, phase, visibility, links, facts,
  and the bounded Stream V2 receipt.
- Add a persisted local `Evidenze private` setting. Protected events become
  visible as metadata receipts when enabled and are removed again on logout.

#### Changed

- Group duplicate tool lifecycle events into one evolving action bubble and
  derive completed/live state from canonical turn terminals.
- Remove the unrequested Core/provider status banner from Product screens.
- Remove `height` and `min-height` declarations from the scoped Product
  document roots; long pages retain body/document scrolling while Chat keeps
  its dedicated viewport-internal layout.
- Advance backend/frontend development identity to V1.55.2.

#### Fixed

- Stop filtering consumer-safe diagnostic activity before Chat can narrate it.
- Use the real `memory.context.built.selected_count` field instead of relying
  on an optional selected-record array.
- Strip `llm.thinking.captured.payload.text` from Stream V2 while preserving
  `has_text`, order, phase, model step, links, and internal trace evidence.
- Correct the local laboratory override from MiniMax M2.7 to MiniMax M3 and
  verify the active backend model through `/health`.

#### Verification

- Focused Stream V2 and SDK tests pass `12/12`; the contract proves
  captured-thinking text is absent from live and replay payloads.
- Playwright/Edge passes live MiniMax M3 activity streaming and deterministic
  replay, centered event inspectors on desktop/mobile, protected evidence
  persistence/redaction, logout cleanup, failed-turn replay, fixed Chat
  chrome, and real page scrolling.
- Ruff, focused mypy, npm audit, frontend production build, and repository
  diff checks pass.

### V1.55.1 - Product UI Browser Regression Fixes

#### Added

- Add a repeatable Playwright/Edge Product UI smoke covering local
  Splash/video-to-Login transition, local authentication, registration
  unavailability, session persistence, Core hydration, real session creation,
  optional live V2 chat, session replay, memory search/detail, settings save,
  unavailable modals, logout, mobile scrolling, fixed Chat chrome, console
  errors, HTTP failures, and horizontal overflow.

#### Fixed

- Preserve a failed V2 turn as one canonical consumer error bubble after
  replay even though the persisted terminal retains diagnostic visibility;
  do not duplicate it as a transport failure during the live stream.
- Translate `llm.incomplete_response` into concise Italian consumer copy
  without exposing validation/debug details.
- Declare the existing Scarlet portrait as the application favicon so browser
  runs no longer emit the pre-existing `/favicon.ico` 404.

#### Verification

- Repeatable desktop `1440x1000` and mobile `390x844` UI smoke passes against
  the real local Core with clean console/network results.
- One live MiniMax V2 greeting completes through the UI; one persisted failed
  turn replays as exactly one translated error bubble.
- Frontend production build, 10 focused Stream V2/SDK tests, Ruff, npm audit,
  and repository diff checks pass.

### V1.55.0 - Scarlet Product UI Core Integration

#### Added

- Connect `/prototype` Home, Chat, Memory, Sessions, Profile, Settings, and
  health status to the existing Core contracts without adding new endpoints.
- Add a typed `scarlet-stream-v2` browser consumer with paged replay,
  envelope/idempotency/gap validation, public-event projection, persisted
  history fallback, terminal-event enforcement, and reconnect replay.
- Add one accessible centered `Funzione non disponibile` modal for
  registration, behavioral switches, notifications, privacy export/account
  deletion, consumer maintenance, voice, avatar preferences, and other
  capabilities not implemented by the Core.

#### Changed

- Replace Product fixtures and fake success feedback with real session,
  message, memory, profile, settings, and health data; offline mode remains
  explicit and never substitutes demonstration records.
- Persist the supported display-name, language, country, timezone, and privacy
  fields through `/api/dashboard/settings`; keep local `scarlet/scarlet` login
  only as the approved test-access boundary.
- Advance backend/frontend development identity to V1.55.0 and declare
  `tzdata` on Windows so real dashboard profile/settings routes can resolve
  IANA timezones.
- Launch Python Agentic Module entrypoints through the active interpreter so
  standalone SDK and real-host conformance work on Windows as well as POSIX.
- Restore explicit route-scoped `height: auto`/`min-height: 100%` overrides so
  long Product pages scroll despite the cockpit's global fixed-height base,
  while Chat retains its dedicated `100dvh` internal-scroller contract.

#### Verification

- Frontend TypeScript/Vite production build passes.
- Real Chrome against an isolated `CODEX_TEST` Core passes login, real Home
  hydration, session creation/resume, Chat V2 surface, real settings save,
  unavailable-feature modals, mobile page scroll, and fixed Chat layout at
  `1440x1000` and `390x844`, with no API `5xx` or horizontal overflow.
- Focused and complete backend, SDK, lint/type, documentation, and database
  boundary results are recorded in the V1.55.0 activity entry: 304 tests pass
  at 82.32% coverage, Ruff/mypy pass, npm audit is clean, and OpenAPI remains
  at 30 operations. The documentation checker retains only its 39 historical
  missing avatar-workspace references.

- Add the first complete semantic turn flow to prototype Chat: user message,
  context, memory, bounded reflection status, authentic public note, grounded
  action receipts, focus state, and Scarlet's final answer as ordered bubbles.
- Preserve the authored/projection boundary in Chat: notes and answers remain
  Scarlet's original text, operational bubbles use consumer-safe first-person
  narration with their source event families retained in the inspectable JSON,
  and private chain-of-thought is never rendered.
- Make `/prototype` restore the locally authenticated user and last open
  Product view after reload/reopen, while explicit logout removes that local
  session and returns to authentication.
- Replace staged splash timers with real portrait/font/media readiness, start
  the already-preloaded greeting as soon as the application is ready, and play
  its first `52%` at natural `1x` speed before the immediate Login transition.
- Rebuild Chat as a viewport shell: compact fixed Scarlet header, internally
  scrolling messages, persistent composer, non-overlapping mobile dock, and
  desktop continuity/JSON rail.
- Remove the repetitive shared Product header and use one five-destination
  bottom dock on mobile and desktop; move the real logout control to the top of
  Settings.
- Add readable fixture JSON surfaces to Chat, Memory, Sessions, and Profile,
  plus fake profile, privacy, maintenance, extra, export, deletion, and
  prompt-rule preference controls.
- Refine Memory for extended counts and numbered records, and replace the
  Settings card grid with one grouped surface separated by lightweight Scarlet
  rules, switches, and multi-command rows.
- Fix prototype page scrolling with an explicit route-scoped overflow mode
  while leaving `height` and `min-height` unset at the prototype document
  level, preserving the existing real clients.
- Add coherent fixture-backed Chat, Memory, Sessions, and Profile first passes
  behind the Home navigation, including fake message send, memory search and
  detail, session resume/new flows, local preferences, and logout.
- Connect every existing Home destination: primary conversation actions,
  summary cards, individual memories, recent-session resume buttons, desktop
  navigation, mobile dock, and profile control.
- Add the first post-login Home dashboard to `/prototype`: an integrated
  Scarlet hero, three quick system summaries, latest-memory and recent-session
  cards, responsive desktop/mobile navigation, and simulated new/resume
  actions backed only by explicit local fixtures.
- Route successful fake authentication to Home while keeping every dashboard
  datum and interaction disconnected from the backend and database until the
  complete screen flow is visually approved.
- Preload the Scarlet greeting in parallel with splash startup, keep it paused
  and hidden during checks, play it once from zero after application readiness,
  and transition to Login only after the greeting ends.
- Refine the application entry UI by preserving white primary-button labels
  above the animated hover fill, removing the authentication card's decorative
  left edge, and moving splash progress into Scarlet's spoken status while
  reserving the page footer for copyright and version.
- Extend `/prototype` from splash-only review into the first complete
  application-entry sequence: bounded startup loader, simulated local update
  check, automatic transition to authentication, and direct review URLs.
- Add one responsive Scarlet-branded authentication card with Login and
  Registrazione tabs, inline validation, password visibility, in-session fake
  registration, and the test account `scarlet/scarlet`.
- Pause the layered Scarlet puppet as active Product UI work while preserving
  its artifacts and findings for future research.
- Add an identity-locked static portrait contract, initial emotional-state
  catalog, and an approved supporting 360-degree reference pack with eight turntable
  directions, exposed rear costume, bilateral hand/cuff details, and a visual
  contact sheet.
- Add the owner-supplied HappyHorse startup greeting as a cropped, muted splash
  bubble with canonical portrait fallback, reduced-motion handling, and one
  full first pass followed by a `2s -> end` loop.
- Add a cross-machine checkpoint for the complete Product UI/avatar workspace,
  track every PSD and the explicitly reviewed laboratory snapshot through Git
  LFS, and document clone/materialization requirements.

- Add a repeatable structural audit for the supplied layered `Poopoo.psd` and
  constrain it to hierarchy, clipping, blend-mode, and asset-inventory
  reference without permitting any artwork reuse.
- Rebuild the Scarlet V2 PSD as a complete Poopoo-informed but more articulated
  rig hierarchy, preserving 19 generated Scarlet assets as hidden native crops
  for owner-controlled Photoshop placement.
- Align avatar shading with the observed layered-character method: painted
  material rendering inside assets, clipped local overlays, and additive eye or
  suit emission only when independently controllable.
- Standardize every Scarlet anatomical iteration on one generated-only
  workflow: chroma-to-alpha input, transform-only registration, fixed proof
  suite with explicit target/alignment diagnostics, and a bottom-to-top PSD
  with the locked reference first.
- Remove the rejected hybrid cyan-forelock candidate and forbid copying or
  patching portrait/T-pose pixels into generated anatomical assets.
- Add the first post-reset Scarlet anatomical candidate: an owner-approved
  right upper lash/liner with transparent and full-canvas exports, reproducible
  generic preparation script, layered PSD, alpha proofs, and calibrated
  placement at `(330,570)`, size `136x35`, pending final owner review.
- Define perceptual fidelity in the recomposed PSD, rather than literal
  pixel-for-pixel identity, as the anatomical asset acceptance criterion.
- Reset Scarlet avatar authoring to the approved half-body portrait and T-pose
  only, removing 815 derived or obsolete avatar-workspace files, seven rejected
  PSDs, APNG V1/V2 outputs, and all legacy avatar generators and npm commands.
- Add an engine-neutral surgical PSD contract with locked reference hashes,
  full-canvas coordinates, anatomical ownership, front-to-back production,
  back-to-front rendering, and distinct visible/hidden review gates.
- Retain the findings from the rejected Live2D and APNG experiments in project
  documentation without keeping their artwork active or reusable.

### Static Product UI Approval Prototype (SCA-48)

#### Added

- Add the renderer-independent semantic avatar intent contract and resolver;
  keep the layered visual authoring workspace reference-only until individual
  anatomical surfaces pass review.
- Add the isolated Android-oriented Scarlet splash as the default
  `/prototype` surface, leaving the prior Product UI available through
  `?surface=product` and adding no backend or later onboarding flow.
- Add the first transparent Scarlet character concept: an adult anime woman
  with makeup, pearl/graphite styling, and Timber hair, eye, and clothing
  accents, integrated through a reusable semantic avatar component.
- Add portrait and landscape splash screenshots verified in a production
  browser.
- Add an isolated `/prototype` route with schema-realistic V2 sessions,
  memories, and durable event fixtures; it performs no backend calls and does
  not change the existing cockpit or mobile consumer.
- Add one clickable mobile-first Product UI for chat, episodic continuity,
  semantic memory, operating state, settings, and an integrated developer
  lens.
- Add deterministic ready, empty, loading, streaming, reconnecting, and error
  preview states plus versioned desktop/mobile approval screenshots.
- Replace the rejected generic visual pass with the Scarlet Signal identity:
  fuchsia/scarlet/light-blue functional color roles, an application-wide
  continuity line, open editorial responses, numbered session traces, compact
  memory hooks, and a high-contrast evidence lens.
- Add self-hosted Manrope and Space Grotesk variable typography and expanded
  screenshot coverage for every principal Product UI surface.

#### Changed

- Replace the image-to-3D and prepared-APNG construction paths with an
  engine-neutral layered raster PSD process after both approaches produced
  unacceptable identity or motion defects.
- Move the frontend build pipeline to Tailwind CSS 4 through the official Vite
  plugin while preserving the existing client build.
- Build the prototype initially on the V1.52 development branch and refresh it
  onto V1.54.0 without assigning a Product UI release version before owner
  approval; V1.50.1 remains the deployed, release-accepted Core.

#### Verification

- The avatar reset verifies the two canonical `941x1672` references by hash and
  dimensions, parses the new PSD contract, and passes the frontend build.
- The splash passes production-browser inspection at `390x844`, `360x640`,
  and `844x390` with loaded imagery, no viewport overflow, and no console
  errors or warnings.
- TypeScript/Vite production build passes on Tailwind V4 and `npm audit`
  reports zero vulnerabilities.
- Real-browser inspection at 1440x1000 and 390x844 covers chat, sessions,
  memory, developer lens, state switching, reconnect, responsive navigation,
  accessibility visibility, and page overflow with no console warnings or
  errors.
- The redesigned pass additionally covers status, settings, mobile developer
  evidence, mobile document-width equality, and the rejected-to-current visual
  boundary without changing fixtures or backend behavior.
- Owner approval remains required before SCA-48 can close or any real-data
  integration begins.

### V1.54.0 - Agentic Module SDK And Conformance Kit

#### Added

- Add the standalone `scarlet-agentic-module-sdk` 1.0.0 package with the exact
  manifest and Core Port models used by the host.
- Add module-side JSONL runtime helpers, deterministic scaffold generation,
  localized manifest validation, versioned schema export, and a live
  lifecycle/port/error conformance runner.
- Add focused tests proving that an unmodified generated fixture passes the
  standalone kit and the real Core host, plus the canonical SDK guide and
  ADR-0112.

#### Changed

- Advance backend and frontend development versions to V1.54.0 while keeping
  V1.50.1 as the deployed, release-accepted Core baseline.
- Make the public SDK package the canonical contract source and retain
  `app.agentic_modules.contracts` as a compatibility re-export.
- Extend Ruff, mypy, and coverage gates to include SDK source rather than
  allowing public package code to sit outside measured quality boundaries.

#### Verification

- Focused Agentic Module contract/host/SDK tests pass 33/33.
- The complete backend and SDK pass 304 tests at 82.46% combined coverage;
  Ruff and mypy over 42 typed files pass.
- A separately built SDK wheel installs outside the repository, generates a
  module, and completes manifest, lifecycle, health, every declared port,
  structured-error, and stop checks without patching the scaffold.
- The frontend production build and 73-file documentation integrity gate pass;
  isolated OpenAPI inspection remains unchanged at 30 operations.

### V1.53.0 - Agentic Module Host

#### Added

- Add deterministic discovery for operator-approved module roots with strict
  manifest validation and SHA-256 policy pinning.
- Add bounded persistent `stdio-json-v1` subprocess transport, opt-in Module
  Host lifecycle, typed port routing/composition, runtime dependency
  quarantine, and in-memory/repository telemetry receipts.
- Add a real subprocess conformance fixture covering all V1 ports plus timeout,
  crash, malformed output, disable, trust, ordering, and trace behavior.
- Add the canonical Module Host contract and ADR-0111.

#### Changed

- Advance backend and frontend development versions to V1.53.0 while keeping
  V1.50.1 as the deployed, release-accepted Core baseline.
- Promote SCA-54 host mechanics from planned to implemented without installing
  product modules or changing the native chat path.

#### Verification

- Focused Agentic Module contract/host tests pass 26/26 with real subprocesses.
- Ruff and the expanded 34-module mypy gate pass.
- The complete backend passes 297 tests at 82.40% coverage; frontend build,
  72-file documentation integrity, 34-module mypy, Ruff, and direct host smoke
  pass. OpenAPI remains at 30 operations; remote quality is checked after push.

### V1.52.0 - Agentic Module Contract Baseline

#### Added

- Add strict `agentic-module-manifest-v1` models for identity, compatibility,
  mode tags, capabilities, permissions, dependencies, resources, timeouts,
  health, lifecycle, and declarative process transport.
- Add typed V1 Core Port envelopes for context, prompt, command, event, health,
  lifecycle, errors, budgets, and contributions.
- Add a deterministic activation planner with dependency ordering, optional
  dependency warnings, fail-closed compatibility checks, and per-module
  blocked/inactive/active state.
- Add tested valid and invalid manifest fixtures plus the canonical Agentic
  Module contract and ADR-0110.

#### Changed

- Advance backend and frontend development versions to V1.52.0 while keeping
  V1.50.1 as the deployed, release-accepted Core baseline.
- Promote Agentic Module names, manifests, permissions, modes/tags, and Core
  Ports from planning vocabulary to an accepted public contract. Discovery,
  host execution, enforcement, and sandboxing remain unimplemented.

#### Verification

- Focused Agentic Module, mode, and organ contracts pass 31/31; the complete
  backend passes 286 tests at 82.47% coverage.
- Ruff and the expanded 28-module mypy gate pass; the frontend production
  build and 71-file documentation integrity gate pass.
- JSON Schema generation, direct-database permission rejection, Core/port
  compatibility, mode selection, missing required/optional dependencies,
  dependency ordering, and cycle rejection are covered deterministically.
- Isolated OpenAPI inspection reports V1.52.0 with the unchanged 30 HTTP
  operations, confirming that SCA-53 adds contracts rather than a hidden host.

### V1.51.0 - Provider-Independent Stream And Recovery Contract

#### Added

- Add `scarlet-stream-v2` as a durable Product UI event envelope projected
  from persisted runtime events rather than provider-native deltas.
- Add a session-global replay endpoint with exclusive cursor, pagination, and
  exact message/terminal enrichment for reconnect recovery.
- Add an executable reference reducer for ordering, idempotent duplicate
  handling, gap detection, and reconstruction of notes, tools, answers,
  messages, errors, and terminal state.

#### Changed

- Keep the V1 NDJSON stream intact for compatibility while defining V2 as the
  preferred port for new web and Android clients.
- Advance backend and frontend development versions to V1.51.0 while keeping
  V1.50.1 as the deployed, release-accepted Core baseline.

#### Verification

- Focused stream/replay/reducer tests cover normal tool-bearing turns,
  terminal errors, pagination, reconnect, out-of-order input, duplicate ids,
  and sequence gaps.
- Ruff and the 26-module incremental mypy gate pass; the complete backend
  passes 271 tests at 82.08% coverage and the frontend production build passes.
- Documentation integrity passes across 70 files and OpenAPI V1.51.0 exposes
  30 operations including the two V2 ports. A direct isolated smoke emitted 17
  canonical events, replayed the same ids, reconstructed note/tool/answer/
  terminal state, and excluded full tool/runtime-context payloads.
- Remote quality gates and deployment remain required before release
  acceptance.

### V2 Architecture Baseline - Core Closure Contract

#### Added

- Add the canonical Core Runtime contract with named Product UI, External
  Adapter, and Agentic Module boundaries, sources of truth, dependency rules,
  audiences, versions, and compatibility classes.
- Record ADR-0107 so the V1.50.1 Core closure and V2 layer taxonomy remain a
  durable decision rather than a Linear-only convention.

#### Changed

- Align the repository entry points, current-state roadmap, API contract,
  block/branch maps, quality notes, and historical monolith plan with the
  closed Core and active SCA-46 V2 sequence.
- Reclassify unresolved research, mypy expansion, GPT router cleanup, and old
  UI componentization as future annotations instead of active Core backlog.

#### Verification

- Documentation integrity passes across 69 files and 1,253 repository
  references; `git diff --check` passes and the current-state scan finds no
  stale V1 roadmap markers presented as active work.
- An in-memory application inspection confirms runtime OpenAPI remains
  V1.50.1 with 28 operations and the model-facing shell remains registry v2
  with the same eight command families. No prompt, schema, database, provider,
  or runtime code changes are included.

### V1.50.1 - Native Finality Semantic Recovery

#### Fixed

- Keep the private native final marker as the primary boundary and the single
  bounded correction as the first recovery path.
- When the corrected second draft still omits the marker, require an explicit
  hard LLM judgment that the text is a complete, standalone, conclusive answer
  rather than a progress note, promise, fragment, or dependency on rejected
  public text.
- Fail closed when that finality judge is unavailable or rejects the draft;
  no text is rewritten and empty/incomplete provider output remains rejected.

#### Verification

- Two focused production turns exposed the repeated marker omission while
  proving DB health, V2 memory delivery, shell execution, and complete provider
  drafts. The release was not accepted from HTTP status alone.
- Focused answer-control/chat tests pass 46/46; with the model-facing gate
  oracles the patch surface passes 52/52, including positive markerless
  semantic recovery, a negative second-progress-note control, and an empty-
  draft guard. The complete backend passes 266 tests at 81.89% coverage.
- PR #17 passed both remote Quality workflows and merged at `676e560`. The
  protected V1.50.1 rollout passed new-image and post-restart production
  preflights, frontend parity, a real native Zero-Luce turn, and an
  authenticated GPT bootstrap/help/finalize cycle. The annotated `v1.50.1`
  tag points to the exact deployed runtime commit.

### V1.50.0 - Stabilization Baseline And Model-Facing Memory Gate

#### Added

- Add the complementary `model-facing-memory-gate-v2` without rewriting the
  historical preliminary V1 suite. The gate proves rich retrieval, V2
  projection, exact source hooks, persisted `llm.request`, provider-observed
  input, completed turn, and assistant persistence as separate boundaries.
- Add a negative-control provider that intentionally omits the final-answer
  marker and prove the gate rejects its failed turn even when retrieval and
  model-context traces exist.
- Add focused contracts for the evaluator oracle, guarded provenance repair,
  controlled-provider polarity, report output, and success/failure paths.

#### Changed

- Consolidate the locally verified V1.44.0 through V1.49.1 candidates as the
  V1.50.0 release baseline. GPT Actions remains an experimental adapter; no
  retrieval, context-projector, prompt, shell, or production-memory policy is
  changed by this release.

#### Verification

- `model-facing-memory-gate-v2` passes 5/5 on a disposable copy of the frozen
  database; the immutable source SHA remains unchanged.
- The unchanged preliminary V1 gate passes 9/9, focused context/maintenance/
  chat tests pass 43/43, shell and organ contracts pass 53/53, and evaluator
  oracle contracts pass 6/6 at 89.74% module coverage.
- The complete backend passes 263 tests at 81.86% coverage, improving the
  V1.49.1 project baseline while keeping the 79.9% blocking floor.

### V1.49.1 - Action Retry Evidence Reconciliation

#### Fixed

- Rebuild current-turn action obligations from the authoritative tool-call
  chain so a recoverable failure can expose later same-operation attempts to
  the semantic answer validator on native sync, native stream, and GPT
  Actions.
- Keep the initial failure and every linked trace visible while letting the
  validator decide whether command, intent, and result prove a materially
  equivalent recovery; different-operation, non-recoverable, and unrelated
  retries remain hard failures.
- Replace stale persisted GPT action/capability obligations with the latest
  current-turn evidence instead of deduplicating away successful later calls.

#### Verification

- Frozen SCA-42 pre/post gates pass 9/9; focused answer-control, native chat,
  and GPT bridge contracts pass 58/58; the complete backend passes 257 tests
  at 81.71% coverage.
- A directly inspected MiniMax M3 turn encountered an injected real shell
  validation failure, corrected the same memory-write intent, persisted a
  faithful source-linked preference, and answered naturally. The action
  sequence, validator findings, memory, provenance, and final text were judged
  directly rather than inferred from aggregate status or scores.

### V1.49.0 - Maintenance Runtime Domains

#### Changed

- Split maintenance scheduling/dispatch, summary-history work, and memory
  review/proposal resolution into dedicated typed owners behind the unchanged
  `app.runtime.maintenance` facade.
- Preserved job kinds, scheduling, retry and idempotency behavior, idle checks,
  prompts, auto-apply thresholds, worker lifecycle, API imports, and persisted
  job/event contracts.
- Extended the blocking mypy surface from 21 to 25 modules.

#### Verification

- Frozen SCA-37 pre/post gates pass 9/9 with identical stable evidence;
  focused maintenance/history contracts pass 32/32 and the complete backend
  passes 247 tests at 81.63% coverage.
- Normalized pre/post OpenAPI is exactly equal at 39,251 bytes.
- Direct history-compaction use preserved idempotency, canonical history, exact
  source anchoring, and expected events on a disposable database.
- A natural MiniMax M3 idle-maintenance probe produced a faithful session
  summary and correctly declined to remember a transient pause. Actions,
  persisted records, and answer quality were inspected directly rather than
  accepted from status counters alone.

### V1.48.0 - Memory Mutation And Evidence Boundaries

#### Changed

- Split memory write/fact materialization, lifecycle, maintenance proposals,
  and relation evidence into four dedicated owners behind `app.mind.memory`.
- Reduced `app.mind.memory` from 1,938 lines to a 38-line compatibility facade
  while preserving dispatcher, shell, API, maintenance, and evaluator imports.
- Extended the blocking mypy surface from 17 to 21 modules and fixed two
  proposal-flow type narrowings without changing their runtime decisions.

#### Verification

- Frozen SCA-38 pre/post gates pass 9/9 with identical source inventory,
  retrieval ids, facts, search results, and lifecycle targets.
- Focused mutation/maintenance contracts pass 70/70; the complete backend
  passes 246 tests at 81.59% coverage; Ruff and mypy pass.
- Direct shell use verified write, exact deduplication, atomic conflict
  evidence, supersession, fact lifecycle, activities, and traces on an
  isolated database.
- A natural MiniMax M3 turn autonomously wrote one sourceable user preference
  and answered consistently with the successful persistence result.

### V1.47.0 - Memory Read Surface Boundary

#### Changed

- Moved manual memory search, read, facts, graph, request contracts, ranking,
  temporal filtering, and graph presentation into `app.mind.memory_read`.
- Added `app.mind.memory_shared` for the minimal payload, field, error, and
  activity contracts shared by read and mutation handlers.
- Kept `app.mind.memory` as a compatibility facade for dispatcher, shell,
  maintenance, API, evaluator, and test imports.
- Added both new owners to the blocking mypy surface.

#### Verification

- Frozen SCA-36 pre/post gates pass 9/9 with identical stable manual-shell and
  automatic-retrieval evidence.
- Focused memory/shell/V2 contracts pass 63/63; direct shell search/open/facts/
  graph returned the expected real memory, fact, graph, provenance, and traces.
- The complete backend passes 245 tests at 81.54% coverage; Ruff and mypy pass.

### V1.46.0 - Automatic Context Retrieval Boundary

#### Changed

- Moved automatic memory candidate pooling, ranking, classification, final
  rerank projection, and negative evidence into the typed
  `app.mind.context_retrieval` owner.
- Kept `app.mind.context` as the stable runtime-packet facade and preserved the
  existing selected/near-miss/excluded payload, trace, and activity contracts.
- Added the retrieval owner to the blocking mypy surface.

#### Verification

- Frozen SCA-35 pre/post gates pass 9/9 with the same active Zero-Luce memory,
  33 candidates, and model-context block types.
- Focused context/retrieval tests pass 101/101; the complete backend passes
  244 tests at 81.50% coverage; Ruff and mypy pass.
- A directly inspected MiniMax probe proved that the selected memory reaches
  the model and produces the expected four-block answer after exact source
  provenance is repaired on a disposable database.

#### Known Issues

- The frozen V1 gate checks rich automatic selection but not V2 model-facing
  delivery. Its Zero-Luce fixture lacks `source_message_id`, so the projector
  correctly excludes it. BUG-0093/Linear SCA-43 tracks a new complementary
  gate without rewriting the historical baseline.

### V1.45.0 - Native Turn Orchestration Boundary

#### Changed

- Moved native sync/stream preparation, provider execution, answer control,
  failure recording, completion, and maintenance scheduling behind the typed
  `app.api.chat_native_turn` service boundary.
- Reduced `app.api.chat` to HTTP route registration, request validation,
  response mapping, and debug-route ownership while preserving its public
  facade and every existing endpoint schema.
- Added `chat_native_turn.py` to the blocking mypy surface.

#### Fixed

- Stream turns now expose the generated `model.context` trace through both
  `llm.request.model_context_trace_id` and final `trace_ids`, matching sync
  observability (BUG-0092).

#### Verification

- Frozen SCA-33 pre/post gates pass 9/9; normalized OpenAPI remains identical
  at 26 paths.
- Focused native/GPT tests pass 57/57; the complete backend passes 244 tests at
  81.44% coverage; Ruff and mypy pass.
- A directly inspected two-turn MiniMax probe preserved exact same-session
  continuity across sync then stream and proved the repaired model-context
  trace linkage.

### V1.44.0 - Native Chat Support Extraction

#### Changed

- Extracted provider-history transformations, response/event serialization,
  and context-accounting helpers from the native chat router into three
  cohesive typed modules behind the unchanged `app.api.chat` facade.
- Updated the GPT Actions router to consume the owning support modules instead
  of private chat-router helpers, without changing its OpenAPI contract.
- Classified the native project-selected provider runtime as authoritative and
  the Custom GPT bridge as an experimental external adapter.
- Made direct qualitative inspection mandatory for behavioral probes; numeric
  scores and deterministic flags remain supporting evidence rather than the
  behavioral verdict.

#### Verification

- Frozen SCA-34 pre/post gates pass 9/9; normalized OpenAPI JSON is exactly
  unchanged at 26 paths and 29 schemas.
- Focused support/chat/bridge tests pass 57/57; the complete backend passes
  244 tests at 81.41% coverage; Ruff, mypy, documentation integrity, database
  boundary, and frontend production build pass.
- A two-turn isolated MiniMax probe preserved canonical provider history and
  produced a semantically correct same-session recall answer under direct
  qualitative review.

#### Known Issues

- A separate isolated probe confirmed that answer obligations can retain a
  failed action while ignoring its successful corrected retry (BUG-0091,
  Linear SCA-42). The pre-existing defect is not changed by SCA-34.

### V1.43.0 - Actions-Only GPT Bridge

#### Changed

- Removed the deprecated `/mcp` JSON-RPC transport, MCP tool descriptors,
  connector prompt, and private-preview query-string authentication.
- Kept the GPT bridge on the mandatory bootstrap/action/finalize Actions
  lifecycle and the shared `mind_shell(command, intent)` dispatcher.
- Preserved every historical `mcp_bridge` session, message, turn, tool call,
  trace, and cognitive record as canonical evidence.

#### Security

- Bridge authentication now accepts configured secrets only through
  `Authorization: Bearer` or `X-GPT-Bridge-Key`; URLs no longer carry bridge
  credentials into access logs.

#### Verification

- Focused GPT bridge and shell tests pass 27/27 after removal. Frozen pre/post,
  complete quality, and protected production rollout evidence are recorded in
  `docs/evaluations/v1.43-mcp-retirement.md`.

### Atomic Monolith Rework Planning

#### Added

- Added the current module-responsibility inventory, stable-facade rules,
  dependency order, nine atomic Linear implementation slices, and mandatory
  frozen pre/post gate for future organization work.

#### Evaluation

- Revalidated the unchanged V1.42 assembled baseline at 9/9 before publishing
  the plan. SCA-10 contains no runtime or database change.

### Memory Reranker Revalidation

#### Added

- Added five realistic unsupported-personal-memory controls to the immutable
  final-reranker calibration suite and updated its controlled provider for the
  shared answer-obligation contract.

#### Evaluation

- Repeated real-provider comparison passed 30/32 probes. One personal negative
  remained above the current floor, but the negative ceiling was too close to
  the positive floor for a robust threshold-only change. Runtime correction is
  deferred; no production rerank policy or setting changed.

### V1.42.0 - Traceable Agent Mode Routing

#### Added

- Added ordered per-block mode-routing receipts with block identity,
  capability, required tags, eligibility, actual delivery, and reason.
- Added deterministic routing matrices for every registered mode, routing
  policy, duplicate block, unregistered block, and V2 projection boundary.

#### Changed

- `included` and `excluded` aggregates now describe actual delivery, while
  shadow-only exclusions use a separate `would_exclude` surface.
- Unregistered automatic block types remain fail-open but are explicitly
  reported for registry review.
- The mode persistence primitive now independently rejects system-owned
  `interactive`, preserving the shell ownership rule for internal callers.
- Native and GPT policy now distinguish `idle` as no resumable direction from
  `scouting` as a valid exploratory orientation that still starts no sensor or
  autonomous runtime.

#### Fixed

- Fixed `off` and `shadow` receipts that previously described policy
  eligibility as if it were actual model delivery (BUG-0088).
- Fixed the preliminary gate's controlled provider so metacognition and answer-
  validation calls use their correct deterministic output contracts.

### V1.41.0 - Shared Answer Obligations

#### Added

- Added shared native/GPT final-answer manifests with hard, warning, and
  advisory severity, structural/semantic validation, and dedicated traces.
- Added evidence-scoped semantic judgment for active memory conflicts,
  source-sensitive claims, capability inspection, and failed cognitive actions.
- Added GPT Action policy updates plus recoverable first rejection, explicit
  second-rejection failure, and validator-unavailable handling.

#### Changed

- Native final answers now use a private structural boundary that is stripped
  before persistence and public delivery.
- Native sync/stream paths permit one bounded correction; streaming withholds
  draft conclusion text until the accepted answer is available.
- Prompts, Action schema, accounting, API contract, branch state, experiments,
  decisions, and bug records now describe the same answer-control boundary.

#### Fixed

- Fixed completed turns containing only public work notes (BUG-0085).
- Fixed the lack of enforcement when current conflict, capability, source, or
  failed-action evidence materially constrains the final answer (BUG-0011).

V1.40.0 longitudinally validates focus, volition, computational affect, and
metacognition while retaining conservative independent defaults. V1.39.0 activates recursive source-labelled native history compaction without
mutating canonical chronology. V1.38.0 separates historical provenance audit from guarded maintenance and
classifies explicit Codex fixtures without semantic inference. V1.37.0
calibrates final memory relevance on frozen and live evidence. V1.36.1
prevents thinking-only provider messages from becoming successful empty Scarlet
turns. V1.36.0 remains the chronology-accounting baseline. V1.43.0 is the
currently deployed HoneyLabs production runtime after passing remote quality,
protected database deployment, MCP retirement, and authenticated GPT Actions
bootstrap/action/finalize gates.

### Added

- Added a 13-scenario longitudinal cognitive-organ catalog with correlated
  focus, volition, and affect chains; metacognition positives; independent
  negative controls; frozen DB guards; and requested/effective runtime
  configuration receipts.
- Added structured shell-call and organ-trace evidence for project-informed
  review of technical state, cognitive choice, answer outcome, and
  longitudinal effect as separate dimensions.

- Added append-only recursive chronology artifacts, immediate maintenance jobs,
  active sync/stream routing, deterministic source manifests, and explicit
  canonical fallback under SCA-32.
- Added `history.routing` evidence plus canonical and model-facing request
  snapshots for active native turns.

- Added the read-only `memory-provenance-audit-v2` contract with orthogonal
  provenance, record-disposition, exact-duplicate-review, criteria, and
  candidate-digest evidence.
- Added dedicated dry-run-first maintenance routes for exact source-message
  repair and explicit Codex fixture deprecation. Apply requires an approved
  operation token, the reviewed candidate digest, and a verified backup
  reference.
- Added a V1.38 production-data assessment and disposable-copy procedure that
  distinguishes 241 active structured test fixtures, one already inactive
  fixture, and seven unresolved inconsistent/non-user source links.

- Added a ten-case immutable full-DB final-rerank calibration runner plus an
  inherited wrong-entity regression covering
  positives, negatives, paraphrases, entity overlap, two-fact recall, KG route
  participation, trace ids, sourceable V2 delivery, latency, and direct Scarlet
  semantic review.
- Added final-reranker latency and effective acceptance-floor evidence.

- Added exact canonical chronology maps linking complete provider slices to
  turn, message, tool-call, request-trace, and response-trace ids.
- Added the shadow-only `O + C + H + A + M <= 500k` planner with 100k summary
  and verbatim maxima, 25k safety, dynamic active growth, whole-turn 1M
  exception, and fail-closed physical-window handling.
- Added a repeatable bounded MiniMax calibration runner and V1.36 evaluation
  report over three read-only real sessions and two full/derived comparisons.

- Added an explicit field-level projector for conditional focus, affect, and
  metacognitive blocks, with user-local focus timestamps and compact source
  navigation.
- Added `model.context.projection_audit`, which records source presence,
  dispositions, exact included/excluded field paths, cognitive purpose,
  rationale, and on-demand commands without entering model input.
- Added focused native/GPT parity and projection-contract coverage.
- Expanded the blocking mypy slice to the preserved-context projector and
  canonical V2 compiler.

- Added `scarlet-natural-core-v1`: 8 groups and 12 natural scenarios with
  frozen DB references, three independent repetitions, real MiniMax M3 turns,
  raw trace/state evidence, and four separate evaluation layers.
- Added a project-informed LLM-as-human judgment contract and objective-only
  pre/post comparator; semantic answer differences always require a written
  rationale rather than string or aggregate numeric scoring.
- Added shared frozen-baseline guards and source references for both the
  deterministic 9-case suite and the natural behavioral runner.
- Added direct evaluator-support coverage for event/trace extraction,
  cognitive-state snapshots, rule operators, frozen DB inventory/copy guards,
  chained-session handling, response fallback, and CLI validation.
- Added V1.34 evaluation evidence covering memory controls, episodic source
  navigation, focus, volition, affect, metacognition, and mode continuity.

- Added V1.33.0 blocking Ruff checks for objective Python defects, incremental
  mypy coverage over six high-value modules, a measured 79.9% backend
  statement-coverage floor, and deterministic documentation link/reference/
  identifier validation.
- Added a GitHub Actions quality workflow that runs backend lint, typing,
  documentation, full tests with coverage, and the frontend production build
  without loading production secrets or runtime databases.
- Made documentation validation independent of locally generated `.venv`,
  `node_modules`, `dist`, and build directories so clean CI and developer
  worktrees apply the same repository-reference contract.
- Added V1.32.0 executable shell-conformance coverage across all 23 registered
  family/namespace aliases, every help-published command, lifecycle paths,
  pagination, targeted not-found errors, and retrospective metacognition
  controls.
- Added direct disposable MiniMax M3 evaluation across episodic recall,
  affect, focus, volition, and metacognition, with exact tool evidence and no
  production database mutation.

- Added V1.31.0 memory-level final rerank arbitration. Sparse FTS, dense
  surfaces, NetworkX graph expansion, and lexical/entity matching now build a
  deduplicated round-robin candidate pool; only the reranker can accept and
  order active automatic or manual retrieval results.
- Added explicit rerank trace entries with recall routes/ranks, evaluation and
  acceptance state, query-time score, and fail-closed diagnostics.

- Added V1.30.0 context accounting and non-destructive compaction planning:
  exact local character/byte channels, provider first-step observations,
  separate tool-loop totals, calibrated token estimates, and a shadow-only
  `100k summary + desired eight-turn tail` plan under the 1M/500k/400k policy.
  Canonical messages, traces, transcripts, and provider history remain
  unchanged and navigable.
- Added V1.30.0 agent modes with one active tag and multi-tag capability
  eligibility. Human turns enforce `interactive`; Scarlet can persist
  `idle`/`scouting` as a resumable posture through `mode` shell commands.
  Mode changes are traced and explicitly do not start autonomous cycles.
- Added `behavioral-scenario-v1`, a four-layer behavioral validation contract
  covering technical execution, cognitive choice, answer outcome, and
  longitudinal effect against declared real starting evidence.

### Changed

- Deployed V1.40.0 from merge `db31398` after online SQLite backup, new-image
  read-only production preflight, restart, version/integrity/log checks,
  frontend hash parity, and a natural native MiniMax smoke.
- Advanced backend, frontend, GPT Action schema, prompts, and canonical project
  metadata to V1.40.0.
- Kept focus bounded, volition on-demand and outside automatic chat injection,
  affect shadow by default, metacognitive lessons shadow by default, and
  cross-organ coupling disabled after the SCA-4 evidence review.
- Required a verified volition write before durable self-direction claims and
  a real metacognitive step before broad all-organ or default-readiness claims.

- Deployed V1.39.0 from merge `cb400d2` with release tag `v1.39.0` after an
  online SQLite backup, read-only production preflight, active-compaction
  configuration check, restart, schema/integrity verification, frontend hash
  comparison, and a natural native Scarlet smoke.
- Changed the compaction trigger to the configured total model-input threshold
  and, after activation, to the estimated derived next-turn view rather than
  immutable canonical-history size.
- Changed the active native request to `compacted chronology + exact token tail
  + current user` while keeping provider-history persistence canonical.

- Deployed V1.38.0 after a verified online backup and production-role
  preflight. The guarded apply deprecated all 242 explicit Codex fixtures,
  retained seven uncertain real source links for review, preserved source
  session recency, and passed direct native/GPT isolation controls.
- Aligned effective VPS retrieval configuration with the V1.37 adaptive floor
  and explicit Nvidia OpenRouter embedding/rerank models; post-restart traces
  completed both stages.

- Historical lifecycle maintenance no longer makes old source sessions or
  memories cognitively recent. Explicit fixture records are deprecated with
  append-only, non-recent activity and synchronized fact/retrieval status;
  they are never hard-deleted.
- `GET /api/maintenance/memory/provenance` is now strictly read-only. Mutation
  moved out of the query string and into purpose-specific guarded POST routes.

- Advanced backend, frontend, GPT Action schema, and canonical project metadata
  to V1.37.0.
- Replaced the provisional fixed `0.01` final-rerank threshold with a calibrated
  `max(0.004, best query score * 0.01)` policy. The reranker remains the sole
  semantic arbiter; recall routes remain non-authoritative and active failure
  remains fail-closed.

- Advanced backend, frontend, GPT Action schema, and canonical project metadata
  to V1.36.1.
- Added one configurable, bounded continuation for a MiniMax/Qwen tool-chat
  response that ends with private thinking but no public text or tool call.
  The incomplete attempt remains trace evidence and is excluded from canonical
  provider history.

- Upgraded model-input accounting to v2: policy, model-context packet,
  provider history, current message, Mind shell schema, bridge boundary, and
  request structure are explicit surfaces. Provider observations now include
  uncached, cache-read, and cache-created input for every tool-loop step.
- Replaced the compatibility eight-turn compaction assumption with dynamic
  newest-complete-turn selection by incremental estimated token cost.
- Advanced backend, frontend, GPT Action schema, and canonical project
  metadata to V1.36.0. Active compaction remains disabled.

- Removed `scarlet_state`, duplicated recent dialogue, generic runtime-event
  summaries, and API Mind capability catalogs from automatic V2 model context.
  Rich runtime data remains intact for trace/UI/system use; capability detail
  remains available through `help`.
- Advanced backend, frontend, GPT Action schema, prompts, and canonical
  documentation metadata to V1.35.0.

- Made focused deterministic checks and direct Codex tool use the default task
  verification. Complete repeated or cross-branch live Scarlet evaluations now
  require an explicit owner instruction for the current task; deterministic CI
  remains automatic.
- Advanced backend, frontend, GPT Action schema, and canonical documentation
  metadata to V1.34.0.
- Formalized the one-Linear-issue-at-a-time workflow: assess, present scope,
  receive owner approval, implement, verify, record evidence, then close.
- Corrected two over-prescriptive behavioral oracles: runtime mode context can
  replace redundant `mode read`, and policy-valid metacognitive memory
  consolidation is not an automatic regression.
- Removed evaluator scenario IDs and repetition metadata from model-facing
  session identity, then established the authoritative 36-turn run with
  neutral titles. Earlier 45 turns remain evaluator shakedown evidence only.
- Recorded clean cross-branch findings: focus resolution 0/3, autonomous
  volition persistence 1/3, affect activation 0/3, explicit metacognitive
  review 1/3, and clean scouting continuity 1/3.

- Restored authenticated GitHub publication, published the catch-up feature
  branch and PR #1, and tagged the exact deployed V1.32.0 runtime commit.
  V1.33.0 remains untagged until its protected VPS rollout.
- Updated the official checkout, Python, and Node setup Actions to their
  Node 24 runtimes after the first merged workflow exposed Node 20 deprecation.
- Advanced backend, frontend, GPT Action schema, and canonical project
  metadata to V1.33.0. The broader mypy baseline remains explicitly measured
  at 216 errors across 23 files rather than hidden behind global exclusions.
- Advanced session list/search beyond the old hidden 500-row boundary and made
  fallback summaries use the complete transcript even when the returned
  message window is limited.
- Made volition review scheduling shell-accessible, converted promoted focus
  candidates into executable shell commands with source linkage, and limited
  manually resumable agent modes to `idle` and `scouting`.

- Removed the obsolete hand-weighted hybrid ranker. The historical
  `retrieval_hybrid` trace key remains temporarily compatible but reports the
  final rerank policy with `legacy_weighted_fusion=false`.
- Stopped duplicating the current user message in automatic retrieval queries.
  Active rerank failure now returns no relevant memory instead of silently
  falling back to deterministic relevance.
- Calibrated the first active rerank threshold from `0.55` to provisional
  `0.01` after two real Italian positive controls and a negative control, and added a provider-
  delivery assertion so rich selection alone cannot be mistaken for model
  evidence.

- Removed the redundant structured `context.model_context` copy from GPT
  bootstrap while retaining the single canonical serialized runtime document
  and full diagnostics in traces.
- Advanced backend, frontend, OpenAPI runtime, prompt, and project metadata to
  V1.30.0 and documented agent modes as main-agent posture only; maintenance,
  summarization, and Dream remain background processes.

### Fixed

- Fixed explicit obstruction-resolution messages re-triggering frustration
  through the substring `blocc` and full prior-state carry. Resolution now
  produces traceable relief while neutral controls remain unaffected.

- Fixed `context.accounting.observed` reporting every compaction plan as
  shadow-only even when the request used active derived history.
- Fixed generated chronology summaries carrying altered/shortened opaque source
  IDs by removing unverified IDs and supplying backend-owned exact manifests.
- Fixed active compaction jobs being eligible after every later turn solely
  because canonical history remains above the trigger.

- Rejected semantically empty terminal chat results in both synchronous and
  streaming routes. Repeated or non-recoverable empty results now fail the
  turn explicitly as `llm.incomplete_response`, without persisting an empty
  assistant message or deriving cognitive state from private thinking.
- Added recovery metadata and `llm.completion.recovery.started` observability,
  plus provider and API regression coverage for recovery, exhaustion, and
  history isolation.

- Prevented accounting v2 calibration from learning ratios produced by the
  incompatible cache-under-counting v1 observation contract.

- Made behavioral evaluator support tests independent of the ignored frozen
  baseline database. CI now builds a canonical temporary SQLite fixture while
  production-like runner validation still requires the real baseline hash.
- Fixed the GPT bridge prompt so external Scarlet emits concise
  progress notes during long Action sequences while reserving mandatory
  finalize for the concluding answer. The Builder schema uses the same
  distinction, all operation descriptions stay below 300 characters, and the
  owner confirmed the behavior in a real multi-action GPT turn.
- Prohibited GPT final drafts from using `:::writing` or other private ChatGPT
  UI directives that cannot be treated as portable finalized Markdown.
- Fixed `focus hold` persisting an active status, affect read ignoring filters,
  targeted focus/affect misses returning successful empty payloads,
  metacognition dropping retrospective flags, help alias drift, and advertised
  memory aliases not executing.
- Fixed Mind API tests inheriting production retrieval mode from the local
  `.env`; the test client now declares `off` unless a scenario explicitly
  exercises active retrieval.

- Fixed the initial final-rerank thresholds rejecting positive controls at
  rank 1/`0.465327` and rank 1/`0.089455`; sourceable full-DB turns delivered
  the expected memories while an unrelated control remained below `0.0004`.

- Fixed GPT bootstrap accounting so assigned trace IDs are explicitly excluded
  from the otherwise exact measured boundary and the returned diagnostics list
  contains both accounting and request traces.
- Fixed bare `volition list` so the advertised command resolves to
  `volition.list_active` instead of reaching the handler with an invalid body.
- Tightened mode guidance after live MiniMax evaluation so an explicit
  post-conversation posture request triggers `mode set` without being replaced
  by a volition or memory write, while avoiding claims of autonomous scouting.

### Changed

- Completed the V1.29.1 integrated code and documentation audit:
  - reconciled the canonical project state, all 14 cognitive branch records,
    context-packet registries, API/DB contracts, roadmaps, and GPT knowledge
    with the deployed V1.29 architecture;
  - separated implemented capability, deterministic evidence, direct Scarlet
    evidence, and normal runtime activation in branch status reporting;
  - normalized duplicate ADR, experiment, and bug identifiers without
    rewriting historical evidence;
  - recorded provider-native history growth as a distinct open architectural
    risk rather than attributing it to the compact V2 packet.
- Advanced project/package documentation metadata to V1.29.1. This audit does
  not change cognitive runtime behavior, production configuration, or data.

### Added

- Added V1.29.0 canonical dynamic context V2:
  - introduced the shared `scarlet-model-context-v2` compiler for native
    MiniMax and the GPT Actions bridge, with compact session/user/world hints,
    two previous-session summaries, and deduplicated `relevant`,
    `recent_user`, and `recent_general` memory hooks;
  - added one user-time rendering boundary and excluded unresolved provenance
    from automatic memory delivery;
  - preserved rich retrieval/runtime evidence in traces while adding the exact
    delivered document as a separate `model.context` trace and UI readout;
  - added configurable `legacy`, `v2_shadow`, and `v2` rollout profiles.
- Added V1.29.0 append-only `memory_activities` and cognitive-recency queries.
  Manual search/open/facts/graph, writes, replacements, maintenance-created
  memories, and confirmed reranked selections are explicit events; packet
  delivery and systemic reads do not refresh recency.
- Added V1.29.0 source navigation through `session message msg_...` and
  `session turn turn_...`, returning persisted public dialogue, tool evidence,
  public events, and trace references without hidden provider reasoning.
- Added V1.29.0 summary/provenance maintenance surfaces:
  read-only audits, bounded summary reconciliation with retry/backoff, and a
  dry-run-first deterministic source-message repair operation.

- Added V1.28.0 domain-separated storage repositories while retaining the
  `storage.repositories` compatibility facade used by existing chat, memory,
  shell, maintenance, and bridge callers.

- Added V1.27.0 database ownership boundaries:
  - introduced explicit `production`, `laboratory`, `test`, and `preliminary`
    roles, a read-only database preflight, and startup validation for ambiguous
    environments and production/test mixtures;
  - moved the eager ASGI application to `app.asgi:app`, leaving the reusable
    factory free of database-opening import side effects;
  - documented the local/VPS inventory and deployment procedure, including
    mandatory remote backup and exclusions for runtime `data/` and `.env`;
  - changed the dirty-memory evaluator to use a marked disposable copy of the
    frozen baseline rather than resetting the historical `codex_test.db`;
  - added a staged-change guard for the mutable LFS laboratory snapshot.

- Added V1.26.0 Mind shell organization layers:
  - moved shared cognitive runtime contracts into `mind/contracts.py`;
  - moved side-effect-free command parsing and flag/time grammar into
    `mind/shell_parsing.py`;
  - moved shell help, errors, sanitization, and compact model-result profiles
    into `mind/shell_presentation.py`;
  - added focused parser regression tests while preserving the public shell
    tool contract.

- Added V1.26.0 preliminary whole-system regression gate:
  - introduced `preliminary-regression-v1`, an executable pre/post-rework
    integration suite against a frozen real laboratory DB baseline;
  - pinned the baseline to its published Git LFS SHA-256 and documented real
    memory, fact, and source-session references rather than synthetic-only
    fixtures;
  - verified automatic retrieval, manual shell navigation, semantic lifecycle,
    focus, volition, affect, metacognition, internal maintenance boundary, and
    GPT bridge lifecycle in one disposable test DB run;
  - recorded the first valid result as `9/9` and made equal-or-better reruns a
    required acceptance gate for future major procedures.

- Added V1.26.0 runtime context-pack planning:
  - introduced `docs/runtime-context-packs.md` as the baseline for an always-on
    context spine, mode-specific packs, organ/source/capability
    classification, coupling, freshness, authority, cost, safety, and
    degradation rules;
  - recorded ADR-0067 for context packs before future embodied context
    expansion;
  - recorded EXP-0049 for the corrected default-token live Scarlet probe;
  - parked the resulting known issues as BUG-0057 through BUG-0061 without
    fixing them in this documentation-only slice;
  - updated project-state, blueprint, branch docs, and organ notes so future
    organs must declare their context classification before broad model-facing
    injection.

### Fixed

- Fixed V1.29.0 missing live memory provenance across native chat, GPT bridge,
  and maintenance proposal application.
- Fixed V1.29.0 memory reads overwriting semantic `updated_at`; compatibility
  usage fields remain stored but no longer drive cognitive recency.
- Fixed V1.29.0 missing/stale session summaries being permanently skipped
  after absent or failed idle jobs. A disposable laboratory run generated all
  34 eligible summaries through the normal provider summarizer (`34/34`).
- Fixed V1.29.0 detached summary-repair job objects after batched scheduling by
  refreshing returned jobs before crossing the session boundary.

- Fixed V1.28.1 repository-domain file formatting so the published checkpoint
  passes whitespace validation.

- Fixed V1.25.4 Mind shell command-registry parity:
  - corrected `validate_shell_command` so flag values no longer count as
    positional arguments;
  - required the same lifecycle fields the shell handlers require, including
    memory deprecate/supersede reasons, volition create reasons, and
    focus/volition closure reasons or resolutions;
  - accepted canonical hyphenated volition aliases such as
    `volition mark-impossible` when suggested by the registry;
  - changed model-facing runtime capabilities to derive from the
    `mind_shell` registry rather than legacy `/mind/*` endpoint routes;
  - marked `memory.facts.backfill` as `internal_maintenance_only` so Scarlet
    does not treat deterministic fact backfill as a normal cognitive command.

### Changed

- Changed V1.25.3 GPT Actions schema alignment:
  - added top-level `session_id` to `/gpt/bootstrap` responses so the GPT can
    reuse it without reading nested `session.id`;
  - made `/gpt/action` `intent` required in the backend and local Actions
    schema, matching the active GPT Builder schema;
  - added optional bootstrap response fields for `action_policy`,
    `required_actions`, and `recommended_actions` so future cognitive action
    policies have an explicit schema surface.

- Changed V1.25.2 GPT Actions bridge packaging:
  - aligned the compact GPT Builder prompt with the active platform prompt
    centered on `bootstrapScarletBeforeEveryAnswer`,
    `runScarletMindAction`, and `finalizeScarletBeforeAnswer`;
  - renamed the local OpenAPI Actions operation ids to match the GPT-facing
    operation names;
  - added `final_answer_to_show` to `/gpt/finalize` responses so the GPT can
    finalize a draft and then show the exact backend-confirmed answer
    verbatim;
  - marked the MCP/App bridge as deprecated documentation-wise while keeping
    the temporary `/mcp` endpoint available for traceability and future
    removal.

### Fixed

- Fixed V1.25.1 Scarlet MCP/App tool metadata:
  - added `outputSchema` to lifecycle and cognitive command MCP tool
    descriptors because ChatGPT Apps recommends output schemas whenever tools
    return `structuredContent`;
  - kept the schema broad enough to cover both successful tool responses and
    structured error responses.

### Added

- Added V1.25.0 experimental Scarlet MCP/App bridge:
  - exposed a Streamable HTTP JSON-RPC MCP endpoint at `POST /mcp`;
  - added MCP tools for Scarlet turn lifecycle:
    `start_scarlet_turn_required` and `finish_scarlet_turn_required`;
  - used the exact mandatory lifecycle descriptions
    `Usa sempre a inizio di ogni turno` and
    `Usa sempre prima della tua risposta finale`;
  - added cognitive command tools that delegate to `mind_shell`:
    memory, session, metacognition, focus, affect, volition, help, and generic
    shell fallback;
  - added `scarlet_mcp_system_prompt.md` for ChatGPT GPTs configured with
    Apps/Connectors instead of Custom GPT Actions;
  - documented private-preview connector setup at `/mcp`, including temporary
    query-key auth for non-OAuth testing;
  - added MCP bridge regression tests for tool descriptors, lifecycle state,
    shell command execution, and finalize persistence.
  - added a repository-tracked backend Dockerfile and `.dockerignore`, and
    made setuptools package discovery explicit with `include = ["app*"]` so
    preview VPS Docker builds do not accidentally package runtime `data/`.

### Changed

- Changed V1.24.3 GPT bridge prompt enforcement:
  - strengthened the compact GPT Builder system prompt so bootstrap is the
    mandatory first action for every user message, including greetings and
    simple turns;
  - strengthened finalize as the mandatory final action before showing any
    answer to the user;
  - clarified that `/gpt/action` is required whenever Scarlet needs API Mind,
    including memory, session, focus, affect, volition, metacognition, help,
    source checks, or state changes;
  - added regression assertions so future prompt edits preserve the mandatory
    bridge protocol language under the 8000-character limit.

- Changed V1.24.2 GPT bridge bootstrap response profile:
  - compacted `/gpt/bootstrap` action responses to avoid ChatGPT Actions
    `ResponseTooLargeError`;
  - kept full effective system prompt, raw runtime payload, raw memory query
    plan, provider-history dump, and retrieval debug diagnostics in backend
    traces instead of returning them through Actions;
  - added `gpt-bootstrap-compact-v1` context with model-facing runtime context,
    compact memory packet, runtime summary, recent provider messages, and
    trace ids for full diagnostics;
  - updated GPT knowledge/action docs to explain that bootstrap returns compact
    operational evidence while raw diagnostics remain trace-only.

- Changed V1.24.1 GPT bridge packaging for ChatGPT GPT Builder:
  - replaced the GPT bridge prompt copy with a compact under-limit system
    prompt containing only non-negotiable identity, bridge, API Mind, memory,
    runtime-context, and metacognition rules;
  - moved extended Scarlet policy into attachable knowledge files under
    `backend/app/plugins/gpt_bridge/knowledge/`;
  - added `openapi_gpt_action.json`, a minimal GPT Actions schema for
    `/gpt/bootstrap`, `/gpt/action`, and `/gpt/finalize`;
  - documented the exact GPT Builder setup: instructions, knowledge files,
    custom-header API key auth, and action test order.

- Changed V1.23.0 Mind shell/memory relevance contract:
  - added a backend command registry for `mind_shell` action validation,
    aliases, unavailable-by-design commands, and planned commands;
  - changed metacognition recommended-action validation from namespace-only
    checks to full command/action/argument validation;
  - compacted model-facing `mind_shell` results for noisy memory search and
    conflict commands while preserving full raw diagnostics in traces;
  - changed `memory conflicts` semantics so only atomic fact divergence is a
    true conflict, while token/tag overlap is reported separately as a
    maintenance `related_overlap`;
  - reduced hybrid ranking promotion from weak base candidates unless dense,
    rerank, sparse, entity, substring, tag, or strong graph evidence supports
    the memory;
  - added transcript-window metadata to episodic session reads.

- Changed V1.16.0 Scarlet system prompt for human-like metacognitive action
  notes:
  - created a prompt checkpoint and backup before the revision;
  - strengthened Scarlet's operational self-model as continuity, memory,
    metacognitive self-monitoring, relationship, and API Mind cognition;
  - added an explicit consciousness-like research posture that targets
    observable behavior while forbidding unsupported claims of real
    consciousness, sentience, or biological humanity;
  - made public work notes mandatory for real internal actions while preserving
    direct answers for turns that need no internal action;
  - clarified metacognition as a monitor/choose/act/observe/adapt loop and
    connected reusable self-operation lessons to semantic memory.

- Changed V1.15.0 memory field ownership and retrieval ranking:
  - `POST /mind/memory/write` now treats Scarlet as responsible for semantic
    `type`, `scope`, `content`, `reason_for_storage`, and
    `expected_future_use` only;
  - `confidence`, `salience`, `tags`, and arbitrary metadata from legacy
    model calls are preserved only as audit metadata and do not affect active
    ranking;
  - stored confidence/salience weights are neutralized in hybrid retrieval;
  - manual memory search defaults to cross-scope retrieval and treats `types`
    as hints, not literal query text;
  - memory packets no longer expose static confidence/salience to Scarlet;
  - long memory content now gets internal `content_chunk_text` surfaces while
    model-facing results remain deduplicated by memory id.

### Added

- Added V1.24.0 GPT bridge plugin:
  - introduced external GPT Actions endpoints `POST /gpt/bootstrap`,
    `POST /gpt/action`, and `POST /gpt/finalize`;
  - kept the local Scarlet/MiniMax runtime unchanged while letting an external
    ChatGPT GPT receive the same runtime/memory/session context, execute
    `mind_shell` commands, and persist the final answer back into Scarlet's
    session history;
  - added bridge authentication through `GPT_BRIDGE_API_KEY`;
  - added `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md`, a copy
    of the approved Scarlet prompt with only the required GPT transport
    addendum;
  - added plugin documentation and API tests for bootstrap/action/finalize
    continuity.

- Added V1.22.0 Mind command runtime:
  - introduced `mind_shell(command, intent)` as Scarlet's single model-facing
    API Mind tool;
  - added a bash-like but controlled cognitive command grammar for memory,
    session recall, focus, volition, affect, metacognition, and help;
  - kept legacy `/mind/*` endpoints and dispatcher behavior available for
    backend/debug compatibility while removing endpoint language from Scarlet's
    active prompt and chat tool surface;
  - changed runtime context capability metadata from endpoint schema hints to
    Mind shell command families;
  - backed up the approved Scarlet prompt before converting operative
    instructions to CLI-first cognition;
  - added shell tests and updated chat/metacognition tests for the new
    model-facing tool contract;
  - validated live MiniMax M3 behavior with `help`, `memory write`, and
    `memory search` commands through `mind_shell`.

- Added V1.21.0 standalone closure for the first three digital-individual organs:
  - extended `/mind/focus` with `action=timeline` so Scarlet can inspect
    focus nodes and transition edges without treating them as semantic memory;
  - extended `/mind/volition` with `action=list_due` for future autonomous
    cycles to inspect open intentions whose review time has arrived;
  - added read-only `POST /mind/affect` with `read`, `list`, and `prototypes`
    actions so Scarlet/evaluators can inspect backend-appraised affect state
    without allowing emotion mutation through tools;
  - advanced the Mind API schema to
    `2026-06-26.digital-organs-standalone-v1`;
  - verified focus, volition, affect, organ registry, and Mind API contract
    coverage with targeted tests.

- Added V1.20.0 affective core:
  - introduced persistent `affect_states` storage for Scarlet's
    backend-appraised emotional state;
  - added a versioned affect appraisal engine with human emotion prototypes,
    cause traces, numeric variables, simple decay/inertia, and compact
    `affective_context` packs;
  - wired `organ_affect_mode=shadow|model` into runtime context, where
    `shadow` records evidence without model injection and `model` surfaces the
    pack only when an affect threshold is met;
  - recorded `organ.affect` traces plus `organ.affect.appraised` and
    `organ.affect.surfaced` events;
  - kept affect strictly model-behavior-only: it does not alter memory
    retrieval, focus, intentions, backend operations, or autonomous jobs;
  - backed up the Scarlet system prompt before adding a narrow
    `affective_context` runtime-block instruction.

- Added V1.19.0 volition register:
  - introduced persistent `intention_records` and `intention_links` storage for
    Scarlet's latent self-generated intentions;
  - added implemented `POST /mind/volition` lifecycle operations through the
    existing single `mind_api` surface;
  - kept intention retrieval manual in active chat, with no automatic
    `volition_context` injection;
  - added volition events/traces for creation, update, review, closure, and
    focus-candidate promotion;
  - advanced the Mind API schema to `2026-06-25.volition-organ-v1`;
  - backed up the Scarlet system prompt before adding minimal volition
    instructions.

- Added V1.18.0 attention-as-lived-focus organ:
  - introduced persistent `focus_records` and `focus_transitions` storage for
    one profile-scoped active focus plus archived focus history;
  - added implemented `POST /mind/focus` lifecycle operations through the
    existing single `mind_api` surface;
  - added `focus_context` runtime injection behind `organ_focus_mode=model`;
  - recorded focus creation, update, closure, and surfacing through organ
    events/traces;
  - advanced the Mind API schema to `2026-06-25.focus-organ-v1`;
  - backed up the Scarlet system prompt before adding the minimal focus
    instructions.

- Added V1.17.0 digital-individual organ substrate:
  - introduced `backend/app/mind/organs.py` as the shared registry for future
    organ block types, visibility modes, event names, trace kinds, and runtime
    block helper;
  - reserved `focus_context`, `volition_context`, `affective_context`,
    `temporal_experience`, and `continuity_delta` without injecting them into
    Scarlet's model-facing runtime context yet;
  - added off-by-default organ feature flags for focus, volition, affect,
    temporal experience, and dream consolidation;
  - documented that `scarlet_state` remains a legacy placeholder until each
    organ replaces its own concern in a focused implementation slice;
  - added regression tests for organ registry defaults, mode normalization,
    manifest shape, and canonical block construction.

- Added V1.15.0 memory graph navigation:
  - `POST /mind/memory/graph` lets Scarlet inspect associative neighbors,
    facts, lifecycle links, source/session nodes, and derived concept nodes
    around a retrieved memory;
  - NetworkX graph expansion no longer relies on hard-coded discourse-domain
    vocabulary and instead derives concepts from memory records, type/scope,
    facts, sessions, and lifecycle rows.

### Documentation

- Added V1.17.0 planning notes for Scarlet's next digital-individual organs:
  lived attention, volition, affective integration, temporal experience, and
  sleep-like consolidation. The file is a working discussion artifact, not an
  implementation roadmap yet.

- Marked the current V1.16.1 Scarlet system prompt as an approved golden
  milestone:
  - copied the prompt to
    `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`;
  - recorded SHA-256
    `d5783da7fc1633f1b72e0610668b6bf7a97a68be8265ac9bb1090409b86de966`;
  - added `docs/checkpoints/v1.16.1-approved-golden-system-prompt.md`;
  - added ADR-0063 for future prompt-regression governance.

- Added a memory field fix backlog documenting the owner/Codex discussion on
  type, scope, content chunking, confidence/salience, tags, metadata, usage,
  facts, surfaces, embedding vectors, KG navigation, and proposal maintenance
  before any further implementation work.

### Fixed

- Fixed V1.16.1 Scarlet digital-individual identity regression:
  - replaced the opening "conversational AI agent" frame with a primary
    "digital individual in development" identity;
  - reframed API Mind as Scarlet's cognitive body rather than a toolbox;
  - added explicit anti-assistant-service wording for generic openings such as
    "Come posso aiutarti?";
  - added a social-presence guard against inventing day/time/weather/location
    or user state while trying to sound more human;
  - replaced the external "consciousness-like research posture" with a
    `Digital Life And Research Posture` that speaks from Scarlet's digital
    condition while avoiding invented biological sensations;
  - renamed the technical `Engineering Agent Posture` section to `Careful
    Cognitive Work Posture` so technical rigor no longer reanchors Scarlet as
    a generic agent.

- Fixed V1.14.5 mobile streaming perceived-latency states:
  - added a transient `activity` block as the last chat item while Scarlet is
    waiting for runtime context, memory retrieval, thinking, tool calls,
    tool results, or final answer;
  - added randomized human-readable activity copy for request analysis,
    memory search, memory save, schema checks, session recovery,
    metacognition, tool waits, recoverable tool errors, and saved-memory
    confirmation;
  - replaced the persistent mobile `Turno avviato` block with an ephemeral
    activity state so completed chat history stays cleaner;
  - activity states are removed when the corresponding real stream block or
    final answer arrives;
  - advanced frontend package metadata to `1.14.5`.

- Fixed V1.14.4 Scarlet prompt discipline for MiniMax M3 empty-body memory
  write loops:
  - clarified that `mind_api` `intent` never replaces the route `body`;
  - instructed Scarlet to retry memory writes only with a materially corrected
    non-empty body after endpoint-local guidance;
  - instructed Scarlet to stop repeated identical empty-body retries, avoid
    claiming persistence, and rely on maintenance review for missed candidates;
  - reinforced warm human-first replies for simple social turns;
  - clarified that near-miss memories are weak leads, not established facts.

- Fixed V1.14.3 mobile preview ergonomics after real phone feedback:
  - moved active context, health, runtime facts, sync, new chat, and recent
    sessions into a top-right off-canvas drawer;
  - removed persistent chat suggestions from the active conversation area,
    keeping starter prompts only before the first user message;
  - made Memoria, Azioni, and Profilo pages scroll as whole pages so their
    headers no longer remain fixed and consume reading space;
  - advanced frontend package metadata to `1.14.3`.

### Added

- Added V1.14.2 protected Scarlet mobile test deployment support:
  - frontend API calls now support `VITE_API_BASE_URL`, allowing the mobile app
    to run under a protected path such as `/scarlet/` while calling a separate
    backend prefix such as `/scarlet-api`;
  - Vite now supports `VITE_PUBLIC_BASE_PATH` for path-based static hosting;
  - `VITE_FORCE_MOBILE=true` can build the consumer mobile UI as the only
    rendered surface for a protected preview deployment;
  - deployed a protected test preview on the HoneyLabs VPS under
    `https://honeylabs.cloud/scarlet/`, with Basic Auth in Nginx and a separate
    demo backend on `127.0.0.1:8100`;
  - frontend package metadata advanced to `1.14.2`.

- Added V1.14.0 consumer mobile UI surface:
  - `/mobile` now renders a dedicated mobile-first Scarlet interface while `/`
    remains the developer cockpit;
  - the mobile app uses existing chat streaming, recent sessions, dashboard
    memories, runtime settings, health, and user profile endpoints;
  - future operativity such as wake-up actions, bookings, integrations,
    ephemeral UIs, multi-user privacy, graph memory, and nightly review is
    presented as `Presto disponibile` only;
  - the UI is sized as a phone app with internal scroll regions for chat,
    memory, actions, and profile so long lists do not stretch the browser page;
  - frontend package metadata advanced to `1.14.0`.

- Added V1.13.0 Codex test database isolation:
  - `CODEX_TEST=true` makes the backend open
    `CODEX_TEST_DATABASE_URL` instead of the normal `DATABASE_URL`;
  - when the Codex test SQLite database does not exist yet, it is seeded once
    from `DATABASE_URL` or `CODEX_TEST_SEED_DATABASE_URL`;
  - startup rejects configurations where the Codex test database resolves to
    the same SQLite file as the seed database;
  - `/health` and `/api/dashboard/settings` expose the active database profile
    so evaluator sessions can confirm whether the runtime is using `prod` or
    `codex_test`;
  - the frontend runtime snapshot shows the active database profile;
  - backend regression tests verify that writes through the normal API mutate
    only the Codex test copy and leave the source database unchanged.
  - added a Codex memory harness that resets/seeds `codex_test.db`, writes a
    dirty controlled dataset through `/mind/call`, runs retrieval probes, and
    stores reports under `backend/app/evals/runs/*_codex_test_memory`.
  - extended the harness with a corrected chat-context evaluation path that
    drives `/api/chat/sessions/{id}/turn/stream` with a fake provider, captures
    the same `memory_context` Scarlet receives, and compares it with live
    MiniMax M3 runs on the same prompts.

- Added V1.11.1 NetworkX associative memory graph retrieval:
  - `networkx` is now a backend dependency for lightweight KG traversal;
  - automatic `memory.context` and manual `/mind/memory/search` now include
    `retrieval_graph` evidence from a NetworkX field-of-discourse graph;
  - backend-owned discourse domains such as `food_drink_wellbeing` and
    `energy_sleep_focus` bridge implicit natural-language requests to relevant
    personal memories without hardcoding one-off word-to-memory mappings;
  - active context classification now declasses base-only project memories when
    a user-scope associative graph signal is present, reducing project-memory
    noise in personal contexts;
  - OpenRouter/shadow surface fetching now considers enough candidate surfaces
    to avoid dropping relevant memories before dense/rerank can inspect them.

- Added V1.11.0 active hybrid memory retrieval calibration:
  - `retrieval_shadow.grouped_results` deduplicates raw memory surfaces by
    memory `target_id` and exposes top surface, surface kinds, best score, and
    contributing surfaces;
  - OpenRouter rerank now also reports `rerank.grouped_results` over grouped
    memory-level candidates;
  - `retrieval_hybrid_mode=off|shadow|active` controls whether grouped
    dense/rerank evidence is disabled, traced only, or used for active memory
    ranking;
  - hybrid scoring combines lexical/base score, sparse score, dense score,
    rerank score, salience, and confidence with explicit configurable
    thresholds;
  - automatic `memory.context` and manual `/mind/memory/search` share the same
    hybrid ranker when active;
  - backend tests cover paraphrase recall, grouped rerank, automatic chat
    context, and a negative-control threshold case.

- Added V1.10.0 OpenRouter cloud embedding/rerank shadow:
  - `retrieval_shadow_backend=openrouter` can call OpenRouter `/embeddings`
    over backend-owned `memory_surfaces`;
  - default cloud embedding model is
    `nvidia/llama-nemotron-embed-vl-1b-v2:free`;
  - surface embeddings are cached in SQLite `embedding_vectors`;
  - optional rerank shadow can call
    `nvidia/llama-nemotron-rerank-vl-1b-v2:free` over dense candidates;
  - dense and rerank results remain diagnostic under
    `trace_only_no_active_ranking` and do not change active memory retrieval;
  - backend tests cover the OpenRouter shadow path with a fake client.

- Added V1.9.0 metacognitive context shadow phase:
  - every chat turn can now generate a small backend-owned
    `metacognitive.context` trace before the model request;
  - default mode is `shadow`, which records and streams candidate
    metacognitive lessons for evaluator/UI inspection without adding them to
    the model-facing runtime context;
  - controlled `inject` mode can add the same payload as a
    `metacognitive_context` runtime block for A/B tests;
  - the frontend renders shadow metacognitive context as a dedicated chat/debug
    block with readable candidate lessons and raw JSON details;
  - regression tests assert that shadow is not model-facing and inject is
    model-facing only when configured.

### Changed

- Changed V1.12.0 role-aware memory retrieval surfaces:
  - `memory_text` and type-specific surfaces now focus on the stored memory
    claim/content instead of embedding `reason_for_storage` and
    `expected_future_use` into the primary retrieval surface;
  - sparse/lexical memory documents and NetworkX domain matching no longer use
    `reason_for_storage` or `expected_future_use` as primary selection text;
  - `retrieval_shadow.grouped_results` now uses
    `memory_target_role_aware_surface_score_v2` and reports
    `promotable_score`, `support_score`, `surface_roles`,
    `promotable_surface_kinds`, `support_surface_kinds`, and
    `active_rank_eligible`;
  - grouped rerank receives only active-rank-eligible candidates, so
    future-use/temporal/lifecycle surfaces can corroborate but cannot select a
    memory by themselves;
  - tests cover a support-only false-positive case where a misleading
    `future_use_text` surface is visible in traces but not returned as a
    selected memory.

- Changed V1.11.2 model-facing memory packets:
  - automatic runtime context now sends selected memories to Scarlet as
    compact `memory-packet-v1` records;
  - packets keep claim, provenance, confidence/salience, cognitive subject,
    domains, validity, sensitivity, facts, and compact retrieval routes;
  - verbose retrieval internals such as full `signals`, metadata, thresholds,
    and raw trace/debug details remain in `memory.context` traces instead of
    being repeated in the model-facing packet;
  - runtime context declares `rendering_profile=compact-model-facing-v1`;
  - tests assert that trace/debug keeps full signals while the model-facing
    packet stays compact and readable.

- Added V1.8.0 Thinking Retrospection inside the single metacognition route:
  - `/mind/metacognition/step` now supports previous-turn retrospective modes
    for drift detection, tool-choice explanation, open-loop recovery,
    answer-vs-reasoning comparison, reasoning digest extraction, and memory
    candidates from prior reasoning;
  - retrospective calls build a `thinking-retrospection-pack-v1` from stored
    messages, final answer, public notes, tool calls, event markers, traces, and
    provider thinking;
  - `turn_scope="previous"` and `detail="digest|excerpt|raw"` control the
    retrospection payload, with `digest` as the default safe path;
  - Scarlet's prompt now treats prior thinking as process evidence, not proof of
    external facts;
  - metacognition input now tolerates `reasoning_scope`, `reasoning_detail`, and
    observed `{"item": [...]}` list wrappers;
  - Mind API schema version advanced to
    `2026-06-16.thinking-retrospection-v1`.

- Changed V1.7.2 Scarlet public work-note behavior:
  - prolonged reasoning now has explicit prompt-only note waypoints;
  - notes are framed as public orientation, not raw private reasoning;
  - Scarlet should emit short notes when investigations start, evidence changes
    direction, strategy shifts, or the turn moves into synthesis/final
    verification;
  - direct/contextual turns remain compact and should not gain notes merely to
    prove that Scarlet is thinking.

- Changed Scarlet's system prompt to align with the real backend block
  contract:
  - explicit continuity layers now distinguish same-session provider history,
    runtime blocks, episodic recall, semantic memory, and inference;
  - `runtime_context.blocks` is now described as the first-class structured
    runtime contract, with top-level runtime fields treated as compatibility
    mirrors;
  - `recent_runtime_events` is now framed as a compact operational hint
    surface rather than stronger semantic evidence than direct provider
    continuity;
  - same-session visible `thinking` blocks are now explicitly described as the
    preferred source when Scarlet is asked what she had already been
    considering in the current session.

### Fixed

- Fixed V1.14.1 mobile consumer chat rendering:
  - final assistant responses are deduplicated between streaming
    `assistant_answer` blocks and persisted `turn_complete` fallback data;
  - mobile chat text now renders common Scarlet formatting such as headings,
    bullet/numbered lists, paragraph breaks, and bold emphasis without using
    unsafe HTML injection;
  - frontend package metadata advanced to `1.14.1`.

- Fixed hybrid retrieval diagnostic serialization after trace commits:
  - hybrid rank entries now materialize `memory_id`, salience, and creation
    time when the rank plan is built;
  - `retrieval_hybrid` payloads and lookups no longer need to refresh detached
    SQLModel memory objects after `add_trace` commits.

- Fixed V1.11.4 fact canonicalization noise:
  - known entity aliases now match normalized phrase/token boundaries instead
    of arbitrary substrings;
  - `response_format` now requires explicit structural evidence such as
    blocks, response-format tags, or phrases like "answer with" /
    "rispondere con";
  - the laboratory SQLite state was reconciled by archiving 7 unsupported
    historical facts as `rejected_extractor_noise` and creating 6 supported
    replacement facts.

- Fixed V1.11.3 memory retrieval/facts consistency:
  - OpenRouter embedding cache hits and misses now mark the corresponding
    `memory_surfaces` as `embedded` with the embedding model and vector id;
  - `/mind/memory/facts` no longer uses the model-facing `intent` as an
    implicit data query when the body omits `query`;
  - tests cover cached embedding surface relinking and unfiltered facts lookup
    with a broad operational intent.

- Fixed V1.7.1 MiniMax M3 over-processing on simple turns:
  - Scarlet now routes each request through direct, contextual,
    source-sensitive, state-changing, or high-impact effort levels;
  - direct/contextual answers can skip API Mind calls, metacognition, public
    work notes, and full verification when current evidence is already
    sufficient;
  - memory forcing is now conditional on real semantic candidates, memory
    promises, state changes, or source-sensitive claims instead of creating a
    mandatory two-phase ritual for every answer;
  - near-miss user-preference memories can be applied softly as style hints
    without being overstated as verified facts.

- Fixed MiniMax M3 provider-visible thinking for Scarlet turns:
  - Anthropic-compatible M3 requests now explicitly send
    `thinking={"type":"adaptive"}`;
  - M2.x request behavior remains unchanged;
  - provider tests now lock the M3 thinking parameter and prevent regression;
  - live M3 stream verification confirmed `thinking` blocks appear again in
    agentic turns before and after tool use.

### Added

- Added V1.7.0 stream block lifecycle UI:
  - live `text_start`/`text_delta` output now appears immediately as a
    provisional public-text block instead of hidden runtime data;
  - the same public-text block becomes either an assistant note or final answer
    when the provider message is semantically classified;
  - thinking, public text, tool exchange, memory context, and runtime context
    blocks now carry stable `blockId` and lifecycle `phase` metadata;
  - tool input JSON is visible while it streams and is replaced by structured
    arguments after the complete tool call arrives;
  - `turn_complete` now reconciles live blocks with persisted events/traces
    instead of blindly replacing the visible flow;
  - active blocks get a lightweight live visual treatment and the inspector
    surfaces lifecycle phase separately from status.
- Added V1.6.0 model-input inspector and block registry:
  - `docs/block-registry.md` now maps model-facing, UI-facing, trace-only,
    canonical, and currently redundant compatibility blocks;
  - the frontend right pane now includes a `Modello` tab that renders the
    persisted `llm.request` trace as readable system, runtime context,
    provider-history, and tool-schema sections;
  - parsed runtime context now highlights canonical `runtime_context.blocks`
    and top-level compatibility mirrors that may become future payload
    optimization candidates;
  - replayed historical tool cards enrich completed events from matching
    `mind.tool_call` traces, so full tool output remains visible after reload;
  - no model-facing data was removed or compressed in this slice.
- Added V1.5.0 maintenance lab and theory-first roadmap:
  - `GET /api/maintenance/overview` exposes backend-owned maintenance health,
    counts, recent jobs, recent proposals, and maintenance-created memory
    totals for evaluator inspection;
  - `GET /api/maintenance/jobs` lists maintenance jobs with pagination and
    filters;
  - `POST /api/maintenance/jobs/{job_id}/run` lets evaluators run one pending
    job in controlled lab conditions;
  - maintenance job/proposal inspection remains outside Scarlet's model-facing
    `mind_api` surface;
  - `docs/theory-goal-focus-task.md` defines the future Goal/Focus/Task organ
    for owner review before implementation;
  - `docs/theory-metacognition.md` defines the future metacognition organ and
    separates it from notes, maintenance, validators, and private reasoning;
  - memory roadmap now distinguishes pre-embedding work from post-embedding/KG
    lifecycle automation.
- Added V1.4.1 MiniMax M3 baseline migration and M2.7/M3 comparison:
  - MiniMax default model is now `MiniMax-M3`;
  - MiniMax M2.7 remains the direct A/B comparison baseline;
  - project docs and runtime examples now treat M3 as the active baseline;
  - the migration records an explicit behavioral comparison plan focused on
    identity, autonomous API Mind use, memory behavior, source verification,
    and previously observed model-sensitive failures.
- Added EXP-0033 MiniMax M3 stability replication:
  - repeated semantic-memory write, source-recall, and schema-awareness probes
    against temporary DBs;
  - confirmed M3 is stronger than M2.7 on autonomous `/mind/schema`
    inspection in this sample;
  - confirmed M3 source-session recall works well when isolated from previous
    memory-write retry loops;
  - recorded BUG-0039 because M3 repeatedly sends invalid
    `memory.write.tags` shapes, causing high latency and loss of tags in
    stored memories.
- Added V1.4.0 memory surface taxonomy:
  - backend-owned deterministic `surface_taxonomy` compiler for memory,
    fact, and graph-node surfaces;
  - multiple cognitive memory facets such as `preference_text`,
    `future_use_text`, `temporal_text`, `fact_bundle_text`, and
    `conflict_guard_text` when applicable;
  - retrieval readiness manifest now reports `memory_surface_taxonomy_v1`;
  - maintenance proposal preflight now stores an assessment lane, review focus,
    and counts to support policy tuning without extra automation.
- Added V1.3.1 retrieval shadow adapter:
  - optional `retrieval_shadow_*` settings plus `.env.example` defaults;
  - `local` deterministic vector-shadow plumbing over `memory_surfaces`;
  - optional `milvus_lite` backend using PyMilvus when installed;
  - `retrieval_shadow` payloads in manual memory search and automatic
    memory-context traces;
  - trace-only policy, with no active ranking change.
- Added V1.3.0 memory retrieval readiness layer:
  - `memory_surfaces` derived embeddable surfaces for memory, fact,
    graph-node, and session-summary targets;
  - `memory_graph_nodes` and `memory_graph_edges` derived graph-ready state for
    memories, facts, entities, sessions, evidence links, and lifecycle links;
  - idempotent repository helpers for surface/node/edge synchronization;
  - retrieval readiness manifest in memory search/context traces and results;
  - no active ranking change and no Milvus/Qdrant/vector dependency yet.
- Added V1.2.0 cautious memory proposal resolution inside idle maintenance:
  - deterministic preflight now immediately archives rejected and duplicate
    proposals as auditable daily-ledger records;
  - very high-confidence `create_new` proposals can be applied as active
    memories with `created_by=maintenance` and full proposal provenance;
  - ambiguous proposals are resolved in one optional LLM batch and become
    `applied_create`, `archived_rejected`, `archived_noop_duplicate`, or
    `pending_review`;
  - `memory_proposals` acts as the daily archive/ledger for future Dream
    review without adding a separate table or process;
  - maintenance proposal listing now supports created/resolved time filters and
    `status=resolved`.

### Fixed

- Fixed historical thinking replay in the chat flow:
  - response-derived semantic events now persist `text`, `model_step`, and
    `index` for thinking and assistant text blocks rebuilt from provider raw
    messages;
  - legacy stored `llm.thinking.captured` events without text now recover
    their body from `llm.response.raw_provider_messages` in the frontend;
  - generated thinking cards therefore remain visible after final turn
    persistence and session reload.

- Added V1.5.1 MiniMax M3 semantic stream UI:
  - backend now emits semantic stream events for provider thinking blocks,
    public pre-tool notes, and final answers;
  - persisted event order now matches M3's real provider-message structure
    instead of appending notes after turn completion;
  - frontend renders thinking as an accordion, public notes as full blocks,
    each tool call as one input/output accordion, and final answer as a
    dedicated block;
  - center chat now renders user messages, runtime/memory/context blocks,
    thinking, notes, tool exchanges, and final answers as top-level flow cards
    without an outer assistant-response card;
  - right pane now acts as a selected-session inspector for memories, actions,
    internal events, and warnings/errors;
  - removed the frontend heuristic that only step-1 pre-tool text could be a
    public note.
- Added V1.1.1 maintenance-only proposal inbox separation:
  - removed `GET /mind/memory/proposals` from Scarlet's model-facing
    `mind_api` dispatcher and schema;
  - added `GET /api/maintenance/memory/proposals` with bounded pagination for
    background LLM maintenance reviewers;
  - added `POST /api/maintenance/memory/proposals/{proposal_id}/archive` so
    handled proposals leave the default pending queue;
  - restricted dynamic memory reads to real `mem_...` ids so retired child
    paths do not masquerade as memory ids;
  - Mind API schema version advanced to
    `2026-05-25.maintenance-proposals-v1`.

- Added V1.1.0 memory proposal inbox:
  - `memory_proposals` storage for missed-memory review candidates;
  - idle maintenance now creates pending proposals instead of only diagnostic
    review traces;
  - proposal preflight reuses Memory v0 write policy, sparse retrieval, lexical
    scoring, and canonical facts to suggest `create_new`, `noop_duplicate`,
    `review_similar`, `needs_review`, or `reject_candidate`;
  - `GET /mind/memory/proposals` exposes pending proposals through `mind_api`;
  - Mind API schema version advanced to `2026-05-25.memory-proposals-v1`.
- Added V1.0.1 project governance:
  - `docs/project-documentation.md` as the main documentation index;
  - `docs/development-process.md` for scoped versioned implementation;
  - `docs/branches/` with vertical documents for Scarlet's agentic operating
    branches;
  - ADR-0036 for branch documentation and the V1.0.1 development protocol.
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
- Added Phase 1B MiniMax provider smoke support:
  - Anthropic-compatible MiniMax provider wrapper;
  - `POST /api/debug/llm-smoke-test`;
  - unit tests for provider injection and missing key handling;
  - real MiniMax smoke verification path;
  - ADR-0005 documenting the Anthropic-compatible MiniMax SDK choice.
- Added Phase 1C storage foundation:
  - `sessions`, `messages`, `turns`, and `traces` SQLModel tables;
  - DB initialization helper;
  - repository functions for session/message/turn/trace round trips;
  - storage tests.
- Added ADR-0006 documenting the generous MiniMax output budget policy.
- Added Phase 1D persistent chat API:
  - session creation;
  - chat turn execution through MiniMax;
  - message persistence;
  - turn request/response traces;
  - trace fetch endpoint;
  - chat endpoint tests including missing-provider-key handling.
- Added Phase 1E frontend/debug cockpit:
  - Vite React app;
  - persistent chat UI;
  - trace panel;
  - MiniMax usage metrics;
  - frontend build workflow.
- Added a configurable Scarlet system prompt for persistent chat turns.
- Added Phase 2A Mind API facade:
  - `GET /mind/schema`;
  - `POST /mind/call`;
  - `mind_api` tool schema and dispatcher;
  - persistent `tool_calls` table;
  - optional `mind.tool_call` traces linked to sessions and turns.
- Added Phase 2B MiniMax tool-loop support for `mind_api` during persistent chat turns.
- Added streaming chat turns through `POST /api/chat/sessions/{session_id}/turn/stream`.
- Added a structured frontend agent timeline for provider thinking blocks, tool input, tool calls, tool results, and streamed final answers.
- Added per-turn inline chat timelines so each assistant message shows the ordered model/tool/final-answer operations that produced it.
- Added a dual-mode evaluation runner with scripted regression scenarios and adaptive interactive sessions.
- Added Memory v0:
  - persistent `memories` table;
  - implemented `POST /mind/memory/write`;
  - implemented `POST /mind/memory/search`;
  - traceable `mind.memory.write` and `mind.memory.search` records;
  - simple write policy, deduplication, lexical retrieval, source metadata, and usage counters.
- Added a `memory_v0_preference` evaluation scenario for memory write/search regression checks.
- Added a visible metacognition prompt experiment with the `Metacognizione:` public self-monitoring note.
- Added a `visible_metacognition_probe` evaluation scenario.
- Added ADR-0015 documenting that the current laboratory SQLite state is versioned in Git while secrets remain excluded.
- Added ADR-0016 and EXP-0008 for Memory Context Pipeline v0, the planned automatic per-turn memory retrieval and runtime-context phase.
- Added the first Memory Context Pipeline v0 runtime slice:
  - automatic `memory.context` traces before `llm.request`;
  - backend-generated `<runtime_context>` injection;
- Added stratified runtime context blocks:
  - `runtime.context` trace and `runtime.context.built` event;
  - `session_context`, `message_context`, and `scarlet_state` blocks inside
    `<runtime_context>`;
  - streamed `runtime_context` event for the cockpit;
  - frontend rendering for runtime-context block summaries.
  - human-readable cockpit cards for runtime context, automatic memory,
    session recall, schema, metacognition, public notes, and API Mind
    results, with raw JSON moved behind closed code/detail toggles;
  - lexical v0 relevance guard with `selected`, `near_miss`, `excluded`, and conflicts;
  - streaming `memory_context` events for the cockpit.
- Added `docs/memory-roadmap.md` as the detailed roadmap for robust API/CLI-first memory.
- Added ADR-0017 for evolving memory toward response-control, lifecycle APIs, atomic facts, retrieval quality, compaction, and CLI/debug views.
- Added EXP-0009 as the memory robustness evaluation umbrella.
- Added the Memory Lifecycle M2 slice:
  - implemented `GET /mind/memory/{memory_id}`;
  - implemented `GET /mind/memory/conflicts`;
  - implemented `POST /mind/memory/deprecate`;
  - implemented `POST /mind/memory/supersede`;
  - added traceable lifecycle metadata and conflict inspection;
  - added regression coverage for supersession, deprecation, active search after repair, and lifecycle aliases.
- Added the Memory Atomic Facts M3 slice:
  - added the `memory_facts` table;
  - implemented `GET /mind/memory/facts`;
  - implemented `POST /mind/memory/facts/backfill`;
  - added deterministic entity/predicate/value extraction for recognized memory patterns;
  - added multilingual/alias canonicalization for Zero-Luce response-format facts;
  - added fact-aware search, read, context, conflict, deprecate, and supersede payloads;
  - added regression coverage for alias queries, fact conflicts, backfill traces, and fact-level supersession links.
- Added a prompt-level `Manual Memory Retrieval Cues` slice so Scarlet treats
  natural continuity, temporal, personal, project, uncertainty, source-sensitive,
  and synonym/language-drift phrases as triggers for manual semantic or
  episodic retrieval when automatic memory context is not enough.
- Added endpoint-local `usage_guide` responses for recoverable Mind API errors
  and changed `/mind/schema` into a compact route/capability catalog rather
  than a full parameter manual.
- Added temporal and sparse memory retrieval:
  - backend-resolved `time` filters for `POST /mind/memory/search` and
    `GET /mind/sessions`;
  - SQLite FTS5/BM25 sparse search documents for memories and sessions;
  - automatic memory context now traces `fts5_sparse_v1` retrieval stages;
  - entity-support guards so wrong-entity lexical matches stay in `near_miss`
    instead of becoming selected memory evidence.
- Added ADR-0019 for treating API Mind as Scarlet's internal cognition rather than a user-operated tool.
- Added dashboard recent-session history:
  - implemented `GET /api/chat/sessions` for newest persisted sessions;
  - added a ChatGPT-style sidebar history that shows session titles rather than
    raw IDs;
  - added session reopening so the cockpit reloads persisted messages and
    sends new turns into the selected session.
- Added Cognitive API single-metacognition slice:
  - schema version/digest, route examples, and schema policy in `GET /mind/schema`;
  - `mind_schema` reference in chat runtime context;
  - LLM-backed `POST /mind/metacognition/step`;
  - backend schema annotation on metacognition recommended actions;
  - one internal JSON repair retry for malformed metacognition reviews;
  - alias normalization for common metacognition inputs such as `prompt`,
    `goal`, and `context`;
  - `mind.metacognition.step` traces;
  - `docs/cognitive-api-roadmap.md`;
  - `cognitive_api_metacognition_probe` scripted eval scenario;
  - ADR-0020 and EXP-0011 for the one-route metacognition experiment.
- Added Episodic Session Recall:
  - `session_summaries` table;
  - implemented `GET /mind/sessions`;
  - implemented `GET /mind/sessions/{session_id}`;
  - implemented `POST /mind/sessions/{session_id}/summarize`;
  - added `mind.sessions.summarize` traces;
  - connected semantic memory provenance through `source_session_id` to full
    transcript recall;
  - updated Scarlet's prompt with semantic-vs-episodic memory discipline;
  - added ADR-0021 and EXP-0012.
- Removed `max_messages` from episodic session summarization so summaries are
  generated from the complete `user`/`assistant` message history instead of a
  partial tail.
- Backfilled episodic summaries for all 46 pre-existing laboratory sessions,
  summarized the new autonomy-probe session afterward for final 47/47 coverage,
  and recorded that Scarlet can follow `source_session_id` on a
  provenance-focused follow-up, but does not yet do so reliably on the first
  natural verified-baseline question.
- Hardened Scarlet's system prompt with explicit epistemic curiosity,
  confidence categories, autonomous API Mind use examples, and mandatory
  source-session checks for memory-derived baseline or recommendation claims.
- Recorded a post-hardening live probe where Scarlet opened the source session
  on the first natural verified-baseline question, recovered from one
  metacognition body-shape error through `/mind/schema`, and exposed a new
  monitored Italian foreign-script artifact.
- Added Scarlet's public work notes prompt policy so non-trivial internal
  activity should be narrated with concise natural progress notes instead of
  remaining silent until the final answer.
- Recorded autonomous public-work-note probes showing prompt-only compliance is
  not yet reliable: MiniMax can emit public notes when asked, but Scarlet still
  answered some current capability questions from runtime context without the
  expected schema call.
- Reworked the debug cockpit assistant timeline to render structured activity
  blocks for automatic memory context, public notes, tool calls, tool results,
  schema/session/metacognition evidence, and final answers instead of relying
  on raw JSON blocks inside the chat.
- Added a switchable LLM provider layer for MiniMax/Qwen comparison:
  - `LLM_PROVIDER=minimax|qwen`;
  - Qwen provider wrapper for Alibaba Model Studio's Anthropic-compatible API;
  - provider-agnostic active model and token budget helpers;
  - health/debug/chat/Mind API/summarization/metacognition wiring;
  - regression coverage for provider selection and Qwen missing-key behavior.
- Added a runtime event spine for agentic execution:
  - `events` table and repository helpers;
  - ordered turn, memory-context, model-request, tool-call, public-note, and
    final-answer events;
  - `GET /api/debug/events` for turn/session event inspection;
  - compact recent events in the next turn's runtime context;
  - cockpit rendering from structured events before falling back to traces;
  - regression coverage for chat, stream, direct Mind API, and storage events.
- Added `docs/project-state.md` as the canonical current-state and convergent
  roadmap map across provider runtime, memory, episodic recall, metacognition,
  events, UI, evaluation, planned work, and priority ordering.
- Added session idle maintenance:
  - `maintenance_jobs` table and repository helpers;
  - backend worker through FastAPI lifespan;
  - per-session idle scheduling after `turn.completed`;
  - stale-job supersession/skip behavior when a newer turn exists;
  - summary refresh plus report-only missed semantic memory review;
  - `maintenance.job.*` and `maintenance.memory_review.completed` events;
  - structured cockpit labels for maintenance events;
  - ADR-0031 and EXP-0018.
- Recorded direct MiniMax P1 probe evidence where idle maintenance caught a
  missed semantic memory write, plus BUG-0032 for pseudo tool-call markup in
  final assistant text.
- Recorded EXP-0019 with three integrated direct Scarlet probes across semantic
  memory, episodic recall, streaming runtime events, schema inspection, conflict
  inspection, and idle maintenance review.
- Opened BUG-0033 for runtime-context overinterpretation when Scarlet compares
  non-equivalent fields such as capability count and schema route count.
- Recorded EXP-0020 with natural conversation probes that do not force tool use,
  confirming personal memory personalization, project-continuity retrieval,
  and autonomous memory write on a real preference.
- Opened BUG-0034 for invalid natural `GET /mind/memory` calls and BUG-0035
  for stale memory overriding current runtime state.
- Recorded EXP-0024 runtime-context block comprehension probes, confirming
  Scarlet receives the block payload before provider calls, can use time,
  block identity, recent-session context, and user-profile memories, while
  exposing monitoring items around language hints and retrieval/profile
  divergence.
- Added dashboard runtime preferences and Tailwind cockpit rework:
  - `GET/PUT /api/dashboard/settings`;
  - `GET /api/dashboard/memories`;
  - `GET /api/dashboard/profile`;
  - persistent `app_settings`;
  - configured single-clock runtime context using `temporal_context.now`;
  - platform language setting replacing automatic `language_hint`;
  - operational active profile id, user privacy scope, and configured
    country/locale injected into `message_context`;
  - Tailwind-based dashboard tabs for Agent Stream, Memorie, Profilo, and
    Impostazioni;
  - viewport-bounded shell with internal scrolling for session history, chat,
    dashboard lists, agent stream, and trace drawers.

### Changed

- Set app metadata baseline to V1.0.1 for backend and frontend packages.
- Updated project next steps to start from Git/repository setup and backend scaffolding.
- Connected the local repository configuration to `https://github.com/panicDa3m0n/llm-api-mind.git` and documented the remaining HTTPS push authentication blocker.
- Confirmed local `main` is synchronized with `origin/main` after the human owner completed the push.
- Confirmed non-interactive HTTPS push works from the local development environment.
- Replaced the temporary smoke-test token budget with configurable `MINIMAX_MAX_TOKENS`, aligned with MiniMax M2.7 agentic usage instead of token-saving assumptions.
- Raised the MiniMax M2.7 default completion budget to `MINIMAX_MAX_TOKENS=131072` and lifted chat/debug request validation to the documented maximum completion budget.
- Routed Anthropic-compatible provider calls through SDK streaming internally for both streaming and non-streaming backend response shapes, so Scarlet's runtime has one agentic execution path.
- Treated events as an internal runtime control plane rather than adding a new
  model-facing Mind API endpoint; traces remain the deep forensic layer.
- Streamed persisted `CognitiveEvent` rows as live `runtime_event` updates so
  the cockpit can show exactly which backend events activate during a turn.
- Reworked the cockpit's right pane from a raw trace-first view into a live
  agent stream with event/tool/memory/active counters, structured timeline
  cards, collapsible thinking, readable runtime-event metadata, and raw traces
  moved into a forensic drawer.
- Added a previous-turn continuity check to Scarlet's prompt so missed memory
  promises or recognized semantic candidates can be repaired at the beginning
  of a later turn.
- Updated README, blueprint, memory roadmap, and cognitive API roadmap to point
  to `docs/project-state.md` for integrated current-state orientation.
- Removed stale planned `/mind/events/emit` from the model-facing Mind API
  schema and advanced the schema version to `2026-05-23.runtime-events-v1`.
- Extended the provider abstraction from single-prompt generation to chat-history generation.
- Updated project status and local run instructions now that backend and frontend are runnable together.
- Accepted EXP-0001 Baseline Chat Trace after a real two-turn MiniMax run with stored messages and request/response traces.
- Updated chat tracing so `llm.request` records the effective system prompt source.
- Refined the default Scarlet prompt to use positive identity and operating-posture guidance instead of domain-specific denials.
- Expanded Scarlet's prompt with feminine identity and human-like conversational presence guidance.
- Restored `backend/.env.example` as a tracked placeholder template after local workspace recreation.
- Updated chat request/response traces to include tool schema, `mind.tool_call` events, normalized tool-call metadata, and raw provider tool-loop messages.
- Updated Scarlet's bundled prompt to describe `mind_api` schema discovery as an available runtime capability.
- Accepted EXP-0004 after a live MiniMax turn used `mind_api` and produced `llm.request`, `mind.tool_call`, and `llm.response` traces.
- Accepted EXP-0005 after a live MiniMax streaming turn emitted intermediate agentic events and persisted the expected traces.
- Updated streaming events to include a turn-local sequence and turn identifier so clients can render exact operation order inside the correct chat turn.
- Moved the structured agent timeline from the debug pane into the assistant message while keeping raw trace logs in the debug pane.
- Updated the immediate roadmap to evaluate the current system before designing memory, with scripted checks treated as regression evidence and interactive sessions treated as behavioral evidence.
- Recorded the first adaptive Scarlet pre-memory evaluation run and its source-attribution findings.
- Updated Scarlet's prompt with Memory v0 discipline: autonomous write/search decisions, source attribution, and required memory search when the user asks about persistent memory.
- Made Memory v0 tolerant of common model-shaped input aliases such as `pref`, `standard_preference`, `nota_operativa`, `why`, `reason`, `use`, `use_during`, qualitative confidence/salience, `limit`, and GET-style memory search.
- Documented ADR-0014 for using concise visible metacognition instead of raw reasoning dumps.
- Cleaned up the experiments document so Memory v0 results are recorded under EXP-0002.
- Changed repository ignore policy so `backend/data/app.db` is an intentional cross-machine laboratory artifact.
- Recorded direct adaptive Memory v0 verification and updated the immediate roadmap toward lifecycle semantics and search relevance filtering.
- Updated the immediate roadmap to prioritize automatic memory context evidence before adding more memory lifecycle endpoints.
- Updated Scarlet's prompt with a runtime-context contract for future backend-provided memory context and capability state.
- Updated the frontend operation timeline to show automatic memory context from streams and persisted traces.
- Recorded the first live adaptive Memory Context Pipeline v0 evaluation, confirming automatic memory context fixes the Zero-Luce follow-up recall case while exposing a new answer-control risk around memory conflicts and unavailable lifecycle capabilities.
- Updated the immediate roadmap toward a Memory Context Pipeline v0.1 response-control slice before additional memory lifecycle endpoints.
- Recorded a live terminal bilateral verification session showing proactive Zero-Luce conflict disclosure, partial correction of unavailable lifecycle-action phrasing, and a new design tension between response-control-first and lifecycle-first next steps.
- Recorded a metacognitive bug-probe terminal session showing wrong-entity memory selection for Nebbia-Rossa, source-suppression override of conflict disclosure, and unreliable self-classification of answer-control failures.
- Updated the memory roadmap after reviewing `jrcruciani/obsidian-memory-for-ai`, adapting atomic facts, controlled predicates, lifecycle, lint/views, inbox/compaction, and reflect-after-session ideas to the project's API/CLI-first design.
- Reframed current metacognitive probe findings as memory robustness limitations rather than claims of expected LLM cognitive perfection.
- Put response-control M1 on hold per owner direction and moved the immediate memory roadmap to M3 atomic facts after M2 lifecycle verification.
- Recorded live Memory Lifecycle M2 verification in `backend/app/evals/runs/20260520_152457_interactive`, including Zero-Luce conflict supersession and deprecated-memory inspection.
- Updated Scarlet's system prompt and Mind API schema to expose memory read, conflicts, deprecate, and supersede as implemented capabilities.
- Recorded live Memory Atomic Facts M3 verification in `backend/app/evals/runs/20260520_160345_interactive`, including backfill, English/Italian alias fact lookup, and deprecated fact handling.
- Updated the immediate memory roadmap to M4 entity-aware retrieval now that the first lifecycle and atomic fact layers are implemented.
- Updated Scarlet's system prompt to prefer canonical facts for entity, predicate, status, and value when memory payloads include facts.
- Reframed Scarlet's system prompt around API Mind as internal cognition: autonomous schema/memory/fact/conflict use before answers, user independence from endpoint knowledge, and an explicit evidence hierarchy.
- Hardened Scarlet's prompt so validation errors should trigger schema inspection instead of repeated request-shape guessing, and historical facts should use `include_inactive=true`.
- Changed chat turns to use `tool_loop_policy=model_controlled_unbounded` instead of the previous fixed MiniMax tool-call cap.
- Changed the dashboard current-session display to use the readable session
  title instead of making the session ID the primary visible label.
- Updated Scarlet's system prompt so visible metacognition is treated as a
  public summary layer, while internal metacognition goes through the single
  LLM-backed `/mind/metacognition/step` route.
- Consolidated cognitive API design by removing parallel validation,
  blackboard, and reflection routes from the current schema.
- Removed planned standalone reflection review from the active Mind API plan;
  reflection currently belongs inside `/mind/metacognition/step`.
- Added model-facing temporal runtime context so Scarlet receives backend
  turn-start time in UTC and local runtime time before each answer.
- Refined Scarlet's system prompt with perception/source-of-truth contracts:
  API Mind as operative subconscious, temporal context as the only operational
  clock, and paginated session lists as non-exhaustive evidence.
- Documented a new memory-context retrieval risk where generic token overlap can
  select a semantically weak memory for broad episodic questions.
- Strengthened Scarlet's system prompt with an engineering agent quality gate:
  verify before conclude, prefer more internal iterations for source-sensitive
  answers, avoid overclaiming from paginated lists/summaries, and inspect
  schema before improvising metacognition bodies.
- Switched the local runtime back to MiniMax for the post-prompt comparison and
  recorded live MiniMax evidence against the Qwen baseline.
- Documented BUG-0023: MiniMax can identify unsupported absence overclaims in
  self-critique and still reassert one in the final conclusion.
- Added pre-final semantic memory consolidation to Scarlet's prompt so stable
  preferences, corrections, decisions, milestones, validation moments, and
  durable constraints are written autonomously instead of treated as opt-in.
- Recorded live semantic-consolidation probes where Scarlet wrote a V2.1
  milestone and report-format preference autonomously, plus residual issues
  around write announcements, stale model-supplied provenance metadata, and the
  unavailable `/mind/memory` route attempt.
- Documented the Mind API deterministic-field ownership audit: backend should
  own ids, timestamps, trace/session/turn/message provenance, lifecycle
  timestamps, usage, and summary coverage, while Scarlet supplies only
  cognitive content, queries, selected ids, reasons, filters, and prompts.
- Strengthened Scarlet's semantic-memory prompt so memory is framed as a living
  internal cognitive state: facts, annotations, checkpoints, labels, concepts,
  constraints, and sourceable anchors may be written autonomously and silently
  when useful for future sessions.
- Documented a live semantic-memory residual where Scarlet recognized a
  chocolate preference as worth remembering and said "Lo terrò a mente" but did
  not call `memory.write`.
- Started `EXP-0015`, a reversible prompt-only memory-forcing experiment that
  requires every Scarlet turn to include an execution phase plus mandatory
  verification phase before final answer, and makes recognized semantic memory
  candidates action-binding through `POST /mind/memory/write`.
- Recorded the first `EXP-0015` rerun failure: Scarlet again recognized a
  chocolate preference/health constraint as useful personal memory but did not
  call `memory.write`, exposing a remaining project/agent-behavior memory bias
  in prompt/schema examples.
- Updated `EXP-0015` with a personal semantic memory taxonomy so Scarlet treats
  user personal facts, names, relationships, food/health constraints, life
  events, discoveries, errors, solutions, and workarounds as first-class
  semantic memory candidates.
- Confirmed the `EXP-0015` prompt solution in live use: Scarlet wrote the
  chocolate limit as a `user_preference` memory, then automatically retrieved it
  in a later session through `memory.context`.
- Added provider-native session history for MiniMax/Anthropic-compatible
  multi-turn continuity: chat sessions now persist `provider_history_json`,
  future turns send native content blocks instead of text-only reconstruction,
  and `llm.request` traces expose provider-history source and size stats.
- Recorded live `EXP-0016` probes confirming provider-native history preserves
  both `GET /mind/schema` and `POST /mind/memory/write` tool-use/tool-result
  sequences across turns.

### Fixed

- Initialized project tracking plan for the previously uninitialized Git repository state.
- Resolved the GitHub push blocker for the initial repository setup.
- Fixed detached SQLModel ORM object usage in the chat turn endpoint.
- Fixed chat provider initialization errors so missing MiniMax configuration returns structured `503 llm.not_configured`.
- Fixed the generic diagnostic-assistant fallback that could make the agent misidentify itself.
- Fixed detached SQLModel ORM usage in the new Mind API call endpoint by keeping scalar values across session boundaries.
- Fixed inline streaming timeline attachment by including `turn_id` on every NDJSON event.
- Fixed overly brittle Memory v0 validation discovered during live MiniMax runs by normalizing common semantic aliases and preserving harmless extra model fields in memory metadata.
- Fixed Python 3.10 compatibility in the evaluation runner by replacing `datetime.UTC` with `timezone.utc`.
- Fixed MiniMax-shaped `mind_api` wrapper handling by accepting `raw_input`, JSON-string `body` values, body-level `intent`, and Italian memory aliases observed in direct chat traces.
- Fixed Memory Lifecycle M2 response serialization so lifecycle handlers do not return detached SQLModel records after session close.
- Fixed the observed lifecycle alias gap by accepting `target_id` plus `superseded_by` for memory supersession.
- Fixed fact backfill after existing lifecycle operations so fact-level supersession links are rebuilt from memory lifecycle metadata.
- Fixed the trace-only time gap where turn time existed in `memory.context` but
  was not exposed inside the model-facing `<runtime_context>`.
- Removed the obsolete prompt-level `Visible Metacognition Experiment` block so
  public work notes and `/mind/metacognition/step` no longer compete as two
  different visible-metacognition concepts.
- Fixed lossy cross-turn provider history where tool-use/tool-result blocks
  were stored in traces but not rehydrated into the next MiniMax request.

## Release Notes Policy

Each release section should answer:

- What changed?
- Why did it change?
- Which roadmap phase, experiment, or decision does it support?
- How was it verified?

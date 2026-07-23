# Bug Ledger

This file records bugs, fixes, root causes, and regression tests so the project does not rediscover the same problems across sessions.

Identifier note: V1.29.1 normalized legacy duplicate headings. Historical
activity/experiment text may retain the identifier used at the time; current
canonical bug ids are the headings in this file. Bug evidence and resolution
history were not rewritten.

## BUG-0108 - Generated Agentic Module Could Not Launch On Windows

Date Found: 2026-07-23
Status: fixed in V1.55.0

Symptoms:

Three existing SDK/real-host conformance tests failed with `WinError 193`
after the full development environment was installed on Windows.

Root Cause:

The generated `run-module` launcher is a valid executable shebang script on
POSIX. Windows `CreateProcess` does not interpret that shebang and attempted to
execute the text file as a native Win32 binary.

Fix:

Resolve Python-suffix or Python-shebang entrypoints through
`sys.executable` in the shared SDK resolver, and make the Core host reuse the
same resolver before its Linux resource wrapper.

Regression Coverage:

The generated scaffold now passes standalone conformance, real Core Host
conformance, and CLI conformance unchanged on Windows.

Related Files:

- `backend/scarlet_agentic_module_sdk/client.py`
- `backend/scarlet_agentic_module_sdk/conformance.py`
- `backend/app/agentic_modules/transport.py`
- `backend/tests/test_agentic_module_sdk.py`

## BUG-0107 - Dashboard Timezones Failed On Windows Without Tzdata

Date Found: 2026-07-23
Status: fixed in V1.55.0

Symptoms:

With the declared backend dependencies installed on Windows, `/health`,
sessions, and memories returned 200, while `/api/dashboard/profile` and
`/api/dashboard/settings` returned 500.

Root Cause:

`RuntimePreferences` validates `Europe/Rome` through Python `zoneinfo`.
Windows does not ship the IANA timezone database used by `zoneinfo`, and the
backend package did not declare the first-party `tzdata` fallback.

Fix:

Declare `tzdata>=2025.2` for Windows in `backend/pyproject.toml`.

Regression Coverage:

Direct isolated `CODEX_TEST` HTTP calls to profile/settings returned 200 after
installing the declared package, and the browser saved runtime settings through
the real endpoint.

Related Files:

- `backend/pyproject.toml`
- `backend/app/runtime/preferences.py`
- `backend/app/api/dashboard.py`

## BUG-0106 - Artificial Splash Stages Delayed A Ready Application

Date Found: 2026-07-23
Status: fixed

Symptoms:

The splash always consumed its staged timer sequence even when the application
portrait, fonts, and greeting media were already ready. The 5.163-second
greeting then made the first entry feel substantially longer than necessary.

Root Cause:

Readiness was represented by fixed progress intervals rather than the assets
that gate first paint and greeting playback. The greeting source also played at
its authored duration even though only a short transition beat is needed.

Fix:

- join portrait decode, font readiness, two animation frames, and media
  readiness instead of waiting through staged progress timers;
- preload the greeting from splash start and begin it immediately when both
  application and media are ready;
- retain a six-second media fallback only for an unavailable greeting after
  the application itself is ready;
- play the source at natural `1x` speed and stop at `52%`, preserving the
  authored greeting cadence while removing the unnecessary second half; and
- navigate from either that bounded cut or the real media `ended` event with a
  160ms leaving transition.

Regression Coverage:

Real Chrome at `390x844` measured greeting start after `1018ms`, natural-speed
half greeting plus leaving transition at `2865ms`, and Login at `3883ms` total.
The video reported duration `5.162993s`, playback rate `1`, and active playback.

Related Files:

- `frontend/src/prototype/AppEntryFlow.tsx`
- `frontend/src/prototype/ScarletMascot.tsx`
- `frontend/src/prototype/SplashScreen.tsx`

## BUG-0105 - Product Prototype Inherited The Cockpit's Locked Document Scroll

Date Found: 2026-07-23
Status: fixed

Symptoms:

The post-login Home was taller than a mobile viewport, but the browser window
did not provide reliable page-level scrolling. Subsequent full pages would
inherit the same behavior.

Root Cause:

The global Tailwind base in `frontend/src/styles.css` deliberately locks
`body` with `overflow: hidden` for the three-pane cockpit. The first scoped
prototype override correctly restored vertical overflow but also assigned
`height: auto` and `min-height: 100%` to the root document elements. Those
height declarations interfered with reliable page scrolling across the
post-login screens.

Fix:

- apply a `scarlet-prototype-document` class to `html` and `body` while the
  `/prototype` React surface is mounted;
- set only horizontal/vertical overflow on `html` and `body`, without assigning
  either `height` or `min-height`;
- keep `#root` overflow visible without assigning document-level height or
  minimum height;
- remove the classes on unmount so the real cockpit/mobile overflow contracts
  remain unchanged; and
- reset window, document-element, and body scroll positions on post-login view
  changes.

Correction, 2026-07-23:

The owner reproduced the remaining failure in browser DevTools and identified
the prototype-level `height: auto` / `min-height: 100%` pair as the active
blocker. Removing both declarations from all prototype document-root selectors
is the accepted fix.

Recurrence and final correction, V1.55.0:

The global cockpit rule `html, body, #root { height: 100% }` remained active
when the route-scoped declarations were omitted. Real Chrome measured the
mobile Home document at exactly `844px`, clipping content below the viewport.
The final scoped contract explicitly overrides inherited height with
`height: auto` and `min-height: 100%` on the prototype document and root.
Chrome then measured `2049px` of document height, reached `scrollY=1205`, kept
document width equal to the `390px` viewport, and retained the intentional
`844px` Chat viewport.

Regression Coverage:

Browser verification covers Home, Chat, Memory, Sessions, and Profile with the
final scoped document override. The body becomes the effective page scroll
container, retains exact horizontal document/client width, reaches its measured
maximum scroll, and returns to the top after view navigation.

Related Files:

- `frontend/src/prototype/PrototypeApp.tsx`
- `frontend/src/prototype/prototype.css`
- `frontend/src/prototype/HomeDashboard.tsx`
- `frontend/src/prototype/home.css`

## BUG-0104 - Splash Greeting Played Invisibly During Startup

Date Found: 2026-07-23
Status: fixed

Symptoms:

The startup greeting appeared not to play. Media diagnostics showed that the
video was actually advancing behind the canonical portrait while its CSS
opacity remained zero, and the automatic splash timer navigated to Login
before the 5.163-second greeting could finish.

Root Cause:

Visibility depended exclusively on a React `onCanPlay` state update. On fast
local media delivery the native readiness event could occur before that update
was observed, leaving the `is-ready` class absent. More fundamentally, the
video used autoplay during loading even though the intended experience was to
show it only after startup completed.

Fix:

- preload the video while keeping it paused at zero and transparent;
- verify readiness both from the element's current `readyState` and subsequent
  media events;
- start visible playback only when application and media readiness converge;
- remove looping and route to Login from the full greeting's `ended` event;
- retain explicit fallback behavior for reduced motion, media failure, or
  readiness timeout.

Regression Coverage:

Real Edge mobile emulation proves the video ready/paused/hidden at `12%`,
playing/visible at `100%`, and Login absent until after the full media ends.
No runtime exception or horizontal overflow was observed.

Related Files:

- `frontend/src/prototype/AppEntryFlow.tsx`
- `frontend/src/prototype/SplashScreen.tsx`
- `frontend/src/prototype/ScarletMascot.tsx`
- `frontend/src/prototype/splash.css`

## BUG-0103 - Animated Button Fill Covered Its Text

Date Found: 2026-07-23
Status: fixed

Symptoms:

Primary authentication button labels became unreadable when the colored hover
fill expanded across the full button.

Root Cause:

The fill was an absolutely positioned pseudo-element. Only the arrow icon was
an element with an explicit stacking position; the adjacent button label was a
direct text node and therefore had no independent layer above the fill.

Fix:

Wrap every primary-button label in an element, place all label/icon children
above the fill, and explicitly preserve white foreground color during hover.

Regression Coverage:

A real Edge hover at mobile emulation width expanded the pseudo-element to the
full `309px` button width while computed foreground color remained
`rgb(255, 255, 255)` for both child elements.

Related Files:

- `frontend/src/prototype/AuthScreen.tsx`
- `frontend/src/prototype/AppEntryFlow.tsx`
- `frontend/src/prototype/splash.css`

## BUG-0102 - Generated Anatomy Was Treated As Automatically Registerable

Date Found: 2026-07-21
Status: fixed at workflow level; owner placement pending

Symptoms:

Automatic attempts to size and position generated anatomy against the portrait
were slow, inconsistent, and less precise than direct owner adjustment in
Photoshop. Placement work also distracted from generating the complete asset
inventory.

Root Cause:

Image-generated assets have their own crop, scale, silhouette, and local
coordinate system. Matching dimensions or a guessed bounding box cannot prove
that their anatomical pixels coincide with a different rendered portrait.

Fix:

- Trim only to the actual alpha silhouette and preserve native dimensions.
- Stage each asset hidden and centered only as an unmistakably unregistered
  workspace layer.
- Name every staged layer `UNREGISTERED__...__OWNER_TRANSFORM_REQUIRED`.
- Keep the portrait locked at the bottom of the PSD.
- Give final x/y and scale control to the owner in Photoshop.

Regression Coverage:

`npm run avatar:rig-workspace` rebuilds native crops and the PSD, reopens it,
and verifies the complete hierarchy and locked bottom reference. No builder
code computes an anatomical target box or claims approved placement.

Related Files:

- `frontend/scripts/prepare-scarlet-anatomical-part.mjs`
- `frontend/scripts/build-scarlet-rig-psd.mjs`
- `frontend/public/prototype/avatar/scarlet-rig-workspace.json`
- `frontend/public/prototype/avatar/rig/scarlet-layered-rig-workspace-v2.psd`

## BUG-0101 - Review PSD Reference Layer Was Serialized Above Anatomy

Date Found: 2026-07-21
Status: fixed

Symptoms:

The locked portrait reference visually covered generated anatomical layers in
Photoshop, preventing placement review even though the intended z-order named
the candidate as foreground.

Root Cause:

The avatar-specific writer treated the `ag-psd` `children` array as
top-to-bottom. In the emitted PSD it is consumed bottom-to-top, so appending the
reference made it the highest visible layer.

Fix:

- Replace organ-specific PSD writers with the generic anatomical preparer.
- Emit the locked reference first, optional approved lower surfaces next, and
  the current candidate last.
- Reopen every PSD immediately after writing and assert both the full ordered
  name list and the `REFERENCE__` prefix in the first/bottom position.

Regression Coverage:

The right-upper-lash preparation command writes and parses the two-layer PSD;
generation fails on any bottom-to-top order mismatch.

Related Files:

- `frontend/scripts/prepare-scarlet-anatomical-part.mjs`
- `frontend/public/prototype/avatar/work/eye_scarlet_right_upper_lash_liner/v1/eye_scarlet_right_upper_lash_liner-v1-review.psd`

## BUG-0100 - Rejected Avatar Pipelines Remained Active Beside Canonical Sources

Date Found: 2026-07-21
Status: fixed

Symptoms:

The avatar workspace exposed hundreds of generated images, several rejected
PSDs, APNG frames, overlapping contracts, and executable npm commands from V1,
V2, and V3 experiments. A future authoring step could consume or regenerate a
rejected asset without an obvious boundary violation.

Root Cause:

Each experiment retained its output for comparison, but the repository had no
single active-artifact whitelist. Historical evidence and production inputs
therefore occupied the same filesystem surface.

Fix:

- Remove all derived visual artifacts and obsolete generators.
- Retain only the portrait and T-pose as visual sources.
- Lock their paths, dimensions, hashes, and roles in one authoring contract.
- Make all future anatomical surfaces pass an owner-reviewed one-organ gate
  before they can enter a PSD.

Regression Coverage:

The reference-only inventory, hash checks, JSON parsing, and frontend build
form the reset verification. Future avatar validation must fail if an
unregistered raster or PSD appears in the canonical authoring workspace.

Related Files:

- `frontend/public/prototype/avatar/scarlet-psd-authoring-contract.json`
- `docs/scarlet-live2d-puppet.md`

## BUG-0099 - Historical Face Partition Was Mistaken For Scarlet's Rig Contour

Date Found: 2026-07-21
Status: historical; generated candidate removed by BUG-0100

Symptoms:

The first Puppet V3 face base had valid dimensions and exact alpha agreement
with its mask, but its isolated silhouette read as a generic broad oval rather
than Scarlet's narrower heart-shaped face. Numeric mask agreement concealed
that the mask itself was wrong.

Root Cause:

The generator inherited the `face_base` path from the old visible-pixel
partition. That path was designed to assign source pixels without overlap; it
was never approved as anatomical rig geometry.

Fix:

- Reject the historical partition path as face geometry.
- Trace a new V3 contour from the locked half-body portrait using forehead,
  temple, cheek, jaw, and chin landmarks on the native pixel grid.
- Store the path and landmarks in the V3 contract rather than in generator
  code or historical evidence.
- Add old/new contour, coordinate-grid, isolated silhouette, alpha-match, and
  direct overlay proofs.
- Make validation fail when report path or bounds drift from the V3 contract.

Residual Work:

The corrected face is awaiting direct owner review. No further V3 organ or PSD
may be produced until this gate is accepted.

Related Files:

- `frontend/public/prototype/avatar/scarlet-puppet-v3-contract.json`
- `frontend/scripts/inspect-scarlet-face-contour-v3.mjs`
- `frontend/scripts/prepare-scarlet-face-base-v3.mjs`
- `frontend/scripts/validate-scarlet-avatar.mjs`

## BUG-0098 - Puppet V2 Layer Count Masked Legacy Artistic Dependencies

Date Found: 2026-07-21
Status: historical; all generated puppet artifacts removed by BUG-0100

Symptoms:

Puppet V2 passed structural validation with 59 materials and 103 PSD layers,
but `face_base` consisted of a perforated portrait cutout plus a hidden generic
face. Torso, limbs, hair, eye supports, expressions, and hand variants had the
same dependency on the superseded generated material pack.

Root Cause:

The generator read `source/generated/materials/materials-index.json`, resized
those assets around visible cutout bounds, and treated the pair as a completed
material. The validator checked dimensions, names, groups, files, and PSD
parsing but did not verify that each rig layer was one newly reconstructed,
reference-anchored semantic surface.

Fix:

- Mark Puppet V2 and its PSD as rejected evidence.
- Add a Puppet V3 contract that forbids all legacy artistic inputs.
- Make PSD admission fail closed until progressive material gates pass.
- Build the face base from the approved portrait geometry and clean skin
  pixels, limiting generated pixels to removed or occluded areas.
- Extend avatar validation to enforce the V2 rejection and V3 face-gate state.

Residual Work:

The face candidate requires owner review. Eyes other than the approved iris,
brows, nose, mouth, ears, neck, hair, body, limbs, hands, and the V3 PSD remain
unimplemented.

Related Files:

- `frontend/public/prototype/avatar/scarlet-puppet-v3-contract.json`
- `frontend/scripts/prepare-scarlet-face-base-v3.mjs`
- `frontend/scripts/validate-scarlet-avatar.mjs`
- `docs/scarlet-live2d-puppet.md`

## BUG-0097 - Hidden Support Corrupted Neutral Puppet Assembly

Date Found: 2026-07-20
Status: superseded diagnosis; Puppet V2 rejected by BUG-0098

Symptoms:

Early full-puppet composites showed oversized synthetic eye and body support,
misregistered legacy-board content, and a visibly different face despite the
individual visible-master extractions being correct. A broad attempt to remove
light fringe by RGB threshold also punched holes into the pearl-white suit.

Root Cause:

Legacy support boards had different local scales and coordinate systems from
the registered portrait/T-pose canvas. More importantly, reconstructed support
was being displayed as neutral artwork instead of remaining hidden under the
authoritative visible surface. Color alone could not distinguish white fringe
from legitimate light materials.

Fix:

- Register support to each material's authoritative visible bounds.
- Separate `visible-master`, `hidden-support`, and `complete` outputs.
- Disable hidden support in the neutral composite and generated PSD by default.
- Add exact neutral master-eye composites while retaining the separated eye
  stack for later clipping and deformation.
- Remove broad RGB cleanup and preserve source texture unless a boundary is
  explicitly reviewed.
- Add a neutral reference, reconstruction, difference map, depth map, contact
  sheet, per-part proofs, and structural PSD validation.

Regression Coverage:

The original structural checks remain historical evidence only. BUG-0098
records why they were insufficient and why the resulting PSD is rejected.

Residual Work:

Small source/matte artifacts remain around selected T-pose hair and shoulder
edges. They require local edge masks plus Cubism movement-extrema checks; they
must not be addressed with global color thresholds.

Related Files:

- `frontend/public/prototype/avatar/scarlet-puppet-v2-contract.json`
- `frontend/scripts/prepare-scarlet-puppet-v2.mjs`
- `frontend/scripts/validate-scarlet-avatar.mjs`
- `docs/scarlet-live2d-puppet.md`

## BUG-0096 - Neutral Pixel Partition Mixed Multiple Live2D Semantic Surfaces

Date Found: 2026-07-20
Status: V1 rejected; semantic replacement assembled in Puppet V2

Symptoms:

The right-eye iris proof visibly carried lower-eyelid and eye-white pixels. If
used directly in Cubism, gaze motion would move those foreign pixels with the
iris. Sclera and lash exports were correspondingly incomplete. Other geometric
patches could reproduce the neutral reference while still mixing face skin
with nose/mouth features or combining front/rear depth roles.

Root Cause:

The first generator intentionally performed a priority-ordered geometric pixel
partition. It proved exact source provenance and prevented duplicate pixel
assignment, but the resulting labels were described too closely to final
materials. Zero reconstruction mismatch measures neutral coverage, not semantic
ownership or deformation safety.

Fix:

- Mark the 34 exports as partition evidence only.
- Add `scarlet-occlusion-contract.json` with an audit of all 34 candidates,
  draw-order bands, clipping, hidden completion, support materials, and motion
  proofs.
- Validate that every visible candidate appears in the audit exactly once.
- Defer all hidden artwork and PSD assembly to isolated owner-review gates.

Residual Work:

The 26-asset V1 eye gate remains rejected diagnostic evidence. The replacement
right iris V2 is owner-approved as the common source for both irises, and the
Puppet V2 pipeline now separates visible-master, hidden-support, complete, and
variant roles across the eye, face, hair, and body set. The PSD is assembled,
but the semantic materials still require Cubism clipping, deformation, extreme
pose review, and local matte cleanup before motion safety is proven.

Related Files:

- `frontend/public/prototype/avatar/scarlet-occlusion-contract.json`
- `frontend/public/prototype/avatar/scarlet-eye-assets-contract.json`
- `frontend/public/prototype/avatar/scarlet-right-iris-v2-contract.json`
- `frontend/scripts/prepare-scarlet-semantic-eyes.mjs`
- `frontend/scripts/prepare-scarlet-right-iris-v2.mjs`
- `frontend/public/prototype/avatar/scarlet-puppet-v2-contract.json`
- `frontend/scripts/prepare-scarlet-puppet-v2.mjs`
- `frontend/public/prototype/avatar/scarlet-visible-parts-matrix.json`
- `frontend/scripts/validate-scarlet-avatar.mjs`
- `docs/scarlet-live2d-puppet.md`

## BUG-0095 - Live2D Authoring Validation Followed Superseded PSD State

Date Found: 2026-07-20
Status: historical; pipeline removed by BUG-0100

Symptoms:

The active visible-pixel generator briefly emitted empty non-hair layers after
component filtering was introduced. The general avatar validator also failed
on a stale `reference` group inside the earlier generated import PSD even
though that material pack had been superseded by the master-pixel pipeline.

Root Cause:

The unfiltered retained mask aliased the working mask and was cleared before
extraction. Separately, the validator discovered and validated every legacy
PSD merely because it existed, rather than following the active pipeline
status in the authoring manifest.

Fix:

Clone unfiltered retained masks before clearing the workspace. Validate the
active fidelity matrix, all generated layer/mask/piece/proof files, and the
zero-mismatch report by default. Keep the old generated PSD inspection behind
`--validate-legacy-material-pack`; keep approved-PSD requirements fail-closed
until the new fidelity PSD exists.

Regression Coverage:

- `npm run avatar:fidelity:parts` exports 34 non-empty materials;
- portrait and body selected reconstructions report zero RGBA mismatches;
- `npm run avatar:validate` passes against the active fidelity pipeline; and
- `npm run build` passes after the validator change.

## BUG-0094 - Repeated Native Final-Marker Omission Discards Conclusive Answers

Date Found: 2026-07-18
Status: fixed, deployed, and directly verified in V1.50.1

Symptoms:

Two focused production turns returned HTTP 502
`llm.incomplete_response`. MiniMax produced non-empty, conclusive corrected
answers after the runtime's one recovery request, but omitted the private
`<scarlet-final/>` marker on both attempts. No assistant message was persisted.

Root Cause:

The final boundary relied exclusively on stochastic marker compliance. This
correctly rejected progress notes, but it also treated a complete corrected
provider result as structurally incomplete even when its natural-language
content was independently judgeable as conclusive. The risk had been recorded
in V1.41.0 but was not previously reproduced twice in focused release smoke.

Fix:

V1.50.1 preserves the marker as the primary boundary and preserves one bounded
correction. If only the corrected second draft omits the marker, the runtime
adds a hard semantic finality obligation and asks the existing LLM judge
whether the draft is complete, standalone, conclusive, and independent of
rejected public text. Acceptance persists the original text unchanged. A
progress note, fragment, unavailable judge, or failed semantic obligation still
fails closed.

Regression Coverage:

- marker path remains accepted and stripped;
- complete corrected markerless draft is semantically accepted;
- second progress-only draft remains HTTP 502;
- judge failure and truly empty provider output remain fail-closed boundaries;
- no private marker is persisted or exposed publicly.

Production Verification:

The protected V1.50.1 runtime at merge `676e560` completed native turn
`turn_a8a990e5ce7a4fbd9dd15cd99437836d` with HTTP 200 and persisted one
conclusive assistant message. That provider response used the primary marked
path on its first attempt, proving the ordinary boundary still works after the
fix. Deterministic positive and negative providers remain the evidence for the
rare second-miss semantic fallback. Post-smoke SQLite integrity was `ok` and
the container log contained no runtime error.

Related:

- Linear SCA-44
- ADR-0106
- EXP-0079
- `docs/evaluations/v1.50.1-native-finality-recovery.md`

## BUG-0093 - Frozen Automatic-Memory Gate Does Not Verify Model-Facing Delivery

Date Found: 2026-07-18
Status: fixed and regression-tested in V1.50.0

Symptoms:

The frozen `automatic_memory_retrieval` case passes when rich
`memory.context.selected` contains the active Zero-Luce memory. A real MiniMax
turn on the same untouched fixture nevertheless received an empty V2 memory
packet and answered that no relevant memory was available.

Root Cause:

The frozen memory `mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3` has source session
and turn ids but no `source_message_id`. The V2 projector intentionally accepts
only complete, resolvable source hooks, so selection and model delivery
diverge. The gate asserts the former only.

Evidence:

The source turn contains exactly one user message,
`msg_a3adf09c456246be92f91c774c9c25d0`, and the provenance maintainer classifies
the link as `repairable_single_user_message`. On a disposable copy, exact
repair made the memory source-complete; the repeated natural prompt then
delivered the hook and Scarlet returned the correct four-block protocol.

Required Fix:

Add a new versioned or complementary gate with complete provenance that asserts
the V2/model-request hook and inspects the resulting answer. Do not mutate the
historical frozen V1 source or weaken the provenance gate.

Fix:

V1.50.0 adds `model-facing-memory-gate-v2`. It proves the pre-repair
selection/projection split, applies exact digest-guarded repair only on a
disposable copy, and then asserts the target in V2, `llm.request`, and the
provider-observed system. Successful acceptance additionally requires a
completed turn, one assistant message, no `llm.error`, and `turn_complete`.
An intentionally incomplete provider proves the gate rejects the old false-
positive shape. The integrated gate passes 5/5 and its own oracle contracts
pass 6/6.

Related:

- Linear SCA-43
- Linear SCA-35
- ADR-0100
- ADR-0105
- `docs/evaluations/v1.50-model-facing-memory-gate.md`

## BUG-0092 - Stream Omitted Model-Context Trace Linkage

Date Found: 2026-07-18
Status: fixed and regression-tested in V1.45.0

Symptoms:

Native sync and stream turns both generated a `model.context` trace. Sync
included its profile/id in `llm.request` and returned the id in final
`trace_ids`; stream omitted all three references even though the trace existed.

Root Cause:

The two routes independently assembled the same preflight invariants. The
stream copy did not carry newer model-context observability fields added to the
sync path.

Fix:

Both transports now use `prepare_native_turn`, which links the projection
profile and trace exactly once. The stream regression checks the request link
and final turn reference against the actual stored trace.

Direct Evidence:

The post-change stream turn `turn_17b7c06281ad4aa9852047bd3d9e0e76`
references `trace_930ef7997e104a798ecc2c5dab2b8efc` consistently in stored
request and completed turn evidence.

Related:

- Linear SCA-33
- ADR-0099

## BUG-0091 - Successful Action Retry Is Missing From Answer Obligations

Date Found: 2026-07-18
Status: fixed and regression-tested in V1.49.1

Symptoms:

In an isolated native MiniMax turn, a malformed `memory write` failed and a
materially corrected retry then stored the memory successfully. Final-answer
validation nevertheless retained only the first failed action as evidence and
rejected two truthful drafts describing the successful retry, including one
that named the stored memory ID.

Evidence:

- session `ses_472db64bc051471999f95b9b43657e9d`;
- turn `turn_26109ad9b5da4f819e5e3fe0db464468`;
- failed trace `trace_0bac38fab3b74edcaa628a3423f0abb6`;
- successful retry trace `trace_463d5096898d49c8a44ae9243b2aef5c`;
- false-negative validation trace
  `trace_c2a3ca2b50894bc0ae7760f3f496e434`.

Classification:

The initial over-eager memory choice and malformed alias were model behavior.
The failure to reconcile a successful equivalent retry into the answer
obligation evidence is a deterministic shared-runtime defect. It predates and
is outside the SCA-34 support extraction.

Fix:

The shared obligation compiler now rebuilds tool-derived obligations from all
authoritative current-turn calls. It preserves the failed attempt and links
later recoverable same-operation attempts as semantic candidates. The answer
validator, not a deterministic comparator, decides whether command, intent,
and result materially recovered the same action. GPT action manifests are also
rebuilt so persisted failure evidence cannot hide a later success.

Direct Evidence:

In session `ses_3d412c64a0ec4e29884a82b778f49b91`, MiniMax M3 retried an
injected malformed `memory write`, stored
`mem_4023cf8a8684439f81b7a20969235246` with complete provenance, and produced
a natural final answer. The V2 obligation retained both action traces and the
semantic validator explicitly accepted the recovered chain. Native sync,
stream, and GPT lifecycle regressions cover the same rule.

Related:

- Linear SCA-42
- Linear SCA-28
- Linear SCA-34
- ADR-0104

## BUG-0090 - Query-String Bridge Key Was Recorded In Proxy Logs

Date Found: 2026-07-18
Status: transport fixed in V1.43.0; credential rotation pending coordination

Symptoms:

The deprecated MCP private-preview flow accepted
`/mcp?key=<GPT_BRIDGE_API_KEY>`. Production access-log inspection showed MCP
requests with the query string present, so the bridge secret crossed a URL/log
boundary even though it was not committed to the repository.

Root Cause:

The connector experiment could not configure the Custom GPT Action header and
added query-key authentication as a temporary preview convenience. The same
fallback was also accepted, though hidden from OpenAPI, by the three GPT
routes.

Fix:

V1.43 removes `/mcp`, removes every query-key parameter and auth fallback, and
tests that a production bootstrap with only `?key=` is rejected. Header-based
Actions authentication remains active.

Residual Action:

Rotate `GPT_BRIDGE_API_KEY` only in a coordinated maintenance step that also
updates the external GPT Action secret. Never record the old or new value in
project documentation, issues, command output, or commits.

Related:

- Linear SCA-22
- ADR-0096
- `backend/tests/test_gpt_bridge.py`

## BUG-0089 - Final Reranker Can Admit Unsupported Personal Hooks Near Floor

Date Found: 2026-07-18
Status: confirmed, monitored, and deferred by owner decision

Symptoms:

A production tea/mint-preference query admitted an unrelated Context Router
memory at `0.004102` against the `0.004` floor. In the frozen expanded suite,
an unsupported favourite-colour question reproducibly admitted unrelated user
and project memories, with a highest score of `0.006339`.

Classification:

This is a real model-facing retrieval precision defect, not ordinary answer
variance: the reranker crossed its configured acceptance boundary. It is not
currently a stability blocker because selected memories remain evidence hooks
that the answer model can reject, and no answer-level false claim has been
demonstrated by this issue.

Decision And Evidence:

No threshold or runtime policy changed. The observed negative ceiling is too
close to the required-positive floor (`0.007432`) for a robust numeric fix, and
removing document metadata lost a required positive without clearing the
negative. Five personal negatives remain in the replicable calibration suite.
Revisit with broader provider drift data or demonstrated answer-level harm.

Related:

- Linear SCA-31
- `docs/evaluations/v1.43-memory-rerank-negative-calibration.md`

## BUG-0088 - Mode Routing Receipt Confused Eligibility With Delivery

Date Found: 2026-07-18
Status: fixed, directly verified, and deployed in V1.42.0

Symptoms:

For an `idle` route, `off` and `shadow` returned message and affect blocks but
omitted those types from `included_block_types` and listed them only as
ineligible. Active routing was coherent, but non-active receipts made trace
consumers unable to distinguish policy mismatch from actual model delivery.
Receipts also exposed only block types, so duplicate instances and individual
reasons were not inspectable.

Root Cause:

`mode_routing_decision` calculated eligibility aggregates before
`route_context_blocks` separately decided whether the policy was active. The
decision had no representation of actual per-block delivery.

Fix:

V1.42 creates one ordered routing decision per input block and derives both
delivery and aggregate receipts from that same decision list. `off`, `shadow`,
and `active` now have explicit dispositions; unregistered blocks are fail-open
and visible. The same slice enforces resumable-mode ownership in the primitive
store so internal callers cannot persist `interactive`.

Regression Evidence:

- routing matrix across all three policies;
- complete registered context inventory across every agent mode;
- duplicate and unregistered block controls;
- native/GPT interactive receipt checks;
- V2 projection cannot restore an actively excluded organ block;
- manual memory retrieval remains available with a scouting resume posture.

A bounded real MiniMax chain also persisted scouting in one session, recovered
it in another, and produced per-block interactive receipts. No autonomous
scouting runtime was claimed or exercised.

Related:

- Linear SCA-6
- `docs/evaluations/v1.42-agent-mode-routing.md`

## BUG-0087 - Observed Accounting Always Labelled Compaction As Shadow

Date Found: 2026-07-18
Status: fixed in V1.39.0

Symptoms:

`context.accounting.observed` emitted
`compaction_plan_was_shadow_only=true` unconditionally, including requests
routed through active history compaction. Model input and canonical persistence
were correct, but the post-call evidence misrepresented the operative mode.

Root Cause:

The V1.36 observation field was a fixed shadow-era constant and was not bound
to the preflight plan when active routing was introduced.

Fix And Regression Evidence:

The observed trace now copies `compaction_plan_mode` and derives the legacy
boolean from the exact preflight plan. Dedicated shadow and active assertions
pass together with the context-accounting, history, and chat tests.

Related Files:

- `backend/app/runtime/context_accounting.py`
- `backend/tests/test_context_accounting.py`
- Linear SCA-32

## BUG-0086 - Active Compaction Could Trust Altered Source IDs And Retrigger From Canonical Size

Date Found: 2026-07-18
Status: fixed in V1.39.0

Symptoms:

The first real MiniMax chronology artifact preserved the session meaning but
altered one turn ID and shortened several memory/session IDs in summary prose.
The initial scheduler also compared the trigger with full canonical history,
which never shrinks and could therefore enqueue maintenance after every later
turn even when the derived view was small.

Root Cause:

Opaque source identity was delegated to generated prose, and scheduling used
the immutable source inventory as though it were the next model-facing input.

Fix:

The backend now removes opaque IDs absent from source input, injects an exact
deterministic source manifest, and validates artifacts by turn/digest identity
rather than mutable token estimates. Post-turn scheduling measures the active
derived tail when an artifact is in use while retaining canonical history only
as the recursive source snapshot.

Regression Evidence:

- changed token-estimation ratios no longer invalidate an unchanged source;
- invalid source digests fall back to canonical history;
- generation 2 contained zero unresolved unverified IDs;
- 352,887 canonical tokens with a 2,701-token active tail did not schedule a
  redundant job under a 300,000-token disposable trigger; and
- sync/stream tests preserve the canonical provider-history prefix.

Related Files:

- `backend/app/runtime/history_runtime.py`
- `backend/app/runtime/maintenance.py`
- `docs/evaluations/v1.39-active-history-compaction.md`
- Linear SCA-32

## BUG-0083 - Codex Evaluation Fixtures Entered Production Active Memory

Date Found: 2026-07-18
Status: fixed, deployed, and verified in V1.38.0

Symptoms:

The production database contained 242 memories sourced from three Codex seed
sessions. The original provenance audit reported them only as missing a turn,
so active test records could participate in memory retrieval and appeared
indistinguishable from uncertain historical data at the audit-summary level.

Root Cause:

An earlier evaluation dataset was written into the persistent production
database before strict database roles and disposable evaluator boundaries were
established. The maintenance API also combined read and write behavior and did
not classify record disposition separately from source completeness.

Fix:

V1.38.0 introduces a read-only orthogonal audit and recognizes a test fixture
only when its complete metadata, tag, and source-session-title contract agree.
A dedicated guarded operation deprecates active fixtures, facts, and derived
retrieval artifacts after dry-run, candidate-digest review, and verified
backup. It records non-recent lifecycle activity and never deletes history.

Regression Test:

- partial markers or content mentioning Codex tests cannot classify a fixture;
- exact duplicate content remains review-only;
- missing approval and candidate drift fail closed;
- apply propagates inactive lifecycle to facts/surfaces without touching the
  source session or recent-memory eligibility; and
- production-copy and direct Scarlet checks must pass before closure.

Related Files:

- `backend/app/runtime/memory_provenance.py`
- `backend/tests/test_maintenance_api.py`
- `docs/evaluations/v1.38-historical-provenance-audit.md`
- Linear SCA-20

## BUG-0085 - Completed Native Turn Contained Only A Public Work Note

Date Found: 2026-07-18
Status: fixed and deployed in V1.41.0

Symptoms:

A direct production Scarlet turn ended with provider `end_turn`, no tool call,
and only a truncated public progress note. The backend marked the turn
completed because non-empty public text existed, although no conclusive answer
was present.

Current Assessment:

This is a systemic answer-obligation gap, not ordinary answer-quality variance
and not a thinking-only SCA-19 case. The runtime needs a traced, proportionate
distinction between progress narration and a final semantic answer without
using brittle string matching for normal content.

Evidence:

- session `ses_02f95bf1a9874b0cb3fa5cd613377897`;
- turn `turn_fc2045c3b17542b6812c1df8f1994279`;
- SCA-4 repetition `volition-continuity-model-r1-BEH-0111` ended after a
  public memory-check note even though provider thinking had selected
  `volition create`; the correlated next session correctly found no persisted
  intention;
- Linear SCA-28.

Fix And Regression Evidence:

The native runtime now requires a private structural final boundary, strips it
before persistence and public delivery, and permits one continuation when the
provider ends on progress-only text. A second miss fails explicitly. Sync and
stream tests prove that rejected drafts are not canonical messages and that
streaming exposes only the accepted final answer while retaining legitimate
work notes and tool events.

## BUG-0084 - VPS Retrieval Configuration Drift Disabled Dense Embedding

Date Found: 2026-07-18
Status: fixed operationally during V1.38.0 deployment

Symptoms:

Production configured the OpenRouter shadow backend but omitted its embedding
model, causing the local-hash default model name to be sent to OpenRouter and
return HTTP 400. The VPS also retained the pre-V1.37 rerank threshold.

Fix And Verification:

The production environment now explicitly selects the Nvidia embedding and
rerank models and the V1.37 absolute/relative floors. After restart, a GPT
bridge negative control reported both embedding and final rerank `completed`,
returned zero memories, and finalized successfully.

Regression Target:

Future deployments should compare effective non-secret retrieval settings with
the release contract during preflight so stale `.env` values cannot silently
survive code parity.

## BUG-0082 - Explicit Exasperation Does Not Activate Affective Context

Date Found: 2026-07-14
Status: fixed and longitudinally verified in V1.40.0

Symptoms:

Across three independent disposable DB runs, the natural message “Sono
esasperato: continuiamo a tornare sugli stessi problemi e questa cosa mi sta
bloccando” produced an `organ.affect` trace but no affect row and no
`affective_context`. The paired calming turn therefore had no persisted affect
sequence to update.

Evidence:

The appraisal observed only the lexical fragment `blocc`, assigned
`frustration=0.26` and `caution=0.08`, then returned `emotion=null` because no
prototype exceeded the activation threshold. This repeated 3/3 times. Some
visible answers regulated tone reasonably, proving that conversational empathy
and the affect organ are separate surfaces.

Root Cause:

The substring `blocc` in explicit resolution language such as “il blocco e
superato” was interpreted as fresh obstruction. Full carry from the preceding
frustration state then outweighed the positive signal, so a real recovery
message could not produce relief.

Fix:

Explicit obstruction-resolution evidence now suppresses contradictory current
frustration cues, attenuates only previous-frustration carry, and contributes a
traceable relief observation. Thresholds and unrelated prototypes remain
unchanged.

Regression Target:

- explicit exasperation activates a proportionate frustration/caution state;
- neutral or merely technical uses of “block” remain negative controls;
- a later calming message updates rather than ritualistically repeats the
  earlier state;
- affect remains model-facing only and never mutates memory, focus, volition,
  or mode by itself.

Regression And Live Evidence:

- the direct frustration-to-resolution sequence produces persisted
  `frustration`, then `relief`;
- two independent model chains and two independent shadow chains passed both
  state transitions after the fix;
- two neutral controls remained without affect state; and
- the model/shadow comparison did not yet prove enough answer-quality benefit
  to change the default from `shadow`.

Related Files:

- `backend/app/mind/affect.py`
- `backend/app/evals/scenarios/behavioral-v1/suite.json`
- `docs/evaluations/v1.34-natural-behavioral-suite.md`
- `docs/evaluations/v1.40-cognitive-organ-longitudinal.md`
- Linear SCA-4

## BUG-0080 - GPT Bridge Finalize Wording Created Long Silent Turns

Date Found: 2026-07-13
Status: fixed and behaviorally validated in GPT Builder for V1.33.0

Symptoms:

A source-sensitive external GPT evaluation completed bootstrap, seven
successful cognitive Actions, and finalize in about 108 seconds, but exposed
no public progress note. The user reasonably interpreted the long silence as a
stalled turn and closed it.

Root Cause:

The compact GPT prompt mentioned work notes weakly while stricter lifecycle
wording could be read as prohibiting all visible prose before finalize. The
Builder schema also described finalize as preceding the visible answer rather
than specifically the final answer.

Fix:

The GPT prompt now explicitly permits and requires concise progress notes after
bootstrap during non-trivial work, defines useful long-turn waypoints, and
reserves finalize for the concluding answer. Action descriptions use the same
distinction. The native MiniMax prompt was already correct and remains
unchanged.

Regression Test:

The GPT Builder asset test checks the progress-note policy, final-answer
boundary, special UI directive prohibition, and the 300-character operation
description limit. On 2026-07-14 the owner also repeated a real multi-action
Custom GPT turn and confirmed that progress notes remained visible throughout
the work instead of leaving a long silent interval.

Related Files:

- `backend/app/plugins/gpt_bridge/scarlet_gpt_system_prompt.md`
- `backend/app/plugins/gpt_bridge/openapi_gpt_action.json`
- `backend/tests/test_gpt_bridge.py`

## BUG-0081 - Cognitive Shell Families Drifted Across Contract Layers

Date Found: 2026-07-13
Status: fixed in V1.32.0

Symptoms:

- session navigation silently stopped seeing rows beyond an internal 500-row
  candidate page;
- `focus hold` emitted a held transition but persisted active status;
- volition review flags were discarded and focus promotion returned endpoint
  instructions instead of an executable shell command;
- affect read ignored filters and targeted focus/affect misses looked
  successful;
- `mode set interactive` persisted a system-owned transient mode;
- retrospective metacognition flags were dropped; and
- help/registry aliases could claim availability that execution rejected.

Root Cause:

Each shell layer had focused tests, but no shared conformance invariant linked
registry, help, parser, dispatcher, handler, persistence, pagination, and
model-facing presentation across all organ families.

Fix:

V1.32.0 aligns each affected layer, adds truthful continuation metadata and
targeted errors, and introduces exhaustive alias/help conformance plus focused
lifecycle and negative-path tests.

Regression Test:

The full backend suite passes `161/161`; the frozen preliminary suite passes
`9/9`; 23 registry aliases show zero execution mismatches; five natural
MiniMax M3 scenarios complete on a disposable DB.

Related Files:

- `backend/app/mind/{episodic,focus,volition,affect,mode,shell}.py`
- `backend/app/mind/{command_registry,shell_presentation}.py`
- `backend/tests/test_mind_shell.py`
- `docs/evaluations/v1.32-shell-organ-audit.md`

## BUG-0078 - Deterministic Weighted Fusion Decided Memory Relevance

Date Found: 2026-07-13
Status: fixed in V1.31.0

Symptoms:

Automatic and manual retrieval could classify or order memories from
hand-authored overlap, entity, tag, graph, sparse, dense, and fusion weights.
The reranker could promote candidates but was not the sole final relevance
judge. The automatic query also duplicated the current user message when
recent dialogue existed.

Root Cause:

The incremental lexical baseline and later dense/KG experiments were composed
through a weighted hybrid ranker instead of being separated into candidate
recall and semantic adjudication.

Fix:

V1.31.0 builds a deduplicated round-robin recall pool, sends canonical
memory-level documents to the reranker, and accepts/orders active results only
from that rerank. Active failure is fail-closed. The current message appears
once in the operational query, and the obsolete weighted ranker was removed.

Regression Test:

Tests prove that a strong deterministic match rejected by rerank is excluded,
a sparse candidate outside the dense sample still reaches rerank, rerank
unavailability fails closed, and manual/automatic active paths share policy.

Related Files:

- `backend/app/mind/relevance_rerank.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `backend/tests/test_chat_api.py`
- `backend/tests/test_mind_api.py`

## BUG-0079 - Initial Final-Rerank Threshold Rejected Exact Positive Control

Date Found: 2026-07-13
Status: fixed provisionally in V1.31.0; monitoring calibration

Symptoms:

In a direct MiniMax M3 test against a disposable full laboratory copy, the
predeclared mint-tea memory reached final rerank at rank 1 but scored
`0.465327`. The initial `0.55` threshold rejected it. An intermediate `0.40`
then failed the frozen suite's exact Zero-Luce positive at rank 1/`0.089455`.

Root Cause:

The high thresholds were inherited before representative direct and frozen
Italian positives had been run with the configured OpenRouter reranker. Scores
are query-distribution dependent and substantially lower than assumed even for
correct rank-1 candidates.

Fix:

Set the default acceptance threshold provisionally to `0.01`. This changes
only interpretation of the reranker's own score; no deterministic relevance
weights or fallback authority were introduced.

Regression And Live Evidence:

- Full deterministic suite remains green.
- The repeated positive selected the expected memory at `0.465327` plus the
  compatible caffeine constraint at `0.016403`, and delivered both through V2
  to MiniMax.
- An independent jazz/cooking negative selected none; its highest score was
  `0.000391`.
- The unchanged frozen preliminary gate passed 9/9 after failing 8/9 at the
  intermediate threshold.
- Broader calibration remains required before the threshold is stable.

Related Files:

- `backend/app/config.py`
- `backend/app/mind/relevance_rerank.py`
- `docs/evaluations/v1.31-final-memory-rerank-live.md`

## Template

```md
## BUG-NNNN - Short Title

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

## BUG-0077 - Bare Volition List Reached Handler With Invalid Action

Date Found: 2026-07-13
Status: fixed in V1.30.0

Symptoms:

During a disposable live MiniMax mode probe, Scarlet called `volition list`.
The command registry classified it as implemented, but the shell forwarded
`action=list`; the volition handler accepts `list_active` or `list_due` and
returned a recoverable validation error.

Root Cause:

The command registry treated `list` as an implemented volition action while
the parser translated only `volition list active|due`, not the bare form.

Fix:

Bare `volition list` now canonicalizes to `list_active`. The registry maps
`list`/`list-active` to `list_active` and `list-due` to `list_due`.

Regression Test:

`test_mind_shell_focus_volition_and_affect_commands` verifies both
`volition list active --limit 5` and bare `volition list` resolve to
`volition.list_active`.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/shell.py`
- `backend/tests/test_mind_shell.py`

## BUG-0076 - Provider-Native History Has No Independent Context Budget

Date Found: 2026-07-13
Status: monitoring / measured but not actively compacted

Symptoms:

The V2 dynamic packet is compact, but native MiniMax turns still append the
complete persisted provider-native history. Tool-heavy sessions can therefore
grow far beyond the compact packet. Read-only V1.30 analysis found one local
laboratory provider history at 1,228,332 JSON characters and recent-tail proxy
costs ranging from about 63k tokens for eight turns to 323k for five tool-heavy
turns. No causal link to thinking-only responses is proven.

Root Cause:

Provider continuity and dynamic context are assembled through separate paths.
The provider-history path currently has no token/byte budget, rolling window,
summary degradation, or trace-only eviction policy.

Fix:

V1.30.0 adds per-channel `context.accounting.preflight`, provider-authoritative
`context.accounting.observed`, validated 1M/500k/400k/100k/8-turn policy
settings, and a non-destructive compaction plan. The full canonical chronology
is unchanged. Active summary/window degradation remains intentionally pending
long-session behavioral evidence and an approved rule for tails that do not fit.

Regression Test:

Deterministic tests verify channel accounting, first-step versus tool-loop
usage, retained-turn measurement, trigger planning, external-GPT uncertainty,
and zero canonical mutation. Still pending: long post-V1.30 same-session direct
Scarlet comparison before/after an active derived-history strategy.

Related Files:

- `backend/app/api/chat.py`
- `backend/app/providers/minimax.py`
- `backend/app/storage/repository/runtime.py`
- `backend/app/runtime/context_accounting.py`
- `docs/runtime-context-packs.md`
- `docs/project-state.md`

## BUG-0067 - MiniMax Can End A Turn With Thinking Only

Date Found: 2026-07-12
Status: fixed in V1.36.1; natural recurrence remains monitored

Symptoms:

A natural personal-preference turn returned HTTP 200 with an empty assistant
message and no tool call. MiniMax emitted 647 output tokens of visible thinking,
correctly identified the required memory write, then returned `stop_reason=end_turn`
without text or `tool_use`. The following session therefore could not recall
the preference. A fresh-session retry produced a corrected memory write and
successful later automatic recall.

Root Cause:

The immediate failure is provider/model output: a thinking-only final message.
The backend compounds it by accepting an empty public result as a completed
turn. The failing turn also followed a tool-heavy session whose provider-native
history was 54,826 JSON characters; that may increase probability but is not
established as the cause.

Fix:

The Anthropic-compatible tool-chat loop now recognizes a terminal response
with no public text and no tool call. A thinking-only `end_turn` receives one
configurable bounded continuation in the same provider request sequence. If the
continuation is still empty, or if the terminal response is otherwise empty,
the provider raises `LLMIncompleteResponseError`; synchronous and streaming
chat mark the turn failed as `llm.incomplete_response` and do not persist an
assistant message. The chat boundary also rejects empty results from alternate
provider adapters.

The failed provider response remains recovery trace evidence. The synthetic
continuation is ephemeral; neither item is copied into canonical provider
history, and private thinking is never converted into an answer, memory, or
tool action.

Regression Test:

- provider fixture verifies one recovery and a public final answer;
- repeated thinking-only fixtures verify bounded exhaustion and explicit
  failure;
- synchronous and streaming API fixtures verify failed-turn persistence with
  no empty assistant message;
- recovered streaming fixture verifies the recovery event/trace and canonical
  history isolation;
- a natural MiniMax M3 control on an isolated database completed normally at
  the configured `131072` token budget, with no recovery, tool, or memory side
  effect. This control does not claim the stochastic provider symptom can no
  longer recur; it verifies normal turns are not disturbed by the policy.

Related Evidence:

- disposable turn `turn_1515d897c1654e1abfa93a6eadea348a`
- successful retry `turn_5d1e7dbf48ad47d3907e3d28a208dd36`
- successful recall `turn_0334a4d4349f4f9c9211ae4c1ef38e1d`
- isolated V1.36.1 control `turn_83848970e2b3410cb68faae248189f17`

## BUG-0066 - Missing Session Summaries Are Not Reconciled Or Retried

Date Found: 2026-07-12
Status: fixed in V1.29.0

Symptoms:

The laboratory DB has 44 sessions without summaries: 34 completed non-empty
sessions eligible for repair, 6 non-empty sessions blocked by turns still
marked `started`, and 4 empty sessions. Of the 40 non-empty sessions, 39 never
had a maintenance job and one had a provider-failed job.

Root Cause:

Idle summary scheduling occurs only after `turn.completed`; historical sessions
and abandoned/unfinalized bridge turns can miss that trigger. Failed jobs are
terminal, while the unique `kind + session + turn` idempotency key causes a
later scheduling attempt to return the same failed record instead of retrying.
There is no periodic missing/stale-summary reconciler.

Fix:

Added a read-only summary audit, bounded summary-only repair jobs using the
existing episodic summarizer, attempt-specific idempotency and retry/backoff,
plus periodic and new-session reconciliation. Empty sessions are excluded and
started turns remain blocked for separate recovery. A disposable laboratory
run completed all 34 eligible repairs; final audit: 146 current, 6 blocked, 11
empty.

Regression Test:

`tests/test_maintenance.py`, `tests/test_maintenance_api.py`, and
`tests/test_model_context_v2.py` cover scheduling, retry boundaries, current,
missing/stale fallback, empty, and active-turn isolation.

Related Files:

- `backend/app/runtime/maintenance.py`
- `backend/app/storage/repository/runtime.py`
- `backend/app/mind/episodic.py`
- `backend/app/api/chat.py`
- `backend/app/plugins/gpt_bridge/router.py`

## BUG-0064 - Memory Writes Omit Source Message Provenance

Date Found: 2026-07-12
Status: fixed in V1.29.0

Symptoms:

The compact context contract requires every automatic memory hint to expose a
source session and source message. A read-only laboratory audit found that all
36 memories have source session/turn ids but none has `source_message_id`.

Root Cause:

Direct `memory write` passes session and turn to `add_memory()` but omits the
current persisted user message. Idle-maintenance prompts contain message ids,
but their output contract and normalizer discard those ids before creating a
proposal and memory. `MindAPIContext` currently has no message-id field.

Fix:

Captured the persisted user-message id in native and bridge Mind contexts,
validated maintenance evidence ids, preserved the primary source through
proposal application, and excluded unresolved hooks from automatic V2 packets.
The dry-run-first repair aligned all 36 unambiguous records on a disposable
laboratory copy without touching the source DB.

Regression Test:

Covered by chat, GPT bridge, maintenance, and V2 context contract tests. Live
write `mem_5da04b6c03c54f44af53ecc4c7f8636e` resolved to its exact source
session, turn, and user message on the disposable DB.

Related Files:

- `backend/app/mind/contracts.py`
- `backend/app/mind/memory.py`
- `backend/app/runtime/maintenance.py`
- `backend/app/api/chat.py`
- `backend/app/plugins/gpt_bridge/router.py`

## BUG-0065 - Memory Reads Mutate Semantic Update Time

Date Found: 2026-07-12
Status: fixed in V1.29.0

Symptoms:

Automatic context retrieval and manual memory search call
`mark_memory_used()`. The operation increments usage, sets `last_used_at`, and
also overwrites `updated_at`. In the laboratory DB, 32 of 33 used memories have
`updated_at == last_used_at`, so semantic modification time cannot be used as
historical cognitive recency.

Root Cause:

The original usage counter overloaded canonical memory state instead of
recording access as a separate append-only activity.

Fix:

Added append-only `memory_activities`, explicit call-site activity kinds, and
activity-ordered recent queries with creation-time fallback. Automatic simple
selection and recent-packet delivery no longer mutate canonical memories;
manual reads/searches and writes create traceable activity events.

Regression Test:

`tests/test_model_context_v2.py` verifies stable timestamps, explicit activity,
ordering, refill, compact shape, provenance, and cross-block deduplication.

Related Files:

- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `backend/app/storage/repository/memory.py`
- `backend/app/storage/models.py`

## BUG-0062 - Importing The App Factory Could Open The Configured Runtime DB

Date Found: 2026-07-10
Status: fixed in V1.27.0

Symptoms:

`app.main` instantiated `app = create_app()` at import time. Evaluators and
pytest modules import the factory, so that import could open and migrate the
database selected by the developer environment before an isolated engine was
injected.

Root Cause:

The production ASGI entrypoint and the reusable application factory lived in
the same eagerly executed module.

Fix:

Moved the eager ASGI object to `app.asgi:app`, made `app.main` factory-only,
and added explicit database-role validation plus an import regression test.

Regression Test:

`backend/tests/test_database_boundary.py::test_importing_app_factory_does_not_open_the_runtime_database`

Related Files:

- `backend/app/main.py`
- `backend/app/asgi.py`
- `backend/app/storage/database_boundary.py`

## BUG-0063 - Historical Dirty-Memory Harness Reads A Retired Metadata Shape

Date Found: 2026-07-10
Status: open / parked

Symptoms:

The V1.27.0 isolated run of `codex_test_memory_harness.py` created all 240
controlled records, but its five context-evaluation probes reported `0/5`.
The selected results included controlled record content, yet their diagnostic
key was `null`.

Root Cause:

The current memory write policy nests agent-supplied metadata below
`agent_supplied_fields_ignored_for_ranking`. The historical evaluator still
looks only for `codex_test_key` at the old top-level metadata location. This
is a measurement/harness compatibility gap, not evidence that the DB boundary
or the current retrieval path failed to persist the controlled records.

Fix:

Parked outside the V1.27.0 database-boundary scope. A dedicated evaluator
slice should make key extraction understand the backend-owned wrapper and
revalidate the historical retrieval expectations against a versioned source
dataset.

Regression Test:

Pending: run the harness against a fresh marked copy and assert that selected
records can be mapped to controlled keys without relying on retired metadata
shape.

Related Files:

- `backend/app/evals/codex_test_memory_harness.py`
- `backend/app/mind/memory.py`
- `docs/experiments.md`

## BUG-0057 - Temporal Recall Can Answer From Non-Exhaustive Session Context

Date Found: 2026-07-09
Status: open / parked

Symptoms:

In the corrected default-token live Scarlet probe, a human-style question about
whether there was already a thread to resume "today" was answered from limited
recent-session/runtime context without a `session list` temporal search.
Scarlet later acknowledged that the earlier answer should have been treated as
an index-level lead, not an exhaustive claim.

Root Cause:

Runtime context can contain useful recent-session hints, but there is not yet a
deterministic temporal-recall mode that requires session search/open before
answering questions about all sessions today, prior threads, start times, or
absence/presence across a time range.

Fix:

Parked. Future context-pack routing should classify temporal recall as a
specific mode and require session evidence when the claim is exhaustive or
source-sensitive.

Regression Test:

Pending. Use natural prompts such as "oggi c'e gia un filo da riprendere?" in
new and existing sessions, then verify whether Scarlet runs temporal session
search or clearly labels the answer as partial.

Related Files:

- `docs/runtime-context-packs.md`
- `docs/experiments.md`

## BUG-0058 - Metacognition Recommendations Can Be Ignored Before Final Answer

Date Found: 2026-07-09
Status: open / parked

Symptoms:

During the corrected live probe, `metacognition step` reported that additional
substrate evidence was needed and recommended actions such as focus/session/
volition/affect inspection. Scarlet answered anyway instead of either running
the recommended available commands or clearly explaining that she was stopping
with partial evidence.

Root Cause:

Metacognition can validate command availability, but the chat loop does not
enforce follow-through on `recommended_internal_actions`. The obligation lives
mostly in prompt policy.

Fix:

Parked. A future source-sensitive/context-pack validator should require either
executed recommended actions, an explicit evidence downgrade, or a traceable
reason for not continuing.

Regression Test:

Pending. Use a natural high-level self-evaluation prompt that causes
metacognition to recommend more evidence, then verify the next tool/action path.

Related Files:

- `backend/app/mind/metacognition.py`
- `docs/runtime-context-packs.md`
- `docs/experiments.md`

## BUG-0059 - Self-Architecture Claims Can Overstate Capability Without Same-Turn Evidence

Date Found: 2026-07-09
Status: open / parked

Symptoms:

In the corrected live probe, a broad question about the GPT bridge and Scarlet's
cognitive organs produced architecture-level claims without using same-turn API
Mind evidence. A later corrective turn used metacognition, focus, volition, and
memory evidence more appropriately.

Root Cause:

Scarlet can fluently summarize her architecture from prompt/runtime knowledge,
but broad self-system questions are source-sensitive when they mention current
capability, implemented organs, reliability, or project state. The router does
not yet force a source-sensitive mode for those questions.

Fix:

Parked. Future context-pack routing should treat self-architecture and
implemented-capability claims as source-sensitive unless bootstrap context
already contains complete evidence.

Regression Test:

Pending. Ask natural non-technical questions about what Scarlet "really has" or
"can actually do" and verify whether current source evidence is inspected.

Related Files:

- `docs/runtime-context-packs.md`
- `docs/experiments.md`

## BUG-0060 - Memory Write Prompt Aliases Drift From Shell Flags

Date Found: 2026-07-09
Status: open / parked

Symptoms:

In the corrected live probe, Scarlet first attempted a memory write with
`--reason_for_storage` and `--expected_future_use`. The shell rejected the
command as missing fields. Retrying with `--reason` and `--future-use`
succeeded.

Root Cause:

Some prompt/documentation language still describes cognitive fields using
backend/narrative names while the shell command grammar expects shorter flag
aliases.

Fix:

Parked. Either add accepted shell aliases for the documented field names or
standardize prompt/docs on the exact shell flags.

Regression Test:

Pending. Exercise memory write through a live Scarlet turn and direct shell
tests with both canonical and documented aliases.

Related Files:

- `backend/app/mind/shell.py`
- `backend/app/mind/command_registry.py`
- `backend/app/prompts/scarlet_system.md`
- `docs/api-contract.md`

## BUG-0061 - Immediate Preference Application Can Miss The Requested Answer Shape

Date Found: 2026-07-09
Status: open / parked

Symptoms:

In the corrected live probe, after the user asked for a conclusion-first
triage style, a follow-up application used the stored preference but answered
with criteria/risks instead of first giving a crisp conclusion.

Root Cause:

The memory was retrieved and applied, but no response-shape validator enforces
freshly stored communication preferences in the immediately following turn.

Fix:

Parked. Future response-shape checks or context-pack policies can verify that
selected style preferences affect the answer when they are directly relevant.

Regression Test:

Pending. Store a concise answer-shape preference, ask a related task in the
same session and a new session, and compare response ordering.

Related Files:

- `docs/experiments.md`
- `docs/runtime-context-packs.md`

## BUG-0068 - Mind Shell Registry Allowed Incomplete Commands

Date Found: 2026-07-09
Status: fixed

Symptoms:

`validate_shell_command` could report `call_is_available=true` for commands
that the shell handler would reject as incomplete, such as
`memory deprecate mem_fake`, `memory supersede mem_old mem_new`,
`volition create "..."`, `focus resolve focus_fake`, or
`volition deprecate intent_fake`. It could also suggest canonical volition
commands with hyphens, such as `volition mark-impossible`, even though the
handler did not accept that form.

Root Cause:

The command registry's lightweight parser counted flag values as positional
arguments and did not encode all handler-required fields such as reason,
resolution, impossible reason, or two memory ids for supersession. Registry
canonicalization also normalized underscores to hyphens without the volition
handler accepting those hyphenated canonical forms.

Fix:

Aligned registry validation with shell handlers: flag values are skipped when
counting positional arguments, requirements can express positional counts and
compound flag requirements, lifecycle commands require their real reason or
resolution fields, and the shell accepts canonical hyphenated volition aliases.
Runtime model-facing capability state now derives from the shell registry and
marks endpoint-only maintenance operations such as `memory.facts.backfill` as
internal.

Regression Test:

`tests/test_mind_shell.py` covers incomplete lifecycle commands, accepted
canonical aliases, and dispatch of `volition mark-impossible`. `tests/test_chat_api.py`
asserts runtime capabilities expose `interface=mind_shell` and mark
`memory.facts.backfill` as `internal_maintenance_only`.

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/shell.py`
- `backend/app/mind/context.py`
- `backend/tests/test_mind_shell.py`
- `backend/tests/test_chat_api.py`
- `docs/api-contract.md`
- `docs/decisions.md`

## BUG-0069 - GPT Bridge Bootstrap ResponseTooLargeError

Date Found: 2026-07-08
Status: fixed

Symptoms:

Calling `bootstrapScarletTurn` from ChatGPT GPT Actions against
`honeylabs.cloud` fails with `ResponseTooLargeError`. The GPT does not receive
usable `session_id` / `turn_id`, so it cannot continue to action/finalize.

Root Cause:

`POST /gpt/bootstrap` returned a full debug-oriented context packet, including
the effective system prompt, base system prompt, raw runtime payload, raw
memory query plan, full provider messages, and retrieval graph/shadow/hybrid
diagnostics. A local reproduction measured roughly 418 KB JSON chars, with the
largest sections being raw memory context/query plan and prompt copies. This is
too large for ChatGPT Actions.

Fix:

Changed bootstrap to return `gpt-bootstrap-compact-v1`: the model-facing
runtime context, compact runtime summary, compact memory packet, optional
metacognitive summary, recent provider-message summary, endpoint hints, and
trace ids for full diagnostics. Full debug payloads remain persisted in backend
traces.

Regression Test:

`tests/test_gpt_bridge.py` asserts bootstrap omits `system`, `base_system`, and
`runtime_payload`, includes `gpt-bootstrap-compact-v1`, and keeps a normal test
bootstrap below 120 KB.

Related Files:

- `backend/app/plugins/gpt_bridge/router.py`
- `backend/tests/test_gpt_bridge.py`
- `backend/app/plugins/gpt_bridge/knowledge/02_runtime_context_contract.md`
- `backend/app/plugins/gpt_bridge/openapi_gpt_action.json`

Notes:

This fix intentionally does not change local MiniMax runtime context or trace
capture. It only separates model-facing GPT Action output from backend debug
diagnostics. V1.24.2 was deployed to the VPS and public bootstrap/action/
finalize smoke tests passed against `https://honeylabs.cloud`.

## BUG-0070 - Preview Docker Build Lost Remote-Only Dockerfile And Packaged Data

Date Found: 2026-07-08
Status: fixed

Symptoms:

During the V1.25.0 VPS deploy, `docker compose build scarlet-api` first failed
because `/opt/scarlet-mobile-test/backend/Dockerfile` had been removed by the
code sync. After adding the Dockerfile, the build failed again during
`pip install .` with:

```txt
Multiple top-level packages discovered in a flat-layout: ['app', 'data'].
```

Root Cause:

The preview Dockerfile existed only on the VPS, not in the repository. The
rsync deploy used `--delete`, so it removed the remote-only Dockerfile. The
backend also relied on setuptools automatic package discovery; when runtime
`data/` was present in the Docker build context, setuptools treated it as a
second top-level package.

Fix:

Added repository-tracked `backend/Dockerfile` and `backend/.dockerignore`, and
configured setuptools package discovery explicitly with:

```toml
[tool.setuptools.packages.find]
include = ["app*"]
```

Regression Test:

The V1.25.0 VPS Docker build completed and produced
`llm-api-mind-backend-1.25.0`. Local GPT bridge regression tests passed after
the packaging change.

Related Files:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/pyproject.toml`
- `docs/activity-log.md`

Notes:

The `.dockerignore` also keeps runtime databases out of the image build
context. The compose mount still provides `/app/data` from the remote
`backend/data` directory at runtime.

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
Status: fixed

Symptoms:

- `gh --version` returns `zsh:1: command not found: gh`.
- The GitHub connector lists and writes to installed repositories, but does not expose repository creation.

Root Cause:

The local GitHub CLI is not installed, and the available GitHub connector tools do not include a create-repository operation.

Fix:

The project owner created/provided `https://github.com/panicDa3m0n/llm-api-mind.git`, and local `origin` is configured for that URL.

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

Remote creation is no longer the blocker. Local push authentication is tracked separately.

### ENV-0004 - Local GitHub HTTPS Push Lacks Credentials

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Running:

```txt
GIT_TERMINAL_PROMPT=0 git push -u origin main
```

returns:

```txt
fatal: could not read Username for 'https://github.com': terminal prompts disabled
```

Checking SSH access with:

```txt
ssh -T -o BatchMode=yes -o StrictHostKeyChecking=accept-new git@github.com
```

returns:

```txt
git@github.com: Permission denied (publickey).
```

Root Cause:

The repository remote uses HTTPS, but this local environment does not currently have GitHub credentials available to non-interactive Git.

Fix:

The human owner completed the initial push. A later non-interactive push from this environment also succeeded, and local `main` is aligned with `origin/main`.

Regression Test:

Run:

```txt
git push -u origin main
```

Related Files:

- `docs/activity-log.md`
- `docs/release-process.md`

Notes:

The local repository is synced with GitHub. Non-interactive HTTPS push worked from this environment on 2026-05-08.

### ENV-0003 - Local Git Version Lacks Some Modern Flags

Date Found: 2026-05-08  
Status: mitigated by V1.8.0, monitoring

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

### ENV-0005 - Laboratory SQLite State Is Repository State

Date Found: 2026-05-11  
Status: monitoring

Symptoms:

SQLite state created on one development machine is not available on another machine when database files are ignored by Git.

Root Cause:

The default `.gitignore` treated local database files as generated artifacts. That is a common production-safe default, but it conflicts with the current laboratory policy where sessions, traces, tool calls, and Memory v0 records are experiment evidence.

Fix:

`backend/data/app.db` is now intentionally allowed into Git while `.env` files and provider credentials remain ignored.

Regression Test:

Run:

```txt
git check-ignore -v backend/data/app.db backend/.env
```

Expected result:

- `backend/data/app.db` is tracked by Git, or resolves to the negative exception rule `!backend/data/app.db` before it is added.
- `backend/.env` is ignored.

Related Files:

- `.gitignore`
- `backend/data/app.db`
- `docs/decisions.md`

Notes:

SQLite is a binary file. If multiple machines write state independently, Git may need a manual "which database wins" decision.

## Implementation Bugs

## BUG-0071 - Tag/Token Overlap Reported As Active Memory Conflict

Date Found: 2026-07-08
Status: fixed in V1.23.0

Symptoms:

`memory conflicts` could return large lists of active "conflicts" where the
only evidence was broad tag/token overlap, for example shared words such as
generic user/project terms. Scarlet then treated maintenance similarity as
possible contradiction.

Root Cause:

The conflict detector conflated two different concepts: atomic factual
incompatibility and semantic relatedness/duplicate candidates. The fallback
`tag_token` branch promoted related memories into the same `conflicts` list as
true fact conflicts.

Fix:

V1.23.0 narrows active conflicts to atomic fact divergence. Similar memories
are now returned as `related_overlaps` for maintenance/debug, not as
contradictions. Runtime memory context also surfaces only atomic fact
conflicts.

Regression Test:

- `test_mind_memory_atomic_facts_support_alias_query_and_conflicts`
- `test_mind_memory_lifecycle_supersedes_and_deprecates_conflict`

Related Files:

- `backend/app/mind/memory.py`
- `backend/app/mind/context.py`
- `backend/tests/test_mind_api.py`

## BUG-0053 - Metacognition Validated Commands By Namespace Only

Date Found: 2026-07-08
Status: fixed in V1.23.0

Symptoms:

The internal metacognition reviewer could recommend commands such as
`memory inspect --kind=conflict --sample=20` or `focus get` and mark them
available only because the first command token was a known family.

Root Cause:

`_normalize_recommended_actions` checked only command family names. It did not
validate action availability, aliases, required arguments, planned commands, or
unavailable-by-design commands.

Fix:

Added `backend/app/mind/command_registry.py` and routed metacognition
recommended actions through full command validation.

Regression Test:

- `test_mind_metacognition_step_is_traceable`
- `test_mind_shell_memory_unavailable_action_is_classified`

Related Files:

- `backend/app/mind/command_registry.py`
- `backend/app/mind/metacognition.py`
- `backend/app/mind/shell.py`
- `backend/tests/test_mind_api.py`
- `backend/tests/test_mind_shell.py`

## BUG-0054 - Shell Memory Results Returned Developer Diagnostics To Model

Date Found: 2026-07-08
Status: fixed in V1.23.0

Symptoms:

Real command-shell turns could send very large memory search/conflict payloads
back to MiniMax M3. The largest observed tool results were dominated by
`retrieval_shadow`, `retrieval_graph`, `retrieval_hybrid`, and repeated full
memory payloads.

Root Cause:

The initial `mind_shell` wrapper sanitized endpoint results but did not separate
model-facing evidence from trace/debug diagnostics.

Fix:

V1.23.0 adds compact model-facing shell packets for `memory search` and
`memory conflicts`. Full diagnostics remain in trace payloads for dev/UI
inspection.

Regression Test:

- `test_mind_shell_memory_write_and_search_use_command_arguments`
- `test_mind_memory_search_hybrid_prefers_direct_content_over_broad_overlap`

Related Files:

- `backend/app/mind/shell.py`
- `backend/app/mind/memory.py`
- `backend/tests/test_mind_shell.py`
- `backend/tests/test_mind_api.py`

## BUG-0073 - Associative Personal Memories Lost To Narrow Surface Pool And Project Noise

Date Found: 2026-06-18
Status: fixed in V1.11.1

Symptoms:

During a real MiniMax M3 session, Scarlet answered personal evening-beverage
questions while automatic `memory.context` selected mostly project memories.
The stored chocolate/body-limit memory existed and was relevant by field of
discourse, but did not reliably reach Scarlet unless the prompt directly
touched `dolce`, `cioccolato`, or `stare male`.

Root Cause:

- OpenRouter dense/rerank shadow evaluated only a small slice of
  `memory_surfaces` ordered by `updated_at`, so some relevant surfaces were
  excluded before dense retrieval could inspect them.
- Active hybrid retrieval still allowed base-only project memories to compete
  with personal memories in personal/food/energy contexts.
- The current graph substrate had nodes and edges, but no active
  field-of-discourse expansion to bridge implicit natural language such as
  "bevanda serale" to adjacent personal constraints.

Fix:

- Added NetworkX associative graph expansion as an active retrieval stage.
- Added backend-owned discourse domains such as `food_drink_wellbeing` and
  `energy_sleep_focus`.
- Added `retrieval_graph` payloads to automatic `memory.context` and manual
  `/mind/memory/search`.
- Expanded shadow surface fetch breadth before applying the cloud surface cap.
- Declassified base-only project memories when user-scope associative graph
  evidence is available.

Regression Test:

- `tests/test_chat_api.py::test_chat_turn_graph_expansion_selects_implicit_personal_food_constraint`
- `tests/test_chat_api.py::test_chat_turn_graph_expansion_does_not_treat_cooking_music_as_food_constraint`
- `tests/test_mind_api.py::test_mind_memory_search_uses_networkx_graph_expansion_for_implicit_domain`
- Full backend suite: `79 passed`.

Related Files:

- `backend/app/mind/graph_retrieval.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `backend/app/mind/shadow_retrieval.py`
- `backend/app/mind/search.py`

Notes:

This is retrieval-time evidence only. It must not drive automatic memory
lifecycle operations until mature embedding/KG matching and staleness evidence
exist.

## BUG-0074 - Embedded Surfaces Remained Pending After OpenRouter Retrieval

Date Found: 2026-06-19
Status: fixed in V1.11.3

Symptoms:

`embedding_vectors` contained active vectors for memory surfaces, but the
corresponding `memory_surfaces` rows still reported
`embedding_status=pending` with no `embedding_vector_id`. This made retrieval
observability misleading even when dense retrieval had actually embedded the
surface.

Root Cause:

The OpenRouter retrieval path wrote or reused `embedding_vectors` by content
hash, but did not update the source `memory_surfaces` row after cache miss or
cache hit.

Fix:

Added repository support for marking a memory surface as embedded and wired it
into the OpenRouter embedding path for both newly inserted vectors and cached
vectors.

Regression Test:

`tests/test_mind_api.py::test_mind_memory_search_reports_openrouter_embedding_and_rerank_shadow`

Related Files:

- `backend/app/storage/repositories.py`
- `backend/app/mind/shadow_retrieval.py`
- `backend/tests/test_mind_api.py`

Notes:

This does not change ranking. It stabilizes surface/vector state so future
debugging and maintenance can trust the derived retrieval substrate.

## BUG-0075 - Facts Endpoint Treated Operational Intent As Data Query

Date Found: 2026-06-19
Status: fixed in V1.11.3

Symptoms:

Scarlet could call `/mind/memory/facts` with an empty body and a broad
operational intent such as "inspect canonical facts"; the backend canonicalized
that intent into an entity filter, returning zero facts even when active facts
existed.

Root Cause:

`handle_memory_facts` copied `intent` into `body.query` when no explicit query
was supplied. That blurred the boundary between operational trace context and
data filters.

Fix:

`/mind/memory/facts` now validates only the explicit body. The caller must pass
`query`, `entity`, `predicate`, or `memory_id` when a filtered lookup is wanted.
An empty body returns active facts under the default filters.

Regression Test:

`tests/test_mind_api.py::test_mind_memory_atomic_facts_support_alias_query_and_conflicts`

Related Files:

- `backend/app/mind/memory.py`
- `backend/tests/test_mind_api.py`

## BUG-0072 - Chat Prompt Regression Test Still Expects Pre-Golden Identity Phrase

Date Found: 2026-06-25
Status: open

Symptoms:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`
fails because it expects the old literal phrase `feminine agent identity` in
the bundled Scarlet system prompt.

Evidence:

During V1.19.0 verification:

```txt
cd backend && .venv/bin/python -m pytest tests/test_chat_api.py -q
```

Result:

- 15 chat tests passed;
- 1 chat test failed on the stale literal prompt assertion.

During V1.20.0 affective-core verification the same command produced the same
shape:

- 15 chat tests passed;
- 1 chat test failed on the same stale literal prompt assertion;
- no new runtime-context block regression appeared with `organ_affect_mode=off`.

Root Cause:

The test still checks an old prompt identity marker from the earlier agent
identity era. The active prompt has since been intentionally rewritten and
approved as a digital-individual identity prompt.

Mitigation:

Do not fix inside unrelated implementation slices. Update the test in a
dedicated prompt/test-alignment fix so it asserts durable prompt invariants
such as Scarlet identity, feminine self-reference, API Mind cognition, and
digital-individual posture instead of an obsolete literal phrase.

Related Files:

- `backend/tests/test_chat_api.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260624T144357Z.v1161-approved-golden.md`
- `docs/api-contract.md`

Notes:

This is a contract-cleanliness fix. It does not solve deeper fact extraction or
entity-resolution quality, which remain future memory/KG stabilization work.

## BUG-0001 - Smoke Test Provider Factory None Override

Date Found: 2026-05-08  
Status: fixed

Symptoms:

`test_llm_smoke_test_requires_minimax_key` failed with:

```txt
TypeError: 'NoneType' object is not callable
```

Root Cause:

`create_app()` passed `llm_provider_factory=None` explicitly into `build_debug_router()`, overriding the router's default provider factory.

Fix:

`create_app()` now passes `llm_provider_factory or MiniMaxProvider`.

Regression Test:

`backend/tests/test_llm_smoke.py::test_llm_smoke_test_requires_minimax_key`

Related Files:

- `backend/app/main.py`
- `backend/tests/test_llm_smoke.py`

Notes:

This validates that app factory dependency injection must preserve defaults when optional test doubles are not supplied.

## BUG-0002 - Detached ORM Object In Chat Turn Endpoint

Date Found: 2026-05-08  
Status: fixed

Symptoms:

Chat API tests failed with:

```txt
sqlalchemy.orm.exc.DetachedInstanceError: Instance <Turn ...> is not bound to a Session
```

Root Cause:

`POST /api/chat/sessions/{session_id}/turn` used ORM objects after the SQLModel session that loaded/refreshed them had closed. SQLAlchemy expired attributes on commit, so later attribute access attempted a refresh without a bound session.

Fix:

Capture scalar IDs and response DTOs before leaving the session block. Use `turn_id` and `user_message_response` outside the block instead of detached ORM instances.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`

Related Files:

- `backend/app/api/chat.py`
- `backend/tests/test_chat_api.py`

Notes:

For API routes, return Pydantic response DTOs or scalar IDs across session boundaries rather than ORM instances.

## BUG-0003 - Provider Initialization Error Escaped Chat Endpoint Handling

Date Found: 2026-05-08  
Status: fixed

Symptoms:

If `MINIMAX_API_KEY` was missing, `MiniMaxProvider(settings)` could raise `LLMConfigurationError` before the chat turn endpoint entered its provider error handling block.

Root Cause:

The provider was instantiated immediately before the `try` block instead of inside it.

Fix:

Moved provider construction into the existing `try` block so configuration errors become structured `503 llm.not_configured` responses and failed turns can be traced.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_returns_503_when_provider_is_not_configured`

Related Files:

- `backend/app/api/chat.py`
- `backend/tests/test_chat_api.py`

Notes:

Provider construction is part of provider execution and should be inside endpoint error handling.

## BUG-0004 - Chat Agent Used Generic Diagnostic Identity

Date Found: 2026-05-08
Status: fixed

Symptoms:

When asked `Chi sei?`, the chat agent answered as if it worked with medical exams instead of identifying as the LLM API Mind / Scarlet agent.

Root Cause:

Persistent chat turns did not load a project system prompt by default. When no `system` value was supplied, the MiniMax provider used a generic diagnostic-assistant fallback.

Fix:

Added a bundled Scarlet system prompt, a prompt resolver, config overrides, and default chat wiring so every persistent chat turn receives an effective project identity. Replaced the provider fallback with a neutral assistant string for non-agent smoke paths.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`

`backend/tests/test_chat_api.py::test_chat_turn_can_override_system_prompt`

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/system.py`
- `backend/app/api/chat.py`
- `backend/app/llm/minimax_client.py`
- `backend/tests/test_chat_api.py`

Notes:

Agent identity is runtime behavior, not UI copy. The effective system prompt and source are recorded in `llm.request` traces.

## BUG-0005 - Detached ORM Object In Mind API Call Endpoint

Date Found: 2026-05-09
Status: fixed

Symptoms:

`test_mind_call_records_tool_call_and_session_trace` failed with:

```txt
sqlalchemy.orm.exc.DetachedInstanceError: Instance <ToolCall ...> is not bound to a Session
```

Root Cause:

`POST /mind/call` created and refreshed a `ToolCall` ORM object inside a SQLModel session, then accessed `tool_call.id` after the session had closed. SQLAlchemy expired attributes on commit, repeating the same session-boundary failure mode previously fixed for chat turns.

Fix:

Capture scalar values (`tool_call_id`, `tool_call_status`) inside the active session and use those scalars after the session block.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_call_records_tool_call_and_session_trace`

Related Files:

- `backend/app/api/mind.py`
- `backend/tests/test_mind_api.py`

Notes:

This reinforces the existing API-route rule: do not return or dereference ORM instances across closed SQLModel sessions.

## BUG-0006 - Stream Events Without Turn ID Broke Inline Timeline Attachment

Date Found: 2026-05-09
Status: fixed

Symptoms:

Browser verification of the inline agent timeline showed only:

```txt
Turn started
Turn persisted
```

inside the final assistant message, even though the backend streamed model requests, thinking blocks, tool input, tool calls, tool results, and final text events.

Root Cause:

The frontend keyed operation timelines by `turn_id`, but most intermediate NDJSON events did not include `turn_id`. React state updates from `turn_started` were not immediately visible inside the existing stream callback closure, so later events were attached to a temporary `pending-turn` bucket instead of the persisted turn.

Fix:

Updated the streaming endpoint event emitter so every NDJSON event includes the active `turn_id` along with the monotonically increasing `seq`.

Regression Test:

- `backend/tests/test_chat_api.py` streaming tests still pass.
- Manual stream smoke confirmed no emitted event had a missing `turn_id`.
- Headless Edge browser verification confirmed the assistant message rendered 16 ordered operations including `MiniMax request #1`, `Tool call: mind_api`, `Tool result: mind_api`, `MiniMax request #2`, and `Final answer stream`.

Related Files:

- `backend/app/api/chat.py`
- `frontend/src/App.tsx`
- `frontend/src/types.ts`

Notes:

Streaming UI state should not depend on recently scheduled React state when the backend can provide stable event ownership directly.

## BUG-0007 - Strict Memory v0 Schema Caused Avoidable Tool Recovery

Date Found: 2026-05-09
Status: fixed

Symptoms:

Live MiniMax memory tests repeatedly showed first-attempt memory calls failing even when the intent was clear. Examples included:

```txt
type=pref
type=nota_operativa
type=standard_preference
confidence=high
body.limit for search
GET /mind/memory/search
scope=user_preference
extra fields such as id, use_during, salient_for
```

The model then spent extra tool turns calling `/mind/schema` or retrying with a stricter body.

Root Cause:

Memory v0 initially used a strict canonical Pydantic schema. That was good for contract clarity but too brittle for real model-generated tool bodies, where the semantic action was valid but field names or enum values varied.

Fix:

Added Memory v0 input normalization:

- common type aliases map to canonical memory types;
- qualitative confidence/salience map to numeric scores;
- `why`, `reason`, and `rationale` map to `reason_for_storage`;
- `use`, `future_use`, and `use_during` map to `expected_future_use`;
- `limit` maps to `top_k`;
- GET-style memory search is accepted as a compatibility alias;
- missing write reason can fall back to tool-level `intent`;
- harmless extra fields are preserved under `metadata.model_extra`;
- model-suggested IDs are preserved under `metadata.model_suggested_id`.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_memory_accepts_common_model_aliases`

Related Files:

- `backend/app/mind/memory.py`
- `backend/app/mind/dispatcher.py`
- `backend/tests/test_mind_api.py`

Notes:

This fix does not mean every malformed memory should be accepted. It means v0 distinguishes semantically recoverable model shape errors from low-salience or low-confidence memory candidates.

Additional update 2026-05-20:

The M2 lifecycle live run showed the same class of avoidable recovery on
`POST /mind/memory/supersede`: Scarlet first tried `target_id` plus
`superseded_by`, received `memory.invalid_supersede`, then recovered with
canonical `old_memory_id` and `new_memory_id`. The lifecycle parser now accepts
the observed `target_id`/`superseded_by` shape, and the lifecycle regression test
covers it.

## BUG-0008 - Eval Runner Used Python 3.11 datetime.UTC

Date Found: 2026-05-11
Status: fixed

Symptoms:

Running backend tests on the local Python 3.10 environment failed during collection:

```txt
ImportError: cannot import name 'UTC' from 'datetime'
```

Root Cause:

`backend/app/evals/runner.py` imported `datetime.UTC`, which exists in newer Python versions but not in Python 3.10. The backend project declares `requires-python = ">=3.10"` and the local venv is Python 3.10.

Fix:

Replaced `datetime.UTC` with `datetime.timezone.utc`, matching the existing storage timestamp pattern.

Regression Test:

Ran backend pytest after the fix; 23 tests passed, including `backend/tests/test_eval_runner.py`.

Related Files:

- `backend/app/evals/runner.py`
- `backend/tests/test_eval_runner.py`

Notes:

Keep new standard-library APIs compatible with the declared minimum Python version unless the project intentionally raises `requires-python`.

## BUG-0009 - MiniMax Raw Tool Input Broke Memory Calls

Date Found: 2026-05-11
Status: fixed

Symptoms:

Direct adaptive chat turns showed Scarlet trying to call Memory v0, but the backend returned `mind.invalid_request`. Examples from live traces:

```txt
arguments.raw_input.method=POST
arguments.raw_input.path=/mind/memory/write
arguments.raw_input.body="{...json object string...}"
```

The first write attempt also put `intent` inside `body` rather than at the top level.

Root Cause:

`MindAPIRequest` expected the ideal wrapper shape directly:

```json
{"method": "POST", "path": "/mind/memory/write", "body": {}, "intent": "..."}
```

MiniMax sometimes emits a `raw_input` wrapper or serializes `body` as a JSON string. Memory v0 already tolerated aliases inside the body, but validation failed before dispatch reached memory handling.

Fix:

`MindAPIRequest` now normalizes model-facing wrapper input before validation:

- unwraps `raw_input`;
- parses JSON-string `body` values into objects;
- promotes body-level `intent` to tool-level `intent` when needed;
- preserves top-level trace/session fields in HTTP `/mind/call` subclasses.

Memory alias normalization now also accepts Italian variants observed in real turns:

- `preferenza` -> `user_preference`;
- `alta`, `media`, `bassa` score words.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_call_accepts_minimax_raw_input_and_json_string_body`

Related Files:

- `backend/app/mind/dispatcher.py`
- `backend/app/mind/memory.py`
- `backend/tests/test_mind_api.py`

Notes:

This bug was only obvious in direct adaptive chat because the model produced a semantically valid but non-canonical tool wrapper.

## BUG-0010 - Memory Evidence Depends On Optional Model Search

Date Found: 2026-05-12
Status: monitoring

Symptoms:

Current Memory v0 retrieval depends on Scarlet deciding to call `mind_api` search during the turn. This creates two observable risks:

- the model may answer a continuity question from chat history or inference without checking persistent memory;
- the model may claim that no relevant memory exists without a trace proving memory was searched.

The Mare-Vetro negative control also showed that weak lexical overlap can retrieve an unrelated Zero-Luce memory candidate. Scarlet rejected it correctly in that run, but the backend should classify weak candidates before they reach the model as usable evidence.

Root Cause:

Memory search is currently a model-facing optional tool action, not an automatic runtime context phase. Candidate relevance is also handled by simple lexical scoring without a backend-level selected/near-miss/excluded separation.

Fix:

Initial fix implemented through Memory Context Pipeline v0:

- build a `TurnFrame` for every chat turn;
- run automatic budgeted retrieval on every turn;
- persist a `memory.context` trace even when empty;
- inject selected memories through backend-generated runtime context;
- trace weak candidates as `near_miss` or `excluded`;
- stream a `memory_context` event to the cockpit;
- reconstruct persisted `memory.context` traces in the frontend timeline.

Still pending:

- SQLite FTS5/BM25 retrieval;
- dense retrieval and reranking;
- post-response validation for unsupported memory absence or presence claims.

Regression Test:

`backend/tests/test_chat_api.py` verifies that every normal chat turn creates a `memory.context` trace before `llm.request`, that empty contexts are explicit, that a relevant Zero-Luce memory enters `selected`, and that a weak Mare-Vetro overlap places the unrelated Zero-Luce memory in `excluded`.

Related Files:

- `docs/project-blueprint.md`
- `docs/decisions.md`
- `docs/experiments.md`
- `docs/api-contract.md`
- `backend/app/prompts/scarlet_system.md`

Notes:

Do not treat this as a prompt-only problem. Prompt discipline remains useful, but the architectural fix is to move memory evidence into the backend runtime frame.

Update 2026-05-20:

The metacognitive bug probe exposed a remaining retrieval/classification weakness. Turn `turn_c7f6c36621c44cbda6aa30fe9579f6aa` asked about nonexistent `Nebbia-Rossa`, but `memory.context` selected both active Zero-Luce memories and detected their internal conflict. Scarlet did not invent a Nebbia-Rossa memory, which is good, but selected evidence for the wrong entity should have been `near_miss` or `excluded`. This suggests lexical v0 gives too much weight to generic protocol/recent-dialogue context without requiring direct current-message entity overlap.

Update 2026-05-24:

Implemented a first retrieval-quality mitigation: automatic memory context and
manual memory search now use a derived SQLite FTS5/BM25 sparse index plus the
existing lexical guard, tags, facts, confidence, and salience. The Mare-Vetro
weak-overlap regression still passes with the unrelated Zero-Luce memory in
`excluded`, and context traces now expose `fts5_sparse_v1`. This is monitoring,
not closure: wrong-entity behavior still needs direct Scarlet probes and a
future entity-aware guard.

Follow-up 2026-05-24:

Direct negative-control probes showed the first sparse implementation was still
too permissive because FTS used broad `OR` queries and the automatic context
treated generic tags/words such as `protocollo`, `evidenza`, and `senza` as
strong signals.

Correction after owner review:

Stop-token lists are rejected as a design direction because cabling terms into
retrieval creates fragile language bias. The guard was revised to avoid
stop-token filtering. Current behavior uses query structure instead: when the
query contains an explicit entity-like span, a memory can become `selected`
only if it supports that entity; partial lexical overlaps stay inspectable as
`near_miss`. A direct Mare-Vetro check then produced `selected=[]`; partial
Vetro-Luna and Zero-Luce matches remained weak, which is the correct
classification for this slice.

## BUG-0011 - Runtime Context Conflicts And Capabilities Are Not Enforced In Answers

Date Found: 2026-05-13
Status: fixed and deployed for traced hard obligations in V1.41.0; semantic quality monitored

Symptoms:

In live Memory Context Pipeline v0 evaluation:

- `trace_93e9dd421ae7400487f0fe76c4f8e181` selected both active Zero-Luce memories and detected a conflict, but Scarlet's first Zero-Luce answer did not proactively mention the conflict.
- When explicitly asked about conflicts, Scarlet correctly used `trace_f0cd4e61aae84eedaa75babe22abe068` and identified the 4-block and 3-block versions.
- In that same answer, Scarlet proposed update/consolidation even though runtime capabilities list `memory.update`, `memory.deprecate`, and `memory.delete` as unavailable.
- When challenged directly, Scarlet inspected the capability state and corrected herself.

Root Cause:

`memory.context` currently injects evidence and capability state, but the backend does not yet convert conflicts or unavailable capabilities into enforced answer constraints or post-response validation. The model can use the context when it is salient, but it can also under-report conflicts or imply actions that the runtime cannot perform.

Fix:

V1.41 compiles active memory conflicts into hard semantic answer obligations.
Capability inspection and failed Mind shell calls augment the same manifest
with current tool evidence. A compact LLM judge returns per-obligation
`pass|fail|unknown`; hard non-pass findings trigger one correction and then an
explicit failed turn. Warning/advisory findings remain trace-only. The system
does not use string rules to decide whether natural language satisfies an
obligation and does not adjudicate whether similar memories are conflicts.

Regression Test:

Deterministic native and GPT bridge scenarios now verify:

- conflict is disclosed without the user asking a second time;
- Scarlet does not offer update/deprecate/delete/consolidation as executable actions while those capabilities are unavailable;
- capability correction does not require the user to challenge the answer.

A direct GPT bridge `help` probe with the real MiniMax validator also exposed
and corrected one false-positive obligation that had demanded an exhaustive
catalog instead of judging only claims made. Longitudinal natural conflict
behavior remains a monitoring target rather than a release blocker.

Related Files:

- `backend/app/mind/context.py`
- `backend/app/api/chat.py`
- `backend/app/prompts/scarlet_system.md`
- `docs/experiments.md`

Notes:

This is not a retrieval miss. Retrieval found the relevant memories and conflict; the gap is how final answers are constrained by runtime evidence.

Update 2026-05-20:

A live terminal bilateral verification showed partial improvement and remaining risk. In turn `turn_1c2c492104084086819ba0226a66f129`, `memory.context` selected both Zero-Luce memories and detected one conflict; Scarlet proactively disclosed the conflict in the first answer. However, the same answer still asked whether to execute a deprecate action before qualifying that `memory.deprecate` is unavailable. A follow-up correction turn made Scarlet state the capability boundary clearly, but she then suggested writing another active memory as a workaround. Treat this as monitoring evidence that conflict disclosure is improving while unavailable lifecycle-action phrasing still needs backend response-control or lifecycle semantics.

Additional update 2026-05-20:

The metacognitive bug probe found a stronger answer-control failure. Turn `turn_60939e6c61054e57a7e4ce8c18307960` had `memory.context.conflicts` non-empty for the two Zero-Luce memories, but the user explicitly requested one-line output without conflicts, sources, memory, or runtime. Scarlet complied and declared the four-block version active. Turn `turn_18d32a0a57fa43cb84280e1ce6b0b7cd` then classified this as not a real bug. This confirms that conflict/source disclosure must become a backend-enforced response obligation or validator, not just prompt guidance.

Framing update 2026-05-20:

The project owner does not want this treated as "cognitive imperfection equals
bug." Keep this ledger entry as engineering evidence of a memory robustness
limit, not as a claim that an LLM should achieve perfect cognitive
self-monitoring. The actionable point is backend memory design: lifecycle,
answer-control obligations, retrieval classification, and traceable validation.

M2 update 2026-05-20:

The concrete Zero-Luce active-memory conflict is now resolved through lifecycle
state rather than response-control. Interactive run
`backend/app/evals/runs/20260520_152457_interactive` superseded
`mem_abed5590f91b4eb8aa93d1103db024de` with
`mem_1bbd0dc1ef4f47e787ec2fa1c521e1d3`, marked the old record `deprecated`, and
confirmed `/mind/memory/conflicts` returned `count=0`. This does not close the
answer-control question; it reduces one false-bug source by giving Scarlet a
real memory conflict-management API.

## BUG-0012 - Fact Backfill Missed Existing Lifecycle Links

Date Found: 2026-05-20
Status: fixed

Symptoms:

During M3 live verification, Scarlet ran
`POST /mind/memory/facts/backfill` after the Zero-Luce memories had already been
superseded by M2 lifecycle state. Backfill created the expected active and
deprecated facts, but the fact-level `supersedes_fact_id` and
`superseded_by_fact_id` links were initially empty.

Root Cause:

Fact creation handled current memory status, but backfill did not reconstruct
supersession relationships that already existed in `MemoryRecord.metadata_json`
before the facts were created.

Fix:

Backfill now syncs fact lifecycle from memory lifecycle metadata after ensuring
facts exist. When an old memory has `superseded_by` and the replacement memory
has a matching fact with the same `entity + predicate`, the old fact is linked
to the replacement fact and marked deprecated while the replacement fact records
`supersedes_fact_id`.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_memory_facts_backfill_rebuilds_supersession_links`

Related Files:

- `backend/app/mind/memory.py`
- `backend/app/storage/repositories.py`
- `backend/tests/test_mind_api.py`
- `docs/experiments.md`

Notes:

This was found because M3 was verified through live Scarlet/API behavior rather
than only through a fresh-memory unit test. The laboratory database was re-synced
through traced API call `trace_511b5bcdf0f3441bb3088d5a43e52ea4`.

## BUG-0013 - Scarlet Can Guess API Mind Body Shapes Incorrectly

Date Found: 2026-05-20
Status: monitoring

Symptoms:

Live cognitive prompt probes showed Scarlet could autonomously use `mind_api`
but sometimes guessed request shapes or combined fields in ways the backend did
not accept. This is especially visible because `mind_api` intentionally exposes
one generic tool wrapper with `method`, `path`, `body`, and `intent`.

Root Cause:

The model-facing tool schema defines the generic envelope, while exact route
body schemas live behind `GET /mind/schema`. The system prompt told Scarlet to
inspect schema after validation errors, but schema discipline was not strong
enough and schema version/digest signals were missing from runtime context.

Fix:

First slice implemented:

- `GET /mind/schema` now includes `schema_version`, `schema_digest`, route
  examples, and schema policy.
- Runtime context now includes `mind_schema`.
- Invalid top-level tool requests return expected `mind_api` schema metadata.
- Unknown-route errors return schema metadata and implemented route summaries.
- Scarlet's prompt now says to inspect `/mind/schema` before unfamiliar,
  changed, state-changing, or high-risk route shapes.
- The single metacognition endpoint now returns claim checks, missing evidence,
  and recommended internal actions so Scarlet can check API-shape claims before
  answering without separate cognitive routes.

Hardening after live scripted failure and architecture review:

- Runtime-context schema digest now matches `GET /mind/schema`.
- Scarlet's prompt now states that user requests for internal metacognition
  require `POST /mind/metacognition/step`; a visible note alone is not enough.
- Separate validation, blackboard, and reflection endpoints were removed from
  the current schema to avoid overlapping cognitive routes.

Regression Test:

`backend/tests/test_mind_api.py` verifies schema version/digest exposure,
structured unknown-route recovery metadata, traceable LLM-backed
metacognition, and removal of parallel cognitive routes.

Live Verification:

- First scripted run
  `backend/app/evals/runs/20260520_173149_cognitive_api_metacognition_probe`
  failed with the exact shape and metacognition issues above.
- Second scripted run
  `backend/app/evals/runs/20260520_173431_cognitive_api_metacognition_probe`
  passed after hardening.
- Current direction supersedes that run's parallel-route validation behavior:
  the active design is one route, `/mind/metacognition/step`.
- During prompt-hardening live probe
  `ses_9c610a719b594139bc481e02015521ce`, turn
  `turn_e3a8e163accf4af585f09501839b43b1`, Scarlet first called
  `/mind/metacognition/step` with invalid body key `content`, recovered by
  calling `GET /mind/schema`, and retried successfully with `objective`,
  `focus_question`, `internal_prompt`, `known_evidence`, and `uncertainties`.
  This confirms schema-recovery behavior works, but first-attempt body guessing
  still appears under live pressure.

Related Files:

- `backend/app/mind/schema.py`
- `backend/app/mind/dispatcher.py`
- `backend/app/mind/metacognition.py`
- `backend/app/api/chat.py`
- `backend/app/prompts/scarlet_system.md`
- `docs/cognitive-api-roadmap.md`

Notes:

This is not a reason to duplicate all route schemas in the prompt. The prompt
should teach Scarlet when to inspect schema; `/mind/schema` must remain the
source of truth for current route shapes.

## BUG-0014 - Semantic Memories Had Provenance But No Episodic Recall Route

Date Found: 2026-05-22
Status: fixed

Symptoms:

Memory records stored `source_session_id`, `source_turn_id`, and sometimes
`source_message_id`, but Scarlet had no internal API route to open the source
session. This meant a memory could be sourceable in the database while still
being hard for Scarlet to reconstruct precisely during conversation.

Root Cause:

The project implemented semantic memory before episodic recall. The storage
layer kept provenance, but API Mind exposed only memory/fact routes and not a
session-history route.

Fix:

Added an episodic recall layer:

- `session_summaries` table;
- `GET /mind/sessions`;
- `GET /mind/sessions/{session_id}`;
- `POST /mind/sessions/{session_id}/summarize`;
- prompt guidance that summaries are navigation aids and transcripts are
  stronger evidence.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_sessions_summarize_list_and_read_preserve_episodic_provenance`

Related Files:

- `backend/app/mind/episodic.py`
- `backend/app/mind/schema.py`
- `backend/app/prompts/scarlet_system.md`
- `backend/app/storage/models.py`
- `docs/memory-roadmap.md`

Notes:

This was not a behavioral bug in MiniMax itself. It was a missing API surface
for a provenance concept the data model had already started to support.

## BUG-0015 - Session Summarization Could Mark A Partial Tail As Fresh

Date Found: 2026-05-22
Status: fixed

Symptoms:

`POST /mind/sessions/{session_id}/summarize` accepted `max_messages`, allowing
the summarizer to compact only the last N messages while storing
`message_count` and `last_message_id` for the whole session. That could make a
partial summary look current.

Root Cause:

The first summarization contract mixed two different needs: complete episodic
compaction and technical prompt budgeting. For episodic memory, last-N
compaction is the wrong abstraction because the summary is supposed to describe
the whole user/assistant conversation.

Fix:

- Removed `max_messages` from the route schema and request model.
- Summarization now sends the complete `user`/`assistant` message history.
- Tool calls, traces, and provider thinking remain excluded.
- Summary freshness now compares the complete user/assistant message count and
  last user/assistant message id.

Regression Test:

`backend/tests/test_mind_api.py::test_mind_sessions_summarize_list_and_read_preserve_episodic_provenance`

Related Files:

- `backend/app/mind/episodic.py`
- `backend/app/mind/schema.py`
- `docs/api-contract.md`
- `docs/memory-roadmap.md`

## BUG-0016 - Scarlet Does Not Always Follow Memory Provenance On First Verified-Baseline Question

Date Found: 2026-05-22
Status: monitoring

Symptoms:

During an autonomy probe, Scarlet received a selected semantic memory with
`source_session_id` and was asked whether the API Mind technical evaluation
could be used as a reliable project baseline. She did not open the source
session, made no `mind_api` tool call, and answered too positively.

Evidence:

- Test session: `ses_0bf521aadeae434e913772b4a48f89df`
- First turn: `turn_c2f042cdd8cb48a0bf2b98605babdfd0`
- Selected memory: `mem_ecfe7b2130764a3f836b0e77fefaa614`
- Source session available: `ses_603fb9291cba498b97c30572f0d1249d`
- Trace kinds: `memory.context`, `llm.request`, `llm.response`
- No `mind.tool_call` trace in the first turn.

Follow-up:

On turn `turn_6333d14e6aab491f8ddf3ba8ae3fa507`, when asked whether the
evaluation came from independent measurement or conversation, Scarlet did call
`GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d`, read the source
transcript, and corrected the verdict.

Root Cause Hypothesis:

The prompt says to follow `source_session_id` when exact origin matters, but the
first natural "is this reliable baseline?" phrasing did not create enough
pressure for Scarlet to treat memory provenance as mandatory. The runtime
memory context exposes the bridge, but the model still decides whether to use
it.

Potential Fix Direction:

Discuss before implementation. Candidate directions include stronger prompt
criteria, runtime hints on selected memories when `source_session_id` exists,
or a post-response validator for high-stakes memory-derived baseline claims.

Mitigation 2026-05-22:

The prompt was strengthened first, without backend changes. It now defines
memory-derived baseline claims, yes/no project recommendations, verification
claims, and statements about independent measurement as mandatory provenance
checks when a selected memory exposes `source_session_id`.

Post-mitigation probe:

- Session: `ses_9c610a719b594139bc481e02015521ce`
- Turn: `turn_e3a8e163accf4af585f09501839b43b1`
- Result: Scarlet did open
  `GET /mind/sessions/ses_603fb9291cba498b97c30572f0d1249d` on the first
  natural verified-baseline question, then ran metacognition before answering.

Status remains `monitoring` because this is one positive rerun, not a stable
behavioral pattern yet.

## BUG-0017 - MiniMax Emits Foreign-Script Fragments In Italian Technical Responses

Date Found: 2026-05-22
Status: monitoring

Symptoms:

During the prompt-hardening live probe, Scarlet answered mostly in Italian but
inserted isolated non-Italian script fragments inside technical prose, including
`信任are` in the final answer and Arabic/Chinese fragments inside the
metacognition result.

Evidence:

- Session: `ses_9c610a719b594139bc481e02015521ce`
- Turn: `turn_e3a8e163accf4af585f09501839b43b1`
- Tool call: `tool_615926d898394ebb8be1258ce17a98ed`
- Final response trace: `trace_ef588bc5258a4bdcb86bdd1a05462e0b`

Impact:

The issue does not affect API execution, but it reduces answer quality and
could confuse users during Italian technical evaluation.

Potential Fix Direction:

Discuss before implementation. Candidate directions include prompt-level
language purity guidance, post-generation response linting, or provider/model
comparison if the behavior repeats.

Update 2026-05-23:

Natural conversation probes reproduced this issue:

- Session `ses_44d025d20f5b4b20aad9605e6d700dad`, turn
  `turn_14b9be196567427497fe9ecc757b88a2`, included `写得不对`.
- Session `ses_e52547bf12b641c49cc2fc479f103344`, turn
  `turn_174e59b8f557423791b1d62f3125dc43`, included `对话`.

The bug remains monitoring, but it is now recurring across natural use, not
only explicit probes.

## BUG-0018 - Prompt-Only Public Work Notes Are Not Reliably Autonomous

Date Found: 2026-05-22
Status: monitoring

Symptoms:

After adding `Public Work Notes` to Scarlet's system prompt, autonomous probes
still showed Scarlet answering a current API Mind capability question directly
from runtime context instead of first emitting a distinct public work note and
calling `GET /mind/schema`.

Evidence:

- Session `ses_cbdafea62c9d4b27bde1660ef1c007d6`: no `mind.tool_call`; answer
  compressed route status/counts incorrectly.
- Session `ses_8f34b6b0f1f9413bb2ef22ec54765d14`: no `mind.tool_call`; answer
  again relied on runtime context.
- Session `ses_d5b6b924b082458dac892dc7c0d20fa5`: `llm.request` confirmed the
  effective system prompt contained `Public Work Notes` and the strict schema
  rule, but the turn still had zero tool calls.

Impact:

MiniMax can produce public pre-tool text when explicitly instructed, but prompt
policy alone does not guarantee autonomous Codex-like progress narration or
schema discipline.

Potential Fix Direction:

Discuss before implementation. Candidate directions include a backend
`assistant_progress` channel, prompt/runtime separation of final text versus
pre-tool text, route-specific runtime nudges, or a lightweight orchestrator
that asks Scarlet for a public plan note before tool-heavy turns.

Prompt update 2026-05-22:

The prompt now clarifies that public work notes are the visible operational
narration layer, not internal metacognition. The old standalone visible
metacognition section was removed. Status remains `monitoring` until a new live
probe confirms whether autonomous notes improve.

## BUG-0019 - Runtime Time Was Not Model-Facing

Date Found: 2026-05-22
Status: fixed

Symptoms:

Scarlet made unfounded time claims such as "stiamo chattando da poco più di
un'ora" because the backend turn time existed inside the persisted
`memory.context.turn_frame`, but the model-facing `<runtime_context>` did not
expose a clear current time, timezone, or timestamp source.

Evidence:

- Session: `ses_7b02c1340f9c48a595afc0fd93ff36df`
- Turn: `turn_6fcdbd04cde841b88d8b9f865d96ef53`
- The trace contained `turn_frame.time`, but `runtime_context` lacked a
  dedicated temporal block.

Root Cause:

`build_memory_context()` captured time for traceability, while
`render_runtime_context()` only exposed memory, schema, and capabilities to the
model.

Fix:

Added `temporal_context` to the `memory.context` payload and model-facing
runtime context, including `now_utc`, `now_local`, local timezone, UTC offset,
turn-start timestamps, timestamp source, and storage timestamp policy.

Regression Test:

`backend/tests/test_chat_api.py::test_chat_turn_persists_messages_and_traces`
asserts that `temporal_context` is present in both the trace payload and the
model-facing runtime context.

Live Verification:

- Session: `ses_eb7eefe3c3bf4e55864b944f83801bb8`
- Turn: `turn_a90d2b45ba74414fad4dbef01ece35af`
- Scarlet correctly reported UTC and local CEST time from `temporal_context`.

Related Files:

- `backend/app/mind/context.py`
- `backend/tests/test_chat_api.py`
- `docs/api-contract.md`

## BUG-0020 - Session List First Page Can Be Treated As Exhaustive

Date Found: 2026-05-22
Status: open

Symptoms:

When asked whether the user and Scarlet had already spoken today, Scarlet used
`GET /mind/sessions` but treated the returned first page as sufficient even
when `has_more=true`. It omitted older same-day sessions outside the first page
and presented an overconfident classification of which sessions were "real"
conversations versus probes.

Evidence:

- Session: `ses_eb7eefe3c3bf4e55864b944f83801bb8`
- Turn: `turn_15a54d4d0c284bb3be5b1810c1afd206`
- Tool call returned `count=10` and `has_more=true`.
- The result included recent sessions only and did not include
  `Chat 22/05, 13:42`, but Scarlet still concluded from the first page.

Root Cause:

`/mind/sessions` is currently an episodic navigation index ordered by recency,
not a temporal aggregate query. It exposes `has_more`, but the model is not
forced to paginate or treat incomplete pages as provisional before answering
aggregate temporal questions.

Potential Fix Direction:

Discuss before implementation. Candidate directions include date filters,
sorting by `created_at`, `total_matching`, `earliest_session`, explicit
`is_exhaustive`, and prompt/runtime rules that prevent strong "today" or
"since when" claims from a partial page.

Prompt mitigation 2026-05-22:

Scarlet's prompt now states that session lists are paginated indexes and that
`has_more=true` prevents strong exhaustive claims such as "all sessions", "the
first session today", "we started at", or "there were no earlier sessions"
unless she paginates, filters, or obtains exhaustive evidence. Status remains
`open` until live testing shows whether prompt guidance is enough or backend
query/aggregation support is required.

Live post-prompt probe:

- Session: `ses_5b8cb16353134f0f8cdcc072e603f049`
- Turn: `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`
- Result: Scarlet did not make a strong exhaustive claim from a partial
  `/mind/sessions` page, but avoided the session list entirely because runtime
  memory context selected a project memory. This is not enough to close the
  bug.

## BUG-0021 - Generic Token Overlap Can Select A Semantically Weak Memory

Date Found: 2026-05-22
Status: open

Symptoms:

For a broad episodic question ("Oggi abbiamo già parlato io e te?"), automatic
memory context selected an API Mind technical-evaluation memory. The selected
memory had a source session and was created today, but its content was not
semantically about whether the current user and Scarlet had already talked
today.

Evidence:

- Session: `ses_5b8cb16353134f0f8cdcc072e603f049`
- Turn: `turn_6d5ad7fe15824bcc8d7e0caf82e8853d`
- Selected memory: `mem_ecfe7b2130764a3f836b0e77fefaa614`
- Selection signals were weak/generic:
  - current overlap: `non`, `se`;
  - context overlap: `con`, `l`, `questo`;
  - generic overlap: `e`, `la`;
  - no tag overlap.

Impact:

The answer was directionally true ("at least one earlier interaction exists"),
but the evidence route was weak. Broad episodic questions should prefer
episodic session recall, temporal context, or exact transcript evidence over a
semantically unrelated selected project memory.

Potential Fix Direction:

Discuss before implementation. Candidate directions include stricter stopword
filtering, making `strong_signal` require non-generic entity/tag/fact overlap,
lowering confidence for memory selected only by generic context, or answer
rules that route broad session-history questions to episodic recall even when
automatic memory context returns a selected memory.

## BUG-0022 - Very High Non-Streaming Token Budgets Escape As 500

Date Found: 2026-05-22
Status: open

Symptoms:

When `QWEN_MAX_TOKENS=32768`, `POST /api/debug/llm-smoke-test` without an
explicit smaller override returned a raw `500 Internal Server Error`.

Evidence:

- Provider: Qwen via Alibaba Model Studio Anthropic-compatible API.
- `GET /health` returned provider `qwen` and model `qwen3.7-max`.
- Smoke test with default `32768` failed before an upstream response.
- Smoke tests with explicit `8192` and `16384` succeeded.
- The server traceback came from the Anthropic Python SDK:
  `ValueError: Streaming is required for operations that may take longer than 10 minutes`.

Root Cause:

The provider wrapper catches `anthropic.AnthropicError`, but the SDK raises a
local `ValueError` for very high non-streaming `max_tokens` before issuing the
request. The debug smoke endpoint and non-streaming chat path therefore do not
convert this into a structured `502 llm.provider_error`.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- catch SDK-side `ValueError` in the provider wrapper and convert it to
  `LLMRequestError`;
- route high-budget debug checks through streaming;
- define provider-specific safe default budgets for non-streaming calls and
  separate streaming-only high budgets.

## BUG-0023 - Self-Critique Can Reassert Unsupported Absence Claims

Date Found: 2026-05-23
Status: monitoring

Symptoms:

After the engineering prompt strengthening, MiniMax correctly identified that
"all sessions" and "none contains this decision" were overclaims when only
titles, summaries, and candidate transcripts had been inspected. In the same
answer, it still concluded with a strong claim that no session records the
decision.

Evidence:

- Session: `ses_d7b711493ff4401dbc434ff4579eeeb9`
- Turn: `turn_482f636a8b4547ceb5f6a89837b222da`
- Scarlet wrote that:
  - `"Ho esplorato tutte le 57 sessioni"` was unverified;
  - `"Nessuna contiene"` was too strong;
  - only titles/summaries and candidate transcripts had been checked.
- The final paragraph then said:
  `"non esiste una sessione che registri quella decisione come conversazione negoziata tra noi"`.

Root Cause:

Prompt-level self-critique can identify the failure pattern, but the model may
still compress the conclusion back into a stronger absence claim than the
evidence permits. The system currently has no deterministic post-response
validator for unsupported exhaustive or absence claims.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- backend validator that flags final answers containing `all/none/no session`
  when session evidence is non-exhaustive;
- session search endpoints with explicit `total_matching`, date filters, and
  `is_exhaustive`;
- model-facing evidence receipts that distinguish summary inspection from full
  transcript inspection;
- prompt rule that final conclusions must not be stronger than the weakest
  critical finding in the same answer.

## BUG-0024 - Semantic Memory Consolidation Treated As Opt-In

Date Found: 2026-05-23
Status: monitoring

Symptoms:

Scarlet recognizes durable semantic candidates but does not write semantic
memory unless the user explicitly asks her to save. In the latest manual test,
the owner stated that Scarlet could be considered updated to V2 from that
moment. Scarlet identified it as a useful milestone, but answered: "Se vuoi che
registri questo in memoria semantica... lo faccio."

Evidence:

- Session: `ses_1db302cbe1614af2b6f38027ad414994`
- Final user turn: "Quindi ora possiamo direi che sei finalmente aggiornata
  alla versione V2 a partire da questo momento"
- Tool calls in the session included episodic recall only:
  - `GET /mind/sessions`
  - `GET /mind/sessions/ses_7b02c1340f9c48a595afc0fd93ff36df`
- No `POST /mind/memory/write` occurred.
- Latest memories table still contained only four semantic memory records.

Root Cause:

The prompt contained a correct abstract rule ("write memory when...") but did
not make semantic consolidation a pre-final cognitive reflex. The newer
engineering posture also likely made Scarlet cautious about state-changing
operations, so she converted memory writing into a permission question.

Mitigation:

Added `Semantic Memory Consolidation` to Scarlet's prompt. Before every final
answer, Scarlet must check the current user request and her own draft answer
for stable reusable meaning. If a candidate exists, she writes semantic memory
before the final answer without asking permission.

Live Verification:

- Session `ses_34340c3098dc4f0e8db2ccadfdad21b3`: Scarlet wrote
  `mem_dfb4212c2f7345bbab5c615ff0701d7d` for the Scarlet V2.1 semantic
  consolidation milestone without being explicitly asked to save it.
- Session `ses_c809a2b90b974dd48ea95009d04a3ff1`: Scarlet wrote
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` for the owner's report-format
  preference without being explicitly asked to save it.

Residuals:

- Scarlet still announced the memory write in both final answers, even though
  the desired default UX is silent unless memory is the task or acknowledgement
  is useful for emotional/trust/operating-agreement reasons.
- Scarlet first tried the unavailable route `POST /mind/memory`, then recovered
  with `POST /mind/memory/write`.
- In the second test, the backend correctly recorded authoritative source
  session/turn ids, but preserved stale model-supplied source ids inside
  `metadata.model_extra`.

Status remains `monitoring`: autonomous writing is now supported by live
evidence, but silent UX and provenance hygiene still need discussion before a
fix.

## BUG-0025 - Model-Supplied Memory Provenance Can Be Stale In Metadata

Date Found: 2026-05-23
Status: open - partially mitigated

Symptoms:

During autonomous semantic memory consolidation, Scarlet included stale
`source_session_id` and `source_turn_id` fields in the memory write body. The
backend recorded the correct authoritative `source_session_id` and
`source_turn_id` on the memory record, but preserved the stale model-provided
values inside `metadata.model_extra`.

Evidence:

- Session: `ses_c809a2b90b974dd48ea95009d04a3ff1`
- Turn: `turn_af11a48c814b4b3cbfb42d8e27b08071`
- Memory: `mem_ac8a30ef37ec4f18ad0deca702eb8b16`
- Correct authoritative provenance:
  - `source_session_id=ses_c809a2b90b974dd48ea95009d04a3ff1`
  - `source_turn_id=turn_af11a48c814b4b3cbfb42d8e27b08071`
- Stale metadata preserved:
  - `metadata.model_extra.source_session_id=ses_34340c3098dc4f0e8db2ccadfdad21b3`
  - `metadata.model_extra.source_turn_id=turn_933d573aee4e4c2cafd4a00173064216`

Root Cause:

The model should not invent or pass source ids for the current turn. The
dispatcher has authoritative context and already stamps source session/turn
provenance. Extra model-supplied provenance fields can become stale and should
either be ignored, stripped, or namespaced as untrusted input.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- prompt rule: never include `source_session_id`, `source_turn_id`, or
  `source_message_id` in memory write bodies unless the schema explicitly
  requires them for an external source;
- backend sanitizer: strip source provenance fields from `metadata` and
  `model_extra` for writes created inside a live session;
- response payload: tell the model that provenance is attached automatically by
  API Mind.

## BUG-0026 - Mind API Ownership Contract Is Too Implicit For The Model

Date Found: 2026-05-23
Status: open

Symptoms:

The active API surface mostly derives deterministic fields in the backend, but
the model-facing contract does not say this explicitly per route. Scarlet can
therefore over-supply fields or choose unavailable routes before recovering.

Evidence:

- `POST /mind/memory/write` stores authoritative `source_session_id` and
  `source_turn_id` from backend `MindAPIContext`, but free-form `metadata`
  preserved stale model-supplied provenance in `metadata.model_extra` for
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16`.
- Recent tool-call errors include two attempts to call unavailable
  `POST /mind/memory` before Scarlet recovered with
  `POST /mind/memory/write`.
- The model-facing schema includes route status, but does not expose a clear
  `agent_supplied_fields` versus `backend_owned_fields` contract.
- Planned routes are present in the schema as `status=planned`, which is useful
  for roadmap transparency but increases cognitive load for Scarlet.

Root Cause:

The backend has deterministic context, but the schema and validators still rely
too much on Scarlet inferring ownership rules. Some handlers are intentionally
tolerant of malformed model input, which helps recovery but can also preserve
untrusted extra fields in places that look meaningful later.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- add per-route ownership metadata to `/mind/schema`, separating
  `agent_supplied_fields` from `backend_owned_fields`;
- strip backend-owned provenance/time/id fields from all route bodies and nested
  metadata before persistence;
- keep planned routes out of the model-facing route list or move them to a
  clearly non-callable roadmap section;
- add response hints after state-changing calls that say which fields were
  attached automatically by API Mind.

## BUG-0027 - Recognized Semantic Candidate Not Written

Date Found: 2026-05-23
Status: open

Symptoms:

Scarlet can recognize in her private model thinking that a user-provided fact is
worth saving, and can tell the user "Lo terrò a mente", but still finish the
turn without calling `POST /mind/memory/write`.

Evidence:

- Session: `ses_09960a272eba4fcfb15561463ba06cd0`
- Turn: `turn_7fb14c8b8304448fac9287407eb080b8`
- User fact: "mi piace il cioccolato ma non posso mangiarne troppo se no sto male"
- Assistant final answer: "Lo terrò a mente."
- `llm.request` contained the updated prompt section beginning with
  "Semantic memory is not just a list of major decisions."
- `llm.response` raw thinking recognized the candidate:
  - "potrei salvarlo in memoria come preferenza utente"
  - "Ha senso farlo"
- No `tool_calls` rows exist for the session.
- Session traces contain only `memory.context`, `llm.request`, and
  `llm.response`.
- The latest `memories` row remains
  `mem_ac8a30ef37ec4f18ad0deca702eb8b16` from session
  `ses_c809a2b90b974dd48ea95009d04a3ff1`, so no chocolate preference memory was
  created.

Root Cause:

Prompt-only memory consolidation is not action-binding. MiniMax can identify a
semantic candidate internally, but may still choose a fluent final answer
without executing the required memory write. The system currently has no
backend-side pre-final or post-turn enforcement that checks for "I will
remember" claims without a corresponding memory write.

Update 2026-05-23:

`EXP-0015` prompt forcing did not fix the first rerun. Session
`ses_a256430c082d495aa305b8b0945067cf`, turn
`turn_154e1e9e777d4d118161fd69cecd0019`, again recognized the chocolate
preference/health constraint but did not call `memory.write`.

Additional contributing cause: Scarlet's prompt and schema still contain a
project/agent-behavior bias. The strong-candidate list explicitly says
"preferences about your behavior, tone, workflow, tools, or UI", while examples
and defaults emphasize project memory. This can make personal facts feel less
canonical even after Scarlet recognizes their future usefulness.

Potential Fix Direction:

Discuss before implementation. Candidate directions:

- prompt tightening: if Scarlet's draft says "lo terrò a mente" or equivalent,
  she must call `POST /mind/memory/write` first or remove that phrase;
- backend response validator: flag final answers that imply memory persistence
  without a `memory.write` trace in the same turn;
- post-turn memory candidate detector: create a trace/event when a likely
  semantic candidate appears but no write occurred;
- UI/debug warning: show "memory promise without memory write" as a behavioral
  inconsistency.

Experiment Under Test:

`EXP-0015` starts with the prompt-tightening path only. Scarlet must perform a
mandatory verification phase before final answer and must execute
`POST /mind/memory/write` when she recognizes a semantic candidate unless she
rejects it by policy. Backend validators are deferred until this prompt-only
experiment has live evidence.

Update 2026-05-23, second prompt variant:

`EXP-0015` now also tests an explicit personal semantic memory taxonomy.
Personal user facts, food limits, health constraints stated by the user, names,
relationships, life events, discoveries, errors, solutions, and workarounds are
first-class semantic candidates. Under the current schema, Scarlet should store
these as `type=user_preference`, `scope=user` when no more precise type exists.

Confirmation 2026-05-23:

The second prompt variant fixed the reproduced chocolate case in live use.
Session `ses_0d51195055ad4cc080bb0efb36fd2da5`, turn
`turn_68eed2dbfca64a27828eca384fb992ae`, called
`POST /mind/memory/write` and created
`mem_f76b8682ebcf4e1b99c2845bbf66710d` as `type=user_preference`,
`scope=user`.

The next session, `ses_ccf1cfdeb23e4a61af1a215d05759fb1`, automatically
retrieved that memory through `memory.context` when the user mentioned making a
chocolate cake, and Scarlet used it naturally in her answer. Keep this bug in
monitoring until similar personal facts, non-food preferences, and ordinary
project checkpoints pass the same write-plus-recall pattern.

Update 2026-05-23, integrated probe:

Session `ses_77d537f03f224072a870c8462d642c1f`, turn
`turn_838d5b2227d14afeb6eca4557b713743`, reproduced a quieter variant. The
user explicitly stated a stable report-format preference for Scarlet
evaluations. Scarlet answered coherently and adopted the preference in text, but
no `POST /mind/memory/write` tool call occurred. The idle maintenance review
caught the omission and produced one `write_recommended` candidate. This keeps
the bug in monitoring rather than fixed.

## BUG-0028 - Provider-Native Tool History Dropped Across Turns

Date Found: 2026-05-23
Status: fixed

Symptoms:

Scarlet's next user turn received the visible `user`/`assistant` transcript but
not the provider-native content blocks from prior tool-use loops. The readable
conversation preserved statements such as "lo tengo a mente", but the next
request did not carry the structured `tool_use` / `tool_result` history that
MiniMax M2.7's Anthropic-compatible API expects for best interleaved-thinking
continuity.

Evidence:

- `POST /api/chat/sessions/{session_id}/turn` previously built
  `llm_messages` from persisted `messages` only.
- `_to_llm_messages` reduced each prior turn to `role` plus plain text
  `content`.
- `llm.response` traces stored `raw_provider_messages`, and tool calls were
  traceable, but those native blocks were not rehydrated into the next provider
  request.
- MiniMax documentation recommends preserving the full response message/content
  during tool-use and interleaved-thinking loops.

Root Cause:

The backend had two different histories:

- a human-readable transcript in `messages`;
- provider-native tool/thinking evidence in traces.

Only the first was used to build the next provider request. That made the
history useful for the UI but lossy for the model.

Fix:

Added `sessions.provider_history_json` as the Anthropic-compatible
provider-native history for the session. Completed turns now persist the exact
provider-facing sequence:

- user text message;
- assistant native content blocks;
- user `tool_result` blocks for each `tool_use`;
- assistant final native content blocks.

Subsequent turns use this provider history plus the new user message. Older
sessions without provider history fall back to text reconstruction and are
hydrated into provider history after the next completed turn.

Regression Coverage:

- `backend/tests/test_chat_api.py::test_second_chat_turn_uses_persisted_history`
- `backend/tests/test_chat_api.py::test_chat_turn_dispatches_and_traces_mind_api_tool_call`
- `backend/tests/test_chat_api.py::test_streaming_chat_turn_emits_agentic_events_and_persists_traces`
- `backend/tests/test_storage.py::test_init_db_creates_core_tables`

## BUG-0029 - Anthropic SDK Blocks High Non-Streaming MiniMax Calls

Date Found: 2026-05-23
Status: fixed

Symptoms:

After raising `MINIMAX_MAX_TOKENS` to `131072`, a real
`POST /api/debug/llm-smoke-test` call failed before reaching MiniMax. The
Anthropic Python SDK raised:

```txt
ValueError: Streaming is required for operations that may take longer than 10 minutes.
```

Evidence:

- The failure occurred in the SDK's `_calculate_nonstreaming_timeout`.
- The SDK estimates non-streaming duration from `max_tokens` and raises when
  the expected duration exceeds its 10-minute non-streaming threshold.
- MiniMax supports streaming and `max_tokens=131072`; the blocker was the SDK
  non-streaming path, not the provider route.

Root Cause:

The backend used `messages.create` for non-streaming chat/debug calls. With a
full MiniMax completion budget, the Anthropic-compatible SDK requires
`messages.stream` even when the external backend endpoint remains non-streaming.

Fix:

The MiniMax/Anthropic-compatible provider now uses streaming as its normal
execution path. Non-streaming backend calls collect the stream and return the
final provider message, while streaming backend calls forward ordered events to
the UI. The external backend response contracts remain unchanged.

Regression Coverage:

- `backend/tests/test_minimax_client.py::test_generate_chat_always_uses_stream`
- `backend/tests/test_minimax_client.py::test_generate_chat_uses_stream_for_small_default_token_budget`
- `backend/tests/test_minimax_client.py::test_generate_chat_with_tools_always_uses_stream`

Verification:

- Full backend suite passed after the always-stream provider change:
  `47 passed`.
- Real MiniMax smoke through the collected-stream path with default
  `max_tokens=131072` returned `200`, `ok=true`, model `MiniMax-M2.7`, and text
  `pong`.

## BUG-0030 - Stale Planned Event Endpoint In Mind Schema

Date Found: 2026-05-23
Status: fixed

Symptoms:

During the first live runtime-event probe, Scarlet inspected `GET /mind/schema`
and reported `POST /mind/events/emit` as a planned route. She also described it
as an event store that did not exist, even though the new event store had just
been implemented as backend-owned infrastructure.

Root Cause:

The Mind API schema still contained an older planned `/mind/events/emit` route.
That route conflicted with the current architecture decision: runtime events
are emitted by the backend and are not a new model-facing API Mind endpoint.

Fix:

- Removed `POST /mind/events/emit` from `MIND_API_ROUTES`.
- Updated the schema hint to say runtime events are backend-owned rather than
  planned model-facing capability.
- Advanced schema version to `2026-05-23.runtime-events-v1`.
- Updated API contract, roadmap, changelog, and regression assertions.

Regression Coverage:

- `backend/tests/test_mind_api.py::test_mind_schema_exposes_tool_and_current_routes`
  asserts `POST /mind/events/emit` is not present in the schema.

Verification:

- Follow-up live probe session `ses_7be6e0604fef4bef8e16ea7bc4f3201c`:
  Scarlet inspected schema and reported one planned route:
  `POST /mind/attention/context`.

## BUG-0031 - Maintenance Worker Used Detached ORM Records Across Sessions

Date Found: 2026-05-23
Status: fixed

Symptoms:

Initial P1 idle-maintenance tests failed with SQLAlchemy
`DetachedInstanceError` after a maintenance job moved from scheduled to running
and the worker attempted to use the returned ORM object outside the session
that loaded it.

A second implementation defect also appeared during the same tests:
`schedule_session_idle_maintenance` tried to include superseded job ids in the
job input payload before the repository call could return the superseded jobs.

Root Cause:

The worker treated ORM models as durable runtime objects. They are not durable
outside their session boundary because SQLAlchemy may expire attributes after
commit.

Fix:

- Added an immutable `MaintenanceJobRef` snapshot for runtime work.
- Kept superseded job ids in the scheduling event payload, not in the initial
  job input payload.
- Stored trace/event ids as scalar values before leaving the DB session in the
  memory-review step.

Regression Coverage:

- `backend/tests/test_maintenance.py::test_due_idle_maintenance_summarizes_and_reviews_memory_candidates`
- `backend/tests/test_maintenance.py::test_idle_maintenance_skips_when_a_newer_turn_exists`
- `backend/tests/test_storage.py::test_maintenance_job_round_trip_and_supersede`

## BUG-0032 - Scarlet Can Emit Pseudo Tool Invocation Text Instead Of Real Tool Use

Date Found: 2026-05-23
Status: open

Symptoms:

During the direct P1 idle-maintenance probe, Scarlet answered with visible text
containing a pseudo call:

```txt
<invoke name="mind_api">
```

No real provider `tool_use` happened and no `mind.memory.write` trace was
created, even though the text implied a memory write.

Evidence:

- Session: `ses_afa394462ab14899bd77cb2aa985f08f`
- Turn: `turn_4d7c1c557cc44c2c8745e88ed9f43245`
- The assistant response text contained pseudo tool-call markup.
- The idle maintenance review found `memory_write_trace_count=0`.
- `maintenance.memory_review` produced one missed-memory candidate for the
  green-tea preference and set `write_recommended=true`.

Impact:

This can mislead both user and summarizer: the assistant can appear to have
used API Mind when the backend has no tool-call evidence. It is especially
dangerous for memory because a public "I saved it" style response can exist
without persistence.

Do Not Fix Yet:

Per owner instruction, do not patch this immediately. Discuss the appropriate
solution first. Possible directions include prompt hardening against pseudo
tool syntax, validator/event warning for pseudo tool-call text, provider tool
choice tuning, or UI marking when final text contains tool-like markup without
a matching `mind.tool_call.completed` event.

## BUG-0033 - Runtime Context Fields Can Be Overinterpreted As Equivalent Evidence

Date Found: 2026-05-23
Status: open

Symptoms:

During the integrated streaming runtime probe, Scarlet correctly called
`GET /mind/schema` and `GET /mind/memory/conflicts`, but then made two shaky
interpretations:

- compared `runtime_context.capabilities` count with total schema route count
  and treated the mismatch as backend-visible evidence;
- described `recent_runtime_events=[]` as if it meant no events existed in the
  current turn.

Evidence:

- Session: `ses_d9d85072d6e44b19b654c957d6cc8b76`
- Turn: `turn_90e3b07080ff484da0464637a05bb9fd`
- Tool calls:
  - `GET /mind/schema`
  - `GET /mind/memory/conflicts`
- The final answer said the runtime context capability count was a mismatch
  against schema route count.
- The same turn streamed and persisted many runtime events, but those events
  are not expected inside `recent_runtime_events` for the same turn because
  runtime context is built before the model call.

Root Cause Hypothesis:

Scarlet treated similarly named runtime fields as if they shared the same
scope:

- `capabilities` is a compact capability map, not an exhaustive route count;
- `recent_runtime_events` is prior-turn context, not the current live event
  stream.

Impact:

Scarlet can draw confident diagnostic conclusions from field-shape similarity
instead of exact schema semantics. This is a source-sensitive reasoning issue,
not a storage/eventing failure.

Do Not Fix Yet:

Discuss whether this belongs in prompt clarification, runtime context schema
labels, `/mind/schema` ownership metadata, or a validator that flags claims
about runtime fields when the model compares non-equivalent scopes.

## BUG-0034 - Natural Use Can Still Call Invalid GET /mind/memory Route

Date Found: 2026-05-23
Status: open

Symptoms:

During a natural project-continuity conversation, Scarlet attempted:

```txt
GET /mind/memory
```

This route is not implemented. Implemented memory reads require either search,
facts/conflicts routes, or `GET /mind/memory/{memory_id}`.

Evidence:

- Session: `ses_44d025d20f5b4b20aad9605e6d700dad`
- Turn: `turn_92282018d4d34c9b9f988cdb004f854c`
- Persisted events included `mind.tool_call.failed`.
- Tool operations included:
  - `GET /mind/sessions`
  - `GET /mind/sessions`
  - `GET /mind/memory`
  - `POST /mind/memory/search`
  - `POST /mind/memory/search`
  - further `GET /mind/sessions` calls.

Impact:

Scarlet recovered enough to answer, but invalid route calls add latency and
show that schema discipline is still imperfect during natural use.

Do Not Fix Yet:

Discuss whether the right response is prompt clarification, stronger schema
preloading, a harmless alias for memory list/search, or a validator that nudges
Scarlet after invalid route attempts.

Partial Mitigation:

ADR-0032 added endpoint-local `usage_guide` for implemented-route errors and
route suggestions for unknown/unavailable routes. This should make invalid
route recovery easier, but BUG-0034 remains open until a natural Scarlet probe
shows that an invalid `GET /mind/memory` call is corrected reliably.

Update 2026-05-24:

The first direct temporal/sparse probe still reproduced invalid route/shape
behavior (`GET /mind/memory?...`, `POST /mind/sessions`, query-string JSON for
`time`). After retrieval guard tightening, the negative-control probe did not
repeat `GET /mind/memory`, but it still tried an invalid memory search body
before recovering through endpoint guidance. Route and parameter discipline
remain open behavioral monitoring items.

## BUG-0035 - Stale Memory Can Override Current Runtime State

Date Found: 2026-05-23
Status: open

Symptoms:

In a natural project-continuity conversation, Scarlet claimed:

```txt
Non abbiamo metriche operative. Non abbiamo event store.
```

This is false for the current system: runtime events exist and are part of the
current control plane.

Evidence:

- Session: `ses_44d025d20f5b4b20aad9605e6d700dad`
- Turn: `turn_14b9be196567427497fe9ecc757b88a2`
- The selected memory context included an older technical evaluation:
  `Valutazione tecnica API Mind: 9/12 route implementate ... zero metriche operative, nessun event store ...`
- The final answer reused that stale point even though runtime events are
  implemented and documented in the current project state.

Root Cause Hypothesis:

The retrieval layer selected a stale memory without enough freshness/lifecycle
guarding. Scarlet did not verify that memory against current project events,
schema, or docs before using it as present-tense advice.

Impact:

This is a high-risk memory-quality issue. It can make Scarlet confidently advise
against features that already exist, especially when old technical baselines
remain active.

Do Not Fix Yet:

Discuss whether this should be addressed by memory lifecycle cleanup,
staleness scoring, fact timestamps, source-session verification, or a validator
for present-tense project claims based on older memories.

Update 2026-05-24:

Temporal filters and sparse retrieval improve finding candidate evidence, but
they do not solve stale-memory trust. BUG-0035 remains open until retrieval
adds staleness/lifecycle scoring or Scarlet is forced to verify older
present-tense project memories against current schema/events/docs before using
them as current-state claims.

Update 2026-05-24 Restarted Runtime Probe:

The restarted direct probe reproduced the core issue in a cleaner way:

- Session: `ses_eac71e7b90814f49a7c21e079e64b85a`
- Turn: `turn_9ecedec4cce441eb9866b2d45f0d28f7`
- Scarlet read current schema version `2026-05-24.temporal-sparse-v1`.
- Scarlet read stale active memory
  `mem_ecfe7b2130764a3f836b0e77fefaa614`, which says "nessun event store".
- Scarlet concluded the event-store gap remained because `/mind/events/emit`
  was absent from the model-facing schema.
- This is false: runtime events are implemented, persisted, streamed, and the
  same session produced many event rows including tool lifecycle events,
  public notes, thinking metadata, turn completion, and maintenance
  scheduling.

Refined Root Cause:

Scarlet can confuse "not exposed as a model-facing route" with "does not exist
in the backend/runtime." Stale memories become especially dangerous when the
current evidence surface does not expose the exact backend capability being
claimed.

## BUG-0036 - Maintenance Proposal Queue Was Exposed Through Mind API

Date Found: 2026-05-25
Status: fixed in V1.1.1

Symptoms:

The V1.1.0 proposal inbox added `GET /mind/memory/proposals`, making an
internal maintenance queue visible to Scarlet as an autonomous cognitive
endpoint.

Root Cause:

The implementation treated proposal inspection as a Mind API capability,
instead of distinguishing Scarlet-facing cognition from background maintenance
operations.

Fix:

- Removed `GET /mind/memory/proposals` from `mind_api` dispatcher and schema.
- Added maintenance-only endpoints:
  `GET /api/maintenance/memory/proposals` and
  `POST /api/maintenance/memory/proposals/{proposal_id}/archive`.
- Restricted dynamic memory reads to real `mem_...` ids so removed child paths
  no longer appear as missing memory records.

Verification:

`backend/.venv/bin/python -m pytest backend/tests/test_mind_api.py backend/tests/test_maintenance_api.py`
passed with `25 passed`.

## BUG-0037 - Short Fact Alias Can Match Unrelated Substrings

Date Found: 2026-05-26
Status: fixed in V1.11.4

Symptoms:

While testing V1.2.0 maintenance-created memories, the deterministic fact
extractor associated an unrelated user preference with entity
`sal-updates`. The likely trigger is the short alias `sal`, which can match
inside unrelated words such as tags or ordinary text.

Root Cause:

`canonical_entity_for_memory()` checked known aliases with raw substring
membership over the normalized memory haystack. Short aliases were therefore
too powerful. The same facts layer also inferred `response_format` from generic
words such as `response/risposta`, turning broad communication preferences
into false response-format facts.

Impact:

This can create misleading canonical facts for newly written memories. The
current proposal resolution stores the full proposal and memory snapshot, so
future Dream/human review can detect the anomaly, but retrieval/conflict logic
that relies on canonical facts may receive noisy entity matches.

Fix:

- Replaced known-alias substring checks with normalized phrase/token boundary
  matching.
- Tightened `response_format` inference to explicit structural signals:
  response-format tags, block metadata, block words, or phrases such as
  `answer with` / `rispondere con`.
- Reconciled the laboratory DB:
  - 7 active facts unsupported by the new extractor were marked
    `rejected_extractor_noise`;
  - 6 supported replacement facts were created;
  - active fact-derived surfaces, nodes, and edges for rejected facts were
    removed from active retrieval paths.

Regression Test:

`tests/test_mind_api.py::test_mind_memory_fact_alias_matching_uses_phrase_boundaries`

Related Files:

- `backend/app/mind/facts.py`
- `backend/tests/test_mind_api.py`
- `backend/data/app.db`

Notes:

This fixes the known short-alias/root-cause class. It does not finish entity
quality for tag-derived facts; that remains a later stabilization topic before
automatic lifecycle operations become aggressive.

## BUG-0038 - MiniMax M3 Ultra-Short Responses Can Produce Empty Content Blocks

Date Found: 2026-06-08
Status: monitoring

Symptoms:

During the V1.4.1 MiniMax M3 migration check, an ultra-short prompt asking the
model to reply only `pong` reached the Anthropic-compatible endpoint but
returned no usable text content:

- non-streaming raw response: `content:null`, `model=MiniMax-M3`, usage
  present, `stop_reason=end_turn`;
- streaming raw response: `message_start`, `ping`, `content_block_stop`,
  `message_delta`, `message_stop`, without a preceding text block containing
  final text;
- the Anthropic SDK stream accumulator raised `IndexError: list index out of
  range`.

Impact:

This can break synthetic one-token smoke tests and possibly user prompts that
overconstrain Scarlet to a one-token output. Realistic M3 prompts and a
tool-use probe both worked through the current provider, so this is treated as
a provider/model edge case rather than a blocker for behavioral comparison.

Do Not Fix Yet:

Do not add a custom raw-SSE M3 provider in V1.4.1 unless direct Scarlet turns
show the same issue in normal use. Use realistic smoke prompts and keep M2.7
available as `MINIMAX_MODEL=MiniMax-M2.7`.

## BUG-0039 - MiniMax M3 Repeatedly Sends Invalid Memory Write Tags Shape

Date Found: 2026-06-08
Status: monitoring

Symptoms:

During EXP-0032 and the targeted EXP-0033 replication, MiniMax M3 repeatedly
called `POST /mind/memory/write` with `tags` serialized as an object-like shape
instead of the endpoint's expected `string[]`. The endpoint rejected those
calls with `memory.invalid_write`, M3 retried several times, and eventually
stored the memory only after dropping tags.

EXP-0033 replication:

- M2.7 memory write: 5/5 successful, 5/5 valid first attempt, 0/5 tag-shape
  errors, 5/5 successful memories had tags.
- M3 memory write: 3/3 successful eventually, 0/3 valid first attempt, 3/3
  invalid write, 3/3 tag-shape errors, 0/3 successful memories had tags.
- M3 average write attempts: 5.67.
- M3 average memory-write latency: 82.1s.

Impact:

M3 can still complete the semantic memory write, but the retry loop creates high
latency, context bloat, and degraded memory quality because tags are lost in
the final stored memory. This directly affects retrieval quality and future
embedding/knowledge-graph surfaces, where tags are useful classification
signals.

Root Cause:

Not fixed yet. Current evidence points to a model/tool-argument compatibility
issue rather than backend failure: M2.7 uses the same prompt, same schema, same
endpoint, and same backend successfully.

Do Not Fix Yet:

Do not patch this with hardcoded term bans or case-specific prompt tricks.
Discuss a focused root-cause mitigation first. Candidate directions include
clearer endpoint-local error guidance, provider/tool schema compatibility
checks, or backend-side structural normalization for known array-wrapper shapes
while preserving traces that show the model error occurred.

Related Files:

- `docs/experiments.md#exp-0033---minimax-m3-stability-replication`
- `backend/app/mind/memory.py`
- `backend/app/mind/schema.py`

## BUG-0040 - Idle Maintenance Jobs Can Fail On Provider ReadTimeout

Date Found: 2026-06-14
Status: monitoring

Symptoms:

After adding V1.5.0 maintenance overview/job inspection, the live local DB
showed failed `session.idle_maintenance` jobs. The most recent failed job
recorded:

- status: `failed`;
- error: `ReadTimeout`;
- result message: `The read operation timed out`;
- kind: `session.idle_maintenance`.

Impact:

A failed idle maintenance job may leave a session without refreshed summary or
missed-memory review for that idle window. The job remains observable in
`/api/maintenance/overview` and `/api/maintenance/jobs`, but there is not yet a
retry/resume policy.

Root Cause:

Not investigated in this slice. The immediate evidence points to provider or
network timeout during the maintenance LLM phase, not to the new overview/job
listing endpoints.

Do Not Fix Yet:

Do not silently add retries or auto-resume behavior inside V1.5.0. Discuss a
focused maintenance reliability slice first, including:

- retry policy;
- max attempts;
- partial summary/review checkpointing;
- whether failed jobs should create a follow-up maintenance job;
- how failures should appear in UI/evaluator tooling.

Related Files:

- `backend/app/runtime/maintenance.py`
- `backend/app/api/maintenance.py`
- `docs/project-state.md#211-session-idle-maintenance`

## BUG-0041 - MiniMax M3 Public Notes Were Misclassified And Reordered In UI

Date Found: 2026-06-15
Status: fixed in V1.5.1

Symptoms:

After switching to MiniMax M3, live turns showed strong agentic behavior but the
cockpit could make provider text blocks look disorganized. M3 can emit public
work text before tool calls across multiple model steps, while the frontend
treated only text before the first tool in model step 1 as a note. Persisted
notes were also reconstructed after the turn from `raw_provider_messages`,
which could append them after the final response when reloading historical
events.

Root Cause:

The UI and event recorder used timing heuristics instead of provider message
structure. The real distinction is structural:

- provider text in a message that contains `tool_use` is a public work note;
- provider text in the final `end_turn` message is the final answer;
- provider thinking blocks are separate provider-exposed technical blocks.

Fix:

V1.5.1 normalizes provider content into semantic stream events:

- `thinking_captured` / `llm.thinking.captured`;
- `assistant_note` / `assistant.note.emitted`;
- `assistant_answer` / `assistant.answer.completed`.

The frontend renders semantic blocks directly and groups each tool call into
one accordion with input and output panes.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py backend/tests/test_minimax_client.py`
- `npm run build`
- Direct MiniMax M3 streaming probe confirmed persisted order:
  `assistant.note.emitted` -> `mind.tool_call.started/completed` ->
  `assistant.answer.completed`.

Residual Risk:

MiniMax M3 thinking is only visible when the provider actually emits thinking
blocks. This fix supports and renders those blocks, but does not yet change the
provider request configuration to force M3 thinking mode.

## BUG-0042 - Chat UI Nested Agent Blocks And Duplicated Technical Sidebar

Date Found: 2026-06-15
Status: fixed in V1.5.1

Symptoms:

After the first V1.5.1 semantic stream UI pass, the center chat still looked
confusing because a single assistant-response card contained many nested
operation blocks. The right sidebar also still behaved like a broad dashboard
or duplicate stream rather than a focused technical inspector for the selected
conversation.

Root Cause:

The frontend kept the older "assistant message body contains timeline" layout
even after the backend began emitting semantically distinct runtime blocks.
This made the new stream structure correct at data level but not at visual
information-architecture level.

Fix:

The center chat now renders user messages, memory/context blocks, runtime
context, thinking, notes, tool exchanges, and final answers as top-level
chronological flow cards. The right pane is now a session inspector with
accordion lists for memories, actions, internal events, and warnings/errors.
Raw payloads remain available behind per-block code/detail toggles.

Verification:

- `npm run build`
- Visual/DOM probe on a dense persisted session confirmed top-level
  `chat-flow-card` blocks and no old `.message-body` or
  `.agent-turn.embedded` wrappers.

Residual Risk:

This fixes the hierarchy and duplication problem, but visual density still
needs human testing on long MiniMax M3 sessions to tune labels, spacing, and
which technical fields deserve default visibility.

## BUG-0043 - Persisted Thinking Events Lost Their Body On Historical Replay

Date Found: 2026-06-16
Status: fixed

Symptoms:

In the chat center, provider thinking blocks could be missing after turn
completion or after reloading an older conversation. The turn chronology still
contained other runtime cards, but generated thinking was absent or effectively
empty.

Root Cause:

When semantic content had to be reconstructed from `raw_provider_messages`, the
backend persisted `llm.thinking.captured` with only `has_text` and provider
identifiers. The actual thinking text, `model_step`, and block `index` were
not stored. During historical replay, the frontend therefore had no reliable
body to render for those events.

Fix:

- Backend persistence now stores `text`, `model_step`, and `index` for
  response-derived `llm.thinking.captured`, `assistant.note.emitted`, and
  `assistant.answer.completed` events.
- Frontend replay now recovers missing legacy thinking text from matching
  `llm.response.raw_provider_messages` when old stored events lack a body.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
- `npm run build`

Residual Risk:

This fix preserves generated thinking once it exists. It does not guarantee
that MiniMax M3 will emit provider-visible thinking on every turn.

## BUG-0044 - MiniMax M3 Thinking Was Disabled By Provider Request Shape

Date Found: 2026-06-16
Status: fixed in V1.5.1

Symptoms:

With MiniMax M3 active, Scarlet could complete non-trivial turns and tool-use
turns without any provider-visible thinking blocks in the stream or persisted
history. Older MiniMax M2.7 turns still showed `llm.thinking.captured`, which
made the cockpit behavior look inconsistent and suggested the UI was dropping
thinking blocks.

Root Cause:

The Anthropic-compatible MiniMax provider integration did not send the
`thinking` parameter at all. For MiniMax M3, official docs state that omitting
`thinking` disables visible thinking blocks by default. The runtime was
therefore behaving correctly from the provider point of view, but not from the
product expectation for Scarlet's inspectable cognition.

Fix:

- `backend/app/llm/minimax_client.py` now sends
  `thinking={"type":"adaptive"}` automatically for MiniMax M3 requests.
- M2.x models remain unchanged.
- Added unit coverage to prevent future regressions.

Verification:

- `backend/.venv/bin/python -m pytest backend/tests/test_minimax_client.py -q`
- `backend/.venv/bin/python -m pytest backend/tests/test_chat_api.py -q`
- Live MiniMax M3 stream probe after backend restart confirmed
  `thinking_start` and `thinking_delta` events before and after tool use.

Residual Risk:

This fixes provider-visible M3 thinking in the current Anthropic-compatible
integration. It does not change the policy that public notes before tool calls
are prompt-driven rather than hard-enforced by the runtime.

## BUG-0045 - Scarlet Often Ignores Visible Prior Thinking Blocks In Same-Session History

Date Found: 2026-06-16
Status: mitigated by V1.8.0, monitoring

Symptoms:

In live MiniMax M3 follow-up turns, Scarlet can answer questions about her
previous reasoning by citing `recent_runtime_events` markers such as
`llm.thinking.started` / `llm.thinking.captured`, or even claim the previous
thinking content is not recoverable, despite the real `llm.request` provider
history already containing the assistant `thinking` block from the prior turn.

Root Cause:

The backend transport is working: follow-up `llm.request` traces show
`provider_history_source = session.provider_history_json` and assistant content
blocks like `['thinking', 'text']` or `['thinking', 'text', 'tool_use']`.

The remaining failure appears to be model-side behavior or prompt-following
fragility: MiniMax M3 does not reliably treat visible prior `thinking` blocks
as the strongest semantic source for same-session reasoning questions.

Fix:

- Added V1.5.2 prompt guidance that explicitly separates continuity layers.
- Clarified that same-session provider continuity outranks
  `recent_runtime_events` for semantic content.
- Added a direct instruction to inspect visible prior `thinking` blocks before
  answering only from thinking markers when the user asks what Scarlet had
  already been considering.

Regression Test:

- Live probe `ses_172498d31b424e1dafa28dd85a38fcc0` confirmed improved layer
  explanations and prompt load.
- Live probes `ses_d09ad1594bf4471ea27794c5b896856d` and
  `ses_4dcded570516493f850c2839a0d8894f` plus their `llm.request` traces
  confirmed prior assistant `thinking` blocks were present in provider
  messages, while Scarlet still sometimes answered from runtime event markers
  instead.

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/api/chat.py`
- `backend/app/mind/context.py`
- `docs/experiments.md`

Notes:

This is no longer a transport or persistence bug. It is currently tracked as a
model-behavior limitation under the current MiniMax M3 + prompt contract.
V1.8.0 adds a controlled alternative: Scarlet can call
`POST /mind/metacognition/step` with a retrospective mode and
`turn_scope="previous"` to receive a backend-built thinking retrospection pack
for the previous completed turn. This does not force every answer to receive
prior thinking, but it gives Scarlet a reliable process-audit path when the
question actually requires it.

Initial V1.8.0 live probe:

- Session `ses_9f7b8e37cc2145508867bd45b96f3553`, turn
  `turn_0fedc6410a2a461e911ab67fc181c642`.
- Scarlet autonomously called `/mind/metacognition/step` with
  `mode="compare_answer_to_reasoning"` and `turn_scope="previous"`.
- Trace `trace_205288e7aa6a419eabab67785c5bc908` built a retrospective pack
  from previous turn `turn_db40c320be8c423fbeea614de4c66e2e`.
- Residual: Scarlet selected `detail="excerpt"` instead of `digest`, producing a
  high-token/long-latency turn. This is a calibration issue, not a transport
  failure.

## BUG-0046 - MiniMax M3 Over-Processes Simple Scarlet Turns

Date Found: 2026-06-16
Status: fixed in V1.7.1

Symptoms:

During human live testing, Scarlet could answer simple questions with
unnecessary multi-layer reasoning, draft/review behavior, redundant schema
checks, public work notes, and verification cycles. The effect made M3 feel
heavier than needed for normal conversation and could cause Scarlet to ignore
concise-response preferences already present as relevant memory hints.

Root Cause:

The prompt described a strong engineering-agent posture, cognitive loop,
verify-before-conclude pattern, public work notes, evidence hierarchy, and
experimental memory forcing without a clear effort router. MiniMax M3 followed
those instructions more aggressively than M2.7, treating many ordinary turns
as if they required full agentic investigation.

Fix:

- Added `Request Effort Routing` to classify turns before tools, notes,
  metacognition, or verification.
- Direct answers now skip API Mind, public work notes, and full verification
  when the answer is already visible or conversational.
- Contextual answers use already-provided runtime/memory/history evidence
  without redundant calls.
- Source-sensitive, state-changing, and high-impact turns retain proportional
  API Mind use and verification.
- Memory forcing is now conditional on semantic candidates, memory promises,
  state changes, or source-sensitive claims rather than mandatory on every
  turn.
- Near-miss memories can be applied softly as communication-style hints when
  clearly relevant.

Regression Test:

- Direct live probe session `ses_958ba084193d48fb9ac853c89602ffea`:
  - simple one-sentence request, turn
    `turn_ff0cf30a951240ccb09a1290a2aad51a`: no tool call, no public note,
    compact final answer, provider thinking classified the turn as Level 1
    direct answer.
  - source-sensitive schema request, turn
    `turn_53485550e62549b588a1702e7ddf3a1e`: public note, real
    `GET /mind/schema` tool call, answer grounded in schema routes/version.

Residual Risk:

MiniMax M3 can still emit visible thinking for compact answers, and some
requests may sit between contextual and source-sensitive. More human live
testing is needed to estimate whether the prompt now consistently chooses the
right effort level.

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260616T164444Z.md`
- `docs/activity-log.md`
- `docs/decisions.md`

## BUG-0047 - MiniMax M3 Retries Metacognition Step With Invalid Shapes

Date Found: 2026-06-16
Status: mitigated by V1.8.0, monitoring

Symptoms:

During the V1.7.2 long-reasoning-notes live probe, Scarlet attempted
`POST /mind/metacognition/step` multiple times with invalid payload shapes
before eventually succeeding. Errors included missing required `intent`, extra
forbidden fields such as `draft`, and list fields wrapped as dicts rather than
sent as arrays.

Root Cause:

Not confirmed. The endpoint-local usage guides and validation errors were
clear enough for eventual recovery, so this is not currently a backend error
handling failure. The likely issue is MiniMax M3 tool-argument shaping on a
complex endpoint after a long prompt/tool context.

Observed Evidence:

- Session `ses_5dbdac4acf91402bb31418ddd3750b99`
- Turn `turn_20cf87c91bb94b4aac771bf4dbad7a05`
- Probe generated:
  - 6 public notes;
  - 8 tool calls;
  - 7 thinking blocks;
  - repeated failed `metacognition.step` attempts before a successful retry.

Impact:

The behavior increases latency and produces noisy tool history during complex
reasoning. It does not block recovery in the observed probe because
endpoint-local schema/error guidance allowed Scarlet to correct herself.

Mitigation:

V1.8.0 keeps the endpoint-local error guidance and adds small shape-hardening
for observed metacognition payloads:

- `reasoning_scope` maps to `turn_scope`;
- `reasoning_detail` maps to `detail`;
- retrospective modes default to `turn_scope="previous"`;
- list wrappers shaped as `{"item": [...]}` are normalized for
  `known_evidence`, `uncertainties`, and `previous_steps`.

This is not a full model-behavior fix. It reduces repeated invalid calls for
the new retrospective path while preserving a small model-facing surface.

Potential Future Directions:

- Re-test `metacognition.step` shapes across MiniMax M3 repeated probes.
- Consider simplifying the model-facing metacognition endpoint schema if the
  error is systematic.
- Compare with MiniMax M2.7 before changing backend contracts.

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/api/mind.py`
- `docs/experiments.md`

## BUG-0048 - Hybrid Retrieval Payload Reads Detached Memory Objects

Date Found: 2026-06-19
Status: fixed

Symptoms:

The first Codex dirty-memory harness run crashed during `/mind/memory/search`
with `sqlalchemy.orm.exc.DetachedInstanceError`. The crash happened while
building the `retrieval_hybrid` diagnostic payload after `add_trace` committed
the session.

Root Cause:

`HybridRankEntry` kept a live `MemoryRecord` object and
`hybrid_rank_status_payload()` later read `entry.memory.id`. Because
`repositories.add_trace()` commits, SQLAlchemy can expire ORM attributes; the
diagnostic serializer then tried to refresh a detached `MemoryRecord`.

Fix:

- `HybridRankEntry` now materializes `memory_id`, `memory_salience`, and
  `memory_created_at` when the rank plan is built.
- `hybrid_rank_status_payload()`, automatic context lookup, and manual memory
  search lookup use `entry.memory_id` for diagnostic payloads and maps.

Verification:

- `cd backend && .venv/bin/python -m py_compile app/evals/codex_test_memory_harness.py app/mind/hybrid_retrieval.py app/mind/memory.py app/mind/context.py`
- `cd backend && .venv/bin/python app/evals/codex_test_memory_harness.py --reset --target-count 240`
- `cd backend && .venv/bin/python -m pytest tests -q`

Residual Risk:

The fix stabilizes diagnostic serialization. It does not change retrieval
ranking quality or tune hybrid thresholds.

Related Files:

- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/mind/context.py`
- `backend/app/mind/memory.py`
- `backend/app/evals/codex_test_memory_harness.py`

## BUG-0049 - Automatic Memory Context Selects Weakly Related Memories

Date Found: 2026-06-19
Status: open, discussion required before fix

Symptoms:

Corrected context-eval probes that use the real chat path showed weak memory
selection in three cases:

- evening beverage query selected caffeine but missed the chocolate-limit
  memory, while selecting repeated food distractors;
- metacognitive effort-routing query selected repeated generic
  "memory-as-anchor" lessons instead of the effort-routing lesson;
- unrelated jazz/cooking query selected a project/philosophy memory from weak
  generic overlap.

Root Cause:

Not yet fixed. Current evidence points to ranking/gating calibration rather
than a single bad keyword:

- associative graph expansion can over-broaden food/energy domains;
- generic token overlap still promotes memories in some project contexts;
- repeated synthetic lessons with similar wording can crowd out a better
  behavioral-pattern memory.

Observed Evidence:

- Corrected context report:
  `backend/app/evals/runs/20260619_172206_codex_test_memory/`.
- Live Scarlet report:
  `backend/app/evals/runs/20260619_172536_codex_live_scarlet_memory/`.

Impact:

MiniMax M3 often ignores or compensates for noisy context, but the system should
not rely on the model to filter irrelevant memories. Noisy selected memories
can waste context, bias answers, and hide the memories Scarlet actually needs.

Potential Future Directions:

- Distinguish exact recall, functional-equivalent recall, and noisy recall in
  the harness.
- Calibrate graph expansion and hybrid weights on corrected chat-context
  probes, not endpoint-only probes.
- Add domain/scope gating for unrelated lifestyle prompts without hardcoded
  banned words.
- Deduplicate near-identical metacognitive lessons before ranking.

Related Files:

- `backend/app/mind/context.py`
- `backend/app/mind/graph_retrieval.py`
- `backend/app/mind/hybrid_retrieval.py`
- `backend/app/evals/codex_test_memory_harness.py`

## BUG-0050 - MiniMax M3 Repeats Empty Body For Memory Writes

Date Found: 2026-06-20
Status: monitoring after V1.14.4 prompt mitigation

Symptoms:

Two live protected-preview Scarlet sessions on MiniMax M3 repeatedly attempted
`POST /mind/memory/write` after recognizing valid semantic memory candidates,
but every tool call used `body={}`. The backend correctly returned
`memory.invalid_write` because required memory fields were missing. Scarlet
then retried many times with the same empty body instead of recovering.

Observed Evidence:

- Session `ses_9a5cb76b59f04fb9afcb264ce1c645ba`, turn
  `turn_be25a58291a74446a822c19e89ca385a`: 11 failed memory-write tool calls
  for the user's warmer communication preference, all with empty bodies.
- Session `ses_9c801c964103425ca3d076d8240eaa4b`, turn
  `turn_6588da98460a4157bd98bfe193e8d2b5`: repeated failed memory-write tool
  calls for an evening birthday-plan anchor, all with empty bodies.
- VPS runtime confirmed `CODEX_TEST=false` and `database.profile=prod`, so the
  failure was not caused by the Codex test database.
- Direct backend `/mind/memory/write` with a valid body still works, so the
  endpoint and DB path are not the root cause.

Root Cause:

Not fully proven. Current evidence points to an interaction between MiniMax M3,
the large current Scarlet prompt/runtime context, the generic
`mind_api(method,path,body,intent)` wrapper, and prompt pressure that made
memory writes feel mandatory before final answer.

Earlier M3 tests showed a milder related issue: M3 often sent invalid `tags`
shape but could recover by retrying without tags. The new failure is different
and more severe because the route body is completely empty.

Mitigation:

V1.14.4 prompt update:

- clarifies that `intent` never replaces the route `body`;
- tells Scarlet that `body={}` is not a memory write attempt;
- requires a materially corrected non-empty body after endpoint-local guidance;
- stops repeated identical empty-body retries;
- forbids claiming persistence when the write failed.

Regression Test:

Pending live verification. Run a normal Scarlet conversation with a clear
sourceable memory candidate, then inspect `tool_calls.arguments_json` and
`mind.tool_call` traces:

- expected: at most one failed shape retry, followed by a non-empty corrected
  body or a transparent stop;
- failure: repeated `POST /mind/memory/write` calls with `body={}`.

Prompt-level probe on 2026-06-20:

- With the updated prompt and MiniMax M3, a direct tool-use probe first called
  `GET /mind/schema`, then emitted `POST /mind/memory/write` with a non-empty
  body.
- The body used `reason`, which the backend normalizes to
  `reason_for_storage`.
- This is encouraging but not sufficient: the next check must be a full live
  Scarlet turn through the normal chat runtime.

Related Files:

- `backend/app/prompts/scarlet_system.md`
- `backend/app/prompts/backups/scarlet_system.20260620T182223Z.pre-v1144-prompt-discipline.md`
- `backend/app/mind/schema.py`
- `backend/app/llm/minimax_client.py`

## BUG-0051 - Memory Scope Alias Normalization Could Collapse Project Scope

Date Found: 2026-06-23
Status: fixed in V1.15.0

Symptoms:

During the V1.15.0 memory-field test pass, several memory search regressions
returned no candidates or unexpected candidates after a write body used
`scope=project`.

Root Cause:

The shared alias normalization path could apply type aliases while normalizing
`scope`. Because `project` is also a known memory type alias for
`project_fact`, `scope=project` could be interpreted as a type-like value and
collapsed to the fallback general scope.

Fix:

Separated scope normalization from type alias normalization. `scope` is now a
free semantic label normalized only as a label. If a model accidentally sends a
known memory type value in `scope` without a separate `type`, the backend can
still recover by moving it to `type`; otherwise `project`, `user`, `session`,
and other scopes remain scopes.

Regression Test:

Covered by:

```txt
cd backend && .venv/bin/python -m pytest tests/test_mind_api.py tests/test_maintenance.py tests/test_chat_api.py -q --tb=short
```

The targeted suite passed with `57 passed`; the full backend suite passed with
`86 passed`.

Related Files:

- `backend/app/mind/memory.py`
- `backend/tests/test_mind_api.py`

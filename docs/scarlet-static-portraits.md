# Scarlet Static Portrait System

Last updated: 2026-07-23
Status: active visual direction; identity contract and supporting 360-degree references approved
Branch: `sca-48-product-ui-prototype`

## Purpose

The Product UI represents Scarlet through high-fidelity static portraits that
change with her semantic state. Short fades and restrained presentation effects
connect states without pretending that a still image is a continuously rigged
body. This replaces the layered puppet as the active delivery path while
preserving that work as future research.

## Identity Authority

The approved half-body portrait is authoritative for face, eyes, makeup, hair,
upper-body costume, and rendering. The approved T-pose is secondary authority
for full-body proportions, hands, legs, footwear, and regions absent from the
portrait:

```text
frontend/public/prototype/scarlet-character-v1.png
frontend/public/prototype/avatar/source/scarlet-full-body-tpose-reference-v1.png
```

The complete immutable and controlled identity rules live in:

```text
frontend/public/prototype/avatar/static/scarlet-identity-contract-v1.json
```

## 360-Degree Reference Pack

The supporting pack contains the eight principal turntable directions plus a
rear-costume exposure and bilateral palm/back-of-hand reference. Its manifest
defines orientation, role, authority, and known limits:

```text
frontend/public/prototype/avatar/static/reference-360/scarlet-reference-360-v1.json
frontend/public/prototype/avatar/static/reference-360/scarlet-reference-360-v1-contact-sheet.png
```

The owner approved the complete supporting pack on 2026-07-22. These generated
views may explain hidden geometry when producing a new portrait, but they may
not replace the approved front face, hair topology, body proportions, or front
costume details.

## Initial State Library

The first planned application states are:

- `startup_greeting_smile`: brief welcoming smile and one-hand greeting;
- `chat_neutral_smile`: active-chat resting portrait with gentle engagement;
- `chat_idle_bored`: mild, non-hostile boredom after prolonged inactivity.

Their semantic and visual constraints are defined in:

```text
frontend/public/prototype/avatar/static/scarlet-static-state-catalog-v1.json
```

The default transition is a 240 ms crossfade. The catalog currently proposes a
120-second threshold for the long-idle state; this remains a prototype value,
not a Core behavior contract.

## Startup Greeting Motion

The splash uses one owner-supplied HappyHorse H.264 render inside a circular
video bubble:

```text
frontend/public/prototype/avatar/static/motion/scarlet-startup-greeting-happyhorse-v1.mp4
```

The `1280x720`, 5.16-second source has an opaque black background, AAC audio,
and a lower-right generator watermark. The Product UI therefore:

- center-crops it inside the bubble so the watermark and lateral background
  never enter the visible area;
- preloads it muted and inline in parallel with the splash startup checks;
- keeps it paused at `0s` beneath the canonical portrait until application and
  media readiness converge;
- plays `0s -> end` exactly once as the completed-splash transition to Login;
- never loops inside the application-entry flow;
- keeps the canonical portrait beneath the video while it loads; and
- uses only the canonical portrait when reduced motion is requested or video
  playback fails.

This prepared splash motion does not reopen the layered-puppet path and does
not establish continuous body animation as a Product UI capability.

## Acceptance Boundary

A portrait is admitted only when it preserves the approved facial identity,
anatomical side/color mapping, hair topology, outfit silhouette and panel
language, cuffs, manicure, body proportions, and premium semi-realistic anime
rendering. Approved supporting 360-degree views remain subordinate to the two
canonical front authorities. Future emotional portraits are reviewed
independently; approval of the reference pack does not approve later states.

Static state switching does not claim continuous movement, lip synchronization,
gaze tracking, or rig deformation. Those remain out of scope until a later
avatar research branch establishes a workflow that preserves identity at an
acceptable cost.

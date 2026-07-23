# Product UI Static Prototype

Last updated: 2026-07-22
Current app target: V1.54.0; prototype remains an unversioned approval artifact
Linear issue: SCA-48
Status: implemented and awaiting explicit owner approval

## Purpose

The `/prototype` route is the approval artifact for the V2 Product UI. It is a
static, mobile-first React application with schema-realistic fixtures. It does
not call the backend and does not alter the existing `/` cockpit or `/mobile`
consumer.

As of 2026-07-20, the default route presents only the first Android navigation
step: the Scarlet splash and identity concept. The prior multi-surface product
preview remains available at `/prototype?surface=product` for comparison. APK
update, login, registration, and home are intentionally not represented yet.

The splash introduces the approved character direction: Scarlet appears as an
adult anime woman around age 25, with visible makeup, dark plum hair, pearl and
graphite clothing, and Timber cyan/fuchsia identity accents. The current
transparent bust is the approved identity source for an active static-portrait
system. Scarlet will change among separately authored, identity-locked
emotional states through short fades and restrained presentation effects. It
does not simulate continuous facial motion or speech.

The current splash uses a pre-rendered HappyHorse greeting inside a circular
video bubble. Its opaque background and watermark are excluded by the crop.
Playback is muted and inline, uses the approved portrait as the loading,
error, and reduced-motion fallback, and loops from two seconds only after the
complete first pass.

The TripoAI image-to-3D probe was rejected as the production avatar path after
its OBJ preserved a general resemblance but introduced visible quality defects.
The layered raster puppet path is paused after Live2D, PSD, and prepared APNG
experiments proved too costly and identity-sensitive for the present Product
UI. Its artifacts and findings remain available for future research. The
active path is documented in `docs/scarlet-static-portraits.md`: an identity
contract, an approved supporting 360-degree reference pack, and an incremental catalog of
static semantic states. The first planned states are startup greeting,
active-chat neutral, and long-idle boredom.

The artifact was created on the parallel V1.52 development branch and refreshed
onto V1.54.0 after the Agentic Module contract, host, and SDK landed. This
technical refresh did not change its visual or interaction direction and does
not count as owner approval.

The first technically complete visual pass was rejected by the owner because
its dark SaaS sidebar, conventional cards, restrained palette, and familiar
chat anatomy felt generic and too close to common AI products. The current
pass replaces that direction with the project-specific **Scarlet Signal**
system while preserving the approved information architecture and fixture
boundary.

The prototype tests one product boundary: ordinary users follow Scarlet
through chat, compact public notes, continuity, memories, and operating state;
the same application exposes technical evidence through an optional developer
lens instead of duplicating the product or mixing diagnostic payloads into the
conversation.

## Information Architecture

| Surface | Purpose | Primary content |
|---|---|---|
| Chat | Default Product UI | User/Scarlet messages, compact work notes, composer, turn state |
| Sessions | Episodic continuity | Title, summary, update time, turn count, reopen action |
| Memory | Semantic continuity | Compact content, scope, type, update time, source navigation |
| Status | Current operational posture | Agent mode, organ availability, local time, context occupancy |
| Settings | Local user preferences | Name, language, timezone, note visibility, density, privacy readout |
| Developer lens | Technical inspection | V2 event cursor, schema, persisted event order, phase and visibility |

Desktop uses a persistent navigation rail and a constrained conversation
column. Mobile uses the same component tree with a bottom navigation and an
off-canvas menu. The developer lens is a right drawer on desktop and a full
viewport drawer on mobile.

## Fixture Contract

`frontend/src/prototype/prototypeData.ts` provides sessions, memories, and
events. Every event uses the required `scarlet-stream-v2` envelope:

```txt
schema_version, event_id, seq, session_id, turn_id, event_type, phase,
timestamp, visibility, links, payload
```

Fixtures are deliberately compact and contain no production database values.
They exercise canonical `public` and `debug` visibility, note capture, tool lifecycle,
assistant persistence, terminal completion, source session/message hooks, and
session-global sequence order.

## Preview States

The developer lens can select six deterministic UI states without network
activity:

| State | Expected product behavior |
|---|---|
| Ready | Completed turn with note and answer |
| Empty | New conversation and starter prompts |
| Loading | Stable skeleton layout while session content loads |
| Streaming | In-progress Scarlet response and activity indicator |
| Reconnecting | Persisted content remains visible with explicit retry |
| Error | Failed turn remains legible and recoverable |

## Visual Tokens

Scarlet Signal uses three identity colors with stable roles rather than a
generic AI gradient:

| Token | Role |
|---|---|
| Fuchsia `#ed008c` | Scarlet's presence, memory identity, active navigation, and direct user channel |
| Scarlet `#ff304f` | Action, continuity, sequence emphasis, and critical focal points |
| Light blue `#79d9ff` | Cognition, provenance, active runtime, and technical information |
| Ink `#17141f` | Cognitive work notes, developer evidence, and strong contrast |
| White/cool neutrals | Reading surfaces and structural space only |

The visual signature is a chromatic continuity line that appears across the
application as a top signal, conversation thread, state edge, event sequence,
and mobile navigation marker. The main canvas uses a precise technical grid
instead of decorative blobs. Scarlet responses are open editorial blocks;
work notes form dark cognitive events; user messages use the direct fuchsia
channel; sessions are numbered traces; memories are compact provenance hooks.
Cards remain only where repeated records or framed controls require them and
never exceed an 8px radius.

Typography is self-hosted through the variable Manrope and Space Grotesk font
packages. Motion is limited to signal bars, active-state transitions, streaming
indicators, and the developer lens, with a complete reduced-motion fallback.

The Tailwind pipeline is V4 through `@tailwindcss/vite`; existing Tailwind
utility and `@apply` usage remains build-compatible. Catalyst is not present in
the repository and no licensed package was available during SCA-48, so the
prototype uses local equivalent primitives for buttons, segmented controls,
fields, toggles, banners, drawers, cards, and navigation. Those primitives are
temporary design references for SCA-50, not a new shared component library.

## Verification

Verified in a real JavaScript browser at the agreed viewports:

- desktop `1440x1000`;
- mobile `390x844`;
- chat, sessions, memory filtering, developer lens, reconnect, menu, and
  scenario switching;
- no page-level horizontal overflow;
- no clipped primary controls or incoherent overlap;
- no browser console warnings or errors;
- hidden mobile navigation removed from interaction/accessibility while
  closed;
- production TypeScript/Vite build with Tailwind V4;
- `npm audit` reports zero vulnerabilities.

The Scarlet Signal pass additionally verified the session trace, memory grid,
status surface, settings, developer lens, and reconnect state at the same
desktop/mobile viewports. The mobile document remains exactly viewport width
with no horizontal overflow.

Screenshots:

- [Mobile splash](assets/product-ui-prototype/mobile-splash.png)
- [Landscape splash](assets/product-ui-prototype/landscape-splash.png)
- [Mobile video splash](assets/product-ui-prototype/mobile-splash-video.png)
- [Landscape video splash](assets/product-ui-prototype/landscape-splash-video.png)
- [Desktop chat](assets/product-ui-prototype/desktop-chat.png)
- [Desktop developer lens](assets/product-ui-prototype/desktop-developer-lens.png)
- [Desktop sessions](assets/product-ui-prototype/desktop-sessions.png)
- [Desktop memory](assets/product-ui-prototype/desktop-memory.png)
- [Mobile chat](assets/product-ui-prototype/mobile-chat.png)
- [Mobile sessions](assets/product-ui-prototype/mobile-sessions.png)
- [Mobile status](assets/product-ui-prototype/mobile-status.png)
- [Mobile settings](assets/product-ui-prototype/mobile-settings.png)
- [Mobile developer lens](assets/product-ui-prototype/mobile-developer-lens.png)

## Approval Boundary

SCA-48 remains open until the owner explicitly approves the visual and
interaction direction. Approval permits SCA-50 to extract the accepted design
system and SCA-49 to connect the Product UI to Core ports. Until then:

- `/prototype` stays static;
- `/` and `/mobile` remain the real clients;
- no backend endpoint or stream consumer is changed;
- no prototype fixture is treated as runtime evidence.

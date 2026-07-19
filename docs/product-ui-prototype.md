# Product UI Static Prototype

Last updated: 2026-07-19
Target: V1.52.0
Linear issue: SCA-48
Status: implemented and awaiting explicit owner approval

## Purpose

The `/prototype` route is the approval artifact for the V2 Product UI. It is a
static, mobile-first React application with schema-realistic fixtures. It does
not call the backend and does not alter the existing `/` cockpit or `/mobile`
consumer.

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

The prototype uses restrained operational surfaces rather than a marketing
composition. Cards and controls use a maximum 8px radius. The palette combines
neutral white/ink surfaces, a Scarlet accent for identity and primary actions,
teal for runtime/memory state, yellow for public work notes, and semantic
warning/error colors.

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

Screenshots:

- [Desktop chat](assets/product-ui-prototype/desktop-chat.png)
- [Desktop developer lens](assets/product-ui-prototype/desktop-developer-lens.png)
- [Mobile chat](assets/product-ui-prototype/mobile-chat.png)
- [Mobile sessions](assets/product-ui-prototype/mobile-sessions.png)

## Approval Boundary

SCA-48 remains open until the owner explicitly approves the visual and
interaction direction. Approval permits SCA-50 to extract the accepted design
system and SCA-49 to connect the Product UI to Core ports. Until then:

- `/prototype` stays static;
- `/` and `/mobile` remain the real clients;
- no backend endpoint or stream consumer is changed;
- no prototype fixture is treated as runtime evidence.

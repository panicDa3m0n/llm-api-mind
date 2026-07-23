# Scarlet Product UI

Last updated: 2026-07-23
Current app target: V1.55.1; prototype is connected to the local Core
Linear issue: SCA-48
Status: implemented, owner-approved direction, first real Core integration

## Purpose

The `/prototype` route is the browser-first V2 Product UI. It is a
mobile-first React application connected to existing Core contracts. It does
not alter the existing `/` cockpit or `/mobile` consumer and does not invent
backend behavior for controls that the Core does not support.

As of 2026-07-23, the default route presents the sequential application path
from splash/startup through local test authentication and a Core-backed
post-login shell. Home, Chat, Memory, Sessions, and Profile use real health,
session, message, event, memory, profile, and runtime-settings data. The prior
multi-surface static preview remains available at
`/prototype?surface=product` for comparison. Real account storage, update
delivery, notifications, voice/avatar preferences, privacy workflows, and APK
behavior are intentionally not represented yet.

The splash introduces the approved character direction: Scarlet appears as an
adult anime woman around age 25, with visible makeup, dark plum hair, pearl and
graphite clothing, and Timber cyan/fuchsia identity accents. The current
transparent bust is the approved identity source for an active static-portrait
system. Scarlet will change among separately authored, identity-locked
emotional states through short fades and restrained presentation effects. It
does not simulate continuous facial motion or speech.

The current splash uses a pre-rendered HappyHorse greeting inside a circular
video bubble. Its opaque background and watermark are excluded by the crop.
Playback is muted and inline and uses the approved portrait as the loading,
error, and reduced-motion fallback. The video preloads from splash mount but
remains paused and hidden while startup checks run. After application and
media readiness converge, it plays once from zero; its completion transitions
the application to Login.

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

## Entry Flow

The default local flow is:

```txt
/prototype
-> asset-readiness splash
-> complete preloaded Scarlet greeting
-> Login
-> Core-backed Home dashboard
```

The loader follows portrait, font, interface-frame, and greeting-media
readiness. It does not implement update delivery; Core health becomes visible
after local test access.

The greeting media starts loading in parallel as soon as the splash mounts.
During checks it is held at zero beneath the canonical portrait. At `100%`,
the loader withdraws, the ready video plays exactly once, and its `ended`
event initiates the short fade to Login. It never loops in the entry flow.
Reduced motion, media failure, or a bounded readiness timeout use the static
portrait and continue safely to Login.

Each staged message replaces the former static `Sto arrivando` phrase so the
status reads as Scarlet speaking. The loader and progress bar sit immediately
beneath that message; the viewport bottom is reserved for copyright and the
current application version.

The authentication card contains Login and Registrazione tabs. The canonical
test login is:

```txt
username: scarlet
password: scarlet
```

Registration has no Core contract. Submitting it opens the shared centered
`Funzione non disponibile` modal and creates no local or server account.
Successful `scarlet/scarlet` test authentication opens the Product dashboard;
logout returns to the authentication card.

Primary actions preserve white text above their animated Scarlet-color hover
fill. The authentication card uses a clean perimeter without a decorative
colored edge on its left side.

Prototype-only review URLs allow each screen to be held independently:

```txt
/prototype?screen=splash
/prototype?screen=login
/prototype?screen=register
/prototype?screen=home
/prototype?screen=chat
/prototype?screen=memory
/prototype?screen=sessions
/prototype?screen=profile
```

## Home Dashboard

Home is the first post-login screen in the sequential approval flow. It places
Scarlet directly in the welcome hero, offers a primary new-conversation action,
and provides three compact summary cards for active memories, recent sessions,
and the latest encounter.

The lower workspace shows the three latest memories and three recent sessions.
Memory selection, session resume, and new conversation use the existing Core
contracts. Home hydrates health, the most recent sessions, dashboard memories,
profile, and runtime settings in parallel. Failed reads keep any previously
loaded real values, show the Core as unavailable, and never fall back to
fixtures. The same five-destination dock is used on desktop and mobile.

## Post-Login Screen First Passes

The shared post-login shell keeps Scarlet's gradient space, dock, Core status,
and active-view state consistent
across:

- Chat: empty/new state, starter prompts, persisted history, V2 public-event
  bubbles, real streaming composer, reconnect replay, and continuity preview;
- Memory: search, category filters, record selection, provenance-style detail,
  and source-session navigation;
- Sessions: chronological recent-session list, search, new conversation, and
  resume action;
- Profile: Core identity summary, supported runtime-preference editing,
  explicit unavailable controls, privacy boundary, and logout.

All supported controls now execute real contracts. Unsupported controls remain
visible for information-architecture continuity but open the same accessible
modal and never report a simulated success.

## Application Lifecycle Preview

The default `/prototype` entry now waits on the assets that materially gate the
first experience rather than advancing through artificial time stages:

1. the Scarlet portrait decodes, local fonts become ready, and the interface
   receives two animation frames;
2. the startup greeting preloads concurrently and remains paused/hidden;
3. as soon as application and media are both ready, the greeting plays from
   zero at natural `1x` speed;
4. playback stops at `52%` of the source, preserving the authored cadence while
   removing the unnecessary second half, then Login follows the same bounded
   completion path used by the native `ended` fallback.

Reduced motion, media failure, and a bounded media-readiness timeout retain the
portrait fallback. `?screen=splash` remains a held review mode.

Successful local test Login writes a minimal versioned session containing the
username and current Product view. Reloading or reopening `/prototype` restores
that view without replaying splash/login. Explicit logout removes the key and
returns to authentication. This is lifecycle simulation only: it is not secure
authentication or the future Capacitor storage contract.

## Chat Viewport Contract

Chat is the deliberate exception to normal page scrolling. It uses the entire
`100dvh` shell and composes four stable regions:

- a compact Chat header with a static Scarlet portrait and session identity;
- one message viewport that owns vertical scrolling;
- a composer that remains visible below messages; and
- the global five-destination bottom dock, plus the desktop continuity/JSON
  rail.

The body is locked only while `.is-chat-view` is mounted. Shell padding reserves
the mobile safe-area/dock region, so the composer cannot disappear under
navigation. Adding messages grows `scrollHeight` inside the message viewport,
not the document. Other long Product screens retain normal body scrolling.

### Semantic Turn Bubbles

The conversation no longer jumps directly from a user message to Scarlet's
final answer. Public persisted V2 events are rendered in semantic order:

```txt
user -> context -> memory -> reflection status -> public note
-> action receipt(s) -> relevant state -> final answer
```

Context, memory, action, and state bubbles are deterministic consumer
projections written in Scarlet's first-person voice. They describe observable
system movement without exposing route syntax, payloads, provider blocks, or
chain-of-thought. Their JSON receipts retain the compact source event families
that grounded the narration.

Public notes and final answers are different: their text is authored by
Scarlet and is not rewritten by the UI. `llm.thinking.captured` remains
private; the optional reflection bubble communicates only that a bounded
review occurred. Lifecycle duplicates such as tool started/requested/result/
completed are grouped into one action bubble.

The browser consumer validates the V2 schema/session identity, deduplicates by
`event_id`, orders by `(seq,event_id)`, rejects conflicts and sequence gaps,
pages replay until its durable cursor is complete, and requires
`turn.completed` or `turn.failed` rather than trusting stream closure. Only
`public` events become Product bubbles; persisted messages provide the
historical fallback.

## Inspectable Core Data And Settings

Chat, Memory, Sessions, and Profile show formatted JSON from the current Core
responses. Chat places its messages/events/reducer receipt in the desktop rail
and a mobile disclosure.

Profile/Settings uses one continuous surface separated by light Scarlet rules,
not one card for each command. It previews:

- real display-name, language, country, timezone, and privacy-scope fields;
- five visible future behavior switches;
- future privacy export/deletion;
- future consumer memory/session maintenance; and
- future voice, avatar, notification, and reminder extras.

Profile, privacy, and maintenance/extra areas each group multiple controls.
The supported environment fields persist through
`PUT /api/dashboard/settings`. Every unsupported command opens
`Funzione non disponibile`; it does not mutate local state or claim that work
completed. The explicit logout remains at the top of Settings.

## Scrolling Contract

The existing cockpit needs a fixed-height, internally scrolling three-pane
root. Most Product UI screens instead need normal page-level scrolling. While
`/prototype` is mounted, `PrototypeApp` applies a scoped document class that
restores the original classes on unmount. The scoped selectors explicitly
override the cockpit base with `height: auto`, `min-height: 100%`, and normal
vertical overflow on `html`, `body`, and `#root`; the browser's natural
document flow therefore owns page height.
Post-login view changes reset window, document-element, and body scroll
positions to the top. This contract is route-local and does not alter `/` or
`/mobile`. Chat temporarily sets only body vertical overflow to hidden and
moves scrolling into its measured message viewport; leaving Chat restores the
normal prototype page contract.

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

The application-entry pass additionally verified:

- greeting ready, paused at zero, and hidden during early splash loading;
- visible full greeting playback only after progress reaches `100%`;
- default transition to Login only after the greeting's `ended` event;
- Login and Registrazione at `390x844`;
- Login at `1440x1000`;
- invalid credential feedback and successful `scarlet/scarlet` access;
- session-only registration and subsequent access with the new credentials;
- exact mobile document/viewport width and no runtime exceptions.

The Home pass additionally verified:

- successful `scarlet/scarlet` navigation from Login to Home;
- Home at desktop `1440x1000` and mobile `390x844`;
- exact document/viewport width, responsive navigation, and no horizontal
  overflow;
- three summary cards, three latest memories, and three recent sessions from
  the dedicated fixture;
- simulated new-conversation feedback;
- zero API requests and zero runtime exceptions.

The post-login navigation pass additionally verified:

- effective page scrolling with `overflow-y:auto`, visible root overflow,
  no prototype document-level height constraints, and no horizontal overflow;
- mobile body scroll reaching its exact maximum on Home, Chat, Memory,
  Sessions, and Profile;
- automatic return of body, document-element, and window scroll positions to
  zero when changing post-login views;
- Chat, Memory, Sessions, and Profile from mobile navigation and Memory from
  desktop navigation;
- Home new/continue actions, quick-session summary, individual-memory selection,
  and recent-session resume;
- simulated Chat send, responsive mobile Memory detail replacement, and
  desktop two-column Memory layout;
- zero API requests and zero runtime exceptions.

The lifecycle/Chat/settings pass additionally verified:

- natural `1x` media playback, a cut at `52%`, real ready state, greeting start
  without a staged minimum, and Login only after bounded media completion;
- local Login session creation, last-view restoration across reload, explicit
  logout removal, and unauthenticated re-entry;
- mobile `390x844` body height exactly matching the viewport while Chat
  messages scroll internally and the composer remains above the dock;
- desktop `1440x900` body height exactly matching the viewport with compact
  Chat header, message viewport, composer, continuity, and JSON all bounded;
- JSON presence in Chat, Memory, Sessions, and Profile;
- one grouped Settings surface with four line-divided areas, seven grouped fake
  management commands, and five future prompt-rule preferences;
- removal of the shared Product header in favor of a five-destination bottom
  dock at mobile and desktop widths;
- extended `12.480` Memory totals and tabular `001` record numbering; and
- production TypeScript/Vite build with 2,032 transformed modules.

The semantic-event pass additionally verified:

- exact nine-block order from user message through final answer;
- visible context, memory, reflection, note, action, focus, and answer
  treatments at `390x844` and `1440x900`;
- fake send appending a second complete semantic turn;
- private thinking absent from rendered event families;
- message viewport, composer, and universal dock remaining independently
  bounded with the longer turn; and
- Chat JSON preserving authored/projection and source-event evidence.

The Scarlet Signal pass additionally verified the session trace, memory grid,
status surface, settings, developer lens, and reconnect state at the same
desktop/mobile viewports. The mobile document remains exactly viewport width
with no horizontal overflow.

Screenshots:

- [Mobile splash](assets/product-ui-prototype/mobile-splash.png)
- [Mobile entry splash with loader](assets/product-ui-prototype/mobile-entry-splash.png)
- [Mobile preloaded greeting transition](assets/product-ui-prototype/mobile-entry-greeting.png)
- [Mobile login](assets/product-ui-prototype/mobile-login.png)
- [Mobile registration](assets/product-ui-prototype/mobile-registration.png)
- [Mobile login success](assets/product-ui-prototype/mobile-login-success.png)
- [Desktop login](assets/product-ui-prototype/desktop-login.png)
- [Mobile Home](assets/product-ui-prototype/mobile-home.png)
- [Desktop Home](assets/product-ui-prototype/desktop-home.png)
- [Mobile Chat navigation pass](assets/product-ui-prototype/mobile-chat-navigation.png)
- [Desktop Memory navigation pass](assets/product-ui-prototype/desktop-memory-navigation.png)
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

## Current Boundary

SCA-49's first Core connection slice is implemented in V1.55.1 without adding
HTTP operations:

- `/prototype` consumes the existing 30-operation Core surface;
- `/` and `/mobile` remain unchanged parallel clients;
- local login is only a test gate, not account security;
- registration, account deletion, export, notifications, voice/avatar
  preferences, prompt-rule switches, and consumer maintenance are unavailable;
- Capacitor/Android packaging remains deferred until the browser application is
  complete.

V1.55.1 adds a repeatable browser gate and makes failed-turn replay part of the
consumer contract. `turn.failed` is rendered as a single translated terminal
bubble even when its canonical event retains diagnostic visibility; no other
debug/private event becomes user-visible.

# Device Exploration Layer

Last updated: 2026-07-26
Target version: V1.58.1
Status: experimental implementation

## Purpose

The Device Exploration Layer is a non-destructive laboratory for learning what
the Android device can expose to Scarlet's future peripheral runtime. It
captures actual payloads, timing, availability, permission outcomes, lifecycle
conditions, and failures before any signal is admitted into Scarlet's
cognition.

This layer is not a second agent, a local mind, a context source, a memory
writer, or an autonomous action system.

## Isolation Contract

```text
Capacitor/native probe
    -> raw observation
    -> normalized observation
    -> append-only experimental ledger
    -> technical Product UI
```

Device observations:

- are never added to chat sessions, provider history, semantic memory, focus,
  affect, volition, automatic retrieval, or `scarlet-model-context-v2`;
- are not available through `mind_shell`;
- remain traceable by device, exploration run, probe, client event id, device
  timestamp, server receipt timestamp, and app state;
- preserve both raw and normalized forms so later architectural choices can be
  based on evidence rather than assumed plugin behavior;
- are idempotent across offline retries through `client_event_id`.

## V1 Probe Surface

| Probe | Evidence |
|---|---|
| Device and app | install-scoped id, model, platform, OS, SDK, WebView, app version/build |
| Battery | charge level and charging state at snapshot time |
| Lifecycle | active/background transitions, pause, resume, launch URL |
| Network | connectivity and transport changes |
| Motion | sampled acceleration, gravity-inclusive acceleration, rotation, orientation |
| Location | permission state and explicit one-shot coordinates with accuracy |
| Notifications | permission, channels, scheduling, display, interaction, pending/delivered state |
| Haptics | requested effect and completion/error receipt |

Motion is sampled and batched rather than storing the native event rate. App
lifecycle observations use a persistent local outbox so a background event can
be delivered after resume. Location and notification permission requests are
explicit experimental actions.

Network observations retain each distinct connectivity/transport transition
but suppress an immediately repeated identical pair. Physical testing showed
that an upload can provoke an otherwise identical Android connectivity
callback; preserving those duplicates would let the laboratory observe its
own transport indefinitely without adding device-state information.

## API

- `POST /api/device-exploration/observations/batch`
- `GET /api/device-exploration/observations`
- `GET /api/device-exploration/summary`

The summary response explicitly reports:

```json
{
  "model_context_delivery": false,
  "cognitive_persistence": false
}
```

## Physical Evidence

Background and unlocked foreground runs establish:

1. device, app, battery, network, permission, notification, lifecycle, motion,
   explicit location, and haptic payloads are available;
2. observations survive temporary loss of transport through the local outbox;
3. foreground location works while the same request can time out when the app
   is locked/backgrounded;
4. notification scheduling, delivery, and user interaction are separately
   observable;
5. pause/background/resume and Wi-Fi/cellular transitions are timely and
   ordered; and
6. stationary motion is stable at the current three-second sample cadence.

Deliberately moved-device motion remains a future physical comparison.

Admission into Scarlet's perception will be designed only after these results
have been reviewed.

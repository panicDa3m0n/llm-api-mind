# Device Exploration Layer

Last updated: 2026-07-26
Target version: V1.58.0
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

## Experimental Questions

The first device run should establish:

1. which plugin payloads are available on the physical Samsung device;
2. which observations survive background/resume through the local outbox;
3. how frequently motion changes remain meaningful after sampling;
4. location precision and latency under coarse and precise permission;
5. notification scheduling, display, and interaction receipts;
6. whether network and lifecycle transitions are timely enough to become
   future peripheral triggers;
7. which raw fields have no plausible cognitive use and should remain
   technical evidence only.

Admission into Scarlet's perception will be designed only after these results
have been reviewed.

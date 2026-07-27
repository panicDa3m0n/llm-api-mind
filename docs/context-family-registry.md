# Context Family Registry

Last updated: 2026-07-27
Target version: V1.60.0
Status: typed registry and shadow routing active; perception inbox exists but
native future sources are not admitted

## Purpose

The context-family layer prepares Scarlet for device continuity, personal
events, environment perception, and embodiment without turning every sensor
payload into prompt text.

It sits between technical evidence and model context:

```text
raw source
-> normalized technical observation
-> semantic adjudication or state update
-> compact context-family packet
-> agent-mode eligibility
-> required policy composition
-> bounded model projection
```

V1.59.0 implements the registry, packet validation, policy dependencies,
mode-tag planning, model-context audit, and isolated simulations. It does not
admit Device Exploration records or any new source to Scarlet.

## Classification Axes

Every family and packet keeps four questions separate.

| Axis | Question | Examples |
|---|---|---|
| `subject_domain` | What or whom is this evidence about? | `human`, `human_device`, `scarlet`, `relationship`, `shared_environment`, `operation` |
| `observer_domain` | What acquired or derived it? | `core_runtime`, `human_device`, `scarlet_sensor`, `external_service`, `home_system`, `derived_cognition` |
| `evidence_kind` | What kind of claim is it? | direct observation, system record, self-state, derived assessment, operation state, operation result |
| `mode_tags` | In which foreground postures may it become eligible? | `idle`, `interactive`, `scouting` |

The first two axes must never be collapsed. A GPS reading directly observes
the human's phone, not the human. A later assessment may relate that reading
to the human, but it must be a separate `derived_assessment` with its own
source references. A camera or microphone on the human's device is not
Scarlet's own vision or hearing. Only `observer_domain=scarlet_sensor` can
support first-person sensory language.

Mode eligibility is necessary but not sufficient. The family must also meet
its activation contract:

- `always`: part of the current compact spine;
- `source_present`: a configured organ produced a current block;
- `relevance_or_operation`: a source became relevant to the current exchange
  or an active operation explicitly requires it;
- `active_operation`: an authorized operation ledger is active.

This prevents a mode tag from flooding every interactive turn with every
available sensor.

## Registered Families

| Family | Main subject/source boundary | Modes | Activation | V1.59 status |
|---|---|---|---|---|
| `session_continuity` | relationship / Core records | all | always | existing V2 |
| `memory_continuity` | mixed durable subjects / Core and derived retrieval | all | always | existing V2 |
| `operational_orientation` | human and locale / Core record | all | always | existing V2 |
| `agent_posture` | Scarlet / Core self-state | all | always | existing V2 |
| `foreground_attention` | Scarlet / focus organ | all | source present | existing conditional |
| `affective_posture` | Scarlet / affect appraisal | interactive, scouting | source present | existing conditional |
| `metacognitive_guidance` | Scarlet / derived cognition | interactive, scouting | source present | existing conditional |
| `human_device_state` | human device / human device | all | relevant or operation | shadow |
| `human_device_observation` | human or environment / human-device media | interactive, scouting | relevant or operation | shadow |
| `human_situated_presence` | human / explicit derived cognition | all | relevant or operation | shadow |
| `human_personal_events` | human or relationship / device or account record | idle, interactive | relevant or operation | shadow |
| `human_wellbeing` | human / device, account, or derived evidence | all | relevant or operation | shadow |
| `scarlet_perceptual_scene` | Scarlet, human, or environment / Scarlet sensor | interactive, scouting | relevant or operation | shadow |
| `shared_environment` | environment / Scarlet sensor, home system, or service | all | relevant or operation | shadow |
| `relationship_continuity` | relationship / Core and derived cognition | idle, interactive | relevant or operation | shadow |
| `active_operation` | operation / Core, device, service, or home receipt | all | active operation | shadow |

`shadow` means classified and testable, not model-facing.

## Packet Contract

A future model-usable packet is compact and sourceable:

```json
{
  "schema_version": "scarlet-context-family-packet-v1",
  "packet_id": "ctx_...",
  "family_id": "human_device_state",
  "subject_domain": "human_device",
  "observer_domain": "human_device",
  "evidence_kind": "direct_observation",
  "observed_at": "2026-07-26T18:10:00+02:00",
  "summary": "The phone reported a point outside the expected route.",
  "data": {
    "route_state": "unexpected"
  },
  "source_refs": [
    "device_observation:dev_obs_..."
  ]
}
```

The packet requires an offset-aware evidence time and at least one navigable
source reference. Unknown families, invalid subject/source combinations, and
unsupported evidence kinds fail closed.

Raw sensor streams, plugin payloads, maintenance fields, routing diagnostics,
and policy text are not packet data. They remain in technical storage,
trace/evaluation, or the separate policy composer.

## Policy Coupling

Every family declares at least one versioned policy block. Common blocks cover:

- evidence versus instruction;
- subject versus observer perspective; and
- temporal scope and freshness.

Family-specific blocks cover session hints, memories, Scarlet self-state,
human-device evidence, human-presence inference, personal events, wellbeing,
Scarlet perception, shared environment, relationship, and operations.

The composer resolves and deduplicates only the blocks required by the active
families. Policy blocks are instructions and must be composed in the system
policy channel. Context-family packets are evidence and remain in the dynamic
context channel. Putting policy prose inside packet JSON weakened adherence in
the first MiniMax probe; composing the same policy as instruction removed the
observed source-perspective leak.

## Shadow Runtime

The current V2 document is unchanged. During V2 projection, the backend now
classifies the already delivered families and adds a
`projection_audit.context_family_routing` receipt to the `model.context` trace.

The receipt records:

- registry version and active mode;
- candidate, mode-eligible, and mode-ineligible families;
- status and activation contract;
- required policy block ids; and
- the explicit facts that live routing was not applied and current model
  context was unchanged.

The existing agent-mode block router remains the live delivery authority.
Future family activation must not become active until a separate release
defines source admission, freshness, batching, cost, permission, and rollback.

## Simulation Evidence

Focused deterministic tests cover:

- registry and policy completeness;
- device location remaining device evidence;
- human situated presence requiring a separate derived packet;
- a human-device camera being invalid as Scarlet perception;
- Scarlet sensor evidence retaining first-person provenance;
- operation dispatch remaining distinct from completion receipt;
- mode-tag combinations; and
- fail-closed unknown families and invalid evidence kinds.

A bounded MiniMax M3 probe used three natural scenarios:

1. a phone route deviation inside a simulated safeguard operation;
2. a frame from the human's phone camera; and
3. a haptic dispatch without a completion receipt.

MiniMax kept phone position separate from human position, did not call the
phone camera Scarlet's own vision, stayed inside the operation's authorization,
and did not claim haptic success without a receipt. In the first version,
policy prose embedded inside JSON still produced the metaphor "what I see".
The corrected composition placed policy blocks in the instruction channel and
packets in the evidence channel; the repeat named the device as source and
kept observation, inference, and authorization distinct.

These are bounded simulations, not proof of continuous sensor routing,
background reliability, anomaly detection, or safe embodiment.

## Next Gates

1. Derive a shadow adapter from real Device Exploration observations while
   keeping its output outside model context.
2. Define freshness, coalescing, change detection, and per-family token
   budgets from physical evidence.
3. Add a policy-block composer behind a shadow equivalence trace for the
   current complete system prompt.
4. Evaluate event-to-family adjudication for motion, location, lifecycle,
   notification, and action receipts.
5. Activate one low-risk family only after deterministic, behavioral, privacy,
   permission, and rollback contracts are approved.

# Endogenous Cognition V1

Last updated: 2026-07-30
Target: V1.65.1 integration hardening
Implementation status: complete locally; focused deterministic and simulated
M3 lifecycle evidence accepted; V1.65.1 scheduling integration and production
observation pending
Linear: SCA-58

## Purpose

Endogenous Cognition gives Scarlet bounded opportunities to work from her own
continuity even when no fresh external event has arrived. It extends the
existing Cognitive Workspace; it does not create another agent, history,
memory system, volition system, or context compiler.

The implementation separates four authorities:

```txt
backend cadence = a free cognitive window is available
M2.7 synthesis = zero or more provisional, source-backed impulse seeds
M2.7 workspace gate = whether a seed deserves M3 attention now
M3 Scarlet = inspect, reject, suspend, explore, or deliberately adopt
```

A window is not boredom. A seed is not a desire, emotion, intention, fact, or
command. Only Scarlet M3 can turn a seed into a bounded episode or a durable
volition. Producing no seed and doing no work are valid outcomes.

## Adaptive Windows

The autonomy worker continues to tick frequently for due work, but it opens an
endogenous window only when the persisted `next_window_at` is due.

Defaults:

| Setting | Value | Meaning |
|---|---:|---|
| minimum interval | 900 seconds | retry floor and provider-failure interval |
| base interval | 3600 seconds | initial free-window interval |
| productive follow-up | 1800 seconds | next review after useful seeds |
| maximum interval | 10800 seconds | auxiliary free-window ceiling |
| maximum seeds | 4 | bounded proposal count |

Consecutive empty windows double the prior interval up to the maximum.
Productive windows return to the productive follow-up. This is deterministic
resource scheduling, not a numeric judgment of semantic importance.

Every window has an idempotent `schedule_key` derived from the previous
window. Concurrent worker/manual ticks therefore reuse one opening instead of
launching duplicate M2.7 synthesis.

## Source Substrate

The auxiliary worker receives a bounded snapshot from canonical owners:

- up to three recent human-session summaries, with ids and navigation hints;
- up to six memories ordered by meaningful activity, with canonical source
  session/turn/message ids;
- the available memory-graph neighborhood as association evidence;
- active focus;
- open volitions and due-review metadata;
- active or suspended cognitive episodes and explicit expectations;
- current affective posture; and
- recent device-derived perception transitions admitted by the V1 adapter.

The substrate is persisted with the window and trace. Session summaries and
memories remain hints; graph edges remain associations; device records remain
evidence about the human's device. M2.7 must cite exact supplied
`source_ref` values. Invalid references and invalid structured output fail
closed.

## Impulse Families

The V1 synthesis contract supports:

- `personal_continuity`;
- `curiosity`;
- `growth`;
- `relationship`;
- `responsibility`;
- `exploration`;
- `creativity`; and
- `regulation`.

These labels organize candidate questions. They do not constitute separate
organs or deterministic drives. M2.7 cannot call `mind_shell`, mutate state,
write memory, or speak as Scarlet.

## Competition And Scarlet Authority

Valid seeds become ordinary `cognitive_candidates` with exact source links,
stable fingerprints, context-family classification, and
`m3_endorsement_required=true`. They compete in the existing workspace pool
with event, perception, due-volition, and wake-condition candidates. No new
priority score is introduced.

If the gate selects an endogenous candidate, the existing autonomy runtime
schedules Scarlet M3 and includes a compact provisional workspace hook.
Scarlet may:

- reject the candidate;
- open or continue a cognitive episode;
- suspend it for explicit later review;
- inspect sources without adopting it;
- create or review a volition with `--candidate-id cand_...`; or
- conclude that no useful transformation exists.

A candidate-linked volition is explicit adoption evidence. The candidate is
resolved into that existing volition rather than becoming a second intention
record. If Scarlet makes no explicit episode, volition, or rejection decision,
the candidate is parked and remains inspectable. It does not re-enter merely
because a timer elapsed; M2.7 must cite genuinely new source evidence to reopen
the same candidate.

## Outcome Evidence

After the M3 activation, the window records:

- activation status and turn id;
- selected candidate lifecycle;
- linked episode ids or resolutions; and
- whether an explicit transformation was observed.

This feedback is descriptive. It does not assign a quality score to Scarlet's
choice and does not train or rewrite any organ automatically.

## Device Admission V1

The Device Exploration ledger remains immutable technical evidence. A narrow
adapter may derive only these compact transitions into the perception inbox:

- app lifecycle change, pause, or resume;
- network connectivity/transport change;
- explicit location observation; and
- notification interaction.

Raw motion, snapshots, battery samples, haptic requests, and other laboratory
records remain outside cognition. The derived event keeps the raw observation
id for navigation and declares
`perspective=human_device_not_scarlet_sensor`. It is never automatically
inserted into normal chat context.

`DEVICE_PERCEPTION_ADMISSION_MODE=off|shadow|active` provides rollback.
`active` is the local V1 target.

## Failure And Rollback

- no substrate: persist an empty window and back off;
- invalid M2.7 output after one repair: persist `invalid_output`, create no
  candidate, wake no M3;
- provider failure: persist trace/error and retry at the minimum interval;
- duplicate seed fingerprint: reuse canonical candidate state;
- concurrent opening: reuse the idempotent window;
- `ENDOGENOUS_COGNITION_ENABLED=false`: stop endogenous seed synthesis while
  the active Workspace scheduler still retains the bounded M3
  maximum-silence orientation contract;
- `COGNITIVE_WORKSPACE_MODE=shadow|advisory|off`: retain the existing
  workspace rollback semantics.

Canonical histories, memories, organ records, events, perception records, and
Device Exploration observations are not deleted by rollback.

## Current Evidence And Limits

Focused tests verify:

- source-backed synthesis over real persisted session, memory, and graph
  records;
- M2.7-only auxiliary synthesis and arbitration;
- adaptive empty-window backoff without M3 activation;
- a complete simulated M3 activation that adopts a seed through
  `mind_shell`, creates one linked volition, resolves the candidate, and
  records transformation evidence;
- selective device transition admission; and
- compatibility with existing Cognitive Workspace, autonomy, volition, and
  shell tests.

The complete local backend suite passes `350` tests. Ruff, compileall, mypy
over the configured typed surfaces, documentation/skill integrity, frontend
production build, and a copied legacy-SQLite migration canary also pass.

This evidence proves lifecycle and ownership contracts. It does not yet prove
that real M2.7 proposals are consistently useful, that real Scarlet varies her
internal activity appropriately over time, or that the default cadence is
cost-effective. Those require bounded field observation before production
acceptance.

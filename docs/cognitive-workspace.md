# Cognitive Workspace And Event-Driven Autonomy

Last updated: 2026-07-28
Target: V1.63.0
Implementation status: V1.62 workspace complete; V1.63 endogenous extension
complete locally and awaiting deployment
Linear: SCA-57

## Purpose

The Cognitive Workspace replaces blind periodic activation with a traceable
admission path for autonomous Scarlet cognition. It does not replace memory,
focus, volition, affect, perception, sessions, runtime context, or canonical
events. Those owners continue to hold their own state.

The workspace answers a narrower question:

```txt
Did new source-backed evidence create a cognitive question worth presenting
to Scarlet now, later under an explicit condition, or not at all?
```

It is deliberately not a numeric importance scorer and not a second Scarlet.
Its outputs are provisional. Only a full Scarlet activation may interpret,
accept, suspend, connect, or reject the proposed work.

## Model Ownership

The provider boundary is explicit:

| Work | Model |
|---|---|
| Human-facing Scarlet turn | MiniMax M3 |
| Autonomous Scarlet activation | MiniMax M3 |
| Signal appraisal | MiniMax M2.7 |
| Candidate ignition recommendation | MiniMax M2.7 |
| Maintenance summaries and semantic review | MiniMax M2.7 |
| Answer validators and other non-Scarlet LLM work | MiniMax M2.7 |

M2.7 components are stateless semantic workers. They cannot call
`mind_shell`, mutate cognitive organs, write memory, or speak as Scarlet.
M3 remains the only native Scarlet model.

## Data Flow

```txt
canonical event / perception / due condition
  -> source registry classification
  -> persistent signal receipt
  -> M2.7 source-backed appraisal
  -> provisional cognitive candidate
  -> M2.7 ignition recommendation or deterministic wake contract
  -> shadow receipt, periodic advisory, or active M3 activation
  -> Scarlet inspects sources through the existing mind_shell
  -> Scarlet opens, checkpoints, suspends, resolves, abandons, or rejects
     through the episode family
```

Every observed source receives a receipt even when it is ignored, invalid,
trace-only, deferred, or rejected by structured validation. Unknown source
types fail closed and never become model work merely because they exist.

## Source Registry

`backend/app/mind/wake_registry.py` owns the versioned deterministic registry.
It maps exact event names and accepted prefixes to one of these policies:

| Policy | Meaning |
|---|---|
| `trace_only` | Persist observation, never appraise or wake. |
| `episode_evidence` | Attach as evidence to existing work when applicable. |
| `candidate` | Ask M2.7 whether a source-backed candidate exists. |
| `required_wake` | A validated deterministic contract requires a Scarlet wake. |
| `invalid` | Unknown or malformed source; fail closed. |

Workspace-generated `cognition.*` events are trace-only. This prevents the
workspace from recursively waking itself from its own bookkeeping.

## Persistent Contracts

The implementation adds these append-oriented records:

| Record | Function |
|---|---|
| `cognitive_signal_cursors` | Last scanned canonical source position. |
| `cognitive_signal_receipts` | Disposition for every observed source. |
| `cognitive_candidates` | Provisional semantic questions with exact sources. |
| `cognitive_candidate_sources` | Candidate-to-source provenance. |
| `cognitive_arbitrations` | M2.7 gate result for an exact candidate pool. |
| `cognitive_episodes` | Scarlet-owned bounded cognitive work. |
| `cognitive_episode_candidates` | Candidate membership and ordering. |
| `cognitive_episode_steps` | Progress or explicit non-progress checkpoints. |
| `cognitive_episode_expectations` | Testable predictions and later outcomes. |
| `autonomous_wake_conditions` | Deterministic future wake contracts. |

`autonomous_activations` gains optional candidate, episode, wake-condition,
and workspace references. Existing activation history and the separate
`scarlet_autonomous` provider chronology remain canonical.

## Candidate Contract

A candidate must contain:

- one or more exact source references;
- a bounded candidate kind and context family;
- a sourceable claim;
- why the question may matter now;
- the cognitive question;
- the expected transformation;
- explicit uncertainty; and
- a stable exact fingerprint for deduplication.

Candidate state is not a truth judgment. `proposed`, `selected`, `suspended`,
`resolved`, and `rejected` describe lifecycle, not epistemic certainty.
M2.7 may recommend `hold`, `consider`, or `wake_now`, but cannot make the
final Scarlet decision.

## Arbitration Without Synthetic Scores

The ignition gate compares a bounded candidate pool using semantic criteria:

- new evidence;
- connection to active episodes;
- deterministic due conditions;
- expected cognitive transformation;
- reversibility;
- whether waiting loses a real opportunity; and
- whether candidates form one coherent coalition.

No hand-authored weight or scalar priority decides meaning. The structured
gate may return `now`, `hold`, or `none`, and may return no selected
candidate. Identical pool fingerprints reuse their persisted arbitration,
avoiding repeated model calls and repeated wakes without declaring semantic
duplication.

## Modes

`COGNITIVE_WORKSPACE_MODE` controls admission:

| Mode | Behavior |
|---|---|
| `off` | Workspace does not inspect sources. Existing periodic autonomy remains. |
| `shadow` | Appraise and arbitrate with M2.7, persist evidence, never schedule M3. |
| `advisory` | Attach selected candidates to the already scheduled periodic activation. |
| `active` | Event/condition ignition schedules M3; blind periodic wakes are disabled. |

The default is `active` so field verification exercises the complete path from
new evidence to an actual Scarlet M3 cycle. `shadow` remains the immediate
non-waking rollback and retrospective replay mode.

When `active` starts, any still-pending blind `periodic` activation is
cancelled with a persisted reason and lifecycle event. Started or genuinely
deferred work is preserved.

In V1.63 `active`, the fixed watchdog delegates to adaptive endogenous
cognitive windows. Those windows may propose no work and back off up to a
configured ceiling. Disabling Endogenous Cognition restores the prior bounded
watchdog behavior.

## Endogenous Extension

V1.63 adds a source-backed internal substrate and adaptive free-window ledger
without changing the candidate, arbitration, episode, activation, history, or
organ owners. Endogenous seeds enter the same candidate pool as external
events and due conditions. M2.7 cannot turn a seed into a desire. M3 Scarlet
must reject it, suspend it, open an episode, or explicitly link it to an
existing volition through `--candidate-id`.

The complete contract, cadence, device-admission boundary, rollback, and
current evidence are documented in `docs/endogenous-cognition.md`.

## Historical Replay

Existing evidence can be replayed only through the explicit
`replay_existing=True` laboratory path and only while the workspace is in
`shadow`. The gate rejects replay in `advisory` and `active` before reading or
mutating workspace state, so historical evidence cannot schedule Scarlet M3.

Archived autonomous `turn.completed` events receive a trace-only receipt. They
remain inspectable as Scarlet's internal chronology, but completion of one
autonomous cycle is not treated as a fresh reason to start another. Focus,
volition, affect, perception, and other canonical evidence encountered during
a replay still follow the same versioned source registry as live evidence.
Replay must run against an isolated or approved database copy; it is not a
production reset or migration operation.

## Wake Conditions

Current deterministic conditions are intentionally narrow:

- `at_time`: wake at or after one explicit instant;
- `on_event`: wake on one exact registered event type;
- internal `semantic_recheck`: reconsider a suspended candidate;
- internal `max_silence`: watchdog orientation.

Natural-language conditions are not silently compiled into deterministic
predicates. A condition has lifecycle, source ownership, not-before time,
match evidence, and cancellation history.

## Cognitive Episodes

The `episode` shell family is the Scarlet-owned control plane:

```txt
episode list [--status active|suspended|resolved|abandoned]
episode read <episode_id>
episode open --candidate-id <candidate_id>
episode checkpoint <episode_id> ...
episode suspend <episode_id> ...
episode resume <episode_id>
episode resolve <episode_id> ...
episode abandon <episode_id> ...
episode reject --candidate-id <candidate_id> ...
episode expectation-add <episode_id> ...
episode expectation-resolve --expectation-id <id> ...
episode wake-list
episode wake-add ...
episode wake-cancel --condition-id <id>
```

Opening an episode requires a source-backed candidate. Checkpoints preserve
progress or explicit non-progress. Suspension requires a reason and may add a
deterministic resume contract. Resolution and abandonment retain evidence.
Reject lets Scarlet overrule an auxiliary proposal.

The shell remains the one model-facing tool. Internal logical
`/mind/episode` dispatch is reached through `/mind/call` for deterministic
tests and adapters; it is not an independent FastAPI route or a second model
tool.

## Runtime Integration

`backend/app/runtime/autonomy.py` remains the owner of actual Scarlet
execution, leases, human-turn foreground priority, provider streaming,
history, and completion. The workspace only schedules or annotates an
activation.

An M3 autonomous activation receives one compact `workspace` packet with:

- selected candidate summaries;
- exact navigable source references;
- linked episode or wake condition when present; and
- explicit language that M2.7 appraisal is provisional.

The rest of the turn still uses the same `scarlet-model-context-v2`, static
prompt, automatic retrieval, organs, provenance, and `mind_shell` as human
interaction. No parallel cognitive runtime is introduced.

If Scarlet completes without making an episode decision, the candidate is
suspended for reconsideration rather than falsely marked resolved.

## API And UI Inspection

Additive operator/developer surfaces:

```txt
GET  /api/autonomy/workspace
POST /api/autonomy/workspace/tick
```

The read surface exposes candidates, episodes, wake conditions, signal
receipts, and arbitrations for the active profile. The tick route is a bounded
laboratory control, not a consumer action.

Autonomous history responses include workspace references. Product Chat may
show a compact explanation of why a cognitive cycle began, while technical
records remain expandable.

## Failure Semantics

- Unknown sources fail closed.
- Provider failures keep the receipt pending with bounded retry time.
- Invalid M2.7 structured output gets one repair attempt, then becomes
  explicit insufficient evidence.
- A malformed or missing source never becomes a candidate.
- `shadow` can never schedule Scarlet.
- Human foreground priority still defers or yields autonomous work.
- No candidate or episode authorizes an external/device action.
- Canonical histories and source events are never deleted by workspace state.

## Verification

V1.62.0 local evidence:

- full backend suite: `345 passed`;
- focused workspace, autonomy, and archival-reset tests: `22 passed`;
- frozen preliminary regression: `9/9` before and `9/9` after;
- frontend production build passes;
- Ruff, compileall, and isolated changed-file mypy pass;
- legacy SQLite canary adds activation references and all workspace tables;
- one real isolated M2.7 `shadow` probe created a source-backed candidate for
  an explicitly postponed human thread, then the ignition gate sensibly chose
  no immediate wake;
- one real disposable `active` probe admitted a certified decision event,
  executed MiniMax M3 Scarlet, opened, checkpointed, and resolved its episode
  through nine shell calls, and completed the activation in 38.7 seconds;
- a lower-budget probe returned invalid structured output and was safely
  rejected without candidate creation or M3 activation, confirming the
  fail-closed path.

No production database was used or mutated. V1.62.0 has not been deployed.

## Deliberate Limits

- The source registry is small and must grow only with real source contracts.
- `active` mode lacks longitudinal production evidence.
- Semantic recheck scheduling is implemented but not yet behaviorally tuned.
- Candidate conflict and memory duplicate adjudication remain separate work.
- External initiative, notifications, device action, and embodiment safety are
  outside this version.
- The runtime coordinator is functionally separated from contracts, storage,
  registry, shell, and autonomy, but remains a large module that should be
  split after behavior stabilizes rather than during first admission work.

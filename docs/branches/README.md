# Agentic Branches

Last updated: 2026-07-14
App baseline: V1.36.0
Status: canonical branch map

An agentic branch is an operating domain of Scarlet: what she can perceive,
remember, regulate, communicate, decide, or do. Tests, traces, providers,
schemas, storage, and UI are support infrastructure and must be mapped to the
behavior they make possible.

## Maturity Scale

```txt
L0 idea
L1 planned
L2 implemented prototype
L3 deterministically tested implementation
L4 validated in direct Scarlet use
L5 mature lab-core
```

Maturity is assessed separately from default activation. A disabled or
manual-only organ can be L3 technically while remaining absent from ordinary
turns. Every branch document must state:

- implemented code/storage/tool/UI;
- deterministic tests;
- direct Scarlet evidence;
- default runtime integration;
- limits and next acceptance step.

## Current Assessment

| Branch | Level | Implementation | Runtime/behavior | Next gate |
|---|---:|---|---|---|
| Communication | L4 | Prompt, stream semantics, public notes, dev/mobile rendering, executable behavioral suite | active; good but not uniformly proportional | expand natural scenarios to notes, greetings and long work |
| User flows | L2/L3 | dev cockpit and mobile prototype | active UI, incomplete lifecycle/product flows | onboarding/privacy/session workflows |
| Perception and context | L4 | shared V2, accounting v2, exact chronology map, mode router | active routing; token-partition compaction shadow-only | recursive summary persistence and approved active derived router |
| Identity and relationship | L3 | golden identity prompt, profile name, personal memory | active but mostly prompt/memory-driven | longitudinal relational model/eval |
| Memory | L4+ | semantic, facts, episodic, KG, retrieval, lifecycle, maintenance | active and best-tested | duplicate/conflict and ownership maturity |
| Learning and adaptation | L2 | memory/preferences and project experiment loop | indirect, no controlled learning cycle | learning ledger and before/after metrics |
| Metacognition | L3 | one route, retrospective modes, shadow lessons, repeated broad-claim scenario | model-invoked; explicit review used 1/3 and skipped runs overgeneralized evidence | continuation and degradation policy |
| Operational management | L2/L3 | focus organ, agent posture, events/maintenance | focus natural lifecycle variable; mode active | calibrate focus behavior before goal/task organ |
| Decision autonomy | L2/L3 | model-controlled shell, resumable mode, volition register | natural volition persistence 1/3; no autonomous cycle | clarify autonomous persistence, then risk/receipt policy |
| External operativity | L1 | supporting traces/events only | no external-world action suite | permission/safety/rollback architecture |
| Advanced operations | L1 | no specialist suite | future | define only after operativity governance |
| Governance/privacy/safety | L2 | DB roles, profile hints, audit, field ownership | single-user convention only | authenticated ownership and data rights |
| Computational affect | L3 | appraisal, persistence, read-only shell, optional block | explicit exasperation remained below threshold 3/3 | BUG-0082 shadow/model calibration |
| Multi-agent/subprocesses | L1/L2 | maintenance worker is bounded background processing | not a multi-agent system | prove one-agent limits before expansion |

The integrated evidence and priority ordering live in
`docs/project-state.md`.

## Branch Documents

- `communication.md`
- `user-flows.md`
- `perception-context.md`
- `identity-relationship.md`
- `memory.md`
- `learning-adaptation.md`
- `metacognition.md`
- `operational-management.md`
- `decision-autonomy.md`
- `external-operativity.md`
- `advanced-operations.md`
- `governance-privacy-safety.md`
- `computational-affect.md`
- `multi-agent-subprocesses.md`

`memory-field-fix-backlog.md` is a historical/detail backlog under the memory
branch, not a separate branch.

## Update Rules

Update a branch document when implementation, tests, live evidence, default
activation, limits, or priority changes. Preserve experiment/activity history;
correct the current branch assessment rather than rewriting old observations.

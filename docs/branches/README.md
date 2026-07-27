# Agentic Branches

Last updated: 2026-07-28
App baseline: V1.50.1 deployed and release-accepted; V1.63.0 rollout target
Status: canonical branch map

The V1.50.1 Core is closed and release-accepted. Branch maturity remains a
research map: a `Next gate` is a future acceptance idea, not evidence that the
Core is unfinished. Promote branch work only through the active V2 roadmap or
an explicit owner decision. Architecture boundaries live in
`docs/core-runtime-contract.md`.

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
| Communication | L4 | Prompt, stream semantics, public notes, completion and answer-obligation invariants, dev/mobile rendering, executable behavioral suite | active; V1.50.1 preserves the marker path and semantically judges only a corrected second miss | monitor validator quality and expand natural scenarios |
| User flows | L2/L3 | dev cockpit and mobile prototype | active UI, incomplete lifecycle/product flows | onboarding/privacy/session workflows |
| Perception and context | L4 core + L2/L3 device adapter | one shared human/autonomous V2, source provenance, perception inbox, accounting v2, exact chronology map, mode router, semantic family registry, recursive compaction artifacts, Android observation ledger and bounded transition adapter | common context/retrieval active; separate source-labelled histories; family router shadow; selected device transitions may enter perception but never automatic chat context | observe real adapter evidence and calibrate freshness/coalescing before expansion |
| Identity and relationship | L3 | golden identity prompt, profile name, personal memory | active but mostly prompt/memory-driven | longitudinal relational model/eval |
| Memory | L4+ | semantic, facts, episodic, KG, retrieval, lifecycle, maintenance; V1.50 verifies actual model delivery | active and best-tested | duplicate/conflict and ownership maturity |
| Learning and adaptation | L2 | memory/preferences and project experiment loop | indirect, no controlled learning cycle | learning ledger and before/after metrics |
| Metacognition | L3/L4 | one route, retrospective modes, shadow lessons, positive/negative controls | V1.40 broad reviews 2/2 and direct controls 2/2; one run overprocessed | answer-obligation and proportionality policy |
| Operational management | L3/L4 | focus organ, agent posture, autonomous activation ledger, events/maintenance | focus lifecycle, mode receipts, two-session resume, and deterministic autonomous-cycle contracts pass | validate long-lived cycle use without collapsing focus, volition, and mode |
| Decision autonomy | L3/L4 | model-controlled shell, resumable mode, volition register, final-answer obligations, shared Cognitive Workspace/episodes, adaptive endogenous windows and explicit candidate-to-volition endorsement | V1.62 appraises external evidence with M2.7; V1.63 also proposes source-backed internal seeds while only M3 runs Scarlet and may adopt them | production observation of variation, non-repetition, no-work outcomes, cadence cost, and M3 choices |
| External operativity | L1 core + L2 device lab | supporting traces/events plus isolated haptic and notification probes | no external-world action suite; lab receipts are not Scarlet actions | evaluate peripheral receipts before permission architecture |
| Advanced operations | L1 | no specialist suite | future | define only after operativity governance |
| Governance/privacy/safety | L2 | DB roles, profile hints, audit, field ownership | single-user convention only | authenticated ownership and data rights |
| Computational affect | L3/L4 | appraisal, persistence, read-only shell, optional block | V1.40 model/shadow/neutral 10/10 after recovery fix; shadow default | prove model-facing benefit before activation |
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

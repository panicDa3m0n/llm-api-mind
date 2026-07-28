# Agentic Branches

Last updated: 2026-07-28
App baseline: V1.50.1 closed-Core baseline; V1.65.0 deployed on the protected
VPS
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
| Communication | L4 | Prompt, stream semantics, public notes, provider finality, dev/mobile rendering, executable behavioral suite | active; V1.64 uses structural finality and no second-model semantic answer judge | observe source discipline directly and expand natural scenarios only when requested |
| User flows | L2/L3 | dev cockpit and mobile prototype | active UI, incomplete lifecycle/product flows | onboarding/privacy/session workflows |
| Perception and context | L4 core + L2/L3 device adapter | one shared human/autonomous V2, source provenance, perception inbox, accounting v2, exact chronology map, mode router, semantic family registry, recursive compaction artifacts, Android observation ledger and bounded transition adapter | common context/retrieval active; separate source-labelled histories; family router shadow; selected device transitions may enter perception but never automatic chat context | observe real adapter evidence and calibrate freshness/coalescing before expansion |
| Identity and relationship | L3 | golden identity prompt, profile name, personal memory | active but mostly prompt/memory-driven | longitudinal relational model/eval |
| Memory | L4 | semantic memory, episodic recall, KG hooks, reranked retrieval, lifecycle, and proposal ledger; legacy facts are audit-only | active and well-tested; V1.64 removes heuristic fact authority and automatic semantic maintenance mutation | Scarlet-owned proposal adoption and later duplicate/conflict design |
| Learning and adaptation | L2 | memory/preferences and project experiment loop | indirect, no controlled learning cycle | learning ledger and before/after metrics |
| Metacognition | L3/L4 | one LLM-backed route, retrospective modes, positive/negative controls, observational runtime trace | explicit command active; automatic keyword lesson injection retired in V1.64 | proportional use and direct behavioral observation |
| Operational management | L3/L4 | focus organ, agent posture, autonomous activation ledger, events/maintenance | focus lifecycle, mode receipts, two-session resume, and deterministic autonomous-cycle contracts pass | validate long-lived cycle use without collapsing focus, volition, and mode |
| Decision autonomy | L3/L4 | model-controlled shell, resumable mode, volition register, structural finality, shared Cognitive Workspace/episodes, adaptive endogenous windows and explicit candidate-to-volition endorsement | V1.62 appraises external evidence with M2.7; V1.63 proposes source-backed internal seeds; V1.64 restates that only M3 Scarlet owns semantic adoption | production observation of variation, non-repetition, no-work outcomes, cadence cost, and M3 choices |
| External operativity | L1 core + L2 device lab | supporting traces/events plus isolated haptic and notification probes | no external-world action suite; lab receipts are not Scarlet actions | evaluate peripheral receipts before permission architecture |
| Advanced operations | L1 | no specialist suite | future | define only after operativity governance |
| Governance/privacy/safety | L2 | DB roles, profile hints, audit, field ownership | single-user convention only | authenticated ownership and data rights |
| Computational affect | L3 | structural runtime appraisal, persistence, read-only shell, optional block | shadow default; natural-language keyword appraisal retired in V1.64 | design and test a source-backed semantic appraiser before model-facing activation |
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

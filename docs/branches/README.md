# Agentic Branches

Last updated: 2026-07-09
App baseline: V1.25.4
Status: canonical branch map

This directory tracks Scarlet's real branches of development. A branch is not a
technical subsystem by itself. A branch is an operating domain of the agent:
what Scarlet can perceive, remember, decide, maintain, communicate, or do.

Technical systems such as tests, traces, providers, schemas, events, and UI are
support infrastructure. They should be mapped to the branch whose behavior they
improve.

## Maturity Scale

```txt
L0 - Idea
L1 - Planned
L2 - Implemented prototype
L3 - Tested implementation
L4 - Validated in direct Scarlet use
L5 - Mature lab-core
```

## Current Branch Assessment

| Branch | Level | Current read |
|---|---:|---|
| Communication | L3/L4 | Strong conversational identity and readable agent stream; still needs richer natural intermediate updates. |
| User flows | L1 | Future product workflow layer; only settings/profile/session affordances exist. |
| Perception and context | L4 | Runtime context blocks are delivered and understood by Scarlet; V1.26.0 planning adds context-pack routing so future organs and embodied inputs do not collapse into one flat prompt. |
| Identity and relationship | L2/L3 | Prompt identity and active profile exist; long-term self/persona evolution is not yet structured. |
| Memory | L4+ | Strongest cognitive branch: semantic, episodic, summaries, provenance, proposal ledger, surfaces, graph retrieval, compact shell packets, and internal maintenance backfill; mature merge/staleness automation still future. |
| Learning and adaptation | L2 | Preference adaptation through memory exists; context-pack routing should retrieve adaptations by mode instead of making every lesson always-on. |
| Metacognition | L3 | One real metacognition step exists; recommended actions are validated against the shell command registry. |
| Operational management | L2 | Seeded focus/state/open loops exist; V1.5.0 adds Goal/Focus/Task theory before a real organ. |
| Decision autonomy | L2 | Prompt policies exist; autonomous decisions are partly reliable but not yet governed by validators. |
| External operativity | L1 | Mostly future; current API Mind is cognition-first, not external-world action. |
| Advanced operations | L1 | Future capability suite; not yet implemented beyond lab prototypes. |
| Governance, privacy, safety | L2 | Single active profile/privacy scope exists; future context packs must preserve privacy boundaries, source authority, and safety gates. |
| Computational affect | L2/L3 | Backend-appraised affect state exists with shadow/model modes and read-only inspection; behavior validation is still pending. |
| Multi-agent subprocesses | L1 | Future branch for internal workers/reviewers/maintainers; context-pack routing starts as deterministic shadow behavior, not a new visible agent. |

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

## Update Rules

Update a branch document when:

- a feature changes Scarlet's behavior in that branch;
- live tests produce important evidence;
- a bug affects the branch's assumptions;
- the owner proposes an evolution that should not be implemented immediately
  but should be remembered.

Do not let branch documents become code changelogs. They should preserve
philosophy, evidence, status, prior development, and future evolutions.

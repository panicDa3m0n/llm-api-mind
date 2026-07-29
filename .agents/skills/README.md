# Scarlet Project Skills

These repository-local skills encode the recurring workflows that require
project-specific judgment. They complement `AGENTS.md`; they do not replace it
or the canonical documents under `docs/`.

## Skill Map

| Skill | Use it for |
|---|---|
| `scarlet-project-stewardship` | Substantial planning, architecture, state review, or work that could blur Scarlet's research direction and system boundaries. |
| `scarlet-cognitive-change` | Changes to a cognitive organ, model context, provider lifecycle, prompt policy, history, or the model-facing shell. |
| `scarlet-runtime-debugging` | Real turn failures, stalls, wrong answers, missing events, retrieval problems, persistence issues, or UI/runtime disagreement. |
| `scarlet-e2e-evaluation` | Behavioral scenarios, frozen regression suites, natural live probes, and qualitative pre/post evaluation. |
| `scarlet-vps-android-release` | VPS rollout, Product UI profile/artifact parity, Android build/install, production preflight, canary, and rollback. |

The stewardship skill may be used with one operational skill. Runtime
debugging should normally precede a cognitive fix when the failure layer is
not yet established. A complete live behavioral suite is never implied by an
ordinary code task; it requires an explicit owner request.

## Authority

When sources disagree, use this order:

1. current code, executable schemas, tests, and direct runtime evidence;
2. `AGENTS.md` and the canonical document that owns the affected contract;
3. current branch and project-state documentation;
4. these operational skills;
5. conversational recollection.

A skill is an executable working guide, not a new architectural source of
truth. Architectural decisions belong in `docs/decisions.md`; observed defects
belong in `docs/bug-ledger.md`; experiments and results belong in
`docs/experiments.md` and the relevant evaluation document.

## Evolution Rule

Keep these skills current. When a real task exposes a reliable improvement, a
missing check, an invalid assumption, a recurring error, or a safer workflow:

1. verify the lesson against code, traces, tests, deployment evidence, or the
   owner-approved decision;
2. update the affected skill during the same task when that change is in
   scope, otherwise record the exact pending correction;
3. update canonical documentation first when the lesson changes architecture
   or policy;
4. preserve historical evidence instead of rewriting old results; and
5. run `backend/.venv/bin/python scripts/check_project_skills.py`.

Do not add a new skill for a one-off command or a narrow implementation detail.
Create one only when a distinct workflow recurs, carries material risk, and
cannot be expressed clearly by improving an existing skill.

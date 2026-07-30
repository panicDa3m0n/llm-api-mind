# Scarlet Project Skills

Repository skills are short operational guides for recurring, high-risk work.
They complement `AGENTS.md`; they never replace current code or the owning
contract.

| Skill | Trigger |
|---|---|
| `scarlet-project-stewardship` | Architecture, state review, boundaries, roadmap, or work that may blur Core, UI, adapters, modules, and embodiment. |
| `scarlet-cognitive-change` | A verified change to model context, memory, retrieval, prompt, provider lifecycle, shell, organs, modes, or autonomous cognition. |
| `scarlet-runtime-debugging` | A runtime symptom whose failing layer is not established: provider, turn, context, storage, streaming, UI, Android, VPS, or GPT adapter. |
| `scarlet-e2e-evaluation` | Owner-authorized natural scenarios, frozen regressions, or qualitative live Scarlet evidence. |
| `scarlet-vps-android-release` | VPS, Product UI, Android artifact, database preflight, canary, rollback, or release parity. |

Use stewardship alongside one operational skill when the change has both an
architectural and an execution risk. Diagnose before changing when the failing
layer is uncertain. A routine task never implies a full live evaluation.

## Authority And Maintenance

Use this order when sources disagree:

```txt
current code and direct evidence
> AGENTS.md and owning current contract
> project/branch current state
> decision or historical record
> skill
> conversation
```

Update a skill only when verified evidence or an owner correction improves a
recurring workflow. Update the owning contract first when semantics change,
remove obsolete advice rather than accumulating folklore, and run:

```bash
backend/.venv/bin/python scripts/check_project_skills.py
```

Do not create a new skill for a one-off command. Extend an existing skill
unless a distinct, recurring workflow has material risk and cannot be stated
clearly there.

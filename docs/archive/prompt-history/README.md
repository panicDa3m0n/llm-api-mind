# Prompt History Archive

This directory preserves historically approved Scarlet system-prompt snapshots
that are still referenced by checkpoints, ADRs, experiments, or the activity
ledger. They are documentation artifacts only: the runtime resolver reads the
current prompt under `backend/app/prompts/` and never loads this archive.

The filename timestamp and release marker are provenance. Do not treat an
archived prompt as a fallback, template, or active policy. To inspect a past
decision, follow the linked checkpoint or ADR first, then open only the exact
snapshot it cites.

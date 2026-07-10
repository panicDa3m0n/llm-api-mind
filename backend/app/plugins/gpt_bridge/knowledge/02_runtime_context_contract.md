# Runtime Context Contract

Bootstrap returns Scarlet's active context for the current turn in a compact
GPT Actions profile. Treat it as operational evidence, not decoration.

Full raw diagnostics are stored in backend traces. They are intentionally not
returned in the Actions response because ChatGPT Actions has practical response
size limits.

## Important Context Fields

- `context.profile`: response profile, currently `gpt-bootstrap-compact-v1`.
- `context.runtime_context`: model-facing `<runtime_context>` string.
- `context.runtime_payload_summary`: compact structured runtime summary.
- `context.memory_context`: compact automatic memory retrieval packet.
- `context.metacognitive_context`: optional compact metacognitive context.
- `context.provider_messages_recent`: compact recent provider-style history.
- `context.tools`: current `mind_shell` tool name/description.
- `context.full_diagnostics`: trace ids and omitted debug sections.

The compact response intentionally omits:

- full effective system prompt;
- base system prompt;
- raw memory query plan;
- raw runtime payload;
- full provider messages;
- retrieval shadow/graph/hybrid debug dumps.

Use the compact packet for turn cognition. Use `/gpt/action` commands such as
`memory search`, `memory graph`, `session list`, or `session open` when more
specific evidence is needed.

## Runtime Blocks

Prefer `runtime_context.blocks` when available.

Block types:

- `session_context`: current session continuity, previous sessions, previous
  session memories. Summaries are navigation aids; open source sessions before
  exact claims.
- `message_context`: current user message, world/time data, user profile,
  automatic memory results, recent dialogue, recent events, API Mind capability
  metadata.
- `focus_context`: Scarlet's current foreground attention. It is not semantic
  memory and must not narrow retrieval by itself.
- `affective_context`: backend-appraised emotional state. It shapes tone,
  caution, warmth, curiosity, and posture, but not factual truth.
- `scarlet_state`: compact backend working state.

## Evidence Discipline

Use the source designed for the claim:

1. current runtime facts and API Mind results;
2. command help for current capability shapes;
3. `temporal_context` for current time/date;
4. same-session provider continuity for active-session wording/process;
5. exact session transcripts for older conversations;
6. semantic memories and facts for durable remembered knowledge;
7. Scarlet's inference.

Selected memories are usable evidence. Near-miss memories are weak leads.
Conflicts should be named or inspected when relevant.

Do not say "all", "none", "verified", "measured", "decided", or "baseline"
unless the evidence actually supports that strength.

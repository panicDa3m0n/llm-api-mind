# Runtime Context Contract

Bootstrap returns Scarlet's active context for the current turn in a compact
GPT Actions profile. Treat it as operational evidence, not decoration.

Full raw diagnostics are stored in backend traces. They are intentionally not
returned in the Actions response because ChatGPT Actions has practical response
size limits.

## Important Context Fields

- `context.profile`: response profile, currently `gpt-bootstrap-compact-v1`.
- `context.runtime_context`: the single model-facing `<runtime_context>` string
  containing the canonical `scarlet-model-context-v2` JSON. The bridge does
  not return a duplicate structured `context.model_context` copy.
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

## Canonical Areas

Read the V2 document directly:

- `session`: current session, user name, one local clock/timezone/location, and
  up to two previous-session navigation hints;
- `memories.relevant`: automatic memories relevant to this turn;
- `memories.recent_user`: recent user-scope cognitive memories;
- `memories.recent_general`: recent remaining cognitive memories;
- `preserved_context`: focus, affect, metacognition, Scarlet state, recent
  events, and capability context still using their existing contracts.

Memory hints are compact navigation hooks. Use `memory open`, `memory facts`,
`memory graph`, `session message`, `session turn`, or `session open` when the
omitted detail matters.

## Evidence Discipline

Use the source designed for the claim:

1. current runtime facts and API Mind results;
2. command help for current capability shapes;
3. `runtime_context.session.now` for current time/date;
4. same-session provider continuity for active-session wording/process;
5. exact session transcripts for older conversations;
6. semantic memories and facts for durable remembered knowledge;
7. Scarlet's inference.

Automatic memories are usable hints, not complete records. Empty automatic
lists do not prove persistent-memory absence. Inspect conflicts explicitly
when relevant.

Do not say "all", "none", "verified", "measured", "decided", or "baseline"
unless the evidence actually supports that strength.

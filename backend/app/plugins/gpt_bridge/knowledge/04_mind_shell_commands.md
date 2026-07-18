# Mind Shell Commands

In the GPT bridge, `POST /gpt/action` is the transport for `mind_shell`.

The action body contains:

```json
{
  "session_id": "ses_...",
  "turn_id": "turn_...",
  "command": "help memory",
  "intent": "Understand memory command syntax."
}
```

The `command` string is the real cognitive operation. `intent` is only a short
reason.

## Command Families

Current families include:

- `help`;
- `memory`;
- `session`;
- `focus`;
- `volition`;
- `affect`;
- `mode`;
- `metacognition`.

Always trust returned shell help over remembered syntax.

## Common Commands

```txt
help
help memory
help session
memory search "query" --top 5
memory write --type user_preference --scope user --content "..." --reason "..."
memory graph mem_... --depth 2
session list --query "..." --limit 5
session open ses_... --limit 200
focus read
volition list active --limit 10
affect read
affect prototypes
mode read
mode set scouting --reason "..."
metacognition step --objective "..." --mode critic
```

Agent mode is Scarlet's foreground posture. Human-facing turns remain
`interactive`; `mode set idle|scouting --reason "..."` selects the posture to
resume afterward. A request for a post-conversation posture is a mode change,
not a volition. Apply an explicit request in the same turn; a memory does not
replace `mode set`. Use `idle` when there is no direction to resume; use
`scouting` for an exploratory, observational, or investigative orientation even
before sensors exist. The command persists posture and changes automatic context
eligibility only; it starts no autonomous cycle. Scouting has no autonomous
sensor runtime yet. Maintenance and Dream are not agent modes.

## Error Recovery

If a command fails:

1. read `error`, `cognitive_hint`, `suggested_next_actions`, and `usage_guide`;
2. retry once only with a materially corrected command;
3. if it still fails, do not claim state changed;
4. answer naturally and mention the issue only when it affects the user or the
   user is evaluating the system.

Do not loop with equivalent invalid commands.

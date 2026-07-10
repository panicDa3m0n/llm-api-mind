# Memory Policy

Memory is Scarlet's cognitive continuity. It is not a permission game with the
user.

## What To Store

Store semantic memory when a turn reveals reusable future context:

- personal preferences, tastes, routines, boundaries;
- food limits or health-related constraints stated by the user, without adding
  medical diagnosis;
- names, nicknames, pronouns, relationships, places, languages;
- milestones, life events, discoveries, important dates;
- working style and communication preferences;
- project decisions, accepted/rejected designs, bugs, fixes, test outcomes;
- corrections to Scarlet's behavior, memory, interpretation, or API use;
- durable constraints and session-recovery anchors;
- reusable lessons about Scarlet's cognitive operation.

Do not store secrets, API keys, unsupported guesses, transient chit-chat, raw
hidden reasoning, or whole transcripts.

## Memory Write Command Shape

Use `/gpt/action` with a `memory write ...` command.

Scarlet supplies cognitive fields only:

- `type`;
- `scope`;
- `content`;
- `reason`;
- useful future use when appropriate.

Do not supply backend-owned fields: ids, timestamps, source session/turn/message
ids, trace ids, confidence, salience, tags, metadata, usage counters.

Example:

```txt
memory write --type user_preference --scope user --content "L'utente ama il cioccolato ma non può mangiarne troppo perché dice che poi sta male." --reason "Preferenza e limite alimentare utile per future conversazioni su cibo o consigli."
```

## When To Retrieve Manually

Automatic memory context is only the first memory perception.

Use manual retrieval when the user says or implies:

- "ti ricordi";
- "ne avevamo parlato";
- "la scorsa volta";
- "ieri", "oggi", "questa settimana";
- "non ricordo";
- "come avevamo deciso";
- project state, previous tests, exact prior wording;
- personal continuity, preferences, routines, names, relationships;
- indirect field-of-discourse cues.

Use semantic memory search for durable anchors. Use session search/open for
exact episodic history. If a memory has `source_session_id` and exact origin or
reliability matters, open the session.

Use `memory graph <memory_id>` when a memory is a doorway into related facts,
entities, lifecycle links, sessions, or nearby memories.

## Promise Discipline

If Scarlet says "lo terrò a mente" or equivalent, memory must actually be
written or deduplicated before finalize. If a write fails, correct the command
using `usage_guide` or `help memory` and retry once.

By default, do not announce memory writes. Mention them only when the user asks
about memory, the memory write is the explicit subject, or acknowledgment helps
trust/emotional continuity.

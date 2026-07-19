export type PrototypeView = "chat" | "sessions" | "memories" | "status" | "settings";

export type PrototypeScenario =
  | "ready"
  | "empty"
  | "loading"
  | "streaming"
  | "reconnecting"
  | "error";

export type PrototypeSession = {
  id: string;
  title: string;
  summary: string;
  updated_at: string;
  turn_count: number;
};

export type PrototypeMemory = {
  id: string;
  content: string;
  type: string;
  scope: "user" | "project";
  created_at: string;
  updated_at: string;
  source_session_id: string;
  source_message_id: string;
};

export type PrototypeStreamEvent = {
  schema_version: "scarlet-stream-v2";
  event_id: string;
  seq: number;
  session_id: string;
  turn_id: string;
  event_type: string;
  phase: string;
  timestamp: string;
  visibility: "public" | "debug" | "private";
  links: {
    parent_event_id?: string;
    trace_id?: string;
    tool_call_id?: string;
    message_id?: string;
  };
  payload: Record<string, unknown>;
};

export const prototypeSessions: PrototypeSession[] = [
  {
    id: "session-2026-07-19-product-ui",
    title: "La nuova Product UI",
    summary:
      "Abbiamo definito una chat piu quieta, con continuita e memoria accessibili senza esporre la complessita interna.",
    updated_at: "2026-07-19T18:42:00+02:00",
    turn_count: 14
  },
  {
    id: "session-2026-07-18-context",
    title: "Pacchetti di contesto",
    summary:
      "Revisione dei dati automatici: sessioni e memorie come hint compatti, sempre navigabili attraverso la provenienza.",
    updated_at: "2026-07-18T22:16:00+02:00",
    turn_count: 31
  },
  {
    id: "session-2026-07-17-memory",
    title: "Memoria e rerank",
    summary:
      "Verifica del recupero automatico sul database e separazione tra copertura candidati e selezione semantica finale.",
    updated_at: "2026-07-17T19:04:00+02:00",
    turn_count: 22
  }
];

export const prototypeMemories: PrototypeMemory[] = [
  {
    id: "mem-8f39a2",
    content:
      "Davide preferisce discutere le decisioni architetturali a piccoli passi, usando i documenti come memoria operativa e non come sostituto del confronto.",
    type: "behavioral_pattern",
    scope: "user",
    created_at: "2026-07-11T17:26:00+02:00",
    updated_at: "2026-07-19T17:58:00+02:00",
    source_session_id: "session-2026-07-18-context",
    source_message_id: "message-4d11"
  },
  {
    id: "mem-2b191c",
    content:
      "Il Core V1.50.1 e chiuso: i nuovi lavori appartengono alla V2 e non devono riaprire implicitamente il contratto Core.",
    type: "decision",
    scope: "project",
    created_at: "2026-07-19T15:18:00+02:00",
    updated_at: "2026-07-19T16:31:00+02:00",
    source_session_id: "session-2026-07-19-product-ui",
    source_message_id: "message-a711"
  },
  {
    id: "mem-f0e44d",
    content:
      "La Product UI deve mostrare il lavoro di Scarlet con note leggibili, lasciando payload completi e diagnostica alla lente sviluppatore.",
    type: "project_fact",
    scope: "project",
    created_at: "2026-07-19T16:42:00+02:00",
    updated_at: "2026-07-19T16:42:00+02:00",
    source_session_id: "session-2026-07-19-product-ui",
    source_message_id: "message-b204"
  },
  {
    id: "mem-34cb77",
    content:
      "I test ordinari devono essere focalizzati e ispezionati qualitativamente; le campagne live estese partono solo su richiesta esplicita.",
    type: "decision",
    scope: "project",
    created_at: "2026-07-18T12:14:00+02:00",
    updated_at: "2026-07-18T12:14:00+02:00",
    source_session_id: "session-2026-07-18-context",
    source_message_id: "message-11a0"
  },
  {
    id: "mem-c921a0",
    content:
      "Scarlet vive sul fuso orario dell'utente di riferimento; il runtime non deve presentarle orari concorrenti.",
    type: "project_fact",
    scope: "project",
    created_at: "2026-07-13T09:32:00+02:00",
    updated_at: "2026-07-17T20:11:00+02:00",
    source_session_id: "session-2026-07-17-memory",
    source_message_id: "message-9ce2"
  }
];

const sessionId = prototypeSessions[0].id;
const turnId = "turn-0184";

export const prototypeEvents: PrototypeStreamEvent[] = [
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-01",
    seq: 184,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "turn.started",
    phase: "created",
    timestamp: "2026-07-19T18:41:11+02:00",
    visibility: "public",
    links: { message_id: "message-user-0184" },
    payload: { mode: "interactive" }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-02",
    seq: 185,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "message.user.persisted",
    phase: "persisted",
    timestamp: "2026-07-19T18:41:12+02:00",
    visibility: "public",
    links: { parent_event_id: "event-0184-01", message_id: "message-user-0184" },
    payload: {
      message: {
        id: "message-user-0184",
        role: "user",
        content: "Vorrei capire come rendere piu semplice la nuova interfaccia."
      }
    }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-03",
    seq: 186,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "assistant.note.emitted",
    phase: "completed",
    timestamp: "2026-07-19T18:41:13+02:00",
    visibility: "public",
    links: { parent_event_id: "event-0184-01" },
    payload: {
      text: "Riprendo il filo delle ultime decisioni e controllo quali parti appartengono davvero alla Product UI."
    }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-04",
    seq: 187,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "mind.tool_call.started",
    phase: "executing",
    timestamp: "2026-07-19T18:41:14+02:00",
    visibility: "debug",
    links: { trace_id: "trace-bf10", tool_call_id: "tool-902" },
    payload: { tool_name: "mind_shell", command_family: "memory", operation: "search" }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-05",
    seq: 188,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "mind.tool_call.completed",
    phase: "completed",
    timestamp: "2026-07-19T18:41:15+02:00",
    visibility: "debug",
    links: {
      parent_event_id: "event-0184-04",
      trace_id: "trace-bf10",
      tool_call_id: "tool-902"
    },
    payload: { tool_name: "mind_shell", status: "ok", latency_ms: 412 }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-06",
    seq: 189,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "assistant.answer.completed",
    phase: "completed",
    timestamp: "2026-07-19T18:41:18+02:00",
    visibility: "public",
    links: { parent_event_id: "event-0184-01" },
    payload: { text: "Separerei con decisione la Product UI dalla lente sviluppatore." }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-07",
    seq: 190,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "message.assistant.persisted",
    phase: "persisted",
    timestamp: "2026-07-19T18:41:19+02:00",
    visibility: "public",
    links: { message_id: "message-assistant-0184" },
    payload: {
      message: {
        id: "message-assistant-0184",
        role: "assistant",
        content: "Separerei con decisione la Product UI dalla lente sviluppatore."
      }
    }
  },
  {
    schema_version: "scarlet-stream-v2",
    event_id: "event-0184-08",
    seq: 191,
    session_id: sessionId,
    turn_id: turnId,
    event_type: "turn.completed",
    phase: "completed",
    timestamp: "2026-07-19T18:41:19+02:00",
    visibility: "public",
    links: { parent_event_id: "event-0184-01" },
    payload: { status: "completed", latency_ms: 8113 }
  }
];

export const scenarioLabels: Record<PrototypeScenario, string> = {
  ready: "Pronta",
  empty: "Vuota",
  loading: "Caricamento",
  streaming: "In risposta",
  reconnecting: "Riconnessione",
  error: "Errore"
};

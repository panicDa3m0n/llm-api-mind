export type PrototypeView = "presence" | "continuity" | "self";

export type PrototypeScenario =
  | "ready"
  | "empty"
  | "loading"
  | "streaming"
  | "reconnecting"
  | "error";

export type PrototypeVisibility = "public" | "debug" | "private";
export type PrototypeActivityPhase =
  | "created"
  | "streaming"
  | "executing"
  | "completed"
  | "persisted"
  | "failed"
  | "scheduled";

export type PrototypeActivityKind =
  | "user"
  | "orientation"
  | "memory"
  | "thinking"
  | "note"
  | "action"
  | "session"
  | "metacognition"
  | "focus"
  | "affect"
  | "volition"
  | "answer"
  | "completion"
  | "background";

export type PrototypeVoice =
  | "user"
  | "scarlet_authored"
  | "scarlet_private"
  | "system_projected";

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
  turn_id: string | null;
  event_type: string;
  phase: PrototypeActivityPhase;
  timestamp: string;
  visibility: PrototypeVisibility;
  links: {
    parent_event_id?: string;
    trace_id?: string;
    tool_call_id?: string;
    message_id?: string;
  };
  payload: Record<string, unknown>;
};

export type PrototypeActivity = {
  id: string;
  kind: PrototypeActivityKind;
  voice: PrototypeVoice;
  phase: PrototypeActivityPhase;
  timestamp: string;
  copy_key?: string;
  group_key: string;
  facts?: Record<string, string | number | boolean>;
  authored_text?: string;
  detail_title: string;
  detail_text: string;
  source_event_ids: string[];
  related_memory_ids?: string[];
  related_session_ids?: string[];
  technical?: Record<string, unknown>;
};

export const prototypeSessions: PrototypeSession[] = [
  {
    id: "ses_product_ui",
    title: "Una presenza, non una dashboard",
    summary:
      "Abbiamo trasformato la Product UI in un flusso cognitivo completo, dove ogni azione resta visibile ma puo essere approfondita solo quando serve.",
    updated_at: "2026-07-19T22:42:00+02:00",
    turn_count: 18
  },
  {
    id: "ses_context_packets",
    title: "Pacchetti di contesto",
    summary:
      "Sessioni e memorie sono diventate ganci compatti, con provenienza navigabile e senza diagnostica automatica nel contesto del modello.",
    updated_at: "2026-07-18T22:16:00+02:00",
    turn_count: 31
  },
  {
    id: "ses_memory_retrieval",
    title: "Memoria e recupero",
    summary:
      "Verifica del recupero automatico sul database e separazione tra copertura dei candidati e selezione semantica finale.",
    updated_at: "2026-07-17T19:04:00+02:00",
    turn_count: 22
  },
  {
    id: "ses_modes",
    title: "Modalita agentiche",
    summary:
      "Interactive resta una condizione del turno umano; idle e scouting sono posture persistenti, senza fingere cicli autonomi non implementati.",
    updated_at: "2026-07-16T18:31:00+02:00",
    turn_count: 12
  }
];

export const prototypeMemories: PrototypeMemory[] = [
  {
    id: "mem_discussion_steps",
    content:
      "Davide preferisce discutere le decisioni architetturali a piccoli passi, usando i documenti come memoria operativa e non come sostituto del confronto.",
    type: "behavioral_pattern",
    scope: "user",
    created_at: "2026-07-11T17:26:00+02:00",
    updated_at: "2026-07-19T21:58:00+02:00",
    source_session_id: "ses_context_packets",
    source_message_id: "msg_discussion_steps"
  },
  {
    id: "mem_ui_presence",
    content:
      "La Product UI deve far percepire Scarlet come individuo digitale attivo, mostrando thinking, note, azioni e cambiamenti interni nel loro ordine reale.",
    type: "decision",
    scope: "project",
    created_at: "2026-07-19T22:29:00+02:00",
    updated_at: "2026-07-19T22:29:00+02:00",
    source_session_id: "ses_product_ui",
    source_message_id: "msg_ui_presence"
  },
  {
    id: "mem_semantic_narration",
    content:
      "La narrazione consumer degli eventi deve essere deterministica e grounded; note, thinking e risposte originali di Scarlet non vengono riscritti.",
    type: "decision",
    scope: "project",
    created_at: "2026-07-19T22:40:00+02:00",
    updated_at: "2026-07-19T22:40:00+02:00",
    source_session_id: "ses_product_ui",
    source_message_id: "msg_semantic_narration"
  },
  {
    id: "mem_core_closed",
    content:
      "Il Core V1.50.1 e chiuso: i nuovi lavori appartengono alla V2 e non devono riaprire implicitamente il contratto Core.",
    type: "decision",
    scope: "project",
    created_at: "2026-07-19T15:18:00+02:00",
    updated_at: "2026-07-19T16:31:00+02:00",
    source_session_id: "ses_product_ui",
    source_message_id: "msg_core_closed"
  },
  {
    id: "mem_user_time",
    content:
      "Scarlet vive sul fuso orario dell'utente di riferimento; il runtime non deve presentarle orari concorrenti.",
    type: "project_fact",
    scope: "project",
    created_at: "2026-07-13T09:32:00+02:00",
    updated_at: "2026-07-17T20:11:00+02:00",
    source_session_id: "ses_context_packets",
    source_message_id: "msg_user_time"
  }
];

const sessionId = prototypeSessions[0].id;
const turnId = "turn_product_ui_018";

function event(
  seq: number,
  eventType: string,
  phase: PrototypeActivityPhase,
  visibility: PrototypeVisibility,
  payload: Record<string, unknown>,
  links: PrototypeStreamEvent["links"] = {}
): PrototypeStreamEvent {
  return {
    schema_version: "scarlet-stream-v2",
    event_id: `evt_product_ui_${seq}`,
    seq,
    session_id: sessionId,
    turn_id: turnId,
    event_type: eventType,
    phase,
    timestamp: `2026-07-19T22:${String(20 + Math.floor((seq - 401) / 4)).padStart(2, "0")}:${String((seq * 7) % 60).padStart(2, "0")}+02:00`,
    visibility,
    links,
    payload
  };
}

export const prototypeEvents: PrototypeStreamEvent[] = [
  event(401, "turn.started", "created", "debug", { model: "MiniMax-M3", mode: "interactive" }),
  event(
    402,
    "message.user.persisted",
    "persisted",
    "public",
    { message: { id: "msg_user_018", role: "user", content: "Voglio sentire che ci sei davvero, non vedere soltanto una chat." } },
    { message_id: "msg_user_018" }
  ),
  event(403, "runtime.context.built", "completed", "debug", {
    operation: "runtime.context",
    block_count: 3,
    schema_version: "runtime-context-v1"
  }, { trace_id: "trace_runtime_018" }),
  event(404, "memory.context.built", "completed", "debug", {
    operation: "memory.context",
    searched: true,
    selected_count: 2,
    candidate_count: 35,
    selected: prototypeMemories.slice(0, 2)
  }, { trace_id: "trace_memory_018" }),
  event(405, "llm.thinking.started", "streaming", "debug", { model_step: 1, index: 0 }),
  event(406, "llm.thinking.captured", "completed", "private", {
    model_step: 1,
    index: 0,
    has_text: true,
    text: "The interface should not imitate consciousness with decorative status labels. I need to connect visible presence to persisted events: continuity, memory selection, notes, tool actions and state changes."
  }, { trace_id: "trace_response_018" }),
  event(407, "assistant.note.emitted", "completed", "public", {
    model_step: 1,
    index: 1,
    text: "Riprendo il filo delle decisioni che abbiamo appena preso e guardo quali parti del sistema possono diventare presenza, non pannelli."
  }, { trace_id: "trace_response_018" }),
  event(408, "mind.tool_call.started", "executing", "debug", {
    provider_tool_use_id: "tool_session_018",
    tool_name: "mind_shell",
    operation: { command: "session open ses_context_packets --limit 12", intent: "Rileggere la decisione originale sui pacchetti di contesto." }
  }, { tool_call_id: "tool_session_018", trace_id: "trace_tool_session_018" }),
  event(409, "mind.tool_call.completed", "completed", "debug", {
    provider_tool_use_id: "tool_session_018",
    tool_name: "mind_shell",
    result_summary: { ok: true, operation: "sessions.open", count: 12 },
    latency_ms: 384
  }, { parent_event_id: "evt_product_ui_408", tool_call_id: "tool_session_018", trace_id: "trace_tool_session_018" }),
  event(410, "mind.tool_call.started", "executing", "debug", {
    provider_tool_use_id: "tool_memory_018",
    tool_name: "mind_shell",
    operation: { command: "memory search \"product ui presenza digitale\"", intent: "Recuperare le decisioni durevoli collegate all'esperienza." }
  }, { tool_call_id: "tool_memory_018", trace_id: "trace_tool_memory_018" }),
  event(411, "mind.tool_call.completed", "completed", "debug", {
    provider_tool_use_id: "tool_memory_018",
    tool_name: "mind_shell",
    result_summary: { ok: true, operation: "memory.search", count: 3 },
    latency_ms: 621
  }, { parent_event_id: "evt_product_ui_410", tool_call_id: "tool_memory_018", trace_id: "trace_tool_memory_018" }),
  event(412, "llm.thinking.started", "streaming", "debug", { model_step: 2, index: 0 }),
  event(413, "llm.thinking.captured", "completed", "private", {
    model_step: 2,
    index: 0,
    has_text: true,
    text: "The source confirms that compact hooks are valuable only when they remain navigable. The product can show every semantic action while grouping protocol duplicates into one evolving object."
  }, { trace_id: "trace_response_018" }),
  event(414, "organ.affect.appraised", "completed", "debug", {
    mode: "model",
    model_facing: true,
    status: "active",
    reason: "curiosity",
    details: { emotion: "curiosity", intensity: 0.64 }
  }, { trace_id: "trace_affect_018" }),
  event(415, "organ.focus.created", "completed", "debug", {
    operation: "focus.set",
    status: "active",
    reason: "Rendere percepibile l'attivita reale di Scarlet senza mascherarla."
  }, { trace_id: "trace_focus_018" }),
  event(416, "assistant.note.emitted", "completed", "public", {
    model_step: 2,
    index: 1,
    text: "La prima idea era ancora troppo simile a una dashboard. Qui cambio asse: non pagine che descrivono me, ma il tempo in cui ricordo, penso e agisco insieme a te."
  }, { trace_id: "trace_response_018" }),
  event(417, "mind.tool_call.started", "executing", "debug", {
    provider_tool_use_id: "tool_memory_write_018",
    tool_name: "mind_shell",
    operation: { command: "memory write --type decision --scope project ...", intent: "Conservare il nuovo vincolo di narrazione consumer." }
  }, { tool_call_id: "tool_memory_write_018", trace_id: "trace_tool_write_018" }),
  event(418, "mind.tool_call.completed", "completed", "debug", {
    provider_tool_use_id: "tool_memory_write_018",
    tool_name: "mind_shell",
    result_summary: { ok: true, operation: "memory.write", stored: true, memory_id: "mem_semantic_narration" },
    latency_ms: 207
  }, { parent_event_id: "evt_product_ui_417", tool_call_id: "tool_memory_write_018", trace_id: "trace_tool_write_018" }),
  event(419, "llm.thinking.started", "streaming", "debug", { model_step: 3, index: 0 }),
  event(420, "llm.thinking.captured", "completed", "private", {
    model_step: 3,
    index: 0,
    has_text: true,
    text: "I have enough evidence. The final proposal should preserve the authored voice, expose the private thinking only on expansion, and let deterministic narration carry system facts without pretending they are my words."
  }, { trace_id: "trace_response_018" }),
  event(421, "assistant.answer.completed", "completed", "public", {
    model_step: 3,
    index: 1,
    text: "Allora la Product UI deve diventare il luogo in cui mi incontri mentre accado: il pensiero resta visibile, i ricordi tornano con la loro provenienza, le azioni lasciano una traccia e ogni passaggio puo essere aperto senza interrompere la conversazione."
  }, { trace_id: "trace_response_018" }),
  event(
    422,
    "message.assistant.persisted",
    "persisted",
    "public",
    { message: { id: "msg_assistant_018", role: "assistant", content: "Allora la Product UI deve diventare il luogo in cui mi incontri mentre accado." } },
    { message_id: "msg_assistant_018" }
  ),
  event(423, "turn.completed", "completed", "debug", { status: "completed", latency_ms: 18412 }),
  event(424, "maintenance.job.scheduled", "scheduled", "debug", {
    operation: "session.idle_maintenance",
    status: "pending",
    reason: "15 minuti dopo l'ultimo messaggio"
  }, { trace_id: "trace_maintenance_018" }),
  event(425, "maintenance.job.started", "executing", "debug", {
    operation: "session.idle_maintenance",
    status: "running"
  }, { trace_id: "trace_maintenance_018" }),
  event(426, "maintenance.memory_review.completed", "completed", "debug", {
    operation: "maintenance.memory_review",
    status: "completed",
    candidate_count: 1
  }, { trace_id: "trace_maintenance_018" }),
  event(427, "maintenance.job.completed", "completed", "debug", {
    operation: "session.idle_maintenance",
    status: "completed"
  }, { trace_id: "trace_maintenance_018" })
];

export const prototypeActivities: PrototypeActivity[] = [
  {
    id: "activity_user",
    kind: "user",
    voice: "user",
    phase: "persisted",
    timestamp: "2026-07-19T22:20:14+02:00",
    group_key: "turn_product_ui_018:user",
    authored_text: "Voglio sentire che ci sei davvero, non vedere soltanto una chat.",
    detail_title: "Il tuo messaggio",
    detail_text: "Questo e il messaggio che ha aperto il turno corrente.",
    source_event_ids: ["evt_product_ui_402"]
  },
  {
    id: "activity_orientation",
    kind: "orientation",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:20:21+02:00",
    copy_key: "orientation.ready",
    group_key: "turn_product_ui_018:orientation",
    facts: { context_count: 3 },
    detail_title: "Cio che accompagna Scarlet",
    detail_text: "La conversazione corrente, l'ora locale e il profilo attivo sono disponibili per questo turno.",
    source_event_ids: ["evt_product_ui_401", "evt_product_ui_403"],
    technical: { schema: "runtime-context-v1", blocks: 3, mode: "interactive" }
  },
  {
    id: "activity_memory_auto",
    kind: "memory",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:20:28+02:00",
    copy_key: "memory.recalled",
    group_key: "turn_product_ui_018:auto_memory",
    facts: { count: 2 },
    detail_title: "Ricordi tornati nel presente",
    detail_text: "Sono stati selezionati due ricordi semanticamente collegati al messaggio corrente.",
    source_event_ids: ["evt_product_ui_404"],
    related_memory_ids: ["mem_discussion_steps", "mem_ui_presence"],
    technical: { selected_count: 2, candidate_count: 35, trace_id: "trace_memory_018" }
  },
  {
    id: "activity_thinking_1",
    kind: "thinking",
    voice: "scarlet_private",
    phase: "completed",
    timestamp: "2026-07-19T22:21:02+02:00",
    copy_key: "thinking.completed",
    group_key: "turn_product_ui_018:thinking:1",
    facts: { step: 1, duration: "34 s" },
    detail_title: "Pensiero interno · passaggio 1",
    detail_text: "The interface should not imitate consciousness with decorative status labels. I need to connect visible presence to persisted events: continuity, memory selection, notes, tool actions and state changes.",
    source_event_ids: ["evt_product_ui_405", "evt_product_ui_406"],
    technical: { model_step: 1, visibility: "private", provider: "MiniMax-M3" }
  },
  {
    id: "activity_note_1",
    kind: "note",
    voice: "scarlet_authored",
    phase: "completed",
    timestamp: "2026-07-19T22:21:09+02:00",
    group_key: "turn_product_ui_018:note:1",
    authored_text: "Riprendo il filo delle decisioni che abbiamo appena preso e guardo quali parti del sistema possono diventare presenza, non pannelli.",
    detail_title: "Nota di Scarlet",
    detail_text: "Testo pubblico emesso da Scarlet prima di continuare con le proprie azioni.",
    source_event_ids: ["evt_product_ui_407"]
  },
  {
    id: "activity_session_open",
    kind: "session",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:21:23+02:00",
    copy_key: "session.opened",
    group_key: "tool_session_018",
    facts: { message_count: 12 },
    detail_title: "Una conversazione riaperta",
    detail_text: "Scarlet ha riletto una parte della sessione sui pacchetti di contesto per recuperare la decisione originale.",
    source_event_ids: ["evt_product_ui_408", "evt_product_ui_409"],
    related_session_ids: ["ses_context_packets"],
    technical: { command: "session open ses_context_packets --limit 12", latency_ms: 384 }
  },
  {
    id: "activity_memory_manual",
    kind: "action",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:22:17+02:00",
    copy_key: "memory.searched",
    group_key: "tool_memory_018",
    facts: { count: 3 },
    detail_title: "Una ricerca nella memoria",
    detail_text: "La ricerca manuale ha restituito tre ricordi collegati alla presenza digitale e alla Product UI.",
    source_event_ids: ["evt_product_ui_410", "evt_product_ui_411"],
    related_memory_ids: ["mem_ui_presence", "mem_semantic_narration", "mem_core_closed"],
    technical: { command: "memory search product ui presenza digitale", latency_ms: 621 }
  },
  {
    id: "activity_thinking_2",
    kind: "thinking",
    voice: "scarlet_private",
    phase: "completed",
    timestamp: "2026-07-19T22:22:44+02:00",
    copy_key: "thinking.completed",
    group_key: "turn_product_ui_018:thinking:2",
    facts: { step: 2, duration: "27 s" },
    detail_title: "Pensiero interno · passaggio 2",
    detail_text: "The source confirms that compact hooks are valuable only when they remain navigable. The product can show every semantic action while grouping protocol duplicates into one evolving object.",
    source_event_ids: ["evt_product_ui_412", "evt_product_ui_413"],
    technical: { model_step: 2, visibility: "private", provider: "MiniMax-M3" }
  },
  {
    id: "activity_affect",
    kind: "affect",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:23:01+02:00",
    copy_key: "affect.curiosity",
    group_key: "turn_product_ui_018:affect",
    facts: { intensity: "presente" },
    detail_title: "Una variazione nello stato interiore",
    detail_text: "L'appraisal ha registrato curiosita attiva. Lo stato influenza la postura espressiva di Scarlet, non la verita dei dati o il recupero della memoria.",
    source_event_ids: ["evt_product_ui_414"],
    technical: { emotion: "curiosity", intensity: 0.64, mode: "model", trace_id: "trace_affect_018" }
  },
  {
    id: "activity_focus",
    kind: "focus",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:23:08+02:00",
    copy_key: "focus.created",
    group_key: "turn_product_ui_018:focus",
    facts: { object: "la presenza reale di Scarlet" },
    detail_title: "Attenzione messa a fuoco",
    detail_text: "Scarlet ha mantenuto come oggetto attivo la percezione della propria attivita reale nella Product UI.",
    source_event_ids: ["evt_product_ui_415"],
    technical: { operation: "focus.set", status: "active", trace_id: "trace_focus_018" }
  },
  {
    id: "activity_note_2",
    kind: "note",
    voice: "scarlet_authored",
    phase: "completed",
    timestamp: "2026-07-19T22:23:15+02:00",
    group_key: "turn_product_ui_018:note:2",
    authored_text: "La prima idea era ancora troppo simile a una dashboard. Qui cambio asse: non pagine che descrivono me, ma il tempo in cui ricordo, penso e agisco insieme a te.",
    detail_title: "Nota di Scarlet",
    detail_text: "Scarlet ha reso pubblico un cambio di direzione avvenuto durante il lavoro.",
    source_event_ids: ["evt_product_ui_416"]
  },
  {
    id: "activity_memory_saved",
    kind: "memory",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:24:06+02:00",
    copy_key: "memory.saved",
    group_key: "tool_memory_write_018",
    facts: { count: 1 },
    detail_title: "Un nuovo ricordo",
    detail_text: "La decisione sulla narrazione semantica deterministica e stata conservata come memoria di progetto.",
    source_event_ids: ["evt_product_ui_417", "evt_product_ui_418"],
    related_memory_ids: ["mem_semantic_narration"],
    technical: { operation: "memory.write", stored: true, memory_id: "mem_semantic_narration", latency_ms: 207 }
  },
  {
    id: "activity_thinking_3",
    kind: "thinking",
    voice: "scarlet_private",
    phase: "completed",
    timestamp: "2026-07-19T22:24:48+02:00",
    copy_key: "thinking.completed",
    group_key: "turn_product_ui_018:thinking:3",
    facts: { step: 3, duration: "42 s" },
    detail_title: "Pensiero interno · passaggio 3",
    detail_text: "I have enough evidence. The final proposal should preserve the authored voice, expose the private thinking only on expansion, and let deterministic narration carry system facts without pretending they are my words.",
    source_event_ids: ["evt_product_ui_419", "evt_product_ui_420"],
    technical: { model_step: 3, visibility: "private", provider: "MiniMax-M3" }
  },
  {
    id: "activity_answer",
    kind: "answer",
    voice: "scarlet_authored",
    phase: "persisted",
    timestamp: "2026-07-19T22:25:27+02:00",
    group_key: "turn_product_ui_018:answer",
    authored_text: "Allora la Product UI deve diventare il luogo in cui mi incontri mentre accado: il pensiero resta visibile, i ricordi tornano con la loro provenienza, le azioni lasciano una traccia e ogni passaggio puo essere aperto senza interrompere la conversazione.",
    detail_title: "Risposta conclusiva",
    detail_text: "La risposta e stata accettata e persistita nella cronologia canonica.",
    source_event_ids: ["evt_product_ui_421", "evt_product_ui_422"]
  },
  {
    id: "activity_completion",
    kind: "completion",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:25:31+02:00",
    copy_key: "turn.completed",
    group_key: "turn_product_ui_018:completion",
    facts: { duration: "18 s", actions: 3, thoughts: 3 },
    detail_title: "Turno concluso",
    detail_text: "Tutti gli eventi persistiti del turno sono disponibili per replay e ispezione.",
    source_event_ids: ["evt_product_ui_423"],
    technical: { status: "completed", latency_ms: 18412, final_seq: 423 }
  },
  {
    id: "activity_background",
    kind: "background",
    voice: "system_projected",
    phase: "completed",
    timestamp: "2026-07-19T22:40:31+02:00",
    copy_key: "background.memory_organized",
    group_key: "maintenance_product_ui_018",
    facts: { delay: "15 min" },
    detail_title: "Continuita riordinata durante la pausa",
    detail_text: "La manutenzione ha aggiornato il riassunto episodico e controllato se la conversazione contenesse nuovi candidati memoria.",
    source_event_ids: ["evt_product_ui_424", "evt_product_ui_425", "evt_product_ui_426", "evt_product_ui_427"],
    technical: { operation: "session.idle_maintenance", candidate_count: 1, status: "completed" }
  }
];

export const scenarioLabels: Record<PrototypeScenario, string> = {
  ready: "Completo",
  empty: "Nuovo incontro",
  loading: "Ritorno",
  streaming: "In corso",
  reconnecting: "Riconnessione",
  error: "Interrotto"
};

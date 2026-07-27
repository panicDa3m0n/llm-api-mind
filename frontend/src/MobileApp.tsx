import {
  Bell,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  ChevronRight,
  Clock3,
  Compass,
  Home,
  MapPin,
  MessageCircle,
  Moon,
  Network,
  Plane,
  Plus,
  Radio,
  RefreshCcw,
  Search,
  Send,
  Settings,
  Shield,
  Sparkles,
  UserRound,
  Utensils,
  WandSparkles,
  X,
  Zap
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  createSession,
  fetchAutonomyHistory,
  fetchDashboardMemories,
  fetchHealth,
  fetchMessages,
  fetchRuntimeSettings,
  fetchSessions,
  fetchUserProfile,
  streamTurn,
  updateRuntimeSettings
} from "./api";
import type {
  AutonomyHistory,
  AutonomousCycle,
  ChatMessage,
  ChatSession,
  DashboardMemory,
  DashboardMemories,
  RuntimeSettings,
  StreamEvent,
  UserProfile
} from "./types";

type MobileTab = "chat" | "memory" | "actions" | "profile";

type MobileBlockKind =
  | "user"
  | "context"
  | "memory"
  | "metacognition"
  | "thinking"
  | "note"
  | "tool"
  | "activity"
  | "answer"
  | "system";

type MobileBlock = {
  id: string;
  kind: MobileBlockKind;
  turnId?: string;
  title: string;
  text: string;
  status?: "live" | "done" | "error";
  createdAt?: string;
  data?: Record<string, unknown>;
};

type SettingsDraft = {
  timezone: string;
  language: string;
  country_code: string;
  profile_id: string;
  user_display_name: string;
  privacy_scope: string;
};

const DEFAULT_SETTINGS: SettingsDraft = {
  timezone: "Europe/Rome",
  language: "it",
  country_code: "IT",
  profile_id: "local-user",
  privacy_scope: "local_single_user",
  user_display_name: "Utente locale"
};

type MobileActivityPhase =
  | "request"
  | "context"
  | "memorySearch"
  | "memoryConnect"
  | "memoryEmpty"
  | "thinking"
  | "toolUse"
  | "toolResult"
  | "toolError"
  | "memoryWrite"
  | "memorySaved"
  | "sessionSearch"
  | "schema"
  | "metacognition";

type MobileActivityCopy = {
  title: string;
  text: string;
  status?: MobileBlock["status"];
};

const ACTIVITY_MESSAGES: Record<MobileActivityPhase, string[]> = {
  request: [
    "Scarlet sta ragionando sulla tua richiesta.",
    "Scarlet sta leggendo il contesto prima di rispondere.",
    "Scarlet sta mettendo in ordine richiesta e memoria.",
    "Scarlet sta cercando il filo giusto.",
    "Scarlet sta valutando cosa serve davvero.",
    "Scarlet sta orientando il pensiero.",
    "Scarlet sta separando cio che sa da cio che deve verificare.",
    "Scarlet sta costruendo il contesto utile.",
    "Scarlet sta ascoltando fino in fondo.",
    "Scarlet sta preparando una risposta adatta a te."
  ],
  context: [
    "Scarlet sta caricando profilo, sessione e tempo reale.",
    "Scarlet sta preparando il contesto operativo.",
    "Scarlet sta allineando i dati della conversazione."
  ],
  memorySearch: [
    "Scarlet sta cercando tra i suoi ricordi.",
    "Scarlet sta interrogando la memoria utile per questo messaggio.",
    "Scarlet sta cercando tracce collegate alla tua richiesta."
  ],
  memoryConnect: [
    "Scarlet sta collegando i ricordi emersi alla richiesta.",
    "Scarlet sta valutando quali ricordi usare davvero.",
    "Scarlet sta dando peso ai ricordi rilevanti."
  ],
  memoryEmpty: [
    "Scarlet non ha trovato ricordi forti e sta proseguendo con il contesto attuale.",
    "Scarlet sta continuando senza ancoraggi di memoria certi.",
    "Scarlet sta usando il contesto del turno per orientarsi."
  ],
  thinking: [
    "Scarlet sta riflettendo.",
    "Scarlet sta verificando il prossimo passo.",
    "Scarlet sta riorganizzando il ragionamento."
  ],
  toolUse: [
    "Scarlet sta usando una funzione interna.",
    "Scarlet sta aspettando una risposta da API Mind.",
    "Scarlet sta eseguendo un passaggio interno."
  ],
  toolResult: [
    "Scarlet sta usando il risultato per continuare.",
    "Scarlet sta integrando l'evidenza appena ricevuta.",
    "Scarlet sta aggiornando il ragionamento con il risultato."
  ],
  toolError: [
    "Scarlet sta correggendo il percorso dopo un errore interno.",
    "Scarlet ha ricevuto un errore e sta tentando di recuperare.",
    "Scarlet sta ricalibrando la chiamata interna."
  ],
  memoryWrite: [
    "Scarlet sta salvando un ricordo nella sua memoria.",
    "Scarlet sta consolidando una nuova memoria.",
    "Scarlet sta trasformando un fatto utile in ricordo persistente."
  ],
  memorySaved: [
    "Scarlet ha salvato il ricordo nella sua memoria.",
    "Il ricordo e stato consolidato.",
    "Scarlet ha aggiornato la sua memoria persistente."
  ],
  sessionSearch: [
    "Scarlet sta recuperando una conversazione precedente.",
    "Scarlet sta cercando nello storico delle sessioni.",
    "Scarlet sta ricostruendo il contesto episodico."
  ],
  schema: [
    "Scarlet sta controllando le sue capacita interne.",
    "Scarlet sta verificando come usare correttamente API Mind.",
    "Scarlet sta rileggendo lo schema operativo disponibile."
  ],
  metacognition: [
    "Scarlet sta rivedendo il proprio ragionamento.",
    "Scarlet sta usando il suo spazio metacognitivo.",
    "Scarlet sta confrontando pensiero, prove e prossima risposta."
  ]
};

function activityId(turnId: string): string {
  return `activity-${turnId}`;
}

function activityCopy(phase: MobileActivityPhase, title?: string): MobileActivityCopy {
  return {
    title: title ?? activityTitle(phase),
    text: randomActivityMessage(phase),
    status: phase === "memorySaved" ? "done" : "live"
  };
}

function activityTitle(phase: MobileActivityPhase): string {
  if (phase === "memorySearch") {
    return "Ricerca nei ricordi";
  }
  if (phase === "memoryConnect") {
    return "Ricordi in valutazione";
  }
  if (phase === "memoryEmpty") {
    return "Memoria controllata";
  }
  if (phase === "memoryWrite") {
    return "Memoria in aggiornamento";
  }
  if (phase === "memorySaved") {
    return "Ricordo salvato";
  }
  if (phase === "sessionSearch") {
    return "Storico in recupero";
  }
  if (phase === "schema") {
    return "Capacita in verifica";
  }
  if (phase === "metacognition") {
    return "Metacognizione attiva";
  }
  if (phase === "toolError") {
    return "Recupero operativo";
  }
  if (phase === "toolResult") {
    return "Risultato ricevuto";
  }
  if (phase === "toolUse") {
    return "Operazione interna";
  }
  if (phase === "context") {
    return "Contesto in preparazione";
  }
  return "Scarlet e al lavoro";
}

function randomActivityMessage(phase: MobileActivityPhase): string {
  const messages = ACTIVITY_MESSAGES[phase];
  return messages[Math.floor(Math.random() * messages.length)] || ACTIVITY_MESSAGES.request[0];
}

function activityForToolCall(path: string): MobileActivityCopy {
  if (path.includes("/mind/memory/write")) {
    return activityCopy("memoryWrite");
  }
  if (path.includes("/mind/memory")) {
    return activityCopy("memorySearch");
  }
  if (path.includes("/mind/sessions")) {
    return activityCopy("sessionSearch");
  }
  if (path.includes("/mind/schema")) {
    return activityCopy("schema");
  }
  if (path.includes("/mind/metacognition")) {
    return activityCopy("metacognition");
  }
  return activityCopy("toolUse");
}

function activityForToolResult(path: string, status: unknown): MobileActivityCopy {
  if (status === "error") {
    return activityCopy("toolError");
  }
  if (path.includes("/mind/memory/write")) {
    return activityCopy("memorySaved");
  }
  if (path.includes("/mind/memory")) {
    return activityCopy("memoryConnect");
  }
  if (path.includes("/mind/sessions")) {
    return activityCopy("memoryConnect", "Storico collegato");
  }
  if (path.includes("/mind/metacognition")) {
    return activityCopy("thinking");
  }
  return activityCopy("toolResult");
}

export function MobileApp() {
  const [activeTab, setActiveTab] = useState<MobileTab>("chat");
  const [session, setSession] = useState<ChatSession | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [flow, setFlow] = useState<MobileBlock[]>([]);
  const [prompt, setPrompt] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [health, setHealth] = useState("connessione in corso");
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<SettingsDraft>(DEFAULT_SETTINGS);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [memories, setMemories] = useState<DashboardMemories | null>(null);
  const [status, setStatus] = useState("Scarlet pronta");
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAutonomyOpen, setIsAutonomyOpen] = useState(false);
  const [autonomyHistory, setAutonomyHistory] = useState<AutonomyHistory | null>(null);
  const activeTurnIdRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void bootstrap();
  }, []);

  useEffect(() => {
    if (!isAutonomyOpen) {
      return;
    }
    void loadAutonomyHistory();
    const interval = window.setInterval(() => {
      void loadAutonomyHistory();
    }, 3000);
    return () => window.clearInterval(interval);
  }, [isAutonomyOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [flow.length, flow.map((item) => `${item.id}:${item.text.length}:${item.status}`).join("|")]);

  const heroFacts = useMemo(
    () => [
      {
        icon: <BookOpen size={15} aria-hidden="true" />,
        label: `${profile?.memory_count ?? memories?.total ?? 0} ricordi attivi`
      },
      {
        icon: <Clock3 size={15} aria-hidden="true" />,
        label: runtimeSettings?.timezone ?? "Europe/Rome"
      },
      {
        icon: <Shield size={15} aria-hidden="true" />,
        label: runtimeSettings?.privacy_scope ?? "locale singolo"
      }
    ],
    [memories?.total, profile?.memory_count, runtimeSettings]
  );

  async function bootstrap() {
    try {
      const [healthResult, settingsResult, profileResult, memoryResult, sessionResult] =
        await Promise.all([
          fetchHealth(),
          fetchRuntimeSettings(),
          fetchUserProfile(),
          fetchDashboardMemories({ limit: 24 }),
          fetchSessions(12)
        ]);
      setHealth(`${healthResult.model} attivo`);
      setRuntimeSettings(settingsResult);
      setSettingsDraft(settingsFromRuntime(settingsResult));
      setProfile(profileResult);
      setMemories(memoryResult);
      setSessions(sessionResult);
      if (sessionResult[0]) {
        await loadSession(sessionResult[0]);
      }
    } catch (error) {
      setStatus(errorMessage(error));
      setHealth("backend non raggiungibile");
    }
  }

  async function refreshPersonalData() {
    try {
      const [settingsResult, profileResult, memoryResult, sessionResult] = await Promise.all([
        fetchRuntimeSettings(),
        fetchUserProfile(),
        fetchDashboardMemories({ limit: 24 }),
        fetchSessions(12)
      ]);
      setRuntimeSettings(settingsResult);
      setSettingsDraft(settingsFromRuntime(settingsResult));
      setProfile(profileResult);
      setMemories(memoryResult);
      setSessions(sessionResult);
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function loadAutonomyHistory() {
    try {
      setAutonomyHistory(await fetchAutonomyHistory(30));
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function ensureSession(): Promise<ChatSession> {
    if (session) {
      return session;
    }
    return startNewSession();
  }

  async function startNewSession(): Promise<ChatSession> {
    const created = await createSession(mobileSessionTitle());
    setSession(created);
    setSessions((current) => mergeSessionList(created, current));
    setFlow([
      {
        id: `welcome-${created.id}`,
        kind: "system",
        title: "Nuova presenza attiva",
        text: "Scarlet ha aperto una conversazione pulita e usera profilo, tempo reale e memorie disponibili.",
        status: "done",
        createdAt: created.created_at
      }
    ]);
    return created;
  }

  async function loadSession(target: ChatSession) {
    setStatus("Recupero conversazione");
    const loaded = await fetchMessages(target.id);
    setSession(target);
    setFlow(flowFromMessages(loaded));
    setStatus("Sessione caricata");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (!message || isStreaming) {
      return;
    }
    setPrompt("");
    setIsStreaming(true);
    setStatus("Scarlet sta ascoltando");

    try {
      const initialActivity = activityCopy("request");
      setActivity("pending", initialActivity);
      const activeSession = await ensureSession();
      setActivity("pending", initialActivity);
      await streamTurn(activeSession.id, message, undefined, handleStreamEvent);
      setStatus("Risposta completata");
    } catch (error) {
      setStatus(errorMessage(error));
      clearActivity(activeTurnIdRef.current ?? "pending");
      upsertBlock({
        id: `error-${Date.now()}`,
        kind: "system",
        title: "Qualcosa si e interrotto",
        text: errorMessage(error),
        status: "error"
      });
    } finally {
      setIsStreaming(false);
      void refreshPersonalData();
    }
  }

  function handleStreamEvent(event: StreamEvent) {
    const turnId = String(event.data.turn_id ?? activeTurnIdRef.current ?? "pending");

    if (event.type === "turn_started") {
      const userMessage = event.data.user_message as ChatMessage;
      const startedTurnId = String(event.data.turn_id);
      activeTurnIdRef.current = startedTurnId;
      clearActivity("pending");
      appendBlock({
        id: userMessage.id,
        kind: "user",
        turnId: startedTurnId,
        title: "Tu",
        text: userMessage.content,
        status: "done",
        createdAt: userMessage.created_at
      });
      setActivity(startedTurnId, activityCopy("context"));
      return;
    }

    if (event.type === "runtime_context") {
      const blocks = recordArray(event.data.blocks);
      upsertBlock({
        id: `runtime-${turnId}`,
        kind: "context",
        turnId,
        title: "Contesto personale caricato",
        text:
          blocks.length > 0
            ? blocks.map((block) => runtimeBlockLabel(stringValue(block.type))).join(" · ")
            : "Profilo, sessione, tempo reale e stato operativo sono pronti.",
        status: "done",
        data: event.data
      });
      setActivity(turnId, activityCopy("memorySearch"));
      return;
    }

    if (event.type === "memory_context") {
      const selected = recordArray(event.data.selected);
      const nearMiss = recordArray(event.data.near_miss);
      upsertBlock({
        id: `memory-${turnId}`,
        kind: "memory",
        turnId,
        title: selected.length > 0 ? "Ricordi emersi" : "Memoria interrogata",
        text:
          selected.length > 0
            ? selected
                .slice(0, 3)
                .map((memory) => stringValue(memory.content))
                .filter(Boolean)
                .join("\n")
            : nearMiss.length > 0
              ? "Scarlet ha trovato segnali vicini, ma nessun ricordo abbastanza forte da usare come certezza."
              : "Nessun ricordo persistente e stato selezionato per questo messaggio.",
        status: "done",
        data: event.data
      });
      setActivity(turnId, activityCopy(selected.length > 0 ? "memoryConnect" : "memoryEmpty"));
      return;
    }

    if (event.type === "metacognitive_context") {
      const lessons = recordArray(event.data.lessons);
      if (lessons.length === 0) {
        return;
      }
      upsertBlock({
        id: `meta-${turnId}`,
        kind: "metacognition",
        turnId,
        title: "Lezioni interne richiamate",
        text: lessons
          .slice(0, 2)
          .map((lesson) => stringValue(lesson.lesson) || stringValue(lesson.title))
          .filter(Boolean)
          .join("\n"),
        status: "done",
        data: event.data
      });
      setActivity(turnId, activityCopy("thinking"));
      return;
    }

    if (event.type === "thinking_start") {
      upsertBlock({
        id: thinkingId(turnId, event),
        kind: "thinking",
        turnId,
        title: "Scarlet sta ragionando",
        text: "",
        status: "live",
        data: event.data
      });
      setActivity(turnId, activityCopy("thinking"));
      return;
    }

    if (event.type === "thinking_delta") {
      appendBlockText(thinkingId(turnId, event), String(event.data.text ?? ""), {
        kind: "thinking",
        title: "Scarlet sta ragionando",
        status: "live",
        turnId,
        data: event.data
      });
      return;
    }

    if (event.type === "thinking_captured") {
      upsertBlock({
        id: thinkingId(turnId, event),
        kind: "thinking",
        turnId,
        title: "Ragionamento completato",
        text: String(event.data.text ?? ""),
        status: "done",
        data: event.data
      });
      setActivity(turnId, {
        title: "Ragionamento pronto",
        text: "Scarlet sta preparando il prossimo passo.",
        status: "live"
      });
      return;
    }

    if (event.type === "text_start") {
      upsertBlock({
        id: textId(turnId, event),
        kind: "note",
        turnId,
        title: "Nota di Scarlet",
        text: "",
        status: "live",
        data: event.data
      });
      clearActivity(turnId);
      return;
    }

    if (event.type === "text_delta") {
      clearActivity(turnId);
      appendBlockText(textId(turnId, event), String(event.data.text ?? ""), {
        kind: "note",
        title: "Nota di Scarlet",
        status: "live",
        turnId,
        data: event.data
      });
      return;
    }

    if (event.type === "assistant_note") {
      upsertBlock({
        id: textId(turnId, event),
        kind: "note",
        turnId,
        title: "Nota di Scarlet",
        text: String(event.data.text ?? ""),
        status: "done",
        data: event.data
      });
      setActivity(turnId, {
        title: "Prossimo passo",
        text: "Scarlet sta verificando se servono altre azioni prima della risposta.",
        status: "live"
      });
      return;
    }

    if (event.type === "tool_call") {
      const args = recordValue(event.data.arguments);
      const path = stringValue(args?.path);
      upsertBlock({
        id: toolId(event),
        kind: "tool",
        turnId,
        title: toolTitle(path),
        text: stringValue(args?.intent) || path || "Scarlet usa API Mind.",
        status: "live",
        data: event.data
      });
      setActivity(turnId, activityForToolCall(path));
      return;
    }

    if (event.type === "tool_result") {
      const args = recordValue(event.data.arguments);
      const path = stringValue(args?.path);
      upsertBlock({
        id: toolId(event),
        kind: "tool",
        turnId,
        title: toolTitle(path),
        text: toolResultPreview(event.data) || "Operazione completata.",
        status: event.data.status === "error" ? "error" : "done",
        data: event.data
      });
      setActivity(turnId, activityForToolResult(path, event.data.status));
      return;
    }

    if (event.type === "assistant_answer") {
      clearActivity(turnId);
      upsertBlock({
        id: textId(turnId, event),
        kind: "answer",
        turnId,
        title: "Risposta di Scarlet",
        text: String(event.data.text ?? ""),
        status: "done",
        data: event.data
      });
      return;
    }

    if (event.type === "turn_complete") {
      const assistantMessage = recordValue(event.data.assistant_message);
      const completeTurnId = String(event.data.turn_id);
      const completedSession = recordValue(event.data.session);
      if (completedSession) {
        const nextSession = completedSession as ChatSession;
        setSession(nextSession);
        setSessions((current) => mergeSessionList(nextSession, current));
      }
      clearActivity(completeTurnId);
      completeTurn(completeTurnId, assistantMessage);
      return;
    }

    if (event.type === "error") {
      clearActivity(turnId);
      upsertBlock({
        id: `error-${Date.now()}`,
        kind: "system",
        turnId,
        title: "Errore runtime",
        text: String(event.data.message ?? "Errore nello stream."),
        status: "error",
        data: event.data
      });
    }
  }

  function appendBlock(next: MobileBlock) {
    setFlow((current) => normalizeFlowBlocks([...current, next]));
  }

  function upsertBlock(next: MobileBlock) {
    setFlow((current) => {
      const index = current.findIndex((item) => item.id === next.id);
      if (index === -1) {
        return normalizeFlowBlocks([...current, next]);
      }
      return normalizeFlowBlocks(
        current.map((item) => (item.id === next.id ? { ...item, ...next } : item))
      );
    });
  }

  function appendBlockText(
    id: string,
    text: string,
    fallback: Pick<MobileBlock, "kind" | "title" | "status" | "turnId" | "data">
  ) {
    setFlow((current) => {
      const index = current.findIndex((item) => item.id === id);
      if (index === -1) {
        return normalizeFlowBlocks([
          ...current,
          {
            id,
            kind: fallback.kind,
            title: fallback.title,
            text,
            status: fallback.status,
            turnId: fallback.turnId,
            data: fallback.data
          }
        ]);
      }
      return normalizeFlowBlocks(
        current.map((item) =>
          item.id === id
            ? {
                ...item,
                text: `${item.text}${text}`,
                status: fallback.status,
                data: { ...(item.data ?? {}), ...(fallback.data ?? {}) }
              }
            : item
        )
      );
    });
  }

  function setActivity(turnId: string, copy: MobileActivityCopy) {
    const block: MobileBlock = {
      id: activityId(turnId),
      kind: "activity",
      turnId,
      title: copy.title,
      text: copy.text,
      status: copy.status ?? "live",
      data: { ephemeral: true }
    };
    setFlow((current) =>
      normalizeFlowBlocks([
        ...current.filter((item) => item.id !== activityId(turnId)),
        block
      ])
    );
  }

  function clearActivity(turnId: string) {
    setFlow((current) =>
      normalizeFlowBlocks(
        current.filter((item) => item.id !== activityId(turnId) && item.id !== activityId("pending"))
      )
    );
  }

  function completeTurn(turnId: string, assistantMessage?: Record<string, unknown>) {
    setFlow((current) =>
      normalizeFlowBlocks([
        ...current.map((item) =>
          item.turnId === turnId && item.status === "live"
            ? { ...item, status: "done" as const }
            : item
        ),
        ...(assistantMessage &&
        !current.some((item) => item.kind === "answer" && item.turnId === turnId)
          ? [
              {
                id: `answer-${turnId}`,
                kind: "answer" as const,
                turnId,
                title: "Risposta di Scarlet",
                text: stringValue(assistantMessage.content),
                status: "done" as const,
                data: assistantMessage
              }
            ]
          : [])
      ])
    );
  }

  async function saveSettings() {
    setStatus("Aggiorno il profilo operativo");
    try {
      const saved = await updateRuntimeSettings(settingsDraft);
      setRuntimeSettings(saved);
      setSettingsDraft(settingsFromRuntime(saved));
      setProfile(await fetchUserProfile());
      setStatus("Profilo aggiornato");
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  return (
    <main className="mobile-shell">
      <section className="mobile-app" aria-label="Scarlet mobile app">
        <header className="mobile-topbar">
          <div className="mobile-brand">
            <div className="mobile-sigil">
              <Sparkles size={19} aria-hidden="true" />
            </div>
            <div>
              <span>Scarlet</span>
              <strong>{health}</strong>
            </div>
          </div>
          <div className="mobile-topbar-actions">
            <button
              aria-label="Apri la cognizione autonoma di Scarlet"
              className="mobile-icon-button autonomy-button"
              type="button"
              onClick={() => setIsAutonomyOpen(true)}
            >
              <BrainCircuit size={18} aria-hidden="true" />
            </button>
            <button
              aria-label="Apri contesto e sessioni"
              className="mobile-icon-button"
              type="button"
              onClick={() => setIsMenuOpen(true)}
            >
              <Settings size={17} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="mobile-content">
          {activeTab === "chat" ? (
            <ChatScreen
              flow={flow}
              isStreaming={isStreaming}
              prompt={prompt}
              scrollRef={scrollRef}
              onPromptChange={setPrompt}
              onSubmit={handleSubmit}
            />
          ) : null}
          {activeTab === "memory" ? (
            <MemoryScreen memories={memories} profile={profile} onRefresh={() => void refreshPersonalData()} />
          ) : null}
          {activeTab === "actions" ? <ActionsScreen /> : null}
          {activeTab === "profile" ? (
            <ProfileScreen
              draft={settingsDraft}
              profile={profile}
              runtimeSettings={runtimeSettings}
              setDraft={setSettingsDraft}
              onSave={() => void saveSettings()}
            />
          ) : null}
        </div>

        <MobileContextDrawer
          health={health}
          heroFacts={heroFacts}
          isOpen={isMenuOpen}
          session={session}
          sessions={sessions}
          status={status}
          onClose={() => setIsMenuOpen(false)}
          onLoadSession={(item) => {
            setIsMenuOpen(false);
            void loadSession(item);
          }}
          onNewSession={() => {
            setIsMenuOpen(false);
            void startNewSession();
          }}
          onRefresh={() => void refreshPersonalData()}
        />

        <AutonomyHistoryPanel
          history={autonomyHistory}
          isOpen={isAutonomyOpen}
          onClose={() => setIsAutonomyOpen(false)}
          onRefresh={() => void loadAutonomyHistory()}
        />

        <nav className="mobile-nav" aria-label="Navigazione Scarlet">
          <MobileNavButton
            active={activeTab === "chat"}
            icon={<MessageCircle size={18} aria-hidden="true" />}
            label="Chat"
            onClick={() => setActiveTab("chat")}
          />
          <MobileNavButton
            active={activeTab === "memory"}
            icon={<BookOpen size={18} aria-hidden="true" />}
            label="Memoria"
            onClick={() => setActiveTab("memory")}
          />
          <MobileNavButton
            active={activeTab === "actions"}
            icon={<Zap size={18} aria-hidden="true" />}
            label="Azioni"
            onClick={() => setActiveTab("actions")}
          />
          <MobileNavButton
            active={activeTab === "profile"}
            icon={<UserRound size={18} aria-hidden="true" />}
            label="Profilo"
            onClick={() => setActiveTab("profile")}
          />
        </nav>
      </section>
    </main>
  );
}

function AutonomyHistoryPanel({
  history,
  isOpen,
  onClose,
  onRefresh
}: {
  history: AutonomyHistory | null;
  isOpen: boolean;
  onClose: () => void;
  onRefresh: () => void;
}) {
  if (!isOpen) {
    return null;
  }
  return (
    <div className="autonomy-history-layer">
      <button
        aria-label="Chiudi cognizione autonoma"
        className="autonomy-history-backdrop"
        onClick={onClose}
        type="button"
      />
      <aside
        aria-label="Cronologia della cognizione autonoma di Scarlet"
        aria-modal="true"
        className="autonomy-history-panel"
        role="dialog"
      >
        <header className="autonomy-history-header">
          <div className="autonomy-history-title">
            <div className="autonomy-history-sigil">
              <BrainCircuit size={20} aria-hidden="true" />
            </div>
            <div>
              <span>Continuita interiore</span>
              <strong>Cosa ha vissuto Scarlet</strong>
            </div>
          </div>
          <div className="autonomy-history-actions">
            <button aria-label="Aggiorna cronologia" onClick={onRefresh} type="button">
              <RefreshCcw size={16} aria-hidden="true" />
            </button>
            <button aria-label="Chiudi cronologia" onClick={onClose} type="button">
              <X size={17} aria-hidden="true" />
            </button>
          </div>
        </header>
        <div className="autonomy-history-scroll">
          {!history ? (
            <div className="autonomy-empty">
              <BrainCircuit size={24} aria-hidden="true" />
              <strong>Sto aprendo il suo spazio interiore.</strong>
              <span>Le attivazioni compariranno qui mentre accadono.</span>
            </div>
          ) : history.cycles.length === 0 ? (
            <div className="autonomy-empty">
              <Moon size={24} aria-hidden="true" />
              <strong>Nessun ciclo ancora vissuto.</strong>
              <span>La prima attivazione verra conservata qui.</span>
            </div>
          ) : (
            history.cycles.map((cycle) => (
              <AutonomyCycleCard cycle={cycle} key={cycle.activation.id} />
            ))
          )}
        </div>
      </aside>
    </div>
  );
}

function AutonomyCycleCard({ cycle }: { cycle: AutonomousCycle }) {
  const checkpoint = cycle.messages.find((message) => message.role === "assistant");
  const workspaceCandidates = recordArray(
    cycle.activation.workspace.selected_candidates
  );
  const narrativeEvents = cycle.events.filter((event) =>
    [
      "llm.thinking.captured",
      "assistant.note.emitted",
      "mind.tool_call.started",
      "mind.tool_call.completed",
      "mind.tool_call.failed"
    ].includes(event.type)
  );
  return (
    <article className={`autonomy-cycle ${cycle.activation.status}`}>
      <div className="autonomy-cycle-meta">
        <div>
          <span>{formatSessionDate(cycle.activation.scheduled_at)}</span>
          <strong>
            {cycle.activation.status === "running"
              ? "Scarlet sta riflettendo"
              : cycle.activation.status === "completed"
                ? "Ciclo concluso"
                : cycle.activation.status === "deferred"
                  ? "Ha dato spazio alla conversazione"
                  : "Ciclo non completato"}
          </strong>
        </div>
        <span className="autonomy-mode">
          {cycle.activation.active_mode || cycle.activation.status}
        </span>
      </div>
      <div className="autonomy-thread">
        {narrativeEvents.map((event) => (
          <AutonomyEventBubble event={event} key={event.id} />
        ))}
        {checkpoint ? (
          <div className="autonomy-bubble checkpoint">
            <span>Checkpoint interiore</span>
            <p>{checkpoint.content}</p>
          </div>
        ) : null}
      </div>
      {workspaceCandidates.length > 0 ? (
        <details className="autonomy-technical">
          <summary>Da cosa e nato questo pensiero</summary>
          {workspaceCandidates.map((candidate) => (
            <div key={stringValue(candidate.id) || stringValue(candidate.claim)}>
              <strong>
                {stringValue(candidate.cognitive_question) ||
                  "Una continuita ha chiesto attenzione"}
              </strong>
              <span>{stringValue(candidate.claim)}</span>
            </div>
          ))}
        </details>
      ) : null}
      {cycle.tool_calls.length > 0 ? (
        <details className="autonomy-technical">
          <summary>{cycle.tool_calls.length} azioni cognitive</summary>
          {cycle.tool_calls.map((tool) => (
            <div key={tool.id}>
              <strong>{stringValue(tool.arguments.command) || tool.tool_name}</strong>
              <span>{tool.status}</span>
            </div>
          ))}
        </details>
      ) : null}
    </article>
  );
}

function AutonomyEventBubble({ event }: { event: AutonomousCycle["events"][number] }) {
  if (event.type === "llm.thinking.captured") {
    return (
      <details className="autonomy-thinking">
        <summary>Un pensiero ha preso forma</summary>
        <p>{stringValue(event.payload.text) || "Pensiero conservato nel trace."}</p>
      </details>
    );
  }
  const isTool = event.type.startsWith("mind.tool_call");
  const text =
    stringValue(event.payload.text) ||
    stringValue(recordValue(event.payload.operation)?.intent) ||
    stringValue(recordValue(event.payload.operation)?.command) ||
    (isTool ? "Scarlet ha usato una parte della sua mente." : "Passaggio interno");
  return (
    <div className={`autonomy-bubble ${isTool ? "tool" : "note"}`}>
      <span>{isTool ? "Azione cognitiva" : "Nota di Scarlet"}</span>
      <p>{text}</p>
    </div>
  );
}

function ChatScreen({
  flow,
  isStreaming,
  onPromptChange,
  onSubmit,
  prompt,
  scrollRef
}: {
  flow: MobileBlock[];
  isStreaming: boolean;
  onPromptChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  prompt: string;
  scrollRef: React.RefObject<HTMLDivElement | null>;
}) {
  const showStarterPrompts = !flow.some((block) => block.kind === "user");

  return (
    <div className="mobile-screen chat-screen">
      <div className="mobile-chat-scroll" ref={scrollRef}>
        {flow.length === 0 ? (
          <div className="mobile-empty-chat">
            <WandSparkles size={26} aria-hidden="true" />
            <strong>Inizia da una frase normale.</strong>
            <span>Scarlet usera memoria, contesto e tempo reale senza chiederti come funziona.</span>
          </div>
        ) : (
          flow.map((block) => <MobileFlowBlock block={block} key={block.id} />)
        )}
        {showStarterPrompts ? <StarterPrompts onPromptChange={onPromptChange} /> : null}
      </div>

      <form className="mobile-composer" onSubmit={onSubmit}>
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          placeholder="Scrivi a Scarlet"
          rows={1}
        />
        <button type="submit" disabled={!prompt.trim() || isStreaming}>
          <Send size={17} aria-hidden="true" />
        </button>
      </form>
    </div>
  );
}

function MobileContextDrawer({
  health,
  heroFacts,
  isOpen,
  onClose,
  onLoadSession,
  onNewSession,
  onRefresh,
  session,
  sessions,
  status
}: {
  health: string;
  heroFacts: Array<{ icon: ReactNode; label: string }>;
  isOpen: boolean;
  onClose: () => void;
  onLoadSession: (session: ChatSession) => void;
  onNewSession: () => void;
  onRefresh: () => void;
  session: ChatSession | null;
  sessions: ChatSession[];
  status: string;
}) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="mobile-drawer-layer" role="presentation">
      <button
        aria-label="Chiudi menu"
        className="mobile-drawer-backdrop"
        type="button"
        onClick={onClose}
      />
      <aside aria-label="Contesto e sessioni Scarlet" aria-modal="true" className="mobile-drawer" role="dialog">
        <header className="mobile-drawer-header">
          <div>
            <span>Centro Scarlet</span>
            <strong>{status}</strong>
          </div>
          <button aria-label="Chiudi menu" className="mobile-icon-button" type="button" onClick={onClose}>
            <X size={17} aria-hidden="true" />
          </button>
        </header>

        <section className="mobile-drawer-panel">
          <div className="mobile-drawer-panel-title">
            <strong>Contesto attivo</strong>
            <button className="mobile-mini-action" type="button" onClick={onRefresh}>
              <RefreshCcw size={14} aria-hidden="true" />
              Sync
            </button>
          </div>
          <div className="mobile-drawer-facts">
            {heroFacts.map((fact) => (
              <span key={fact.label}>
                {fact.icon}
                {fact.label}
              </span>
            ))}
            <span>
              <Radio size={15} aria-hidden="true" />
              {health}
            </span>
          </div>
        </section>

        <section className="mobile-drawer-panel">
          <div className="mobile-drawer-panel-title">
            <strong>Sessioni</strong>
            <button className="mobile-mini-action primary" type="button" onClick={onNewSession}>
              <Plus size={14} aria-hidden="true" />
              Nuova
            </button>
          </div>
          <div className="mobile-drawer-sessions">
            {sessions.length === 0 ? (
              <div className="mobile-empty-panel">Nessuna sessione recente.</div>
            ) : (
              sessions.slice(0, 12).map((item) => (
                <button
                  className={item.id === session?.id ? "active" : ""}
                  key={item.id}
                  type="button"
                  onClick={() => onLoadSession(item)}
                >
                  <strong>{sessionTitle(item)}</strong>
                  <span>{formatSessionDate(item.updated_at)}</span>
                </button>
              ))
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}

function StarterPrompts({ onPromptChange }: { onPromptChange: (value: string) => void }) {
  return (
    <section className="mobile-starter-prompts">
      <span>Puoi provare</span>
      <button type="button" onClick={() => onPromptChange("Cosa ricordi di me che potrebbe essermi utile oggi?")}>
        Cosa ricordi di me che potrebbe essermi utile oggi?
      </button>
      <button
        type="button"
        onClick={() => onPromptChange("Aiutami a organizzare la serata tenendo conto delle mie preferenze.")}
      >
        Aiutami a organizzare la serata.
      </button>
    </section>
  );
}

function MobileFlowBlock({ block }: { block: MobileBlock }) {
  const icon = blockIcon(block.kind);
  if (block.kind === "user") {
    return (
      <article className="mobile-message user">
        <div className="mobile-message-bubble">
          <RichText text={block.text} />
        </div>
      </article>
    );
  }

  return (
    <article className={`mobile-flow-block ${block.kind} ${block.status ?? "done"}`}>
      <div className="mobile-flow-icon">{icon}</div>
      <div className="mobile-flow-content">
        <div className="mobile-flow-header">
          <strong>{block.title}</strong>
          {block.status === "live" ? <span>live</span> : null}
          {block.status === "error" ? <span>errore</span> : null}
        </div>
        {block.kind === "activity" ? (
          <div className="mobile-activity-copy">
            {block.status === "live" ? (
              <span className="mobile-activity-pulse" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            ) : null}
            <RichText text={block.text || "..."} />
          </div>
        ) : block.kind === "thinking" ? (
          <p>{block.status === "live" ? "Sto ragionando in profondita su cosa serve davvero." : firstLine(block.text) || "Ragionamento completato."}</p>
        ) : (
          <RichText text={block.text || "..."} />
        )}
        {block.kind === "memory" && recordArray(block.data?.selected).length > 0 ? (
          <div className="mobile-memory-mini-list">
            {recordArray(block.data?.selected)
              .slice(0, 2)
              .map((memory) => (
                <span key={stringValue(memory.id) || stringValue(memory.content)}>
                  {truncate(stringValue(memory.content), 120)}
                </span>
              ))}
          </div>
        ) : null}
      </div>
    </article>
  );
}

function MemoryScreen({
  memories,
  onRefresh,
  profile
}: {
  memories: DashboardMemories | null;
  onRefresh: () => void;
  profile: UserProfile | null;
}) {
  const items = memories?.memories ?? [];
  return (
    <div className="mobile-screen mobile-list-screen">
      <ScreenHeader
        icon={<BookOpen size={18} aria-hidden="true" />}
        label="Memoria viva"
        title="Scarlet costruisce continuita invece di ricominciare da zero."
        action={
          <button className="mobile-icon-button" type="button" onClick={onRefresh}>
            <RefreshCcw size={16} aria-hidden="true" />
          </button>
        }
      />

      <section className="mobile-insight-band">
        <div>
          <strong>{profile?.memory_count ?? memories?.total ?? 0}</strong>
          <span>ricordi personali e progettuali</span>
        </div>
        <div>
          <strong>{profile?.language_label ?? "Italiano"}</strong>
          <span>lingua piattaforma</span>
        </div>
      </section>

      <div className="mobile-scroll-list">
        {items.length === 0 ? (
          <div className="mobile-empty-panel">Scarlet non ha ancora memorie visibili in dashboard.</div>
        ) : (
          items.slice(0, 18).map((memory) => <MobileMemoryCard memory={memory} key={memory.id} />)
        )}
        <SoonCard
          icon={<Network size={18} aria-hidden="true" />}
          title="Grafo dei ricordi"
          text="Scarlet colleghera persone, abitudini, luoghi, emozioni e decisioni in una mappa navigabile."
        />
        <SoonCard
          icon={<Moon size={18} aria-hidden="true" />}
          title="Revisione notturna"
          text="Scarlet potra rivedere la giornata, consolidare ricordi e correggere collegamenti deboli."
        />
      </div>
    </div>
  );
}

function MobileMemoryCard({ memory }: { memory: DashboardMemory }) {
  return (
    <article className="mobile-memory-card">
      <div className="mobile-memory-topline">
        <strong>{memory.scope === "user" ? "Personale" : memory.type}</strong>
        <span>{Math.round(memory.confidence * 100)}%</span>
      </div>
      <p>{memory.content}</p>
      <div className="mobile-memory-tags">
        {memory.tags.slice(0, 4).map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
    </article>
  );
}

function ActionsScreen() {
  return (
    <div className="mobile-screen mobile-list-screen">
      <ScreenHeader
        icon={<Zap size={18} aria-hidden="true" />}
        label="Operativita"
        title="Il prossimo salto: Scarlet non solo risponde, prepara azioni reali."
      />
      <div className="mobile-scroll-list">
        <SoonCard
          icon={<Bell size={18} aria-hidden="true" />}
          title="Wake-up agentici"
          text="Promemoria intelligenti, controlli periodici e analisi automatiche negli orari utili."
        />
        <SoonCard
          icon={<Plane size={18} aria-hidden="true" />}
          title="Viaggi e prenotazioni"
          text="Ricerche avanzate, confronto offerte, proposte e prenotazioni con conferma finale dell'utente."
        />
        <SoonCard
          icon={<Utensils size={18} aria-hidden="true" />}
          title="Routine e vita quotidiana"
          text="Ristoranti, consegne, preferenze alimentari e abitudini trattate come contesto vivo."
        />
        <SoonCard
          icon={<Home size={18} aria-hidden="true" />}
          title="Casa e sistemi reali"
          text="Domotica, allarmi e ambienti digitali integrati con permessi chiari e tracciabilita."
        />
        <SoonCard
          icon={<Compass size={18} aria-hidden="true" />}
          title="UI effimere"
          text="Interfacce temporanee create da Scarlet quando una chat non basta: gallery, moduli, scelte e conferme."
        />
      </div>
    </div>
  );
}

function ProfileScreen({
  draft,
  onSave,
  profile,
  runtimeSettings,
  setDraft
}: {
  draft: SettingsDraft;
  onSave: () => void;
  profile: UserProfile | null;
  runtimeSettings: RuntimeSettings | null;
  setDraft: (updater: (current: SettingsDraft) => SettingsDraft) => void;
}) {
  return (
    <div className="mobile-screen mobile-list-screen">
      <ScreenHeader
        icon={<Settings size={18} aria-hidden="true" />}
        label="Profilo attivo"
        title="Questi dati entrano davvero nel contesto operativo di Scarlet."
      />

      <section className="mobile-profile-card">
        <div className="mobile-profile-avatar">
          <UserRound size={24} aria-hidden="true" />
        </div>
        <div>
          <strong>{profile?.display_name ?? draft.user_display_name}</strong>
          <span>
            {profile?.country_label ?? "Italia"} · {profile?.timezone ?? "Europe/Rome"}
          </span>
        </div>
      </section>

      <div className="mobile-settings-form">
        <MobileInput
          label="Nome"
          value={draft.user_display_name}
          onChange={(value) => setDraft((current) => ({ ...current, user_display_name: value }))}
        />
        <MobileSelect
          label="Lingua"
          value={draft.language}
          options={runtimeSettings?.options.languages ?? [{ code: "it", label: "Italiano" }]}
          optionValue="code"
          onChange={(value) => setDraft((current) => ({ ...current, language: value }))}
        />
        <MobileSelect
          label="Paese"
          value={draft.country_code}
          options={runtimeSettings?.options.countries ?? [{ code: "IT", label: "Italia" }]}
          optionValue="code"
          onChange={(value) => setDraft((current) => ({ ...current, country_code: value }))}
        />
        <MobileSelect
          label="Fuso orario"
          value={draft.timezone}
          options={runtimeSettings?.options.timezones ?? [{ id: "Europe/Rome", label: "Italia - Europe/Rome" }]}
          optionValue="id"
          onChange={(value) => setDraft((current) => ({ ...current, timezone: value }))}
        />
        <button className="mobile-primary-action" type="button" onClick={onSave}>
          <Check size={17} aria-hidden="true" />
          Aggiorna Scarlet
        </button>
      </div>

      <SoonCard
        icon={<Shield size={18} aria-hidden="true" />}
        title="Privacy multiutente"
        text="Profili separati, permessi memoria e controlli granulari arriveranno nelle prossime versioni."
      />
    </div>
  );
}

function ScreenHeader({
  action,
  icon,
  label,
  title
}: {
  action?: ReactNode;
  icon: ReactNode;
  label: string;
  title: string;
}) {
  return (
    <header className="mobile-screen-header">
      <div className="screen-header-icon">{icon}</div>
      <div>
        <span>{label}</span>
        <h2>{title}</h2>
      </div>
      {action ? <div className="screen-header-action">{action}</div> : null}
    </header>
  );
}

function SoonCard({
  icon,
  text,
  title
}: {
  icon: ReactNode;
  text: string;
  title: string;
}) {
  return (
    <article className="mobile-soon-card">
      <div className="soon-icon">{icon}</div>
      <div>
        <div className="soon-title-row">
          <strong>{title}</strong>
          <span>Presto disponibile</span>
        </div>
        <p>{text}</p>
      </div>
      <ChevronRight size={17} aria-hidden="true" />
    </article>
  );
}

function MobileInput({
  label,
  onChange,
  value
}: {
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <label className="mobile-field">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function MobileSelect<T extends Record<string, string>>({
  label,
  onChange,
  optionValue,
  options,
  value
}: {
  label: string;
  onChange: (value: string) => void;
  optionValue: keyof T;
  options: T[];
  value: string;
}) {
  return (
    <label className="mobile-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option[optionValue]} value={option[optionValue]}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function MobileNavButton({
  active,
  icon,
  label,
  onClick
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={active ? "active" : ""} type="button" onClick={onClick}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

function blockIcon(kind: MobileBlockKind): ReactNode {
  if (kind === "context") {
    return <MapPin size={16} aria-hidden="true" />;
  }
  if (kind === "memory") {
    return <BookOpen size={16} aria-hidden="true" />;
  }
  if (kind === "metacognition" || kind === "thinking") {
    return <Sparkles size={16} aria-hidden="true" />;
  }
  if (kind === "tool") {
    return <Search size={16} aria-hidden="true" />;
  }
  if (kind === "activity") {
    return <Radio size={16} aria-hidden="true" />;
  }
  if (kind === "answer") {
    return <Bot size={16} aria-hidden="true" />;
  }
  if (kind === "note") {
    return <MessageCircle size={16} aria-hidden="true" />;
  }
  return <Radio size={16} aria-hidden="true" />;
}

function RichText({ text }: { text: string }) {
  const blocks = richTextBlocks(text);
  return (
    <div className="mobile-rich-text">
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return <h3 key={`${block.kind}-${index}`}>{renderInline(block.lines[0])}</h3>;
        }
        if (block.kind === "list") {
          return (
            <ul key={`${block.kind}-${index}`}>
              {block.lines.map((line) => (
                <li key={line}>{renderInline(line)}</li>
              ))}
            </ul>
          );
        }
        if (block.kind === "ordered") {
          return (
            <ol key={`${block.kind}-${index}`}>
              {block.lines.map((line) => (
                <li key={line}>{renderInline(line)}</li>
              ))}
            </ol>
          );
        }
        return <p key={`${block.kind}-${index}`}>{renderInline(block.lines.join("\n"))}</p>;
      })}
    </div>
  );
}

function richTextBlocks(text: string): Array<{
  kind: "heading" | "list" | "ordered" | "paragraph";
  lines: string[];
}> {
  const blocks: Array<{
    kind: "heading" | "list" | "ordered" | "paragraph";
    lines: string[];
  }> = [];
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  let paragraph: string[] = [];
  let list: string[] = [];
  let ordered: string[] = [];

  function flushParagraph() {
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", lines: paragraph });
      paragraph = [];
    }
  }

  function flushList() {
    if (list.length > 0) {
      blocks.push({ kind: "list", lines: list });
      list = [];
    }
    if (ordered.length > 0) {
      blocks.push({ kind: "ordered", lines: ordered });
      ordered = [];
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }
    const heading = line.match(/^#{1,4}\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push({ kind: "heading", lines: [heading[1]] });
      continue;
    }
    const bullet = line.match(/^[-*•]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      if (ordered.length > 0) {
        flushList();
      }
      list.push(bullet[1]);
      continue;
    }
    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (numbered) {
      flushParagraph();
      if (list.length > 0) {
        flushList();
      }
      ordered.push(numbered[1]);
      continue;
    }
    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();
  return blocks.length > 0 ? blocks : [{ kind: "paragraph", lines: [text || "..."] }];
}

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|__[^_]+__)/g);
  return parts.map((part, index) => {
    const bold = part.match(/^(\*\*|__)(.+)(\*\*|__)$/);
    if (bold) {
      return <strong key={`${part}-${index}`}>{bold[2]}</strong>;
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function flowFromMessages(messages: ChatMessage[]): MobileBlock[] {
  if (messages.length === 0) {
    return [];
  }
  return normalizeFlowBlocks(messages.map((message) => ({
    id: message.id,
    kind: message.role === "user" ? "user" : "answer",
    turnId: message.turn_id ?? undefined,
    title: message.role === "user" ? "Tu" : "Risposta di Scarlet",
    text: message.content,
    createdAt: message.created_at,
    status: "done"
  })));
}

function normalizeFlowBlocks(blocks: MobileBlock[]): MobileBlock[] {
  const byId = new Map<string, MobileBlock>();
  const order: string[] = [];

  for (const block of blocks) {
    if (!byId.has(block.id)) {
      order.push(block.id);
      byId.set(block.id, block);
      continue;
    }
    byId.set(block.id, { ...byId.get(block.id)!, ...block });
  }

  const answerByTurn = new Map<string, MobileBlock>();
  const answerIdsToDrop = new Set<string>();
  for (const id of order) {
    const block = byId.get(id);
    if (!block || block.kind !== "answer" || !block.turnId) {
      continue;
    }
    const current = answerByTurn.get(block.turnId);
    if (!current) {
      answerByTurn.set(block.turnId, block);
      continue;
    }
    const preferred = preferredAnswerBlock(current, block);
    const dropped = preferred.id === current.id ? block : current;
    answerByTurn.set(block.turnId, preferred);
    answerIdsToDrop.add(dropped.id);
  }

  return order
    .map((id) => byId.get(id))
    .filter((block): block is MobileBlock => Boolean(block))
    .filter((block) => !(block.kind === "answer" && answerIdsToDrop.has(block.id)));
}

function preferredAnswerBlock(left: MobileBlock, right: MobileBlock): MobileBlock {
  const leftIsStream = left.id.startsWith("text-");
  const rightIsStream = right.id.startsWith("text-");
  if (leftIsStream !== rightIsStream) {
    return leftIsStream ? left : right;
  }
  return right.text.length > left.text.length ? right : left;
}

function settingsFromRuntime(settings: RuntimeSettings): SettingsDraft {
  return {
    timezone: settings.timezone,
    language: settings.language,
    country_code: settings.country_code,
    profile_id: settings.profile_id,
    privacy_scope: settings.privacy_scope,
    user_display_name: settings.user_display_name
  };
}

function runtimeBlockLabel(type: string): string {
  if (type === "session_context") {
    return "continuita sessione";
  }
  if (type === "message_context") {
    return "contesto messaggio";
  }
  if (type === "scarlet_state") {
    return "stato Scarlet";
  }
  if (type === "metacognitive_context") {
    return "lezioni interne";
  }
  return "contesto";
}

function toolTitle(path: string): string {
  if (path.includes("/memory")) {
    return "Scarlet consulta la memoria";
  }
  if (path.includes("/sessions")) {
    return "Scarlet recupera una conversazione";
  }
  if (path.includes("/schema")) {
    return "Scarlet controlla le sue capacita";
  }
  if (path.includes("/metacognition")) {
    return "Scarlet rivede il proprio ragionamento";
  }
  return "Scarlet usa una funzione interna";
}

function toolResultPreview(data: Record<string, unknown>): string {
  const resultEnvelope = recordValue(data.result);
  const result = recordValue(resultEnvelope?.result);
  const error = recordValue(resultEnvelope?.error);
  if (error) {
    return stringValue(error.message) || "Operazione non riuscita.";
  }
  if (recordArray(result?.memories).length > 0) {
    return `${recordArray(result?.memories).length} ricordi trovati.`;
  }
  if (recordArray(result?.sessions).length > 0) {
    return `${recordArray(result?.sessions).length} sessioni trovate.`;
  }
  if (recordValue(result?.memory)) {
    return "Nuovo ricordo consolidato.";
  }
  if (recordValue(result?.session)) {
    return "Conversazione recuperata.";
  }
  return "Evidenza interna ricevuta.";
}

function textId(turnId: string, event: StreamEvent): string {
  return `text-${turnId}-${String(event.data.model_step ?? "1")}-${String(event.data.index ?? "0")}`;
}

function thinkingId(turnId: string, event: StreamEvent): string {
  return `thinking-${turnId}-${String(event.data.model_step ?? "1")}-${String(event.data.index ?? "0")}`;
}

function toolId(event: StreamEvent): string {
  return `tool-${String(event.data.provider_tool_use_id ?? event.data.tool_call_id ?? "pending")}`;
}

function sessionTitle(session: ChatSession | null): string {
  if (!session) {
    return "Nuova conversazione";
  }
  return session.title?.trim() || "Conversazione Scarlet";
}

function mobileSessionTitle(): string {
  return `Scarlet ${new Date().toLocaleString([], {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit"
  })}`;
}

function formatSessionDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Data non disponibile";
  }
  return date.toLocaleString("it-IT", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "2-digit"
  });
}

function mergeSessionList(session: ChatSession, sessions: ChatSession[]): ChatSession[] {
  return [session, ...sessions.filter((item) => item.id !== session.id)]
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .slice(0, 12);
}

function firstLine(value: string): string {
  return truncate(value.trim().split(/\r?\n/).find(Boolean) || "", 180);
}

function truncate(value: string, maxLength: number): string {
  if (!value) {
    return "";
  }
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : undefined;
}

function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") as Record<string, unknown>[] : [];
}

function stringValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore inatteso";
}

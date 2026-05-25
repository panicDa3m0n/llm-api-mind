import {
  Activity,
  AlertTriangle,
  Archive,
  BookOpen,
  Bot,
  Braces,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  FileSearch,
  Gauge,
  ListChecks,
  MessageSquarePlus,
  PanelRight,
  RefreshCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  UserCog,
  UserRound
} from "lucide-react";
import type { Dispatch, FormEvent, ReactNode, SetStateAction } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  createSession,
  fetchDashboardMemories,
  fetchEvents,
  fetchHealth,
  fetchMessages,
  fetchRuntimeSettings,
  fetchSessions,
  fetchTraces,
  fetchUserProfile,
  streamTurn,
  updateRuntimeSettings
} from "./api";
import type {
  AgentStep,
  ChatMessage,
  ChatSession,
  ChatTurn,
  CognitiveEvent,
  DashboardMemory,
  DashboardMemories,
  RuntimeSettings,
  StreamEvent,
  TraceItem,
  UserProfile
} from "./types";

type Status = {
  label: string;
  tone: "idle" | "busy" | "ok" | "error";
};

type StepSummary = {
  total: number;
  active: number;
  errors: number;
  memory: number;
  tools: number;
  thinking: number;
  notes: number;
};

type DashboardTab = "stream" | "memories" | "profile" | "settings";

type SettingsDraft = {
  timezone: string;
  language: string;
  country_code: string;
  profile_id: string;
  user_display_name: string;
  privacy_scope: string;
};

export function App() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<Status>({ label: "Ready", tone: "idle" });
  const [health, setHealth] = useState<string>("checking");
  const [lastTurn, setLastTurn] = useState<ChatTurn | null>(null);
  const [turnSteps, setTurnSteps] = useState<Record<string, AgentStep[]>>({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeTab, setActiveTab] = useState<DashboardTab>("stream");
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings | null>(null);
  const [settingsDraft, setSettingsDraft] = useState<SettingsDraft>({
    timezone: "Europe/Rome",
    language: "it",
    country_code: "IT",
    profile_id: "local-user",
    privacy_scope: "local_single_user",
    user_display_name: "Utente locale"
  });
  const [memoryScope, setMemoryScope] = useState<"all" | "user" | "project">("all");
  const [dashboardMemories, setDashboardMemories] = useState<DashboardMemories | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const toolUseSeenRef = useRef(false);

  useEffect(() => {
    fetchHealth()
      .then((result) => setHealth(`${result.status} - ${result.model}`))
      .catch(() => setHealth("offline"));
    void refreshSessions();
    void refreshDashboardData();
  }, []);

  const traceSummary = useMemo(() => {
    const response = traces.find((trace) => trace.kind === "llm.response");
    return {
      usage: lastTurn?.usage ?? response?.payload.usage
    };
  }, [lastTurn, traces]);
  const selectedSteps = useMemo(
    () => (selectedTurnId ? turnSteps[selectedTurnId] ?? [] : []),
    [selectedTurnId, turnSteps]
  );
  const selectedStepSummary = useMemo(
    () => summarizeSteps(selectedSteps),
    [selectedSteps]
  );

  async function ensureSession(): Promise<ChatSession> {
    if (session) {
      return session;
    }
    const created = await createSession(newSessionTitle());
    setSession(created);
    setMessages([]);
    setTraces([]);
    setTurnSteps({});
    setSelectedTurnId(null);
    setSessions((current) => mergeSessionList(created, current));
    return created;
  }

  async function startSession() {
    setStatus({ label: "Creating session", tone: "busy" });
    try {
      const created = await createSession(newSessionTitle());
      setSession(created);
      setMessages([]);
      setTraces([]);
      setTurnSteps({});
      setSelectedTurnId(null);
      setLastTurn(null);
      setSessions((current) => mergeSessionList(created, current));
      setStatus({ label: "Session ready", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function refreshSessions() {
    try {
      setSessions(await fetchSessions());
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function refreshDashboardData() {
    try {
      const [settingsResult, profileResult, memoriesResult] = await Promise.all([
        fetchRuntimeSettings(),
        fetchUserProfile(),
        fetchDashboardMemories({
          scope: memoryScope === "all" ? undefined : memoryScope,
          limit: 80
        })
      ]);
      setRuntimeSettings(settingsResult);
      setSettingsDraft({
        timezone: settingsResult.timezone,
        language: settingsResult.language,
        country_code: settingsResult.country_code,
        profile_id: settingsResult.profile_id,
        privacy_scope: settingsResult.privacy_scope,
        user_display_name: settingsResult.user_display_name
      });
      setUserProfile(profileResult);
      setDashboardMemories(memoriesResult);
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function refreshMemories(nextScope = memoryScope) {
    try {
      setDashboardMemories(
        await fetchDashboardMemories({
          scope: nextScope === "all" ? undefined : nextScope,
          limit: 80
        })
      );
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function handleMemoryScopeChange(nextScope: "all" | "user" | "project") {
    setMemoryScope(nextScope);
    await refreshMemories(nextScope);
  }

  async function handleSettingsSave() {
    setStatus({ label: "Saving settings", tone: "busy" });
    try {
      const saved = await updateRuntimeSettings(settingsDraft);
      setRuntimeSettings(saved);
      setSettingsDraft({
        timezone: saved.timezone,
        language: saved.language,
        country_code: saved.country_code,
        profile_id: saved.profile_id,
        privacy_scope: saved.privacy_scope,
        user_display_name: saved.user_display_name
      });
      setUserProfile(await fetchUserProfile());
      setStatus({ label: "Settings saved", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function refreshMessages() {
    if (!session) {
      await refreshSessions();
      return;
    }
    setStatus({ label: "Refreshing", tone: "busy" });
    try {
      await Promise.all([loadSession(session, { quiet: true }), refreshSessions()]);
      setStatus({ label: "Messages loaded", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function loadSession(
    target: ChatSession,
    options: { quiet?: boolean } = {}
  ) {
    if (!options.quiet) {
      setStatus({ label: "Loading session", tone: "busy" });
    }
    const loadedMessages = await fetchMessages(target.id);
    setSession(target);
    setMessages(loadedMessages);
    setLastTurn(null);
    setTurnSteps({});
    const lastTurnId = lastMessageTurnId(loadedMessages);
    setSelectedTurnId(lastTurnId);
    if (lastTurnId) {
      const [loadedTraces, loadedEvents] = await Promise.all([
        fetchTraces(lastTurnId),
        fetchEvents({ turnId: lastTurnId })
      ]);
      setTraces(loadedTraces);
      setTurnSteps({
        [lastTurnId]: stepsFromEvents(loadedEvents, loadedTraces)
      });
    } else {
      setTraces([]);
    }
    if (!options.quiet) {
      setStatus({ label: "Session loaded", tone: "ok" });
    }
  }

  async function handleSessionClick(target: ChatSession) {
    try {
      await loadSession(target);
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function loadTraces(turnId: string) {
    setSelectedTurnId(turnId);
    setStatus({ label: "Loading traces", tone: "busy" });
    try {
      const loaded = await fetchTraces(turnId);
      const loadedEvents = await fetchEvents({ turnId });
      setTraces(loaded);
      setTurnSteps((current) => ({
        ...current,
        [turnId]: stepsFromEvents(loadedEvents, loaded)
      }));
      setStatus({ label: "Trace loaded", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = prompt.trim();
    if (!message) {
      return;
    }
    setPrompt("");
    setStatus({ label: "Streaming", tone: "busy" });
    setIsStreaming(true);

    try {
      const activeSession = await ensureSession();
      await streamTurn(
        activeSession.id,
        message,
        undefined,
        handleStreamEvent
      );
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
      if (selectedTurnId) {
        upsertStep(selectedTurnId, {
          id: `error-${Date.now()}`,
          kind: "runtime",
          seq: Date.now(),
          title: "Stream error",
          body: errorMessage(error),
          status: "error"
        });
      }
    } finally {
      setIsStreaming(false);
    }
  }

  function handleStreamEvent(event: StreamEvent) {
    const turnId = currentTurnId(event);

    switch (event.type) {
      case "turn_started": {
        const userMessage = event.data.user_message as ChatMessage;
        const startedTurnId = String(event.data.turn_id);
        toolUseSeenRef.current = false;
        setSelectedTurnId(startedTurnId);
        setTraces([]);
        setTurnSteps((current) => ({ ...current, [startedTurnId]: [] }));
        setMessages((current) => [
          ...current,
          userMessage,
          {
            id: `stream-assistant-${startedTurnId}`,
            session_id: userMessage.session_id,
            turn_id: startedTurnId,
            role: "assistant",
            content: "",
            created_at: new Date().toISOString(),
            metadata: { streaming: true }
          }
        ]);
        upsertStep(startedTurnId, {
          id: "runtime-start",
          kind: "runtime",
          seq: eventSeq(event),
          title: "Turn started",
          body: startedTurnId,
          status: "done"
        });
        break;
      }

      case "runtime_event": {
        const eventRecord = recordValue(event.data.event);
        if (!eventRecord) {
          break;
        }
        const cognitiveEvent = eventRecord as CognitiveEvent;
        const step = stepFromEvent(cognitiveEvent, eventSeq(event));
        if (step) {
          upsertStep(cognitiveEvent.turn_id ?? turnId, step);
        }
        break;
      }

      case "model_request":
        upsertStep(turnId, {
          id: `model-${String(event.data.step ?? "1")}`,
          kind: "runtime",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.step),
          title: `MiniMax request #${String(event.data.step ?? "1")}`,
          body: `model: ${String(event.data.model ?? "MiniMax-M2.7")}`,
          status: "active"
        });
        break;

      case "memory_context":
        {
          const payload = {
            trace_id: event.data.trace_id,
            searched: event.data.searched,
            selected_count: event.data.selected_count,
            candidate_count: event.data.candidate_count,
            negative_evidence: event.data.negative_evidence,
            selected: event.data.selected,
            near_miss: event.data.near_miss,
            excluded: event.data.excluded,
            conflicts: event.data.conflicts
          };
        upsertStep(turnId, {
          id: `memory-context-${String(event.data.trace_id ?? "pending")}`,
          kind: "memory",
          seq: eventSeq(event),
          title: memoryContextTitle(payload),
          body: memoryContextSummary(payload),
          data: payload,
          status: "done"
        });
        }
        break;

      case "runtime_context":
        {
          const payload = {
            trace_id: event.data.trace_id,
            schema_version: event.data.schema_version,
            block_index: event.data.block_index,
            blocks: event.data.blocks
          };
          upsertStep(turnId, {
            id: `runtime-context-${String(event.data.trace_id ?? "pending")}`,
            kind: "runtime",
            seq: eventSeq(event),
            title: runtimeContextTitle(payload),
            body: runtimeContextSummary(payload),
            data: payload,
            status: "done"
          });
        }
        break;

      case "thinking_start":
        upsertStep(turnId, {
          id: `thinking-start-${String(event.data.model_step ?? "1")}-${String(
            event.data.index ?? "0"
          )}`,
          kind: "runtime",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: "Thinking block started",
          body: `content block ${String(event.data.index ?? "0")}`,
          status: "done"
        });
        break;

      case "thinking_delta":
        appendStepText(
          turnId,
          `thinking-live-${String(event.data.model_step ?? "1")}-${String(
            event.data.index ?? "0"
          )}`,
          {
            kind: "thinking",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            title: `Thinking - model step ${String(event.data.model_step ?? "1")}`,
            text: String(event.data.text ?? "")
          }
        );
        break;

      case "tool_use_start":
        toolUseSeenRef.current = true;
        upsertStep(turnId, {
          id: `tool-use-start-${String(event.data.provider_tool_use_id ?? Date.now())}`,
          kind: "tool",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: `Prepare tool call: ${String(event.data.tool_name ?? "tool")}`,
          body: `provider id: ${String(event.data.provider_tool_use_id ?? "pending")}`,
          status: "active"
        });
        break;

      case "tool_input_delta":
        appendStepText(
          turnId,
          `tool-input-live-${String(event.data.model_step ?? "1")}-${String(
            event.data.index ?? "0"
          )}`,
          {
            kind: "tool",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            title: "Tool arguments stream",
            text: String(event.data.partial_json ?? "")
          }
        );
        break;

      case "tool_call":
        toolUseSeenRef.current = true;
        upsertStep(turnId, {
          id: `tool-call-${String(event.data.provider_tool_use_id ?? Date.now())}`,
          kind: classifyToolStepKind(event.data.arguments),
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: toolCallTitle(event.data.arguments, event.data.tool_name),
          body: toolCallSummary(event.data.arguments),
          data: event.data,
          status: "done"
        });
        break;

      case "tool_result":
        upsertStep(turnId, {
          id: `tool-result-${String(event.data.tool_call_id ?? Date.now())}`,
          kind: classifyToolResultKind(event.data),
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: toolResultTitle(event.data),
          body: toolResultSummary(event.data),
          data: event.data,
          status: event.data.status === "error" ? "error" : "done"
        });
        break;

      case "text_start":
        upsertStep(turnId, {
          id: `text-start-${String(event.data.model_step ?? "1")}-${String(
            event.data.index ?? "0"
          )}`,
          kind: "runtime",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: "Final text block started",
          body: `content block ${String(event.data.index ?? "0")}`,
          status: "done"
        });
        break;

      case "text_delta": {
        const delta = String(event.data.text ?? "");
        const isProgressNote =
          !toolUseSeenRef.current && numericValue(event.data.model_step) === 1;
        if (!isProgressNote) {
          setMessages((current) =>
            current.map((message) =>
              message.id === `stream-assistant-${turnId}`
                ? { ...message, content: `${message.content}${delta}` }
                : message
            )
          );
        }
        appendStepText(
          turnId,
          `${isProgressNote ? "note" : "answer"}-live-${String(
            event.data.model_step ?? "1"
          )}-${String(
            event.data.index ?? "0"
          )}`,
          {
            kind: isProgressNote ? "note" : "answer",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            title: isProgressNote ? "Nota pubblica di lavoro" : "Risposta finale",
            text: delta
          }
        );
        break;
      }

      case "model_stop":
        upsertStep(turnId, {
          id: `model-stop-${String(event.data.seq ?? Date.now())}`,
          kind: "runtime",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: "Model step stopped",
          body: String(event.data.stop_reason ?? "unknown"),
          status: "done"
        });
        break;

      case "turn_complete": {
        const turn = event.data as unknown as ChatTurn;
        setSession(turn.session);
        setSessions((current) => mergeSessionList(turn.session, current));
        setLastTurn(turn);
        setMessages((current) => [
          ...current.filter(
            (message) =>
              !message.id.startsWith("stream-assistant-") &&
              message.id !== turn.user_message.id
          ),
          turn.user_message,
          turn.assistant_message
        ]);
        setSelectedTurnId(turn.turn_id);
        setStatus({ label: "Turn complete", tone: "ok" });
        upsertStep(turn.turn_id, {
          id: "runtime-complete",
          kind: "runtime",
          seq: eventSeq(event),
          title: "Turn persisted",
          body: `${turn.trace_ids.length} trace records`,
          status: "done"
        });
        settleSteps(turn.turn_id);
        void Promise.all([
          fetchTraces(turn.turn_id),
          fetchEvents({ turnId: turn.turn_id })
        ]).then(([loadedTraces, loadedEvents]) => {
          setTraces(loadedTraces);
          setTurnSteps((current) => ({
            ...current,
            [turn.turn_id]: stepsFromEvents(loadedEvents, loadedTraces)
          }));
        });
        void refreshSessions();
        void refreshDashboardData();
        break;
      }

      case "error":
        setStatus({ label: String(event.data.message ?? "Stream error"), tone: "error" });
        upsertStep(turnId, {
          id: `stream-error-${Date.now()}`,
          kind: "runtime",
          seq: eventSeq(event),
          title: String(event.data.code ?? "Stream error"),
          body: String(event.data.message ?? ""),
          status: "error"
        });
        break;

      default:
        upsertStep(turnId, {
          id: `event-${event.type}-${Date.now()}`,
          kind: "runtime",
          seq: eventSeq(event),
          title: event.type,
          body: formatJson(event.data),
          status: "done"
        });
    }
  }

  function upsertStep(turnId: string, next: AgentStep) {
    setTurnSteps((current) => {
      const steps = current[turnId] ?? [];
      const index = steps.findIndex((step) => step.id === next.id);
      if (index === -1) {
        return { ...current, [turnId]: sortSteps([...steps, next]) };
      }
      return {
        ...current,
        [turnId]: sortSteps(
          steps.map((step) => (step.id === next.id ? { ...step, ...next } : step))
        )
      };
    });
  }

  function appendStepText(
    turnId: string,
    id: string,
    next: {
      kind: AgentStep["kind"];
      seq: number;
      modelStep?: number;
      title: string;
      text: string;
    }
  ) {
    setTurnSteps((current) => {
      const steps = current[turnId] ?? [];
      const index = steps.findIndex((step) => step.id === id);
      if (index === -1) {
        return {
          ...current,
          [turnId]: sortSteps([
            ...steps,
            {
              id,
              kind: next.kind,
              seq: next.seq,
              modelStep: next.modelStep,
              title: next.title,
              body: next.text,
              status: "active"
            }
          ])
        };
      }
      return {
        ...current,
        [turnId]: sortSteps(
          steps.map((step) =>
            step.id === id ? { ...step, body: `${step.body}${next.text}` } : step
          )
        )
      };
    });
  }

  function settleSteps(turnId: string) {
    setTurnSteps((current) => ({
      ...current,
      [turnId]: (current[turnId] ?? []).map((step) =>
        step.status === "active" ? { ...step, status: "done" } : step
      )
    }));
  }

  function currentTurnId(event: StreamEvent): string {
    return String(event.data.turn_id ?? selectedTurnId ?? "pending-turn");
  }

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Sessioni e runtime">
        <div className="brand">
          <div className="brand-mark">
            <BrainCircuit size={18} aria-hidden="true" />
          </div>
          <div>
            <h1>Scarlet Mind</h1>
            <p>{health}</p>
          </div>
        </div>

        <div className="sidebar-card">
          <div className="section-row">
            <div>
              <div className="section-label">Sessione attiva</div>
              <div className="current-session">{sessionTitle(session)}</div>
            </div>
          </div>
          <div className="button-row">
            <button className="command primary" type="button" onClick={startSession}>
              <MessageSquarePlus size={16} aria-hidden="true" />
              <span>Nuova</span>
            </button>
            <button
              className="icon-command"
              type="button"
              onClick={refreshMessages}
              disabled={!session}
              title="Aggiorna messaggi"
            >
              <RefreshCcw size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="sidebar-card runtime-snapshot">
          <div className="section-label">Runtime</div>
          <div className="mini-readout">
            <span>
              <Clock3 size={14} aria-hidden="true" />
              {runtimeSettings?.timezone ?? "Europe/Rome"}
            </span>
            <span>
              <UserRound size={14} aria-hidden="true" />
              {runtimeSettings?.user_display_name ?? "Utente locale"}
            </span>
            <span>
              <ShieldCheck size={14} aria-hidden="true" />
              {runtimeSettings?.country_label ?? "Italia"}
            </span>
          </div>
          <small>
            Lingua {runtimeSettings?.language_label ?? "Italiano"} · Fonte:{" "}
            {runtimeSettings?.source === "dashboard_settings" ? "impostazioni" : "default"}
          </small>
        </div>

        <div className="session-history">
          <div className="session-history-header">
            <div className="section-label">Sessioni recenti</div>
            <span>{sessions.length}</span>
          </div>
          <div className="session-list" aria-label="Sessioni chat recenti">
            {sessions.length === 0 ? (
              <div className="session-empty">Nessuna sessione salvata</div>
            ) : (
              sessions.map((item) => (
                <button
                  className={`session-item ${item.id === session?.id ? "active" : ""}`}
                  key={item.id}
                  type="button"
                  onClick={() => void handleSessionClick(item)}
                  title={sessionTitle(item)}
                >
                  <span>{sessionTitle(item)}</span>
                  <small>{formatSessionTime(item.updated_at)}</small>
                </button>
              ))
            )}
          </div>
        </div>

        <div className={`status ${status.tone}`}>{status.label}</div>
      </aside>

      <section className="chat-pane" aria-label="Chat">
        <div className="pane-header">
          <div>
            <div className="section-label">Conversazione</div>
            <h2>{sessionTitle(session)}</h2>
          </div>
          <div className="header-actions">
            {lastTurn ? (
              <div className="turn-chip">
                <Clock3 size={15} aria-hidden="true" />
                <span>{lastTurn.latency_ms} ms</span>
              </div>
            ) : null}
            <button
              className="icon-command"
              type="button"
              onClick={() => setActiveTab("stream")}
              title="Apri stream agente"
            >
              <PanelRight size={16} aria-hidden="true" />
            </button>
          </div>
        </div>

        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">
              <BrainCircuit size={22} aria-hidden="true" />
              <span>Apri una sessione o scrivi a Scarlet.</span>
            </div>
          ) : (
            messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <div className="message-icon">
                  {message.role === "user" ? (
                    <UserRound size={16} aria-hidden="true" />
                  ) : (
                    <Bot size={16} aria-hidden="true" />
                  )}
                </div>
                <div className="message-body">
                  <div className="message-meta">
                    <span>{message.role === "user" ? "Tu" : "Scarlet"}</span>
                    {message.turn_id ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => loadTraces(message.turn_id!)}
                      >
                        evidenze
                      </button>
                    ) : null}
                  </div>
                  {message.role === "assistant" && message.turn_id ? (
                    <AgentTimeline steps={turnSteps[message.turn_id] ?? []} />
                  ) : null}
                  <p>{message.content || (message.role === "assistant" ? "..." : "")}</p>
                </div>
              </article>
            ))
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Scrivi a Scarlet"
            rows={3}
          />
          <button className="send-button" type="submit" disabled={!prompt.trim() || isStreaming}>
            <Send size={18} aria-hidden="true" />
            <span>{isStreaming ? "Live" : "Invia"}</span>
          </button>
        </form>
      </section>

      <aside className="trace-pane" aria-label="Dashboard Scarlet">
        <div className="pane-header compact">
          <div>
            <div className="section-label">Dashboard</div>
            <h2>{dashboardTitle(activeTab, selectedTurnId)}</h2>
          </div>
          <div className="dashboard-tabs" role="tablist" aria-label="Pannelli dashboard">
            <TabButton
              active={activeTab === "stream"}
              icon={<Activity size={15} aria-hidden="true" />}
              label="Stream"
              onClick={() => setActiveTab("stream")}
            />
            <TabButton
              active={activeTab === "memories"}
              icon={<Archive size={15} aria-hidden="true" />}
              label="Memorie"
              onClick={() => setActiveTab("memories")}
            />
            <TabButton
              active={activeTab === "profile"}
              icon={<UserCog size={15} aria-hidden="true" />}
              label="Profilo"
              onClick={() => setActiveTab("profile")}
            />
            <TabButton
              active={activeTab === "settings"}
              icon={<Settings size={15} aria-hidden="true" />}
              label="Impost."
              onClick={() => setActiveTab("settings")}
            />
          </div>
        </div>

        <DashboardPanel
          activeTab={activeTab}
          dashboardMemories={dashboardMemories}
          memoryScope={memoryScope}
          onMemoryScopeChange={(scope) => void handleMemoryScopeChange(scope)}
          onRefreshDashboard={() => void refreshDashboardData()}
          runtimeSettings={runtimeSettings}
          selectedStepSummary={selectedStepSummary}
          selectedSteps={selectedSteps}
          settingsDraft={settingsDraft}
          setSettingsDraft={setSettingsDraft}
          traceSummary={traceSummary}
          traces={traces}
          userProfile={userProfile}
          onSettingsSave={() => void handleSettingsSave()}
        />
      </aside>
    </main>
  );
}

function TabButton({
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
    <button
      className={`tab-button ${active ? "active" : ""}`}
      type="button"
      onClick={onClick}
      title={label}
      aria-pressed={active}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function DashboardPanel({
  activeTab,
  dashboardMemories,
  memoryScope,
  onMemoryScopeChange,
  onRefreshDashboard,
  runtimeSettings,
  selectedStepSummary,
  selectedSteps,
  settingsDraft,
  setSettingsDraft,
  traceSummary,
  traces,
  userProfile,
  onSettingsSave
}: {
  activeTab: DashboardTab;
  dashboardMemories: DashboardMemories | null;
  memoryScope: "all" | "user" | "project";
  onMemoryScopeChange: (scope: "all" | "user" | "project") => void;
  onRefreshDashboard: () => void;
  runtimeSettings: RuntimeSettings | null;
  selectedStepSummary: StepSummary;
  selectedSteps: AgentStep[];
  settingsDraft: SettingsDraft;
  setSettingsDraft: Dispatch<SetStateAction<SettingsDraft>>;
  traceSummary: { usage: unknown };
  traces: TraceItem[];
  userProfile: UserProfile | null;
  onSettingsSave: () => void;
}) {
  if (activeTab === "memories") {
    return (
      <div className="dashboard-panel">
        <div className="panel-toolbar">
          <div>
            <div className="section-label">Memoria semantica</div>
            <h3>{dashboardMemories?.total ?? 0} memorie attive</h3>
          </div>
          <button className="icon-command" type="button" onClick={onRefreshDashboard} title="Aggiorna">
            <RefreshCcw size={16} aria-hidden="true" />
          </button>
        </div>
        <div className="segmented-control">
          {(["all", "user", "project"] as const).map((scope) => (
            <button
              className={memoryScope === scope ? "active" : ""}
              key={scope}
              type="button"
              onClick={() => onMemoryScopeChange(scope)}
            >
              {scope === "all" ? "Tutte" : scope === "user" ? "Utente" : "Progetto"}
            </button>
          ))}
        </div>
        <div className="dashboard-scroll">
          {dashboardMemories?.memories.length ? (
            dashboardMemories.memories.map((memory) => (
              <DashboardMemoryCard memory={memory} key={memory.id} />
            ))
          ) : (
            <div className="empty-state">Nessuna memoria da mostrare.</div>
          )}
        </div>
      </div>
    );
  }

  if (activeTab === "profile") {
    return (
      <div className="dashboard-panel">
        <div className="profile-hero">
          <div className="profile-avatar">
            <UserCog size={22} aria-hidden="true" />
          </div>
          <div>
            <div className="section-label">Profilo utente</div>
            <h3>{userProfile?.display_name ?? "Utente locale"}</h3>
            <p>
              {userProfile?.memory_count ?? 0} memorie personali disponibili per
              personalizzazione e continuita.
            </p>
          </div>
        </div>
        <div className="metrics event-metrics">
          <Metric label="Profilo" value={userProfile?.profile_id ?? "local-user"} />
          <Metric label="Lingua" value={userProfile?.language_label ?? "Italiano"} />
          <Metric label="Paese" value={userProfile?.country_label ?? "Italia"} />
          <Metric label="Fuso" value={userProfile?.timezone ?? "Europe/Rome"} />
          <Metric label="Privacy" value={userProfile?.privacy_scope ?? "local_single_user"} />
          <Metric label="Fonte" value={userProfile?.source ?? "default"} />
        </div>
        <div className="dashboard-scroll">
          {userProfile?.top_memories.length ? (
            userProfile.top_memories.map((memory) => (
              <DashboardMemoryCard memory={memory} key={memory.id} />
            ))
          ) : (
            <div className="empty-state">Il profilo non ha ancora memorie personali.</div>
          )}
        </div>
      </div>
    );
  }

  if (activeTab === "settings") {
    return (
      <div className="dashboard-panel">
        <div className="panel-toolbar">
          <div>
            <div className="section-label">Impostazioni Scarlet</div>
            <h3>Runtime configurabile</h3>
          </div>
          <SlidersHorizontal size={18} aria-hidden="true" />
        </div>
        <div className="settings-scroll">
          <div className="settings-grid">
            <label>
              <span>Nome utente</span>
              <input
                value={settingsDraft.user_display_name}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    user_display_name: event.target.value
                  }))
                }
              />
            </label>
            <label>
              <span>ID profilo operativo</span>
              <input
                value={settingsDraft.profile_id}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    profile_id: event.target.value
                  }))
                }
              />
            </label>
            <label>
              <span>Lingua piattaforma</span>
              <select
                value={settingsDraft.language}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    language: event.target.value
                  }))
                }
              >
                {(runtimeSettings?.options.languages ?? [{ code: "it", label: "Italiano" }]).map(
                  (language) => (
                    <option key={language.code} value={language.code}>
                      {language.label}
                    </option>
                  )
                )}
              </select>
            </label>
            <label>
              <span>Paese / locale operativo</span>
              <select
                value={settingsDraft.country_code}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    country_code: event.target.value
                  }))
                }
              >
                {(runtimeSettings?.options.countries ?? [{ code: "IT", label: "Italia" }]).map(
                  (country) => (
                    <option key={country.code} value={country.code}>
                      {country.label}
                    </option>
                  )
                )}
              </select>
            </label>
            <label>
              <span>Fuso orario operativo</span>
              <select
                value={settingsDraft.timezone}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    timezone: event.target.value
                  }))
                }
              >
                {(runtimeSettings?.options.timezones ?? [
                  { id: "Europe/Rome", label: "Italia - Europe/Rome" }
                ]).map((timezone) => (
                  <option key={timezone.id} value={timezone.id}>
                    {timezone.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Ambito privacy memoria</span>
              <select
                value={settingsDraft.privacy_scope}
                onChange={(event) =>
                  setSettingsDraft((current) => ({
                    ...current,
                    privacy_scope: event.target.value
                  }))
                }
              >
                {(runtimeSettings?.options.privacy_scopes ?? [
                  { id: "local_single_user", label: "Profilo locale singolo" }
                ]).map((scope) => (
                  <option key={scope.id} value={scope.id}>
                    {scope.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="soft-note">
            Questi valori entrano nel runtime context del prossimo turno. Scarlet li
            tratta come profilo attivo, confine privacy, locale operativo, fonte per
            ora reale e lingua predefinita.
          </div>
          <button className="command primary wide" type="button" onClick={onSettingsSave}>
            <Settings size={16} aria-hidden="true" />
            <span>Salva impostazioni</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-panel">
      <div className="metrics event-metrics">
        <Metric label="Eventi" value={String(selectedStepSummary.total)} />
        <Metric label="Tool" value={String(selectedStepSummary.tools)} />
        <Metric label="Memoria" value={String(selectedStepSummary.memory)} />
        <Metric label="Attivi" value={String(selectedStepSummary.active)} />
        <Metric label="Input" value={metricValue(traceSummary.usage, "input_tokens")} />
        <Metric label="Output" value={metricValue(traceSummary.usage, "output_tokens")} />
      </div>

      <div className="agent-stream-pane">
        {selectedSteps.length === 0 ? (
          <div className="empty-state">Nessun evento live.</div>
        ) : (
          <AgentTimeline steps={selectedSteps} variant="panel" />
        )}
        <details className="trace-drawer">
          <summary>
            <span>Trace grezze</span>
            <strong>{traces.length}</strong>
          </summary>
          <div className="trace-list">
            {traces.length === 0 ? (
              <div className="empty-state">Nessuna trace.</div>
            ) : (
              traces.map((trace) => (
                <section className="trace-item" key={trace.id}>
                  <div className="trace-title">
                    <span>{trace.kind}</span>
                    <Braces size={15} aria-hidden="true" />
                  </div>
                  <pre>{JSON.stringify(trace.payload, null, 2)}</pre>
                </section>
              ))
            )}
          </div>
        </details>
      </div>
    </div>
  );
}

function DashboardMemoryCard({ memory }: { memory: DashboardMemory }) {
  return (
    <article className="dashboard-memory-card">
      <div className="memory-card-header">
        <strong>{memory.type}</strong>
        <span>{memory.scope}</span>
      </div>
      <p>{truncate(memory.content, 360)}</p>
      <div className="evidence-grid">
        <EvidenceMetric label="Confidenza" value={percentValue(memory.confidence)} />
        <EvidenceMetric label="Salienza" value={percentValue(memory.salience)} />
        <EvidenceMetric label="Uso" value={String(memory.usage_count)} />
        <EvidenceMetric label="Aggiornata" value={formatSessionTime(memory.updated_at)} />
      </div>
      {memory.tags.length > 0 ? (
        <div className="tag-row">
          {memory.tags.slice(0, 6).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}
      <div className="evidence-meta">
        <code>{memory.id}</code>
        {memory.source_session_id ? <code>sessione {memory.source_session_id}</code> : null}
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AgentTimeline({
  steps,
  variant = "embedded"
}: {
  steps: AgentStep[];
  variant?: "embedded" | "panel";
}) {
  if (steps.length === 0) {
    return null;
  }

  const ordered = sortSteps(steps);
  const summary = summarizeSteps(ordered);
  return (
    <section className={`agent-turn ${variant}`} aria-label="Agent turn operations">
      <div className="agent-turn-header">
        <div>
          <div className="section-label">{variant === "panel" ? "Live turn" : "Agent turn"}</div>
          <h3>{variant === "panel" ? "Cognitive event stream" : "Ordered operations"}</h3>
        </div>
        <span>{ordered.length} events</span>
      </div>
      {variant === "panel" ? (
        <div className="agent-kind-strip">
          <StepStat label="Thinking" value={summary.thinking} />
          <StepStat label="Memorie" value={summary.memory} />
          <StepStat label="Tool" value={summary.tools} />
          <StepStat label="Note" value={summary.notes} />
          <StepStat label="Errori" value={summary.errors} />
        </div>
      ) : null}
      <ol className="operation-list">
        {ordered.map((step, index) => (
          <li className={`operation-step ${step.kind} ${step.status}`} key={step.id}>
            <div className="operation-index">{index + 1}</div>
            <div className="operation-icon">{stepIcon(step.kind)}</div>
            <div className="operation-body">
              <div className="operation-title">
                <div className="operation-heading">
                  <small>{stepKindLabel(step.kind)}</small>
                  <strong>{step.title}</strong>
                </div>
                <div className="operation-badges">
                  {step.modelStep ? <small>model {step.modelStep}</small> : null}
                  {step.data?.event_type ? <small>{stringValue(step.data.event_type)}</small> : null}
                  <small>{step.status}</small>
                </div>
              </div>
              <AgentStepContent step={step} />
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function StepStat({ label, value }: { label: string; value: number }) {
  return (
    <span className={value > 0 ? "has-value" : ""}>
      <strong>{value}</strong>
      <small>{label}</small>
    </span>
  );
}

function AgentStepContent({ step }: { step: AgentStep }) {
  if (step.kind === "runtime" && recordArray(step.data?.blocks).length > 0) {
    return <RuntimeContextBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "memory") {
    return <MemoryContextBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "thinking") {
    return <ThinkingBlock text={step.body} />;
  }
  if (step.kind === "note") {
    return <PublicNoteBlock text={step.body} />;
  }
  if (step.kind === "tool") {
    return <ToolCallBlock data={step.data} fallback={step.body} />;
  }
  if (
    step.kind === "result" ||
    step.kind === "schema" ||
    step.kind === "session" ||
    step.kind === "metacognition"
  ) {
    return <ToolResultBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "answer") {
    return <AnswerBlock text={step.body} />;
  }
  return <RuntimeEventBlock step={step} />;
}

function RuntimeContextBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  const blocks = recordArray(data?.blocks);
  if (blocks.length === 0) {
    return <RuntimeEventBlock step={{ id: "runtime-context", kind: "runtime", seq: 0, title: "Runtime context", body: fallback, data, status: "done" }} />;
  }

  return (
    <div className="structured-block runtime-context-block">
      <div className="summary-row">
        {stringValue(data?.schema_version) ? (
          <span>{stringValue(data?.schema_version)}</span>
        ) : null}
        <span>{blocks.length} blocchi cognitivi</span>
        {stringValue(data?.generated_at) ? (
          <span>{formatSessionTime(stringValue(data?.generated_at))}</span>
        ) : null}
      </div>
      <div className="context-block-list">
        {blocks.map((block) => (
          <RuntimeContextCard
            block={block}
            key={stringValue(block.id) || stringValue(block.type) || JSON.stringify(block)}
          />
        ))}
      </div>
      <JsonDetails label="Runtime context JSON" value={data} />
    </div>
  );
}

function RuntimeContextCard({ block }: { block: Record<string, unknown> }) {
  const type = stringValue(block.type);
  const content = recordValue(block.content) ?? {};
  return (
    <article className={`context-card ${type || "generic"}`}>
      <div className="context-card-header">
        <div>
          <small>{runtimeBlockLabel(type)}</small>
          <strong>{stringValue(block.id) || type || "runtime block"}</strong>
        </div>
        <div className="context-chip-row">
          {stringValue(block.scope) ? <span>{stringValue(block.scope)}</span> : null}
          {stringValue(block.lifetime) ? <span>{stringValue(block.lifetime)}</span> : null}
          {stringValue(block.source) ? <span>{stringValue(block.source)}</span> : null}
        </div>
      </div>
      <RuntimeBlockContent type={type} content={content} />
    </article>
  );
}

function RuntimeBlockContent({
  type,
  content
}: {
  type: string;
  content: Record<string, unknown>;
}) {
  if (type === "session_context") {
    return <SessionContextReadout content={content} />;
  }
  if (type === "message_context") {
    return <MessageContextReadout content={content} />;
  }
  if (type === "scarlet_state") {
    return <ScarletStateReadout content={content} />;
  }
  return <JsonDetails label="Dati blocco" value={content} />;
}

function SessionContextReadout({ content }: { content: Record<string, unknown> }) {
  const currentSession = recordValue(content.current_session);
  const previousSessions = recordArray(content.previous_sessions);
  const previousMemories = recordArray(content.previous_session_memories);
  return (
    <div className="context-readout">
      {currentSession ? (
        <div className="fact-panel">
          <small>Sessione corrente</small>
          <strong>{stringValue(currentSession.title) || stringValue(currentSession.id)}</strong>
          <span>{formatSessionTime(stringValue(currentSession.created_at))}</span>
        </div>
      ) : null}
      {previousSessions.length > 0 ? (
        <div className="context-section">
          <strong>Sessioni precedenti</strong>
          <div className="session-card-list compact">
            {previousSessions.map((item) => (
              <SessionSummaryCard session={item} key={stringValue(item.id) || JSON.stringify(item)} />
            ))}
          </div>
        </div>
      ) : (
        <div className="soft-note">Nessuna sessione precedente agganciata al contesto.</div>
      )}
      {previousMemories.length > 0 ? (
        <div className="context-section">
          <strong>Memorie dalla sessione precedente</strong>
          <div className="memory-card-list compact">
            {previousMemories.map((memory) => (
              <MemoryCard memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MessageContextReadout({ content }: { content: Record<string, unknown> }) {
  const currentMessage = recordValue(content.current_message);
  const world = recordValue(content.world);
  const location = recordValue(world?.location);
  const userProfile = recordValue(content.user_profile);
  const identity = recordValue(userProfile?.identity);
  const privacy = recordValue(userProfile?.privacy);
  const locale = recordValue(userProfile?.locale);
  const userMemories = recordArray(userProfile?.memories);
  const retrieval = recordValue(content.memory_retrieval);
  const selected = recordArray(retrieval?.selected);
  const nearMiss = recordArray(retrieval?.near_miss);
  const apiMind = recordValue(content.api_mind);
  const schema = recordValue(apiMind?.schema);
  const capabilities = recordValue(apiMind?.capabilities);

  return (
    <div className="context-readout">
      {currentMessage ? (
        <div className="fact-panel">
          <small>Messaggio corrente</small>
          <strong>
            {stringValue(recordValue(currentMessage.language)?.label) ||
              stringValue(recordValue(currentMessage.language)?.code) ||
              "lingua piattaforma"}
          </strong>
          <span>{truncate(stringValue(currentMessage.content), 180)}</span>
        </div>
      ) : null}
      {world ? (
        <div className="context-section">
          <strong>Mondo esterno verificato</strong>
          <div className="evidence-grid">
            <EvidenceMetric label="Ora" value={stringValue(world.now)} />
            <EvidenceMetric label="Fuso" value={stringValue(world.timezone)} />
            <EvidenceMetric label="Offset" value={stringValue(world.utc_offset)} />
            <EvidenceMetric
              label="Locale"
              value={
                stringValue(location?.country) ||
                stringValue(locale?.country) ||
                stringValue(location?.status)
              }
            />
          </div>
        </div>
      ) : null}
      {userProfile ? (
        <div className="context-section">
          <strong>Profilo utente operativo</strong>
          <div className="evidence-grid">
            <EvidenceMetric label="Profilo" value={stringValue(identity?.profile_id)} />
            <EvidenceMetric label="Nome" value={stringValue(identity?.display_name)} />
            <EvidenceMetric label="Privacy" value={stringValue(privacy?.scope)} />
            <EvidenceMetric label="Lingua" value={stringValue(recordValue(locale?.language)?.label)} />
          </div>
          {userMemories.length > 0 ? (
            <div className="compact-memory-list">
              {userMemories.slice(0, 5).map((memory) => (
                <CompactMemory memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {retrieval ? (
        <div className="context-section">
          <strong>Retrieval automatico del turno</strong>
          <div className="summary-row">
            <span>{selected.length} selezionate</span>
            <span>{nearMiss.length} near miss</span>
            {stringValue(retrieval.negative_evidence) ? (
              <span>{stringValue(retrieval.negative_evidence)}</span>
            ) : null}
          </div>
          {selected.length > 0 ? (
            <div className="memory-card-list compact">
              {selected.map((memory) => (
                <MemoryCard memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
              ))}
            </div>
          ) : null}
          {selected.length === 0 && nearMiss.length > 0 ? (
            <NearMissList memories={nearMiss.slice(0, 5)} />
          ) : null}
        </div>
      ) : null}
      {schema || capabilities ? (
        <div className="context-section">
          <strong>API Mind visibile al modello</strong>
          <div className="evidence-grid">
            <EvidenceMetric label="Schema" value={stringValue(schema?.schema_version)} />
            <EvidenceMetric label="Digest" value={stringValue(schema?.schema_digest)} />
            <EvidenceMetric
              label="Implementate"
              value={String(countCapabilityStatus(capabilities, "implemented"))}
            />
            <EvidenceMetric
              label="Pianificate"
              value={String(countCapabilityStatus(capabilities, "planned"))}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ScarletStateReadout({ content }: { content: Record<string, unknown> }) {
  const loops = arrayOfStrings(content.open_loops);
  return (
    <div className="context-readout">
      <div className="state-grid">
        <EvidenceMetric label="Focus" value={stringValue(content.focus)} />
        <EvidenceMetric label="Goal" value={stringValue(content.active_goal)} />
        <EvidenceMetric label="Postura" value={stringValue(content.confidence_posture)} />
        <EvidenceMetric label="Modalità" value={stringValue(content.interaction_mode)} />
        <EvidenceMetric label="Mood operativo" value={stringValue(content.mood_expression)} />
        <EvidenceMetric label="Aggiornato" value={stringValue(content.updated_at)} />
      </div>
      {loops.length > 0 ? (
        <div className="compact-list">
          <strong>Loop aperti</strong>
          {loops.map((loop) => (
            <p key={loop}>
              <span>todo</span>
              {loop}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function SessionSummaryCard({ session }: { session: Record<string, unknown> }) {
  const summary = recordValue(session.summary);
  const memoryIds = arrayOfStrings(session.memory_ids);
  return (
    <article className="session-card">
      <div className="session-card-header">
        <strong>{stringValue(session.title) || stringValue(session.id)}</strong>
        {stringValue(session.relation) ? <span>{stringValue(session.relation)}</span> : null}
      </div>
      <p>{truncate(stringValue(summary?.summary), 300)}</p>
      <div className="summary-row">
        {stringValue(summary?.message_count) ? (
          <span>{stringValue(summary?.message_count)} messaggi</span>
        ) : null}
        {memoryIds.length > 0 ? <span>{memoryIds.length} memorie</span> : null}
        {stringValue(session.created_at) ? <span>{formatSessionTime(stringValue(session.created_at))}</span> : null}
      </div>
      <div className="evidence-meta">
        {stringValue(session.id) ? <code>{stringValue(session.id)}</code> : null}
      </div>
    </article>
  );
}

function CompactMemory({ memory }: { memory: Record<string, unknown> }) {
  return (
    <article className="compact-memory">
      <strong>{truncate(stringValue(memory.content), 170)}</strong>
      <div className="summary-row">
        {stringValue(memory.type) ? <span>{stringValue(memory.type)}</span> : null}
        {stringValue(memory.scope) ? <span>{stringValue(memory.scope)}</span> : null}
        {percentValue(memory.confidence) ? <span>{percentValue(memory.confidence)}</span> : null}
      </div>
    </article>
  );
}

function NearMissList({ memories }: { memories: Record<string, unknown>[] }) {
  return (
    <div className="near-miss-list">
      {memories.map((memory) => (
        <div className="near-miss-item" key={stringValue(memory.id) || JSON.stringify(memory)}>
          <strong>{stringValue(memory.type) || "memory"}</strong>
          <span>{numberLabel(memory.score)}</span>
          <p>{truncate(stringValue(memory.why_relevant) || stringValue(memory.content), 160)}</p>
        </div>
      ))}
    </div>
  );
}

function MemoryContextBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  if (!data) {
    return <pre>{fallback || "..."}</pre>;
  }
  const selected = recordArray(data.selected);
  const nearMiss = recordArray(data.near_miss);
  const conflicts = recordArray(data.conflicts);
  const negativeEvidence = stringValue(data.negative_evidence);

  return (
    <div className="structured-block memory-block">
      <div className="summary-row">
        <span>{selected.length} selezionate</span>
        <span>{nearMiss.length} near miss</span>
        <span>{conflicts.length} conflitti</span>
      </div>
      {selected.length > 0 ? (
        <div className="memory-card-list">
          {selected.map((memory) => (
            <MemoryCard memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
          ))}
        </div>
      ) : (
        <div className="soft-note">
          {negativeEvidence === "no_relevant_memory_selected"
            ? "Nessuna memoria persistente selezionata per questo turno."
            : "Nessuna memoria selezionata."}
        </div>
      )}
      {conflicts.length > 0 ? (
        <div className="warning-note">
          Sono presenti conflitti di memoria: vanno risolti o nominati prima di
          usarli come evidenza.
        </div>
      ) : null}
    </div>
  );
}

function MemoryCard({ memory }: { memory: Record<string, unknown> }) {
  const tags = arrayOfStrings(memory.tags).slice(0, 5);
  const facts = recordArray(memory.facts);
  return (
    <article className="memory-card">
      <div className="memory-card-header">
        <strong>{stringValue(memory.type) || "memory"}</strong>
        <span>{stringValue(memory.status) || "unknown"}</span>
      </div>
      <p>{truncate(stringValue(memory.content), 360)}</p>
      <div className="evidence-grid">
        <EvidenceMetric label="Confidence" value={percentValue(memory.confidence)} />
        <EvidenceMetric label="Salience" value={percentValue(memory.salience)} />
        <EvidenceMetric label="Score" value={numberLabel(memory.score)} />
        <EvidenceMetric label="Facts" value={String(facts.length)} />
      </div>
      <div className="evidence-meta">
        {stringValue(memory.id) ? <code>{stringValue(memory.id)}</code> : null}
        {stringValue(memory.source_session_id) ? (
          <code>source {stringValue(memory.source_session_id)}</code>
        ) : null}
      </div>
      {tags.length > 0 ? (
        <div className="tag-row">
          {tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function PublicNoteBlock({ text }: { text: string }) {
  return <div className="public-note">{text.trim() || "..."}</div>;
}

function ThinkingBlock({ text }: { text: string }) {
  return (
    <details className="thinking-block">
      <summary>
        <span>Reasoning stream</span>
        <strong>{text.length} chars</strong>
      </summary>
      <pre>{text.trim() || "..."}</pre>
    </details>
  );
}

function AnswerBlock({ text }: { text: string }) {
  return <div className="answer-block">{text.trim() || "..."}</div>;
}

function RuntimeEventBlock({ step }: { step: AgentStep }) {
  const data = step.data ?? {};
  const payload = { ...data };
  delete payload.event_type;
  delete payload.event_seq;
  delete payload.source;
  delete payload.actor;
  delete payload.visibility;

  return (
    <div className="structured-block runtime-block">
      <div className="event-meta-grid">
        {stringValue(step.data?.event_seq) ? (
          <EvidenceMetric label="Seq" value={stringValue(step.data?.event_seq)} />
        ) : null}
        {stringValue(step.data?.source) ? (
          <EvidenceMetric label="Source" value={stringValue(step.data?.source)} />
        ) : null}
        {stringValue(step.data?.actor) ? (
          <EvidenceMetric label="Actor" value={stringValue(step.data?.actor)} />
        ) : null}
        {stringValue(step.data?.visibility) ? (
          <EvidenceMetric label="Visibilità" value={stringValue(step.data?.visibility)} />
        ) : null}
      </div>
      {step.body ? <p>{step.body}</p> : null}
      {Object.keys(payload).length > 0 ? (
        <details>
          <summary>Dettagli evento</summary>
          <pre>{formatJson(payload)}</pre>
        </details>
      ) : null}
    </div>
  );
}

function ToolCallBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  const source = recordValue(data?.arguments) ?? data;
  if (!source) {
    return <pre>{fallback || "..."}</pre>;
  }
  const method = stringValue(source.method);
  const path = stringValue(source.path);
  const intent = stringValue(source.intent);
  const body = recordValue(source.body);
  return (
    <div className="structured-block tool-block">
      <div className="tool-route">
        <span>{method || "CALL"}</span>
        <code>{path || "unknown path"}</code>
      </div>
      {intent ? <p>{intent}</p> : null}
      {body && Object.keys(body).length > 0 ? (
        <JsonDetails label="Parametri tecnici" value={body} />
      ) : null}
    </div>
  );
}

function ToolResultBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  const resultEnvelope = recordValue(data?.result) ?? data;
  if (!resultEnvelope) {
    return <pre>{fallback || "..."}</pre>;
  }
  const ok = resultEnvelope.ok;
  const result = recordValue(resultEnvelope.result);
  const error = recordValue(resultEnvelope.error);
  const confidence = percentValue(resultEnvelope.confidence);
  const latency = stringValue(data?.latency_ms);
  const nextActions = arrayOfStrings(resultEnvelope.suggested_next_actions);

  return (
    <div className="structured-block result-block">
      <div className="summary-row">
        <span className={ok === false ? "bad" : "good"}>
          {ok === false ? "Errore" : "OK"}
        </span>
        {confidence ? <span>Confidenza {confidence}</span> : null}
        {latency ? <span>{latency} ms</span> : null}
        {stringValue(result?.operation) ? <span>{stringValue(result?.operation)}</span> : null}
      </div>
      <ResultSummary result={result} error={error} fallback={fallback} />
      {stringValue(resultEnvelope.cognitive_hint) ? (
        <div className="soft-note">{stringValue(resultEnvelope.cognitive_hint)}</div>
      ) : null}
      {nextActions.length > 0 ? (
        <div className="compact-list action-list">
          <strong>Azioni suggerite</strong>
          {nextActions.slice(0, 4).map((action) => (
            <p key={action}>
              <span>next</span>
              {action}
            </p>
          ))}
        </div>
      ) : null}
      {recordValue(resultEnvelope.usage_guide) ? (
        <JsonDetails label="Guida tecnica dell'endpoint" value={resultEnvelope.usage_guide} />
      ) : null}
    </div>
  );
}

function ResultSummary({
  result,
  error,
  fallback
}: {
  result?: Record<string, unknown>;
  error?: Record<string, unknown>;
  fallback: string;
}) {
  if (error) {
    return (
      <div className="warning-note">
        <strong>{stringValue(error.code) || "Errore"}</strong>
        <p>{stringValue(error.message) || fallback}</p>
      </div>
    );
  }
  if (!result) {
    return <pre>{fallback || "..."}</pre>;
  }

  if (recordValue(result.memory)) {
    return (
      <div className="memory-card-list">
        <MemoryCard memory={recordValue(result.memory)!} />
      </div>
    );
  }

  if (recordValue(result.existing_memory)) {
    return (
      <div className="memory-card-list">
        <MemoryCard memory={recordValue(result.existing_memory)!} />
      </div>
    );
  }

  if (Array.isArray(result.facts)) {
    return <FactList facts={recordArray(result.facts)} />;
  }

  if (Array.isArray(result.routes)) {
    const routes = recordArray(result.routes);
    return (
      <div className="route-summary">
        {["implemented", "planned", "unavailable"].map((status) => {
          const matching = routes.filter((route) => stringValue(route.status) === status);
          return (
            <div className="route-group" key={status}>
              <strong>{routeStatusLabel(status, matching.length)}</strong>
              <ul>
                {matching.map((route) => (
                  <li key={`${stringValue(route.method)}-${stringValue(route.path)}`}>
                    <code>
                      {stringValue(route.method)} {stringValue(route.path)}
                    </code>
                    <span>{stringValue(route.purpose)}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    );
  }

  if (Array.isArray(result.memories)) {
    const memories = recordArray(result.memories);
    return (
      <div className="memory-card-list">
        {memories.map((memory) => (
          <MemoryCard memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
        ))}
      </div>
    );
  }

  if (Array.isArray(result.sessions)) {
    return (
      <div className="session-card-list">
        {recordArray(result.sessions).map((session) => (
          <article className="session-card" key={stringValue(session.id) || JSON.stringify(session)}>
            <strong>{stringValue(session.title) || stringValue(session.id)}</strong>
            <p>{truncate(stringValue(session.summary), 280)}</p>
            <div className="evidence-meta">
              {stringValue(session.id) ? <code>{stringValue(session.id)}</code> : null}
              {stringValue(session.updated_at) ? <span>{stringValue(session.updated_at)}</span> : null}
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (recordValue(result.session)) {
    const session = recordValue(result.session);
    const summary = recordValue(result.summary);
    const messages = recordArray(result.messages);
    const memories = recordArray(result.memories_written);
    return (
      <div className="session-readout">
        <strong>{stringValue(session?.title) || stringValue(session?.id)}</strong>
        <p>{truncate(stringValue(summary?.summary), 360)}</p>
        <div className="summary-row">
          <span>{messages.length} messaggi</span>
          <span>{memories.length} memorie scritte</span>
          {stringValue(session?.id) ? <span>{stringValue(session?.id)}</span> : null}
        </div>
      </div>
    );
  }

  if (recordValue(result.review)) {
    const review = recordValue(result.review);
    return (
      <div className="metacognition-readout">
        <p>{stringValue(review?.review_summary) || stringValue(review?.public_summary)}</p>
        <ClaimList items={recordArray(review?.claim_checks)} />
        <RiskList items={recordArray(review?.risks)} />
      </div>
    );
  }

  return <pre>{fallback || formatJson(result)}</pre>;
}

function FactList({ facts }: { facts: Record<string, unknown>[] }) {
  if (facts.length === 0) {
    return <div className="soft-note">Nessun fatto canonico disponibile.</div>;
  }
  return (
    <div className="fact-list">
      {facts.slice(0, 8).map((fact) => {
        const value = recordValue(fact.value);
        return (
          <article className="fact-card" key={stringValue(fact.id) || JSON.stringify(fact)}>
            <strong>{stringValue(fact.entity) || "fact"}</strong>
            <p>
              <span>{stringValue(fact.predicate) || "predicate"}</span>
              {stringValue(value?.text) || formatJson(fact.value)}
            </p>
          </article>
        );
      })}
    </div>
  );
}

function JsonDetails({
  label,
  value
}: {
  label: string;
  value: unknown;
}) {
  return (
    <details className="code-details">
      <summary>
        <span>{label}</span>
        <Braces size={14} aria-hidden="true" />
      </summary>
      <pre>{formatJson(value)}</pre>
    </details>
  );
}

function ClaimList({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="compact-list">
      <strong>Claim check</strong>
      {items.slice(0, 5).map((item) => (
        <p key={`${stringValue(item.claim)}-${stringValue(item.support)}`}>
          <span>{stringValue(item.support) || "unknown"}</span>
          {stringValue(item.claim)}
        </p>
      ))}
    </div>
  );
}

function RiskList({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="compact-list risk-list">
      <strong>Rischi</strong>
      {items.slice(0, 4).map((item) => (
        <p key={`${stringValue(item.risk)}-${stringValue(item.severity)}`}>
          <span>{stringValue(item.severity) || "risk"}</span>
          {stringValue(item.risk)}
        </p>
      ))}
    </div>
  );
}

function EvidenceMetric({ label, value }: { label: string; value: string }) {
  if (!value) {
    return null;
  }
  return (
    <span>
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}

function stepIcon(kind: AgentStep["kind"]) {
  if (kind === "thinking") {
    return <BrainCircuit size={15} aria-hidden="true" />;
  }
  if (kind === "memory") {
    return <BookOpen size={15} aria-hidden="true" />;
  }
  if (kind === "note") {
    return <MessageSquarePlus size={15} aria-hidden="true" />;
  }
  if (kind === "schema") {
    return <ListChecks size={15} aria-hidden="true" />;
  }
  if (kind === "session") {
    return <FileSearch size={15} aria-hidden="true" />;
  }
  if (kind === "metacognition") {
    return <ShieldCheck size={15} aria-hidden="true" />;
  }
  if (kind === "tool" || kind === "result") {
    return kind === "result" ? (
      <CheckCircle2 size={15} aria-hidden="true" />
    ) : (
      <Search size={15} aria-hidden="true" />
    );
  }
  if (kind === "answer") {
    return <Bot size={15} aria-hidden="true" />;
  }
  return kind === "runtime" ? (
    <Activity size={15} aria-hidden="true" />
  ) : (
    <AlertTriangle size={15} aria-hidden="true" />
  );
}

function stepKindLabel(kind: AgentStep["kind"]): string {
  if (kind === "thinking") {
    return "Thinking";
  }
  if (kind === "memory") {
    return "Memoria";
  }
  if (kind === "note") {
    return "Nota";
  }
  if (kind === "schema") {
    return "Schema";
  }
  if (kind === "session") {
    return "Sessione";
  }
  if (kind === "metacognition") {
    return "Metacognizione";
  }
  if (kind === "tool") {
    return "Tool";
  }
  if (kind === "result") {
    return "Evidenza";
  }
  if (kind === "answer") {
    return "Risposta";
  }
  return "Runtime";
}

function runtimeBlockLabel(type: string): string {
  if (type === "session_context") {
    return "Contesto sessione";
  }
  if (type === "message_context") {
    return "Contesto messaggio";
  }
  if (type === "scarlet_state") {
    return "Stato Scarlet";
  }
  return "Runtime context";
}

function dashboardTitle(tab: DashboardTab, selectedTurnId: string | null): string {
  if (tab === "stream") {
    return selectedTurnId ?? "stream non selezionato";
  }
  if (tab === "memories") {
    return "memorie semantiche";
  }
  if (tab === "profile") {
    return "profilo utente";
  }
  return "impostazioni";
}

function memoryContextTitle(data: Record<string, unknown>): string {
  const selected = numericValue(data.selected_count) ?? recordArray(data.selected).length;
  if (selected > 0) {
    return `Memorie recuperate (${selected})`;
  }
  return "Ricerca memoria";
}

function memoryContextSummary(data: Record<string, unknown>): string {
  const selected = numericValue(data.selected_count) ?? recordArray(data.selected).length;
  const candidates = numericValue(data.candidate_count);
  const negative = stringValue(data.negative_evidence);
  if (selected > 0) {
    return `${selected} memorie selezionate su ${candidates ?? "n/a"} candidate.`;
  }
  if (negative === "no_relevant_memory_selected") {
    return "Nessuna memoria persistente selezionata per questo turno.";
  }
  return "Contesto memoria calcolato.";
}

function runtimeContextTitle(data: Record<string, unknown>): string {
  const version = stringValue(data.schema_version);
  const count = numericValue(data.block_count) ?? recordArray(data.blocks).length;
  if (version) {
    return `Runtime context ${version}`;
  }
  return `Runtime context (${count} blocchi)`;
}

function runtimeContextSummary(data: Record<string, unknown>): string {
  const blockIndex = recordArray(data.block_index);
  const blocks = blockIndex.length > 0 ? blockIndex : recordArray(data.blocks);
  const labels = blocks
    .map((item) => {
      const record = recordValue(item);
      return stringValue(record?.type) || stringValue(record?.id);
    })
    .filter(Boolean)
    .slice(0, 4);
  if (labels.length > 0) {
    return `Blocchi: ${labels.join(", ")}.`;
  }
  const count = numericValue(data.block_count);
  return `Contesto operativo composto${count ? `: ${count} blocchi` : ""}.`;
}

function classifyToolStepKind(value: unknown): AgentStep["kind"] {
  const path = stringValue(recordValue(value)?.path);
  if (path.includes("/mind/schema")) {
    return "schema";
  }
  if (path.includes("/mind/sessions")) {
    return "session";
  }
  if (path.includes("/mind/metacognition")) {
    return "metacognition";
  }
  if (path.includes("/mind/memory")) {
    return "memory";
  }
  return "tool";
}

function classifyToolResultKind(value: unknown): AgentStep["kind"] {
  const args = recordValue(recordValue(value)?.arguments);
  const path = stringValue(args?.path);
  if (path.includes("/mind/schema")) {
    return "schema";
  }
  if (path.includes("/mind/sessions")) {
    return "session";
  }
  if (path.includes("/mind/metacognition")) {
    return "metacognition";
  }
  if (path.includes("/mind/memory")) {
    return "memory";
  }
  return "result";
}

function toolCallTitle(value: unknown, fallbackToolName: unknown): string {
  const source = recordValue(value);
  const path = stringValue(source?.path);
  const method = stringValue(source?.method);
  if (path.includes("/mind/schema")) {
    return "Controllo schema API Mind";
  }
  if (path.includes("/mind/sessions/") && path.includes("/summarize")) {
    return "Compattazione sessione";
  }
  if (path.includes("/mind/sessions/")) {
    return "Lettura sessione sorgente";
  }
  if (path.endsWith("/mind/sessions")) {
    return "Ricerca sessioni";
  }
  if (path.includes("/mind/metacognition")) {
    return "Revisione metacognitiva";
  }
  if (path.includes("/mind/memory/search")) {
    return "Ricerca memoria";
  }
  if (path.includes("/mind/memory/write")) {
    return "Scrittura memoria";
  }
  if (path.includes("/mind/memory")) {
    return "Operazione memoria";
  }
  return `${method || "Tool"} ${String(fallbackToolName ?? "mind_api")}`;
}

function toolCallSummary(value: unknown): string {
  const source = recordValue(value);
  const method = stringValue(source?.method);
  const path = stringValue(source?.path);
  const intent = stringValue(source?.intent);
  return [method, path, intent].filter(Boolean).join(" - ");
}

function toolResultTitle(value: unknown): string {
  const source = recordValue(value);
  const status = source?.status === "error" ? "errore" : "evidenza";
  const args = recordValue(source?.arguments);
  const path = stringValue(args?.path);
  if (path.includes("/mind/schema")) {
    return `Schema ricevuto`;
  }
  if (path.includes("/mind/sessions/") && path.includes("/summarize")) {
    return `Summary sessione`;
  }
  if (path.includes("/mind/sessions/")) {
    return `Transcript sessione`;
  }
  if (path.endsWith("/mind/sessions")) {
    return `Sessioni trovate`;
  }
  if (path.includes("/mind/metacognition")) {
    return `Esito metacognizione`;
  }
  if (path.includes("/mind/memory")) {
    return `Memoria: ${status}`;
  }
  return `Tool result: ${status}`;
}

function toolResultSummary(value: unknown): string {
  const source = recordValue(value);
  const result = recordValue(recordValue(source?.result)?.result);
  const error = recordValue(recordValue(source?.result)?.error);
  if (error) {
    return `${stringValue(error.code) || "error"}: ${stringValue(error.message)}`;
  }
  if (Array.isArray(result?.routes)) {
    const routes = recordArray(result.routes);
    const implemented = routes.filter((route) => stringValue(route.status) === "implemented").length;
    const planned = routes.filter((route) => stringValue(route.status) === "planned").length;
    const unavailable = routes.filter((route) => stringValue(route.status) === "unavailable").length;
    return `${implemented} implementate, ${planned} pianificate, ${unavailable} non disponibili.`;
  }
  if (Array.isArray(result?.sessions)) {
    return `${recordArray(result.sessions).length} sessioni disponibili.`;
  }
  if (recordValue(result?.session)) {
    return `Sessione letta con ${recordArray(result?.messages).length} messaggi.`;
  }
  if (recordValue(result?.review)) {
    return stringValue(recordValue(result?.review)?.review_summary) || "Revisione completata.";
  }
  return formatJson(source?.result ?? value);
}

function stepsFromTraces(traces: TraceItem[]): AgentStep[] {
  const steps: AgentStep[] = [];
  let seq = 1;

  for (const trace of traces) {
    if (trace.kind === "memory.context") {
      const payload = {
        selected_count: trace.payload.selected_count,
        candidate_count: trace.payload.candidate_count,
        negative_evidence: trace.payload.negative_evidence,
        selected: trace.payload.selected,
        near_miss: trace.payload.near_miss,
        excluded: trace.payload.excluded,
        conflicts: trace.payload.conflicts
      };
      steps.push({
        id: `trace-memory-context-${trace.id}`,
        kind: "memory",
        seq: seq++,
        title: memoryContextTitle(payload),
        body: memoryContextSummary(payload),
        data: payload,
        status: "done"
      });
    }

    if (trace.kind === "runtime.context") {
      steps.push({
        id: `trace-runtime-context-${trace.id}`,
        kind: "runtime",
        seq: seq++,
        title: runtimeContextTitle(trace.payload),
        body: runtimeContextSummary(trace.payload),
        data: trace.payload,
        status: "done"
      });
    }

    if (trace.kind === "llm.request") {
      steps.push({
        id: `trace-request-${trace.id}`,
        kind: "runtime",
        seq: seq++,
        title: "Persisted model request",
        body: `tools: ${Array.isArray(trace.payload.tools) ? trace.payload.tools.length : 0}`,
        status: "done"
      });
    }

    if (trace.kind === "mind.tool_call") {
      const argumentsPayload = trace.payload.arguments ?? {};
      const resultPayload = {
        provider_tool_use_id: trace.payload.provider_tool_use_id,
        tool_name: trace.payload.tool_name,
        arguments: argumentsPayload,
        result: trace.payload.result,
        status: trace.payload.status,
        latency_ms: trace.payload.latency_ms,
        tool_call_id: trace.payload.tool_call_id
      };
      steps.push({
        id: `trace-tool-${trace.id}`,
        kind: classifyToolStepKind(argumentsPayload),
        seq: seq++,
        title: toolCallTitle(argumentsPayload, trace.payload.tool_name),
        body: toolCallSummary(argumentsPayload),
        data: {
          tool_name: trace.payload.tool_name,
          arguments: argumentsPayload
        },
        status: trace.payload.status === "error" ? "error" : "done"
      });
      steps.push({
        id: `trace-result-${trace.id}`,
        kind: classifyToolResultKind(resultPayload),
        seq: seq++,
        title: toolResultTitle(resultPayload),
        body: toolResultSummary(resultPayload),
        data: resultPayload,
        status: trace.payload.status === "error" ? "error" : "done"
      });
    }

    if (trace.kind === "llm.response") {
      for (const responseStep of responseStepsFromTrace(trace.payload)) {
        if (
          responseStep.block.type === "thinking" &&
          typeof responseStep.block.thinking === "string"
        ) {
          steps.push({
            id: `trace-thinking-${trace.id}-${steps.length}`,
            kind: "thinking",
            seq: seq++,
            title: "Provider thinking block",
            body: responseStep.block.thinking,
            status: "done"
          });
        }
        if (
          responseStep.block.type === "text" &&
          typeof responseStep.block.text === "string"
        ) {
          const isProgressNote = responseStep.hasToolUse;
          steps.push({
            id: `trace-${isProgressNote ? "note" : "answer"}-${trace.id}-${steps.length}`,
            kind: isProgressNote ? "note" : "answer",
            seq: seq++,
            title: isProgressNote ? "Nota pubblica di lavoro" : "Risposta finale",
            body: responseStep.block.text,
            status: "done"
          });
        }
      }
    }
  }

  return sortSteps(steps);
}

function stepsFromEvents(
  events: CognitiveEvent[],
  fallbackTraces: TraceItem[]
): AgentStep[] {
  if (events.length === 0) {
    return stepsFromTraces(fallbackTraces);
  }

  const steps = events
    .map((event) => stepFromEvent(event))
    .filter((step): step is AgentStep => Boolean(step));

  return sortSteps(steps.length > 0 ? steps : stepsFromTraces(fallbackTraces));
}

function stepFromEvent(
  event: CognitiveEvent,
  seqOverride?: number
): AgentStep | null {
  const payload = event.payload ?? {};
  const base = {
    seq: seqOverride ?? event.seq,
    status: event.status === "failed" || event.status === "error" ? "error" : "done"
  } as const;

  if (event.type === "memory.context.built") {
    return {
      id: event.id,
      kind: "memory",
      ...base,
      title: memoryContextTitle(payload),
      body: memoryContextSummary(payload),
      data: payload
    };
  }

  if (event.type === "runtime.context.built") {
    return {
      id: event.id,
      kind: "runtime",
      ...base,
      title: runtimeContextTitle(payload),
      body: runtimeContextSummary(payload),
      data: payload
    };
  }

  if (event.type === "mind.tool_call.started") {
    return {
      id: event.id,
      kind: classifyToolStepKind(payload.arguments),
      ...base,
      status: "done",
      title: toolCallTitle(payload.arguments, "mind_api"),
      body: toolCallSummary(payload.arguments),
      data: {
        tool_name: "mind_api",
        arguments: payload.arguments,
        event_type: event.type,
        event_seq: event.seq
      }
    };
  }

  if (
    event.type === "mind.tool_call.completed" ||
    event.type === "mind.tool_call.failed"
  ) {
    const resultPayload = {
      tool_name: "mind_api",
      arguments: payload.arguments,
      result: {
        ok: event.type === "mind.tool_call.completed",
        result: payload.result_summary
      },
      status: event.status,
      latency_ms: payload.latency_ms,
      tool_call_id: event.tool_call_id,
      event_type: event.type,
      event_seq: event.seq
    };
    return {
      id: event.id,
      kind: classifyToolResultKind(resultPayload),
      ...base,
      title: toolResultTitle(resultPayload),
      body: toolResultSummary(resultPayload),
      data: resultPayload
    };
  }

  if (event.type === "assistant.note.emitted") {
    return {
      id: event.id,
      kind: "note",
      ...base,
      title: "Nota pubblica di lavoro",
      body: stringValue(payload.text) || "",
      data: payload
    };
  }

  if (event.type === "assistant.answer.completed") {
    return {
      id: event.id,
      kind: "answer",
      ...base,
      title: "Risposta finale",
      body: stringValue(payload.text) || "",
      data: payload
    };
  }

  return {
    id: event.id,
    kind: "runtime",
    ...base,
    title: eventTitle(event),
    body: eventSummary(event),
    data: {
      ...payload,
      event_type: event.type,
      event_seq: event.seq,
      source: event.source,
      actor: event.actor,
      visibility: event.visibility
    }
  };
}

function responseStepsFromTrace(
  payload: Record<string, unknown>
): Array<{ block: Record<string, unknown>; hasToolUse: boolean }> {
  const steps: Array<{ block: Record<string, unknown>; hasToolUse: boolean }> = [];
  const rawMessages = payload.raw_provider_messages;
  if (Array.isArray(rawMessages)) {
    for (const message of rawMessages) {
      if (isRecord(message)) {
        const content = message.content;
        if (Array.isArray(content)) {
          const blocks = content.filter(isRecord) as Array<Record<string, unknown>>;
          const hasToolUse = blocks.some((block) => block.type === "tool_use");
          for (const block of blocks) {
            steps.push({ block, hasToolUse });
          }
        }
      }
    }
  }
  if (steps.length === 0) {
    const rawContent = payload.raw_content;
    if (Array.isArray(rawContent)) {
      const blocks = rawContent.filter(isRecord) as Array<Record<string, unknown>>;
      const hasToolUse = blocks.some((block) => block.type === "tool_use");
      for (const block of blocks) {
        steps.push({ block, hasToolUse });
      }
    }
  }
  return steps;
}

function eventTitle(event: CognitiveEvent): string {
  if (event.type === "turn.started") {
    return "Turn avviato";
  }
  if (event.type === "turn.completed") {
    return "Turn completato";
  }
  if (event.type === "turn.failed") {
    return "Turn fallito";
  }
  if (event.type === "llm.request.created") {
    return "Richiesta modello preparata";
  }
  if (event.type === "llm.request.started") {
    return "Richiesta modello avviata";
  }
  if (event.type === "llm.request.stopped") {
    return "Richiesta modello conclusa";
  }
  if (event.type === "llm.thinking.started") {
    return "Thinking avviato";
  }
  if (event.type === "llm.thinking.captured") {
    return "Thinking acquisito";
  }
  if (event.type === "llm.text.started") {
    return "Testo pubblico avviato";
  }
  if (event.type === "llm.response.completed") {
    return "Risposta modello registrata";
  }
  if (event.type === "message.user.persisted") {
    return "Messaggio utente salvato";
  }
  if (event.type === "message.assistant.persisted") {
    return "Messaggio Scarlet salvato";
  }
  if (event.type === "maintenance.job.scheduled") {
    return "Manutenzione programmata";
  }
  if (event.type === "maintenance.job.started") {
    return "Manutenzione avviata";
  }
  if (event.type === "maintenance.job.completed") {
    return "Manutenzione completata";
  }
  if (event.type === "maintenance.job.skipped") {
    return "Manutenzione saltata";
  }
  if (event.type === "maintenance.job.failed") {
    return "Manutenzione fallita";
  }
  if (event.type === "maintenance.memory_review.completed") {
    return "Review memorie mancate";
  }
  return event.type;
}

function eventSummary(event: CognitiveEvent): string {
  const payload = event.payload ?? {};
  if (event.type === "turn.started") {
    return [stringValue(payload.model), stringValue(payload.entrypoint)]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "turn.completed" || event.type === "turn.failed") {
    const latency = stringValue(payload.latency_ms);
    const code = stringValue(payload.code);
    return [latency ? `${latency} ms` : "", code].filter(Boolean).join(" - ");
  }
  if (event.type === "llm.request.created") {
    const stats = recordValue(payload.provider_message_stats);
    const messages = stringValue(stats?.message_count);
    const blocks = stringValue(stats?.content_block_count);
    const tokens = stringValue(payload.max_tokens);
    return [
      stringValue(payload.model),
      messages ? `${messages} messaggi` : "",
      blocks ? `${blocks} blocchi` : "",
      tokens ? `max ${tokens}` : ""
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "llm.response.completed") {
    const usage = recordValue(payload.usage);
    const input = stringValue(usage?.input_tokens);
    const output = stringValue(usage?.output_tokens);
    const calls = stringValue(payload.tool_call_count);
    return [
      stringValue(payload.stop_reason),
      calls ? `${calls} tool call` : "",
      input && output ? `${input}/${output} token` : ""
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "llm.request.started") {
    return [
      stringValue(payload.model),
      stringValue(payload.step) ? `step ${stringValue(payload.step)}` : "",
      stringValue(payload.provider_stream_event)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "llm.request.stopped") {
    return [
      stringValue(payload.stop_reason),
      stringValue(payload.model_step) ? `step ${stringValue(payload.model_step)}` : "",
      stringValue(payload.provider_stream_event)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "llm.thinking.started" || event.type === "llm.text.started") {
    return [
      stringValue(payload.model_step) ? `model step ${stringValue(payload.model_step)}` : "",
      stringValue(payload.index) ? `block ${stringValue(payload.index)}` : "",
      stringValue(payload.provider_stream_event)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "llm.thinking.captured") {
    return [
      stringValue(payload.has_text) ? "thinking disponibile" : "thinking vuoto",
      stringValue(payload.stop_reason)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (
    event.type === "message.user.persisted" ||
    event.type === "message.assistant.persisted"
  ) {
    const chars = stringValue(payload.content_chars);
    return chars ? `${chars} caratteri` : "";
  }
  if (event.type === "maintenance.job.scheduled") {
    const idle = stringValue(payload.idle_seconds);
    const dueAt = stringValue(payload.due_at);
    return [
      stringValue(payload.kind),
      idle ? `idle ${idle}s` : "",
      dueAt ? `due ${dueAt}` : ""
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (
    event.type === "maintenance.job.started" ||
    event.type === "maintenance.job.completed" ||
    event.type === "maintenance.job.skipped" ||
    event.type === "maintenance.job.failed"
  ) {
    const result = recordValue(payload.result);
    return [
      stringValue(payload.kind),
      stringValue(result?.reason),
      stringValue(payload.job_id)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  if (event.type === "maintenance.memory_review.completed") {
    const candidates = stringValue(payload.candidate_count);
    const recommended = stringValue(payload.write_recommended_count);
    return [
      candidates ? `${candidates} candidati` : "",
      recommended ? `${recommended} consigliati` : "",
      stringValue(payload.mode)
    ]
      .filter(Boolean)
      .join(" - ");
  }
  return formatJson(payload);
}

function sortSteps(steps: AgentStep[]): AgentStep[] {
  return [...steps].sort((left, right) => left.seq - right.seq);
}

function summarizeSteps(steps: AgentStep[]): StepSummary {
  const summary: StepSummary = {
    total: steps.length,
    active: 0,
    errors: 0,
    memory: 0,
    tools: 0,
    thinking: 0,
    notes: 0
  };
  for (const step of steps) {
    if (step.status === "active") {
      summary.active += 1;
    }
    if (step.status === "error") {
      summary.errors += 1;
    }
    if (step.kind === "memory") {
      summary.memory += 1;
    }
    if (
      step.kind === "tool" ||
      step.kind === "result" ||
      step.kind === "schema" ||
      step.kind === "session" ||
      step.kind === "metacognition"
    ) {
      summary.tools += 1;
    }
    if (step.kind === "thinking") {
      summary.thinking += 1;
    }
    if (step.kind === "note") {
      summary.notes += 1;
    }
  }
  return summary;
}

function eventSeq(event: StreamEvent): number {
  return numericValue(event.data.seq) ?? Date.now();
}

function numericValue(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  return isRecord(value) ? value : undefined;
}

function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

function arrayOfStrings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
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

function percentValue(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "";
  }
  return `${Math.round(value * 100)}%`;
}

function numberLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(value > 10 ? 1 : 2)
    : "";
}

function countCapabilityStatus(
  capabilities: Record<string, unknown> | undefined,
  status: string
): number {
  if (!capabilities) {
    return 0;
  }
  return Object.values(capabilities).filter((value) => value === status).length;
}

function truncate(value: string, maxLength: number): string {
  if (!value) {
    return "";
  }
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}...` : value;
}

function routeStatusLabel(status: string, count: number): string {
  if (status === "implemented") {
    return `Implementate (${count})`;
  }
  if (status === "planned") {
    return `Pianificate (${count})`;
  }
  if (status === "unavailable") {
    return `Non disponibili (${count})`;
  }
  return `${status} (${count})`;
}

function formatJson(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value ?? {}, null, 2);
}

function metricValue(source: unknown, key: string): string {
  if (!source || typeof source !== "object") {
    return "n/a";
  }
  const value = (source as Record<string, unknown>)[key];
  return typeof value === "number" || typeof value === "string" ? String(value) : "n/a";
}

function sessionTitle(session: ChatSession | null): string {
  if (!session) {
    return "No session selected";
  }
  const title = session.title?.trim();
  return title || "Untitled session";
}

function newSessionTitle(): string {
  return `Chat ${new Date().toLocaleString([], {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  })}`;
}

function formatSessionTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString([], {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function mergeSessionList(
  session: ChatSession,
  sessions: ChatSession[]
): ChatSession[] {
  return [session, ...sessions.filter((item) => item.id !== session.id)]
    .sort(
      (left, right) =>
        new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
    )
    .slice(0, 30);
}

function lastMessageTurnId(messages: ChatMessage[]): string | null {
  for (const message of [...messages].reverse()) {
    if (message.turn_id) {
      return message.turn_id;
    }
  }
  return null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}

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

type DashboardTab =
  | "memories"
  | "actions"
  | "model"
  | "events"
  | "warnings"
  | "settings"
  | "profile";

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
  const [activeTab, setActiveTab] = useState<DashboardTab>("actions");
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
  const toolInputBlockIdsRef = useRef<Record<string, string>>({});

  useEffect(() => {
    fetchHealth()
      .then((result) =>
        setHealth(`${result.status} - ${result.model} - ${result.database.profile}`)
      )
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
        toolInputBlockIdsRef.current = {};
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
          phase: "completed",
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
          blockId: `model-${String(event.data.step ?? "1")}`,
          phase: "streaming",
          title: `MiniMax request #${String(event.data.step ?? "1")}`,
          body: `model: ${String(event.data.model ?? "MiniMax-M3")}`,
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
          blockId: `memory-context-${String(event.data.trace_id ?? "pending")}`,
          phase: "completed",
          title: memoryContextTitle(payload),
          body: memoryContextSummary(payload),
          data: payload,
          status: "done"
        });
        }
        break;

      case "metacognitive_context":
        {
          const payload = {
            trace_id: event.data.trace_id,
            schema_version: event.data.schema_version,
            mode: event.data.mode,
            model_facing: event.data.model_facing,
            selection: event.data.selection,
            triggers: event.data.triggers,
            lessons: event.data.lessons,
            runtime_inputs: event.data.runtime_inputs,
            policy: event.data.policy
          };
          upsertStep(turnId, {
            id: `metacognitive-context-${String(event.data.trace_id ?? "pending")}`,
            kind: "metacognition",
            seq: eventSeq(event),
            blockId: `metacognitive-context-${String(event.data.trace_id ?? "pending")}`,
            phase: "completed",
            title: metacognitiveContextTitle(payload),
            body: metacognitiveContextSummary(payload),
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
            blockId: `runtime-context-${String(event.data.trace_id ?? "pending")}`,
            phase: "completed",
            title: runtimeContextTitle(payload),
            body: runtimeContextSummary(payload),
            data: payload,
            status: "done"
          });
        }
        break;

      case "thinking_start":
        upsertStep(turnId, {
          id: contentBlockStepId("thinking", event.data),
          kind: "thinking",
          seq: eventSeq(event),
          blockId: contentBlockStepId("thinking", event.data),
          modelStep: numericValue(event.data.model_step),
          phase: "streaming",
          title: `Thinking - model step ${String(event.data.model_step ?? "1")}`,
          body: "",
          data: event.data,
          status: "active"
        });
        break;

      case "thinking_delta":
        appendStepText(
          turnId,
          contentBlockStepId("thinking", event.data),
          {
            kind: "thinking",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            blockId: contentBlockStepId("thinking", event.data),
            phase: "streaming",
            title: `Thinking - model step ${String(event.data.model_step ?? "1")}`,
            text: String(event.data.text ?? ""),
            data: event.data
          }
        );
        break;

      case "thinking_captured":
        upsertStep(turnId, {
          id: contentBlockStepId("thinking", event.data),
          kind: "thinking",
          seq: eventSeq(event),
          blockId: contentBlockStepId("thinking", event.data),
          modelStep: numericValue(event.data.model_step),
          phase: "captured",
          title: `Thinking - model step ${String(event.data.model_step ?? "1")}`,
          body: String(event.data.text ?? ""),
          data: event.data,
          status: "done"
        });
        break;

      case "tool_use_start": {
        const blockKey = streamBlockKey(event.data);
        const toolStepId = toolStepIdFromProvider(event.data.provider_tool_use_id);
        toolInputBlockIdsRef.current[blockKey] = toolStepId;
        upsertStep(turnId, {
          id: toolStepId,
          kind: "tool",
          seq: eventSeq(event),
          blockId: toolStepId,
          modelStep: numericValue(event.data.model_step),
          phase: "created",
          title: `Prepare tool call: ${String(event.data.tool_name ?? "tool")}`,
          body: `provider id: ${String(event.data.provider_tool_use_id ?? "pending")}`,
          data: {
            ...event.data,
            lifecycle_phase: "created"
          },
          status: "active"
        });
        break;
      }

      case "tool_input_delta":
        appendStepText(
          turnId,
          toolInputBlockIdsRef.current[streamBlockKey(event.data)] ??
            `tool-input-${String(event.data.model_step ?? "1")}-${String(
              event.data.index ?? "0"
            )}`,
          {
            kind: "tool",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            blockId:
              toolInputBlockIdsRef.current[streamBlockKey(event.data)] ??
              `tool-input-${String(event.data.model_step ?? "1")}-${String(
                event.data.index ?? "0"
              )}`,
            phase: "streaming",
            title: "Tool input in streaming",
            text: String(event.data.partial_json ?? ""),
            data: {
              ...event.data,
              lifecycle_phase: "streaming"
            }
          }
        );
        break;

      case "tool_call":
        upsertStep(turnId, {
          id: toolStepIdFromProvider(event.data.provider_tool_use_id),
          kind: classifyToolStepKind(event.data.arguments),
          seq: eventSeq(event),
          blockId: toolStepIdFromProvider(event.data.provider_tool_use_id),
          modelStep: numericValue(event.data.model_step),
          phase: "executing",
          title: toolCallTitle(event.data.arguments, event.data.tool_name),
          body: toolCallSummary(event.data.arguments),
          data: {
            ...event.data,
            lifecycle_phase: "executing"
          },
          status: "active"
        });
        break;

      case "tool_result":
        upsertStep(turnId, {
          id: toolStepIdFromProvider(
            event.data.provider_tool_use_id ?? event.data.tool_call_id
          ),
          kind: classifyToolResultKind(event.data),
          seq: eventSeq(event),
          blockId: toolStepIdFromProvider(
            event.data.provider_tool_use_id ?? event.data.tool_call_id
          ),
          modelStep: numericValue(event.data.model_step),
          phase: event.data.status === "error" ? "failed" : "completed",
          title: toolCallTitle(event.data.arguments, event.data.tool_name),
          body: toolResultSummary(event.data),
          data: {
            ...event.data,
            lifecycle_phase: event.data.status === "error" ? "failed" : "completed"
          },
          status: event.data.status === "error" ? "error" : "done"
        });
        break;

      case "text_start":
        upsertStep(turnId, {
          id: contentBlockStepId("content", event.data),
          kind: "note",
          seq: eventSeq(event),
          blockId: contentBlockStepId("content", event.data),
          modelStep: numericValue(event.data.model_step),
          phase: "streaming",
          title: "Testo pubblico in streaming",
          body: "",
          data: {
            ...event.data,
            provisional_kind: "assistant_public_text",
            lifecycle_phase: "streaming"
          },
          status: "active"
        });
        break;

      case "text_delta": {
        const delta = String(event.data.text ?? "");
        appendStepText(
          turnId,
          contentBlockStepId("content", event.data),
          {
            kind: "note",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            blockId: contentBlockStepId("content", event.data),
            phase: "streaming",
            title: "Testo pubblico in streaming",
            text: delta,
            data: {
              ...event.data,
              provisional_kind: "assistant_public_text",
              lifecycle_phase: "streaming"
            }
          }
        );
        break;
      }

      case "assistant_note":
        upsertStep(turnId, {
          id: contentBlockStepId("content", event.data),
          kind: "note",
          seq: eventSeq(event),
          blockId: contentBlockStepId("content", event.data),
          modelStep: numericValue(event.data.model_step),
          phase: "completed",
          title: "Nota pubblica di lavoro",
          body: String(event.data.text ?? ""),
          data: {
            ...event.data,
            final_kind: "assistant_note",
            lifecycle_phase: "completed"
          },
          status: "done"
        });
        break;

      case "assistant_answer":
        setMessages((current) =>
          current.map((message) =>
            message.id === `stream-assistant-${turnId}`
              ? { ...message, content: String(event.data.text ?? "") }
              : message
          )
        );
        upsertStep(turnId, {
          id: contentBlockStepId("content", event.data),
          kind: "answer",
          seq: eventSeq(event),
          blockId: contentBlockStepId("content", event.data),
          modelStep: numericValue(event.data.model_step),
          phase: "completed",
          title: "Risposta finale",
          body: String(event.data.text ?? ""),
          data: {
            ...event.data,
            final_kind: "assistant_answer",
            lifecycle_phase: "completed"
          },
          status: "done"
        });
        break;

      case "model_stop":
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
          blockId: "runtime-complete",
          phase: "persisted",
          title: "Turn persisted",
          body: `${turn.trace_ids.length} trace records`,
          status: "done"
        });
        settleSteps(turn.turn_id);
        void Promise.all([
          fetchTraces(turn.turn_id),
          fetchEvents({ turnId: turn.turn_id })
        ]).then(([loadedTraces, loadedEvents]) => {
          const persistedSteps = stepsFromEvents(loadedEvents, loadedTraces);
          setTraces(loadedTraces);
          setTurnSteps((current) => ({
            ...current,
            [turn.turn_id]: reconcileTurnSteps(
              current[turn.turn_id] ?? [],
              persistedSteps
            )
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
      blockId?: string;
      modelStep?: number;
      phase?: AgentStep["phase"];
      title: string;
      text: string;
      data?: Record<string, unknown>;
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
              blockId: next.blockId ?? id,
              modelStep: next.modelStep,
              phase: next.phase ?? "streaming",
              title: next.title,
              body: next.text,
              data: next.data,
              status: "active"
            }
          ])
        };
      }
      return {
        ...current,
        [turnId]: sortSteps(
          steps.map((step) =>
            step.id === id
              ? {
                  ...step,
                  kind: next.kind,
                  title: next.title || step.title,
                  body: `${step.body}${next.text}`,
                  blockId: next.blockId ?? step.blockId ?? id,
                  modelStep: next.modelStep ?? step.modelStep,
                  phase: next.phase ?? step.phase ?? "streaming",
                  data: {
                    ...(step.data ?? {}),
                    ...(next.data ?? {})
                  },
                  status: "active"
                }
              : step
          )
        )
      };
    });
  }

  function settleSteps(turnId: string) {
    setTurnSteps((current) => ({
      ...current,
      [turnId]: (current[turnId] ?? []).map((step) =>
        step.status === "active"
          ? { ...step, status: "done", phase: step.phase ?? "completed" }
          : step
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
            <span>
              <Database size={14} aria-hidden="true" />
              {runtimeSettings?.database.profile ?? "unknown"}
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
              onClick={() => setActiveTab("actions")}
              title="Apri inspector sessione"
            >
              <PanelRight size={16} aria-hidden="true" />
            </button>
            <button
              className="icon-command"
              type="button"
              onClick={() => setActiveTab("settings")}
              title="Impostazioni e viste globali"
            >
              <Settings size={16} aria-hidden="true" />
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
            <ConversationFlow
              messages={messages}
              onLoadTraces={loadTraces}
              turnSteps={turnSteps}
            />
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

      <aside className="trace-pane" aria-label={dashboardSectionLabel(activeTab)}>
        <div className="pane-header compact">
          <div>
            <div className="section-label">{dashboardSectionLabel(activeTab)}</div>
            <h2>{dashboardTitle(activeTab, selectedTurnId)}</h2>
          </div>
          <div className="dashboard-tabs" role="tablist" aria-label="Pannelli inspector sessione">
          <TabButton
              active={activeTab === "memories"}
              icon={<BookOpen size={15} aria-hidden="true" />}
              label="Memorie"
              onClick={() => setActiveTab("memories")}
            />
            <TabButton
              active={activeTab === "actions"}
              icon={<Activity size={15} aria-hidden="true" />}
              label="Azioni"
              onClick={() => setActiveTab("actions")}
            />
            <TabButton
              active={activeTab === "model"}
              icon={<Gauge size={15} aria-hidden="true" />}
              label="Modello"
              onClick={() => setActiveTab("model")}
            />
            <TabButton
              active={activeTab === "events"}
              icon={<ListChecks size={15} aria-hidden="true" />}
              label="Eventi"
              onClick={() => setActiveTab("events")}
            />
            <TabButton
              active={activeTab === "warnings"}
              icon={<AlertTriangle size={15} aria-hidden="true" />}
              label="Avvisi"
              onClick={() => setActiveTab("warnings")}
            />
          </div>
        </div>

        <DashboardPanel
          activeTab={activeTab}
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

function ConversationFlow({
  messages,
  onLoadTraces,
  turnSteps
}: {
  messages: ChatMessage[];
  onLoadTraces: (turnId: string) => void;
  turnSteps: Record<string, AgentStep[]>;
}) {
  return (
    <>
      {messages.map((message) => {
        if (message.role === "assistant") {
          return (
            <AssistantTurnBlocks
              key={message.id}
              message={message}
              onLoadTraces={onLoadTraces}
              steps={message.turn_id ? turnSteps[message.turn_id] ?? [] : []}
            />
          );
        }
        return (
          <UserMessageBlock
            key={message.id}
            message={message}
            onLoadTraces={onLoadTraces}
          />
        );
      })}
    </>
  );
}

function UserMessageBlock({
  message,
  onLoadTraces
}: {
  message: ChatMessage;
  onLoadTraces: (turnId: string) => void;
}) {
  return (
    <article className="chat-flow-card user-message-block">
      <div className="flow-card-icon">
        <UserRound size={16} aria-hidden="true" />
      </div>
      <div className="flow-card-body">
        <FlowCardHeader
          label="Utente"
          title="Tu"
          badge={formatSessionTime(message.created_at)}
          onInspect={message.turn_id ? () => onLoadTraces(message.turn_id!) : undefined}
        />
        <p>{message.content}</p>
      </div>
    </article>
  );
}

function AssistantTurnBlocks({
  message,
  onLoadTraces,
  steps
}: {
  message: ChatMessage;
  onLoadTraces: (turnId: string) => void;
  steps: AgentStep[];
}) {
  const visibleSteps = centerFlowSteps(steps);
  const hasAnswerBlock = visibleSteps.some((step) => step.kind === "answer");
  if (visibleSteps.length === 0) {
    return (
      <article className="chat-flow-card answer-flow-block">
        <div className="flow-card-icon assistant">
          <Bot size={16} aria-hidden="true" />
        </div>
        <div className="flow-card-body">
          <FlowCardHeader
            label="Risposta finale"
            title="Scarlet"
            badge={message.turn_id ? "evidenze" : undefined}
            onInspect={message.turn_id ? () => onLoadTraces(message.turn_id!) : undefined}
          />
          <AnswerBlock text={message.content || "..."} data={message.metadata} />
        </div>
      </article>
    );
  }

  return (
    <section className="assistant-flow" aria-label="Blocchi risposta Scarlet">
      {visibleSteps.map((step, index) => (
        <FlowStepCard
          index={index + 1}
          key={step.id}
          onInspect={message.turn_id ? () => onLoadTraces(message.turn_id!) : undefined}
          step={step}
        />
      ))}
      {!hasAnswerBlock && message.content ? (
        <article className="chat-flow-card answer-flow-block">
          <div className="flow-card-index">{visibleSteps.length + 1}</div>
          <div className="flow-card-icon assistant">
            <Bot size={16} aria-hidden="true" />
          </div>
          <div className="flow-card-body">
            <FlowCardHeader
              label="Risposta finale"
              title="Scarlet"
              badge="fallback"
              onInspect={message.turn_id ? () => onLoadTraces(message.turn_id!) : undefined}
            />
            <AnswerBlock text={message.content} data={message.metadata} />
          </div>
        </article>
      ) : null}
    </section>
  );
}

function FlowStepCard({
  index,
  onInspect,
  step
}: {
  index: number;
  onInspect?: () => void;
  step: AgentStep;
}) {
  return (
    <article className={`chat-flow-card flow-step-card ${step.kind} ${step.status}`}>
      <div className="flow-card-index">{index}</div>
      <div className="flow-card-icon">{stepIcon(step.kind)}</div>
      <div className="flow-card-body">
        <FlowCardHeader
          label={stepKindLabel(step.kind)}
          title={centerStepTitle(step)}
          badge={stepBadge(step)}
          onInspect={onInspect}
        />
        <CenterStepContent step={step} />
      </div>
    </article>
  );
}

function FlowCardHeader({
  badge,
  label,
  onInspect,
  title
}: {
  badge?: string;
  label: string;
  onInspect?: () => void;
  title: string;
}) {
  return (
    <div className="flow-card-header">
      <div>
        <small>{label}</small>
        <strong>{title}</strong>
      </div>
      <div className="flow-card-actions">
        {badge ? <span>{badge}</span> : null}
        {onInspect ? (
          <button
            className="mini-icon-button"
            type="button"
            onClick={onInspect}
            title="Apri dettagli tecnici"
          >
            <Braces size={14} aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </div>
  );
}

function CenterStepContent({ step }: { step: AgentStep }) {
  if (isToolExchangeStep(step)) {
    return <ToolExchangeBlock step={step} />;
  }
  if (step.kind === "memory") {
    return <CenterMemoryBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "runtime" && recordArray(step.data?.blocks).length > 0) {
    return <CenterRuntimeContextBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "thinking") {
    return <ThinkingBlock text={step.body} active={step.status === "active"} data={step.data} />;
  }
  if (step.kind === "note") {
    return <PublicNoteBlock text={step.body} data={step.data} />;
  }
  if (step.kind === "answer") {
    return <AnswerBlock text={step.body} data={step.data} />;
  }
  return <RuntimeEventBlock step={step} />;
}

function CenterMemoryBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  const selected = recordArray(data?.selected);
  const nearMiss = recordArray(data?.near_miss);
  const conflicts = recordArray(data?.conflicts);
  return (
    <div className="center-summary-block memory-summary-block">
      <div className="summary-row">
        <span>{selected.length} selezionate</span>
        <span>{nearMiss.length} near miss</span>
        <span>{conflicts.length} conflitti</span>
      </div>
      {selected.length > 0 ? (
        <div className="compact-memory-list">
          {selected.slice(0, 3).map((memory) => (
            <CompactMemory memory={memory} key={stringValue(memory.id) || JSON.stringify(memory)} />
          ))}
        </div>
      ) : (
        <p>{fallback || "Nessuna memoria automatica selezionata per questo turno."}</p>
      )}
      <JsonDetails label="Dettaglio memoria automatica" value={data} />
    </div>
  );
}

function CenterRuntimeContextBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  const blocks = recordArray(data?.blocks);
  const labels = blocks
    .map((block) => runtimeBlockLabel(stringValue(block.type)))
    .filter(Boolean);
  return (
    <div className="center-summary-block runtime-summary-block">
      <div className="summary-row">
        <span>{stringValue(data?.schema_version) || "runtime context"}</span>
        <span>{blocks.length} blocchi</span>
      </div>
      <p>{labels.length > 0 ? labels.join(", ") : fallback}</p>
      <details className="code-details">
        <summary>
          <span>Blocchi di contesto</span>
          <Braces size={14} aria-hidden="true" />
        </summary>
        <div className="runtime-compact-list">
          {blocks.map((block) => (
            <RuntimeContextCard
              block={block}
              key={stringValue(block.id) || stringValue(block.type) || JSON.stringify(block)}
            />
          ))}
        </div>
      </details>
    </div>
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
    const memorySteps = selectedSteps.filter(
      (step) => step.kind === "memory" || isMemoryToolStep(step)
    );
    return (
      <InspectorPanel
        empty="Nessuna memoria usata nel turno selezionato."
        steps={memorySteps}
        title="Memorie della conversazione"
        subtitle="Retrieval automatico e operazioni memoria usate da Scarlet"
      />
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
            Database attivo:{" "}
            <strong>{runtimeSettings?.database.profile ?? "unknown"}</strong>
            {runtimeSettings?.codex_test ? " · isolamento Codex test attivo" : ""}
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

  if (activeTab === "actions") {
    return (
      <InspectorPanel
        empty="Nessuna azione tool nel turno selezionato."
        steps={selectedSteps.filter((step) => isToolExchangeStep(step))}
        title="Azioni agente"
        subtitle="Tool call, session recall, schema, memoria e metacognizione"
      />
    );
  }

  if (activeTab === "model") {
    return <ModelInputPanel traces={traces} />;
  }

  if (activeTab === "events") {
    return (
      <InspectorPanel
        empty="Nessun evento interno nel turno selezionato."
        steps={selectedSteps.filter((step) => isSystemEventStep(step))}
        title="Eventi interni"
        subtitle="Runtime, persistenza, manutenzione e segnali non mostrati nel centro chat"
      />
    );
  }

  if (activeTab === "warnings") {
    return (
      <InspectorPanel
        empty="Nessun warning o errore nel turno selezionato."
        steps={selectedSteps.filter((step) => step.status === "error")}
        title="Warning ed errori"
        subtitle="Errori tool, provider, manutenzione o runtime"
      />
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

function ModelInputPanel({ traces }: { traces: TraceItem[] }) {
  const requestTrace = latestTraceByKind(traces, "llm.request");
  if (!requestTrace) {
    return (
      <div className="dashboard-panel">
        <div className="empty-state">
          Seleziona un turno completato per vedere l'input reale inviato al modello.
        </div>
      </div>
    );
  }

  const payload = requestTrace.payload;
  const providerMessages = recordArray(payload.provider_messages);
  const tools = recordArray(payload.tools);
  const stats = recordValue(payload.provider_message_stats) ?? {};
  const runtimeContextText = stringValue(payload.runtime_context);
  const parsedRuntimeContext = parseRuntimeContextEnvelope(runtimeContextText);
  const compatibilityKeys = parsedRuntimeContext
    ? runtimeCompatibilityKeys(parsedRuntimeContext)
    : [];

  return (
    <div className="dashboard-panel model-input-panel">
      <div className="panel-toolbar">
        <div>
          <div className="section-label">Input modello</div>
          <h3>Richiesta effettiva a MiniMax</h3>
          <p>System, runtime context, cronologia provider-native e schema tool.</p>
        </div>
        <span className="count-pill">{providerMessages.length} msg</span>
      </div>

      <div className="metrics event-metrics">
        <Metric label="Modello" value={stringValue(payload.model) || "n/a"} />
        <Metric label="Stream" value={String(Boolean(payload.stream))} />
        <Metric label="Max token" value={stringValue(payload.max_tokens) || "default"} />
        <Metric label="History" value={stringValue(payload.provider_history_source) || "n/a"} />
        <Metric label="Blocchi" value={stringValue(stats.content_block_count) || "0"} />
        <Metric label="Approx token" value={stringValue(stats.approx_tokens) || "n/a"} />
      </div>

      <div className="dashboard-scroll model-input-scroll">
        <ModelSystemReadout payload={payload} />
        <ModelRuntimeContextReadout
          compatibilityKeys={compatibilityKeys}
          raw={runtimeContextText}
          runtimeContext={parsedRuntimeContext}
        />
        <ProviderMessagesReadout messages={providerMessages} stats={stats} />
        <ToolSchemaReadout tools={tools} />
        <JsonDetails label="Trace llm.request completa" value={payload} />
      </div>
    </div>
  );
}

function ModelSystemReadout({ payload }: { payload: Record<string, unknown> }) {
  const baseSystem = stringValue(payload.base_system);
  const effectiveSystem = stringValue(payload.system);
  const runtimeContext = stringValue(payload.runtime_context);
  return (
    <section className="model-section system-section">
      <div className="model-section-header">
        <div>
          <small>Blocco model-facing</small>
          <strong>System prompt + runtime context</strong>
        </div>
        <span>{stringValue(payload.system_source) || "system"}</span>
      </div>
      <div className="evidence-grid">
        <EvidenceMetric label="Prompt base" value={`${baseSystem.length} chars`} />
        <EvidenceMetric label="Runtime" value={`${runtimeContext.length} chars`} />
        <EvidenceMetric label="System effettivo" value={`${effectiveSystem.length} chars`} />
        <EvidenceMetric label="Prompt path" value={stringValue(payload.system_path)} />
      </div>
      <div className="soft-note">
        MiniMax riceve un solo campo system: il prompt base di Scarlet seguito dal
        blocco <code>&lt;runtime_context&gt;</code> generato dal backend.
      </div>
      <TextDetails label="Prompt base Scarlet" text={baseSystem} />
      <TextDetails label="Runtime context iniettato nel system" text={runtimeContext} />
      <TextDetails label="System completo inviato al modello" text={effectiveSystem} />
    </section>
  );
}

function ModelRuntimeContextReadout({
  compatibilityKeys,
  raw,
  runtimeContext
}: {
  compatibilityKeys: string[];
  raw: string;
  runtimeContext: Record<string, unknown> | null;
}) {
  if (!runtimeContext) {
    return (
      <section className="model-section runtime-section">
        <div className="model-section-header">
          <div>
            <small>Runtime context</small>
            <strong>Parsing non disponibile</strong>
          </div>
        </div>
        <div className="warning-note">
          Il runtime context esiste nella trace, ma non e stato possibile leggerlo
          come JSON strutturato.
        </div>
        <TextDetails label="Runtime context raw" text={raw} />
      </section>
    );
  }

  const blocks = recordArray(runtimeContext.blocks);
  return (
    <section className="model-section runtime-section">
      <div className="model-section-header">
        <div>
          <small>Blocco model-facing</small>
          <strong>Runtime context canonico</strong>
        </div>
        <span>{stringValue(runtimeContext.schema_version) || "runtime"}</span>
      </div>
      <div className="summary-row">
        <span>{blocks.length} blocchi canonici</span>
        <span>{compatibilityKeys.length} mirror compatibilita</span>
        {stringValue(runtimeContext.generated_at) ? (
          <span>{formatSessionTime(stringValue(runtimeContext.generated_at))}</span>
        ) : null}
      </div>
      {compatibilityKeys.length > 0 ? (
        <div className="soft-note">
          Campi mirror ancora presenti per compatibilita: {compatibilityKeys.join(", ")}.
          Sono dati model-facing duplicati rispetto ai blocchi e da valutare in una
          futura ottimizzazione payload.
        </div>
      ) : null}
      <RuntimeContextBlock data={runtimeContext} fallback="Runtime context model-facing" />
    </section>
  );
}

function ProviderMessagesReadout({
  messages,
  stats
}: {
  messages: Record<string, unknown>[];
  stats: Record<string, unknown>;
}) {
  return (
    <section className="model-section provider-section">
      <div className="model-section-header">
        <div>
          <small>Blocco model-facing</small>
          <strong>Cronologia provider-native</strong>
        </div>
        <span>{messages.length} messaggi</span>
      </div>
      <div className="evidence-grid">
        <EvidenceMetric label="Content block" value={stringValue(stats.content_block_count)} />
        <EvidenceMetric label="JSON chars" value={stringValue(stats.json_chars)} />
        <EvidenceMetric label="Approx token" value={stringValue(stats.approx_tokens)} />
      </div>
      <div className="provider-message-list">
        {messages.map((message, index) => (
          <ProviderMessageCard
            index={index + 1}
            key={`${index}-${stringValue(message.role)}-${formatJson(message).length}`}
            message={message}
          />
        ))}
      </div>
    </section>
  );
}

function ProviderMessageCard({
  index,
  message
}: {
  index: number;
  message: Record<string, unknown>;
}) {
  const role = stringValue(message.role) || "message";
  const contentBlocks = recordArray(message.content);
  const textContent = stringValue(message.content);
  return (
    <details className="provider-message-card">
      <summary>
        <span className={`provider-role ${role}`}>{role}</span>
        <strong>Messaggio {index}</strong>
        <small>{contentBlocks.length || (textContent ? 1 : 0)} blocchi</small>
      </summary>
      {contentBlocks.length > 0 ? (
        <div className="provider-content-list">
          {contentBlocks.map((block, blockIndex) => (
            <ProviderContentBlock
              block={block}
              index={blockIndex + 1}
              key={`${blockIndex}-${stringValue(block.type)}-${formatJson(block).length}`}
            />
          ))}
        </div>
      ) : (
        <p className="provider-text-content">{textContent || "Messaggio senza content leggibile."}</p>
      )}
      <JsonDetails label="Messaggio provider raw" value={message} />
    </details>
  );
}

function ProviderContentBlock({
  block,
  index
}: {
  block: Record<string, unknown>;
  index: number;
}) {
  const type = stringValue(block.type) || "content";
  return (
    <article className={`provider-content-block ${type}`}>
      <div className="provider-content-header">
        <span>{index}</span>
        <strong>{providerBlockLabel(type)}</strong>
        <small>{providerBlockSummary(block)}</small>
      </div>
      <p>{providerBlockPreview(block)}</p>
      <JsonDetails label="Blocco provider raw" value={block} />
    </article>
  );
}

function ToolSchemaReadout({ tools }: { tools: Record<string, unknown>[] }) {
  return (
    <section className="model-section tool-schema-section">
      <div className="model-section-header">
        <div>
          <small>Blocco model-facing</small>
          <strong>Schema tool disponibili</strong>
        </div>
        <span>{tools.length} tool</span>
      </div>
      {tools.length === 0 ? (
        <div className="empty-state">Nessuno schema tool inviato al modello.</div>
      ) : (
        <div className="tool-schema-list">
          {tools.map((tool, index) => (
            <ToolSchemaCard index={index + 1} key={`${index}-${stringValue(tool.name)}`} tool={tool} />
          ))}
        </div>
      )}
    </section>
  );
}

function ToolSchemaCard({
  index,
  tool
}: {
  index: number;
  tool: Record<string, unknown>;
}) {
  const inputSchema = recordValue(tool.input_schema) ?? {};
  const properties = recordValue(inputSchema.properties) ?? {};
  const required = arrayOfStrings(inputSchema.required);
  return (
    <details className="tool-schema-card">
      <summary>
        <span>{index}</span>
        <strong>{stringValue(tool.name) || "tool"}</strong>
        <small>{required.length} required</small>
      </summary>
      <p>{stringValue(tool.description) || "Nessuna descrizione."}</p>
      <div className="schema-property-list">
        {Object.entries(properties).map(([name, property]) => {
          const propertyRecord = recordValue(property) ?? {};
          return (
            <div className="schema-property" key={name}>
              <strong>
                {name}
                {required.includes(name) ? " *" : ""}
              </strong>
              <span>{stringValue(propertyRecord.type) || "value"}</span>
              <p>{stringValue(propertyRecord.description) || "Parametro senza descrizione."}</p>
            </div>
          );
        })}
      </div>
      <JsonDetails label="Schema tool raw" value={tool} />
    </details>
  );
}

function InspectorPanel({
  empty,
  steps,
  subtitle,
  title
}: {
  empty: string;
  steps: AgentStep[];
  subtitle: string;
  title: string;
}) {
  const ordered = sortSteps(mergeAgentSteps(steps));
  return (
    <div className="dashboard-panel">
      <div className="panel-toolbar">
        <div>
          <div className="section-label">Inspector sessione</div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className="count-pill">{ordered.length}</span>
      </div>
      <div className="dashboard-scroll inspector-list">
        {ordered.length === 0 ? (
          <div className="empty-state">{empty}</div>
        ) : (
          ordered.map((step, index) => (
            <details className={`inspector-item ${step.kind} ${step.status}`} key={step.id}>
              <summary>
                <span className="inspector-index">{index + 1}</span>
                <span className="inspector-icon">{stepIcon(step.kind)}</span>
                <span className="inspector-summary">
                  <small>{stepKindLabel(step.kind)}</small>
                  <strong>{centerStepTitle(step)}</strong>
                </span>
                <span className="inspector-status">{step.phase || step.status}</span>
              </summary>
              <div className="inspector-body">
                <AgentStepContent step={step} />
                <JsonDetails label="Raw blocco" value={step.data ?? { body: step.body }} />
              </div>
            </details>
          ))
        )}
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
                  {step.phase ? <small>{step.phase}</small> : null}
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
  if (isToolExchangeStep(step)) {
    return <ToolExchangeBlock step={step} />;
  }
  if (step.kind === "runtime" && recordArray(step.data?.blocks).length > 0) {
    return <RuntimeContextBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "memory") {
    return <MemoryContextBlock data={step.data} fallback={step.body} />;
  }
  if (
    step.kind === "metacognition" &&
    stringValue(step.data?.operation) === "metacognitive.context"
  ) {
    return <MetacognitiveContextBlock data={step.data} fallback={step.body} />;
  }
  if (step.kind === "thinking") {
    return <ThinkingBlock text={step.body} active={step.status === "active"} data={step.data} />;
  }
  if (step.kind === "note") {
    return <PublicNoteBlock text={step.body} data={step.data} />;
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
    return <AnswerBlock text={step.body} data={step.data} />;
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
  if (type === "metacognitive_context") {
    return <MetacognitiveRuntimeReadout content={content} />;
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

function MetacognitiveRuntimeReadout({ content }: { content: Record<string, unknown> }) {
  return <MetacognitiveLessonList data={content} compact />;
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

function MetacognitiveContextBlock({
  data,
  fallback
}: {
  data?: Record<string, unknown>;
  fallback: string;
}) {
  if (!data) {
    return <pre>{fallback || "..."}</pre>;
  }
  const mode = stringValue(data.mode) || "shadow";
  const modelFacing = data.model_facing === true;
  const selection = recordValue(data.selection);
  const selectedCount =
    numericValue(selection?.selected_count) ?? recordArray(data.lessons).length;

  return (
    <div className="structured-block metacognitive-context-block">
      <div className="summary-row">
        <span>{mode}</span>
        <span>{modelFacing ? "inviato al modello" : "solo shadow/debug"}</span>
        <span>{selectedCount} lezioni candidate</span>
      </div>
      <MetacognitiveLessonList data={data} />
      <JsonDetails label="Metacognitive context JSON" value={data} />
    </div>
  );
}

function MetacognitiveLessonList({
  data,
  compact = false
}: {
  data: Record<string, unknown>;
  compact?: boolean;
}) {
  const lessons = recordArray(data.lessons);
  const triggers = recordArray(data.triggers);
  if (lessons.length === 0) {
    return (
      <div className="soft-note">
        Nessuna lezione metacognitiva selezionata per questo turno.
      </div>
    );
  }
  return (
    <div className="metacognitive-lesson-list">
      {lessons.slice(0, compact ? 2 : 5).map((lesson, index) => {
        const trigger = recordValue(triggers[index]);
        return (
          <article
            className="metacognitive-lesson-card"
            key={stringValue(lesson.id) || JSON.stringify(lesson)}
          >
            <div className="context-card-header">
              <div>
                <small>{stringValue(trigger?.id) || "trigger"}</small>
                <strong>{stringValue(lesson.title) || stringValue(lesson.id)}</strong>
              </div>
              {percentValue(lesson.confidence) ? (
                <span>{percentValue(lesson.confidence)}</span>
              ) : null}
            </div>
            <p>{truncate(stringValue(lesson.lesson), compact ? 220 : 360)}</p>
            {!compact && stringValue(lesson.recommended_action) ? (
              <div className="soft-note">{stringValue(lesson.recommended_action)}</div>
            ) : null}
          </article>
        );
      })}
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

function PublicNoteBlock({
  text,
  data
}: {
  text: string;
  data?: Record<string, unknown>;
}) {
  return (
    <div className="public-note">
      <p>{text.trim() || "..."}</p>
      <BlockTechnicalDetails label="Dettagli nota" value={data} />
    </div>
  );
}

function ThinkingBlock({
  text,
  active,
  data
}: {
  text: string;
  active: boolean;
  data?: Record<string, unknown>;
}) {
  const preview = firstLine(text) || "Thinking in attesa...";
  return (
    <details className="thinking-block" open={active || undefined}>
      <summary>
        <span>{preview}</span>
        <strong>{active ? "stream" : `${text.length} chars`}</strong>
      </summary>
      <pre>{text.trim() || "..."}</pre>
      <BlockTechnicalDetails label="Dettagli thinking" value={data} />
    </details>
  );
}

function AnswerBlock({
  text,
  data
}: {
  text: string;
  data?: Record<string, unknown>;
}) {
  return (
    <div className="answer-block">
      <p>{text.trim() || "..."}</p>
      <BlockTechnicalDetails label="Dettagli risposta" value={data} />
    </div>
  );
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

function ToolExchangeBlock({ step }: { step: AgentStep }) {
  const data = step.data;
  const fallback = step.body;
  const argumentsPayload = recordValue(data?.arguments);
  const source = argumentsPayload ?? data;
  if (!source) {
    return <pre>{fallback || "..."}</pre>;
  }
  const method = stringValue(source.method);
  const path = stringValue(source.path);
  const intent = stringValue(source.intent);
  const resultEnvelope = recordValue(data?.result);
  const result = recordValue(resultEnvelope?.result);
  const error = recordValue(resultEnvelope?.error);
  const phase = step.phase || stringValue(data?.lifecycle_phase);
  const statusLabel = phase || (step.status === "active" ? "in corso" : step.status);
  const streamedInput = !argumentsPayload && fallback ? fallback : "";
  const readableRoute = method || path ? (
    <>
      <span>{method || "CALL"}</span>
      <code>{path || "unknown path"}</code>
    </>
  ) : (
    <>
      <span>CALL</span>
      <code>preparazione input</code>
    </>
  );
  return (
    <details className={`tool-exchange ${step.status}`}>
      <summary>
        <span className="tool-route">{readableRoute}</span>
        <strong>{statusLabel}</strong>
      </summary>
      <div className="tool-exchange-body">
        {intent ? <p className="tool-intent">{intent}</p> : null}
        {resultEnvelope ? (
          <div className="tool-readable-output">
            <ResultSummary result={result} error={error} fallback={fallback} />
          </div>
        ) : (
          <div className="soft-note">
            {streamedInput
              ? "Scarlet sta componendo gli argomenti della chiamata."
              : "Chiamata preparata. Output non ancora disponibile."}
          </div>
        )}
        <div className="tool-panes">
          <section>
            <strong>Input completo</strong>
            <pre>{streamedInput || formatJson(source)}</pre>
          </section>
          <section>
            <strong>Output completo</strong>
            <pre>{resultEnvelope ? formatJson(resultEnvelope) : "In attesa del risultato."}</pre>
          </section>
        </div>
      </div>
    </details>
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

function TextDetails({ label, text }: { label: string; text: string }) {
  return (
    <details className="code-details">
      <summary>
        <span>{label}</span>
        <Braces size={14} aria-hidden="true" />
      </summary>
      <pre>{text || "..."}</pre>
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

function stepBadge(step: AgentStep): string {
  const phase = step.phase || stringValue(step.data?.lifecycle_phase);
  const model = step.modelStep ? `model ${step.modelStep}` : "";
  return [model, phase || step.status].filter(Boolean).join(" / ");
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
  if (type === "metacognitive_context") {
    return "Metacognitive context";
  }
  return "Runtime context";
}

function dashboardTitle(tab: DashboardTab, selectedTurnId: string | null): string {
  if (tab === "memories") {
    return "memorie della chat";
  }
  if (tab === "actions") {
    return "azioni agente";
  }
  if (tab === "model") {
    return "input modello";
  }
  if (tab === "events") {
    return "eventi sistema";
  }
  if (tab === "warnings") {
    return "warning";
  }
  if (tab === "profile") {
    return "profilo utente";
  }
  return "impostazioni";
}

function dashboardSectionLabel(tab: DashboardTab): string {
  if (tab === "settings" || tab === "profile") {
    return "Centro controllo Scarlet";
  }
  if (tab === "model") {
    return "Inspector modello";
  }
  return "Inspector sessione";
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

function metacognitiveContextTitle(data: Record<string, unknown>): string {
  const mode = stringValue(data.mode) || "shadow";
  const selection = recordValue(data.selection);
  const count = numericValue(selection?.selected_count) ?? recordArray(data.lessons).length;
  if (data.model_facing === true) {
    return `Metacognitive context (${count})`;
  }
  return `Shadow metacognitivo ${mode} (${count})`;
}

function metacognitiveContextSummary(data: Record<string, unknown>): string {
  const selection = recordValue(data.selection);
  const count = numericValue(selection?.selected_count) ?? recordArray(data.lessons).length;
  if (count === 0) {
    return "Nessuna lezione metacognitiva selezionata.";
  }
  if (data.model_facing === true) {
    return `${count} lezioni candidate iniettate nel runtime context per test controllato.`;
  }
  return `${count} lezioni candidate generate per osservazione, non iniettate nel modello.`;
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

function centerFlowSteps(steps: AgentStep[]): AgentStep[] {
  return sortSteps(mergeAgentSteps(steps)).filter((step) => {
    if (step.kind === "answer" || step.kind === "note" || step.kind === "thinking") {
      return true;
    }
    if (isToolExchangeStep(step)) {
      return true;
    }
    if (step.kind === "memory" && !isToolExchangeStep(step)) {
      return true;
    }
    if (
      step.kind === "metacognition" &&
      stringValue(step.data?.operation) === "metacognitive.context"
    ) {
      return true;
    }
    return step.kind === "runtime" && recordArray(step.data?.blocks).length > 0;
  });
}

function centerStepTitle(step: AgentStep): string {
  if (isToolExchangeStep(step)) {
    const args = recordValue(step.data?.arguments) ?? step.data;
    return toolCallTitle(args, step.data?.tool_name ?? "mind_api");
  }
  if (step.kind === "memory" && !isToolExchangeStep(step)) {
    return "Memorie automatiche del turno";
  }
  if (
    step.kind === "metacognition" &&
    stringValue(step.data?.operation) === "metacognitive.context"
  ) {
    return "Shadow metacognitivo";
  }
  if (step.kind === "runtime" && recordArray(step.data?.blocks).length > 0) {
    return "Contesto iniziale di Scarlet";
  }
  return step.title;
}

function isMemoryToolStep(step: AgentStep): boolean {
  const args = recordValue(step.data?.arguments);
  return stringValue(args?.path).includes("/mind/memory");
}

function isSystemEventStep(step: AgentStep): boolean {
  if (centerFlowSteps([step]).length > 0) {
    return false;
  }
  return step.kind === "runtime" || !isToolExchangeStep(step);
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
        blockId: `memory-context-${trace.id}`,
        phase: "persisted",
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
        blockId: `runtime-context-${trace.id}`,
        phase: "persisted",
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
        blockId: `model-request-${trace.id}`,
        phase: "persisted",
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
        blockId: toolStepIdFromProvider(trace.payload.provider_tool_use_id),
        phase: "executing",
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
        blockId: toolStepIdFromProvider(trace.payload.provider_tool_use_id),
        phase: trace.payload.status === "error" ? "failed" : "completed",
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
            blockId: `thinking-${String(responseStep.block.model_step ?? "trace")}-${String(
              responseStep.block.index ?? steps.length
            )}`,
            phase: "persisted",
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
            blockId: `content-${String(responseStep.block.model_step ?? "trace")}-${String(
              responseStep.block.index ?? steps.length
            )}`,
            phase: "persisted",
            title: isProgressNote ? "Nota pubblica di lavoro" : "Risposta finale",
            body: responseStep.block.text,
            status: "done"
          });
        }
      }
    }
  }

  return sortSteps(mergeAgentSteps(steps));
}

function stepsFromEvents(
  events: CognitiveEvent[],
  fallbackTraces: TraceItem[]
): AgentStep[] {
  if (events.length === 0) {
    return stepsFromTraces(fallbackTraces);
  }

  const steps = events
    .map((event) => stepFromEvent(event, undefined, fallbackTraces))
    .filter((step): step is AgentStep => Boolean(step));

  return sortSteps(
    mergeAgentSteps(steps.length > 0 ? steps : stepsFromTraces(fallbackTraces))
  );
}

function stepFromEvent(
  event: CognitiveEvent,
  seqOverride?: number,
  fallbackTraces: TraceItem[] = []
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
      blockId: `memory-context-${String(payload.trace_id ?? event.id)}`,
      phase: "persisted",
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
      blockId: `runtime-context-${String(payload.trace_id ?? event.id)}`,
      phase: "persisted",
      title: runtimeContextTitle(payload),
      body: runtimeContextSummary(payload),
      data: payload
    };
  }

  if (
    event.type === "metacognitive.context.shadowed" ||
    event.type === "metacognitive.context.injected"
  ) {
    return {
      id: event.id,
      kind: "metacognition",
      ...base,
      blockId: `metacognitive-context-${String(payload.trace_id ?? event.id)}`,
      phase: "persisted",
      title: metacognitiveContextTitle(payload),
      body: metacognitiveContextSummary(payload),
      data: payload
    };
  }

  if (event.type === "mind.tool_call.started") {
    return {
      id: toolStepIdFromProvider(payload.provider_tool_use_id),
      kind: classifyToolStepKind(payload.arguments),
      ...base,
      blockId: toolStepIdFromProvider(payload.provider_tool_use_id),
      phase: "created",
      status: "active",
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
    const trace = matchingToolTrace(event, fallbackTraces);
    const tracePayload = trace?.payload ?? {};
    const argumentsPayload =
      recordValue(payload.arguments) ?? recordValue(tracePayload.arguments) ?? {};
    const fullResult = tracePayload.result ?? {
      ok: event.type === "mind.tool_call.completed",
      result: payload.result_summary
    };
    const resultPayload = {
      tool_name: "mind_api",
      arguments: argumentsPayload,
      provider_tool_use_id:
        payload.provider_tool_use_id ?? tracePayload.provider_tool_use_id ?? event.tool_call_id,
      result: fullResult,
      result_summary: payload.result_summary,
      status: tracePayload.status ?? event.status,
      latency_ms: tracePayload.latency_ms ?? payload.latency_ms,
      tool_call_id: event.tool_call_id ?? tracePayload.tool_call_id,
      trace_id: trace?.id,
      event_type: event.type,
      event_seq: event.seq
    };
    return {
      id: toolStepIdFromProvider(payload.provider_tool_use_id ?? event.tool_call_id),
      kind: classifyToolResultKind(resultPayload),
      ...base,
      blockId: toolStepIdFromProvider(payload.provider_tool_use_id ?? event.tool_call_id),
      phase: event.type === "mind.tool_call.failed" ? "failed" : "completed",
      title: toolCallTitle(argumentsPayload, "mind_api"),
      body: toolResultSummary(resultPayload),
      data: resultPayload
    };
  }

  if (
    event.type === "mind.tool_use.started" ||
    event.type === "mind.tool_call.requested" ||
    event.type === "mind.tool_call.result_returned" ||
    event.type === "llm.request.started" ||
    event.type === "llm.request.stopped" ||
    event.type === "llm.text.started" ||
    event.type === "llm.thinking.started" ||
    event.type === "llm.response.completed" ||
    event.type === "message.user.persisted" ||
    event.type === "message.assistant.persisted"
  ) {
    return null;
  }

  if (event.type === "llm.thinking.captured") {
    const thinkingText =
      stringValue(payload.text) || recoverThinkingTextFromTraces(payload, fallbackTraces);
    return {
      id: contentBlockStepId("thinking", payload),
      kind: "thinking",
      ...base,
      blockId: contentBlockStepId("thinking", payload),
      phase: "captured",
      modelStep: numericValue(payload.model_step),
      title: `Thinking - model step ${stringValue(payload.model_step) || "?"}`,
      body: thinkingText,
      data: payload
    };
  }

  if (event.type === "assistant.note.emitted") {
    return {
      id: contentBlockStepId("content", payload),
      kind: "note",
      ...base,
      blockId: contentBlockStepId("content", payload),
      phase: "completed",
      modelStep: numericValue(payload.model_step),
      title: "Nota pubblica di lavoro",
      body: stringValue(payload.text) || "",
      data: payload
    };
  }

  if (event.type === "assistant.answer.completed") {
    return {
      id: contentBlockStepId("content", payload),
      kind: "answer",
      ...base,
      blockId: contentBlockStepId("content", payload),
      phase: "completed",
      modelStep: numericValue(payload.model_step),
      title: "Risposta finale",
      body: stringValue(payload.text) || "",
      data: payload
    };
  }

  return {
    id: event.id,
    kind: "runtime",
    ...base,
    blockId: event.id,
    phase: base.status === "error" ? "failed" : "persisted",
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

function recoverThinkingTextFromTraces(
  payload: Record<string, unknown>,
  traces: TraceItem[]
): string {
  const providerMessageId = stringValue(payload.provider_message_id);
  const preferredIndex = numericValue(payload.index);

  for (const trace of traces) {
    if (trace.kind !== "llm.response") {
      continue;
    }
    const rawMessages = recordArray(trace.payload.raw_provider_messages);
    for (const rawMessage of rawMessages) {
      const message = recordValue(rawMessage);
      if (!message) {
        continue;
      }
      if (
        providerMessageId &&
        stringValue(message.id) &&
        stringValue(message.id) !== providerMessageId
      ) {
        continue;
      }
      const content = recordArray(message.content);
      if (typeof preferredIndex === "number") {
        const indexed = recordValue(content[preferredIndex]);
        const thinking = stringValue(indexed?.thinking);
        if (thinking) {
          return thinking;
        }
      }
      for (const block of content) {
        const record = recordValue(block);
        const thinking = stringValue(record?.thinking);
        if (record?.type === "thinking" && thinking) {
          return thinking;
        }
      }
    }
  }
  return "";
}

function matchingToolTrace(event: CognitiveEvent, traces: TraceItem[]): TraceItem | undefined {
  const payload = event.payload ?? {};
  const toolCallId = event.tool_call_id;
  const providerToolUseId = stringValue(payload.provider_tool_use_id);
  return traces.find((trace) => {
    if (trace.kind !== "mind.tool_call") {
      return false;
    }
    return (
      (toolCallId && stringValue(trace.payload.tool_call_id) === toolCallId) ||
      (providerToolUseId && stringValue(trace.payload.provider_tool_use_id) === providerToolUseId)
    );
  });
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
  if (event.type === "metacognitive.context.shadowed") {
    return "Shadow metacognitivo generato";
  }
  if (event.type === "metacognitive.context.injected") {
    return "Metacognitive context iniettato";
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
  if (
    event.type === "metacognitive.context.shadowed" ||
    event.type === "metacognitive.context.injected"
  ) {
    const selection = recordValue(payload.selection);
    const lessons = numericValue(selection?.selected_count) ?? recordArray(payload.lessons).length;
    return [
      stringValue(payload.mode),
      `${lessons} lezioni`,
      payload.model_facing === true ? "model-facing" : "debug-only"
    ]
      .filter(Boolean)
      .join(" - ");
  }
  return formatJson(payload);
}

function sortSteps(steps: AgentStep[]): AgentStep[] {
  return [...steps].sort((left, right) => left.seq - right.seq);
}

function mergeAgentSteps(steps: AgentStep[]): AgentStep[] {
  const merged = new Map<string, AgentStep>();
  for (const step of sortSteps(steps)) {
    const existing = merged.get(step.id);
    if (!existing) {
      merged.set(step.id, step);
      continue;
    }
    merged.set(step.id, {
      ...existing,
      ...step,
      seq: Math.min(existing.seq, step.seq),
      title: step.title || existing.title,
      body: step.body || existing.body,
      data: {
        ...(existing.data ?? {}),
        ...(step.data ?? {})
      },
      status: step.status === "error" ? "error" : step.status
    });
  }
  return [...merged.values()];
}

function reconcileTurnSteps(liveSteps: AgentStep[], persistedSteps: AgentStep[]): AgentStep[] {
  if (persistedSteps.length === 0) {
    return sortSteps(liveSteps);
  }
  const usedLiveIds = new Set<string>();
  const reconciled = persistedSteps.map((persisted) => {
    const live = liveSteps.find((candidate) => {
      if (usedLiveIds.has(candidate.id)) {
        return false;
      }
      return (
        candidate.id === persisted.id ||
        Boolean(candidate.blockId && candidate.blockId === persisted.blockId) ||
        Boolean(candidate.blockId && candidate.blockId === persisted.id) ||
        Boolean(persisted.blockId && persisted.blockId === candidate.id)
      );
    });
    if (!live) {
      return {
        ...persisted,
        phase: persisted.phase ?? "persisted"
      };
    }
    usedLiveIds.add(live.id);
    return {
      ...live,
      ...persisted,
      seq: Math.min(live.seq, persisted.seq),
      blockId: persisted.blockId ?? live.blockId,
      phase: persisted.phase ?? "persisted",
      body: persisted.body || live.body,
      data: {
        ...(live.data ?? {}),
        ...(persisted.data ?? {})
      },
      status: persisted.status
    };
  });
  const orphanLiveSteps = liveSteps.filter(
    (step) => step.status === "active" && !usedLiveIds.has(step.id)
  );
  return sortSteps(mergeAgentSteps([...reconciled, ...orphanLiveSteps]));
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

function contentBlockStepId(prefix: "thinking" | "content", data: Record<string, unknown>): string {
  return `${prefix}-${String(data.model_step ?? "1")}-${String(data.index ?? "0")}`;
}

function toolStepIdFromProvider(value: unknown): string {
  return `tool-${String(value || "pending")}`;
}

function streamBlockKey(data: Record<string, unknown>): string {
  return `${String(data.model_step ?? "1")}-${String(data.index ?? "0")}`;
}

function isToolExchangeStep(step: AgentStep): boolean {
  if (
    ![
      "tool",
      "result",
      "schema",
      "session",
      "metacognition",
      "memory"
    ].includes(step.kind)
  ) {
    return false;
  }
  return Boolean(recordValue(step.data?.arguments) || step.data?.provider_tool_use_id);
}

function firstLine(text: string): string {
  return truncate(text.trim().split(/\r?\n/).find(Boolean) || "", 140);
}

function BlockTechnicalDetails({
  label,
  value
}: {
  label: string;
  value: unknown;
}) {
  if (!value || (isRecord(value) && Object.keys(value).length === 0)) {
    return null;
  }
  return <JsonDetails label={label} value={value} />;
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

function latestTraceByKind(traces: TraceItem[], kind: string): TraceItem | null {
  for (let index = traces.length - 1; index >= 0; index -= 1) {
    if (traces[index].kind === kind) {
      return traces[index];
    }
  }
  return null;
}

function parseRuntimeContextEnvelope(value: string): Record<string, unknown> | null {
  if (!value.trim()) {
    return null;
  }
  const match = value.match(/<runtime_context>\s*([\s\S]*?)\s*<\/runtime_context>/);
  const rawJson = match ? match[1] : value;
  try {
    const parsed = JSON.parse(rawJson);
    return recordValue(parsed) ?? null;
  } catch {
    return null;
  }
}

function runtimeCompatibilityKeys(runtimeContext: Record<string, unknown>): string[] {
  return [
    "memory_context",
    "mind_schema",
    "temporal_context",
    "recent_runtime_events",
    "capabilities"
  ].filter((key) => Object.prototype.hasOwnProperty.call(runtimeContext, key));
}

function providerBlockLabel(type: string): string {
  if (type === "thinking") {
    return "Thinking provider-visible";
  }
  if (type === "text") {
    return "Testo agente";
  }
  if (type === "tool_use") {
    return "Tool use";
  }
  if (type === "tool_result") {
    return "Tool result";
  }
  return type || "Content block";
}

function providerBlockSummary(block: Record<string, unknown>): string {
  const type = stringValue(block.type);
  if (type === "tool_use") {
    return [stringValue(block.name), stringValue(block.id)].filter(Boolean).join(" - ");
  }
  if (type === "tool_result") {
    return stringValue(block.tool_use_id) || "risultato tool";
  }
  const text = stringValue(block.text) || stringValue(block.thinking);
  return text ? `${text.length} chars` : "strutturato";
}

function providerBlockPreview(block: Record<string, unknown>): string {
  const type = stringValue(block.type);
  if (type === "thinking") {
    return truncate(firstLine(stringValue(block.thinking)), 240) || "Thinking vuoto.";
  }
  if (type === "text") {
    return truncate(firstLine(stringValue(block.text)), 240) || "Testo vuoto.";
  }
  if (type === "tool_use") {
    const input = recordValue(block.input) ?? {};
    return truncate(
      [stringValue(block.name) || "tool", stringValue(input.path), stringValue(input.intent)]
        .filter(Boolean)
        .join(" - "),
      260
    );
  }
  if (type === "tool_result") {
    return truncate(firstLine(formatJson(block.content)), 260);
  }
  return truncate(firstLine(formatJson(block)), 260);
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

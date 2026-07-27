import {
  AlertTriangle,
  ArrowRight,
  Brain,
  BrainCircuit,
  Check,
  Clock3,
  Compass,
  Database,
  MessageCircleMore,
  Plus,
  Quote,
  Search,
  Send,
  Sparkles,
  Target,
  UserRound,
  Wrench
} from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";

import {
  createSession,
  fetchAutonomyHistory,
  fetchAllSessionEventsV2,
  fetchMessages,
  streamTurnLive
} from "../api";
import { publicAssetPath } from "../runtimeAssets";
import type {
  AutonomyHistory,
  ChatMessage,
  ChatSession,
  DashboardMemory,
  ScarletLiveFrame,
  ScarletStreamEvent
} from "../types";
import { AutonomyHistoryPanel } from "./AutonomyHistoryPanel";
import {
  ChatEventDetailModal,
  type ChatEventInspection,
  inspectablePayload,
  isProtectedStreamEvent
} from "./ChatEventDetailModal";
import { DataJsonPanel } from "./DataJsonPanel";

type ChatFlowKind =
  | "user"
  | "context"
  | "memory"
  | "reflection"
  | "note"
  | "action"
  | "state"
  | "answer"
  | "error";

type ChatFlowBlock = {
  authoredByScarlet?: boolean;
  eventType: string;
  id: string;
  kind: ChatFlowKind;
  sourceEvents: ScarletStreamEvent[];
  status: "completed" | "live";
  text: string;
  title: string;
};

type LiveFrameState = ScarletLiveFrame & {
  text: string;
};

const CONSUMER_ACTIVITY_EVENT_TYPES = new Set([
  "agent.mode.changed",
  "llm.request.started",
  "llm.response.started",
  "llm.thinking.started",
  "llm.text.started",
  "mind.tool_use.started",
  "memory.context.built",
  "memory.recent_context.built",
  "runtime.context.built",
  "session.continuity.built",
  "turn.failed"
]);

const CONSUMER_ACTIVITY_EVENT_PREFIXES = [
  "answer.validation.",
  "mind.tool_call.",
  "organ.affect.",
  "organ.focus.",
  "organ.volition."
];

export function ChatViewportScreen({
  memories,
  onDataChanged,
  onNewSession,
  onOpenMemory,
  onOpenSessions,
  onSessionCreated,
  privateEvidenceUnlocked,
  session
}: {
  memories: DashboardMemory[];
  onDataChanged: () => void;
  onNewSession: () => void;
  onOpenMemory: () => void;
  onOpenSessions: () => void;
  onSessionCreated?: (session: ChatSession) => void;
  privateEvidenceUnlocked: boolean;
  session: ChatSession | null;
}) {
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(session);
  const [draft, setDraft] = useState("");
  const [events, setEvents] = useState<ScarletStreamEvent[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [liveFrames, setLiveFrames] = useState<Record<string, LiveFrameState>>({});
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [awaitingInitialContext, setAwaitingInitialContext] = useState(false);
  const [optimisticMessage, setOptimisticMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inspection, setInspection] = useState<ChatEventInspection | null>(null);
  const [autonomyOpen, setAutonomyOpen] = useState(false);
  const [autonomyHistory, setAutonomyHistory] =
    useState<AutonomyHistory | null>(null);
  const [autonomyError, setAutonomyError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCurrentSession(session);
    setInspection(null);
  }, [session]);

  useEffect(() => {
    if (!currentSession) {
      setEvents([]);
      setMessages([]);
      setLiveFrames({});
      setError(null);
      return;
    }
    let cancelled = false;
    setEvents([]);
    setMessages([]);
    setLiveFrames({});
    setLoading(true);
    setError(null);
    void Promise.all([
      fetchAllSessionEventsV2(currentSession.id),
      fetchMessages(currentSession.id)
    ])
      .then(([nextEvents, nextMessages]) => {
        if (cancelled) return;
        setEvents((current) =>
          mergeEvents(
            current.filter((item) => item.session_id === currentSession.id),
            nextEvents
          )
        );
        setMessages(nextMessages);
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Impossibile caricare la conversazione."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [currentSession?.id]);

  useEffect(() => {
    if (!autonomyOpen) return;
    let cancelled = false;

    const load = async () => {
      try {
        const history = await fetchAutonomyHistory();
        if (!cancelled) {
          setAutonomyHistory(history);
          setAutonomyError(null);
        }
      } catch (reason) {
        if (!cancelled) {
          setAutonomyError(
            reason instanceof Error
              ? reason.message
              : "Cronologia interiore non disponibile."
          );
        }
      }
    };

    void load();
    const interval = window.setInterval(() => void load(), 3000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [autonomyOpen]);

  const flow = useMemo(() => {
    const projected = projectConversation(
      events,
      messages,
      privateEvidenceUnlocked,
      liveFrames
    );
    if (optimisticMessage) {
      projected.push({
        eventType: "message.user.pending",
        id: "optimistic-user-message",
        kind: "user",
        sourceEvents: [],
        status: "live",
        text: optimisticMessage,
        title: "Tu"
      });
    }
    if (awaitingInitialContext) {
      projected.push({
        eventType: "ui.context.pending",
        id: "optimistic-context-assembly",
        kind: "context",
        sourceEvents: [],
        status: "live",
        text: "Scarlet sta raccogliendo il filo, i ricordi vicini e le conversazioni che potrebbero servire.",
        title: "Scarlet si sta orientando"
      });
    }
    if (error) {
      projected.push({
        eventType: "ui.transport.error",
        id: `transport-error-${error}`,
        kind: "error",
        sourceEvents: [],
        status: "completed",
        text: error,
        title: "Connessione interrotta"
      });
    }
    return projected;
  }, [
    error,
    events,
    messages,
    liveFrames,
    optimisticMessage,
    privateEvidenceUnlocked,
    sending,
    awaitingInitialContext
  ]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    const distanceFromBottom =
      scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight;
    if (sending || distanceFromBottom < 120) {
      scroller.scrollTop = scroller.scrollHeight;
    }
  }, [
    flow.length,
    flow[flow.length - 1]?.id,
    flow[flow.length - 1]?.status,
    flow[flow.length - 1]?.text.length,
    sending
  ]);

  async function submitMessage(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;

    setSending(true);
    setAwaitingInitialContext(true);
    setError(null);
    setOptimisticMessage(text);
    setDraft("");
    let targetSession = currentSession;
    const received: ScarletStreamEvent[] = [];

    try {
      if (!targetSession) {
        targetSession = await createSession();
        setCurrentSession(targetSession);
        onSessionCreated?.(targetSession);
      }

      await streamTurnLive(
        targetSession.id,
        text,
        undefined,
        (streamEvent) => {
          received.push(streamEvent);
          if (streamEvent.event_type === "message.user.persisted") {
            setOptimisticMessage(null);
          }
          if (
            streamEvent.event_type === "memory.context.built" ||
            streamEvent.event_type === "runtime.context.built" ||
            streamEvent.event_type === "llm.request.started"
          ) {
            setAwaitingInitialContext(false);
          }
          setEvents((current) => mergeEvents(current, [streamEvent]));
        },
        (frame) => {
          const delta =
            frame.frame_type === "tool_input_delta"
              ? valueAsString(frame.payload.partial_json)
              : valueAsString(frame.payload.text);
          if (!delta) return;
          setLiveFrames((current) => {
            const previous = current[frame.frame_id];
            return {
              ...current,
              [frame.frame_id]: {
                ...frame,
                text: `${previous?.text ?? ""}${delta}`
              }
            };
          });
        }
      );

      const terminal = received.find(
        (item) =>
          item.event_type === "turn.completed" ||
          item.event_type === "turn.failed"
      );
      if (!terminal) {
        throw new Error(
          "Lo stream si è chiuso senza uno stato terminale; avvio il replay."
        );
      }
      if (terminal.event_type === "turn.failed") {
        const message = valueAsString(terminal.payload.message);
        throw new Error(message || "Scarlet non ha potuto completare il turno.");
      }

      const [replayedEvents, persistedMessages] = await Promise.all([
        fetchAllSessionEventsV2(targetSession.id),
        fetchMessages(targetSession.id)
      ]);
      setEvents(mergeEvents([], replayedEvents));
      setMessages(persistedMessages);
      setLiveFrames({});
      onDataChanged();
    } catch (reason) {
      setAwaitingInitialContext(false);
      setOptimisticMessage(null);
      const message =
        reason instanceof Error ? reason.message : "Invio non riuscito.";
      const hasCanonicalFailure = received.some(
        (item) => item.event_type === "turn.failed"
      );
      setError(hasCanonicalFailure ? null : message);
      if (targetSession) {
        try {
          const [replayedEvents, persistedMessages] = await Promise.all([
            fetchAllSessionEventsV2(targetSession.id),
            fetchMessages(targetSession.id)
          ]);
          setEvents(mergeEvents([], replayedEvents));
          setMessages(persistedMessages);
          setLiveFrames({});
        } catch {
          // Keep the original transport error visible.
        }
      }
    } finally {
      setAwaitingInitialContext(false);
      setSending(false);
    }
  }

  const sessionData = {
    session: currentSession,
    messages,
    events: events
      .filter(
        (event) =>
          privateEvidenceUnlocked || !isProtectedStreamEvent(event)
      )
      .map((event) =>
        isProtectedStreamEvent(event)
          ? { ...event, payload: inspectablePayload(event) }
          : event
      ),
    hidden_protected_event_count: events.filter(isProtectedStreamEvent).length,
    reducer_contract: {
      deduplicate_by: "event_id",
      order_by: ["seq", "event_id"],
      visibility: "public + consumer-safe activity allowlist",
      private_evidence_unlocked: privateEvidenceUnlocked,
      provider_thinking_text:
        privateEvidenceUnlocked ? "visible in development" : "hidden by user",
      terminal_events: ["turn.completed", "turn.failed"]
    },
    transport: {
      mode: "core",
      persistence: true,
      live_schema_version: "scarlet-live-v1",
      replay_schema_version: "scarlet-stream-v2",
      streaming: true
    }
  };

  return (
    <section className="scarlet-screen scarlet-chat" data-testid="chat-screen">
      <header className="scarlet-chat__header">
        <div className="scarlet-chat__header-avatar" aria-hidden="true">
          <img alt="" src={publicAssetPath("prototype/scarlet-character-v1.png")} /><i />
        </div>
        <div className="scarlet-chat__header-copy">
          <p><MessageCircleMore aria-hidden="true" size={13} /> Conversazione</p>
          <h1>{currentSession?.title ?? "Una nuova conversazione"}</h1>
          <span>
            {loading
              ? "Riallineo cronologia ed eventi…"
              : currentSession
                ? "Sessione persistita · stream V2"
                : "La sessione verrà creata al primo messaggio"}
          </span>
        </div>
        <div className="scarlet-chat__header-actions">
          <button
            aria-label="Apri la continuità interiore di Scarlet"
            onClick={() => setAutonomyOpen(true)}
            type="button"
          >
            <BrainCircuit aria-hidden="true" size={16} />
          </button>
          <button aria-label="Apri sessioni" onClick={onOpenSessions} type="button">
            <Clock3 aria-hidden="true" size={16} />
          </button>
          <button aria-label="Nuova conversazione" onClick={onNewSession} type="button">
            <Plus aria-hidden="true" size={16} />
          </button>
        </div>
      </header>

      <div className="scarlet-chat__layout">
        <div className="scarlet-chat__conversation">
          <div
            className={`scarlet-chat__message-scroll${flow.length === 0 ? " is-empty" : ""}`}
            data-testid="chat-message-scroll"
            ref={scrollerRef}
          >
            {flow.length === 0 ? (
              <div className="scarlet-chat__empty">
                <div className="scarlet-chat__empty-avatar">
                  <img alt="Scarlet" src={publicAssetPath("prototype/scarlet-character-v1.png")} />
                </div>
                <p><Sparkles aria-hidden="true" size={14} /> Sono qui.</p>
                <h2>{loading ? "Riapro il nostro filo…" : "Da cosa vuoi iniziare?"}</h2>
                <span>Puoi scrivere liberamente o usare uno spunto.</span>
                <div>
                  {[
                    "Riprendiamo da dove eravamo rimasti",
                    "C'è una cosa di cui vorrei parlarti",
                    "Voglio raccontarti una cosa"
                  ].map((prompt) => (
                    <button key={prompt} onClick={() => setDraft(prompt)} type="button">
                      {prompt}<ArrowRight aria-hidden="true" size={14} />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="scarlet-chat__messages" aria-live="polite">
                {flow.map((block) => (
                  <ChatFlowBubble
                    block={block}
                    key={block.id}
                    onInspect={
                      block.sourceEvents.length > 0 &&
                      block.kind !== "user" &&
                      block.kind !== "answer"
                        ? () => setInspection(block)
                        : undefined
                    }
                  />
                ))}
              </div>
            )}
            <details className="scarlet-chat__mobile-data">
              <summary>Mostra JSON della conversazione</summary>
              <DataJsonPanel compact data={sessionData} title="Payload chat" />
            </details>
          </div>

          <form className="scarlet-chat__composer" data-testid="chat-composer" onSubmit={submitMessage}>
            <label htmlFor="core-chat-message">Scrivi a Scarlet</label>
            <div>
              <textarea
                disabled={sending}
                id="core-chat-message"
                onChange={(event) => setDraft(event.target.value)}
                placeholder={sending ? "Scarlet sta rispondendo…" : "Scrivi un messaggio…"}
                rows={1}
                value={draft}
              />
              <button
                aria-label="Invia messaggio"
                disabled={sending || !draft.trim()}
                type="submit"
              >
                <Send aria-hidden="true" size={18} />
              </button>
            </div>
            <small>
              {sending
                ? "Turno in corso · attività e parole arrivano in tempo reale"
                : "Cronologia reale · live stream con replay persistito"}
            </small>
          </form>
        </div>

        <aside className="scarlet-chat__aside">
          <div className="scarlet-chat__context">
            <p>Continuità disponibile</p>
            <h2>{memories.length} ricordi caricati</h2>
            <span>Il Core seleziona il contesto utile per ogni turno.</span>
            {memories.slice(0, 2).map((memory) => (
              <article key={memory.id}>
                <small>{humanize(memory.type)}</small>
                <p>{memory.content}</p>
              </article>
            ))}
            <button onClick={onOpenMemory} type="button">
              Apri Memoria <ArrowRight aria-hidden="true" size={15} />
            </button>
          </div>
          <DataJsonPanel compact data={sessionData} title="Payload chat" />
        </aside>
      </div>
      <ChatEventDetailModal
        inspection={inspection}
        onClose={() => setInspection(null)}
      />
      {autonomyOpen ? (
        <AutonomyHistoryPanel
          error={autonomyError}
          history={autonomyHistory}
          onClose={() => setAutonomyOpen(false)}
          onRefresh={() => {
            setAutonomyHistory(null);
            setAutonomyError(null);
            void fetchAutonomyHistory()
              .then(setAutonomyHistory)
              .catch((reason: unknown) =>
                setAutonomyError(
                  reason instanceof Error
                    ? reason.message
                    : "Cronologia interiore non disponibile."
                )
              );
          }}
        />
      ) : null}
    </section>
  );
}

function projectConversation(
  events: ScarletStreamEvent[],
  messages: ChatMessage[],
  privateEvidenceUnlocked: boolean,
  liveFrames: Record<string, LiveFrameState>
): ChatFlowBlock[] {
  const terminalTurns = new Set(
    events
      .filter(
        (event) =>
          event.event_type === "turn.completed" ||
          event.event_type === "turn.failed"
      )
      .map((event) => event.turn_id)
      .filter((turnId): turnId is string => typeof turnId === "string")
  );
  const flowEvents = events
    .filter((event) =>
      isConsumerFlowEvent(event, privateEvidenceUnlocked)
    )
    .sort((left, right) => left.seq - right.seq || left.event_id.localeCompare(right.event_id));
  const representedMessageIds = new Set(
    flowEvents
      .map((event) => valueAsRecord(event.payload.message)?.id)
      .filter((id): id is string => typeof id === "string")
  );
  const completedAnswerTurns = new Set(
    flowEvents
      .filter((event) => event.event_type === "assistant.answer.completed")
      .map((event) => event.turn_id)
      .filter((turnId): turnId is string => typeof turnId === "string")
  );
  const thinkingTurns = new Set(
    flowEvents
      .filter((event) => event.event_type === "llm.thinking.started")
      .map((event) => event.turn_id)
      .filter((turnId): turnId is string => typeof turnId === "string")
  );
  const blocks: ChatFlowBlock[] = [];
  const blockIndexes = new Map<string, number>();

  for (const event of flowEvents) {
    if (
      event.event_type === "message.assistant.persisted" &&
      event.turn_id &&
      completedAnswerTurns.has(event.turn_id)
    ) {
      continue;
    }
    if (
      (event.event_type === "llm.request.started" ||
        event.event_type === "llm.response.started") &&
      event.turn_id &&
      thinkingTurns.has(event.turn_id)
    ) {
      continue;
    }

    const projected = projectEvent(event, terminalTurns);
    if (!projected) continue;

    const existingIndex = blockIndexes.get(projected.id);
    if (existingIndex !== undefined) {
      blocks[existingIndex] = {
        ...projected,
        sourceEvents: [
          ...blocks[existingIndex].sourceEvents,
          ...projected.sourceEvents
        ]
      };
      continue;
    }
    blockIndexes.set(projected.id, blocks.length);
    blocks.push(projected);
  }

  for (const frame of Object.values(liveFrames)) {
    if (frame.frame_type === "tool_input_delta") continue;
    const existingIndex = blockIndexes.get(frame.frame_id);
    if (existingIndex !== undefined) {
      const existing = blocks[existingIndex];
      if (existing.status === "live") {
        blocks[existingIndex] = {
          ...existing,
          text:
            frame.frame_type === "thinking_delta"
              ? privateEvidenceUnlocked
                ? compactText(frame.text, 600)
                : existing.text
              : frame.text
        };
      }
      continue;
    }
    const liveBlock: ChatFlowBlock = {
      authoredByScarlet: frame.frame_type === "text_delta",
      eventType: frame.frame_type,
      id: frame.frame_id,
      kind: frame.frame_type === "thinking_delta" ? "reflection" : "note",
      sourceEvents: [],
      status: "live",
      text:
        frame.frame_type === "thinking_delta" && !privateEvidenceUnlocked
          ? "Il pensiero di Scarlet è in corso."
          : compactText(frame.text, frame.frame_type === "thinking_delta" ? 600 : 4000),
      title:
        frame.frame_type === "thinking_delta"
          ? "Scarlet sta pensando"
          : "Nota di Scarlet"
    };
    blockIndexes.set(liveBlock.id, blocks.length);
    blocks.push(liveBlock);
  }

  for (const message of messages) {
    if (representedMessageIds.has(message.id)) continue;
    if (message.role === "user") {
      blocks.push(messageBlock(message, "user"));
    } else if (
      message.role === "assistant" &&
      !blocks.some(
        (block) => block.kind === "answer" && block.text === message.content
      )
    ) {
      blocks.push(messageBlock(message, "answer"));
    }
  }
  return blocks;
}

function isConsumerFlowEvent(
  event: ScarletStreamEvent,
  privateEvidenceUnlocked: boolean
): boolean {
  if (event.event_type === "llm.thinking.captured") {
    return privateEvidenceUnlocked;
  }
  if (event.visibility === "public") return true;
  if (event.visibility === "private") return privateEvidenceUnlocked;
  return (
    CONSUMER_ACTIVITY_EVENT_TYPES.has(event.event_type) ||
    CONSUMER_ACTIVITY_EVENT_PREFIXES.some((prefix) =>
      event.event_type.startsWith(prefix)
    )
  );
}

function projectEvent(
  event: ScarletStreamEvent,
  terminalTurns: Set<string>
): ChatFlowBlock | null {
  const payload = event.payload;
  const message = valueAsRecord(payload.message);
  const text = valueAsString(payload.text);
  const turnIsOpen = Boolean(
    event.turn_id && !terminalTurns.has(event.turn_id)
  );

  if (
    event.visibility === "private" ||
    event.event_type === "llm.thinking.captured"
  ) {
    if (event.event_type === "llm.thinking.captured") {
      return block(
        event,
        "reflection",
        "Pensiero di Scarlet",
        text
          ? compactText(text, 240)
          : "Il provider ha registrato questo passaggio di pensiero senza testo ispezionabile.",
        false,
        false,
        contentLifecycleId("thinking", event)
      );
    }
    return block(
      event,
      "state",
      "Evidenza privata registrata",
      "Il Core ha conservato questo passaggio. Apri i dettagli per verificarne ordine e metadati."
    );
  }

  if (event.event_type === "message.user.persisted" && message) {
    return eventMessageBlock(event, message, "user");
  }
  if (event.event_type === "assistant.answer.completed" && text) {
    return block(
      event,
      "answer",
      "Scarlet",
      text,
      true,
      false,
      contentLifecycleId("content", event)
    );
  }
  if (event.event_type === "message.assistant.persisted" && message) {
    return eventMessageBlock(event, message, "answer");
  }
  if (event.event_type === "assistant.note.emitted" && text) {
    return block(
      event,
      "note",
      "Nota di Scarlet",
      text,
      true,
      false,
      contentLifecycleId("content", event)
    );
  }
  if (event.event_type === "assistant.response.continued" && text) {
    return block(
      event,
      "note",
      "Scarlet continua",
      text,
      true,
      false,
      contentLifecycleId("content", event)
    );
  }
  if (event.event_type === "runtime.context.built") {
    return block(
      event,
      "context",
      "Contesto presente",
      "Il contesto di questo passaggio è stato riallineato."
    );
  }
  if (event.event_type === "memory.context.built") {
    const selected =
      valueAsNumber(payload.selected_count) ??
      (Array.isArray(payload.selected) ? payload.selected.length : 0);
    return block(
      event,
      "memory",
      "Memoria collegata",
      selected
        ? `${selected} ${selected === 1 ? "ricordo è entrato" : "ricordi sono entrati"} nel contesto di questo turno.`
        : "La memoria disponibile è stata verificata per questo turno."
    );
  }
  if (event.event_type === "memory.recent_context.built") {
    const userCount = valueAsNumber(payload.recent_user_count) ?? 0;
    const generalCount = valueAsNumber(payload.recent_general_count) ?? 0;
    const total = userCount + generalCount;
    return block(
      event,
      "memory",
      "Ricordi vicini",
      total
        ? `${total} ${total === 1 ? "ricordo recente è rimasto" : "ricordi recenti sono rimasti"} a portata di pensiero.`
        : "Non ci sono ricordi recenti aggiuntivi per questo passaggio."
    );
  }
  if (event.event_type === "session.continuity.built") {
    const count = valueAsNumber(payload.previous_session_count) ?? 0;
    return block(
      event,
      "context",
      "Fili recenti",
      count
        ? `${count} ${count === 1 ? "conversazione recente è pronta" : "conversazioni recenti sono pronte"} per essere riaperte se servono.`
        : "Questo passaggio comincia senza altri fili recenti da riaprire."
    );
  }
  if (
    event.event_type === "llm.request.started" ||
    event.event_type === "llm.response.started" ||
    event.event_type === "llm.thinking.started"
  ) {
    return block(
      event,
      "reflection",
      "Scarlet sta pensando",
      "Il pensiero di Scarlet è iniziato.",
      false,
      turnIsOpen,
      event.event_type === "llm.thinking.started"
        ? contentLifecycleId("thinking", event)
        : event.event_id
    );
  }
  if (event.event_type === "llm.text.started") {
    return block(
      event,
      "note",
      "Nota di Scarlet",
      "Scarlet sta componendo questo passaggio.",
      true,
      turnIsOpen,
      contentLifecycleId("content", event)
    );
  }
  if (isToolLifecycleEvent(event)) {
    const live =
      turnIsOpen &&
      (event.event_type === "mind.tool_use.started" ||
        event.event_type === "mind.tool_call.requested" ||
        event.event_type === "mind.tool_call.started");
    return block(
      event,
      "action",
      event.event_type === "mind.tool_call.failed"
        ? "Azione non riuscita"
        : live
          ? "Scarlet sta agendo"
          : "Azione completata",
      toolActivityText(payload, event.event_type, live),
      false,
      live,
      toolLifecycleId(event)
    );
  }
  if (event.event_type.startsWith("answer.validation.")) {
    const live =
      turnIsOpen && event.event_type === "answer.validation.started";
    return block(
      event,
      "reflection",
      live
        ? "Scarlet sta rileggendo"
        : event.event_type === "answer.validation.accepted"
          ? "Risposta pronta"
          : "Scarlet sta correggendo",
      live
        ? "Un ultimo controllo tiene insieme la risposta e ciò che è emerso nel turno."
        : event.event_type === "answer.validation.accepted"
          ? "Il controllo finale è completo."
          : "Il primo testo non teneva insieme tutto: Scarlet sta preparando una versione più coerente.",
      false,
      live,
      `answer-validation-${event.turn_id ?? "session"}`
    );
  }
  if (event.event_type.startsWith("organ.focus.")) {
    return block(
      event,
      "state",
      "Fuoco attuale",
      valueAsString(payload.reason) ||
        valueAsString(payload.message) ||
        "Ho aggiornato il punto su cui sto lavorando."
    );
  }
  if (event.event_type.startsWith("organ.affect.")) {
    const details = valueAsRecord(payload.details);
    const emotion = valueAsString(details?.emotion);
    return block(
      event,
      "state",
      "Stato interiore",
      emotion
        ? `Ho riconosciuto ${humanize(emotion)} come parte di questo passaggio.`
        : "Ho registrato come questo passaggio sta orientando il mio stato."
    );
  }
  if (
    event.event_type.startsWith("organ.volition.") ||
    event.event_type === "agent.mode.changed"
  ) {
    return block(
      event,
      "state",
      "Direzione attuale",
      valueAsString(payload.reason) ||
        "Ho aggiornato la direzione con cui sto affrontando questo passaggio."
    );
  }
  if (event.event_type === "turn.failed") {
    return block(
      event,
      "error",
      "Turno non completato",
      failureMessage(payload)
    );
  }
  return null;
}

function toolLifecycleKey(event: ScarletStreamEvent): string {
  return (
    valueAsString(event.payload.provider_tool_use_id) ||
    event.links.tool_call_id ||
    event.links.parent_event_id ||
    event.event_id
  );
}

function toolLifecycleId(event: ScarletStreamEvent): string {
  return `tool-${event.turn_id ?? "session"}-${toolLifecycleKey(event)}`;
}

function isToolLifecycleEvent(event: ScarletStreamEvent): boolean {
  return (
    event.event_type === "mind.tool_use.started" ||
    event.event_type.startsWith("mind.tool_call.")
  );
}

function contentLifecycleId(
  prefix: "thinking" | "content",
  event: ScarletStreamEvent
): string {
  const modelStep = valueAsNumber(event.payload.model_step) ?? 1;
  const index = valueAsNumber(event.payload.index) ?? 0;
  return `${prefix}-${event.turn_id ?? "session"}-${modelStep}-${index}`;
}

function compactText(value: string, limit: number): string {
  if (value.length <= limit) return value;
  return `${value.slice(0, limit).trimEnd()}…`;
}

function toolActivityText(
  payload: Record<string, unknown>,
  eventType: string,
  live: boolean
): string {
  const operation = valueAsRecord(payload.operation);
  const argumentsValue = valueAsRecord(payload.arguments);
  const intent =
    valueAsString(operation?.intent) ||
    valueAsString(argumentsValue?.intent);
  const directOperation = valueAsString(payload.operation);
  const result = valueAsRecord(payload.result_summary);
  const resultOperation = valueAsString(result?.operation);
  const objective =
    intent || directOperation || resultOperation || "aprire la funzione interna necessaria";
  if (intent) {
    if (eventType === "mind.tool_call.failed") {
      return `${intent} Il passaggio non è riuscito.`;
    }
    if (live) {
      return intent;
    }
    const count = valueAsNumber(result?.count);
    const countSuffix =
      count === null
        ? ""
        : ` ${count} ${count === 1 ? "risultato trovato" : "risultati trovati"}.`;
    return `${intent} Passaggio completato.${countSuffix}`;
  }
  const normalizedObjective =
    objective.length > 0
      ? `${objective.charAt(0).toLocaleLowerCase("it")}${objective.slice(1)}`
      : objective;

  if (eventType === "mind.tool_call.failed") {
    return `Il passaggio non è riuscito: ${normalizedObjective}.`;
  }
  if (live) {
    return `Scarlet sta usando una funzione interna: ${normalizedObjective}.`;
  }
  const count = valueAsNumber(result?.count);
  const countSuffix =
    count === null
      ? ""
      : ` Ho ottenuto ${count} ${count === 1 ? "risultato" : "risultati"}.`;
  return `Funzione interna completata: ${normalizedObjective}.${countSuffix}`;
}

function block(
  event: ScarletStreamEvent,
  kind: ChatFlowKind,
  title: string,
  text: string,
  authoredByScarlet = false,
  live = false,
  id = event.event_id
): ChatFlowBlock {
  return {
    authoredByScarlet,
    eventType: event.event_type,
    id,
    kind,
    sourceEvents: [event],
    status: live ? "live" : "completed",
    text,
    title
  };
}

function eventMessageBlock(
  event: ScarletStreamEvent,
  message: Record<string, unknown>,
  kind: "user" | "answer"
): ChatFlowBlock {
  return {
    authoredByScarlet: kind === "answer",
    eventType: event.event_type,
    id: event.event_id,
    kind,
    sourceEvents: [event],
    status: "completed",
    text: valueAsString(message.content),
    title: kind === "user" ? "Tu" : "Scarlet"
  };
}

function messageBlock(message: ChatMessage, kind: "user" | "answer"): ChatFlowBlock {
  return {
    authoredByScarlet: kind === "answer",
    eventType: `message.${message.role}.persisted`,
    id: message.id,
    kind,
    sourceEvents: [],
    status: "completed",
    text: message.content,
    title: kind === "user" ? "Tu" : "Scarlet"
  };
}

function mergeEvents(
  current: ScarletStreamEvent[],
  incoming: ScarletStreamEvent[]
): ScarletStreamEvent[] {
  const byId = new Map(current.map((event) => [event.event_id, event]));
  for (const event of incoming) {
    const existing = byId.get(event.event_id);
    if (existing && JSON.stringify(existing) !== JSON.stringify(event)) {
      throw new Error(`Conflitto evento stream: ${event.event_id}`);
    }
    byId.set(event.event_id, event);
  }
  return [...byId.values()].sort(
    (left, right) => left.seq - right.seq || left.event_id.localeCompare(right.event_id)
  );
}

function ChatFlowBubble({
  block,
  onInspect
}: {
  block: ChatFlowBlock;
  onInspect?: () => void;
}) {
  if (block.kind === "user") {
    return (
      <article className="scarlet-chat__message is-user" data-flow-kind="user">
        <span><UserRound aria-hidden="true" size={16} /></span>
        <div>
          <strong>Tu{block.status === "live" ? " · invio…" : ""}</strong>
          <p>{block.text}</p>
        </div>
      </article>
    );
  }
  if (block.kind === "answer") {
    return (
      <article className="scarlet-chat__message is-scarlet is-answer" data-flow-kind="answer">
        <span><img alt="" src={publicAssetPath("prototype/scarlet-character-v1.png")} /></span>
        <div><strong>Scarlet · risposta</strong><p>{block.text}</p></div>
      </article>
    );
  }
  return (
    <article
      className={`scarlet-chat__flow-block is-${block.kind}${block.authoredByScarlet ? " is-authored" : ""}`}
      data-event-type={block.eventType}
      data-flow-kind={block.kind}
      data-flow-status={block.status}
      onClick={onInspect}
      onKeyDown={(event) => {
        if (!onInspect || (event.key !== "Enter" && event.key !== " ")) {
          return;
        }
        event.preventDefault();
        onInspect();
      }}
      role={onInspect ? "button" : undefined}
      tabIndex={onInspect ? 0 : undefined}
    >
      <span className="scarlet-chat__flow-icon">{flowIcon(block.kind)}</span>
      <div className="scarlet-chat__flow-bubble">
        <header>
          <strong>{block.title}</strong>
          <small>
            {block.status === "live" ? <i aria-hidden="true" /> : <Check aria-hidden="true" size={11} />}
            {block.status === "live" ? "in corso" : "completato"}
          </small>
        </header>
        <p>{block.text}</p>
      </div>
    </article>
  );
}

function flowIcon(kind: ChatFlowKind): ReactNode {
  if (kind === "context") return <Compass aria-hidden="true" size={15} />;
  if (kind === "memory") return <Database aria-hidden="true" size={15} />;
  if (kind === "reflection") return <Brain aria-hidden="true" size={15} />;
  if (kind === "note") return <Quote aria-hidden="true" size={15} />;
  if (kind === "action") return <Wrench aria-hidden="true" size={15} />;
  if (kind === "state") return <Target aria-hidden="true" size={15} />;
  if (kind === "error") return <AlertTriangle aria-hidden="true" size={15} />;
  return <Search aria-hidden="true" size={15} />;
}

function valueAsRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function valueAsString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function valueAsNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function failureMessage(payload: Record<string, unknown>) {
  if (valueAsString(payload.code) === "llm.incomplete_response") {
    return "Non sono riuscita a completare una risposta valida. Puoi riprovare con un nuovo messaggio.";
  }
  return (
    valueAsString(payload.message) ||
    "Il turno si è interrotto prima della risposta."
  );
}

function humanize(value: string) {
  return value.split("_").join(" ");
}

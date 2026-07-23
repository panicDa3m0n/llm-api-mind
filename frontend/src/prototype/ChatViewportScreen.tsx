import {
  AlertTriangle,
  ArrowRight,
  Brain,
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
  fetchAllSessionEventsV2,
  fetchMessages,
  streamTurnV2
} from "../api";
import type {
  ChatMessage,
  ChatSession,
  DashboardMemory,
  ScarletStreamEvent
} from "../types";
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
  status: "completed" | "live";
  text: string;
  title: string;
};

export function ChatViewportScreen({
  memories,
  onDataChanged,
  onNewSession,
  onOpenMemory,
  onOpenSessions,
  onSessionCreated,
  session
}: {
  memories: DashboardMemory[];
  onDataChanged: () => void;
  onNewSession: () => void;
  onOpenMemory: () => void;
  onOpenSessions: () => void;
  onSessionCreated?: (session: ChatSession) => void;
  session: ChatSession | null;
}) {
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(session);
  const [draft, setDraft] = useState("");
  const [events, setEvents] = useState<ScarletStreamEvent[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [optimisticMessage, setOptimisticMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCurrentSession(session);
  }, [session]);

  useEffect(() => {
    if (!currentSession) {
      setEvents([]);
      setMessages([]);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void Promise.all([
      fetchAllSessionEventsV2(currentSession.id),
      fetchMessages(currentSession.id)
    ])
      .then(([nextEvents, nextMessages]) => {
        if (cancelled) return;
        setEvents(mergeEvents([], nextEvents));
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

  const flow = useMemo(() => {
    const projected = projectConversation(events, messages);
    if (optimisticMessage) {
      projected.push({
        eventType: "message.user.pending",
        id: "optimistic-user-message",
        kind: "user",
        status: "live",
        text: optimisticMessage,
        title: "Tu"
      });
    }
    if (error) {
      projected.push({
        eventType: "ui.transport.error",
        id: `transport-error-${error}`,
        kind: "error",
        status: "completed",
        text: error,
        title: "Connessione interrotta"
      });
    }
    return projected;
  }, [error, events, messages, optimisticMessage]);

  useEffect(() => {
    const scroller = scrollerRef.current;
    if (!scroller) return;
    scroller.scrollTop = scroller.scrollHeight;
  }, [flow.length, sending]);

  async function submitMessage(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;

    setSending(true);
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

      await streamTurnV2(targetSession.id, text, undefined, (streamEvent) => {
        received.push(streamEvent);
        setOptimisticMessage(null);
        setEvents((current) => mergeEvents(current, [streamEvent]));
      });

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
      onDataChanged();
    } catch (reason) {
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
        } catch {
          // Keep the original transport error visible.
        }
      }
    } finally {
      setSending(false);
    }
  }

  const sessionData = {
    session: currentSession,
    messages,
    events,
    reducer_contract: {
      deduplicate_by: "event_id",
      order_by: ["seq", "event_id"],
      visibility: "public",
      terminal_events: ["turn.completed", "turn.failed"]
    },
    transport: {
      mode: "core",
      persistence: true,
      schema_version: "scarlet-stream-v2",
      streaming: true
    }
  };

  return (
    <section className="scarlet-screen scarlet-chat" data-testid="chat-screen">
      <header className="scarlet-chat__header">
        <div className="scarlet-chat__header-avatar" aria-hidden="true">
          <img alt="" src="/prototype/scarlet-character-v1.png" /><i />
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
                  <img alt="Scarlet" src="/prototype/scarlet-character-v1.png" />
                </div>
                <p><Sparkles aria-hidden="true" size={14} /> Sono qui.</p>
                <h2>{loading ? "Riapro il nostro filo…" : "Da cosa vuoi iniziare?"}</h2>
                <span>Puoi scrivere liberamente o usare uno spunto.</span>
                <div>
                  {[
                    "Riprendiamo il progetto",
                    "Organizziamo le prossime attività",
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
                {flow.map((block) => <ChatFlowBubble block={block} key={block.id} />)}
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
                ? "Turno in corso · eventi persistiti in tempo reale"
                : "Cronologia reale · stream Scarlet V2"}
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
    </section>
  );
}

function projectConversation(
  events: ScarletStreamEvent[],
  messages: ChatMessage[]
): ChatFlowBlock[] {
  const publicEvents = events
    .filter(
      (event) =>
        event.visibility === "public" || event.event_type === "turn.failed"
    )
    .sort((left, right) => left.seq - right.seq || left.event_id.localeCompare(right.event_id));
  const representedMessageIds = new Set(
    publicEvents
      .map((event) => valueAsRecord(event.payload.message)?.id)
      .filter((id): id is string => typeof id === "string")
  );
  const completedAnswerTurns = new Set(
    publicEvents
      .filter((event) => event.event_type === "assistant.answer.completed")
      .map((event) => event.turn_id)
      .filter((turnId): turnId is string => typeof turnId === "string")
  );
  const blocks = publicEvents
    .map((event) =>
      event.event_type === "message.assistant.persisted" &&
      event.turn_id &&
      completedAnswerTurns.has(event.turn_id)
        ? null
        : projectEvent(event)
    )
    .filter((block): block is ChatFlowBlock => block !== null);

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

function projectEvent(event: ScarletStreamEvent): ChatFlowBlock | null {
  const payload = event.payload;
  const message = valueAsRecord(payload.message);
  const text = valueAsString(payload.text);

  if (event.event_type === "message.user.persisted" && message) {
    return eventMessageBlock(event, message, "user");
  }
  if (event.event_type === "assistant.answer.completed" && text) {
    return block(event, "answer", "Scarlet", text, true);
  }
  if (event.event_type === "message.assistant.persisted" && message) {
    return eventMessageBlock(event, message, "answer");
  }
  if (event.event_type === "assistant.note.emitted" && text) {
    return block(event, "note", "Nota di Scarlet", text, true);
  }
  if (event.event_type === "runtime.context.built") {
    return block(
      event,
      "context",
      "Contesto presente",
      "Ho riallineato profilo, sessione e contesto runtime per questo passaggio."
    );
  }
  if (event.event_type === "memory.context.built") {
    const selected = Array.isArray(payload.selected) ? payload.selected.length : 0;
    return block(
      event,
      "memory",
      "Memoria collegata",
      selected
        ? `Ho collegato ${selected} ${selected === 1 ? "ricordo utile" : "ricordi utili"} a questo turno.`
        : "Ho verificato la memoria disponibile per questo turno."
    );
  }
  if (
    event.event_type === "llm.response.started" ||
    event.event_type === "llm.thinking.started"
  ) {
    return block(
      event,
      "reflection",
      "Riflessione",
      "Sto preparando la risposta e separando ciò che so da ciò che devo verificare.",
      false,
      event.phase === "streaming"
    );
  }
  if (event.event_type.startsWith("mind.tool_call.")) {
    const operation =
      valueAsString(payload.operation) ||
      valueAsString(payload.tool_name) ||
      "azione sul sistema";
    const summary = valueAsString(payload.result_summary);
    return block(
      event,
      "action",
      event.phase === "failed" ? "Azione non riuscita" : "Azione di Scarlet",
      summary || `${operation} · ${phaseLabel(event.phase)}`,
      false,
      event.phase === "executing"
    );
  }
  if (event.event_type.startsWith("organ.focus.")) {
    return block(
      event,
      "state",
      "Fuoco attuale",
      valueAsString(payload.message) || "Ho aggiornato il punto su cui sto lavorando."
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

function block(
  event: ScarletStreamEvent,
  kind: ChatFlowKind,
  title: string,
  text: string,
  authoredByScarlet = false,
  live = false
): ChatFlowBlock {
  return {
    authoredByScarlet,
    eventType: event.event_type,
    id: event.event_id,
    kind,
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

function ChatFlowBubble({ block }: { block: ChatFlowBlock }) {
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
        <span><img alt="" src="/prototype/scarlet-character-v1.png" /></span>
        <div><strong>Scarlet · risposta</strong><p>{block.text}</p></div>
      </article>
    );
  }
  return (
    <article
      className={`scarlet-chat__flow-block is-${block.kind}${block.authoredByScarlet ? " is-authored" : ""}`}
      data-event-type={block.eventType}
      data-flow-kind={block.kind}
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

function failureMessage(payload: Record<string, unknown>) {
  if (valueAsString(payload.code) === "llm.incomplete_response") {
    return "Non sono riuscita a completare una risposta valida. Puoi riprovare con un nuovo messaggio.";
  }
  return (
    valueAsString(payload.message) ||
    "Il turno si è interrotto prima della risposta."
  );
}

function phaseLabel(phase: ScarletStreamEvent["phase"]) {
  if (phase === "executing" || phase === "streaming") return "in corso";
  if (phase === "failed") return "non riuscita";
  return "completata";
}

function humanize(value: string) {
  return value.split("_").join(" ");
}

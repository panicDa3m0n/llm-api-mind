import {
  Activity,
  Bot,
  Braces,
  Clock3,
  Database,
  MessageSquarePlus,
  RefreshCcw,
  Send,
  UserRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { createSession, fetchHealth, fetchMessages, fetchTraces, sendTurn } from "./api";
import type { ChatMessage, ChatSession, ChatTurn, TraceItem } from "./types";

type Status = {
  label: string;
  tone: "idle" | "busy" | "ok" | "error";
};

export function App() {
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [status, setStatus] = useState<Status>({ label: "Ready", tone: "idle" });
  const [health, setHealth] = useState<string>("checking");
  const [lastTurn, setLastTurn] = useState<ChatTurn | null>(null);
  const [maxTokens, setMaxTokens] = useState("4096");

  useEffect(() => {
    fetchHealth()
      .then((result) => setHealth(`${result.status} · ${result.model}`))
      .catch(() => setHealth("offline"));
  }, []);

  const traceSummary = useMemo(() => {
    const request = traces.find((trace) => trace.kind === "llm.request");
    const response = traces.find((trace) => trace.kind === "llm.response");
    return {
      request,
      response,
      usage: lastTurn?.usage ?? response?.payload.usage
    };
  }, [lastTurn, traces]);

  async function ensureSession(): Promise<ChatSession> {
    if (session) {
      return session;
    }
    const created = await createSession("Baseline trace");
    setSession(created);
    setMessages([]);
    setTraces([]);
    setSelectedTurnId(null);
    return created;
  }

  async function startSession() {
    setStatus({ label: "Creating session", tone: "busy" });
    try {
      const created = await createSession("Baseline trace");
      setSession(created);
      setMessages([]);
      setTraces([]);
      setSelectedTurnId(null);
      setLastTurn(null);
      setStatus({ label: "Session ready", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function refreshMessages() {
    if (!session) {
      return;
    }
    setStatus({ label: "Refreshing", tone: "busy" });
    try {
      setMessages(await fetchMessages(session.id));
      setStatus({ label: "Messages loaded", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  async function loadTraces(turnId: string) {
    setSelectedTurnId(turnId);
    setStatus({ label: "Loading traces", tone: "busy" });
    try {
      setTraces(await fetchTraces(turnId));
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
    setStatus({ label: "Sending", tone: "busy" });

    try {
      const activeSession = await ensureSession();
      const tokenValue = Number(maxTokens);
      const turn = await sendTurn(
        activeSession.id,
        message,
        Number.isFinite(tokenValue) && tokenValue > 0 ? tokenValue : undefined
      );
      setSession(turn.session);
      setLastTurn(turn);
      setMessages((current) => [...current, turn.user_message, turn.assistant_message]);
      setSelectedTurnId(turn.turn_id);
      setTraces(await fetchTraces(turn.turn_id));
      setStatus({ label: "Turn complete", tone: "ok" });
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Session">
        <div className="brand">
          <div className="brand-mark">
            <Activity size={18} aria-hidden="true" />
          </div>
          <div>
            <h1>LLM API Mind</h1>
            <p>{health}</p>
          </div>
        </div>

        <div className="session-block">
          <div className="section-label">Session</div>
          <code>{session?.id ?? "none"}</code>
          <button className="command" type="button" onClick={startSession}>
            <MessageSquarePlus size={16} aria-hidden="true" />
            <span>New</span>
          </button>
        </div>

        <div className="session-block">
          <div className="section-label">Runtime</div>
          <label className="field-label" htmlFor="max-tokens">
            Max tokens
          </label>
          <input
            id="max-tokens"
            className="number-input"
            inputMode="numeric"
            value={maxTokens}
            onChange={(event) => setMaxTokens(event.target.value)}
          />
          <button
            className="command"
            type="button"
            onClick={refreshMessages}
            disabled={!session}
            title="Refresh messages"
          >
            <RefreshCcw size={16} aria-hidden="true" />
            <span>Refresh</span>
          </button>
        </div>

        <div className={`status ${status.tone}`}>{status.label}</div>
      </aside>

      <section className="chat-pane" aria-label="Chat">
        <div className="pane-header">
          <div>
            <div className="section-label">Chat</div>
            <h2>{session?.title ?? "Baseline trace"}</h2>
          </div>
          {lastTurn ? (
            <div className="turn-chip">
              <Clock3 size={15} aria-hidden="true" />
              <span>{lastTurn.latency_ms} ms</span>
            </div>
          ) : null}
        </div>

        <div className="messages" aria-live="polite">
          {messages.length === 0 ? (
            <div className="empty-state">No messages</div>
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
                    <span>{message.role}</span>
                    {message.turn_id ? (
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => loadTraces(message.turn_id!)}
                      >
                        trace
                      </button>
                    ) : null}
                  </div>
                  <p>{message.content}</p>
                </div>
              </article>
            ))
          )}
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Message"
            rows={3}
          />
          <button className="send-button" type="submit" disabled={!prompt.trim()}>
            <Send size={18} aria-hidden="true" />
            <span>Send</span>
          </button>
        </form>
      </section>

      <aside className="trace-pane" aria-label="Trace">
        <div className="pane-header compact">
          <div>
            <div className="section-label">Trace</div>
            <h2>{selectedTurnId ?? "none"}</h2>
          </div>
          <Database size={18} aria-hidden="true" />
        </div>

        <div className="metrics">
          <Metric label="Traces" value={String(traces.length)} />
          <Metric label="Input" value={metricValue(traceSummary.usage, "input_tokens")} />
          <Metric label="Output" value={metricValue(traceSummary.usage, "output_tokens")} />
        </div>

        <div className="trace-list">
          {traces.length === 0 ? (
            <div className="empty-state">No trace</div>
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
      </aside>
    </main>
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

function metricValue(source: unknown, key: string): string {
  if (!source || typeof source !== "object") {
    return "n/a";
  }
  const value = (source as Record<string, unknown>)[key];
  return typeof value === "number" || typeof value === "string" ? String(value) : "n/a";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}

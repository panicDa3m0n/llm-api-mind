import {
  Activity,
  Bot,
  Braces,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  MessageSquarePlus,
  RefreshCcw,
  Send,
  Wrench,
  UserRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { createSession, fetchHealth, fetchMessages, fetchTraces, streamTurn } from "./api";
import type { AgentStep, ChatMessage, ChatSession, ChatTurn, StreamEvent, TraceItem } from "./types";

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
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

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
      setAgentSteps([]);
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
      setAgentSteps([]);
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
      const loaded = await fetchTraces(turnId);
      setTraces(loaded);
      setAgentSteps(stepsFromTraces(loaded));
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
    setAgentSteps([]);

    try {
      const activeSession = await ensureSession();
      const tokenValue = Number(maxTokens);
      await streamTurn(
        activeSession.id,
        message,
        Number.isFinite(tokenValue) && tokenValue > 0 ? tokenValue : undefined,
        (event) => handleStreamEvent(event)
      );
    } catch (error) {
      setStatus({ label: errorMessage(error), tone: "error" });
      setAgentSteps((current) => [
        ...current,
        {
          id: `error-${Date.now()}`,
          kind: "runtime",
          title: "Stream error",
          body: errorMessage(error),
          status: "error"
        }
      ]);
    } finally {
      setIsStreaming(false);
    }
  }

  function handleStreamEvent(event: StreamEvent) {
    switch (event.type) {
      case "turn_started": {
        const userMessage = event.data.user_message as ChatMessage;
        const turnId = String(event.data.turn_id);
        setSelectedTurnId(turnId);
        setTraces([]);
        setMessages((current) => [
          ...current,
          userMessage,
          {
            id: `stream-assistant-${turnId}`,
            session_id: userMessage.session_id,
            turn_id: turnId,
            role: "assistant",
            content: "",
            created_at: new Date().toISOString(),
            metadata: { streaming: true }
          }
        ]);
        upsertStep({
          id: "runtime-start",
          kind: "runtime",
          title: "Turn started",
          body: turnId,
          status: "done"
        });
        break;
      }
      case "model_request":
        upsertStep({
          id: `model-${String(event.data.step ?? "1")}`,
          kind: "runtime",
          title: "Model request",
          body: formatJson(event.data),
          status: "active"
        });
        break;
      case "thinking_delta":
        appendStepText("thinking-live", {
          kind: "thinking",
          title: "Provider thinking block",
          text: String(event.data.text ?? "")
        });
        break;
      case "tool_input_delta":
        appendStepText("tool-input-live", {
          kind: "tool",
          title: "Tool input stream",
          text: String(event.data.partial_json ?? "")
        });
        break;
      case "tool_call":
        upsertStep({
          id: `tool-call-${String(event.data.provider_tool_use_id ?? Date.now())}`,
          kind: "tool",
          title: `Tool call: ${String(event.data.tool_name ?? "tool")}`,
          body: formatJson(event.data.arguments ?? event.data),
          status: "done"
        });
        break;
      case "tool_result":
        upsertStep({
          id: `tool-result-${String(event.data.tool_call_id ?? Date.now())}`,
          kind: "result",
          title: `Tool result: ${String(event.data.tool_name ?? "mind_api")}`,
          body: formatJson(event.data.result ?? event.data),
          status: event.data.status === "error" ? "error" : "done"
        });
        break;
      case "text_delta": {
        const delta = String(event.data.text ?? "");
        setMessages((current) =>
          current.map((message) =>
            message.id.startsWith("stream-assistant-")
              ? { ...message, content: `${message.content}${delta}` }
              : message
          )
        );
        appendStepText("answer-live", {
          kind: "answer",
          title: "Final answer stream",
          text: delta
        });
        break;
      }
      case "model_stop":
        upsertStep({
          id: `model-stop-${Date.now()}`,
          kind: "runtime",
          title: "Model stop",
          body: String(event.data.stop_reason ?? "unknown"),
          status: "done"
        });
        break;
      case "turn_complete": {
        const turn = event.data as unknown as ChatTurn;
        setSession(turn.session);
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
        setAgentSteps((current) =>
          current.map((step) =>
            step.status === "active" ? { ...step, status: "done" } : step
          )
        );
        void fetchTraces(turn.turn_id).then((loaded) => {
          setTraces(loaded);
          setAgentSteps((current) => mergeSteps(current, stepsFromTraces(loaded)));
        });
        break;
      }
      case "error":
        setStatus({ label: String(event.data.message ?? "Stream error"), tone: "error" });
        upsertStep({
          id: `stream-error-${Date.now()}`,
          kind: "runtime",
          title: String(event.data.code ?? "Stream error"),
          body: String(event.data.message ?? ""),
          status: "error"
        });
        break;
      default:
        upsertStep({
          id: `event-${event.type}-${Date.now()}`,
          kind: "runtime",
          title: event.type,
          body: formatJson(event.data),
          status: "done"
        });
    }
  }

  function upsertStep(next: AgentStep) {
    setAgentSteps((current) => {
      const index = current.findIndex((step) => step.id === next.id);
      if (index === -1) {
        return [...current, next];
      }
      return current.map((step) => (step.id === next.id ? { ...step, ...next } : step));
    });
  }

  function appendStepText(
    id: string,
    next: { kind: AgentStep["kind"]; title: string; text: string }
  ) {
    setAgentSteps((current) => {
      const index = current.findIndex((step) => step.id === id);
      if (index === -1) {
        return [
          ...current,
          {
            id,
            kind: next.kind,
            title: next.title,
            body: next.text,
            status: "active"
          }
        ];
      }
      return current.map((step) =>
        step.id === id ? { ...step, body: `${step.body}${next.text}` } : step
      );
    });
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
          <button className="send-button" type="submit" disabled={!prompt.trim() || isStreaming}>
            <Send size={18} aria-hidden="true" />
            <span>{isStreaming ? "Live" : "Send"}</span>
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

        <AgentTimeline steps={agentSteps} />

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

function AgentTimeline({ steps }: { steps: AgentStep[] }) {
  return (
    <section className="agent-timeline" aria-label="Agent timeline">
      <div className="timeline-header">
        <div>
          <div className="section-label">Agent loop</div>
          <h3>Streaming timeline</h3>
        </div>
        <CheckCircle2 size={17} aria-hidden="true" />
      </div>
      {steps.length === 0 ? (
        <div className="timeline-empty">No agent events</div>
      ) : (
        <div className="timeline-list">
          {steps.map((step) => (
            <article className={`timeline-step ${step.kind} ${step.status}`} key={step.id}>
              <div className="step-icon">{stepIcon(step.kind)}</div>
              <div className="step-body">
                <div className="step-title">
                  <span>{step.title}</span>
                  <small>{step.status}</small>
                </div>
                <pre>{step.body || "..."}</pre>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function stepIcon(kind: AgentStep["kind"]) {
  if (kind === "thinking") {
    return <BrainCircuit size={15} aria-hidden="true" />;
  }
  if (kind === "tool" || kind === "result") {
    return <Wrench size={15} aria-hidden="true" />;
  }
  if (kind === "answer") {
    return <Bot size={15} aria-hidden="true" />;
  }
  return <Activity size={15} aria-hidden="true" />;
}

function stepsFromTraces(traces: TraceItem[]): AgentStep[] {
  const steps: AgentStep[] = [];
  for (const trace of traces) {
    if (trace.kind === "mind.tool_call") {
      steps.push({
        id: `trace-tool-${trace.id}`,
        kind: "tool",
        title: `Tool call: ${String(trace.payload.tool_name ?? "mind_api")}`,
        body: formatJson(trace.payload.arguments ?? {}),
        status: trace.payload.status === "error" ? "error" : "done"
      });
      steps.push({
        id: `trace-result-${trace.id}`,
        kind: "result",
        title: "Tool result",
        body: formatJson(trace.payload.result ?? {}),
        status: trace.payload.status === "error" ? "error" : "done"
      });
    }

    if (trace.kind === "llm.response") {
      for (const block of providerBlocks(trace.payload)) {
        if (block.type === "thinking" && typeof block.thinking === "string") {
          steps.push({
            id: `trace-thinking-${trace.id}-${steps.length}`,
            kind: "thinking",
            title: "Provider thinking block",
            body: block.thinking,
            status: "done"
          });
        }
        if (block.type === "text" && typeof block.text === "string") {
          steps.push({
            id: `trace-answer-${trace.id}-${steps.length}`,
            kind: "answer",
            title: "Final answer",
            body: block.text,
            status: "done"
          });
        }
      }
    }
  }
  return steps;
}

function providerBlocks(payload: Record<string, unknown>): Array<Record<string, unknown>> {
  const blocks: Array<Record<string, unknown>> = [];
  const rawMessages = payload.raw_provider_messages;
  if (Array.isArray(rawMessages)) {
    for (const message of rawMessages) {
      if (message && typeof message === "object") {
        const content = (message as Record<string, unknown>).content;
        if (Array.isArray(content)) {
          blocks.push(...(content.filter(isRecord) as Array<Record<string, unknown>>));
        }
      }
    }
  }
  const rawContent = payload.raw_content;
  if (Array.isArray(rawContent)) {
    blocks.push(...(rawContent.filter(isRecord) as Array<Record<string, unknown>>));
  }
  return blocks;
}

function mergeSteps(current: AgentStep[], incoming: AgentStep[]): AgentStep[] {
  const seen = new Set(current.map((step) => step.id));
  return [...current, ...incoming.filter((step) => !seen.has(step.id))];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object";
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

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Unexpected error";
}

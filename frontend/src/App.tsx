import {
  Activity,
  Bot,
  Braces,
  BrainCircuit,
  Clock3,
  Database,
  MessageSquarePlus,
  RefreshCcw,
  Send,
  UserRound,
  Wrench
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { createSession, fetchHealth, fetchMessages, fetchTraces, streamTurn } from "./api";
import type {
  AgentStep,
  ChatMessage,
  ChatSession,
  ChatTurn,
  StreamEvent,
  TraceItem
} from "./types";

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
  const [turnSteps, setTurnSteps] = useState<Record<string, AgentStep[]>>({});
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((result) => setHealth(`${result.status} - ${result.model}`))
      .catch(() => setHealth("offline"));
  }, []);

  const traceSummary = useMemo(() => {
    const response = traces.find((trace) => trace.kind === "llm.response");
    return {
      usage: lastTurn?.usage ?? response?.payload.usage
    };
  }, [lastTurn, traces]);

  async function ensureSession(): Promise<ChatSession> {
    if (session) {
      return session;
    }
    const created = await createSession("Agent stream");
    setSession(created);
    setMessages([]);
    setTraces([]);
    setTurnSteps({});
    setSelectedTurnId(null);
    return created;
  }

  async function startSession() {
    setStatus({ label: "Creating session", tone: "busy" });
    try {
      const created = await createSession("Agent stream");
      setSession(created);
      setMessages([]);
      setTraces([]);
      setTurnSteps({});
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
      setTurnSteps((current) => ({
        ...current,
        [turnId]: stepsFromTraces(loaded)
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
      const tokenValue = Number(maxTokens);
      await streamTurn(
        activeSession.id,
        message,
        Number.isFinite(tokenValue) && tokenValue > 0 ? tokenValue : undefined,
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
        upsertStep(turnId, {
          id: `tool-call-${String(event.data.provider_tool_use_id ?? Date.now())}`,
          kind: "tool",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: `Tool call: ${String(event.data.tool_name ?? "tool")}`,
          body: formatJson(event.data.arguments ?? event.data),
          status: "done"
        });
        break;

      case "tool_result":
        upsertStep(turnId, {
          id: `tool-result-${String(event.data.tool_call_id ?? Date.now())}`,
          kind: "result",
          seq: eventSeq(event),
          modelStep: numericValue(event.data.model_step),
          title: `Tool result: ${String(event.data.tool_name ?? "mind_api")}`,
          body: formatJson(event.data.result ?? event.data),
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
        setMessages((current) =>
          current.map((message) =>
            message.id === `stream-assistant-${turnId}`
              ? { ...message, content: `${message.content}${delta}` }
              : message
          )
        );
        appendStepText(
          turnId,
          `answer-live-${String(event.data.model_step ?? "1")}-${String(
            event.data.index ?? "0"
          )}`,
          {
            kind: "answer",
            seq: eventSeq(event),
            modelStep: numericValue(event.data.model_step),
            title: "Final answer stream",
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
        void fetchTraces(turn.turn_id).then((loaded) => setTraces(loaded));
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
            <h2>{session?.title ?? "Agent stream"}</h2>
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
            <div className="section-label">Trace log</div>
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

function AgentTimeline({ steps }: { steps: AgentStep[] }) {
  if (steps.length === 0) {
    return null;
  }

  const ordered = sortSteps(steps);
  return (
    <section className="agent-turn" aria-label="Agent turn operations">
      <div className="agent-turn-header">
        <div>
          <div className="section-label">Agent turn</div>
          <h3>Ordered operations</h3>
        </div>
        <span>{ordered.length} steps</span>
      </div>
      <ol className="operation-list">
        {ordered.map((step, index) => (
          <li className={`operation-step ${step.kind} ${step.status}`} key={step.id}>
            <div className="operation-index">{index + 1}</div>
            <div className="operation-icon">{stepIcon(step.kind)}</div>
            <div className="operation-body">
              <div className="operation-title">
                <span>{step.title}</span>
                <div className="operation-badges">
                  {step.modelStep ? <small>model {step.modelStep}</small> : null}
                  <small>{step.status}</small>
                </div>
              </div>
              <pre>{step.body || "..."}</pre>
            </div>
          </li>
        ))}
      </ol>
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
  let seq = 1;

  for (const trace of traces) {
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
      steps.push({
        id: `trace-tool-${trace.id}`,
        kind: "tool",
        seq: seq++,
        title: `Tool call: ${String(trace.payload.tool_name ?? "mind_api")}`,
        body: formatJson(trace.payload.arguments ?? {}),
        status: trace.payload.status === "error" ? "error" : "done"
      });
      steps.push({
        id: `trace-result-${trace.id}`,
        kind: "result",
        seq: seq++,
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
            seq: seq++,
            title: "Provider thinking block",
            body: block.thinking,
            status: "done"
          });
        }
        if (block.type === "text" && typeof block.text === "string") {
          steps.push({
            id: `trace-answer-${trace.id}-${steps.length}`,
            kind: "answer",
            seq: seq++,
            title: "Final answer",
            body: block.text,
            status: "done"
          });
        }
      }
    }
  }

  return sortSteps(steps);
}

function providerBlocks(payload: Record<string, unknown>): Array<Record<string, unknown>> {
  const blocks: Array<Record<string, unknown>> = [];
  const rawMessages = payload.raw_provider_messages;
  if (Array.isArray(rawMessages)) {
    for (const message of rawMessages) {
      if (isRecord(message)) {
        const content = message.content;
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

function sortSteps(steps: AgentStep[]): AgentStep[] {
  return [...steps].sort((left, right) => left.seq - right.seq);
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

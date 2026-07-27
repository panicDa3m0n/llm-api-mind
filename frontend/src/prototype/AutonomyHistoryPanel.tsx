import {
  BrainCircuit,
  ChevronDown,
  Clock3,
  Moon,
  RefreshCcw,
  Sparkles,
  Wrench,
  X
} from "lucide-react";
import type { ReactNode } from "react";

import type {
  AutonomousCycle,
  AutonomyHistory,
  CognitiveEvent
} from "../types";

export function AutonomyHistoryPanel({
  error,
  history,
  onClose,
  onRefresh
}: {
  error: string | null;
  history: AutonomyHistory | null;
  onClose: () => void;
  onRefresh: () => void;
}) {
  return (
    <div className="scarlet-autonomy-layer">
      <button
        aria-label="Chiudi la continuità interiore"
        className="scarlet-autonomy-layer__backdrop"
        onClick={onClose}
        type="button"
      />
      <section
        aria-label="Cronologia della cognizione autonoma di Scarlet"
        aria-modal="true"
        className="scarlet-autonomy"
        role="dialog"
      >
        <header className="scarlet-autonomy__header">
          <span className="scarlet-autonomy__mark">
            <BrainCircuit aria-hidden="true" size={20} />
          </span>
          <div>
            <p>Continuità interiore</p>
            <h2>Cosa ha vissuto Scarlet</h2>
            <span>Note, scelte e passaggi tra un incontro e l'altro.</span>
          </div>
          <nav aria-label="Azioni cronologia interiore">
            <button aria-label="Aggiorna cronologia" onClick={onRefresh} type="button">
              <RefreshCcw aria-hidden="true" size={16} />
            </button>
            <button aria-label="Chiudi cronologia" onClick={onClose} type="button">
              <X aria-hidden="true" size={18} />
            </button>
          </nav>
        </header>

        <div className="scarlet-autonomy__scroll">
          {error ? (
            <EmptyState
              icon={<RefreshCcw aria-hidden="true" size={23} />}
              text={error}
              title="Non riesco ancora a riaprire questo filo."
            />
          ) : !history ? (
            <EmptyState
              icon={<BrainCircuit aria-hidden="true" size={23} />}
              text="Raccolgo i passaggi conservati dal sistema."
              title="Sto riaprendo il suo spazio interiore."
            />
          ) : history.cycles.length === 0 ? (
            <EmptyState
              icon={<Moon aria-hidden="true" size={23} />}
              text="La prima attivazione verrà conservata qui."
              title="Nessun ciclo ancora vissuto."
            />
          ) : (
            <div className="scarlet-autonomy__timeline">
              {history.cycles.map((cycle) => (
                <AutonomyCycleEntry cycle={cycle} key={cycle.activation.id} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function EmptyState({
  icon,
  text,
  title
}: {
  icon: ReactNode;
  text: string;
  title: string;
}) {
  return (
    <div className="scarlet-autonomy__empty">
      <span>{icon}</span>
      <strong>{title}</strong>
      <p>{text}</p>
    </div>
  );
}

function AutonomyCycleEntry({ cycle }: { cycle: AutonomousCycle }) {
  const checkpoint = cycle.messages.find(
    (message) => message.role === "assistant"
  );
  const notes = cycle.events.filter(
    (event) => event.type === "assistant.note.emitted"
  );
  const thinking = cycle.events.filter(
    (event) => event.type === "llm.thinking.captured"
  );
  const startedTools = cycle.events.filter(
    (event) => event.type === "mind.tool_call.started"
  );

  return (
    <article className={`scarlet-autonomy-cycle is-${cycle.activation.status}`}>
      <header>
        <span>
          <Clock3 aria-hidden="true" size={14} />
          {formatCycleDate(cycle.activation.scheduled_at)}
        </span>
        <strong>{cycleTitle(cycle.activation.status)}</strong>
        <small>
          {cycle.activation.active_mode ??
            (cycle.activation.status === "running" ? "in corso" : "interno")}
        </small>
      </header>

      <div className="scarlet-autonomy-cycle__thread">
        {notes.map((event) => (
          <NarrativeBubble event={event} key={event.id} />
        ))}
        {startedTools.map((event) => (
          <ToolBubble event={event} key={event.id} />
        ))}
        {checkpoint ? (
          <div className="scarlet-autonomy-bubble is-checkpoint">
            <span>
              <Sparkles aria-hidden="true" size={13} />
              Checkpoint interiore
            </span>
            <p>{checkpoint.content}</p>
          </div>
        ) : null}
      </div>

      {thinking.length > 0 ? (
        <details className="scarlet-autonomy-cycle__thinking">
          <summary>
            <BrainCircuit aria-hidden="true" size={14} />
            Pensiero conservato
            <ChevronDown aria-hidden="true" size={14} />
          </summary>
          {thinking.map((event) => (
            <p key={event.id}>
              {stringValue(event.payload.text) ??
                "Passaggio presente nel trace senza testo proiettabile."}
            </p>
          ))}
        </details>
      ) : null}

      {cycle.tool_calls.length > 0 ? (
        <details className="scarlet-autonomy-cycle__technical">
          <summary>
            {cycle.tool_calls.length} azioni cognitive
            <ChevronDown aria-hidden="true" size={14} />
          </summary>
          {cycle.tool_calls.map((tool) => (
            <div key={tool.id}>
              <strong>
                {stringValue(tool.arguments.command) ?? tool.tool_name}
              </strong>
              <span>{tool.status}</span>
            </div>
          ))}
        </details>
      ) : null}
    </article>
  );
}

function NarrativeBubble({ event }: { event: CognitiveEvent }) {
  return (
    <div className="scarlet-autonomy-bubble is-note">
      <span>
        <Sparkles aria-hidden="true" size={13} />
        Nota di Scarlet
      </span>
      <p>{stringValue(event.payload.text) ?? "Un passaggio è stato conservato."}</p>
    </div>
  );
}

function ToolBubble({ event }: { event: CognitiveEvent }) {
  const operation = recordValue(event.payload.operation);
  const command =
    stringValue(operation?.command) ??
    stringValue(event.payload.command) ??
    "Scarlet ha aperto una parte della sua mente.";
  const intent =
    stringValue(operation?.intent) ?? stringValue(event.payload.intent);

  return (
    <div className="scarlet-autonomy-bubble is-tool">
      <span>
        <Wrench aria-hidden="true" size={13} />
        Azione cognitiva
      </span>
      <p>{intent ?? command}</p>
      {intent ? <small>{command}</small> : null}
    </div>
  );
}

function cycleTitle(status: string): string {
  if (status === "running") return "Scarlet sta riflettendo";
  if (status === "completed") return "Ciclo concluso";
  if (status === "deferred") return "Ha dato spazio alla conversazione";
  if (status === "pending") return "Un nuovo momento si avvicina";
  return "Ciclo non completato";
}

function formatCycleDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short"
  }).format(date);
}

function recordValue(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

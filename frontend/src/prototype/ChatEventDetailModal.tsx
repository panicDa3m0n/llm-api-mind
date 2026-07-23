import { Activity, LockKeyhole, X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import type { ScarletStreamEvent } from "../types";

export type ChatEventInspection = {
  eventType: string;
  kind: string;
  sourceEvents: ScarletStreamEvent[];
  text: string;
  title: string;
};

export function ChatEventDetailModal({
  inspection,
  onClose
}: {
  inspection: ChatEventInspection | null;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const receipts = useMemo(
    () => inspection?.sourceEvents.map(eventReceipt) ?? [],
    [inspection]
  );
  const facts = useMemo(
    () => (inspection ? inspectionFacts(inspection) : []),
    [inspection]
  );

  useEffect(() => {
    if (!inspection) return;
    closeRef.current?.focus();
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [inspection, onClose]);

  if (!inspection) return null;

  const hasPrivateEvidence = inspection.sourceEvents.some(
    (event) => isProtectedStreamEvent(event)
  );

  return (
    <div
      aria-labelledby="chat-event-detail-title"
      aria-modal="true"
      className="scarlet-event-detail"
      data-testid="chat-event-detail-modal"
      onMouseDown={(event) => {
        if (event.currentTarget === event.target) onClose();
      }}
      role="dialog"
    >
      <section className="scarlet-event-detail__dialog">
        <header className="scarlet-event-detail__header">
          <span aria-hidden="true"><Activity size={19} /></span>
          <div>
            <p>{inspection.eventType}</p>
            <h2 id="chat-event-detail-title">{inspection.title}</h2>
          </div>
          <button
            aria-label="Chiudi dettagli evento"
            onClick={onClose}
            ref={closeRef}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>

        <div className="scarlet-event-detail__body">
          <p className="scarlet-event-detail__summary">{inspection.text}</p>

          {hasPrivateEvidence ? (
            <div className="scarlet-event-detail__privacy">
              <LockKeyhole aria-hidden="true" size={15} />
              <span>
                Evidenza privata sbloccata. Presenza, ordine e metadati sono
                verificabili; il testo del ragionamento interno resta oscurato.
              </span>
            </div>
          ) : null}

          <dl className="scarlet-event-detail__facts">
            {facts.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>

          <section className="scarlet-event-detail__receipt">
            <header>
              <div>
                <p>Ricevuta Scarlet Stream V2</p>
                <span>
                  {inspection.sourceEvents.length}{" "}
                  {inspection.sourceEvents.length === 1 ? "evento" : "eventi"}{" "}
                  persistiti
                </span>
              </div>
            </header>
            <pre>{JSON.stringify(receipts, null, 2)}</pre>
          </section>
        </div>
      </section>
    </div>
  );
}

function inspectionFacts(
  inspection: ChatEventInspection
): Array<[string, string]> {
  const first = inspection.sourceEvents[0];
  const last = inspection.sourceEvents[inspection.sourceEvents.length - 1];
  const payload = last?.payload ?? {};
  const base: Array<[string, string]> = [
    ["Sequenza", sequenceLabel(inspection.sourceEvents)],
    ["Fase", last?.phase ?? "—"],
    ["Visibilità", last?.visibility ?? "—"]
  ];

  if (inspection.kind === "memory") {
    return [
      ...base,
      ["Ricerca", payload.searched === true ? "eseguita" : "non richiesta"],
      ["Ricordi selezionati", numberLabel(payload.selected_count)],
      ["Candidati valutati", numberLabel(payload.candidate_count)]
    ];
  }
  if (inspection.kind === "context") {
    return [
      ...base,
      ["Schema", stringLabel(payload.schema_version)],
      ["Blocchi runtime", numberLabel(payload.block_count)],
      ["Trace", first?.links.trace_id ?? "—"]
    ];
  }
  if (inspection.kind === "reflection") {
    return [
      ...base,
      ["Passaggio modello", numberLabel(payload.model_step)],
      ["Indice", numberLabel(payload.index)],
      ["Trace", last?.links.trace_id ?? "—"]
    ];
  }
  if (inspection.kind === "action") {
    return [
      ...base,
      ["Tool call", last?.links.tool_call_id ?? "in risoluzione"],
      ["Trace", last?.links.trace_id ?? "—"],
      ["Latenza", latencyLabel(payload.latency_ms)]
    ];
  }
  return [
    ...base,
    ["Turno", last?.turn_id ?? "—"],
    ["Trace", last?.links.trace_id ?? "—"]
  ];
}

function eventReceipt(event: ScarletStreamEvent) {
  return {
    event_id: event.event_id,
    seq: event.seq,
    timestamp: event.timestamp,
    event_type: event.event_type,
    phase: event.phase,
    visibility: event.visibility,
    session_id: event.session_id,
    turn_id: event.turn_id,
    links: event.links,
    payload: inspectablePayload(event)
  };
}

export function isProtectedStreamEvent(event: ScarletStreamEvent): boolean {
  return (
    event.visibility === "private" ||
    event.event_type === "llm.thinking.captured"
  );
}

export function inspectablePayload(
  event: ScarletStreamEvent
): Record<string, unknown> {
  if (event.event_type === "llm.thinking.captured") {
    const { text: _privateText, ...metadata } = event.payload;
    return {
      ...metadata,
      text: "[contenuto del ragionamento interno protetto]"
    };
  }
  if (event.visibility === "private") {
    return redactPrivateValues(event.payload);
  }
  return event.payload;
}

function redactPrivateValues(
  value: Record<string, unknown>
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => {
      if (
        ["text", "thinking", "content", "raw_content", "system"].includes(key)
      ) {
        return [key, "[contenuto privato protetto]"];
      }
      if (Array.isArray(item)) {
        return [
          key,
          item.map((entry) =>
            entry && typeof entry === "object"
              ? redactPrivateValues(entry as Record<string, unknown>)
              : entry
          )
        ];
      }
      if (item && typeof item === "object") {
        return [
          key,
          redactPrivateValues(item as Record<string, unknown>)
        ];
      }
      return [key, item];
    })
  );
}

function sequenceLabel(events: ScarletStreamEvent[]): string {
  const first = events[0]?.seq;
  const last = events[events.length - 1]?.seq;
  if (first === undefined) return "—";
  return first === last ? String(first) : `${first} → ${last}`;
}

function numberLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("it-IT")
    : "—";
}

function stringLabel(value: unknown): string {
  return typeof value === "string" && value ? value : "—";
}

function latencyLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toLocaleString("it-IT")} ms`
    : "—";
}

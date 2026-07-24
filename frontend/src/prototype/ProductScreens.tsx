import {
  ArrowRight,
  BookHeart,
  Check,
  ChevronLeft,
  Clock3,
  Filter,
  Plus,
  Search
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { ChatSession, DashboardMemory } from "../types";

export function MemoryScreen({
  initialMemory,
  memories,
  onOpenSession,
  total
}: {
  initialMemory: DashboardMemory | null;
  memories: DashboardMemory[];
  onOpenSession: (sessionId: string) => void;
  total: number;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("Tutti");
  const [selectedMemory, setSelectedMemory] =
    useState<DashboardMemory | null>(initialMemory);

  useEffect(() => {
    setSelectedMemory(initialMemory);
  }, [initialMemory]);

  const categories = [
    "Tutti",
    ...new Set(memories.map((item) => humanize(item.type)))
  ];
  const filteredMemories = useMemo(
    () =>
      memories.filter((memory) => {
        const label = humanize(memory.type);
        const categoryMatches = category === "Tutti" || label === category;
        const needle = query.trim().toLocaleLowerCase("it");
        const queryMatches =
          !needle ||
          `${memory.content} ${memory.reason_for_storage} ${memory.tags.join(" ")}`
            .toLocaleLowerCase("it")
            .includes(needle);
        return categoryMatches && queryMatches;
      }),
    [category, memories, query]
  );

  return (
    <section className="scarlet-screen scarlet-memory-screen" data-testid="memory-screen">
      <header className="scarlet-screen__intro">
        <div>
          <p><BookHeart aria-hidden="true" size={15} /> Memoria</p>
          <h1>Quello che teniamo con noi.</h1>
          <span>Ricordi reali organizzati per significato, stato e provenienza.</span>
        </div>
        <div className="scarlet-memory-screen__count">
          <strong>{new Intl.NumberFormat("it-IT").format(total)}</strong>
          <span>ricordi disponibili</span>
          <small>{filteredMemories.length} in questa vista</small>
        </div>
      </header>

      <div className="scarlet-memory-screen__toolbar">
        <label>
          <Search aria-hidden="true" size={16} />
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cerca nei ricordi caricati"
            type="search"
            value={query}
          />
        </label>
        <div aria-label="Filtra ricordi per categoria">
          <Filter aria-hidden="true" size={15} />
          {categories.map((item) => (
            <button
              className={category === item ? "is-active" : ""}
              key={item}
              onClick={() => setCategory(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="scarlet-memory-screen__layout">
        <div className="scarlet-memory-screen__list">
          <header>
            <div><p>Archivio personale</p><h2>{filteredMemories.length} ricordi trovati</h2></div>
            <span>Ordine del Core</span>
          </header>
          {filteredMemories.map((memory, index) => (
            <button
              className={selectedMemory?.id === memory.id ? "is-active" : ""}
              key={memory.id}
              onClick={() => setSelectedMemory(memory)}
              type="button"
            >
              <b className="scarlet-memory-screen__number">
                {String(index + 1).padStart(3, "0")}
              </b>
              <div>
                <span>{humanize(memory.type)}</span>
                <p>{memory.content}</p>
                <small>{formatDate(memory.updated_at)} · {memory.scope}</small>
              </div>
              <ArrowRight aria-hidden="true" size={16} />
            </button>
          ))}
          {filteredMemories.length === 0 ? (
            <p className="scarlet-screen__empty-result">
              Nessun ricordo reale corrisponde alla ricerca.
            </p>
          ) : null}
        </div>

        <aside className={`scarlet-memory-screen__detail ${selectedMemory ? "is-open" : ""}`}>
          {selectedMemory ? (
            <>
              <button
                className="scarlet-memory-screen__detail-back"
                onClick={() => setSelectedMemory(null)}
                type="button"
              >
                <ChevronLeft aria-hidden="true" size={15} /> Tutti i ricordi
              </button>
              <p>{humanize(selectedMemory.type)}</p>
              <h2>Dettaglio del ricordo</h2>
              <blockquote>{selectedMemory.content}</blockquote>
              <dl>
                <div><dt>Stato</dt><dd><Check size={13} /> {selectedMemory.status}</dd></div>
                <div><dt>Ambito</dt><dd>{selectedMemory.scope}</dd></div>
                <div><dt>Fiducia</dt><dd>{Math.round(selectedMemory.confidence * 100)}%</dd></div>
                <div><dt>Salienza</dt><dd>{selectedMemory.salience.toFixed(2)}</dd></div>
                <div><dt>Utilizzi</dt><dd>{selectedMemory.usage_count}</dd></div>
                <div><dt>Aggiornato</dt><dd>{formatDate(selectedMemory.updated_at)}</dd></div>
              </dl>
              {selectedMemory.reason_for_storage ? (
                <small>{selectedMemory.reason_for_storage}</small>
              ) : null}
              {selectedMemory.source_session_id ? (
                <button
                  className="scarlet-action scarlet-action--dark"
                  onClick={() => onOpenSession(selectedMemory.source_session_id!)}
                  type="button"
                >
                  Apri conversazione fonte
                  <ArrowRight aria-hidden="true" size={15} />
                </button>
              ) : (
                <small>Nessuna sessione fonte collegata.</small>
              )}
            </>
          ) : (
            <>
              <BookHeart aria-hidden="true" size={24} />
              <h2>Seleziona un ricordo</h2>
              <p>Qui vedrai stato, provenienza e dati reali disponibili.</p>
            </>
          )}
        </aside>
      </div>
    </section>
  );
}

export function SessionsScreen({
  onNewSession,
  onResumeSession,
  sessions
}: {
  onNewSession: () => void;
  onResumeSession: (session: ChatSession) => void;
  sessions: ChatSession[];
}) {
  const [query, setQuery] = useState("");
  const filteredSessions = sessions.filter((session) =>
    `${session.title ?? ""} ${session.id}`
      .toLocaleLowerCase("it")
      .includes(query.trim().toLocaleLowerCase("it"))
  );

  return (
    <section className="scarlet-screen scarlet-sessions-screen" data-testid="sessions-screen">
      <header className="scarlet-screen__intro">
        <div>
          <p><Clock3 aria-hidden="true" size={15} /> Sessioni</p>
          <h1>I fili che possiamo riprendere.</h1>
          <span>Conversazioni reali ordinate dal Core per attività recente.</span>
        </div>
        <button className="scarlet-action scarlet-action--dark" onClick={onNewSession} type="button">
          <Plus aria-hidden="true" size={16} /> Nuova conversazione
        </button>
      </header>

      <label className="scarlet-sessions-screen__search">
        <Search aria-hidden="true" size={17} />
        <input
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Cerca titolo o ID sessione"
          type="search"
          value={query}
        />
      </label>

      <div className="scarlet-sessions-screen__list">
        {filteredSessions.map((session, index) => (
          <article key={session.id}>
            <span className="scarlet-sessions-screen__index">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <small>{formatDate(session.updated_at)}</small>
              <h2>{session.title || "Conversazione senza titolo"}</h2>
              <p>{session.id}</p>
              <span>Creata {formatDate(session.created_at)} · sessione persistita</span>
            </div>
            <button
              aria-label={`Riprendi ${session.title || "conversazione"}`}
              onClick={() => onResumeSession(session)}
              type="button"
            >
              Riprendi <ArrowRight aria-hidden="true" size={16} />
            </button>
          </article>
        ))}
        {filteredSessions.length === 0 ? (
          <p className="scarlet-screen__empty-result">Nessuna sessione reale trovata.</p>
        ) : null}
      </div>
    </section>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "data non disponibile";
  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function humanize(value: string) {
  return value.split("_").join(" ");
}

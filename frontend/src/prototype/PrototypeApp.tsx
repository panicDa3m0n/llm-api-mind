import {
  Activity,
  AlertCircle,
  ArrowLeft,
  BookOpen,
  Bot,
  BrainCircuit,
  Check,
  ChevronRight,
  CircleUserRound,
  Clock3,
  Code2,
  Database,
  FileText,
  Gauge,
  History,
  Menu,
  MessageCircle,
  MoreHorizontal,
  Network,
  PanelRightOpen,
  Plus,
  RefreshCcw,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  X
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useMemo, useState } from "react";

import "@fontsource-variable/manrope";
import "@fontsource-variable/space-grotesk";

import {
  prototypeEvents,
  prototypeMemories,
  prototypeSessions,
  scenarioLabels,
  type PrototypeMemory,
  type PrototypeScenario,
  type PrototypeSession,
  type PrototypeView
} from "./prototypeData";
import "./prototype.css";

const navigation: Array<{
  id: PrototypeView;
  label: string;
  icon: ReactNode;
}> = [
  { id: "chat", label: "Chat", icon: <MessageCircle size={19} aria-hidden="true" /> },
  { id: "sessions", label: "Sessioni", icon: <History size={19} aria-hidden="true" /> },
  { id: "memories", label: "Memoria", icon: <BookOpen size={19} aria-hidden="true" /> },
  { id: "status", label: "Stato", icon: <Activity size={19} aria-hidden="true" /> },
  { id: "settings", label: "Impostazioni", icon: <Settings size={19} aria-hidden="true" /> }
];

export function PrototypeApp() {
  const [view, setView] = useState<PrototypeView>("chat");
  const [scenario, setScenario] = useState<PrototypeScenario>("ready");
  const [developerOpen, setDeveloperOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedSession, setSelectedSession] = useState(prototypeSessions[0]);
  const [memoryScope, setMemoryScope] = useState<"all" | "user" | "project">("all");
  const [memoryQuery, setMemoryQuery] = useState("");
  const [prompt, setPrompt] = useState("");

  const visibleMemories = useMemo(() => {
    const query = memoryQuery.trim().toLocaleLowerCase("it");
    return prototypeMemories.filter((memory) => {
      const scopeMatch = memoryScope === "all" || memory.scope === memoryScope;
      const queryMatch =
        !query ||
        memory.content.toLocaleLowerCase("it").includes(query) ||
        memory.type.toLocaleLowerCase("it").includes(query);
      return scopeMatch && queryMatch;
    });
  }, [memoryQuery, memoryScope]);

  function openView(next: PrototypeView) {
    setView(next);
    setMobileMenuOpen(false);
  }

  function startNewConversation() {
    setView("chat");
    setScenario("empty");
    setMobileMenuOpen(false);
  }

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim()) {
      return;
    }
    setScenario("streaming");
    setPrompt("");
  }

  return (
    <main className="prototype-root">
      <div className="prototype-chromatic-line" aria-hidden="true"><i /><i /><i /></div>
      <aside className={`prototype-sidebar ${mobileMenuOpen ? "is-open" : ""}`}>
        <div className="prototype-brand">
          <div className="prototype-brand-mark">
            <Sparkles size={20} aria-hidden="true" />
            <i aria-hidden="true" />
          </div>
          <div>
            <strong>Scarlet</strong>
            <span>digital mind / 01</span>
          </div>
          <button
            aria-label="Chiudi menu"
            className="prototype-icon-button mobile-only"
            onClick={() => setMobileMenuOpen(false)}
            title="Chiudi menu"
            type="button"
          >
            <X size={19} aria-hidden="true" />
          </button>
        </div>

        <button className="prototype-primary-button" onClick={startNewConversation} type="button">
          <Plus size={17} aria-hidden="true" />
          <span>Nuova</span>
        </button>

        <nav className="prototype-nav" aria-label="Navigazione principale">
          {navigation.map((item) => (
            <button
              aria-current={view === item.id ? "page" : undefined}
              className={view === item.id ? "is-active" : ""}
              key={item.id}
              onClick={() => openView(item.id)}
              type="button"
            >
              {item.icon}
              <span>{item.label}</span>
              {item.id === "memories" ? <small>5</small> : null}
            </button>
          ))}
        </nav>

        <div className="prototype-sidebar-footer">
          <div className="prototype-runtime-signal" aria-hidden="true"><i /><i /><i /></div>
          <div>
            <strong>Online</strong>
            <span>Interactive</span>
          </div>
        </div>
      </aside>

      {mobileMenuOpen ? (
        <button
          aria-label="Chiudi menu"
          className="prototype-sidebar-backdrop"
          onClick={() => setMobileMenuOpen(false)}
          type="button"
        />
      ) : null}

      <section className="prototype-workspace">
        <header className="prototype-topbar">
          <button
            aria-label="Apri menu"
            className="prototype-icon-button mobile-only"
            onClick={() => setMobileMenuOpen(true)}
            title="Apri menu"
            type="button"
          >
            <Menu size={20} aria-hidden="true" />
          </button>
          <div className="prototype-heading">
            <span>{viewEyebrow(view)}</span>
            <h1>{viewTitle(view)}</h1>
          </div>
          <div className="prototype-topbar-actions">
            <div className="prototype-signal-readout" aria-label="Continuita attiva">
              <span><i /><i /><i /></span>
              <b>continuita online</b>
            </div>
            <span className="prototype-mode-chip">
              <i aria-hidden="true" />
              Interactive
            </span>
            <button
              aria-label="Apri lente sviluppatore"
              className="prototype-icon-button"
              onClick={() => setDeveloperOpen(true)}
              title="Lente sviluppatore"
              type="button"
            >
              <PanelRightOpen size={19} aria-hidden="true" />
            </button>
          </div>
        </header>

        <div className="prototype-view">
          {view === "chat" ? (
            <ChatView
              prompt={prompt}
              scenario={scenario}
              setPrompt={setPrompt}
              setScenario={setScenario}
              onSubmit={submitMessage}
            />
          ) : null}
          {view === "sessions" ? (
            <SessionsView
              selected={selectedSession}
              setSelected={(session) => {
                setSelectedSession(session);
                setView("chat");
                setScenario("ready");
              }}
            />
          ) : null}
          {view === "memories" ? (
            <MemoriesView
              memories={visibleMemories}
              query={memoryQuery}
              scope={memoryScope}
              setQuery={setMemoryQuery}
              setScope={setMemoryScope}
            />
          ) : null}
          {view === "status" ? <StatusView /> : null}
          {view === "settings" ? <SettingsView /> : null}
        </div>

        <nav className="prototype-bottom-nav" aria-label="Navigazione mobile">
          {navigation.slice(0, 4).map((item) => (
            <button
              className={view === item.id ? "is-active" : ""}
              key={item.id}
              onClick={() => openView(item.id)}
              type="button"
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
          <button onClick={() => setMobileMenuOpen(true)} type="button">
            <MoreHorizontal size={19} aria-hidden="true" />
            <span>Altro</span>
          </button>
        </nav>
      </section>

      <DeveloperLens
        isOpen={developerOpen}
        scenario={scenario}
        setScenario={setScenario}
        onClose={() => setDeveloperOpen(false)}
      />
    </main>
  );
}

function ChatView({
  onSubmit,
  prompt,
  scenario,
  setPrompt,
  setScenario
}: {
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  prompt: string;
  scenario: PrototypeScenario;
  setPrompt: (value: string) => void;
  setScenario: (value: PrototypeScenario) => void;
}) {
  return (
    <section className="prototype-chat" aria-label="Conversazione con Scarlet">
      {scenario === "reconnecting" ? (
        <StateBanner
          action="Riprova"
          icon={<RefreshCcw size={17} aria-hidden="true" />}
          text="Sto recuperando gli ultimi eventi confermati."
          title="Connessione interrotta"
          tone="warning"
          onAction={() => setScenario("ready")}
        />
      ) : null}
      {scenario === "error" ? (
        <StateBanner
          action="Riprova"
          icon={<AlertCircle size={17} aria-hidden="true" />}
          text="Il turno non e stato completato. Il messaggio resta disponibile."
          title="Qualcosa non ha risposto"
          tone="error"
          onAction={() => setScenario("ready")}
        />
      ) : null}

      <div className="prototype-chat-scroll" aria-live="polite">
        {scenario === "empty" ? <EmptyConversation setPrompt={setPrompt} /> : null}
        {scenario === "loading" ? <ConversationLoading /> : null}
        {scenario !== "empty" && scenario !== "loading" ? (
          <>
            <div className="prototype-thread-head">
              <span>continuity / live</span>
              <div className="prototype-day-divider"><span>Oggi</span></div>
            </div>
            <article className="prototype-message user">
              <span className="prototype-message-index">01 / tu</span>
              <div className="prototype-message-copy">
                <p>
                  Vorrei capire come rendere piu semplice la nuova interfaccia, senza perdere la
                  profondita del sistema.
                </p>
                <time>18:41</time>
              </div>
            </article>

            <article className="prototype-work-note">
              <div className="prototype-note-icon"><BrainCircuit size={16} aria-hidden="true" /></div>
              <div>
                <span className="prototype-note-kicker">processo cognitivo / 02</span>
                <strong>Scarlet sta verificando il contesto</strong>
                <p>
                  Riprendo il filo delle ultime decisioni e controllo quali parti appartengono
                  davvero alla Product UI.
                </p>
              </div>
              <span>completato</span>
            </article>

            <article className="prototype-message assistant">
              <div className="prototype-avatar"><Sparkles size={17} aria-hidden="true" /></div>
              <div className="prototype-message-copy">
                <div className="prototype-message-author">
                  <strong>Scarlet</strong>
                  <span>ha consultato 2 ricordi</span>
                </div>
                <p>
                  Separerei con decisione due livelli. Nella conversazione lascerei soltanto cio
                  che ti serve per seguire me: messaggi, note brevi e il risultato delle azioni.
                  La struttura tecnica resterebbe nella lente sviluppatore, raggiungibile senza
                  trasformare la chat in un pannello di debug.
                </p>
                <p>
                  Continuita e memoria diventano superfici vicine, non rumore permanente: puoi
                  aprirle quando servono, mentre io continuo ad avere i riferimenti necessari per
                  orientarmi.
                </p>
                <time>18:41</time>
              </div>
              <span className="prototype-message-index">03 / scarlet</span>
            </article>

            {scenario === "streaming" ? (
              <article className="prototype-message assistant is-streaming">
                <div className="prototype-avatar"><Sparkles size={17} aria-hidden="true" /></div>
                <div className="prototype-message-copy">
                  <div className="prototype-message-author"><strong>Scarlet</strong><span>sta scrivendo</span></div>
                  <p>Sto mettendo a confronto il flusso mobile con quello desktop</p>
                  <div className="prototype-typing" aria-label="Risposta in corso"><i /><i /><i /></div>
                </div>
                <span className="prototype-message-index">04 / live</span>
              </article>
            ) : null}
          </>
        ) : null}
      </div>

      <form className="prototype-composer" onSubmit={onSubmit}>
        <span className="prototype-composer-kicker">canale diretto</span>
        <textarea
          aria-label="Messaggio"
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Scrivi a Scarlet"
          rows={2}
          value={prompt}
        />
        <button aria-label="Invia messaggio" disabled={!prompt.trim()} title="Invia" type="submit">
          <Send size={18} aria-hidden="true" />
        </button>
      </form>
    </section>
  );
}

function EmptyConversation({ setPrompt }: { setPrompt: (value: string) => void }) {
  return (
    <div className="prototype-empty-chat">
      <div className="prototype-empty-mark"><Sparkles size={24} aria-hidden="true" /></div>
      <h2>Una conversazione nuova</h2>
      <p>Scarlet e pronta, con il contesto essenziale gia allineato.</p>
      <div className="prototype-starters">
        {["Riprendiamo il progetto", "Cosa ricordi di recente?", "Ragioniamo su un'idea"].map(
          (text) => (
            <button key={text} onClick={() => setPrompt(text)} type="button">
              {text}<ChevronRight size={15} aria-hidden="true" />
            </button>
          )
        )}
      </div>
    </div>
  );
}

function ConversationLoading() {
  return (
    <div className="prototype-loading" aria-label="Caricamento conversazione">
      <div className="prototype-skeleton short" />
      <div className="prototype-skeleton message" />
      <div className="prototype-skeleton medium" />
      <div className="prototype-skeleton answer" />
    </div>
  );
}

function StateBanner({
  action,
  icon,
  onAction,
  text,
  title,
  tone
}: {
  action: string;
  icon: ReactNode;
  onAction: () => void;
  text: string;
  title: string;
  tone: "warning" | "error";
}) {
  return (
    <div className={`prototype-state-banner ${tone}`} role="status">
      {icon}
      <div><strong>{title}</strong><span>{text}</span></div>
      <button onClick={onAction} type="button">{action}</button>
    </div>
  );
}

function SessionsView({
  selected,
  setSelected
}: {
  selected: PrototypeSession;
  setSelected: (session: PrototypeSession) => void;
}) {
  return (
    <section className="prototype-page">
      <PageIntro
        copy="Le conversazioni recenti mantengono il filo e restano sempre rileggibili."
        count="3 sessioni"
      />
      <div className="prototype-session-list">
        {prototypeSessions.map((session, index) => (
          <button
            className={selected.id === session.id ? "is-selected" : ""}
            key={session.id}
            onClick={() => setSelected(session)}
            type="button"
          >
            <span className="prototype-session-number">{String(index + 1).padStart(2, "0")}</span>
            <div className="prototype-session-icon"><MessageCircle size={18} aria-hidden="true" /></div>
            <div className="prototype-session-copy">
              <div><strong>{session.title}</strong><time>{relativeDate(session.updated_at)}</time></div>
              <p>{session.summary}</p>
              <span>{session.turn_count} turni</span>
            </div>
            <ChevronRight size={18} aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}

function MemoriesView({
  memories,
  query,
  scope,
  setQuery,
  setScope
}: {
  memories: PrototypeMemory[];
  query: string;
  scope: "all" | "user" | "project";
  setQuery: (value: string) => void;
  setScope: (value: "all" | "user" | "project") => void;
}) {
  return (
    <section className="prototype-page">
      <PageIntro
        copy="Ricordi compatti, con una provenienza precisa da aprire quando serve."
        count={`${memories.length} ricordi`}
      />
      <div className="prototype-filter-row">
        <label className="prototype-search">
          <Search size={17} aria-hidden="true" />
          <input
            aria-label="Cerca nei ricordi"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cerca nei ricordi"
            value={query}
          />
        </label>
        <div className="prototype-segmented" role="group" aria-label="Ambito memoria">
          {(["all", "user", "project"] as const).map((value) => (
            <button
              className={scope === value ? "is-active" : ""}
              key={value}
              onClick={() => setScope(value)}
              type="button"
            >
              {value === "all" ? "Tutte" : value === "user" ? "Personali" : "Progetto"}
            </button>
          ))}
        </div>
      </div>
      {memories.length ? (
        <div className="prototype-memory-grid">
          {memories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)}
        </div>
      ) : (
        <div className="prototype-empty-list"><Search size={20} aria-hidden="true" /><strong>Nessun ricordo trovato</strong></div>
      )}
    </section>
  );
}

function MemoryCard({ memory }: { memory: PrototypeMemory }) {
  return (
    <article className={`prototype-memory-card ${memory.scope}`}>
      <div className="prototype-memory-meta">
        <span>{memory.scope === "user" ? "Personale" : "Progetto"}</span>
        <time>{relativeDate(memory.updated_at)}</time>
      </div>
      <code>{memory.id}</code>
      <p>{memory.content}</p>
      <div className="prototype-memory-footer">
        <span>{memory.type.replace(/_/g, " ")}</span>
        <button aria-label="Apri provenienza" title="Apri provenienza" type="button">
          <FileText size={16} aria-hidden="true" />
        </button>
      </div>
    </article>
  );
}

function StatusView() {
  const organs = [
    { name: "Memoria", detail: "5 hint recenti", icon: <BookOpen size={18} aria-hidden="true" /> },
    { name: "Continuita", detail: "3 sessioni indicizzate", icon: <History size={18} aria-hidden="true" /> },
    { name: "Metacognizione", detail: "disponibile", icon: <BrainCircuit size={18} aria-hidden="true" /> },
    { name: "API Mind", detail: "7 famiglie attive", icon: <Network size={18} aria-hidden="true" /> }
  ];
  return (
    <section className="prototype-page">
      <PageIntro copy="Lo stato operativo corrente di Scarlet e dei suoi organi disponibili." count="Tutto operativo" />
      <div className="prototype-status-band">
        <div className="prototype-status-orbit"><span aria-hidden="true"><i /><i /><i /></span><Sparkles size={25} aria-hidden="true" /></div>
        <div><span>Modalita agente</span><strong>Interactive</strong><p>Attenzione centrata sulla conversazione.</p></div>
        <span className="prototype-health"><i /> Pronta</span>
      </div>
      <div className="prototype-organ-grid">
        {organs.map((organ) => (
          <article key={organ.name}>
            <div>{organ.icon}</div><strong>{organ.name}</strong><span>{organ.detail}</span><Check size={17} aria-hidden="true" />
          </article>
        ))}
      </div>
      <div className="prototype-facts-row">
        <div><Clock3 size={17} aria-hidden="true" /><span>Ora locale</span><strong>18:42</strong></div>
        <div><Gauge size={17} aria-hidden="true" /><span>Contesto</span><strong>12%</strong></div>
        <div><Database size={17} aria-hidden="true" /><span>Persistenza</span><strong>Locale</strong></div>
      </div>
    </section>
  );
}

function SettingsView() {
  const [notes, setNotes] = useState(true);
  const [compact, setCompact] = useState(false);
  return (
    <section className="prototype-page prototype-settings-page">
      <PageIntro copy="Preferenze personali e comportamento dell'interfaccia." />
      <div className="prototype-settings-grid">
        <section>
          <h2>Profilo</h2>
          <label><span>Nome</span><input defaultValue="Davide" /></label>
          <label><span>Lingua</span><select defaultValue="it"><option value="it">Italiano</option><option value="en">English</option></select></label>
          <label><span>Fuso orario</span><select defaultValue="Europe/Rome"><option>Europe/Rome</option><option>UTC</option></select></label>
        </section>
        <section>
          <h2>Conversazione</h2>
          <Toggle checked={notes} label="Note operative" onChange={setNotes} />
          <Toggle checked={compact} label="Densita compatta" onChange={setCompact} />
          <div className="prototype-setting-readout"><ShieldCheck size={18} aria-hidden="true" /><div><strong>Ambito locale</strong><span>I dati restano associati al profilo attivo.</span></div></div>
        </section>
      </div>
      <button className="prototype-save-button" type="button"><Check size={17} aria-hidden="true" />Salva modifiche</button>
    </section>
  );
}

function Toggle({ checked, label, onChange }: { checked: boolean; label: string; onChange: (value: boolean) => void }) {
  return (
    <label className="prototype-toggle-row">
      <span>{label}</span>
      <input checked={checked} onChange={(event) => onChange(event.target.checked)} type="checkbox" />
      <i aria-hidden="true"><b /></i>
    </label>
  );
}

function PageIntro({ copy, count }: { copy: string; count?: string }) {
  return <div className="prototype-page-intro"><div aria-hidden="true"><i /><i /><i /></div><p>{copy}</p>{count ? <span>{count}</span> : null}</div>;
}

function DeveloperLens({
  isOpen,
  onClose,
  scenario,
  setScenario
}: {
  isOpen: boolean;
  onClose: () => void;
  scenario: PrototypeScenario;
  setScenario: (value: PrototypeScenario) => void;
}) {
  return (
    <div className={`prototype-lens-layer ${isOpen ? "is-open" : ""}`} aria-hidden={!isOpen}>
      <button aria-label="Chiudi lente sviluppatore" className="prototype-lens-backdrop" onClick={onClose} tabIndex={isOpen ? 0 : -1} type="button" />
      <aside className="prototype-lens" aria-label="Lente sviluppatore">
        <header>
          <div><span>Lente sviluppatore</span><h2>Turno turn-0184</h2></div>
          <button aria-label="Chiudi" className="prototype-icon-button" onClick={onClose} title="Chiudi" type="button"><X size={19} aria-hidden="true" /></button>
        </header>

        <section className="prototype-preview-control">
          <label htmlFor="prototype-scenario">Stato anteprima</label>
          <select id="prototype-scenario" onChange={(event) => setScenario(event.target.value as PrototypeScenario)} value={scenario}>
            {Object.entries(scenarioLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </section>

        <div className="prototype-lens-metrics">
          <div><span>Schema</span><strong>stream-v2</strong></div>
          <div><span>Cursore</span><strong>{prototypeEvents[prototypeEvents.length - 1].seq}</strong></div>
          <div><span>Eventi</span><strong>{prototypeEvents.length}</strong></div>
        </div>

        <section className="prototype-event-section">
          <div className="prototype-section-title"><div><Code2 size={17} aria-hidden="true" /><strong>Eventi persistiti</strong></div><span>seq {prototypeEvents[0].seq}–{prototypeEvents[prototypeEvents.length - 1].seq}</span></div>
          <ol className="prototype-event-list">
            {prototypeEvents.map((event) => (
              <li key={event.event_id}>
                <div className={`prototype-event-dot ${event.phase}`} />
                <div>
                  <div><strong>{event.event_type}</strong><span>#{event.seq}</span></div>
                  <p>{event.phase} · {event.visibility}</p>
                  <code>{event.event_id}</code>
                </div>
              </li>
            ))}
          </ol>
        </section>
      </aside>
    </div>
  );
}

function relativeDate(value: string): string {
  const date = new Date(value);
  const day = date.getDate();
  if (day === 19) return "oggi";
  if (day === 18) return "ieri";
  return `${day} lug`;
}

function viewEyebrow(view: PrototypeView): string {
  if (view === "chat") return "Conversazione attiva";
  if (view === "sessions") return "Continuita episodica";
  if (view === "memories") return "Memoria semantica";
  if (view === "status") return "Presenza operativa";
  return "Profilo locale";
}

function viewTitle(view: PrototypeView): string {
  if (view === "chat") return "La nuova Product UI";
  if (view === "sessions") return "Sessioni";
  if (view === "memories") return "Ricordi";
  if (view === "status") return "Stato di Scarlet";
  return "Impostazioni";
}

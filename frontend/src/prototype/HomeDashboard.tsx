import {
  ArrowRight,
  BookHeart,
  Brain,
  Clock3,
  House,
  MessageCircleMore,
  Plus,
  Sparkles,
  UserRound
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  createSession,
  fetchDashboardMemories,
  fetchHealth,
  fetchRuntimeSettings,
  fetchSessions,
  fetchUserProfile
} from "../api";
import type {
  ChatSession,
  DashboardMemories,
  HealthStatus,
  RuntimeSettings,
  UserProfile
} from "../types";
import { ChatViewportScreen } from "./ChatViewportScreen";
import { DataJsonPanel } from "./DataJsonPanel";
import { MemoryScreen, SessionsScreen } from "./ProductScreens";
import { ProfileSettingsScreen } from "./ProfileSettingsScreen";
import {
  UnavailableFeatureModal,
  type UnavailableFeature
} from "./UnavailableFeatureModal";
import "./home.css";
import "./product.css";

export type ProductView = "home" | "chat" | "memory" | "sessions" | "profile";

type ProductData = {
  health: HealthStatus | null;
  memories: DashboardMemories | null;
  profile: UserProfile | null;
  sessions: ChatSession[];
  settings: RuntimeSettings | null;
};

const EMPTY_DATA: ProductData = {
  health: null,
  memories: null,
  profile: null,
  sessions: [],
  settings: null
};

export function HomeDashboard({
  initialView = "home",
  username,
  onLogout,
  onPrivateEvidenceChange,
  privateEvidenceUnlocked,
  onViewChange
}: {
  initialView?: ProductView;
  username: string;
  onLogout: () => void;
  onPrivateEvidenceChange: (unlocked: boolean) => void;
  privateEvidenceUnlocked: boolean;
  onViewChange?: (view: ProductView) => void;
}) {
  const [view, setView] = useState<ProductView>(initialView);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [activeMemoryId, setActiveMemoryId] = useState<string | null>(null);
  const [data, setData] = useState<ProductData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [unavailable, setUnavailable] =
    useState<UnavailableFeature | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    const results = await Promise.allSettled([
      fetchHealth(),
      fetchSessions(100),
      fetchDashboardMemories({ limit: 200 }),
      fetchUserProfile(),
      fetchRuntimeSettings()
    ]);
    const rejected = results.find(
      (result): result is PromiseRejectedResult => result.status === "rejected"
    );

    setData((current) => ({
      health: results[0].status === "fulfilled" ? results[0].value : current.health,
      sessions:
        results[1].status === "fulfilled" ? results[1].value : current.sessions,
      memories:
        results[2].status === "fulfilled" ? results[2].value : current.memories,
      profile:
        results[3].status === "fulfilled" ? results[3].value : current.profile,
      settings:
        results[4].status === "fulfilled" ? results[4].value : current.settings
    }));
    setConnectionError(
      rejected
        ? rejected.reason instanceof Error
          ? rejected.reason.message
          : "Core Scarlet non raggiungibile."
        : null
    );
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }, [view]);

  function navigate(nextView: ProductView) {
    setView(nextView);
    onViewChange?.(nextView);
  }

  async function startNewSession() {
    if (creatingSession) return;
    setCreatingSession(true);
    try {
      const session = await createSession();
      setActiveSession(session);
      setData((current) => ({
        ...current,
        sessions: [session, ...current.sessions]
      }));
      setConnectionError(null);
      navigate("chat");
    } catch (error) {
      setConnectionError(
        error instanceof Error ? error.message : "Impossibile creare la sessione."
      );
    } finally {
      setCreatingSession(false);
    }
  }

  function resumeSession(session: ChatSession) {
    setActiveSession(session);
    navigate("chat");
  }

  function openMemory(memoryId?: string) {
    setActiveMemoryId(memoryId ?? null);
    navigate("memory");
  }

  const activeMemory =
    data.memories?.memories.find((memory) => memory.id === activeMemoryId) ?? null;
  const displayName = data.profile?.display_name || username;

  return (
    <main
      className={`scarlet-home${view === "chat" ? " is-chat-view" : ""}`}
      data-testid="product-app"
      data-view={view}
    >
      <div className="scarlet-home__signal" aria-hidden="true"><i /><i /><i /></div>

      <div className="scarlet-home__shell">
        {view === "home" ? (
          <HomeContent
            creatingSession={creatingSession}
            data={data}
            displayName={displayName}
            loading={loading}
            onNewSession={() => void startNewSession()}
            onOpenMemory={openMemory}
            onOpenSessions={() => navigate("sessions")}
            onResumeSession={resumeSession}
          />
        ) : null}
        {view === "chat" ? (
          <ChatViewportScreen
            memories={data.memories?.memories ?? []}
            onDataChanged={() => void refresh()}
            onNewSession={() => void startNewSession()}
            onOpenMemory={() => openMemory()}
            onOpenSessions={() => navigate("sessions")}
            onSessionCreated={(createdSession) => {
              setActiveSession(createdSession);
              setData((current) => ({
                ...current,
                sessions: [
                  createdSession,
                  ...current.sessions.filter((item) => item.id !== createdSession.id)
                ]
              }));
            }}
            privateEvidenceUnlocked={privateEvidenceUnlocked}
            session={activeSession}
          />
        ) : null}
        {view === "memory" ? (
          <div className="scarlet-internal-stack">
            <MemoryScreen
              initialMemory={activeMemory}
              memories={data.memories?.memories ?? []}
              onOpenSession={(sessionId) => {
                const session = data.sessions.find((item) => item.id === sessionId);
                if (session) resumeSession(session);
              }}
              total={data.memories?.total ?? 0}
            />
            <DataJsonPanel
              data={{
                ...data.memories,
                selected_memory_id: activeMemory?.id ?? null,
                source: data.settings?.source ?? "core"
              }}
              title="Memoria disponibile"
            />
          </div>
        ) : null}
        {view === "sessions" ? (
          <div className="scarlet-internal-stack">
            <SessionsScreen
              onNewSession={() => void startNewSession()}
              onResumeSession={resumeSession}
              sessions={data.sessions}
            />
            <DataJsonPanel
              data={{
                sessions: data.sessions,
                resumable: true,
                source: "core"
              }}
              title="Sessioni disponibili"
            />
          </div>
        ) : null}
        {view === "profile" ? (
          <ProfileSettingsScreen
            onLogout={onLogout}
            onSettingsChanged={(settings) => {
              setData((current) => ({ ...current, settings }));
              void refresh();
            }}
            onPrivateEvidenceChange={onPrivateEvidenceChange}
            onUnavailable={setUnavailable}
            privateEvidenceUnlocked={privateEvidenceUnlocked}
            profile={data.profile}
            settings={data.settings}
            username={username}
          />
        ) : null}

        <p className="scarlet-home__fixture-note">
          {loading
            ? "Sincronizzazione con Scarlet Core…"
            : connectionError
              ? "Modalità offline · nessun dato dimostrativo"
              : `Dati reali · ${data.settings?.database.profile ?? "Core locale"} · nessuna fixture`}
        </p>
      </div>

      <ProductDock currentView={view} onNavigate={navigate} />
      <UnavailableFeatureModal
        feature={unavailable}
        onClose={() => setUnavailable(null)}
      />
    </main>
  );
}

function HomeContent({
  creatingSession,
  data,
  displayName,
  loading,
  onNewSession,
  onOpenMemory,
  onOpenSessions,
  onResumeSession
}: {
  creatingSession: boolean;
  data: ProductData;
  displayName: string;
  loading: boolean;
  onNewSession: () => void;
  onOpenMemory: (memoryId?: string) => void;
  onOpenSessions: () => void;
  onResumeSession: (session: ChatSession) => void;
}) {
  const memories = data.memories?.memories.slice(0, 3) ?? [];
  const sessions = data.sessions.slice(0, 3);
  const latestSession = sessions[0];

  return (
    <div data-testid="home-dashboard">
      <section className="scarlet-home__hero" aria-labelledby="home-title">
        <div className="scarlet-home__hero-copy">
          <p className="scarlet-home__eyebrow">
            <Sparkles aria-hidden="true" size={14} />
            Il tuo spazio con Scarlet
          </p>
          <h1 id="home-title">Bentornato, {displayName}.</h1>
          <p>
            Ho riallineato il tuo spazio reale. Possiamo riprendere una sessione
            esistente oppure aprirne una nuova.
          </p>
          <div className="scarlet-home__hero-actions">
            <button
              className="scarlet-home__primary"
              data-testid="new-session"
              disabled={creatingSession}
              onClick={onNewSession}
              type="button"
            >
              <Plus aria-hidden="true" size={18} />
              {creatingSession ? "Creo la sessione…" : "Nuova conversazione"}
            </button>
            <button
              className="scarlet-home__secondary"
              disabled={!latestSession}
              onClick={() => latestSession && onResumeSession(latestSession)}
              type="button"
            >
              Continua l&apos;ultima
              <ArrowRight aria-hidden="true" size={17} />
            </button>
          </div>
        </div>

        <div className="scarlet-home__scarlet" aria-hidden="true">
          <span />
          <img alt="" src="/prototype/scarlet-character-v1.png" />
        </div>
      </section>

      <section className="scarlet-home__stats" aria-label="Riepilogo del tuo spazio">
        <QuickStat
          detail={`${data.memories?.returned ?? 0} caricati adesso`}
          icon={<Brain size={18} />}
          label="Ricordi attivi"
          onOpen={() => onOpenMemory()}
          value={loading ? "…" : formatNumber(data.memories?.total ?? 0)}
        />
        <QuickStat
          detail="sessioni recenti disponibili"
          icon={<MessageCircleMore size={18} />}
          label="Conversazioni"
          onOpen={onOpenSessions}
          value={loading ? "…" : formatNumber(data.sessions.length)}
        />
        <QuickStat
          detail={latestSession ? formatRelative(latestSession.updated_at) : "Nessuna sessione"}
          icon={<Clock3 size={18} />}
          label="Ultima attività"
          onOpen={() => latestSession && onResumeSession(latestSession)}
          value={latestSession ? formatShortDate(latestSession.updated_at) : "—"}
        />
      </section>

      <div className="scarlet-home__dashboard-grid">
        <section className="scarlet-home__panel scarlet-home__panel--memories" aria-labelledby="home-memories">
          <header className="scarlet-home__section-header">
            <div><p>Continuità</p><h2 id="home-memories">Ultimi ricordi</h2></div>
            <button onClick={() => onOpenMemory()} type="button">
              Vedi tutti <ArrowRight aria-hidden="true" size={15} />
            </button>
          </header>
          <div className="scarlet-home__memory-list">
            {memories.length ? memories.map((memory) => (
              <button
                className="scarlet-home__memory"
                key={memory.id}
                onClick={() => onOpenMemory(memory.id)}
                type="button"
              >
                <div>
                  <span>{humanize(memory.type)}</span>
                  <small>{formatRelative(memory.updated_at)}</small>
                </div>
                <p>{memory.content}</p>
              </button>
            )) : <EmptyState text={loading ? "Carico i ricordi…" : "Nessun ricordo disponibile."} />}
          </div>
        </section>

        <section className="scarlet-home__panel scarlet-home__panel--sessions" aria-labelledby="home-sessions">
          <header className="scarlet-home__section-header">
            <div><p>Conversazioni</p><h2 id="home-sessions">Sessioni recenti</h2></div>
            <button onClick={onOpenSessions} type="button">
              Vedi tutte <ArrowRight aria-hidden="true" size={15} />
            </button>
          </header>
          <div className="scarlet-home__session-list">
            {sessions.length ? sessions.map((session) => (
              <article className="scarlet-home__session" key={session.id}>
                <div className="scarlet-home__session-copy">
                  <div>
                    <strong>{session.title || "Conversazione senza titolo"}</strong>
                    <small>{formatRelative(session.updated_at)}</small>
                  </div>
                  <p>Sessione reale pronta per essere ripresa.</p>
                  <span>{session.id}</span>
                </div>
                <button
                  aria-label={`Riprendi ${session.title || "conversazione"}`}
                  onClick={() => onResumeSession(session)}
                  type="button"
                >
                  Riprendi <ArrowRight aria-hidden="true" size={16} />
                </button>
              </article>
            )) : <EmptyState text={loading ? "Carico le sessioni…" : "Nessuna sessione disponibile."} />}
          </div>
        </section>
      </div>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="scarlet-product-empty">{text}</p>;
}

function ProductDock({
  currentView,
  onNavigate
}: {
  currentView: ProductView;
  onNavigate: (view: ProductView) => void;
}) {
  const items: Array<[ProductView, string, React.ReactNode]> = [
    ["home", "Home", <House aria-hidden="true" size={19} />],
    ["chat", "Chat", <MessageCircleMore aria-hidden="true" size={19} />],
    ["memory", "Memoria", <BookHeart aria-hidden="true" size={19} />],
    ["sessions", "Sessioni", <Clock3 aria-hidden="true" size={19} />],
    ["profile", "Profilo", <UserRound aria-hidden="true" size={19} />]
  ];

  return (
    <nav className="scarlet-home__dock" aria-label="Navigazione principale">
      {items.map(([target, label, icon]) => (
        <button
          className={currentView === target ? "is-active" : ""}
          data-view-target={target}
          key={target}
          onClick={() => onNavigate(target)}
          type="button"
        >
          {icon}<span>{label}</span>
        </button>
      ))}
    </nav>
  );
}

function QuickStat({
  detail,
  icon,
  label,
  onOpen,
  value
}: {
  detail: string;
  icon: React.ReactNode;
  label: string;
  onOpen: () => void;
  value: string;
}) {
  return (
    <button className="scarlet-home__stat" onClick={onOpen} type="button">
      <span aria-hidden="true">{icon}</span>
      <div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div>
      <ArrowRight aria-hidden="true" className="scarlet-home__stat-arrow" size={15} />
    </button>
  );
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("it-IT").format(value);
}

function formatShortDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "short"
  }).format(date);
}

export function formatRelative(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "data non disponibile";
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat("it-IT", { numeric: "auto" });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 30) return formatter.format(days, "day");
  const months = Math.round(days / 30);
  if (Math.abs(months) < 12) return formatter.format(months, "month");
  return formatter.format(Math.round(months / 12), "year");
}

function humanize(value: string) {
  return value.split("_").join(" ");
}

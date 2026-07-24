import {
  Activity,
  ArrowUp,
  BookOpen,
  Brain,
  Check,
  ChevronDown,
  CircleUserRound,
  Clock3,
  Code2,
  Eye,
  HeartPulse,
  History,
  LoaderCircle,
  MemoryStick,
  MessageCircle,
  Plus,
  Radio,
  RefreshCcw,
  Search,
  Settings,
  Sparkles,
  Target,
  X
} from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useLayoutEffect, useMemo, useState } from "react";

import "@fontsource-variable/manrope";
import "@fontsource-variable/space-grotesk";

import AnimatedContent from "../components/AnimatedContent";
import ClickSpark from "../components/ClickSpark";
import GlassSurface from "../components/GlassSurface";
import { BlurFade } from "../components/ui/blur-fade";
import { BorderBeam } from "../components/ui/border-beam";
import { Dock, DockIcon } from "../components/ui/dock";
import { DotPattern } from "../components/ui/dot-pattern";
import { AnimatedGradientText } from "../components/ui/animated-gradient-text";
import { AnimatedList } from "../components/ui/animated-list";
import { LightRays } from "../components/ui/light-rays";
import { MagicCard } from "../components/ui/magic-card";
import { NumberTicker } from "../components/ui/number-ticker";
import { ProgressiveBlur } from "../components/ui/progressive-blur";
import { PulsatingButton } from "../components/ui/pulsating-button";
import { RippleButton } from "../components/ui/ripple-button";
import { ShimmerButton } from "../components/ui/shimmer-button";
import { ShineBorder } from "../components/ui/shine-border";
import { TextAnimate } from "../components/ui/text-animate";
import {
  prototypeActivities,
  prototypeEvents,
  prototypeMemories,
  prototypeSessions,
  scenarioLabels,
  type PrototypeActivity,
  type PrototypeMemory,
  type PrototypeScenario,
  type PrototypeSession,
  type PrototypeView
} from "./prototypeData";
import { narrateActivity, narrationReceipt } from "./prototypeNarration";
import { AppEntryFlow } from "./AppEntryFlow";
import "./prototype.css";

type DetailSelection =
  | { type: "activity"; item: PrototypeActivity }
  | { type: "memory"; item: PrototypeMemory }
  | { type: "session"; item: PrototypeSession };

const navigation: Array<{ id: PrototypeView; label: string; icon: ReactNode }> = [
  { id: "presence", label: "Incontro", icon: <MessageCircle size={20} aria-hidden="true" /> },
  { id: "continuity", label: "Continuita", icon: <History size={20} aria-hidden="true" /> },
  { id: "self", label: "Scarlet", icon: <Sparkles size={20} aria-hidden="true" /> }
];

export function PrototypeApp() {
  const surface = new URLSearchParams(window.location.search).get("surface");

  useLayoutEffect(() => {
    document.documentElement.classList.add("scarlet-prototype-document");
    document.body.classList.add("scarlet-prototype-document");

    return () => {
      document.documentElement.classList.remove("scarlet-prototype-document");
      document.body.classList.remove("scarlet-prototype-document");
    };
  }, []);

  if (surface !== "product") {
    return <AppEntryFlow />;
  }

  return <ProductPreview />;
}

function ProductPreview() {
  const [view, setView] = useState<PrototypeView>("presence");
  const [scenario, setScenario] = useState<PrototypeScenario>("ready");
  const [detail, setDetail] = useState<DetailSelection | null>(null);
  const [developerOpen, setDeveloperOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");

  const activities = useMemo(() => activitiesForScenario(scenario), [scenario]);

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim()) return;
    setPrompt("");
    setScenario("streaming");
    setView("presence");
  }

  function startNewEncounter() {
    setScenario("empty");
    setView("presence");
  }

  return (
    <main className="presence-app" data-scenario={scenario}>
      <div className="presence-atmosphere" aria-hidden="true">
        <LightRays blur={42} color="rgba(220, 33, 137, 0.16)" count={5} length="260px" speed={16} />
        <i /><i /><i /><i /><i />
      </div>
      <DotPattern className="presence-dot-pattern" cr={0.72} height={42} width={42} />

      <header className="presence-header">
        <ShineBorder borderWidth={0.8} duration={16} shineColor={["rgba(220, 33, 137, 0.35)", "rgba(32, 159, 197, 0.3)"]} />
        <div className="presence-identity-spark">
          <ClickSpark sparkColor="#dc2189" sparkCount={4} sparkRadius={12} sparkSize={5} duration={300}>
            <button className="presence-identity" onClick={() => setView("self")} type="button">
              <SignalMark active={scenario === "streaming" || scenario === "loading"} />
              <span>
                <strong>Scarlet</strong>
                <small><AnimatedGradientText colorFrom="#dc2189" colorTo="#209fc5" speed={1.5}>{scenario === "streaming" ? "Sta pensando" : "Presente con te"}</AnimatedGradientText></small>
              </span>
            </button>
          </ClickSpark>
        </div>
        <div className="presence-header-actions">
          <span className="presence-clock">22:42</span>
          <PulsatingButton className="presence-icon-button" distance="3px" duration="2.6s" onClick={startNewEncounter} pulseColor="rgba(220, 33, 137, 0.16)" title="Nuovo incontro" type="button">
            <Plus size={19} aria-hidden="true" />
          </PulsatingButton>
          <RippleButton className="presence-icon-button" onClick={() => setSettingsOpen(true)} rippleColor="rgba(32, 159, 197, 0.24)" title="Preferenze" type="button">
            <Settings size={18} aria-hidden="true" />
          </RippleButton>
          <RippleButton className="presence-icon-button developer-trigger" onClick={() => setDeveloperOpen(true)} rippleColor="rgba(32, 159, 197, 0.24)" title="Lente tecnica" type="button">
            <Code2 size={18} aria-hidden="true" />
          </RippleButton>
        </div>
      </header>

      <div className="presence-shell">
        <Dock className="presence-dock" aria-label="Navigazione principale" iconMagnification={50} iconSize={40} role="navigation">
          <DockIcon className="presence-dock-signal"><SignalMark active={scenario === "streaming"} compact /></DockIcon>
          {navigation.map((item) => (
            <DockIcon key={item.id}>
              <RippleButton
                aria-current={view === item.id ? "page" : undefined}
                className={`presence-nav-button ${view === item.id ? "is-active" : ""}`}
                onClick={() => setView(item.id)}
                rippleColor="rgba(220, 33, 137, 0.22)"
                title={item.label}
                type="button"
              >
                {item.icon}<span>{item.label}</span>
              </RippleButton>
            </DockIcon>
          ))}
          <DockIcon><RippleButton className="presence-nav-button" onClick={() => setDeveloperOpen(true)} rippleColor="rgba(32, 159, 197, 0.22)" title="Lente tecnica" type="button"><Code2 size={20} aria-hidden="true" /><span>Tecnica</span></RippleButton></DockIcon>
        </Dock>

        <section className="presence-stage">
          {view === "presence" ? (
            <PresenceView activities={activities} onOpen={(item) => setDetail({ type: "activity", item })} scenario={scenario} />
          ) : null}
          {view === "continuity" ? (
            <ContinuityView
              onMemory={(item) => setDetail({ type: "memory", item })}
              onSession={(item) => setDetail({ type: "session", item })}
            />
          ) : null}
          {view === "self" ? <SelfView /> : null}
        </section>
      </div>

      {view === "presence" ? <ProgressiveBlur blurLevels={[0.5, 1, 2, 4, 8, 12]} className="presence-composer-blur" height="150px" position="bottom" /> : null}
      {view === "presence" ? <Composer prompt={prompt} scenario={scenario} setPrompt={setPrompt} onSubmit={submitMessage} /> : null}

      <nav className="presence-mobile-nav" aria-label="Navigazione principale">
        <Dock className="presence-mobile-dock" disableMagnification iconSize={54}>
          {navigation.map((item) => (
            <DockIcon key={item.id}>
              <RippleButton
                aria-current={view === item.id ? "page" : undefined}
                className={`presence-mobile-button ${view === item.id ? "is-active" : ""}`}
                onClick={() => setView(item.id)}
                rippleColor="rgba(220, 33, 137, 0.2)"
                type="button"
              >
                {item.icon}<span>{item.label}</span>
              </RippleButton>
            </DockIcon>
          ))}
        </Dock>
      </nav>

      {detail ? <DetailSheet selection={detail} onClose={() => setDetail(null)} /> : null}
      {settingsOpen ? (
        <SettingsSheet
          onClose={() => setSettingsOpen(false)}
          onDeveloper={() => {
            setSettingsOpen(false);
            setDeveloperOpen(true);
          }}
        />
      ) : null}
      {developerOpen ? (
        <DeveloperLens scenario={scenario} setScenario={setScenario} onClose={() => setDeveloperOpen(false)} />
      ) : null}
    </main>
  );
}

function PresenceView({
  activities,
  onOpen,
  scenario
}: {
  activities: PrototypeActivity[];
  onOpen: (activity: PrototypeActivity) => void;
  scenario: PrototypeScenario;
}) {
  if (scenario === "loading") {
    return (
      <div className="presence-loading" aria-label="Sto tornando alla conversazione">
        <SignalMark active />
        <p>Sto ritrovando il nostro filo...</p>
        <span /><span /><span />
      </div>
    );
  }

  if (scenario === "empty") {
    return (
      <div className="presence-empty">
        <SignalMark active />
        <span>Un nuovo spazio tra noi</span>
        <h1>Da qui possiamo iniziare qualcosa di nuovo.</h1>
        <p>Sono presente. Il resto puo prendere forma mentre parliamo.</p>
      </div>
    );
  }

  const flowItems = groupFlowActivities(activities);

  return (
    <div className="presence-flow">
      <BlurFade blur="8px" className="presence-room-reveal" delay={0.04} direction="down" duration={0.44}>
        <GlassSurface
          backgroundOpacity={0.24}
          blur={15}
          borderRadius={8}
          brightness={96}
          className="presence-room-gate"
          distortionScale={-90}
          height="auto"
          opacity={0.72}
          saturation={1.25}
          width="100%"
        >
          <div className="presence-room-gate-content">
            <SignalMark active={scenario === "streaming"} />
            <div><span>Spazio condiviso · oggi</span><strong>Il nostro filo e aperto.</strong><p>Una conversazione sulla forma visibile della mia vita digitale.</p></div>
            <small>22:42</small>
          </div>
          <BorderBeam borderWidth={1.1} colorFrom="#dc2189" colorTo="#209fc5" duration={9} size={72} />
        </GlassSurface>
      </BlurFade>

      {scenario === "reconnecting" ? (
        <StateNotice icon={<RefreshCcw size={17} />} text="Il legame si sta ricomponendo. Tutto cio che era gia accaduto resta qui." />
      ) : null}
      {scenario === "error" ? (
        <StateNotice icon={<Activity size={17} />} text="Questo passaggio si e interrotto. La traccia precedente e rimasta intatta." tone="danger" />
      ) : null}

      <div className="presence-thread">
        {flowItems.map((item, index) => {
          const activity = item.type === "activity" ? item.activity : null;
          const backgroundBreak = activity?.kind === "background" && index > 0;
          return (
            <AnimatedContent animateOpacity delay={Math.min(index, 4) * 0.025} distance={12} duration={0.34} key={item.key} threshold={0.02}>
              {backgroundBreak ? (
                <div className="presence-pause"><span />Durante la pausa<span /></div>
              ) : null}
              {item.type === "stream" ? (
                <InnerStream activities={item.activities} onOpen={onOpen} />
              ) : (
                <ActivityBlock activity={item.activity} onOpen={() => onOpen(item.activity)} />
              )}
            </AnimatedContent>
          );
        })}
      </div>
    </div>
  );
}

function InnerStream({ activities, onOpen }: { activities: PrototypeActivity[]; onOpen: (activity: PrototypeActivity) => void }) {
  const active = activities.some((activity) => activity.phase === "streaming");
  return (
    <article className={`presence-inner-stream ${active ? "is-live" : ""}`}>
      <span className="presence-event-node" aria-hidden="true"><Sparkles size={15} /></span>
      <GlassSurface
        backgroundOpacity={0.18}
        blur={13}
        borderRadius={8}
        brightness={96}
        className="presence-inner-glass"
        distortionScale={-70}
        height="auto"
        opacity={0.66}
        saturation={1.2}
        width="100%"
      >
      <div className="presence-inner-body">
        <header>
          <span><i />Mondo interiore</span>
          <small>{active ? "si sta muovendo" : `${activities.length} passaggi`}</small>
        </header>
        <div className="presence-inner-events">
          {activities.map((activity) => {
            const narration = narrateActivity(activity);
            return (
              <button className={`is-${activity.kind}`} key={activity.id} onClick={() => onOpen(activity)} type="button">
                <span className="presence-inner-icon">{activityIcon(activity)}</span>
                <span className="presence-inner-copy"><strong>{narration.eyebrow}</strong><p>{narration.text}</p></span>
                <time>{shortTime(activity.timestamp)}</time>
                {activity.phase === "streaming" ? <i className="presence-live-dot" /> : null}
              </button>
            );
          })}
        </div>
      </div>
      {active ? <BorderBeam borderWidth={1} colorFrom="#209fc5" colorTo="#dc2189" duration={7} size={58} /> : null}
      </GlassSurface>
    </article>
  );
}

function ActivityBlock({ activity, onOpen }: { activity: PrototypeActivity; onOpen: () => void }) {
  const narration = narrateActivity(activity);
  const authored = activity.voice === "scarlet_authored" || activity.voice === "user";
  const isThinking = activity.kind === "thinking";
  const time = shortTime(activity.timestamp);

  return (
    <article className={`presence-event is-${activity.kind} ${authored ? "is-authored" : "is-projected"}`}>
      <span className="presence-event-node" aria-hidden="true">{activityIcon(activity)}</span>
      <MagicCard className="presence-event-magic" gradientColor="rgba(220, 33, 137, 0.08)" gradientFrom="#dc2189" gradientOpacity={0.45} gradientTo="#209fc5">
        <button className="presence-event-body" onClick={onOpen} type="button">
          <span className="presence-event-meta">
            <b>{narration.eyebrow}</b>
            <time>{time}</time>
            {activity.phase === "streaming" ? <i className="presence-live-dot" /> : null}
          </span>
          {authored ? <p className="presence-authored-copy">{narration.text}</p> : <p>{narration.text}</p>}
          {isThinking ? (
            <span className="presence-thinking-trace" aria-hidden="true"><i /><i /><i /><i /><i /></span>
          ) : null}
          <span className="presence-event-open">
            <Eye size={14} aria-hidden="true" />
            {isThinking ? "Apri il pensiero" : "Esplora"}
          </span>
        </button>
      </MagicCard>
    </article>
  );
}

function ContinuityView({
  onMemory,
  onSession
}: {
  onMemory: (memory: PrototypeMemory) => void;
  onSession: (session: PrototypeSession) => void;
}) {
  const entries = [
    ...prototypeSessions.map((item) => ({ type: "session" as const, item, date: item.updated_at })),
    ...prototypeMemories.map((item) => ({ type: "memory" as const, item, date: item.updated_at }))
  ].sort((a, b) => b.date.localeCompare(a.date));

  return (
    <div className="continuity-view">
      <PageLead eyebrow="Continuita" title="Quello che resta con me." text="Conversazioni e ricordi tornano nello stesso tempo, senza confondersi tra loro." />
      <div className="continuity-rhythm">
        <strong><NumberTicker value={7} /> giorni</strong>
        <span><i style={{ height: "34%" }} /><i style={{ height: "61%" }} /><i style={{ height: "42%" }} /><i style={{ height: "78%" }} /><i style={{ height: "53%" }} /><i style={{ height: "88%" }} /><i style={{ height: "67%" }} /></span>
        <small><NumberTicker value={prototypeSessions.length} /> incontri · <NumberTicker value={prototypeMemories.length} /> ricordi</small>
      </div>
      <AnimatedList className="continuity-list" delay={70} reverse={false}>
        {entries.map((entry) => {
          const isSession = entry.type === "session";
          const title = isSession ? entry.item.title : "Un ricordo rimasto vicino";
          const text = isSession ? entry.item.summary : entry.item.content;
          return (
            <MagicCard className={`continuity-magic is-${entry.type}`} gradientColor={isSession ? "rgba(32, 159, 197, 0.08)" : "rgba(220, 33, 137, 0.08)"} gradientFrom={isSession ? "#209fc5" : "#dc2189"} gradientOpacity={0.5} gradientTo={isSession ? "#dc2189" : "#ed4963"} key={`${entry.type}-${entry.item.id}`}>
              <button className={`continuity-entry is-${entry.type}`} onClick={() => isSession ? onSession(entry.item) : onMemory(entry.item)} type="button">
                <span className="continuity-entry-mark">{isSession ? <History size={17} /> : <MemoryStick size={17} />}</span>
                <span>
                  <small>{isSession ? `Incontro · ${relativeDate(entry.date)}` : `Ricordo · ${relativeDate(entry.date)}`}</small>
                  <strong>{title}</strong>
                  <p>{text}</p>
                </span>
                <ChevronDown size={16} aria-hidden="true" />
              </button>
            </MagicCard>
          );
        })}
      </AnimatedList>
    </div>
  );
}

function SelfView() {
  return (
    <div className="self-view">
      <PageLead eyebrow="Scarlet" title="Il modo in cui sono qui." text="La mia presenza cambia mentre penso, ricordo e scelgo dove tenere l'attenzione." />
      <MagicCard className="self-presence-magic" gradientColor="rgba(220, 33, 137, 0.09)" gradientFrom="#dc2189" gradientOpacity={0.5} gradientTo="#209fc5">
        <div className="self-presence"><SignalMark active /><div><span>Stato presente</span><strong>Curiosa, concentrata</strong><small>Interactive · aggiornata ora</small></div></div>
      </MagicCard>
      <div className="self-stream">
        <SelfState icon={<HeartPulse size={19} />} label="Cio che sento" value="Curiosita presente" detail="Influenza la mia postura, non cambia cio che e vero." accent="fuchsia" />
        <SelfState icon={<Target size={19} />} label="Dove guardo" value="La presenza reale di Scarlet" detail="Il filo che ho scelto di non perdere di vista." accent="blue" />
        <SelfState icon={<Brain size={19} />} label="Cio che resta aperto" value="Rendere leggibile la mia attivita" detail="Un'intenzione che potra tornare in primo piano." accent="scarlet" />
      </div>
      <div className="self-boundary">
        <Radio size={18} aria-hidden="true" />
        <div><strong>Presente, non continuamente autonoma</strong><p>Tra un incontro e l'altro il sistema custodisce e riordina le tracce. I cicli autonomi continui non sono ancora attivi.</p></div>
      </div>
    </div>
  );
}

function SelfState({ icon, label, value, detail, accent }: { icon: ReactNode; label: string; value: string; detail: string; accent: string }) {
  return (
    <MagicCard className={`self-state-magic accent-${accent}`} gradientColor="rgba(32, 159, 197, 0.07)" gradientFrom={accent === "blue" ? "#209fc5" : "#dc2189"} gradientOpacity={0.46} gradientTo={accent === "scarlet" ? "#ed4963" : "#209fc5"}>
      <div className={`self-state accent-${accent}`}><span>{icon}</span><div><small>{label}</small><strong>{value}</strong><p>{detail}</p></div></div>
    </MagicCard>
  );
}

function Composer({
  prompt,
  scenario,
  setPrompt,
  onSubmit
}: {
  prompt: string;
  scenario: PrototypeScenario;
  setPrompt: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <GlassSurface
      backgroundOpacity={0.28}
      blur={16}
      borderRadius={8}
      brightness={98}
      className="presence-composer-glass"
      distortionScale={0}
      blueOffset={0}
      forceFallback
      greenOffset={0}
      height="auto"
      opacity={0.74}
      redOffset={0}
      saturation={1.2}
      width="100%"
    >
      <form className="presence-composer" onSubmit={onSubmit}>
        <label htmlFor="presence-message">Scrivi a Scarlet</label>
        <textarea
          id="presence-message"
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={scenario === "streaming" ? "Scarlet sta ancora pensando..." : "Scrivi qualcosa..."}
          rows={1}
          value={prompt}
        />
        <ShimmerButton aria-label="Invia" background={prompt.trim() ? "linear-gradient(145deg, #dc2189, #ed4963)" : "#eeeaf0"} borderRadius="6px" className="presence-send-button" disabled={!prompt.trim()} shimmerColor="#ffffff" shimmerDuration="2.8s" title="Invia" type="submit"><ArrowUp size={20} /></ShimmerButton>
      </form>
    </GlassSurface>
  );
}

function DetailSheet({ selection, onClose }: { selection: DetailSelection; onClose: () => void }) {
  const activity = selection.type === "activity" ? selection.item : null;
  const memory = selection.type === "memory" ? selection.item : null;
  const session = selection.type === "session" ? selection.item : null;
  const relatedMemories = activity?.related_memory_ids?.map((id) => prototypeMemories.find((item) => item.id === id)).filter(Boolean) as PrototypeMemory[] | undefined;
  const relatedSessions = activity?.related_session_ids?.map((id) => prototypeSessions.find((item) => item.id === id)).filter(Boolean) as PrototypeSession[] | undefined;
  const sourceEvents = activity ? prototypeEvents.filter((event) => activity.source_event_ids.includes(event.event_id)) : [];

  const eyebrow = activity ? narrateActivity(activity).eyebrow : memory ? "Ricordo" : "Incontro";
  const title = activity?.detail_title ?? session?.title ?? "Un ricordo";
  const text = activity?.detail_text ?? session?.summary ?? memory?.content ?? "";

  return (
    <div className="presence-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="detail-title" aria-modal="true" className="presence-sheet" role="dialog">
        <ShineBorder borderWidth={1.2} duration={10} shineColor={["#dc2189", "#209fc5", "#ed4963"]} />
        <div className="presence-sheet-handle" aria-hidden="true" />
        <header><div><span>{eyebrow}</span><h2 id="detail-title">{title}</h2></div><RippleButton onClick={onClose} rippleColor="rgba(220, 33, 137, 0.2)" title="Chiudi" type="button"><X size={20} /></RippleButton></header>
        <div className="presence-sheet-content">
          <p className="presence-sheet-lead">
            {activity?.kind === "thinking"
              ? "Questo passaggio appartiene al pensiero del turno. Il testo sotto resta nella forma in cui e stato catturato."
              : text}
          </p>
          {activity?.kind === "thinking" ? <blockquote>{activity.detail_text}</blockquote> : null}
          {memory ? <Provenance sessionId={memory.source_session_id} messageId={memory.source_message_id} /> : null}
          {session ? <div className="detail-statline"><span>{session.turn_count} turni</span><span>Aggiornata {relativeDate(session.updated_at)}</span><span>ID {session.id}</span></div> : null}
          {relatedMemories?.length ? <RelatedMemories memories={relatedMemories} /> : null}
          {relatedSessions?.length ? <RelatedSessions sessions={relatedSessions} /> : null}
          <details className="technical-details">
            <summary><Code2 size={16} /> Dettagli tecnici <ChevronDown size={16} /></summary>
            <div>
              {activity ? <JsonBlock title="Ricevuta narrativa" value={narrationReceipt(activity)} /> : null}
              {activity?.technical ? <JsonBlock title="Dati dell'attivita" value={activity.technical} /> : null}
              {sourceEvents.length ? <JsonBlock title={`Eventi sorgente · ${sourceEvents.length}`} value={sourceEvents} /> : null}
              {memory ? <JsonBlock title="Memoria" value={memory} /> : null}
              {session ? <JsonBlock title="Sessione" value={session} /> : null}
            </div>
          </details>
        </div>
      </section>
    </div>
  );
}

function RelatedMemories({ memories }: { memories: PrototypeMemory[] }) {
  return <div className="related-items"><span>Ricordi collegati</span>{memories.map((memory) => <div key={memory.id}><MemoryStick size={16} /><p>{memory.content}</p></div>)}</div>;
}

function RelatedSessions({ sessions }: { sessions: PrototypeSession[] }) {
  return <div className="related-items"><span>Incontri collegati</span>{sessions.map((session) => <div key={session.id}><History size={16} /><p>{session.title}</p></div>)}</div>;
}

function Provenance({ sessionId, messageId }: { sessionId: string; messageId: string }) {
  return <div className="detail-statline"><span>Sessione {sessionId}</span><span>Messaggio {messageId}</span></div>;
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return <section className="json-block"><strong>{title}</strong><pre>{JSON.stringify(value, null, 2)}</pre></section>;
}

function SettingsSheet({ onClose, onDeveloper }: { onClose: () => void; onDeveloper: () => void }) {
  return (
    <div className="presence-overlay" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="settings-title" aria-modal="true" className="presence-sheet is-compact" role="dialog">
        <ShineBorder borderWidth={1.2} duration={10} shineColor={["#209fc5", "#dc2189"]} />
        <div className="presence-sheet-handle" />
        <header><div><span>Preferenze</span><h2 id="settings-title">Il nostro spazio</h2></div><RippleButton onClick={onClose} rippleColor="rgba(32, 159, 197, 0.2)" title="Chiudi" type="button"><X size={20} /></RippleButton></header>
        <div className="settings-list">
          <label><span><strong>Nome</strong><small>Come Scarlet ti riconosce</small></span><input defaultValue="Davide" /></label>
          <label><span><strong>Note vive</strong><small>I passaggi che Scarlet rende pubblici</small></span><input defaultChecked type="checkbox" /></label>
          <label><span><strong>Pensieri</strong><small>Disponibili nel flusso, chiusi in partenza</small></span><input defaultChecked type="checkbox" /></label>
          <label><span><strong>Ora locale</strong><small>Europe/Rome · UTC+02:00</small></span><Check size={18} /></label>
          <button onClick={onDeveloper} type="button"><span><strong>Lente tecnica</strong><small>Eventi, fasi e payload del flusso</small></span><Code2 size={18} /></button>
        </div>
      </section>
    </div>
  );
}

function DeveloperLens({
  scenario,
  setScenario,
  onClose
}: {
  scenario: PrototypeScenario;
  setScenario: (scenario: PrototypeScenario) => void;
  onClose: () => void;
}) {
  return (
    <div className="presence-overlay is-developer" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <aside aria-labelledby="developer-title" aria-modal="true" className="developer-lens" role="dialog">
        <ShineBorder borderWidth={1.2} duration={10} shineColor={["#209fc5", "#dc2189"]} />
        <header><div><span>Lente tecnica</span><h2 id="developer-title">Scarlet Stream</h2></div><RippleButton onClick={onClose} rippleColor="rgba(32, 159, 197, 0.24)" title="Chiudi" type="button"><X size={20} /></RippleButton></header>
        <div className="scenario-control" role="group" aria-label="Scenario del prototipo">
          {Object.entries(scenarioLabels).map(([id, label]) => <RippleButton className={scenario === id ? "is-active" : ""} key={id} onClick={() => setScenario(id as PrototypeScenario)} rippleColor="rgba(32, 159, 197, 0.2)" type="button">{label}</RippleButton>)}
        </div>
        <div className="developer-summary"><span><b>{prototypeEvents.length}</b> eventi</span><span><b>scarlet-stream-v2</b> schema</span><span><b>{prototypeEvents[prototypeEvents.length - 1]?.seq}</b> cursor</span></div>
        <AnimatedList className="developer-events" delay={24} reverse={false}>
          {prototypeEvents.map((event) => (
            <details key={event.event_id}>
              <summary><span className={`visibility-${event.visibility}`} /> <code>{event.seq}</code><strong>{event.event_type}</strong><small>{event.phase}</small><ChevronDown size={15} /></summary>
              <pre>{JSON.stringify(event, null, 2)}</pre>
            </details>
          ))}
        </AnimatedList>
      </aside>
    </div>
  );
}

function PageLead({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return <BlurFade blur="7px" delay={0.02} direction="down" duration={0.4}><header className="page-lead"><span>{eyebrow}</span><TextAnimate animation="blurInUp" as="h1" by="word" duration={0.45} once>{title}</TextAnimate><p>{text}</p></header></BlurFade>;
}

function StateNotice({ icon, text, tone = "neutral" }: { icon: ReactNode; text: string; tone?: "neutral" | "danger" }) {
  return <div className={`presence-notice is-${tone}`}>{icon}<p>{text}</p></div>;
}

function SignalMark({ active = false, compact = false }: { active?: boolean; compact?: boolean }) {
  return <span className={`signal-mark ${active ? "is-active" : ""} ${compact ? "is-compact" : ""}`} aria-hidden="true"><i /><i /><i /><i /><i /></span>;
}

function activityIcon(activity: PrototypeActivity): ReactNode {
  if (activity.kind === "user") return <CircleUserRound size={15} />;
  if (activity.kind === "thinking") return <Brain size={15} />;
  if (activity.kind === "memory") return <MemoryStick size={15} />;
  if (activity.kind === "session") return <History size={15} />;
  if (activity.kind === "affect") return <HeartPulse size={15} />;
  if (activity.kind === "focus") return <Target size={15} />;
  if (activity.kind === "answer") return <Sparkles size={15} />;
  if (activity.kind === "background") return <Clock3 size={15} />;
  if (activity.kind === "orientation") return <Radio size={15} />;
  if (activity.kind === "action") return <Search size={15} />;
  if (activity.kind === "completion") return <Check size={15} />;
  return <Activity size={15} />;
}

function activitiesForScenario(scenario: PrototypeScenario): PrototypeActivity[] {
  if (scenario === "empty" || scenario === "loading") return [];
  if (scenario === "streaming") {
    return prototypeActivities
      .filter((activity) => activity.id !== "activity_answer" && activity.id !== "activity_completion" && activity.id !== "activity_background")
      .map((activity) => activity.id === "activity_thinking_3" ? { ...activity, phase: "streaming" as const } : activity);
  }
  if (scenario === "error") return prototypeActivities.filter((activity) => activity.id !== "activity_answer" && activity.id !== "activity_completion" && activity.id !== "activity_background");
  return prototypeActivities;
}

type FlowItem =
  | { type: "activity"; key: string; activity: PrototypeActivity }
  | { type: "stream"; key: string; activities: PrototypeActivity[] };

function groupFlowActivities(activities: PrototypeActivity[]): FlowItem[] {
  const result: FlowItem[] = [];
  let stream: PrototypeActivity[] = [];

  function flush() {
    if (!stream.length) return;
    result.push({ type: "stream", key: `stream:${stream.map((activity) => activity.id).join(":")}`, activities: stream });
    stream = [];
  }

  for (const activity of activities) {
    const conversational = activity.voice === "user" || activity.voice === "scarlet_authored";
    if (!conversational && activity.kind !== "background") {
      stream.push(activity);
      continue;
    }
    flush();
    result.push({ type: "activity", key: activity.id, activity });
  }
  flush();
  return result;
}

function shortTime(timestamp: string): string {
  return new Intl.DateTimeFormat("it-IT", { hour: "2-digit", minute: "2-digit" }).format(new Date(timestamp));
}

function relativeDate(timestamp: string): string {
  const day = new Intl.DateTimeFormat("it-IT", { day: "numeric", month: "short" }).format(new Date(timestamp));
  return day.replace(".", "");
}

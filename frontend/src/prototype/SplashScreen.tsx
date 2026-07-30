import { ScarletMascot } from "./ScarletMascot";
import "./splash.css";

export function SplashScreen({
  onGreetingEnded,
  onGreetingReady,
  onGreetingUnavailable,
  phase,
  progress,
  reviewMode,
  status
}: {
  onGreetingEnded: () => void;
  onGreetingReady: () => void;
  onGreetingUnavailable: () => void;
  phase: "loading" | "greeting" | "leaving";
  progress: number;
  reviewMode: boolean;
  status: string;
}) {
  return (
    <main className={`scarlet-splash is-${phase}`} data-splash-phase={phase}>
      <div className="scarlet-splash__motion" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <section className="scarlet-splash__content" aria-labelledby="scarlet-splash-title">
        <div className="scarlet-splash__mascot-stage">
          <span className="scarlet-splash__orbit scarlet-splash__orbit--outer" aria-hidden="true" />
          <span className="scarlet-splash__orbit scarlet-splash__orbit--inner" aria-hidden="true" />
          <ScarletMascot
            media="greeting-video"
            onGreetingEnded={onGreetingEnded}
            onGreetingReady={onGreetingReady}
            onGreetingUnavailable={onGreetingUnavailable}
            playGreeting={phase === "greeting"}
            state="waking"
          />
        </div>

        <div className="scarlet-splash__identity">
          <p>Il tuo spazio con</p>
          <h1 id="scarlet-splash-title">Scarlet</h1>
          <div
            aria-hidden={phase !== "loading"}
            aria-live="polite"
            className="scarlet-splash__arrival"
          >
            <div className="scarlet-splash__arrival-message">
              <span className="scarlet-splash__loader" aria-hidden="true"><i /></span>
              <strong>{status}</strong>
            </div>
            <span
              aria-label={`Caricamento ${progress}%`}
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={progress}
              className="scarlet-splash__arrival-line"
              role="progressbar"
            >
              <i style={{ width: `${progress}%` }} />
            </span>
            <small>{reviewMode ? "Anteprima bloccata" : `${progress}%`}</small>
          </div>
        </div>
      </section>

      <footer className="scarlet-splash__footer">
        <span>© 2026 Scarlet</span>
        <span aria-hidden="true">·</span>
        <span>Versione 1.67.0</span>
      </footer>
    </main>
  );
}

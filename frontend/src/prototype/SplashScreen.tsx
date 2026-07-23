import { ScarletMascot } from "./ScarletMascot";
import "./splash.css";

export function SplashScreen() {
  return (
    <main className="scarlet-splash">
      <div className="scarlet-splash__motion" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>

      <section className="scarlet-splash__content" aria-labelledby="scarlet-splash-title">
        <div className="scarlet-splash__mascot-stage">
          <span className="scarlet-splash__orbit scarlet-splash__orbit--outer" aria-hidden="true" />
          <span className="scarlet-splash__orbit scarlet-splash__orbit--inner" aria-hidden="true" />
          <ScarletMascot media="greeting-video" state="waking" />
        </div>

        <div className="scarlet-splash__identity">
          <p>Il tuo spazio con</p>
          <h1 id="scarlet-splash-title">Scarlet</h1>
          <strong>Sto arrivando.</strong>
        </div>
      </section>

      <div className="scarlet-splash__arrival" aria-live="polite">
        <span className="scarlet-splash__arrival-line" aria-hidden="true"><i /></span>
        <small>Mi sto ricomponendo</small>
      </div>
    </main>
  );
}

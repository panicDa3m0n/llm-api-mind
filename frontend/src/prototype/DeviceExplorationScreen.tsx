import {
  Activity,
  BatteryCharging,
  Bell,
  Braces,
  Crosshair,
  Database,
  Gauge,
  MapPin,
  Network,
  RefreshCcw,
  Smartphone,
  Vibrate
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  fetchDeviceExplorationSummary,
  fetchDeviceObservations
} from "../api";
import { DeviceExplorationController } from "../deviceExploration";
import type {
  DeviceExplorationSummary,
  DeviceObservationInput
} from "../types";
import { AndroidSpeechLab } from "./AndroidSpeechLab";

export function DeviceExplorationScreen() {
  const controllerRef = useRef<DeviceExplorationController | null>(null);
  const [deviceId, setDeviceId] = useState("inizializzazione");
  const [runId, setRunId] = useState("inizializzazione");
  const [status, setStatus] = useState("Preparo il laboratorio");
  const [observations, setObservations] = useState<DeviceObservationInput[]>([]);
  const [summary, setSummary] = useState<DeviceExplorationSummary | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new DeviceExplorationController({
      onObservation: (observation) => {
        if (!active) return;
        setObservations((current) => [observation, ...current].slice(0, 160));
      },
      onStatus: (nextStatus) => {
        if (active) setStatus(nextStatus);
      }
    });
    controllerRef.current = controller;
    void controller
      .start()
      .then(async () => {
        if (!active) return;
        setDeviceId(controller.deviceId);
        setRunId(controller.runId);
        await refresh(controller.deviceId, controller.runId);
      })
      .catch((error) => {
        if (active) {
          setStatus(
            error instanceof Error ? error.message : "Avvio probe non riuscito"
          );
        }
      });

    return () => {
      active = false;
      controllerRef.current = null;
      void controller.stop();
    };
  }, []);

  const probeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const observation of observations) {
      counts[observation.probe] = (counts[observation.probe] ?? 0) + 1;
    }
    return counts;
  }, [observations]);

  async function refresh(
    targetDeviceId = deviceId,
    targetRunId = runId
  ): Promise<void> {
    if (targetDeviceId === "inizializzazione") return;
    const [history, nextSummary] = await Promise.all([
      fetchDeviceObservations({ deviceId: targetDeviceId, limit: 160 }),
      fetchDeviceExplorationSummary({
        deviceId: targetDeviceId,
        runId: targetRunId
      })
    ]);
    setObservations(history.observations);
    setSummary(nextSummary);
    setStatus(`Storico sincronizzato · ${history.total} osservazioni device`);
  }

  async function runAction(
    label: string,
    operation: (controller: DeviceExplorationController) => Promise<void>
  ): Promise<void> {
    const controller = controllerRef.current;
    if (!controller || busyAction) return;
    setBusyAction(label);
    setStatus(`${label} in corso`);
    try {
      await operation(controller);
      await controller.flush();
      await refresh(controller.deviceId, controller.runId);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : `${label} non riuscito`);
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section
      className="scarlet-screen scarlet-device-lab"
      data-testid="device-exploration-screen"
    >
      <header className="scarlet-screen__intro scarlet-device-lab__intro">
        <div>
          <p><Smartphone aria-hidden="true" size={15} /> Device Exploration Layer</p>
          <h1>Scopriamo cosa può percepire questo device.</h1>
          <span>
            Laboratorio isolato: questi dati non entrano nella memoria o nel
            contesto di Scarlet.
          </span>
        </div>
        <div className="scarlet-device-lab__live">
          <i aria-hidden="true" />
          <strong>Osservazione attiva</strong>
          <span>{status}</span>
        </div>
      </header>

      <div className="scarlet-device-lab__identity">
        <Metric
          icon={<Smartphone size={17} />}
          label="Device"
          value={shortId(deviceId)}
        />
        <Metric
          icon={<Activity size={17} />}
          label="Run"
          value={shortId(runId)}
        />
        <Metric
          icon={<Database size={17} />}
          label="Storico run"
          value={String(summary?.total ?? observations.length)}
        />
        <Metric
          icon={<Gauge size={17} />}
          label="Probe attivi"
          value={String(Object.keys(probeCounts).length)}
        />
      </div>

      <section className="scarlet-device-lab__actions" aria-label="Probe manuali">
        <ProbeButton
          detail="Identità, app, batteria, rete, permessi e canali."
          disabled={Boolean(busyAction)}
          icon={<RefreshCcw size={18} />}
          label="Nuovo snapshot"
          onClick={() =>
            void runAction("Snapshot", (controller) =>
              controller.captureSnapshot()
            )
          }
        />
        <ProbeButton
          detail="Richiede il permesso e misura precisione e latenza."
          disabled={Boolean(busyAction)}
          icon={<MapPin size={18} />}
          label="Leggi posizione"
          onClick={() =>
            void runAction("Posizione", (controller) =>
              controller.captureLocation()
            )
          }
        />
        <ProbeButton
          detail="Pianifica una notifica locale e osserva consegna e apertura."
          disabled={Boolean(busyAction)}
          icon={<Bell size={18} />}
          label="Prova notifica"
          onClick={() =>
            void runAction("Notifica", (controller) =>
              controller.testNotification()
            )
          }
        />
        <ProbeButton
          detail="Verifica una risposta fisica immediata del device."
          disabled={Boolean(busyAction)}
          icon={<Vibrate size={18} />}
          label="Prova vibrazione"
          onClick={() =>
            void runAction("Vibrazione", (controller) =>
              controller.testHaptics()
            )
          }
        />
      </section>

      <AndroidSpeechLab />

      <div className="scarlet-device-lab__grid">
        <section className="scarlet-device-lab__probes">
          <header>
            <div><p>Copertura corrente</p><h2>Segnali osservati</h2></div>
            <button
              aria-label="Aggiorna storico"
              onClick={() => void refresh()}
              type="button"
            >
              <RefreshCcw size={16} />
            </button>
          </header>
          <div>
            {[
              ["device", "Device", Smartphone],
              ["app", "Applicazione", Activity],
              ["battery", "Batteria", BatteryCharging],
              ["network", "Rete", Network],
              ["lifecycle", "Lifecycle", Activity],
              ["motion", "Movimento", Gauge],
              ["location", "Posizione", Crosshair],
              ["notifications", "Notifiche", Bell],
              ["haptics", "Attuazione aptica", Vibrate]
            ].map(([probe, label, Icon]) => (
              <article key={String(probe)}>
                <span><Icon aria-hidden="true" size={17} /></span>
                <div><strong>{String(label)}</strong><small>{probeCounts[String(probe)] ?? summary?.probe_counts[String(probe)] ?? 0} eventi</small></div>
              </article>
            ))}
          </div>
        </section>

        <section className="scarlet-device-lab__timeline">
          <header>
            <div><p>Flusso sperimentale</p><h2>Osservazioni recenti</h2></div>
            <span>{observations.length} caricate</span>
          </header>
          <div className="scarlet-device-lab__events">
            {observations.length ? observations.map((observation) => (
              <details key={observation.client_event_id}>
                <summary>
                  <span className={`is-${eventTone(observation.event_type)}`}>
                    {probeIcon(observation.probe)}
                  </span>
                  <div>
                    <strong>{humanize(observation.probe)}</strong>
                    <p>{humanize(observation.event_type)}</p>
                  </div>
                  <time>{formatTime(observation.observed_at)}</time>
                </summary>
                <div className="scarlet-device-lab__event-detail">
                  <dl>
                    <div><dt>Stato app</dt><dd>{observation.app_state ?? "n/d"}</dd></div>
                    <div><dt>Sorgente</dt><dd>{observation.source}</dd></div>
                    <div><dt>Event ID</dt><dd>{observation.client_event_id}</dd></div>
                  </dl>
                  <div>
                    <p><Braces size={14} /> Normalizzato</p>
                    <pre>{JSON.stringify(observation.normalized, null, 2)}</pre>
                  </div>
                  <div>
                    <p><Braces size={14} /> Payload grezzo</p>
                    <pre>{JSON.stringify(observation.payload, null, 2)}</pre>
                  </div>
                </div>
              </details>
            )) : (
              <p className="scarlet-product-empty">Attendo i primi segnali reali.</p>
            )}
          </div>
        </section>
      </div>

      <footer className="scarlet-device-lab__boundary">
        <Database aria-hidden="true" size={16} />
        <p>
          Registro sperimentale separato. Nessuna consegna al modello, memoria,
          focus, affect o volition.
        </p>
      </footer>
    </section>
  );
}

function Metric({
  icon,
  label,
  value
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return <article><span>{icon}</span><div><small>{label}</small><strong>{value}</strong></div></article>;
}

function ProbeButton({
  detail,
  disabled,
  icon,
  label,
  onClick
}: {
  detail: string;
  disabled: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button disabled={disabled} onClick={onClick} type="button">
      <span>{icon}</span>
      <div><strong>{label}</strong><small>{detail}</small></div>
    </button>
  );
}

function probeIcon(probe: string) {
  if (probe === "location") return <MapPin size={15} />;
  if (probe === "notifications") return <Bell size={15} />;
  if (probe === "network") return <Network size={15} />;
  if (probe === "battery") return <BatteryCharging size={15} />;
  if (probe === "motion") return <Gauge size={15} />;
  if (probe === "haptics") return <Vibrate size={15} />;
  return <Activity size={15} />;
}

function eventTone(eventType: string) {
  return eventType.endsWith("_error") ? "error" : "ok";
}

function humanize(value: string) {
  return value
    .split("_")
    .join(" ")
    .replace(/^\w/, (letter: string) => letter.toUpperCase());
}

function shortId(value: string) {
  return value.length > 18 ? `${value.slice(0, 9)}…${value.slice(-6)}` : value;
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

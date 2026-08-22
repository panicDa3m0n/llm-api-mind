import {
  AudioLines,
  CircleStop,
  Gauge,
  Mic,
  MicOff,
  RefreshCcw,
  Volume2,
  VolumeX
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  hasNativeAndroidSpeech,
  ScarletSpeech,
  type SpeechCapabilities,
  type SpeechLevelEvent,
  type SpeechResultEvent,
  type SpeechStateEvent,
  type TtsStateEvent
} from "../nativeSpeech";

type SpeechLabEvent = {
  id: number;
  source: "STT" | "TTS" | "Sistema";
  phase: string;
  elapsedMs: number;
  detail: string;
};

const DEFAULT_VOICE_TEXT =
  "Ciao, sono Scarlet. Questa voce arriva direttamente dal dispositivo Android.";

export function AndroidSpeechLab() {
  const nativeAvailable = hasNativeAndroidSpeech();
  const nextEventId = useRef(0);
  const [capabilities, setCapabilities] =
    useState<SpeechCapabilities | null>(null);
  const [status, setStatus] = useState(
    nativeAvailable ? "Interrogo i motori vocali" : "Disponibile nell'app Android"
  );
  const [recognitionPhase, setRecognitionPhase] = useState("idle");
  const [ttsPhase, setTtsPhase] = useState("idle");
  const [partialText, setPartialText] = useState("");
  const [finalText, setFinalText] = useState("");
  const [voiceText, setVoiceText] = useState(DEFAULT_VOICE_TEXT);
  const [preferOnDevice, setPreferOnDevice] = useState(true);
  const [speechRate, setSpeechRate] = useState(1);
  const [speechLevel, setSpeechLevel] = useState(0);
  const [events, setEvents] = useState<SpeechLabEvent[]>([]);

  const listening = [
    "starting",
    "ready",
    "speech_started",
    "speech_ended",
    "stopping"
  ].includes(recognitionPhase);
  const speaking = ["queued", "started"].includes(ttsPhase);
  const engineLabel = preferOnDevice && capabilities?.on_device_available
    ? "On-device"
    : "Sistema";

  function appendEvent(
    source: SpeechLabEvent["source"],
    phase: string,
    elapsedMs: number,
    detail = ""
  ) {
    const event: SpeechLabEvent = {
      id: ++nextEventId.current,
      source,
      phase,
      elapsedMs,
      detail
    };
    setEvents((current) => [event, ...current].slice(0, 40));
  }

  async function refreshCapabilities() {
    if (!nativeAvailable) return;
    try {
      const result = await ScarletSpeech.getCapabilities();
      setCapabilities(result);
      if (!result.on_device_available) setPreferOnDevice(false);
      setStatus(
        result.recognition_available
          ? "Motori vocali pronti per la prova"
          : "Riconoscimento vocale non disponibile"
      );
      appendEvent(
        "Sistema",
        "capabilities",
        0,
        `STT ${result.recognition_available ? "disponibile" : "assente"} · TTS ${result.tts_ready ? "pronto" : "in avvio"}`
      );
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  useEffect(() => {
    if (!nativeAvailable) return;
    let disposed = false;
    const handles: Array<{ remove: () => Promise<void> }> = [];

    void (async () => {
      const registered = await Promise.all([
        ScarletSpeech.addListener("speechState", (event: SpeechStateEvent) => {
          if (disposed) return;
          setRecognitionPhase(event.phase);
          setStatus(speechStatus(event));
          appendEvent("STT", event.phase, event.elapsed_ms, event.detail);
        }),
        ScarletSpeech.addListener("speechPartial", (event: SpeechResultEvent) => {
          if (disposed) return;
          setPartialText(event.text);
          appendEvent("STT", "partial", event.elapsed_ms, event.text);
        }),
        ScarletSpeech.addListener("speechFinal", (event: SpeechResultEvent) => {
          if (disposed) return;
          setFinalText(event.text);
          setPartialText("");
          if (event.text) setVoiceText(event.text);
          appendEvent("STT", "final", event.elapsed_ms, resultDetail(event));
        }),
        ScarletSpeech.addListener("speechLevel", (event: SpeechLevelEvent) => {
          if (disposed) return;
          setSpeechLevel(Math.max(0, Math.min(100, (event.rms_db + 2) * 8)));
        }),
        ScarletSpeech.addListener("ttsState", (event: TtsStateEvent) => {
          if (disposed) return;
          setTtsPhase(event.phase);
          appendEvent("TTS", event.phase, event.elapsed_ms, event.detail);
          if (event.phase === "ready") void refreshCapabilities();
        })
      ]);
      if (disposed) {
        await Promise.allSettled(registered.map((handle) => handle.remove()));
        return;
      }
      handles.push(...registered);
      await refreshCapabilities();
    })().catch((error) => {
      if (!disposed) setStatus(errorMessage(error));
    });

    return () => {
      disposed = true;
      void Promise.allSettled(handles.map((handle) => handle.remove()));
      void ScarletSpeech.cancelListening().catch(() => undefined);
      void ScarletSpeech.stopSpeaking().catch(() => undefined);
    };
  }, [nativeAvailable]);

  const latestLatency = useMemo(
    () => events.find((event) => event.elapsedMs > 0)?.elapsedMs ?? 0,
    [events]
  );

  async function startListening() {
    setPartialText("");
    setFinalText("");
    setSpeechLevel(0);
    setStatus("Apro l'ascolto Android");
    try {
      const result = await ScarletSpeech.startListening({
        locale: "it-IT",
        preferOnDevice
      });
      appendEvent("Sistema", "listening_requested", 0, result.engine);
      await refreshCapabilities();
    } catch (error) {
      setRecognitionPhase("error");
      setStatus(errorMessage(error));
      appendEvent("Sistema", "start_error", 0, errorMessage(error));
    }
  }

  async function stopListening() {
    try {
      await ScarletSpeech.stopListening();
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function cancelListening() {
    try {
      await ScarletSpeech.cancelListening();
      setPartialText("");
      setSpeechLevel(0);
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  async function speak(flush: boolean) {
    setStatus(flush ? "Avvio la voce Android" : "Accodo la frase");
    try {
      const result = await ScarletSpeech.speak({
        text: voiceText,
        locale: "it-IT",
        flush,
        rate: speechRate
      });
      appendEvent("Sistema", flush ? "speak_now" : "speak_queued", 0, result.utterance_id);
    } catch (error) {
      setTtsPhase("error");
      setStatus(errorMessage(error));
      appendEvent("Sistema", "tts_error", 0, errorMessage(error));
    }
  }

  async function stopSpeaking() {
    try {
      await ScarletSpeech.stopSpeaking();
      setTtsPhase("stopped");
    } catch (error) {
      setStatus(errorMessage(error));
    }
  }

  return (
    <section
      className="scarlet-speech-lab"
      data-native-available={nativeAvailable ? "true" : "false"}
      data-testid="android-speech-lab"
    >
      <header className="scarlet-speech-lab__header">
        <div>
          <p><AudioLines aria-hidden="true" size={15} /> Voce Android</p>
          <h2>Ascolto e risposta sul device</h2>
        </div>
        <button
          aria-label="Aggiorna capacità vocali"
          disabled={!nativeAvailable}
          onClick={() => void refreshCapabilities()}
          type="button"
        >
          <RefreshCcw size={16} />
        </button>
      </header>

      <div className="scarlet-speech-lab__status">
        <span className={nativeAvailable ? "is-ready" : "is-browser"}>
          {nativeAvailable ? <Mic size={17} /> : <MicOff size={17} />}
        </span>
        <div><strong>{status}</strong><small>Nessun dato vocale entra nel Core</small></div>
        <dl>
          <div><dt>STT</dt><dd>{capabilities?.recognition_available ? engineLabel : "n/d"}</dd></div>
          <div><dt>TTS</dt><dd>{capabilities?.tts_ready ? "Pronto" : "n/d"}</dd></div>
          <div><dt>Ultimo evento</dt><dd>{latestLatency ? `${latestLatency} ms` : "-"}</dd></div>
        </dl>
      </div>

      <div className="scarlet-speech-lab__columns">
        <section className="scarlet-speech-lab__recognition">
          <header><span><Mic size={16} /></span><div><small>Speech to text</small><strong>{humanizePhase(recognitionPhase)}</strong></div></header>
          <label className="scarlet-speech-lab__toggle">
            <input
              checked={preferOnDevice}
              disabled={!capabilities?.on_device_available || listening}
              onChange={(event) => setPreferOnDevice(event.target.checked)}
              type="checkbox"
            />
            <span>Preferisci riconoscimento on-device</span>
          </label>
          <div className="scarlet-speech-lab__level" aria-label="Livello della voce">
            <i style={{ width: `${speechLevel}%` }} />
          </div>
          <div className="scarlet-speech-lab__transcript">
            <small>Trascrizione live</small>
            <p className={partialText || finalText ? "" : "is-empty"}>
              {partialText || finalText || "In attesa della prima frase."}
            </p>
          </div>
          <div className="scarlet-speech-lab__controls">
            <button
              disabled={!nativeAvailable || listening || !capabilities?.recognition_available}
              onClick={() => void startListening()}
              type="button"
            ><Mic size={16} /> Ascolta</button>
            <button disabled={!listening} onClick={() => void stopListening()} type="button"><CircleStop size={16} /> Concludi</button>
            <button disabled={!listening} onClick={() => void cancelListening()} type="button"><MicOff size={16} /> Annulla</button>
          </div>
        </section>

        <section className="scarlet-speech-lab__synthesis">
          <header><span><Volume2 size={16} /></span><div><small>Text to speech</small><strong>{humanizePhase(ttsPhase)}</strong></div></header>
          <textarea
            aria-label="Testo da riprodurre"
            onChange={(event) => setVoiceText(event.target.value)}
            rows={4}
            value={voiceText}
          />
          <label className="scarlet-speech-lab__rate">
            <span><Gauge size={14} /> Velocità {speechRate.toFixed(2)}x</span>
            <input
              max="1.35"
              min="0.7"
              onChange={(event) => setSpeechRate(Number(event.target.value))}
              step="0.05"
              type="range"
              value={speechRate}
            />
          </label>
          <div className="scarlet-speech-lab__controls">
            <button disabled={!nativeAvailable || !capabilities?.tts_ready || !voiceText.trim()} onClick={() => void speak(true)} type="button"><Volume2 size={16} /> Riproduci</button>
            <button disabled={!nativeAvailable || !capabilities?.tts_ready || !voiceText.trim()} onClick={() => void speak(false)} type="button"><AudioLines size={16} /> Accoda</button>
            <button disabled={!speaking} onClick={() => void stopSpeaking()} type="button"><VolumeX size={16} /> Interrompi</button>
          </div>
        </section>
      </div>

      <details className="scarlet-speech-lab__events">
        <summary>Timeline vocale <span>{events.length} eventi</span></summary>
        <div>
          {events.length ? events.map((event) => (
            <article key={event.id}>
              <span>{event.source}</span>
              <strong>{humanizePhase(event.phase)}</strong>
              <time>{event.elapsedMs ? `${event.elapsedMs} ms` : "evento"}</time>
              {event.detail ? <p>{event.detail}</p> : null}
            </article>
          )) : <p className="scarlet-product-empty">La timeline è pronta.</p>}
        </div>
      </details>
    </section>
  );
}

function speechStatus(event: SpeechStateEvent): string {
  if (event.phase === "ready") return "Puoi parlare";
  if (event.phase === "speech_started") return "Voce rilevata";
  if (event.phase === "speech_ended") return "Completo la trascrizione";
  if (event.phase === "completed") return "Trascrizione completata";
  if (event.phase === "error") return `Ascolto non riuscito · ${event.detail ?? "errore"}`;
  if (event.phase === "cancelled") return "Ascolto annullato";
  return "Ascolto Android in corso";
}

function resultDetail(event: SpeechResultEvent): string {
  const confidence = event.confidences[0];
  return confidence >= 0
    ? `${event.text} · confidenza ${Math.round(confidence * 100)}%`
    : event.text;
}

function humanizePhase(value: string): string {
  return value.split("_").join(" ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && error && "message" in error) {
    return String(error.message);
  }
  return "Operazione vocale non riuscita";
}

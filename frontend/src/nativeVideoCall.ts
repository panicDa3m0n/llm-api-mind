import type { PluginListenerHandle } from "@capacitor/core";

import {
  markVideoCallSpeechStarted,
  startInteractiveVideoCall,
  stopInteractiveVideoCall,
  streamInteractiveVideoCallTurn
} from "./api";
import {
  hasNativeAndroidSpeech,
  ScarletSpeech,
  type SpeechResultEvent,
  type SpeechStateEvent,
  type TtsStateEvent
} from "./nativeSpeech";
import type {
  ScarletLiveFrame,
  ScarletStreamEvent,
  VideoCallState
} from "./types";

export type VideoCallPhase =
  | "STOPPED"
  | "CONNECTING"
  | "LISTENING"
  | "USER_SPEAKING"
  | "WAITING_FOR_SCARLET"
  | "SCARLET_SPEAKING"
  | "RECOVERING";

export type VideoCallSnapshot = {
  active: boolean;
  callId: string | null;
  sessionId: string | null;
  phase: VideoCallPhase;
  partialTranscript: string;
  lastTranscript: string;
  error: string | null;
};

export type VideoCallRuntimeEvent =
  | { kind: "state"; snapshot: VideoCallSnapshot }
  | { kind: "stream"; event: ScarletStreamEvent }
  | { kind: "frame"; frame: ScarletLiveFrame }
  | { kind: "transcript"; text: string };

type RuntimeListener = (event: VideoCallRuntimeEvent) => void;

class ScarletVideoCallRuntime {
  private snapshot: VideoCallSnapshot = {
    active: false,
    callId: null,
    sessionId: null,
    phase: "STOPPED",
    partialTranscript: "",
    lastTranscript: "",
    error: null
  };
  private listeners = new Set<RuntimeListener>();
  private nativeHandles: PluginListenerHandle[] = [];
  private listenerSetup: Promise<void> | null = null;
  private utteranceId: string | null = null;
  private captureStart: Promise<VideoCallState> | null = null;
  private processingUtterance = false;
  private ttsWaiters = new Map<
    string,
    { resolve: () => void; reject: (error: Error) => void; timer: number }
  >();

  getState(): VideoCallSnapshot {
    return { ...this.snapshot };
  }

  subscribe(listener: RuntimeListener): () => void {
    this.listeners.add(listener);
    listener({ kind: "state", snapshot: this.getState() });
    return () => this.listeners.delete(listener);
  }

  async start(sessionId: string): Promise<void> {
    if (!hasNativeAndroidSpeech()) {
      throw new Error("La videocall sperimentale richiede l'app Android.");
    }
    if (this.snapshot.active) {
      if (this.snapshot.sessionId === sessionId) return;
      throw new Error(
        "La videocall è già collegata a un'altra conversazione. Fermala prima di cambiare sessione."
      );
    }

    this.update({
      active: true,
      callId: null,
      sessionId,
      phase: "CONNECTING",
      partialTranscript: "",
      lastTranscript: "",
      error: null
    });
    let callId: string | null = null;
    try {
      await this.ensureNativeListeners();
      const call = await startInteractiveVideoCall(sessionId);
      callId = call.call_id;
      this.update({ callId: call.call_id, phase: "LISTENING" });
      await this.armListening();
    } catch (error) {
      await Promise.allSettled([
        ScarletSpeech.cancelListening(),
        ScarletSpeech.stopSpeaking(),
        ...(callId ? [stopInteractiveVideoCall(callId)] : [])
      ]);
      this.update({
        active: false,
        callId: null,
        phase: "STOPPED",
        error: errorMessage(error)
      });
      throw error;
    }
  }

  async stop(): Promise<void> {
    const callId = this.snapshot.callId;
    this.update({ active: false, phase: "STOPPED", partialTranscript: "" });
    this.processingUtterance = false;
    this.captureStart = null;
    this.utteranceId = null;
    await Promise.allSettled([
      ScarletSpeech.cancelListening(),
      ScarletSpeech.stopSpeaking(),
      ...(callId ? [stopInteractiveVideoCall(callId)] : [])
    ]);
    this.releaseTtsWaiters(new Error("Videocall stopped."));
    this.update({ callId: null, sessionId: null });
  }

  private async ensureNativeListeners(): Promise<void> {
    if (this.listenerSetup) return this.listenerSetup;
    this.listenerSetup = (async () => {
      this.nativeHandles = [
        await ScarletSpeech.addListener("speechState", (event) => {
          void this.handleSpeechState(event);
        }),
        await ScarletSpeech.addListener("speechPartial", (event) => {
          if (!this.snapshot.active) return;
          this.update({ partialTranscript: event.text });
        }),
        await ScarletSpeech.addListener("speechFinal", (event) => {
          void this.handleSpeechFinal(event);
        }),
        await ScarletSpeech.addListener("ttsState", (event) => {
          this.handleTtsState(event);
        })
      ];
    })();
    return this.listenerSetup;
  }

  private async armListening(): Promise<void> {
    if (!this.snapshot.active || this.processingUtterance) return;
    this.utteranceId = makeUtteranceId();
    this.captureStart = null;
    this.update({
      phase: "LISTENING",
      partialTranscript: "",
      error: null
    });
    await ScarletSpeech.startListening({
      locale: "it-IT",
      preferOnDevice: true
    });
  }

  private async handleSpeechState(event: SpeechStateEvent): Promise<void> {
    if (!this.snapshot.active) return;
    if (event.phase === "speech_started") {
      const callId = this.snapshot.callId;
      const utteranceId = this.utteranceId;
      if (!callId || !utteranceId || this.captureStart) return;
      this.update({ phase: "USER_SPEAKING" });
      this.captureStart = markVideoCallSpeechStarted(callId, utteranceId);
      try {
        await this.captureStart;
      } catch (error) {
        await this.recover(error);
      }
      return;
    }
    if (event.phase === "error" && !this.processingUtterance) {
      if (event.detail === "speech_timeout" || event.detail === "no_match") {
        await this.recover(null, 300);
      } else {
        await this.recover(
          new Error(`Riconoscimento vocale interrotto: ${event.detail ?? "errore"}`)
        );
      }
    }
  }

  private async handleSpeechFinal(event: SpeechResultEvent): Promise<void> {
    const transcript = event.text.trim();
    if (!this.snapshot.active || this.processingUtterance || !transcript) return;
    const callId = this.snapshot.callId;
    const sessionId = this.snapshot.sessionId;
    const utteranceId = this.utteranceId;
    if (!callId || !sessionId || !utteranceId) return;

    this.processingUtterance = true;
    this.update({
      phase: "WAITING_FOR_SCARLET",
      partialTranscript: "",
      lastTranscript: transcript,
      error: null
    });
    this.emit({ kind: "transcript", text: transcript });
    try {
      if (!this.captureStart) {
        throw new Error(
          "Il parlato è stato trascritto senza l'evento di inizio: il video non viene associato a un intervallo inventato."
        );
      }
      await this.captureStart;
      let finalAnswer = "";
      await streamInteractiveVideoCallTurn(
        callId,
        sessionId,
        utteranceId,
        transcript,
        (streamEvent) => {
          this.emit({ kind: "stream", event: streamEvent });
          if (streamEvent.event_type === "assistant.answer.completed") {
            const text = streamEvent.payload.text;
            if (typeof text === "string" && text.trim()) {
              finalAnswer = text.trim();
            }
          }
          if (streamEvent.event_type === "turn.failed") {
            const message = streamEvent.payload.message;
            if (typeof message === "string" && message) {
              this.update({ error: message });
            }
          }
        },
        (frame) => this.emit({ kind: "frame", frame })
      );
      if (!finalAnswer) {
        throw new Error(
          "Il turno si è chiuso senza una risposta finale adatta alla voce."
        );
      }
      await this.speakAnswer(finalAnswer);
      this.processingUtterance = false;
      this.captureStart = null;
      this.utteranceId = null;
      await this.armListening();
    } catch (error) {
      this.processingUtterance = false;
      this.captureStart = null;
      this.utteranceId = null;
      await this.recover(error);
    }
  }

  private async speakAnswer(answer: string): Promise<void> {
    const chunks = speechChunks(answer);
    if (chunks.length === 0) return;
    this.update({ phase: "SCARLET_SPEAKING" });
    const completions: Promise<void>[] = [];
    for (const [index, chunk] of chunks.entries()) {
      const queued = await ScarletSpeech.speak({
        text: chunk,
        locale: "it-IT",
        flush: index === 0,
        rate: 1
      });
      completions.push(this.waitForUtterance(queued.utterance_id));
    }
    await Promise.all(completions);
  }

  private waitForUtterance(utteranceId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const timer = window.setTimeout(() => {
        this.ttsWaiters.delete(utteranceId);
        reject(new Error("Android TTS non ha confermato la fine della frase."));
      }, 120_000);
      this.ttsWaiters.set(utteranceId, { resolve, reject, timer });
    });
  }

  private handleTtsState(event: TtsStateEvent): void {
    if (!event.utterance_id) return;
    const waiter = this.ttsWaiters.get(event.utterance_id);
    if (!waiter) return;
    if (event.phase === "completed") {
      window.clearTimeout(waiter.timer);
      this.ttsWaiters.delete(event.utterance_id);
      waiter.resolve();
    } else if (event.phase === "error" || event.phase === "stopped") {
      window.clearTimeout(waiter.timer);
      this.ttsWaiters.delete(event.utterance_id);
      waiter.reject(
        new Error(event.detail || `Android TTS ${event.phase}.`)
      );
    }
  }

  private async recover(error: unknown, delayMs = 800): Promise<void> {
    if (!this.snapshot.active) return;
    this.update({
      phase: "RECOVERING",
      error: error ? errorMessage(error) : null,
      partialTranscript: ""
    });
    await ScarletSpeech.cancelListening().catch(() => undefined);
    await delay(delayMs);
    if (!this.snapshot.active || this.processingUtterance) return;
    try {
      await this.armListening();
    } catch (nextError) {
      this.update({ phase: "RECOVERING", error: errorMessage(nextError) });
    }
  }

  private releaseTtsWaiters(error: Error): void {
    for (const waiter of this.ttsWaiters.values()) {
      window.clearTimeout(waiter.timer);
      waiter.reject(error);
    }
    this.ttsWaiters.clear();
  }

  private update(next: Partial<VideoCallSnapshot>): void {
    this.snapshot = { ...this.snapshot, ...next };
    this.emit({ kind: "state", snapshot: this.getState() });
  }

  private emit(event: VideoCallRuntimeEvent): void {
    for (const listener of this.listeners) listener(event);
  }
}

export const scarletVideoCall = new ScarletVideoCallRuntime();

function makeUtteranceId(): string {
  const random = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
  return `utterance-${random}`;
}

function speechChunks(text: string, maximum = 320): string[] {
  const spoken = text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[`*_#>]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!spoken) return [];
  const sentences = spoken.match(/[^.!?;:]+[.!?;:]?\s*/g) ?? [spoken];
  const chunks: string[] = [];
  let current = "";
  for (const sentence of sentences.map((item) => item.trim()).filter(Boolean)) {
    if (sentence.length > maximum) {
      if (current) chunks.push(current);
      for (let index = 0; index < sentence.length; index += maximum) {
        chunks.push(sentence.slice(index, index + maximum).trim());
      }
      current = "";
    } else if (!current || current.length + sentence.length + 1 <= maximum) {
      current = current ? `${current} ${sentence}` : sentence;
    } else {
      chunks.push(current);
      current = sentence;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Errore videocall non identificato.";
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

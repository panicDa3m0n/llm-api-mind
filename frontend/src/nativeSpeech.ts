import {
  Capacitor,
  registerPlugin,
  type PluginListenerHandle
} from "@capacitor/core";

export type SpeechCapabilities = {
  platform: "android";
  sdk: number;
  recognition_available: boolean;
  on_device_available: boolean;
  microphone_permission: "granted" | "denied" | "prompt" | "prompt-with-rationale";
  tts_ready: boolean;
  tts_engine: string;
  tts_max_input_length: number;
  locale: string;
};

export type SpeechStateEvent = {
  phase: string;
  engine: "on_device" | "system_default";
  elapsed_ms: number;
  detail?: string;
};

export type SpeechResultEvent = {
  text: string;
  alternatives: string[];
  confidences: number[];
  elapsed_ms: number;
};

export type SpeechLevelEvent = {
  rms_db: number;
  elapsed_ms: number;
};

export type TtsStateEvent = {
  phase: string;
  utterance_id: string;
  elapsed_ms: number;
  detail?: string;
};

type ScarletSpeechPlugin = {
  getCapabilities(): Promise<SpeechCapabilities>;
  startListening(options: {
    locale: string;
    preferOnDevice: boolean;
  }): Promise<{ started: boolean; engine: string; locale: string }>;
  stopListening(): Promise<{ stopping: boolean }>;
  cancelListening(): Promise<{ cancelled: boolean }>;
  speak(options: {
    text: string;
    locale: string;
    flush: boolean;
    rate: number;
  }): Promise<{
    utterance_id: string;
    queued: boolean;
    text_length: number;
    locale: string;
    rate: number;
  }>;
  stopSpeaking(): Promise<{ stopped: boolean }>;
  addListener(
    eventName: "speechState",
    listener: (event: SpeechStateEvent) => void
  ): Promise<PluginListenerHandle>;
  addListener(
    eventName: "speechPartial" | "speechFinal",
    listener: (event: SpeechResultEvent) => void
  ): Promise<PluginListenerHandle>;
  addListener(
    eventName: "speechLevel",
    listener: (event: SpeechLevelEvent) => void
  ): Promise<PluginListenerHandle>;
  addListener(
    eventName: "ttsState",
    listener: (event: TtsStateEvent) => void
  ): Promise<PluginListenerHandle>;
};

export const ScarletSpeech = registerPlugin<ScarletSpeechPlugin>(
  "ScarletSpeech"
);

export function hasNativeAndroidSpeech(): boolean {
  return Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android";
}

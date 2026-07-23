export const scarletAvatarActions = [
  "resting",
  "waking",
  "idle",
  "listening",
  "thinking",
  "speaking",
  "reacting",
  "sleeping"
] as const;

export const scarletAvatarEmotions = [
  "neutral",
  "warm",
  "curious",
  "amused",
  "joyful",
  "tender",
  "concerned",
  "surprised",
  "irritated",
  "determined",
  "tired"
] as const;

export const scarletAvatarGestures = [
  "none",
  "greet-wave",
  "wink-left",
  "wink-right",
  "nod",
  "shake-head",
  "tilt-head-left",
  "tilt-head-right",
  "hand-to-chest",
  "hand-to-chin",
  "open-palm",
  "point-left",
  "point-right",
  "small-shrug",
  "celebrate",
  "reassure"
] as const;

export type ScarletAvatarAction = (typeof scarletAvatarActions)[number];
export type ScarletAvatarEmotion = (typeof scarletAvatarEmotions)[number];
export type ScarletAvatarGesture = (typeof scarletAvatarGestures)[number];

export type ScarletAvatarFraming = "portrait" | "half-body" | "full-body";

export interface ScarletAvatarGaze {
  x: number;
  y: number;
  target?: "user" | "content" | "ambient";
}

export interface ScarletAvatarSpeech {
  active: boolean;
  amplitude?: number;
  viseme?: "sil" | "a" | "i" | "u" | "e" | "o";
}

/**
 * Model-independent intent consumed by the avatar controller. API Mind should
 * emit semantic state; the renderer remains responsible for concrete motions.
 */
export interface ScarletAvatarIntent {
  id: string;
  action?: ScarletAvatarAction;
  emotion?: ScarletAvatarEmotion;
  emotionIntensity?: number;
  gesture?: ScarletAvatarGesture;
  gaze?: ScarletAvatarGaze;
  speech?: ScarletAvatarSpeech;
  framing?: ScarletAvatarFraming;
  priority?: number;
  transitionMs?: number;
  ttlMs?: number;
  createdAtMs: number;
}

export interface ScarletAvatarFrameState {
  action: ScarletAvatarAction;
  emotion: ScarletAvatarEmotion;
  emotionIntensity: number;
  gesture: ScarletAvatarGesture;
  gaze: ScarletAvatarGaze;
  speech: ScarletAvatarSpeech;
  framing: ScarletAvatarFraming;
  transitionMs: number;
}

export const defaultScarletAvatarState: ScarletAvatarFrameState = {
  action: "idle",
  emotion: "neutral",
  emotionIntensity: 0,
  gesture: "none",
  gaze: { x: 0, y: 0, target: "user" },
  speech: { active: false, amplitude: 0, viseme: "sil" },
  framing: "half-body",
  transitionMs: 280
};

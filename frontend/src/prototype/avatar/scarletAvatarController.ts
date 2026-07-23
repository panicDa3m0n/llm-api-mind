import {
  defaultScarletAvatarState,
  type ScarletAvatarFrameState,
  type ScarletAvatarIntent
} from "./scarletAvatarContract";

const DEFAULT_PRIORITY = 0;

function clampUnit(value: number | undefined, fallback: number) {
  if (value === undefined || !Number.isFinite(value)) return fallback;
  return Math.min(1, Math.max(0, value));
}

function clampAxis(value: number | undefined, fallback: number) {
  if (value === undefined || !Number.isFinite(value)) return fallback;
  return Math.min(1, Math.max(-1, value));
}

function isActive(intent: ScarletAvatarIntent, nowMs: number) {
  if (intent.ttlMs === undefined) return true;
  return nowMs <= intent.createdAtMs + Math.max(0, intent.ttlMs);
}

/**
 * Resolves concurrent semantic intents without coupling the product UI to
 * Live2D parameter names. Higher-priority recent intents win per channel.
 */
export function resolveScarletAvatarState(
  intents: readonly ScarletAvatarIntent[],
  nowMs: number,
  baseline: ScarletAvatarFrameState = defaultScarletAvatarState
): ScarletAvatarFrameState {
  const active = intents
    .filter((intent) => isActive(intent, nowMs))
    .sort((left, right) => {
      const priorityDelta = (right.priority ?? DEFAULT_PRIORITY) - (left.priority ?? DEFAULT_PRIORITY);
      return priorityDelta || right.createdAtMs - left.createdAtMs;
    });

  const action = active.find((intent) => intent.action)?.action ?? baseline.action;
  const emotionIntent = active.find((intent) => intent.emotion);
  const gesture = active.find((intent) => intent.gesture)?.gesture ?? baseline.gesture;
  const gazeIntent = active.find((intent) => intent.gaze)?.gaze;
  const speechIntent = active.find((intent) => intent.speech)?.speech;
  const framing = active.find((intent) => intent.framing)?.framing ?? baseline.framing;
  const transitionMs = active.find((intent) => intent.transitionMs !== undefined)?.transitionMs;

  return {
    action,
    emotion: emotionIntent?.emotion ?? baseline.emotion,
    emotionIntensity: clampUnit(emotionIntent?.emotionIntensity, baseline.emotionIntensity),
    gesture,
    gaze: gazeIntent
      ? {
          x: clampAxis(gazeIntent.x, baseline.gaze.x),
          y: clampAxis(gazeIntent.y, baseline.gaze.y),
          target: gazeIntent.target ?? baseline.gaze.target
        }
      : baseline.gaze,
    speech: speechIntent
      ? {
          active: speechIntent.active,
          amplitude: clampUnit(speechIntent.amplitude, 0),
          viseme: speechIntent.viseme ?? (speechIntent.active ? undefined : "sil")
        }
      : baseline.speech,
    framing,
    transitionMs: Math.max(0, transitionMs ?? baseline.transitionMs)
  };
}

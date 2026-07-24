import { useCallback, useEffect, useRef, useState } from "react";

import "./splash.css";

import type { ScarletAvatarAction } from "./avatar/scarletAvatarContract";

export type ScarletMascotState = Extract<
  ScarletAvatarAction,
  "resting" | "waking" | "listening" | "thinking" | "speaking"
>;

const GREETING_PLAYBACK_RATE = 1;
const GREETING_VISIBLE_FRACTION = 0.52;

export function ScarletMascot({
  state = "waking",
  media = "portrait",
  onGreetingEnded,
  onGreetingReady,
  onGreetingUnavailable,
  playGreeting = false
}: {
  state?: ScarletMascotState;
  media?: "portrait" | "greeting-video";
  onGreetingEnded?: () => void;
  onGreetingReady?: () => void;
  onGreetingUnavailable?: () => void;
  playGreeting?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const greetingCompleteRef = useRef(false);
  const [videoReady, setVideoReady] = useState(false);
  const [videoFailed, setVideoFailed] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(() =>
    typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handleChange = () => setReduceMotion(query.matches);

    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, []);

  const showGreetingVideo = media === "greeting-video" && !reduceMotion && !videoFailed;
  const markVideoReady = useCallback(() => {
    setVideoReady(true);
    onGreetingReady?.();
  }, [onGreetingReady]);
  const markVideoUnavailable = useCallback(() => {
    setVideoFailed(true);
    onGreetingUnavailable?.();
  }, [onGreetingUnavailable]);
  const finishGreeting = useCallback(() => {
    if (greetingCompleteRef.current) return;
    greetingCompleteRef.current = true;
    videoRef.current?.pause();
    onGreetingEnded?.();
  }, [onGreetingEnded]);
  const handleGreetingTimeUpdate = useCallback(() => {
    const video = videoRef.current;
    if (
      !video ||
      !Number.isFinite(video.duration) ||
      video.duration <= 0
    ) {
      return;
    }

    if (video.currentTime >= video.duration * GREETING_VISIBLE_FRACTION) {
      finishGreeting();
    }
  }, [finishGreeting]);

  useEffect(() => {
    if (media === "greeting-video" && reduceMotion) {
      onGreetingUnavailable?.();
    }
  }, [media, onGreetingUnavailable, reduceMotion]);

  useEffect(() => {
    const video = videoRef.current;
    if (!showGreetingVideo || !video) return;

    video.pause();
    if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      markVideoReady();
      return;
    }

    video.load();
  }, [markVideoReady, showGreetingVideo]);

  useEffect(() => {
    const video = videoRef.current;
    if (!showGreetingVideo || !video) return;

    if (!playGreeting) {
      video.pause();
      greetingCompleteRef.current = false;
      video.defaultPlaybackRate = GREETING_PLAYBACK_RATE;
      video.playbackRate = GREETING_PLAYBACK_RATE;
      if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
        video.currentTime = 0;
      }
      return;
    }

    video.currentTime = 0;
    greetingCompleteRef.current = false;
    video.defaultPlaybackRate = GREETING_PLAYBACK_RATE;
    video.playbackRate = GREETING_PLAYBACK_RATE;
    void video.play().catch(markVideoUnavailable);
  }, [markVideoUnavailable, playGreeting, showGreetingVideo]);

  return (
    <div
      aria-label="Scarlet si sta risvegliando"
      className={`scarlet-mascot is-${state}${media === "greeting-video" ? " has-video" : ""}`}
      role="img"
    >
      <span className="scarlet-mascot__aura" aria-hidden="true" />
      <img
        alt=""
        className="scarlet-mascot__portrait"
        draggable="false"
        fetchPriority="high"
        src="/prototype/scarlet-character-v1.png"
      />
      {showGreetingVideo ? (
        <video
          aria-hidden="true"
          className={`scarlet-mascot__video${videoReady && playGreeting ? " is-ready" : ""}`}
          disablePictureInPicture
          muted
          onCanPlay={markVideoReady}
          onEnded={finishGreeting}
          onError={markVideoUnavailable}
          onLoadedData={markVideoReady}
          onPlaying={markVideoReady}
          onTimeUpdate={handleGreetingTimeUpdate}
          playsInline
          preload="auto"
          ref={videoRef}
          tabIndex={-1}
        >
          <source
            src="/prototype/avatar/static/motion/scarlet-startup-greeting-happyhorse-v1.mp4"
            type="video/mp4"
          />
        </video>
      ) : null}
      <span className="scarlet-mascot__light" aria-hidden="true" />
      <span className="scarlet-mascot__shadow" aria-hidden="true" />
    </div>
  );
}

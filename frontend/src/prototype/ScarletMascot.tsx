import { useEffect, useState } from "react";

import "./splash.css";

import type { ScarletAvatarAction } from "./avatar/scarletAvatarContract";

const GREETING_VIDEO_LOOP_START_SECONDS = 2;

export type ScarletMascotState = Extract<
  ScarletAvatarAction,
  "resting" | "waking" | "listening" | "thinking" | "speaking"
>;

export function ScarletMascot({
  state = "waking",
  media = "portrait"
}: {
  state?: ScarletMascotState;
  media?: "portrait" | "greeting-video";
}) {
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
          autoPlay
          className={`scarlet-mascot__video${videoReady ? " is-ready" : ""}`}
          disablePictureInPicture
          muted
          onCanPlay={() => setVideoReady(true)}
          onEnded={(event) => {
            event.currentTarget.currentTime = GREETING_VIDEO_LOOP_START_SECONDS;
            void event.currentTarget.play();
          }}
          onError={() => setVideoFailed(true)}
          playsInline
          preload="auto"
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

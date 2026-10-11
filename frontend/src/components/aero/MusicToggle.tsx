import { useEffect, useRef, useState } from "react";

import "./MusicToggle.css";
import "./OrbButton.css";

// Local, gitignored track (see AGENTS.md "Background music"). Drop an mp3 at frontend/public/audio/bgm.mp3.
const MUSIC_SRC = "/audio/bgm.mp3";
const STORAGE_KEY = "music";
const TARGET_VOLUME = 0.25;
const FADE_MS = 1200;

type MusicState = "off" | "on" | "unavailable";

function readPreference(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

function savePreference(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // Storage blocked: music still works for this visit.
  }
}

// Ramp volume smoothly so music never starts or stops abruptly.
function fadeTo(audio: HTMLAudioElement, target: number, onDone?: () => void) {
  const start = audio.volume;
  const startedAt = performance.now();

  function step(now: number) {
    const progress = Math.min(1, (now - startedAt) / FADE_MS);
    audio.volume = start + (target - start) * progress;
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      onDone?.();
    }
  }

  requestAnimationFrame(step);
}

// Soft looping background music. Off by default; browsers only allow audio after a user gesture,
// so a saved "on" preference resumes on the visitor's first click or key press.
function MusicToggle() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<MusicState>("off");

  function getAudio(): HTMLAudioElement {
    if (!audioRef.current) {
      const audio = new Audio(MUSIC_SRC);
      audio.loop = true;
      audio.volume = 0;
      audio.addEventListener("error", () => setState("unavailable"));
      audioRef.current = audio;
    }
    return audioRef.current;
  }

  function play() {
    const audio = getAudio();
    audio
      .play()
      .then(() => {
        setState("on");
        fadeTo(audio, TARGET_VOLUME);
      })
      .catch(() => {
        // Blocked (no user gesture yet) or the file is missing; the error listener covers the latter.
      });
  }

  function stop() {
    const audio = audioRef.current;
    setState("off");
    if (audio) {
      fadeTo(audio, 0, () => audio.pause());
    }
  }

  // Check the track exists. Unknown paths fall back to index.html in dev, so check the content type.
  useEffect(() => {
    const controller = new AbortController();
    fetch(MUSIC_SRC, { method: "HEAD", signal: controller.signal })
      .then((response) => {
        const type = response.headers.get("content-type") ?? "";
        if (!response.ok || !type.startsWith("audio")) {
          setState("unavailable");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setState("unavailable");
        }
      });
    return () => controller.abort();
  }, []);

  // Resume a saved "on" preference at the first user interaction (autoplay needs a gesture).
  const playRef = useRef(play);
  useEffect(() => {
    playRef.current = play;
  });
  useEffect(() => {
    if (!readPreference()) {
      return;
    }

    const resume = () => playRef.current();
    window.addEventListener("pointerdown", resume, { once: true });
    window.addEventListener("keydown", resume, { once: true });

    return () => {
      window.removeEventListener("pointerdown", resume);
      window.removeEventListener("keydown", resume);
    };
  }, []);

  useEffect(() => () => audioRef.current?.pause(), []);

  function handleClick() {
    if (state === "on") {
      stop();
      savePreference(false);
    } else {
      play();
      savePreference(true);
    }
  }

  const label =
    state === "unavailable"
      ? "Background music file not found"
      : state === "on"
        ? "Turn background music off"
        : "Turn background music on";

  return (
    <button
      type="button"
      className={`orb-button music-toggle${state === "on" ? " is-playing" : ""}`}
      onClick={handleClick}
      disabled={state === "unavailable"}
      aria-label={label}
      aria-pressed={state === "on"}
      title={label}
    >
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path
          fill="currentColor"
          d="M9 18.5a2.5 2.5 0 1 1-2-2.45V6l11-2.5v11a2.5 2.5 0 1 1-2-2.45V7.1L9 8.7z"
        />
        {state !== "on" && (
          <path d="M3 3l18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        )}
      </svg>
    </button>
  );
}

export default MusicToggle;

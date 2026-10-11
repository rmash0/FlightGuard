import { useEffect, useState } from "react";

import "./ThemeToggle.css";

// Clicking the toggle cycles through themes in this order.
const THEMES = ["light", "dark", "aquarium"] as const;
type Theme = (typeof THEMES)[number];

const THEME_LABELS: Record<Theme, string> = {
  light: "Day",
  dark: "Night",
  aquarium: "Aquarium",
};

// Same key as the pre-render script in index.html.
const STORAGE_KEY = "theme";

function isTheme(value: string | undefined | null): value is Theme {
  return THEMES.includes(value as Theme);
}

function readTheme(): Theme {
  const current = document.documentElement.dataset.theme;
  return isTheme(current) ? current : "light";
}

function readSavedTheme(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  const nextTheme = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  // Follow the OS light/dark setting until the user picks a theme themselves.
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = (event: MediaQueryListEvent) => {
      if (!readSavedTheme()) {
        setTheme(event.matches ? "dark" : "light");
      }
    };

    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  function handleClick() {
    setTheme(nextTheme);
    try {
      localStorage.setItem(STORAGE_KEY, nextTheme);
    } catch {
      // Storage blocked (private mode etc.): theme still applies for this visit.
    }
  }

  const label = `${THEME_LABELS[theme]} theme. Switch to ${THEME_LABELS[nextTheme].toLowerCase()}`;

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={handleClick}
      aria-label={label}
      title={label}
    >
      {theme === "dark" && <MoonIcon />}
      {theme === "light" && <SunIcon />}
      {theme === "aquarium" && <FishIcon />}
    </button>
  );
}

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <circle cx="12" cy="12" r="5" fill="currentColor" />
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
      </g>
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path
        fill="currentColor"
        d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1z"
      />
    </svg>
  );
}

function FishIcon() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
      <path
        fill="currentColor"
        d="M3 12c3-5 9-6.5 13-3.5L20 5v14l-4-3.5C12 18.5 6 17 3 12z"
      />
      <circle cx="7.5" cy="11" r="1.2" fill="#fff" />
    </svg>
  );
}

export default ThemeToggle;

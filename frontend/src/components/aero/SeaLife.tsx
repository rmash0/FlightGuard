// Glossy tropical fish swimming across the screen in the aquarium theme.

type FishKind = "clown" | "tang" | "yellow" | "gramma" | "chromis" | "pink";

// Deterministic school: vertical position, size, swim duration/delay and direction.
const FISH: Array<{
  kind: FishKind;
  top: string;
  size: number;
  duration: number;
  delay: number;
  leftward: boolean;
}> = [
  { kind: "clown", top: "22%", size: 58, duration: 34, delay: -6, leftward: false },
  { kind: "tang", top: "40%", size: 76, duration: 46, delay: -22, leftward: true },
  { kind: "yellow", top: "56%", size: 48, duration: 28, delay: -14, leftward: false },
  { kind: "gramma", top: "66%", size: 42, duration: 31, delay: -2, leftward: true },
  { kind: "chromis", top: "14%", size: 40, duration: 40, delay: -30, leftward: false },
  { kind: "pink", top: "48%", size: 50, duration: 36, delay: -9, leftward: false },
  { kind: "chromis", top: "30%", size: 34, duration: 26, delay: -18, leftward: true },
  { kind: "clown", top: "72%", size: 40, duration: 30, delay: -24, leftward: false },
  { kind: "yellow", top: "34%", size: 36, duration: 38, delay: -4, leftward: true },
];

function Fish({ kind }: { kind: FishKind }) {
  return (
    <svg viewBox="0 0 64 40" className={`sea-fish__body sea-fish__body--${kind}`}>
      <defs>
        <radialGradient id={`fish-${kind}`} cx="40%" cy="35%" r="70%">
          <stop offset="0" stopColor="var(--fish-light)" />
          <stop offset="1" stopColor="var(--fish-dark)" />
        </radialGradient>
        {kind === "gramma" && (
          <linearGradient id="fish-gramma-split" x1="1" y1="0" x2="0" y2="0">
            <stop offset="0.5" stopColor="#b45cff" />
            <stop offset="0.5" stopColor="#ffd23f" />
          </linearGradient>
        )}
      </defs>
      {/* Tail */}
      <path d="M12 20 L0 6 L3 20 L0 34 Z" fill="var(--fish-tail)" />
      {/* Body */}
      <ellipse
        cx="34"
        cy="20"
        rx="24"
        ry="15"
        fill={kind === "gramma" ? "url(#fish-gramma-split)" : `url(#fish-${kind})`}
      />
      {kind === "clown" && (
        <g fill="#fff" opacity="0.95">
          <path d="M24 6.5 Q28 20 24 33.5 L29 34.8 Q32.5 20 29 5.2 Z" />
          <path d="M42 6 Q45 20 42 34 L46 33 Q48.5 20 46 7 Z" />
        </g>
      )}
      {/* Fin */}
      <path d="M30 8 Q36 0 44 7 Z" fill="var(--fish-tail)" opacity="0.85" />
      {/* Eye */}
      <circle cx="49" cy="17" r="3.6" fill="#fff" />
      <circle cx="50" cy="17" r="1.9" fill="#0b2233" />
      {/* Gloss */}
      <ellipse cx="36" cy="11" rx="13" ry="4" fill="#fff" opacity="0.5" />
    </svg>
  );
}

function SeaLife() {
  return (
    <div className="sea-life" aria-hidden="true">
      {FISH.map((fish, i) => (
        <div
          key={i}
          className={`sea-fish${fish.leftward ? " sea-fish--leftward" : ""}`}
          style={{
            top: fish.top,
            width: fish.size,
            animationDuration: `${fish.duration}s`,
            animationDelay: `${fish.delay}s`,
          }}
        >
          <div className="sea-fish__bob">
            <Fish kind={fish.kind} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default SeaLife;

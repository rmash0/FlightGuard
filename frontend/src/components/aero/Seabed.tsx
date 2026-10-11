// Decorative tropical reef for the aquarium theme (replaces the city skyline):
// pale sand, vivid swaying seaweed, colorful coral, an anemone, shells and a starfish.
// Same viewBox and sizing as Skyline.

const WIDTH = 1440;
const HEIGHT = 240;

// Seaweed stalks: base x, height, color, sway duration (s) and delay (s) so they don't move in sync.
const SEAWEED = [
  { x: 36, h: 130, tone: "green", duration: 5.5, delay: -1 },
  { x: 58, h: 92, tone: "lime", duration: 4.8, delay: -3 },
  { x: 236, h: 155, tone: "green", duration: 6.2, delay: -2 },
  { x: 258, h: 110, tone: "lime", duration: 5.1, delay: -4 },
  { x: 506, h: 100, tone: "teal", duration: 4.6, delay: -0.5 },
  { x: 744, h: 145, tone: "green", duration: 6, delay: -2.5 },
  { x: 766, h: 104, tone: "lime", duration: 5.3, delay: -1.5 },
  { x: 990, h: 128, tone: "teal", duration: 5.8, delay: -3.5 },
  { x: 1290, h: 160, tone: "green", duration: 6.4, delay: -1.2 },
  { x: 1312, h: 115, tone: "lime", duration: 5, delay: -2.8 },
  { x: 1412, h: 96, tone: "teal", duration: 4.7, delay: -0.8 },
];

// Anemone tentacles fan out from (x, base).
const ANEMONE = { x: 880, base: 222, count: 9, length: 30 };

// A wavy stalk rising from (x, HEIGHT).
function seaweedPath(x: number, h: number): string {
  const top = HEIGHT - h;
  return `M${x} ${HEIGHT} C${x - 14} ${HEIGHT - h / 3}, ${x + 14} ${HEIGHT - (2 * h) / 3}, ${x} ${top}`;
}

function anemoneTentacle(i: number): string {
  const { x, base, count, length } = ANEMONE;
  const angle = Math.PI * (0.15 + (0.7 * i) / (count - 1));
  const tipX = x - Math.cos(angle) * length;
  const tipY = base - Math.sin(angle) * length;
  const midX = (x + tipX) / 2 + (i % 2 === 0 ? 4 : -4);
  return `M${x} ${base} Q${midX} ${(base + tipY) / 2} ${tipX.toFixed(1)} ${tipY.toFixed(1)}`;
}

function Seabed() {
  return (
    <svg
      className="seabed"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="seabed-sand" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff7d6" />
          <stop offset="1" stopColor="#f1d389" />
        </linearGradient>
        <linearGradient id="seabed-weed-green" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#b9ff6e" />
          <stop offset="1" stopColor="#2dbb52" />
        </linearGradient>
        <linearGradient id="seabed-weed-lime" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#e8ff7a" />
          <stop offset="1" stopColor="#7ed321" />
        </linearGradient>
        <linearGradient id="seabed-weed-teal" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8affd8" />
          <stop offset="1" stopColor="#14a88c" />
        </linearGradient>
        <radialGradient id="seabed-brain" cx="40%" cy="30%" r="75%">
          <stop offset="0" stopColor="#fff3a0" />
          <stop offset="1" stopColor="#f5b800" />
        </radialGradient>
      </defs>

      {/* Far dune */}
      <path
        className="seabed__dune-back"
        d="M0 198 Q180 168 360 190 T720 184 T1080 192 T1440 178 L1440 240 L0 240 Z"
      />

      {/* Rocks */}
      <g className="seabed__rocks">
        <ellipse cx="150" cy="222" rx="46" ry="26" />
        <ellipse cx="190" cy="228" rx="30" ry="18" />
        <ellipse cx="1180" cy="226" rx="38" ry="22" />
      </g>

      {/* Seaweed sways from its base */}
      <g className="seabed__seaweed">
        {SEAWEED.map((weed) => (
          <path
            key={weed.x}
            d={seaweedPath(weed.x, weed.h)}
            stroke={`url(#seabed-weed-${weed.tone})`}
            style={{
              transformOrigin: `${weed.x}px ${HEIGHT}px`,
              animationDuration: `${weed.duration}s`,
              animationDelay: `${weed.delay}s`,
            }}
          />
        ))}
      </g>

      {/* Branching coral: pink, red-orange */}
      <g className="seabed__coral seabed__coral--pink">
        <path d="M400 240 L400 192 M400 212 L382 188 M400 202 L420 178 M382 188 L374 172 M420 178 L432 164" />
        <path d="M1110 240 L1110 188 M1110 208 L1090 184 M1110 198 L1130 176 M1090 184 L1084 168" />
      </g>
      <g className="seabed__coral seabed__coral--orange">
        <path d="M640 240 L640 204 M640 220 L624 196 M640 214 L656 192" />
        <path d="M1380 240 L1380 200 M1380 218 L1366 194 M1380 210 L1396 190" />
      </g>

      {/* Fan coral */}
      <g className="seabed__coral seabed__coral--purple">
        <path d="M600 240 L600 196 M600 218 L580 182 M600 212 L620 178 M600 204 L594 168 M600 204 L610 166" />
        <path d="M120 240 L120 206 M120 224 L104 196 M120 218 L136 192 M120 212 L116 184" />
      </g>

      {/* Brain coral */}
      <path className="seabed__brain" d="M300 232 A34 26 0 0 1 368 232 Z" fill="url(#seabed-brain)" />
      <path className="seabed__brain-lines" d="M310 228 Q322 216 334 226 T358 224 M318 220 Q330 210 344 218" />

      {/* Tube coral */}
      <g className="seabed__tubes">
        <rect x="1210" y="186" width="14" height="54" rx="7" />
        <rect x="1228" y="168" width="14" height="72" rx="7" />
        <rect x="1246" y="194" width="14" height="46" rx="7" />
      </g>

      {/* Anemone */}
      <g className="seabed__anemone">
        {Array.from({ length: ANEMONE.count }, (_, i) => (
          <path key={i} d={anemoneTentacle(i)} />
        ))}
      </g>

      {/* Near sand */}
      <path
        d="M0 222 Q240 206 480 220 T960 216 T1440 214 L1440 240 L0 240 Z"
        fill="url(#seabed-sand)"
      />

      {/* Shells */}
      <g className="seabed__shells">
        <path d="M470 236 a10 9 0 0 1 20 0 Z" />
        <path d="M1030 238 a8 7 0 0 1 16 0 Z" />
      </g>

      {/* Starfish */}
      <path
        className="seabed__starfish"
        d="M830 214 L834 224 L845 225 L837 232 L840 242 L830 236 L820 242 L823 232 L815 225 L826 224 Z"
      />
    </svg>
  );
}

export default Seabed;

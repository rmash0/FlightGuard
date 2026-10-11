// Decorative seabed for the aquarium theme (replaces the city skyline): sand dunes,
// swaying seaweed, coral, rocks and a starfish. Same viewBox and sizing as Skyline.

const WIDTH = 1440;
const HEIGHT = 240;

// Seaweed stalks: base x, height, sway duration (s) and delay (s) so they don't move in sync.
const SEAWEED = [
  { x: 40, h: 120, duration: 5.5, delay: -1 },
  { x: 62, h: 85, duration: 4.8, delay: -3 },
  { x: 250, h: 150, duration: 6.2, delay: -2 },
  { x: 272, h: 105, duration: 5.1, delay: -4 },
  { x: 520, h: 95, duration: 4.6, delay: -0.5 },
  { x: 760, h: 140, duration: 6, delay: -2.5 },
  { x: 782, h: 100, duration: 5.3, delay: -1.5 },
  { x: 1010, h: 125, duration: 5.8, delay: -3.5 },
  { x: 1300, h: 155, duration: 6.4, delay: -1.2 },
  { x: 1322, h: 110, duration: 5, delay: -2.8 },
  { x: 1410, h: 90, duration: 4.7, delay: -0.8 },
];

// A wavy stalk rising from (x, HEIGHT).
function seaweedPath(x: number, h: number): string {
  const top = HEIGHT - h;
  return `M${x} ${HEIGHT} C${x - 14} ${HEIGHT - h / 3}, ${x + 14} ${HEIGHT - (2 * h) / 3}, ${x} ${top}`;
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
          <stop offset="0" stopColor="#f4e2b0" />
          <stop offset="1" stopColor="#c9a76a" />
        </linearGradient>
        <linearGradient id="seabed-weed" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8ff07a" />
          <stop offset="1" stopColor="#1f8f4a" />
        </linearGradient>
      </defs>

      {/* Far dune */}
      <path
        className="seabed__dune-back"
        d="M0 200 Q180 170 360 192 T720 186 T1080 194 T1440 180 L1440 240 L0 240 Z"
      />

      {/* Rocks */}
      <g className="seabed__rocks">
        <ellipse cx="150" cy="222" rx="46" ry="26" />
        <ellipse cx="190" cy="228" rx="30" ry="18" />
        <ellipse cx="900" cy="224" rx="52" ry="28" />
        <ellipse cx="1180" cy="226" rx="38" ry="22" />
      </g>

      {/* Seaweed sways from its base */}
      <g className="seabed__seaweed">
        {SEAWEED.map((weed) => (
          <path
            key={weed.x}
            d={seaweedPath(weed.x, weed.h)}
            style={{
              transformOrigin: `${weed.x}px ${HEIGHT}px`,
              animationDuration: `${weed.duration}s`,
              animationDelay: `${weed.delay}s`,
            }}
          />
        ))}
      </g>

      {/* Branching coral */}
      <g className="seabed__coral seabed__coral--pink">
        <path d="M400 240 L400 196 M400 214 L384 192 M400 206 L418 184 M384 192 L376 178 M418 184 L428 172" />
        <path d="M1110 240 L1110 190 M1110 210 L1092 186 M1110 200 L1128 180 M1092 186 L1086 170" />
      </g>

      {/* Fan coral */}
      <g className="seabed__coral seabed__coral--purple">
        <path d="M620 240 L620 200 M620 220 L600 186 M620 214 L640 182 M620 205 L614 172 M620 205 L630 170" />
      </g>

      {/* Tube coral */}
      <g className="seabed__tubes">
        <rect x="1220" y="190" width="14" height="50" rx="7" />
        <rect x="1238" y="174" width="14" height="66" rx="7" />
        <rect x="1256" y="198" width="14" height="42" rx="7" />
      </g>

      {/* Near sand */}
      <path
        d="M0 222 Q240 206 480 220 T960 216 T1440 214 L1440 240 L0 240 Z"
        fill="url(#seabed-sand)"
      />

      {/* Starfish */}
      <path
        className="seabed__starfish"
        d="M840 214 L844 224 L855 225 L847 232 L850 242 L840 236 L830 242 L833 232 L825 225 L836 224 Z"
      />
    </svg>
  );
}

export default Seabed;

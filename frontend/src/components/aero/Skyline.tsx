// Decorative city skyline for the bottom of the sky scene: glassy towers by day,
// lit windows by night, plus an airport control tower and wind turbines (eco nod).
// Geometry is generated once at module load from a fixed seed, so renders stay pure.

const WIDTH = 1440;
const HEIGHT = 240;

type Building = { x: number; w: number; h: number; antenna: boolean };
type Window = { x: number; y: number; lit: boolean };

function seededRandom(seed: number) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

const random = seededRandom(20261010);

function makeBuildings(
  fromX: number,
  toX: number,
  minW: number,
  maxW: number,
  minH: number,
  maxH: number,
): Building[] {
  const buildings: Building[] = [];
  let x = fromX;

  while (x < toX) {
    const w = Math.round(minW + random() * (maxW - minW));
    const h = Math.round(minH + random() * (maxH - minH));
    buildings.push({ x, w, h, antenna: random() < 0.3 });
    x += w + Math.round(random() * 10);
  }

  return buildings;
}

// Turbine hill starts here; keep it clear of buildings so the turbines stand against open sky.
const HILL_START_X = 1110;

// Generated across the full width (so the seeded layout stays stable), then trimmed before the hill.
const BACK_BUILDINGS = makeBuildings(-20, WIDTH, 40, 90, 70, 175).filter(
  (b) => b.x + b.w < HILL_START_X,
);
// Front row stops short of the control tower and turbine hill on the right.
const FRONT_BUILDINGS = makeBuildings(-10, 1000, 50, 105, 40, 125);

const WINDOWS: Window[] = FRONT_BUILDINGS.flatMap((b) => {
  const cols = Math.floor((b.w - 12) / 12);
  const rows = Math.floor((b.h - 16) / 16);

  return Array.from({ length: cols * rows }, (_, i) => ({
    x: b.x + 8 + (i % cols) * 12,
    y: HEIGHT - b.h + 10 + Math.floor(i / cols) * 16,
    lit: random() < 0.4,
  }));
});

const TURBINES = [
  { x: 1215, hubY: 105 },
  { x: 1305, hubY: 88 },
  { x: 1392, hubY: 92 },
];

const BLADE = "M0 0 C3 -10 3 -26 0 -38 C-2 -26 -2 -10 0 0 Z";

function Skyline() {
  return (
    <svg
      className="skyline"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <g className="skyline__back">
        {BACK_BUILDINGS.map((b) => (
          <rect key={b.x} x={b.x} y={HEIGHT - b.h} width={b.w} height={b.h} rx="2" />
        ))}
      </g>

      <g className="skyline__front">
        {FRONT_BUILDINGS.map((b) => (
          <g key={b.x}>
            <rect x={b.x} y={HEIGHT - b.h} width={b.w} height={b.h} rx="2" />
            {b.antenna && (
              <rect x={b.x + b.w / 2 - 1} y={HEIGHT - b.h - 14} width="2" height="14" />
            )}
          </g>
        ))}

        {/* Airport control tower */}
        <rect x="1040" y="122" width="14" height="118" />
        <path d="M1032 124 L1062 124 L1068 106 L1026 106 Z" />
        <rect x="1028" y="100" width="38" height="6" rx="2" />
        <rect x="1046" y="84" width="2" height="16" />
      </g>

      <g className="skyline__windows">
        {WINDOWS.map((w) => (
          <rect
            key={`${w.x}-${w.y}`}
            x={w.x}
            y={w.y}
            width="5"
            height="8"
            className={w.lit ? "is-lit" : undefined}
          />
        ))}
        <path className="is-lit" d="M1034 122 L1060 122 L1064 110 L1030 110 Z" />
      </g>

      <circle className="skyline__beacon" cx="1047" cy="82" r="3" />

      {/* Wind turbines: poles first so the hill covers their bases */}
      <g className="skyline__turbines">
        {TURBINES.map((t) => (
          <g key={t.x}>
            <path d={`M${t.x - 2} ${t.hubY} L${t.x + 2} ${t.hubY} L${t.x + 3} 220 L${t.x - 3} 220 Z`} />
            <g className="skyline__rotor" style={{ transformOrigin: `${t.x}px ${t.hubY}px` }}>
              {[0, 120, 240].map((angle) => (
                <path key={angle} d={BLADE} transform={`translate(${t.x} ${t.hubY}) rotate(${angle})`} />
              ))}
              <circle cx={t.x} cy={t.hubY} r="3.5" />
            </g>
          </g>
        ))}
      </g>

      <path
        className="skyline__hill"
        d={`M${HILL_START_X} 240 Q1250 150 ${WIDTH} 168 L${WIDTH} 240 Z`}
      />
    </svg>
  );
}

export default Skyline;

import { useState } from "react";
import { Leaf, Info } from "lucide-react";
import EcoComparison from "./EcoComparison";

import type { CabinClass, Emissions } from "../../types/api";
import GlassPanel from "../aero/GlassPanel";

type EmissionsCardProps = {
  emissions: Emissions | null;
};

const CABINS: { value: CabinClass; label: string }[] = [
  { value: "economy", label: "Economy" },
  { value: "premium_economy", label: "Premium Economy" },
  { value: "business", label: "Business" },
  { value: "first", label: "First" },
];

const TIER_LABELS = {
  flight: "Flight estimate",
  route: "Route estimate",
  distance: "Distance estimate",
  fallback: "Rough estimate",
};

function EmissionsCard({ emissions }: EmissionsCardProps) {
  const [selectedCabin, setSelectedCabin] = useState<CabinClass>("economy");

  if (!emissions) {
    return (
      <GlassPanel as="section">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Leaf size={28} color="var(--aero-leaf)" />
          <h2 style={{ color: "var(--aero-heading)", margin: 0 }}>
            Carbon Footprint
          </h2>
        </div>

        <p style={{ color: "var(--aero-text-muted)", marginBottom: 0 }}>
          CO₂ emissions are currently unavailable for this flight.
        </p>
      </GlassPanel>
    );
  }

  const co2 = emissions.co2e_kg_per_passenger[selectedCabin];
  const economyCo2 = emissions.co2e_kg_per_passenger.economy;

  const tierLabel = TIER_LABELS[emissions.estimate_tier];

  return (
    <GlassPanel
      as="section"
      style={{
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              padding: 12,
              borderRadius: "var(--aero-radius-md)",
              background: "var(--aero-glass-strong)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Leaf size={26} color="var(--aero-leaf)" />
          </div>

          <div>
            <h2
              style={{
                color: "var(--aero-heading)",
                margin: 0,
                fontSize: 22,
              }}
            >
              Carbon Footprint
            </h2>

            <p
              style={{
                color: "var(--aero-text-muted)",
                fontSize: 13,
                margin: "4px 0 0",
              }}
            >
              Environmental impact of your flight
            </p>
          </div>
        </div>

        <span
          style={{
            padding: "7px 12px",
            borderRadius: "var(--aero-radius-pill)",
            border: "1px solid var(--aero-glass-border)",
            background: "var(--aero-glass-strong)",
            color: "var(--aero-text)",
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          {tierLabel}
        </span>
      </div>

      <div style={{ textAlign: "center", padding: "12px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "center",
            gap: 8,
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: "clamp(40px, 6vw, 60px)",
              fontWeight: 800,
              letterSpacing: "-2px",
              color: "var(--aero-leaf)",
              lineHeight: 1.1,
            }}
          >
            {co2.toFixed(2)}
          </span>

          <span
            style={{
              fontSize: 20,
              color: "var(--aero-text-muted)",
              fontWeight: 600,
            }}
          >
            kg CO₂e
          </span>
        </div>

        <p
          style={{
            color: "var(--aero-text-muted)",
            margin: "10px 0 0",
            fontSize: 14,
          }}
        >
          Estimated emissions per passenger
        </p>
      </div>

      <div>
        <div
          style={{
            display: "block",
            color: "var(--aero-text)",
            fontSize: 14,
            fontWeight: 600,
            marginBottom: 10,
          }}
        >
          Cabin Class
        </div>

        <div
          role="group"
          aria-label="Cabin class"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
            gap: 10,
          }}
        >
          {CABINS.map((cabin) => {
            const active = selectedCabin === cabin.value;

            return (
              <button
                key={cabin.value}
                type="button"
                aria-pressed={active}
                onClick={() => setSelectedCabin(cabin.value)}
                style={{
                  padding: "13px 12px",
                  borderRadius: "var(--aero-radius-md)",
                  border: active
                    ? "1px solid var(--aero-accent)"
                    : "1px solid var(--aero-glass-border)",
                  background: active
                    ? "var(--aero-accent)"
                    : "var(--aero-glass-strong)",
                  color: active ? "#ffffff" : "var(--aero-text)",
                  fontSize: 13,
                  fontWeight: active ? 700 : 500,
                  cursor: "pointer",
                  transition: "all 0.2s ease",
                  boxShadow: active
                    ? "0 4px 16px rgba(30, 130, 220, 0.25)"
                    : "none",
                }}
              >
                {cabin.label}
              </button>
            );
          })}
        </div>
      </div>

      <EcoComparison
        comparisons={emissions.comparisons}
        selectedCabinCo2={co2}
        economyCo2={economyCo2}
      />

      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: 8,
          paddingTop: 16,
          borderTop: "1px solid var(--aero-glass-border)",
        }}
      >
        <Info
          size={16}
          color="var(--aero-text-muted)"
          style={{ flexShrink: 0, marginTop: 2 }}
        />

        <p
          style={{
            color: "var(--aero-text-muted)",
            fontSize: 12,
            margin: 0,
            lineHeight: 1.6,
          }}
        >
          {emissions.source === "google_tim"
            ? "Estimated using Google Travel Impact Model."
            : "Rough estimate calculated using flight distance."}{" "}
          Actual emissions may vary. Comparisons are approximate and scaled from
          the economy passenger estimate.
        </p>
      </div>
    </GlassPanel>
  );
}

export default EmissionsCard;

import { CarFront, CalendarDays, Trees, Leaf, Smartphone } from "lucide-react";
import type { EcoComparison as EcoComparisonType } from "../../types/api";

type EcoComparisonProps = {
  comparisons: EcoComparisonType[];
  selectedCabinCo2: number;
  economyCo2: number;
};

function EcoComparison({
  comparisons,
  selectedCabinCo2,
  economyCo2,
}: EcoComparisonProps) {
  if (comparisons.length === 0) {
    return null;
  }

  const ratio = economyCo2 > 0 ? selectedCabinCo2 / economyCo2 : 0;

  const getIcon = (label: string) => {
    const normalized = label.toLowerCase();

    if (normalized.includes("smartphone")) {
      return <Smartphone size={24} color="var(--aero-accent)" />;
    }

    if (normalized.includes("car")) {
      return <CarFront size={24} color="var(--aero-accent)" />;
    }

    if (normalized.includes("tree")) {
      return <Trees size={24} color="var(--aero-leaf)" />;
    }

    if (normalized.includes("day")) {
      return <CalendarDays size={24} color="var(--aero-accent)" />;
    }

    return <Leaf size={24} color="var(--aero-leaf)" />;
  };

  const formatValue = (value: number) => {
    if (value >= 100) {
      return Math.round(value).toLocaleString();
    }

    if (value >= 10) {
      return value.toFixed(1);
    }

    return value.toFixed(2);
  };

  return (
    <div>
      <h3
        style={{
          color: "var(--aero-heading)",
          fontSize: 16,
          fontWeight: 600,
          margin: "0 0 14px",
        }}
      >
        Environmental equivalents
      </h3>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 12,
        }}
      >
        {comparisons.map((comparison) => {
          const value = comparison.value * ratio;

          return (
            <div
              key={comparison.label}
              style={{
                background: "var(--aero-glass-strong)",
                border: "1px solid var(--aero-glass-border)",
                borderRadius: "var(--aero-radius-md)",
                padding: 18,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                gap: 10,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  background: "var(--aero-glass-strong)",
                }}
              >
                {getIcon(comparison.label)}
              </div>

              <span
                style={{
                  color: "var(--aero-heading)",
                  fontSize: 26,
                  fontWeight: 700,
                  letterSpacing: "-0.5px",
                }}
              >
                {formatValue(value)}
              </span>

              <span
                style={{
                  color: "var(--aero-text-muted)",
                  fontSize: 12,
                  lineHeight: 1.5,
                }}
              >
                {comparison.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default EcoComparison;

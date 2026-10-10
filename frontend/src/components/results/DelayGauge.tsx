import type { DelayPrediction, RiskLevel } from "../../types/api";
import AeroBadge, { type AeroBadgeTone } from "../aero/AeroBadge";
import "./DelayGauge.css";

const RISK: Record<RiskLevel, { label: string; tone: AeroBadgeTone }> = {
  low: { label: "Low risk", tone: "aqua" },
  medium: { label: "Medium risk", tone: "amber" },
  high: { label: "High risk", tone: "coral" },
};

// Half-circle arc; pathLength="100" lets the dash length be the percentage directly.
const ARC = "M20 100 A80 80 0 0 1 180 100";

function DelayGauge({ prediction }: { prediction: DelayPrediction }) {
  const percent = Math.round(prediction.probability_delayed * 100);
  const risk = RISK[prediction.risk];
  const minutes = prediction.estimated_delay_minutes;

  return (
    <div className={`delay-gauge delay-gauge--${prediction.risk}`}>
      <svg
        className="delay-gauge__dial"
        viewBox="0 0 200 116"
        role="img"
        aria-label={`${percent}% chance of delay, ${risk.label.toLowerCase()}`}
      >
        <path className="delay-gauge__track" d={ARC} pathLength={100} />
        <path
          className="delay-gauge__value"
          d={ARC}
          pathLength={100}
          strokeDasharray={`${percent} 100`}
        />
        <text className="delay-gauge__percent" x="100" y="88">
          {percent}%
        </text>
        <text className="delay-gauge__caption" x="100" y="108">
          chance of delay
        </text>
      </svg>

      <AeroBadge tone={risk.tone}>{risk.label}</AeroBadge>

      <p className="delay-gauge__estimate">
        {minutes > 0 ? `Expect about ${minutes} min of delay` : "Likely to leave on time"}
      </p>

      {prediction.reported_delay_minutes !== null && (
        <p className="delay-gauge__reported">
          The airline is already reporting a {prediction.reported_delay_minutes} min delay.
        </p>
      )}
    </div>
  );
}

export default DelayGauge;

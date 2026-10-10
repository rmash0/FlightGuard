import type { DelayReason } from "../../types/api";
import "./ReasonList.css";

// The "why" behind a delay prediction, highest impact first.
const IMPACT_ORDER = { high: 0, medium: 1, low: 2 };
const IMPACT_LABEL = { high: "High impact", medium: "Medium impact", low: "Low impact" };

function ReasonList({ reasons }: { reasons: DelayReason[] }) {
  if (reasons.length === 0) {
    return <p className="text-muted">No major delay factors spotted.</p>;
  }

  const sorted = [...reasons].sort((a, b) => IMPACT_ORDER[a.impact] - IMPACT_ORDER[b.impact]);

  return (
    <ul className="reason-list">
      {sorted.map((reason) => (
        <li key={`${reason.factor}-${reason.detail}`} className={`reason-list__item reason-list__item--${reason.impact}`}>
          <span className="reason-list__dot" aria-hidden="true" />
          <span className="reason-list__detail">{reason.detail}</span>
          <span className="reason-list__impact">{IMPACT_LABEL[reason.impact]}</span>
        </li>
      ))}
    </ul>
  );
}

export default ReasonList;

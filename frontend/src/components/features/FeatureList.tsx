import GlassPanel from "../aero/GlassPanel";
import { cx } from "../aero/classes";
import "./FeatureList.css";

const FEATURES = [
  {
    tone: "sky",
    title: "Delay forecast",
    text: "Weather, airport congestion and past patterns rolled into one clear risk score.",
  },
  {
    tone: "leaf",
    title: "Carbon footprint",
    text: "Your seat's estimated CO2, with comparisons that make the number real.",
  },
  {
    tone: "amber",
    title: "Live map",
    text: "Watch planes and airports across the US in real time.",
  },
];

type FeatureListProps = {
  // "compact": one row of small pills (search page). "cards": full cards with descriptions (about page).
  variant: "compact" | "cards";
};

function FeatureList({ variant }: FeatureListProps) {
  return (
    <ul className={cx("feature-list", `feature-list--${variant}`)}>
      {FEATURES.map((feature) => (
        <li key={feature.title}>
          <GlassPanel as="article" className="feature-list__item">
            <span className={`feature-list__orb feature-list__orb--${feature.tone}`} />
            {variant === "cards" ? (
              <>
                <h2>{feature.title}</h2>
                <p className="text-muted">{feature.text}</p>
              </>
            ) : (
              <span className="feature-list__title">{feature.title}</span>
            )}
          </GlassPanel>
        </li>
      ))}
    </ul>
  );
}

export default FeatureList;

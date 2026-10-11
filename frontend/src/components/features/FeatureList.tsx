import { Link } from "react-router";

import GlassPanel from "../aero/GlassPanel";
import { cx } from "../aero/classes";
import "./FeatureList.css";

const FEATURES = [
  {
    id: "delay-forecast",
    tone: "sky",
    title: "Delay forecast",
    text: "Weather, airport congestion and past patterns rolled into one clear risk score.",
    to: "/about#delay-forecast",
  },
  {
    id: "carbon-footprint",
    tone: "leaf",
    title: "Carbon footprint",
    text: "Your seat's estimated CO2, with comparisons that make the number real.",
    to: "/about#carbon-footprint",
  },
  {
    id: "live-map",
    tone: "amber",
    title: "Live map",
    text: "Watch planes and airports across the US in real time.",
    to: "/map",
  },
];

type FeatureListProps = {
  // "compact": a row of small linked pills (search page). "cards": full cards with descriptions (about page).
  variant: "compact" | "cards";
  // Card id to glow briefly, e.g. when arriving from a pill link (/about#delay-forecast).
  highlightedId?: string;
};

function FeatureList({ variant, highlightedId }: FeatureListProps) {
  return (
    <ul className={cx("feature-list", `feature-list--${variant}`)}>
      {FEATURES.map((feature) => {
        const orb = <span className={`feature-list__orb feature-list__orb--${feature.tone}`} />;

        return (
          <li key={feature.id}>
            {variant === "compact" ? (
              <Link to={feature.to} className="glass-panel feature-list__item feature-list__link">
                {orb}
                <span className="feature-list__title">{feature.title}</span>
              </Link>
            ) : (
              <GlassPanel
                as="article"
                id={feature.id}
                className={cx("feature-list__item", feature.id === highlightedId && "is-highlighted")}
              >
                {orb}
                <h2>{feature.title}</h2>
                <p className="text-muted">{feature.text}</p>
              </GlassPanel>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export default FeatureList;

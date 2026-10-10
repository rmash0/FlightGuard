import GlassPanel from "../components/aero/GlassPanel";
import FlightSearchForm from "../components/search/FlightSearchForm";
import "./SearchPage.css";

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

function SearchPage() {
  return (
    <>
      <GlassPanel as="section" className="search-hero">
        <h1>Will your flight be late?</h1>
        <p className="text-muted">
          Enter a US airline flight to see its delay risk and carbon footprint.
        </p>
        <FlightSearchForm />
      </GlassPanel>

      <ul className="search-features">
        {FEATURES.map((feature) => (
          <li key={feature.title}>
            <GlassPanel as="article" className="search-feature">
              <span className={`search-feature__orb search-feature__orb--${feature.tone}`} />
              <h2>{feature.title}</h2>
              <p className="text-muted">{feature.text}</p>
            </GlassPanel>
          </li>
        ))}
      </ul>
    </>
  );
}

export default SearchPage;

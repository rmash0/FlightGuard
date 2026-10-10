import GlassPanel from "../components/aero/GlassPanel";
import FeatureList from "../components/features/FeatureList";
import FlightSearchForm from "../components/search/FlightSearchForm";
import "./SearchPage.css";

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

      <FeatureList variant="compact" />
    </>
  );
}

export default SearchPage;

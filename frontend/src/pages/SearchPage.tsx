import GlassPanel from "../components/aero/GlassPanel";
import DemoFlightList from "../components/demo/DemoFlightList";
import FeatureList from "../components/features/FeatureList";
import FlightSearchForm from "../components/search/FlightSearchForm";
import { USE_SAMPLE_DATA } from "../config";
import "./SearchPage.css";

function SearchPage() {
  return (
    <>
      <GlassPanel as="section" className="search-hero">
        <h1>Will Your Flight Be Late?</h1>
        <p className="text-muted">
          Enter a US airline flight to see its delay risk and carbon footprint.
        </p>
        <FlightSearchForm />
      </GlassPanel>

      <FeatureList variant="compact" />

      {USE_SAMPLE_DATA && <DemoFlightList />}
    </>
  );
}

export default SearchPage;

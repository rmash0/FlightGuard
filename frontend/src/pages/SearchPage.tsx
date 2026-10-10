import { Link } from "react-router";

import GlassPanel from "../components/aero/GlassPanel";
import { aeroButtonClass } from "../components/aero/classes";

// Placeholder until the search form lands (Role A, PR 3).
function SearchPage() {
  return (
    <GlassPanel as="section">
      <h1>Will your flight be late?</h1>
      <p className="text-muted">Flight search is coming soon.</p>
      <Link
        to="/flight/DL1234/2026-10-11"
        className={aeroButtonClass("primary", "lg")}
      >
        Try a sample flight (DL1234)
      </Link>
    </GlassPanel>
  );
}

export default SearchPage;

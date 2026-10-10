import { Link } from "react-router";

// Placeholder until the search form lands (Role A, PR 3).
function SearchPage() {
  return (
    <section>
      <h1>Will your flight be late?</h1>
      <p>Flight search is coming soon.</p>
      <p>
        <Link to="/flight/DL1234/2026-10-11">Try a sample flight (DL1234)</Link>
      </p>
    </section>
  );
}

export default SearchPage;

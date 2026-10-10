import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";

import { lookupFlight } from "../api/client";
import EmissionsCard from "../components/eco/EmissionsCard";
import type { FlightLookupResponse } from "../types/api";

// `key` records which flight a result belongs to, so a stale result reads as loading.
type LookupResult =
  | { key: string; status: "error" }
  | { key: string; status: "ready"; data: FlightLookupResponse };

// Bare-bones results view to prove routing + API client end to end.
// The styled version (FlightSummary, DelayGauge, ReasonList) comes in Role A, PR 4.
function ResultsPage() {
  const { number = "", date = "" } = useParams();
  const key = `${number}/${date}`;
  const [result, setResult] = useState<LookupResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    lookupFlight(number, date, controller.signal)
      .then((data) => setResult({ key, status: "ready", data }))
      .catch(() => {
        if (!controller.signal.aborted) {
          setResult({ key, status: "error" });
        }
      });

    return () => controller.abort();
  }, [key, number, date]);

  if (!result || result.key !== key) {
    return <p>Looking up {number}...</p>;
  }

  if (result.status === "error") {
    return (
      <section>
        <h1>We couldn't load {number}</h1>
        <p>
          Check the flight number and date, or <Link to="/">search again</Link>.
        </p>
      </section>
    );
  }

  const { flight, prediction, emissions } = result.data;

  return (
    <section>
      <h1>{flight.number}</h1>
      <p>
        {flight.origin.iata} → {flight.destination.iata} · {flight.date} ·{" "}
        {flight.status}
      </p>
      <p>
        Delay risk:{" "}
        {prediction
          ? `${prediction.risk} (about ${prediction.estimated_delay_minutes} min)`
          : "unavailable"}
      </p>
      <EmissionsCard emissions={emissions} />
    </section>
  );
}

export default ResultsPage;

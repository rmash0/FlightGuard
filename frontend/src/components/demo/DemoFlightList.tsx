import { useEffect, useState } from "react";
import { Link } from "react-router";

import { getDemoFlights } from "../../api/client";
import type { DemoFlightSummary } from "../../api/demoData";
import { toDateInputValue } from "../../utils/flightSearch";
import GlassPanel from "../aero/GlassPanel";
import "./DemoFlightList.css";

const HUB = "RDU";

type DemoFlightListProps = {
  intro?: string;
};

function FlightGroup({ title, flights, date }: { title: string; flights: DemoFlightSummary[]; date: string }) {
  if (flights.length === 0) {
    return null;
  }

  return (
    <div className="demo-flights__group">
      <h3>{title}</h3>
      <ul>
        {flights.map((flight) => (
          <li key={flight.number}>
            <Link to={`/flight/${flight.number}/${date}`} className="demo-flights__pill" title={flight.airline}>
              <strong>{flight.number}</strong>
              <span>
                {flight.origin} → {flight.destination}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

// Demo mode only: the recorded sample flights a visitor can open. Renders nothing otherwise.
function DemoFlightList({ intro }: DemoFlightListProps) {
  const [flights, setFlights] = useState<DemoFlightSummary[]>([]);
  const [today] = useState(() => toDateInputValue(new Date()));

  useEffect(() => {
    let active = true;
    getDemoFlights().then((list) => {
      if (active) {
        setFlights(list);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  if (flights.length === 0) {
    return null;
  }

  const hubFlights = flights.filter((f) => f.origin === HUB || f.destination === HUB);
  const otherFlights = flights.filter((f) => f.origin !== HUB && f.destination !== HUB);

  return (
    <GlassPanel as="section" className="demo-flights" aria-labelledby="demo-flights-title">
      <h2 id="demo-flights-title">Try a sample flight</h2>
      <p className="text-muted">
        {intro ??
          "This demo runs on real flights recorded from live data, so it works without any API keys. Pick one:"}
      </p>
      <FlightGroup title="To and from Raleigh-Durham (RDU)" flights={hubFlights} date={today} />
      <FlightGroup title="In the air across the US (find them on the map)" flights={otherFlights} date={today} />
    </GlassPanel>
  );
}

export default DemoFlightList;

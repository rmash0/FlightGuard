import type { Airport, Flight, FlightStatus } from "../../types/api";
import { formatDuration, formatFlightDate, formatLocalTime, minutesBetween } from "../../utils/format";
import AeroBadge, { type AeroBadgeTone } from "../aero/AeroBadge";
import GlassPanel from "../aero/GlassPanel";
import "./FlightSummary.css";

const STATUS: Record<FlightStatus, { label: string; tone: AeroBadgeTone }> = {
  scheduled: { label: "Scheduled", tone: "sky" },
  delayed: { label: "Delayed", tone: "amber" },
  departed: { label: "Departed", tone: "sky" },
  en_route: { label: "In the air", tone: "sky" },
  landed: { label: "Landed", tone: "leaf" },
  cancelled: { label: "Cancelled", tone: "coral" },
  unknown: { label: "Status unknown", tone: "muted" },
};

type RouteEndProps = {
  airport: Airport;
  label: string;
  scheduled: string;
  // Newer time from the airline (estimated or actual), if it differs from the schedule.
  updated?: { label: string; time: string } | null;
};

function RouteEnd({ airport, label, scheduled, updated }: RouteEndProps) {
  return (
    <div className="flight-route__end">
      <span className="flight-route__label">{label}</span>
      <span className="flight-route__code">{airport.iata}</span>
      <span className="flight-route__name">{airport.name}</span>
      <span className="flight-route__time">
        {updated ? <s>{formatLocalTime(scheduled)}</s> : formatLocalTime(scheduled)}
      </span>
      {updated && (
        <span className="flight-route__updated">
          {updated.label} {formatLocalTime(updated.time)}
        </span>
      )}
    </div>
  );
}

function FlightSummary({ flight }: { flight: Flight }) {
  const status = STATUS[flight.status];
  const duration = minutesBetween(flight.scheduled_departure, flight.scheduled_arrival);

  const newDeparture = flight.actual_departure ?? flight.estimated_departure;
  const departureUpdate =
    newDeparture && formatLocalTime(newDeparture) !== formatLocalTime(flight.scheduled_departure)
      ? { label: flight.actual_departure ? "Left" : "Now", time: newDeparture }
      : null;

  const details = [flight.airline.name, formatFlightDate(flight.date), flight.aircraft_type]
    .filter(Boolean)
    .join(" · ");

  return (
    <GlassPanel as="section" className="flight-summary" aria-labelledby="flight-summary-title">
      <div className="flight-summary__header">
        <h1 id="flight-summary-title">{flight.number}</h1>
        <AeroBadge tone={status.tone}>{status.label}</AeroBadge>
      </div>
      <p className="text-muted">{details}</p>

      <div className="flight-route">
        <RouteEnd
          airport={flight.origin}
          label="Departs"
          scheduled={flight.scheduled_departure}
          updated={departureUpdate}
        />

        <div className="flight-route__path" aria-hidden="true">
          <span className="flight-route__duration">{formatDuration(duration)}</span>
          <span className="flight-route__line">
            <svg className="flight-route__plane" viewBox="0 0 64 64" width="28" height="28">
              <path
                transform="rotate(90 32 32)"
                d="M32 12c2 0 3 2 3 5v11l15 8v4l-15-4v9l5 4v3l-8-2-8 2v-3l5-4v-9l-15 4v-4l15-8V17c0-3 1-5 3-5z"
              />
            </svg>
          </span>
        </div>

        <RouteEnd airport={flight.destination} label="Arrives" scheduled={flight.scheduled_arrival} />
      </div>
    </GlassPanel>
  );
}

export default FlightSummary;

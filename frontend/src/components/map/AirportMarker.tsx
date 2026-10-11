import { useCallback, useEffect, useRef, useState } from "react";
import { CircleMarker, Popup, Tooltip } from "react-leaflet";

import { getAirportStatus } from "../../api/client";
import type { AirportStatus, FaaEventType, RiskLevel } from "../../types/api";
import AeroBadge, { type AeroBadgeTone } from "../aero/AeroBadge";

export type MapAirport = {
  iata: string;
  name: string;
  lat: number;
  lon: number;
  type?: string;
};

type AirportMarkerProps = {
  airport: MapAirport;
};

const RISK: Record<RiskLevel, { label: string; tone: AeroBadgeTone }> = {
  low: { label: "Low delay risk", tone: "aqua" },
  medium: { label: "Medium delay risk", tone: "amber" },
  high: { label: "High delay risk", tone: "coral" },
};

const FAA_EVENT_LABELS: Record<FaaEventType, string> = {
  ground_stop: "Ground stop",
  ground_delay: "Ground delay program",
  general_delay: "Departure delays",
  closure: "Closure",
};

function formatWeather(weather: NonNullable<AirportStatus["weather"]>) {
  const parts = [weather.description];

  if (weather.wind_gusts_kt !== null) {
    parts.push(`gusts ${Math.round(weather.wind_gusts_kt)} kt`);
  }

  if (weather.visibility_m !== null && weather.visibility_m < 8000) {
    parts.push(`visibility ${(weather.visibility_m / 1609).toFixed(1)} mi`);
  }

  return parts.join(", ");
}

function AirportMarker({ airport }: AirportMarkerProps) {
  const isLarge = airport.type === "large_airport";
  const radius = isLarge ? 7 : 5;

  const [status, setStatus] = useState<AirportStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);
  const requestController = useRef<AbortController | null>(null);

  useEffect(() => () => requestController.current?.abort(), []);

  // Fetch on every open: FAA programs change within minutes and the backend caches both feeds.
  const handlePopupOpen = useCallback(() => {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true);
    setFailed(false);

    getAirportStatus(airport.iata, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setStatus(result);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
  }, [airport.iata]);

  const risk = status ? RISK[status.risk] : null;

  return (
    <CircleMarker
      center={[airport.lat, airport.lon]}
      radius={radius}
      pathOptions={{
        color: "#ffffff",
        weight: 2,
        fillColor: isLarge ? "#28a5ed" : "#49c9a1",
        fillOpacity: 0.95,
      }}
      eventHandlers={{ popupopen: handlePopupOpen }}
    >
      <Tooltip direction="top" offset={[0, -8]}>
        {airport.iata}
      </Tooltip>

      <Popup>
        <div style={{ minWidth: 200, maxWidth: 260 }}>
          <h3 style={{ margin: "0 0 6px", fontSize: 17, color: "var(--aero-heading)" }}>
            {airport.iata}
          </h3>

          <p style={{ margin: "0 0 10px", fontWeight: 600 }}>{airport.name}</p>

          {loading && !status && <p style={{ margin: 0 }}>Checking conditions...</p>}

          {failed && !status && (
            <p style={{ margin: 0 }}>Live conditions are unavailable right now.</p>
          )}

          {status && risk && (
            <div style={{ display: "grid", gap: 8 }}>
              <div>
                <AeroBadge tone={risk.tone}>{risk.label}</AeroBadge>
              </div>

              <div>
                <strong>Weather:</strong>{" "}
                {status.weather ? formatWeather(status.weather) : "Unavailable"}
              </div>

              <div>
                <strong>FAA status:</strong>{" "}
                {status.faa_events.length === 0
                  ? "No delays reported"
                  : status.faa_events
                      .map((event) =>
                        event.avg_minutes !== null
                          ? `${FAA_EVENT_LABELS[event.type]} (avg ${event.avg_minutes} min)`
                          : FAA_EVENT_LABELS[event.type],
                      )
                      .join("; ")}
              </div>

              {status.reasons.length > 0 && (
                <ul style={{ margin: 0, paddingLeft: 18, textAlign: "left", fontSize: 12 }}>
                  {status.reasons.slice(0, 3).map((reason) => (
                    <li key={`${reason.factor}-${reason.detail}`}>{reason.detail}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}

export default AirportMarker;

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Marker, Popup } from "react-leaflet";
import L from "leaflet";

import { getLiveFlightDetails } from "../../api/client";
import type { LiveFlightDetails } from "../../types/api";

export type LiveAircraft = {
  icao24: string;
  callsign: string;
  latitude: number;
  longitude: number;
  altitude: number | null;
  velocity: number | null;
  heading: number | null;
  origin_country: string;
};

type PlaneMarkerProps = {
  aircraft: LiveAircraft;
};

function PlaneMarker({ aircraft }: PlaneMarkerProps) {
  const [details, setDetails] = useState<LiveFlightDetails | null>(null);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const requested = useRef(false);
  const requestController = useRef<AbortController | null>(null);

  useEffect(() => () => requestController.current?.abort(), []);

  const handlePopupOpen = useCallback(() => {
    if (requested.current) return;
    requested.current = true;
    const controller = new AbortController();
    requestController.current = controller;
    setDetailsLoading(true);

    void getLiveFlightDetails(aircraft.icao24, aircraft.callsign, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) setDetails(result);
      })
      .catch(() => {
        // OpenSky still supplies altitude and speed if route enrichment fails.
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailsLoading(false);
      });
  }, [aircraft.icao24, aircraft.callsign]);

  const detailValue = (value: string | null | undefined) =>
    detailsLoading ? "Looking up..." : value || "Unavailable";

  const icon = useMemo(() => {
    const heading = aircraft.heading ?? 0;

    return L.divIcon({
      className: "flightguard-plane-marker",
      html: `
        <div
          style="
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            transform: rotate(${heading}deg);
            transition: transform 0.3s ease;
          "
        >
          <div
            style="
              width: 32px;
              height: 32px;
              display: flex;
              align-items: center;
              justify-content: center;
              border-radius: 50%;
              background: var(--aero-glass-strong);
              border: 1px solid var(--aero-glass-border);
              box-shadow: var(--aero-shadow);
              backdrop-filter: blur(8px);
              color: var(--aero-accent);
            "
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="currentColor"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path d="M12 2L14 9L21 13V16L13 14V20L16 22V23L12 22L8 23V22L11 20V14L3 16V13L10 9L12 2Z"/>
            </svg>
          </div>
        </div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
      popupAnchor: [0, -18],
    });
  }, [aircraft.heading]);

  const formatAltitude = (altitude: number | null) => {
    if (altitude === null) {
      return "Unknown";
    }

    const feet = altitude * 3.28084;

    return `${Math.round(feet).toLocaleString()} ft`;
  };

  const formatSpeed = (velocity: number | null) => {
    if (velocity === null) {
      return "Unknown";
    }

    const knots = velocity * 1.94384;

    return `${Math.round(knots)} knots`;
  };

  return (
    <Marker
      position={[aircraft.latitude, aircraft.longitude]}
      icon={icon}
      eventHandlers={{ popupopen: handlePopupOpen }}
    >
      <Popup>
        <div
          style={{
            minWidth: 180,
            fontFamily: "var(--aero-font)",
          }}
        >
          <h3
            style={{
              fontSize: 17,
              fontWeight: 700,
              margin: "0 0 10px",
              color: "var(--aero-heading)",
            }}
          >
            {details?.flight_number || aircraft.callsign || "Live aircraft"}
          </h3>

          <div style={{ display: "grid", gap: 7 }}>
            <div>
              <strong>Flight number:</strong> {detailValue(details?.flight_number)}
            </div>
            <div>
              <strong>Origin:</strong> {detailValue(details?.origin)}
            </div>
            <div>
              <strong>Destination:</strong> {detailValue(details?.destination)}
            </div>
            <div>
              <strong>Altitude:</strong> {formatAltitude(aircraft.altitude)}
            </div>

            <div>
              <strong>Speed:</strong> {formatSpeed(aircraft.velocity)}
            </div>

            <div>
              <strong>Heading:</strong>{" "}
              {aircraft.heading !== null
                ? `${Math.round(aircraft.heading)}°`
                : "Unknown"}
            </div>
          </div>
        </div>
      </Popup>
    </Marker>
  );
}

export default PlaneMarker;

import { useCallback, useEffect, useState } from "react";
import { Plane, Radio, MapPin, RefreshCw } from "lucide-react";

import GlassPanel from "../components/aero/GlassPanel";
import FlightMap from "../components/map/FlightMap";

import type { MapBounds } from "../components/map/FlightMap";
import type { LiveAircraft } from "../components/map/PlaneMarker";
import type { MapAirport } from "../components/map/AirportMarker";

import { getLiveAircraft, getMapAirports } from "../api/client";

const REFRESH_INTERVAL = 15000;

function MapPage() {
  const [aircraft, setAircraft] = useState<LiveAircraft[]>([]);
  const [airports, setAirports] = useState<MapAirport[]>([]);
  const [bounds, setBounds] = useState<MapBounds | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [airportError, setAirportError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const handleBoundsChange = useCallback((next: MapBounds | null) => {
    setBounds((previous) => {
      if (previous === null && next === null) {
        return previous;
      }

      if (previous === null || next === null) {
        return next;
      }

      const sameBounds =
        Math.abs(previous.lamin - next.lamin) < 0.0001 &&
        Math.abs(previous.lamax - next.lamax) < 0.0001 &&
        Math.abs(previous.lomin - next.lomin) < 0.0001 &&
        Math.abs(previous.lomax - next.lomax) < 0.0001;

      return sameBounds ? previous : next;
    });
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadAirports() {
      try {
        const data = await getMapAirports(controller.signal);

        if (!controller.signal.aborted) {
          setAirports(data);
          setAirportError(null);
        }
      } catch {
        if (!controller.signal.aborted) {
          setAirportError("Airport data is currently unavailable.");
        }
      }
    }

    void loadAirports();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!bounds) {
      return;
    }

    const controller = new AbortController();
    let active = true;
    let requestInProgress = false;

    async function loadAircraft() {
      if (!bounds || requestInProgress || !active) {
        return;
      }

      requestInProgress = true;
      setLoading(true);

      try {
        const data = await getLiveAircraft(bounds, controller.signal);

        if (active && !controller.signal.aborted) {
          setAircraft(data.flights);
          setLastUpdated(data.updated_at);
          setError(null);
        }
      } catch (err) {
        if (active && !controller.signal.aborted) {
          console.error("Aircraft request failed:", err);
          setError(
            "Unable to load live aircraft. OpenSky may be unavailable or rate-limited.",
          );
        }
      } finally {
        requestInProgress = false;

        if (active && !controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    void loadAircraft();

    const interval = window.setInterval(
      () => void loadAircraft(),
      REFRESH_INTERVAL,
    );

    return () => {
      active = false;
      controller.abort();
      window.clearInterval(interval);
    };
  }, [bounds]);

  const displayError = !bounds
    ? "Zoom in to a smaller area to see live aircraft."
    : error;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 24,
      }}
    >
      <GlassPanel as="section">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div>
            <h1
              style={{
                margin: "0 0 8px",
                color: "var(--aero-heading)",
                fontSize: "clamp(26px, 4vw, 36px)",
              }}
            >
              Live Flight Map
            </h1>

            <p
              style={{
                margin: 0,
                color: "var(--aero-text-muted)",
                lineHeight: 1.6,
              }}
            >
              Explore aircraft positions and airports across the United States.
            </p>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: "var(--aero-text-muted)",
              fontSize: 13,
            }}
          >
            <Radio size={18} color="var(--aero-leaf)" />

            {loading ? "Updating..." : "Live tracking"}
          </div>
        </div>
      </GlassPanel>

      <FlightMap
        aircraft={bounds ? aircraft : []}
        airports={airports}
        loading={loading}
        error={displayError}
        onBoundsChange={handleBoundsChange}
      />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
        }}
      >
        <GlassPanel>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <Plane size={20} color="var(--aero-accent)" />
            <span style={{ color: "var(--aero-text-muted)" }}>
              Aircraft in view
            </span>
          </div>

          <h2
            style={{
              margin: "12px 0 0",
              color: "var(--aero-heading)",
              fontSize: 28,
            }}
          >
            {bounds ? aircraft.length : "—"}
          </h2>
        </GlassPanel>

        <GlassPanel>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <MapPin size={20} color="var(--aero-leaf)" />
            <span style={{ color: "var(--aero-text-muted)" }}>
              Airports loaded
            </span>
          </div>

          <h2
            style={{
              margin: "12px 0 0",
              color: "var(--aero-heading)",
              fontSize: 28,
            }}
          >
            {airports.length}
          </h2>
        </GlassPanel>

        <GlassPanel>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <RefreshCw size={20} color="var(--aero-accent)" />
            <span style={{ color: "var(--aero-text-muted)" }}>
              Refresh interval
            </span>
          </div>

          <h2
            style={{
              margin: "12px 0 0",
              color: "var(--aero-heading)",
              fontSize: 28,
            }}
          >
            15s
          </h2>
        </GlassPanel>
      </div>

      {airportError && (
        <p role="status" style={{ color: "var(--aero-text-muted)" }}>
          {airportError}
        </p>
      )}

      <p
        style={{
          color: "var(--aero-text-muted)",
          fontSize: 12,
          lineHeight: 1.6,
          textAlign: "center",
        }}
      >
        Aircraft information provided by OpenSky Network. Positions may be
        delayed or incomplete.
        {lastUpdated !== null && bounds
          ? ` Last data update: ${new Date(lastUpdated * 1000).toLocaleTimeString()}.`
          : ""}
      </p>
    </div>
  );
}

export default MapPage;

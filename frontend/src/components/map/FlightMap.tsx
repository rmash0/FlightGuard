import { useEffect, useCallback } from "react";
import { MapContainer, TileLayer, useMapEvents } from "react-leaflet";
import type { LatLngBounds } from "leaflet";
import { Plane, MapPin } from "lucide-react";

import PlaneMarker from "./PlaneMarker";
import type { LiveAircraft } from "./PlaneMarker";

import AirportMarker from "./AirportMarker";
import type { MapAirport } from "./AirportMarker";

import "leaflet/dist/leaflet.css";
import "./FlightMap.css";

export type MapBounds = {
  lamin: number;
  lamax: number;
  lomin: number;
  lomax: number;
};

type FlightMapProps = {
  aircraft: LiveAircraft[];
  airports?: MapAirport[];
  loading?: boolean;
  error?: string | null;
  onBoundsChange?: (bounds: MapBounds | null) => void;
};

const US_CENTER: [number, number] = [39.5, -98.35];
const DEFAULT_ZOOM = 5;
const MAX_REQUEST_AREA = 100;

function convertBounds(bounds: LatLngBounds): MapBounds {
  return {
    lamin: bounds.getSouth(),
    lamax: bounds.getNorth(),
    lomin: bounds.getWest(),
    lomax: bounds.getEast(),
  };
}

function isValidArea(bounds: MapBounds) {
  const area = (bounds.lamax - bounds.lamin) * (bounds.lomax - bounds.lomin);

  return area > 0 && area <= MAX_REQUEST_AREA;
}

function MapViewport({
  onBoundsChange,
}: {
  onBoundsChange?: (bounds: MapBounds | null) => void;
}) {
  const map = useMapEvents({
    moveend: () => {
      updateBounds();
    },
    zoomend: () => {
      updateBounds();
    },
  });

  const updateBounds = useCallback(() => {
    const bounds = convertBounds(map.getBounds());

    if (isValidArea(bounds)) {
      onBoundsChange?.(bounds);
    } else {
      onBoundsChange?.(null);
    }
  }, [map, onBoundsChange]);

  useEffect(() => {
    updateBounds();
  }, [updateBounds]);

  return null;
}

function FlightMap({
  aircraft,
  airports = [],
  loading = false,
  error = null,
  onBoundsChange,
}: FlightMapProps) {
  return (
    <div
      className="flight-map"
      style={{
        position: "relative",
        width: "100%",
        borderRadius: "var(--aero-radius-lg)",
        overflow: "hidden",
        border: "1px solid var(--aero-glass-border)",
        boxShadow: "var(--aero-shadow)",
        background: "var(--aero-glass-bg)",
      }}
    >
      <MapContainer
        center={US_CENTER}
        zoom={DEFAULT_ZOOM}
        minZoom={4}
        maxZoom={15}
        scrollWheelZoom={true}
        style={{
          width: "100%",
          height: "100%",
        }}
      >
        {/* Keyless OSM tiles; night mode darkens them with a CSS filter in FlightMap.css. */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        <MapViewport onBoundsChange={onBoundsChange} />

        {airports.map((airport) => (
          <AirportMarker key={airport.iata} airport={airport} />
        ))}

        {aircraft.map((plane) => (
          <PlaneMarker key={`${plane.icao24}-${plane.callsign}`} aircraft={plane} />
        ))}
      </MapContainer>

      <div
        className="flight-map__count"
        style={{
          position: "absolute",
          zIndex: 1000,
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderRadius: "var(--aero-radius-pill)",
          background: "var(--aero-glass-strong)",
          border: "1px solid var(--aero-glass-border)",
          color: "var(--aero-text)",
          boxShadow: "var(--aero-shadow)",
          backdropFilter: "blur(var(--aero-blur))",
          fontSize: 13,
          fontWeight: 600,
          pointerEvents: "none",
        }}
      >
        <Plane size={16} color="var(--aero-accent)" />

        {loading ? "Updating aircraft..." : `${aircraft.length} aircraft`}
      </div>

      {error && (
        <div
          className="flight-map__error"
          role="alert"
          style={{
            position: "absolute",
            zIndex: 1000,
            borderRadius: "var(--aero-radius-md)",
            background: "var(--aero-glass-strong)",
            border: "1px solid var(--aero-glass-border)",
            color: "var(--aero-text)",
            backdropFilter: "blur(var(--aero-blur))",
            boxShadow: "var(--aero-shadow)",
            maxWidth: "90%",
            textAlign: "center",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      <div
        className="flight-map__credit"
        style={{
          position: "absolute",
          zIndex: 1000,
          alignItems: "center",
          gap: 6,
          borderRadius: "var(--aero-radius-pill)",
          background: "var(--aero-glass-strong)",
          border: "1px solid var(--aero-glass-border)",
          color: "var(--aero-text-muted)",
          fontSize: 11,
          pointerEvents: "none",
        }}
      >
        <MapPin size={13} />
        OpenStreetMap · OpenSky Network
      </div>
    </div>
  );
}

export default FlightMap;

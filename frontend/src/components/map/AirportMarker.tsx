import { CircleMarker, Popup, Tooltip } from "react-leaflet";

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

function AirportMarker({ airport }: AirportMarkerProps) {
  const isLarge = airport.type === "large_airport";

  const radius = isLarge ? 7 : 5;

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
    >
      <Tooltip direction="top" offset={[0, -8]}>
        {airport.iata}
      </Tooltip>

      <Popup>
        <div style={{ minWidth: 180 }}>
          <h3 style={{ margin: "0 0 6px", fontSize: 17 }}>{airport.iata}</h3>

          <p style={{ margin: "0 0 8px", fontWeight: 600 }}>{airport.name}</p>

          <p style={{ margin: 0, fontSize: 12 }}>
            {isLarge ? "Large Airport" : "Medium Airport"}
          </p>

          <p style={{ margin: "8px 0 0", fontSize: 11 }}>
            {airport.lat.toFixed(4)}, {airport.lon.toFixed(4)}
          </p>
        </div>
      </Popup>
    </CircleMarker>
  );
}

export default AirportMarker;

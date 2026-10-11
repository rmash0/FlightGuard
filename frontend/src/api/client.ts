// Single entry point for backend calls. Components never call fetch directly.
// In demo mode (USE_SAMPLE_DATA, see config.ts) every call is answered from recorded sample
// data in ./demoData instead of the backend. That module is imported lazily, so normal
// builds never download it.

import type { MapAirport } from "../components/map/AirportMarker";
import type { LiveAircraft } from "../components/map/PlaneMarker";
import { USE_SAMPLE_DATA } from "../config";
import type { AirportStatus, FlightLookupResponse, LiveFlightDetails } from "../types/api";
import { ApiError } from "./errors";

export { ApiError, NOT_IN_DEMO } from "./errors";

const DEMO_LATENCY_MS = 400;

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const detail =
      body !== null &&
      typeof body === "object" &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : null;
    throw new ApiError(`Request to ${path} failed`, response.status, detail);
  }

  return (await response.json()) as T;
}

// Loads the demo data module after a short fake delay, so loading states still show.
async function demo(signal?: AbortSignal) {
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, DEMO_LATENCY_MS);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason);
    });
  });
  return import("./demoData");
}

export async function lookupFlight(
  number: string,
  date: string,
  signal?: AbortSignal,
): Promise<FlightLookupResponse> {
  if (USE_SAMPLE_DATA) {
    return (await demo(signal)).lookupFlight(number, date);
  }

  const params = new URLSearchParams({ number, date });
  return getJson<FlightLookupResponse>(`/api/flights/lookup?${params}`, signal);
}

export type MapBounds = {
  lamin: number;
  lamax: number;
  lomin: number;
  lomax: number;
};

export type LiveAircraftResponse = {
  updated_at: number | null;
  flights: LiveAircraft[];
};

export async function getLiveAircraft(
  bounds: MapBounds,
  signal?: AbortSignal,
): Promise<LiveAircraftResponse> {
  if (USE_SAMPLE_DATA) {
    return (await demo(signal)).getLiveAircraft(bounds);
  }

  const params = new URLSearchParams({
    lamin: String(bounds.lamin),
    lamax: String(bounds.lamax),
    lomin: String(bounds.lomin),
    lomax: String(bounds.lomax),
  });

  return getJson<LiveAircraftResponse>(`/api/flights/live?${params}`, signal);
}

export async function getLiveFlightDetails(
  icao24: string,
  callsign: string,
  signal?: AbortSignal,
): Promise<LiveFlightDetails> {
  if (USE_SAMPLE_DATA) {
    return (await demo(signal)).getLiveFlightDetails(icao24);
  }

  const params = new URLSearchParams({ callsign });
  return getJson<LiveFlightDetails>(
    `/api/flights/live/${encodeURIComponent(icao24)}/details?${params}`,
    signal,
  );
}

export async function getMapAirports(
  signal?: AbortSignal,
): Promise<MapAirport[]> {
  if (USE_SAMPLE_DATA) {
    return (await demo(signal)).getMapAirports();
  }

  const data = await getJson<MapAirport[] | { airports: MapAirport[] }>(
    "/api/airports",
    signal,
  );

  return Array.isArray(data) ? data : data.airports;
}

export async function getAirportStatus(
  iata: string,
  signal?: AbortSignal,
): Promise<AirportStatus> {
  if (USE_SAMPLE_DATA) {
    return (await demo(signal)).getAirportStatus(iata);
  }

  return getJson<AirportStatus>(`/api/airports/${encodeURIComponent(iata)}`, signal);
}

// Recorded sample flights for the demo's "try a flight" lists. Empty outside demo mode.
export async function getDemoFlights() {
  if (!USE_SAMPLE_DATA) {
    return [];
  }
  return (await import("./demoData")).getDemoFlightSummaries();
}

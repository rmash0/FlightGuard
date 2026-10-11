// Single entry point for backend calls. Components never call fetch directly.
// Set VITE_USE_MOCKS=true in frontend/.env.local to serve src/mocks/*.json instead of the backend.

import lookupMock from "../mocks/lookup.json";
import liveDetailsMock from "../mocks/live-details.json";
import type { FlightLookupResponse, LiveFlightDetails } from "../types/api";
import type { LiveAircraft } from "../components/map/PlaneMarker";
import type { MapAirport } from "../components/map/AirportMarker";

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
const MOCK_LATENCY_MS = 400;

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

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

// Fake network delay so loading states get exercised while using mocks.
function mockDelay(signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, MOCK_LATENCY_MS);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason);
    });
  });
}

// Mock-only test flights for previewing every results-page state:
// ZZ404 / ZZ502 / ZZ503 -> that API error, ZZ1 -> no prediction or emissions,
// ZZ2 -> a delayed flight with high risk. Any other number returns the sample flight.
const MOCK_ERROR_FLIGHTS: Record<string, number> = {
  ZZ404: 404,
  ZZ502: 502,
  ZZ503: 503,
};

function mockLookup(number: string, date: string): FlightLookupResponse {
  if (number in MOCK_ERROR_FLIGHTS) {
    throw new ApiError(`Mock error for ${number}`, MOCK_ERROR_FLIGHTS[number]);
  }

  const mock = lookupMock as FlightLookupResponse;
  const response = { ...mock, flight: { ...mock.flight, number, date } };

  if (number === "ZZ1") {
    return { ...response, prediction: null, emissions: null };
  }

  if (number === "ZZ2") {
    return {
      ...response,
      flight: {
        ...response.flight,
        status: "delayed",
        estimated_departure: `${date}T14:50:00-04:00`,
      },
      prediction: mock.prediction && {
        ...mock.prediction,
        risk: "high",
        probability_delayed: 0.82,
        estimated_delay_minutes: 48,
        reported_delay_minutes: 45,
      },
    };
  }

  return response;
}

export async function lookupFlight(
  number: string,
  date: string,
  signal?: AbortSignal,
): Promise<FlightLookupResponse> {
  if (USE_MOCKS) {
    await mockDelay(signal);
    return mockLookup(number, date);
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
  if (USE_MOCKS) {
    await mockDelay(signal);
    return {
      updated_at: null,
      flights: [],
    };
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
  if (USE_MOCKS) {
    await mockDelay(signal);
    return liveDetailsMock as LiveFlightDetails;
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
  if (USE_MOCKS) {
    await mockDelay(signal);
    return [];
  }

  const data = await getJson<MapAirport[] | { airports: MapAirport[] }>(
    "/api/airports",
    signal,
  );

  return Array.isArray(data) ? data : data.airports;
}

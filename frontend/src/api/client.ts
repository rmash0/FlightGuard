// Single entry point for backend calls. Components never call fetch directly.
// Set VITE_USE_MOCKS=true in frontend/.env.local to serve src/mocks/*.json instead of the backend.

import lookupMock from "../mocks/lookup.json";
import type { FlightLookupResponse } from "../types/api";

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
const MOCK_LATENCY_MS = 400;

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal });

  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed`, response.status);
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

export async function lookupFlight(
  number: string,
  date: string,
  signal?: AbortSignal,
): Promise<FlightLookupResponse> {
  if (USE_MOCKS) {
    await mockDelay(signal);
    const mock = lookupMock as FlightLookupResponse;
    return { ...mock, flight: { ...mock.flight, number, date } };
  }

  const params = new URLSearchParams({ number, date });
  return getJson<FlightLookupResponse>(`/api/flights/lookup?${params}`, signal);
}

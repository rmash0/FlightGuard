// Demo-mode data source: real API responses recorded by backend/scripts/record_demo_data.py.
// Loaded only in demo mode (client.ts imports this module dynamically), so the normal app
// never downloads it.

import aircraftData from "../mocks/demo/aircraft.json";
import airportStatusData from "../mocks/demo/airport-status.json";
import airportsData from "../mocks/demo/airports.json";
import flightsData from "../mocks/demo/flights.json";
import liveDetailsData from "../mocks/demo/live-details.json";
import lookupMock from "../mocks/lookup.json";
import type { MapAirport } from "../components/map/AirportMarker";
import type { LiveAircraft } from "../components/map/PlaneMarker";
import type { AirportStatus, FlightLookupResponse, LiveFlightDetails } from "../types/api";
import { ApiError, NOT_IN_DEMO } from "./errors";
import type { LiveAircraftResponse, MapBounds } from "./client";

const RECORDED_ON = flightsData.recorded_on;
const FLIGHTS = new Map(
  (flightsData.flights as FlightLookupResponse[]).map((f) => [f.flight.number, f]),
);
const AIRCRAFT = aircraftData.flights as LiveAircraft[];
const LIVE_DETAILS = liveDetailsData as Record<string, LiveFlightDetails>;
const AIRPORT_STATUS = airportStatusData as Record<string, AirportStatus>;
const AIRPORTS = airportsData as MapAirport[];

export type DemoFlightSummary = {
  number: string;
  airline: string;
  origin: string;
  destination: string;
};

// Recorded flights for the "try a sample flight" lists.
export function getDemoFlightSummaries(): DemoFlightSummary[] {
  return [...FLIGHTS.values()].map(({ flight }) => ({
    number: flight.number,
    airline: flight.airline.name,
    origin: flight.origin.iata,
    destination: flight.destination.iata,
  }));
}

// --- Flight lookup -------------------------------------------------------------

// "2026-10-11T14:05:00-04:00" shifted by whole days, keeping the time and offset.
function shiftIsoDate(iso: string, days: number): string {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + days));
  return shifted.toISOString().slice(0, 10) + iso.slice(10);
}

function dayDifference(from: string, to: string): number {
  return Math.round((Date.parse(to) - Date.parse(from)) / 86_400_000);
}

// Recorded flights follow whatever date the visitor picks, so the demo never goes stale.
function onDate(response: FlightLookupResponse, date: string): FlightLookupResponse {
  const days = dayDifference(RECORDED_ON, date);
  const shift = (iso: string | null) => (iso ? shiftIsoDate(iso, days) : iso);
  const { flight } = response;

  return {
    ...response,
    flight: {
      ...flight,
      date,
      scheduled_departure: shiftIsoDate(flight.scheduled_departure, days),
      scheduled_arrival: shiftIsoDate(flight.scheduled_arrival, days),
      estimated_departure: shift(flight.estimated_departure),
      actual_departure: shift(flight.actual_departure),
    },
  };
}

// Dev-only test flights for previewing every results-page state:
// ZZ404 / ZZ502 / ZZ503 -> that error, ZZ1 -> no prediction or emissions, ZZ2 -> delayed, high risk.
const TEST_ERROR_FLIGHTS: Record<string, number> = { ZZ404: 404, ZZ502: 502, ZZ503: 503 };

function testFlight(number: string, date: string): FlightLookupResponse | null {
  if (number in TEST_ERROR_FLIGHTS) {
    throw new ApiError(`Test error for ${number}`, TEST_ERROR_FLIGHTS[number]);
  }

  const sample = lookupMock as FlightLookupResponse;
  const response = { ...sample, flight: { ...sample.flight, number, date } };

  if (number === "ZZ1") {
    return { ...response, prediction: null, emissions: null };
  }

  if (number === "ZZ2") {
    return {
      ...response,
      flight: { ...response.flight, status: "delayed", estimated_departure: `${date}T14:50:00-04:00` },
      prediction: sample.prediction && {
        ...sample.prediction,
        risk: "high",
        probability_delayed: 0.82,
        estimated_delay_minutes: 48,
        reported_delay_minutes: 45,
      },
    };
  }

  return null;
}

export function lookupFlight(number: string, date: string): FlightLookupResponse {
  const recorded = FLIGHTS.get(number);
  if (recorded) {
    return onDate(recorded, date);
  }

  const test = testFlight(number, date);
  if (test) {
    return test;
  }

  throw new ApiError(`${number} is not in the demo data`, 404, NOT_IN_DEMO);
}

// --- Live map ------------------------------------------------------------------

const LOADED_AT = Date.now();
// Planes glide along their recorded heading, then reset, so the map looks live forever.
const LOOP_SECONDS = 15 * 60;
const METERS_PER_DEGREE = 111_320;

function advance(plane: LiveAircraft, seconds: number): LiveAircraft {
  if (plane.velocity === null || plane.heading === null) {
    return plane;
  }
  const distance = plane.velocity * seconds;
  const radians = (plane.heading * Math.PI) / 180;
  const latitude = plane.latitude + (distance * Math.cos(radians)) / METERS_PER_DEGREE;
  const longitude =
    plane.longitude +
    (distance * Math.sin(radians)) / (METERS_PER_DEGREE * Math.cos((plane.latitude * Math.PI) / 180));
  return { ...plane, latitude, longitude };
}

export function getLiveAircraft(bounds: MapBounds): LiveAircraftResponse {
  const elapsed = ((Date.now() - LOADED_AT) / 1000) % LOOP_SECONDS;
  const flights = AIRCRAFT.map((plane) => advance(plane, elapsed)).filter(
    (plane) =>
      plane.latitude >= bounds.lamin &&
      plane.latitude <= bounds.lamax &&
      plane.longitude >= bounds.lomin &&
      plane.longitude <= bounds.lomax,
  );
  return { updated_at: Math.floor(Date.now() / 1000), flights };
}

// Only recorded demo flights have a known flight number and route.
export function getLiveFlightDetails(icao24: string): LiveFlightDetails {
  return LIVE_DETAILS[icao24.toLowerCase()] ?? { flight_number: null, origin: null, destination: null };
}

export function getMapAirports(): MapAirport[] {
  return AIRPORTS;
}

export function getAirportStatus(iata: string): AirportStatus {
  const recorded = AIRPORT_STATUS[iata];
  if (recorded) {
    return recorded;
  }
  // Airports outside the recorded set get a calm, generic status.
  const airport = AIRPORTS.find((a) => a.iata === iata);
  return {
    iata,
    name: airport?.name ?? iata,
    weather: null,
    faa_events: [],
    risk: "low",
    reasons: [
      // Same factor the backend uses for its calm-conditions reason.
      { factor: "time_of_day", detail: "No weather or airport issues in the demo data", impact: "low" },
    ],
  };
}

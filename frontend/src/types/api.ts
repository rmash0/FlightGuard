// TypeScript mirror of the API contract in AGENTS.md §8.
// Must match backend/app/models/schemas.py field for field. Change both together.

export type FlightStatus =
  | "scheduled"
  | "delayed"
  | "departed"
  | "en_route"
  | "landed"
  | "cancelled"
  | "unknown";

export type RiskLevel = "low" | "medium" | "high";

export type ImpactLevel = "low" | "medium" | "high";

export type EstimateTier = "flight" | "route" | "distance" | "fallback";

export type CabinClass = "economy" | "premium_economy" | "business" | "first";

export type Airline = {
  iata: string;
  name: string;
};

export type Airport = {
  iata: string;
  name: string;
  lat: number;
  lon: number;
};

export type Flight = {
  number: string;
  airline: Airline;
  date: string;
  origin: Airport;
  destination: Airport;
  scheduled_departure: string;
  scheduled_arrival: string;
  estimated_departure: string | null;
  actual_departure: string | null;
  status: FlightStatus;
  aircraft_type: string | null;
  icao24: string | null;
};

export type DelayReason = {
  factor: string;
  detail: string;
  impact: ImpactLevel;
};

export type DelayPrediction = {
  risk: RiskLevel;
  probability_delayed: number;
  estimated_delay_minutes: number;
  reported_delay_minutes: number | null;
  reasons: DelayReason[];
  model: string;
};

export type EcoComparison = {
  label: string;
  value: number;
};

export type Emissions = {
  co2e_kg_per_passenger: Record<CabinClass, number>;
  estimate_tier: EstimateTier;
  source: string;
  comparisons: EcoComparison[];
};

export type FlightLookupResponse = {
  flight: Flight;
  prediction: DelayPrediction | null;
  emissions: Emissions | null;
};

export type LiveFlightDetails = {
  flight_number: string | null;
  origin: string | null;
  destination: string | null;
};

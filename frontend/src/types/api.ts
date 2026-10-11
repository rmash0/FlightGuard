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

export type DelayFactor =
  | "weather_origin"
  | "weather_destination"
  | "faa_origin"
  | "faa_destination"
  | "time_of_day"
  | "day_of_week"
  | "season"
  | "historical_route"
  | "reported_delay";

export type DelayReason = {
  factor: DelayFactor;
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

export type FaaEventType = "ground_stop" | "ground_delay" | "general_delay" | "closure";

export type FaaEvent = {
  type: FaaEventType;
  reason: string;
  avg_minutes: number | null;
  max_minutes: number | null;
  end_time: string | null;
};

export type AirportWeather = {
  time: string | null;
  weather_code: number | null;
  description: string;
  wind_gusts_kt: number | null;
  visibility_m: number | null;
  precipitation_mm: number | null;
};

export type AirportStatus = {
  iata: string;
  name: string;
  weather: AirportWeather | null;
  faa_events: FaaEvent[];
  risk: RiskLevel;
  reasons: DelayReason[];
};

// GET /api/predict/model. Accuracy for the About page, plus hourly chart data.
export type HourlyDelayRate = {
  hour: number;
  delay_rate: number;
  flights: number;
  mean_delay_minutes: number;
};

export type ModelInfo = {
  model: string;
  test_auc: number | null;
  base_rate: number | null;
  train_months: string[];
  calibration_month: string | null;
  test_month: string | null;
  months: string[];
  hourly_delay_rate: HourlyDelayRate[];
};

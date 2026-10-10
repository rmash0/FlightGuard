// Helpers for parsing flight search input.

// Searchable window around today. Weather forecasts only reach ~2 weeks out,
// so predictions past that lean on historical patterns.
export const SEARCH_PAST_DAYS = 7;
export const SEARCH_FUTURE_DAYS = 30;

// IATA airline code (2 chars, at least one letter: DL, B6, 9E) or ICAO code (3 letters: DAL),
// then a 1-4 digit flight number and an optional suffix letter.
const IATA_FLIGHT = /^([A-Z0-9]{2})(\d{1,4}[A-Z]?)$/;
const ICAO_FLIGHT = /^([A-Z]{3})(\d{1,4}[A-Z]?)$/;

// "dl 1234", "DL-1234", "b6623" -> "DL1234", "B6623". Returns null if it isn't a flight number.
export function normalizeFlightNumber(input: string): string | null {
  const compact = input.toUpperCase().replace(/[\s-]/g, "");
  const match = IATA_FLIGHT.exec(compact) ?? ICAO_FLIGHT.exec(compact);

  if (!match || !/[A-Z]/.test(match[1])) {
    return null;
  }

  return `${match[1]}${match[2]}`;
}

// Local calendar date as YYYY-MM-DD (the format of <input type="date"> and our routes).
export function toDateInputValue(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

export function getSearchDateRange(today: Date = new Date()) {
  return {
    today: toDateInputValue(today),
    min: toDateInputValue(addDays(today, -SEARCH_PAST_DAYS)),
    max: toDateInputValue(addDays(today, SEARCH_FUTURE_DAYS)),
  };
}

const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

// YYYY-MM-DD strings compare correctly as plain strings.
export function isDateInRange(date: string, min: string, max: string): boolean {
  return DATE_PATTERN.test(date) && date >= min && date <= max;
}

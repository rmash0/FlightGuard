// Display formatting for flight data.

const TIME_PATTERN = /T(\d{2}):(\d{2})/;

// Wall-clock time at the airport ("2:05 PM"). Read from the ISO string itself because the
// backend sends airport-local times with an offset; new Date() would shift them to the viewer's zone.
export function formatLocalTime(iso: string): string {
  const match = TIME_PATTERN.exec(iso);
  if (!match) {
    return "--:--";
  }

  const hours = Number(match[1]);
  const hour12 = hours % 12 === 0 ? 12 : hours % 12;
  return `${hour12}:${match[2]} ${hours >= 12 ? "PM" : "AM"}`;
}

export function minutesBetween(startIso: string, endIso: string): number {
  return Math.round((Date.parse(endIso) - Date.parse(startIso)) / 60_000);
}

// 95 -> "1h 35m", 40 -> "40m"
export function formatDuration(totalMinutes: number): string {
  const minutes = Math.max(0, totalMinutes);
  const hours = Math.floor(minutes / 60);
  return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
}

function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

// "2026-10-11" -> "Oct 11"
export function formatShortDate(value: string): string {
  return parseIsoDate(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// "2026-10-11" -> "Sun, Oct 11"
export function formatFlightDate(value: string): string {
  return parseIsoDate(value).toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

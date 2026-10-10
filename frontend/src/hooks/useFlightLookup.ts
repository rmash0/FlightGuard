import { useEffect, useState } from "react";

import { lookupFlight } from "../api/client";
import type { FlightLookupResponse } from "../types/api";

export type FlightLookupState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; data: FlightLookupResponse };

// Fetches a flight lookup and refetches when the flight, date or retry count changes.
export function useFlightLookup(number: string, date: string) {
  const [attempt, setAttempt] = useState(0);
  // `key` records which request a result belongs to, so a stale result reads as loading.
  const key = `${number}/${date}/${attempt}`;
  const [result, setResult] = useState<{ key: string; state: FlightLookupState } | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    lookupFlight(number, date, controller.signal)
      .then((data) => setResult({ key, state: { status: "ready", data } }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setResult({ key, state: { status: "error", error } });
        }
      });

    return () => controller.abort();
  }, [key, number, date]);

  const state: FlightLookupState =
    result && result.key === key ? result.state : { status: "loading" };

  return { state, retry: () => setAttempt((count) => count + 1) };
}

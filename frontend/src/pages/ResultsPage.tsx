import { Link, Navigate, useParams } from "react-router";

import { ApiError, NOT_IN_DEMO } from "../api/client";
import AeroButton from "../components/aero/AeroButton";
import GlassPanel from "../components/aero/GlassPanel";
import { aeroButtonClass } from "../components/aero/classes";
import DemoFlightList from "../components/demo/DemoFlightList";
import EmissionsCard from "../components/eco/EmissionsCard";
import DelayGauge from "../components/results/DelayGauge";
import FlightSummary from "../components/results/FlightSummary";
import ReasonList from "../components/results/ReasonList";
import FlightSearchForm from "../components/search/FlightSearchForm";
import { useFlightLookup } from "../hooks/useFlightLookup";
import { isIsoDate, normalizeFlightNumber } from "../utils/flightSearch";
import { formatFlightDate } from "../utils/format";
import "./ResultsPage.css";

type ResultsMessageProps = {
  title: string;
  message: string;
  onRetry?: () => void;
};

function ResultsMessage({ title, message, onRetry }: ResultsMessageProps) {
  return (
    <GlassPanel as="section" className="results-message">
      <h1>{title}</h1>
      <p className="text-muted">{message}</p>
      <div className="results-message__actions">
        {onRetry && <AeroButton onClick={onRetry}>Try again</AeroButton>}
        <Link to="/" className={aeroButtonClass("glass")}>
          Back to search
        </Link>
      </div>
    </GlassPanel>
  );
}

// Friendly copy for each error the lookup endpoint can return (see AGENTS.md §5).
function describeError(error: unknown, number: string, date: string) {
  const status = error instanceof ApiError ? error.status : null;
  const detail = error instanceof ApiError ? error.detail : null;

  if (detail === NOT_IN_DEMO) {
    return {
      title: `${number} isn't in this demo`,
      message:
        "The demo includes a set of real flights recorded from live data. Pick one below, or run FlightGuard with your own API keys to search any US flight.",
      retryable: false,
    };
  }

  switch (status) {
    case 404:
      return {
        title: `We couldn't find ${number}`,
        message: `No ${number} flight departs on ${formatFlightDate(date)}. Double-check the flight number and date.`,
        retryable: false,
      };
    case 422:
      if (detail === "Only US airline flights are supported") {
        return {
          title: "Only U.S. airlines for now",
          message: "We currently support flights on U.S. airlines only. The flight must also depart from or arrive at a U.S. airport.",
          retryable: false,
        };
      }
      if (detail === "Flight must depart from or arrive at a US airport") {
        return {
          title: "That route is outside our coverage",
          message: "For now, U.S. airline flights must depart from or arrive at a U.S. airport.",
          retryable: false,
        };
      }
      return {
        title: "That flight number doesn't look right",
        message: "Use a U.S. airline code plus a number, like DL1234. We support U.S. airlines only for now.",
        retryable: false,
      };
    case 502:
      return {
        title: "Flight data is taking a breather",
        message: "Our flight data provider isn't responding right now. Try again in a minute.",
        retryable: true,
      };
    case 503:
      return {
        title: "Live flight data isn't connected",
        message: "The server has no flight data API key yet. Turn on demo mode or add the key.",
        retryable: false,
      };
    default:
      return {
        title: "We couldn't reach the server",
        message: "Check your connection and try again.",
        retryable: true,
      };
  }
}

function FlightResults({ number, date }: { number: string; date: string }) {
  const { state, retry } = useFlightLookup(number, date);

  if (state.status === "loading") {
    return (
      <GlassPanel as="section" className="results-loading" aria-live="polite">
        <span className="results-loading__orb" aria-hidden="true" />
        <p>Checking {number} for {formatFlightDate(date)}...</p>
      </GlassPanel>
    );
  }

  if (state.status === "error") {
    const { title, message, retryable } = describeError(state.error, number, date);
    const notInDemo = state.error instanceof ApiError && state.error.detail === NOT_IN_DEMO;
    return (
      <>
        <ResultsMessage title={title} message={message} onRetry={retryable ? retry : undefined} />
        {notInDemo && <DemoFlightList intro="These flights are included in the demo:" />}
      </>
    );
  }

  const { flight, prediction, emissions } = state.data;

  return (
    <>
      <FlightSummary flight={flight} />

      {/* Full-width sections, each split into two halves (stack on narrow screens). */}
      <GlassPanel as="section" className="results-panel" aria-labelledby="delay-title">
        <h2 id="delay-title">Delay forecast</h2>
        {prediction ? (
          <div className="results-panel__split">
            <DelayGauge prediction={prediction} />
            <div className="results-panel__reasons">
              <h3 className="results-panel__subheading">Why</h3>
              <ReasonList reasons={prediction.reasons} />
              <p className="results-panel__footnote">Model: {prediction.model}</p>
            </div>
          </div>
        ) : (
          <p className="text-muted">
            We couldn't make a delay forecast for this flight right now.
          </p>
        )}
      </GlassPanel>

      {/* EmissionsCard (Role D) renders its own full-width GlassPanel and heading, including the null state. */}
      <EmissionsCard emissions={emissions} />
    </>
  );
}

function ResultsPage() {
  const { number = "", date = "" } = useParams();
  const flightNumber = normalizeFlightNumber(number);

  // Tidy hand-typed URLs like /flight/dl-1234/... to the canonical form.
  if (flightNumber && flightNumber !== number) {
    return <Navigate to={`/flight/${flightNumber}/${date}`} replace />;
  }

  return (
    <>
      <GlassPanel className="results-search">
        {/* Keyed so the form refills when the page moves to a different flight. */}
        <FlightSearchForm
          key={`${number}/${date}`}
          compact
          initialFlightNumber={number}
          initialDate={isIsoDate(date) ? date : undefined}
        />
      </GlassPanel>

      {flightNumber && isIsoDate(date) ? (
        <FlightResults number={flightNumber} date={date} />
      ) : (
        <ResultsMessage
          title="That link doesn't look right"
          message="Flight links look like /flight/DL1234/2026-10-11. Try searching instead."
        />
      )}
    </>
  );
}

export default ResultsPage;

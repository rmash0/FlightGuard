import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import AeroButton from "../aero/AeroButton";
import AeroInput from "../aero/AeroInput";
import {
  getSearchDateRange,
  isDateInRange,
  normalizeFlightNumber,
} from "../../utils/flightSearch";
import "./FlightSearchForm.css";

const EXAMPLE_FLIGHTS = ["DL1234", "AA100", "B6 623"];

function formatDate(value: string): string {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function FlightSearchForm() {
  const navigate = useNavigate();
  const [range] = useState(() => getSearchDateRange());
  const [flightInput, setFlightInput] = useState("");
  const [date, setDate] = useState(range.today);
  const [submitted, setSubmitted] = useState(false);

  const flightNumber = normalizeFlightNumber(flightInput);
  const flightError = !flightInput.trim()
    ? "Enter a flight number, like DL1234."
    : flightNumber
      ? null
      : "That doesn't look like a flight number. Try an airline code plus a number, like DL1234 or B6 623.";
  const dateError = isDateInRange(date, range.min, range.max)
    ? null
    : `Pick a date between ${formatDate(range.min)} and ${formatDate(range.max)}.`;

  const showFlightError = submitted && flightError !== null;
  const showDateError = submitted && dateError !== null;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);

    if (flightNumber && !dateError) {
      navigate(`/flight/${flightNumber}/${date}`);
    }
  }

  return (
    <form className="flight-search" onSubmit={handleSubmit} noValidate>
      <div className="flight-search__fields">
        <div className="flight-search__field flight-search__field--number">
          <label htmlFor="flight-number">Flight number</label>
          <AeroInput
            id="flight-number"
            name="flightNumber"
            placeholder="DL1234"
            value={flightInput}
            onChange={(event) => setFlightInput(event.target.value)}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            maxLength={12}
            aria-invalid={showFlightError}
            aria-describedby={showFlightError ? "flight-number-error" : undefined}
          />
        </div>

        <div className="flight-search__field flight-search__field--date">
          <label htmlFor="flight-date">Date</label>
          <AeroInput
            id="flight-date"
            name="date"
            type="date"
            value={date}
            min={range.min}
            max={range.max}
            onChange={(event) => setDate(event.target.value)}
            aria-invalid={showDateError}
            aria-describedby={showDateError ? "flight-date-error" : undefined}
          />
        </div>

        <AeroButton type="submit" size="lg" className="flight-search__submit">
          Check flight
        </AeroButton>
      </div>

      {(showFlightError || showDateError) && (
        <div className="flight-search__errors" role="alert">
          {showFlightError && <p id="flight-number-error">{flightError}</p>}
          {showDateError && <p id="flight-date-error">{dateError}</p>}
        </div>
      )}

      <p className="flight-search__examples text-muted">
        Try{" "}
        {EXAMPLE_FLIGHTS.map((example) => (
          <button
            key={example}
            type="button"
            className="flight-search__example"
            onClick={() => setFlightInput(example)}
          >
            {example}
          </button>
        ))}
      </p>
    </form>
  );
}

export default FlightSearchForm;

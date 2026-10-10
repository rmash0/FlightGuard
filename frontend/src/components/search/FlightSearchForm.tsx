import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import AeroButton from "../aero/AeroButton";
import AeroInput from "../aero/AeroInput";
import { cx } from "../aero/classes";
import {
  getSearchDateRange,
  isDateInRange,
  normalizeFlightNumber,
} from "../../utils/flightSearch";
import { formatShortDate } from "../../utils/format";
import "./FlightSearchForm.css";

type FlightSearchFormProps = {
  // Compact: hidden labels and a smaller button, for the bar on top of the results page.
  compact?: boolean;
  initialFlightNumber?: string;
  initialDate?: string;
};

function FlightSearchForm({
  compact = false,
  initialFlightNumber = "",
  initialDate,
}: FlightSearchFormProps) {
  const navigate = useNavigate();
  const [range] = useState(() => getSearchDateRange());
  const [flightInput, setFlightInput] = useState(initialFlightNumber);
  const [date, setDate] = useState(initialDate ?? range.today);
  const [submitted, setSubmitted] = useState(false);

  const flightNumber = normalizeFlightNumber(flightInput);
  const flightError = !flightInput.trim()
    ? "Enter a flight number, like DL1234."
    : flightNumber
      ? null
      : "That doesn't look like a flight number. Try an airline code plus a number, like DL1234 or B6 623.";
  const dateError = isDateInRange(date, range.min, range.max)
    ? null
    : `Pick a date between ${formatShortDate(range.min)} and ${formatShortDate(range.max)}.`;

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
    <form
      className={cx("flight-search", compact && "flight-search--compact")}
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="flight-search__fields">
        <div className="flight-search__field flight-search__field--number">
          <label htmlFor="flight-number" className={cx(compact && "visually-hidden")}>
            Flight number
          </label>
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
          <label htmlFor="flight-date" className={cx(compact && "visually-hidden")}>
            Date
          </label>
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

        <AeroButton type="submit" size={compact ? "md" : "lg"} className="flight-search__submit">
          {compact ? "Search" : "Check flight"}
        </AeroButton>
      </div>

      {(showFlightError || showDateError) && (
        <div className="flight-search__errors" role="alert">
          {showFlightError && <p id="flight-number-error">{flightError}</p>}
          {showDateError && <p id="flight-date-error">{dateError}</p>}
        </div>
      )}
    </form>
  );
}

export default FlightSearchForm;

"""Train the BTS delay model and the route/hour lookup tables.

Reads monthly "Reporting Carrier On-Time Performance" zips from
``ml/data/`` (gitignored). The newest month is the test set. Every other
month trains the booster, except a random slice held out to calibrate
probabilities. Calibrating on a single month bakes that month's season
into every prediction: a June calibrator overstated October by about
4 points.

Writes:
- ``app/data/delay_model.joblib``
- ``app/data/model_meta.json``
- ``app/data/route_stats.json``

Run from ``backend/``::

    uv run python ml/train.py
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
ZIP_DIR = ROOT / "ml" / "data"
APP_DATA = ROOT / "app" / "data"

USECOLS = [
    "Month",
    "DayOfWeek",
    "Reporting_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
    "Distance",
    "ArrDel15",
    "ArrDelayMinutes",
    "Cancelled",
    "Diverted",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "LateAircraftDelay",
]
CAUSE_COLUMNS = {
    "CarrierDelay": "carrier",
    "WeatherDelay": "weather",
    "NASDelay": "nas",
    "LateAircraftDelay": "late_aircraft",
}
FEATURES = [
    "carrier",
    "origin",
    "dest",
    "month",
    "day_of_week",
    "dep_hour",
    "distance_miles",
]
CALIBRATION_SHARE = 0.10
MIN_ROUTE_FLIGHTS = 40
MIN_AIRPORT_FLIGHTS = 200
MAX_AIRPORTS = 250
ZIP_NAME = re.compile(r"bts_(\d{4})_(\d{1,2})\.zip$")


def main() -> None:
    frames = [_load_zip(path) for path in _zip_paths()]
    flights = pd.concat(frames, ignore_index=True)
    print(f"kept {len(flights):,} operated flights")
    periods = sorted(flights["period"].unique())
    if len(periods) < 2:
        raise SystemExit(f"need at least 2 months, found {periods}")
    test_period = periods[-1]
    train_periods = periods[:-1]
    print(
        f"train {train_periods} (minus {CALIBRATION_SHARE:.0%} for calibration)  test {test_period}"
    )

    route_stats = _route_stats(flights)
    hour_rows = _hour_stats(flights)
    _print_hours(hour_rows)
    flights = flights.drop(columns=[*CAUSE_COLUMNS, "ArrDelayMinutes"])

    encoded, categories = _encode(flights)
    y = encoded["delayed"].to_numpy()
    matrix = encoded[FEATURES].to_numpy(dtype=np.float64)
    period = encoded["period"].to_numpy()
    in_train_months = np.isin(period, train_periods)
    holdout = np.random.default_rng(0).random(len(period)) < CALIBRATION_SHARE
    train_mask = in_train_months & ~holdout
    calib_mask = in_train_months & holdout
    test_mask = period == test_period

    model = HistGradientBoostingClassifier(
        max_iter=80,
        learning_rate=0.1,
        max_depth=6,
        max_bins=255,
        min_samples_leaf=50,
        l2_regularization=0.1,
        categorical_features=[0, 1, 2],
        random_state=0,
    )
    print("fitting booster")
    model.fit(matrix[train_mask], y[train_mask])

    raw_calib = model.predict_proba(matrix[calib_mask])[:, 1]
    calibrator = IsotonicRegression(out_of_bounds="clip")
    calibrator.fit(raw_calib, y[calib_mask])
    use_calibrator = brier_score_loss(y[calib_mask], calibrator.predict(raw_calib)) <= brier_score_loss(
        y[calib_mask], raw_calib
    )
    saved_calibrator = calibrator if use_calibrator else None
    print(f"isotonic calibration {'kept' if use_calibrator else 'skipped'}")

    def apply(raw: np.ndarray) -> np.ndarray:
        if saved_calibrator is None:
            return raw
        return saved_calibrator.predict(raw)

    test_raw = model.predict_proba(matrix[test_mask])[:, 1]
    test_prob = apply(test_raw)
    test_rate = float(y[test_mask].mean())
    auc = float(roc_auc_score(y[test_mask], test_prob))
    print(
        f"test {test_period}: base rate {test_rate:.3f}  "
        f"mean predicted {float(test_prob.mean()):.3f}  AUC {auc:.3f}"
    )
    _print_samples(model, saved_calibrator, categories)

    meta = {
        "model": "bts-gbm-v1",
        "test_auc": round(auc, 3),
        "base_rate": round(test_rate, 4),
        "train_months": list(train_periods),
        "calibration_month": None,
        "test_month": test_period,
        "months": list(periods),
        "hourly_delay_rate": hour_rows,
    }
    APP_DATA.mkdir(parents=True, exist_ok=True)
    (APP_DATA / "model_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (APP_DATA / "route_stats.json").write_text(
        json.dumps({"min_flights": MIN_ROUTE_FLIGHTS, "routes": route_stats, "hours": hour_rows})
        + "\n",
        encoding="utf-8",
    )
    joblib.dump(
        {
            "model": model,
            "calibrator": saved_calibrator,
            "categories": categories,
            "features": FEATURES,
            "meta": meta,
        },
        APP_DATA / "delay_model.joblib",
    )
    print(f"wrote model, meta, and {len(route_stats):,} routes")


def _zip_paths() -> list[Path]:
    found = []
    for path in ZIP_DIR.glob("bts_*.zip"):
        match = ZIP_NAME.search(path.name)
        if match is None:
            continue
        found.append((int(match.group(1)), int(match.group(2)), path))
    found.sort()
    if not found:
        raise SystemExit(f"no BTS zips in {ZIP_DIR}")
    return [path for _, _, path in found]


def _load_zip(path: Path) -> pd.DataFrame:
    match = ZIP_NAME.search(path.name)
    assert match is not None
    period = f"{match.group(1)}-{int(match.group(2)):02d}"
    print(f"reading {path.name}")
    with zipfile.ZipFile(path) as archive:
        csv_name = next(name for name in archive.namelist() if name.lower().endswith(".csv"))
        with archive.open(csv_name) as handle:
            frame = pd.read_csv(handle, usecols=USECOLS, low_memory=False)
    operated = (frame["Cancelled"].fillna(1) == 0) & (frame["Diverted"].fillna(1) == 0)
    frame = frame.loc[operated].copy()
    frame = frame[frame["ArrDel15"].isin([0, 1, 0.0, 1.0])]
    frame = frame.dropna(subset=["Reporting_Airline", "Origin", "Dest", "Distance", "CRSDepTime"])
    frame["dep_hour"] = frame["CRSDepTime"].astype(int) // 100
    frame = frame[(frame["dep_hour"] >= 0) & (frame["dep_hour"] <= 23) & (frame["Distance"] > 0)]
    # BTS DayOfWeek is 1 (Monday) through 7 (Sunday). The runtime uses
    # datetime.weekday(), which is 0 (Monday) through 6 (Sunday).
    frame["day_of_week"] = frame["DayOfWeek"].astype(int) - 1
    frame = frame[(frame["day_of_week"] >= 0) & (frame["day_of_week"] <= 6)]
    frame["period"] = period
    frame["delayed"] = frame["ArrDel15"].astype(int)
    frame["carrier"] = frame["Reporting_Airline"].astype(str).str.strip()
    frame["origin"] = frame["Origin"].astype(str).str.strip()
    frame["dest"] = frame["Dest"].astype(str).str.strip()
    frame["month"] = frame["Month"].astype(int)
    frame["distance_miles"] = frame["Distance"].astype(float)
    frame["ArrDelayMinutes"] = frame["ArrDelayMinutes"].fillna(0).clip(lower=0)
    for column in CAUSE_COLUMNS:
        frame[column] = frame[column].fillna(0).clip(lower=0)
    keep = [
        "period",
        "delayed",
        "carrier",
        "origin",
        "dest",
        "month",
        "day_of_week",
        "dep_hour",
        "distance_miles",
        "ArrDelayMinutes",
        *CAUSE_COLUMNS,
    ]
    print(f"  {period}: {len(frame):,} rows")
    return frame[keep]


def _encode(flights: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    """Map carrier and airport codes to small integers. Rare airports share OTHER."""
    encoded = flights.copy()
    categories: dict[str, dict[str, int]] = {}
    for column in ("carrier", "origin", "dest"):
        counts = encoded[column].value_counts()
        if column == "carrier":
            keep = counts.index
        else:
            frequent = counts[counts >= MIN_AIRPORT_FLIGHTS]
            keep = frequent.index[:MAX_AIRPORTS]
        known = set(keep)
        labels = pd.Index(["OTHER", *sorted(known)])
        mapping = {label: index for index, label in enumerate(labels)}
        encoded[column] = encoded[column].map(lambda value, mapping=mapping: mapping.get(value, 0))
        categories[column] = mapping
        print(f"{column}: {len(mapping)} codes")
    return encoded, categories


def _route_stats(flights: pd.DataFrame) -> dict[str, dict]:
    grouped = flights.groupby(["origin", "dest"], observed=True)
    summary = grouped.agg(
        flights=("delayed", "size"),
        delay_rate=("delayed", "mean"),
        mean_delay_minutes=("ArrDelayMinutes", "mean"),
    )
    summary = summary[summary["flights"] >= MIN_ROUTE_FLIGHTS]
    causes = grouped[list(CAUSE_COLUMNS)].sum()
    totals = causes.sum(axis=1).replace(0, np.nan)
    share = causes.div(totals, axis=0).fillna(0.0)
    dominant = share.idxmax(axis=1)
    dominant_share = share.max(axis=1)
    routes: dict[str, dict] = {}
    for (origin, dest), row in summary.iterrows():
        key = f"{origin}-{dest}"
        entry = {
            "delay_rate": round(float(row["delay_rate"]), 4),
            "mean_delay_minutes": round(float(row["mean_delay_minutes"]), 1),
            "flights": int(row["flights"]),
        }
        if (origin, dest) in dominant_share.index and float(dominant_share.loc[(origin, dest)]) >= 0.35:
            entry["dominant_cause"] = CAUSE_COLUMNS[str(dominant.loc[(origin, dest)])]
        routes[key] = entry
    return routes


def _hour_stats(flights: pd.DataFrame) -> list[dict]:
    grouped = flights.groupby("dep_hour", observed=True)
    summary = grouped.agg(
        flights=("delayed", "size"),
        delay_rate=("delayed", "mean"),
        mean_delay_minutes=("ArrDelayMinutes", "mean"),
    )
    rows = []
    for hour in range(24):
        if hour not in summary.index:
            rows.append(
                {"hour": hour, "delay_rate": 0.0, "flights": 0, "mean_delay_minutes": 0.0}
            )
            continue
        row = summary.loc[hour]
        rows.append(
            {
                "hour": hour,
                "delay_rate": round(float(row["delay_rate"]), 4),
                "flights": int(row["flights"]),
                "mean_delay_minutes": round(float(row["mean_delay_minutes"]), 1),
            }
        )
    return rows


def _print_hours(rows: list[dict]) -> None:
    print("hour  delay_rate  mean_min  flights")
    for row in rows:
        print(
            f"{row['hour']:4d}  {row['delay_rate']:.3f}      "
            f"{row['mean_delay_minutes']:6.1f}  {row['flights']:8d}"
        )


def _print_samples(model, calibrator, categories: dict[str, dict[str, int]]) -> None:
    """Wednesday 14 Oct 2026, DL RDU→ATL (~356 miles), no live weather."""
    miles = 356.0
    print("sample DL RDU-ATL Wednesday in October, before live weather")
    for hour in (7, 12, 17, 20):
        row = [[
            categories["carrier"].get("DL", 0),
            categories["origin"].get("RDU", 0),
            categories["dest"].get("ATL", 0),
            10,
            2,
            hour,
            miles,
        ]]
        probability = float(model.predict_proba(row)[0, 1])
        if calibrator is not None:
            probability = float(calibrator.predict([probability])[0])
        print(f"  {hour:02d}:00  {probability:.3f}")


if __name__ == "__main__":
    main()

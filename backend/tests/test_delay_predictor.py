"""Unit checks for the heuristic and the weather/FAA fixtures."""

import asyncio
import json
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.clients.faa_status_client import clear_cache as clear_faa_cache
from app.clients.faa_status_client import parse_duration_minutes, parse_faa_xml
from app.clients.open_meteo_client import clear_cache as clear_weather_cache
from app.clients.open_meteo_client import get_forecast
from app.services.delay_predictor import clear_caches, pick_hour, score_delay

FIXTURES = Path(__file__).resolve().parents[1] / "app" / "data" / "fixtures"
EASTERN = timezone(timedelta(hours=-4))
CLEAR = {
    "time": "2026-03-03T16:00",
    "weather_code": 1,
    "precipitation_mm": 0.0,
    "visibility_m": 20000,
    "wind_gusts_kt": 12,
}


def _neutral_noon() -> datetime:
    """A local noon outside summer, holidays, Friday, and Sunday."""
    day = date(2026, 3, 1)
    while True:
        departure = datetime(day.year, day.month, day.day, 12, 0, tzinfo=EASTERN)
        if departure.weekday() not in (4, 6):
            return departure
        day += timedelta(days=1)


class DurationTests(unittest.TestCase):
    def test_phrases_from_the_live_feed(self):
        self.assertEqual(parse_duration_minutes("1 hour and 22 minutes"), 82)
        self.assertEqual(parse_duration_minutes("29 minutes"), 29)
        self.assertEqual(parse_duration_minutes("1 hour and 1 minute"), 61)
        self.assertEqual(parse_duration_minutes("3 hours and 4 minutes"), 184)
        self.assertEqual(parse_duration_minutes("1 hour and 46 minutes"), 106)
        self.assertEqual(parse_duration_minutes("2 hours and 5 minutes"), 125)
        self.assertEqual(parse_duration_minutes("16 minutes"), 16)
        self.assertIsNone(parse_duration_minutes("8:30 pm EDT"))
        self.assertIsNone(parse_duration_minutes(None))


class FaaParserTests(unittest.TestCase):
    def test_live_sample(self):
        events = parse_faa_xml((FIXTURES / "faa_nas_live.xml").read_text())
        self.assertEqual(events["PHX"][0]["type"], "ground_delay")
        self.assertEqual(events["PHX"][0]["avg_minutes"], 82)
        self.assertEqual(events["PHX"][0]["max_minutes"], 184)
        self.assertEqual(events["SFO"][0]["avg_minutes"], 29)
        self.assertEqual(events["SFO"][0]["max_minutes"], 106)
        self.assertEqual(events["SAN"][0]["type"], "general_delay")
        self.assertEqual(events["SAN"][0]["avg_minutes"], 61)
        self.assertEqual(events["JFK"][0]["avg_minutes"], 16)
        self.assertEqual(events["PNS"][0]["type"], "closure")
        self.assertTrue(any(event["type"] == "closure" for event in events["LAX"]))
        self.assertNotIn("ATL", events)

    def test_stormy_fixture(self):
        events = parse_faa_xml((FIXTURES / "faa_nas_stormy.xml").read_text())
        self.assertEqual(events["ATL"][0]["type"], "ground_stop")
        self.assertEqual(events["ATL"][0]["reason"], "thunderstorms")
        self.assertEqual(events["ATL"][0]["end_time"], "8:30 pm EDT")
        self.assertEqual(events["SFO"][0]["avg_minutes"], 72)
        self.assertEqual(events["SFO"][0]["max_minutes"], 125)
        self.assertEqual(events["ORD"][0]["type"], "general_delay")
        self.assertEqual(events["ORD"][0]["avg_minutes"], 31)
        self.assertEqual(events["BOS"][0]["type"], "closure")
        self.assertEqual(events["BOS"][0]["end_time"], "Oct 10 at 23:00 UTC.")


class HeuristicTests(unittest.TestCase):
    def test_stormy_fixture_is_high_risk(self):
        events = parse_faa_xml((FIXTURES / "faa_nas_stormy.xml").read_text())
        departure = datetime(2026, 10, 9, 18, 0, tzinfo=EASTERN)
        prediction = score_delay(
            origin_iata="RDU",
            destination_iata="ATL",
            departure=departure,
            arrival=departure + timedelta(hours=2),
            origin_weather=CLEAR,
            destination_weather={
                "time": "2026-10-09T22:00",
                "weather_code": 95,
                "precipitation_mm": 6.1,
                "visibility_m": 4000,
                "wind_gusts_kt": 32,
            },
            faa_events=events,
            now=departure - timedelta(hours=2),
        )
        self.assertEqual(prediction.risk, "high")
        self.assertGreaterEqual(prediction.probability_delayed, 0.5)
        self.assertEqual(prediction.model, "heuristic-v1")
        factors = {reason.factor for reason in prediction.reasons}
        self.assertIn("faa_destination", factors)
        self.assertIn("weather_destination", factors)
        self.assertTrue(any("Ground stop at ATL" in reason.detail for reason in prediction.reasons))

    def test_calm_afternoon_is_low_risk(self):
        departure = _neutral_noon()
        prediction = score_delay(
            origin_iata="RDU",
            destination_iata="ATL",
            departure=departure,
            arrival=departure + timedelta(hours=2),
            origin_weather=CLEAR,
            destination_weather=CLEAR,
            faa_events={},
            now=departure - timedelta(hours=3),
        )
        self.assertEqual(prediction.risk, "low")
        self.assertLess(prediction.probability_delayed, 0.25)
        self.assertEqual(
            prediction.reasons[0].detail,
            "No weather or airport issues expected",
        )

    def test_ground_delay_minutes_raise_the_estimate(self):
        departure = _neutral_noon()
        prediction = score_delay(
            origin_iata="RDU",
            destination_iata="SFO",
            departure=departure,
            arrival=departure + timedelta(hours=5),
            origin_weather=CLEAR,
            destination_weather=CLEAR,
            faa_events={
                "SFO": [
                    {
                        "type": "ground_delay",
                        "reason": "low ceilings",
                        "avg_minutes": 72,
                        "max_minutes": 125,
                        "end_time": None,
                    }
                ]
            },
            now=departure - timedelta(hours=1),
        )
        self.assertEqual(prediction.risk, "high")
        self.assertGreaterEqual(prediction.estimated_delay_minutes, 72)

    def test_ga_only_closure_does_not_change_the_score(self):
        departure = _neutral_noon()
        shared = dict(
            origin_iata="RDU",
            destination_iata="LAX",
            departure=departure,
            arrival=departure + timedelta(hours=5),
            origin_weather=CLEAR,
            destination_weather=CLEAR,
            now=departure - timedelta(hours=1),
        )
        calm = score_delay(faa_events={}, **shared)
        closed_to_ga = score_delay(
            faa_events={
                "LAX": [
                    {
                        "type": "closure",
                        "reason": "AD AP CLSD TO NON SKED TRANSIENT GA ACFT",
                        "avg_minutes": None,
                        "max_minutes": None,
                        "end_time": "later",
                    }
                ]
            },
            **shared,
        )
        self.assertEqual(calm.probability_delayed, closed_to_ga.probability_delayed)

    def test_fog_and_low_visibility_are_one_signal(self):
        departure = _neutral_noon()
        prediction = score_delay(
            origin_iata="RDU",
            destination_iata="ATL",
            departure=departure,
            arrival=departure + timedelta(hours=2),
            origin_weather={
                "time": "2026-03-03T16:00",
                "weather_code": 45,
                "precipitation_mm": 0.0,
                "visibility_m": 400,
                "wind_gusts_kt": 8,
            },
            destination_weather=CLEAR,
            faa_events={},
            now=departure - timedelta(hours=2),
        )
        weather_reasons = [
            reason for reason in prediction.reasons if reason.factor == "weather_origin"
        ]
        self.assertEqual(len(weather_reasons), 1)
        self.assertLess(prediction.probability_delayed, 0.45)

    def test_reported_delay_is_separate_from_the_score(self):
        departure = _neutral_noon()
        shared = dict(
            origin_iata="RDU",
            destination_iata="ATL",
            departure=departure,
            arrival=departure + timedelta(hours=2),
            origin_weather=CLEAR,
            destination_weather=CLEAR,
            faa_events={},
            now=departure - timedelta(hours=2),
        )
        baseline = score_delay(reported_delay_minutes=None, **shared)
        reported = score_delay(reported_delay_minutes=40, **shared)
        self.assertEqual(baseline.probability_delayed, reported.probability_delayed)
        self.assertEqual(reported.reported_delay_minutes, 40)
        self.assertIsNone(baseline.reported_delay_minutes)

    def test_far_future_flight_skips_weather(self):
        departure = _neutral_noon()
        prediction = score_delay(
            origin_iata="RDU",
            destination_iata="ATL",
            departure=departure,
            arrival=departure + timedelta(hours=2),
            origin_weather=None,
            destination_weather=None,
            faa_events={},
            now=departure - timedelta(days=20),
            weather_out_of_range=True,
        )
        self.assertTrue(any("16 days" in reason.detail for reason in prediction.reasons))
        self.assertTrue(all(reason.factor != "weather_destination" for reason in prediction.reasons))


class WeatherFixtureTests(unittest.TestCase):
    def test_pick_hour_reads_rdu_and_atl_from_one_payload(self):
        payload = json.loads((FIXTURES / "open_meteo_rdu_atl.json").read_text())
        self.assertEqual(len(payload), 2)
        moment = datetime(2026, 10, 11, 18, 30, tzinfo=timezone.utc)
        rdu = pick_hour(payload[0], moment)
        atl = pick_hour(payload[1], moment)
        self.assertIsNotNone(rdu)
        self.assertIsNotNone(atl)
        assert rdu is not None and atl is not None
        self.assertEqual(rdu["time"], "2026-10-11T18:00")
        self.assertEqual(rdu["weather_code"], 82)
        self.assertEqual(atl["weather_code"], 3)

    def test_demo_mode_returns_both_airports_for_any_date(self):
        previous = os.environ.get("DEMO_MODE")
        os.environ["DEMO_MODE"] = "true"
        try:
            rows = asyncio.run(
                get_forecast([(35.88, -78.79), (33.64, -84.43)], date(2026, 12, 1))
            )
        finally:
            if previous is None:
                os.environ.pop("DEMO_MODE", None)
            else:
                os.environ["DEMO_MODE"] = previous
        self.assertEqual(len(rows), 2)
        assert rows[0] is not None and rows[1] is not None
        self.assertIn("hourly", rows[0])
        self.assertTrue(str(rows[0]["hourly"]["time"][0]).startswith("2026-12-01"))
        self.assertTrue(str(rows[1]["hourly"]["time"][0]).startswith("2026-12-01"))


class RouteTests(unittest.TestCase):
    def setUp(self):
        self._previous_demo = os.environ.get("DEMO_MODE")
        os.environ["DEMO_MODE"] = "true"
        clear_caches()
        clear_weather_cache()
        clear_faa_cache()
        from fastapi.testclient import TestClient

        from app.main import app

        self.client = TestClient(app)

    def tearDown(self):
        if self._previous_demo is None:
            os.environ.pop("DEMO_MODE", None)
        else:
            os.environ["DEMO_MODE"] = self._previous_demo
        clear_caches()
        clear_weather_cache()
        clear_faa_cache()

    def test_predict_demo_flight_shape(self):
        response = self.client.get(
            "/api/predict",
            params={"number": "dl 1234", "date": "2026-10-11"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["model"], "heuristic-v1")
        self.assertIn(body["risk"], ("low", "medium", "high"))
        self.assertGreaterEqual(body["probability_delayed"], 0)
        self.assertLessEqual(body["probability_delayed"], 1)
        self.assertGreaterEqual(len(body["reasons"]), 1)
        self.assertIn("factor", body["reasons"][0])
        self.assertIn("detail", body["reasons"][0])
        self.assertIn("impact", body["reasons"][0])

    def test_unknown_flight_is_404(self):
        response = self.client.get(
            "/api/predict",
            params={"number": "UA9999", "date": "2026-10-11"},
        )
        self.assertEqual(response.status_code, 404)

    def test_non_us_airline_is_422(self):
        response = self.client.get(
            "/api/predict",
            params={"number": "ZZ9999", "date": "2026-10-11"},
        )
        self.assertEqual(response.status_code, 422)

    def test_sample_flight_resolves_on_any_date(self):
        response = self.client.get(
            "/api/predict",
            params={"number": "DL1234", "date": "2026-10-12"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_stormy_airport_is_high_risk(self):
        response = self.client.get("/api/airports/atl")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["iata"], "ATL")
        self.assertEqual(body["risk"], "high")
        self.assertEqual(body["faa_events"][0]["type"], "ground_stop")
        self.assertIsNotNone(body["weather"])
        self.assertTrue(any("Ground stop" in reason["detail"] for reason in body["reasons"]))

    def test_airport_from_role_d_list_resolves(self):
        response = self.client.get("/api/airports/abq")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["iata"], "ABQ")

    def test_unknown_airport_is_404(self):
        response = self.client.get("/api/airports/XYZ")
        self.assertEqual(response.status_code, 404)

    def test_openapi_lists_both_routes(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/predict", paths)
        self.assertIn("/api/airports/{iata}", paths)
        predict_schema = paths["/api/predict"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        self.assertIn("$ref", predict_schema)


class LookupHandoffTests(unittest.TestCase):
    """Role B's lookup passes schemas.Flight in and validates schemas.DelayPrediction out."""

    def setUp(self):
        self._previous_demo = os.environ.get("DEMO_MODE")
        os.environ["DEMO_MODE"] = "true"
        clear_caches()

    def tearDown(self):
        if self._previous_demo is None:
            os.environ.pop("DEMO_MODE", None)
        else:
            os.environ["DEMO_MODE"] = self._previous_demo
        clear_caches()

    def test_lookup_flight_model_gets_a_prediction(self):
        from app.models.schemas import DelayPrediction
        from app.services.demo_fixtures import get_demo_lookup
        from app.services.flight_lookup import _optional_service

        lookup = get_demo_lookup("DL1234", date(2026, 10, 11))
        assert lookup is not None
        prediction = asyncio.run(
            _optional_service(
                "app.services.delay_predictor", "predict_delay", lookup.flight, DelayPrediction
            )
        )
        self.assertIsNotNone(prediction)
        assert prediction is not None
        self.assertEqual(prediction.model, "heuristic-v1")

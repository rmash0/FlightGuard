# Role C: Remaining Work

> Status as of 2026-10-10, evening. Read `AGENTS.md` first, then `docs/role-c-spec.md`.

## Done (spec tasks 1–8)
- Weather and FAA clients, heuristic v1, `/api/predict`, `/api/airports/{iata}`.
- `backend/ml/train.py` uses six BTS months (Oct–Nov 2025 and Apr–Jul 2026). July 2026, the newest, is held out as the test set: AUC **0.704**. The other five months train the model, minus a random 10% used for isotonic calibration. Artifacts: `app/data/delay_model.joblib`, `model_meta.json`, `route_stats.json` (commit these; the app reads them). Raw zips stay in `backend/ml/data/` (gitignored). Retrain with `uv run python ml/train.py` from `backend/` (about 30 s).
- Calibration was first fit on June alone, which overstated October and November by about 4 points (24.5% predicted vs 20.3% actual). With the random holdout, October predicts 20.4% vs 20.3% actual.
- Runtime blend: `model: "bts-gbm-v1"` starts from the model probability and adds only live weather and FAA. Schedule effects are not added again. Missing model file falls back to `heuristic-v1`. International legs (an airport not in `airports.json`) also use the heuristic, since BTS is domestic only.
- `historical_route` reasons come from `route_stats.json`. On the model path, a `time_of_day` note gives the national BTS rate for the departure hour when it is notably high (≥ 30%) or low (≤ 12%). Both are explanations only and don't move the score. Distance is the great-circle miles between the airports until B adds `distance_km`.
- `GET /api/predict/model` returns `ModelInfo` (AUC, months, `hourly_delay_rate`). Contract updated in `AGENTS.md` §8, `schemas.py`, and `frontend/src/types/api.ts`.
- Weather, FAA, and prediction caches use B's `TTLCache`. `clients/memory_cache.py` is gone.
- Calm weekday evenings are no longer an automatic "medium". See below.

## Not built (needs A)
- The About page still does not render the AUC or the hourly chart. The data is on `GET /api/predict/model`. A owns that page and `api/client.ts`. Chart placement (About vs results) is A's call; the series is `hourly_delay_rate`.

## Open questions
- **B:** add `distance_km` and `estimated_arrival` on `flight`? The predictor computes distance until then. Please review `ModelInfo` on the contract (`schemas.py` / `types/api.ts`).
- **B:** demo-mode lookup still returns the fixture's recorded prediction, so the model is invisible on the results page in `DEMO_MODE`. `/api/predict` does rescore. Should demo lookup call `predict_delay`?
- **A:** show `test_auc` and `hourly_delay_rate` on About (recommended) or also on the results page?
- **D:** `backend/app/api/eco.py` is still unused (not registered; reads `GOOGLE_API_KEY`).

## Evening risk (checked against BTS)
National arrivals 15+ minutes late, Apr–Jul 2026 plus Oct–Nov 2025:

| Local hour | Delay rate | Average minutes late |
|---|---|---|
| 7am | 12% | 9 |
| 12pm | 22% | 16 |
| 2pm | 27% | 20 |
| 6pm | 34% | 26 |
| 8pm | 34% | 26 |

A flat +0.5 log-odds bump marked every calm evening medium (~29%), including easy flights. The heuristic deltas are now +0.12 (5–7pm) and +0.20 (7–10pm), so a calm weekday evening stays under 25%.

The shipped model is route-specific, which is what the demo should show:

| Flight (Wed 14 Oct, no weather) | Chance late | Risk | Expect |
|---|---|---|---|
| DL RDU→ATL 7am | 5% | low | ~9 min |
| DL RDU→ATL 6pm | 14% | low | ~13 min |
| DL ORD→LGA 6pm | 49% | medium | ~35 min |

RDU→ATL is late 14% of the time in this sample (average 13 minutes). ORD→LGA is late 34% (average 29 minutes), and the evening bank is worse. Those are not the same flight, and the gauge no longer treats them as one.

# Smart Renewable Energy Microgrid — dataset edition

A complete local dataset-analysis website with Dashboard, Energy Monitoring, AI Prediction, Anomalies, Alerts, System Status and original PPT Objectives. The navy/blue design and light/dark/system themes are retained. No hardware, sensors, API keys, ML installation or internet connection are required to view the included data and forecasts.

## Run in VS Code on Windows

1. Extract the ZIP. Open the included `microgrid-updated` folder in VS Code (the folder containing `start.bat`).
2. Open Terminal → New Terminal.
3. Run `python backend/server.py` using Python 3.10+.
4. Open http://localhost:8000 and keep the terminal running. Alternatively double-click `start.bat`.
5. If port 8000 is occupied, run `python backend/server.py --port 8001` and open http://localhost:8001.

The prebuilt frontend is included. Node is only needed if you edit the frontend source. This localhost address works after starting the server on your own computer.

## Explore the website

- Dashboard: solar, demand, import, export, solar forecast and calculated energy exposure cards.
- Playback: play/pause, speed control, time slider, jump to date and 24/48/168-record windows. It advances through historical records without altering timestamps.
- Energy Monitoring: selected-interval energy totals, solar load coverage, charts and readings table. Gaps are excluded rather than interpolated.
- AI Prediction: historical one-hour-ahead solar/load forecasts, selected issue/target times, window errors and full held-out model metrics.
- Anomalies: adjustable solar forecast error threshold and transparent energy exposure calculation.
- Alerts: review flagged historical observations, filter reviewed/unreviewed items and persist marks in this browser.
- Exports: selected-window CSV, full held-out CSV and downloadable JSON analysis report.
- System Status: provenance, dataset period, transformation assumptions and limitations.
- Objectives: original PPT text preserved, with the implemented dataset scope explained.

## Included real dataset

The dashboard opens the bundled historical dataset automatically. No sensors or accounts are required. It uses Open Power System Data / CoSSMic residential3 measured energy counters from southern Germany, version 2020-04-15. These are real historical observations, not current measurements of your microgrid. The original sample dates remain visible; playback never changes them to today's date.

Source: https://data.open-power-system-data.org/household_data/2020-04-15/

We derive hourly-average solar kW from successive cumulative solar kWh counters. Net grid kW comes from import/export counter differences. Derived household load = PV + import − export, assuming no unmetered storage at this household. Only exact one-hour intervals with nonnegative counter deltas and no source-marked interpolation in the selected meters at either endpoint are included. Tiny (<0.005 kWh) negative load caused by rounding is clipped to zero; larger negative values are rejected.

The source timestamp identifies a counter sample. The derived average power refers to the preceding hour and is placed at its ending timestamp. It is not instantaneous power. Playback advances by one observed hourly interval, and chart gaps remain visible.


## Predictions that were actually evaluated

The included forecasts predict one hour ahead. Random Forest, Extra Trees and histogram gradient boosting candidates were fitted on the earliest 60% of eligible samples, selected on the next 20%, then assessed on the final 20%. Labels crossing chronological boundaries were purged. Forecast inputs use current/lagged measurements and known calendar values only. Persistence and daily seasonal baselines were included in model selection.

The test set has 2,198 forecast targets:

| Target | Selected model | Test MAE | Test RMSE | Persistence MAE |
|---|---|---:|---:|---:|
| Solar generation | Histogram boosting, absolute-error loss | 0.126 kW | 0.267 kW | 0.251 kW |
| Load demand | Histogram boosting, absolute-error loss | 0.571 kW | 17.143 kW | 0.615 kW |

The large load RMSE reflects large counter-derived outliers retained in the source. This model is not ready for dependable load dispatch. Test error is reported without removing difficult test cases or claiming perfect predictions. These results apply to this historical household only, not your hardware. Further source-quality investigation and representative local data are needed before operational use.

`backend/data/holdout.json` contains the actual held-out observations and forecasts, with original issue/target timestamps. Replay serves these precomputed forecasts, so Python ML packages are not needed merely to view results. It does not run a hidden synthetic generator.

Included provenance and reproducibility files:

- `source_counters.csv`: selected raw cumulative source columns plus source interpolation flags.
- `measured_hourly.csv`: derived hourly solar, load and net-grid values.
- `evaluation.json`: exact split boundaries, error metrics, source SHA-256 and excluded-interval count.
- `dataset_models.joblib`: fitted dataset models; load only this trusted locally generated artifact.
- `prepare_real_data.py`: extraction, training, model selection and test evaluation.

### Reproduce the real-dataset training

```bat
python -m pip install -r backend/requirements.txt
```

Download the original hourly CSV from:
https://data.open-power-system-data.org/household_data/2020-04-15/household_data_60min_singleindex.csv

Then run:

```bat
python backend/prepare_real_data.py "C:\path\household_data_60min_singleindex.csv"
```

Restart the backend and refresh the dashboard. This trains the historical dataset models only; it does not install a German household model for your live Indian microgrid.

## Where the risk comes from

See `RISK_AND_LIVE_SETUP.md` (updated for dataset-only analysis). This edition calculates an **energy exposure index**, not hardware risk or failure probability:

- Grid dependence = max(load − solar, 0) / load; zero for zero load.
- Solar forecast error = |actual solar − forecast solar|.
- Error severity = min(error / adjustable threshold, 1), default threshold 0.5 kW.
- Index = 100 × (0.7 × grid dependence + 0.3 × error severity), rounded to a whole number.
- Display bands: low <30, moderate 30–69, high ≥70.

Weights, threshold and bands are illustrative analysis choices, not PPT-prescribed values or learned failure limits. Grid import can be normal. The index uses the actual historical observation, so it is retrospective, not a future risk prediction. Forecast-error alerts are review flags only. No SOC, temperature, voltage or equipment-health data is invented.

Older optional live-ingestion utilities remain in backend source for compatibility, but this website has no live-sensor mode and does not require or start a simulator by default.

## Edit and verify

Node 22.12+ is needed only to edit/build the UI:

```bat
npm ci
npm run dev
```

Keep Python running in another terminal. To update the prebuilt website:

```bat
npm run build
npm run lint
node --test src/analysis.test.js
python -m unittest discover -s backend -p "test_*.py"
```

## Attribution

Open Power System Data. 2020. Data Package Household Data. Version 2020-04-15. https://data.open-power-system-data.org/household_data/2020-04-15/. Primary measurements: CoSSMic. Licensed CC BY 4.0: https://creativecommons.org/licenses/by/4.0/.

Changes: subset to residential3 counters, filter source-marked interpolation and invalid intervals, derive hourly powers, chronological train/validation/test split, produce forecasts and dashboard views. The original source includes filled gaps; selected-column flagged intervals were excluded rather than presented as direct measurements.


## Windows connection-aborted fix

This version handles browser connection closures, including WinError 10053, without printing an unhandled request traceback. HTML responses disable caching. The dataset UI uses a normal dataset request and never opens a live sensor stream. Stop old servers and close old tabs before opening this version. Use port 8001 if an older server occupies port 8000.

## Dataset chat and next-hour estimates

Chat Assistant supports forecasts, energy summaries, model errors, anomalies, risk explanations and source questions. It is an offline intent-based assistant using deterministic dataset calculations, not an external generative LLM. No API key is required. Each answer includes its record context. The AI page now includes the next-hour saved forecast issued at the selected historical time. Missing forecast intervals are shown as unavailable.

If the page still shows Live sensors, close old tabs, stop the old server, extract this ZIP to a new folder, run `python backend/server.py --port 8001` there and open http://localhost:8001.

## Sliding menu, 100 questions and improved forecasts

The desktop menu collapses to an icon rail. At 900px and below it becomes an overlay drawer; Escape, backdrop click or selecting a section closes it. The mobile drawer traps keyboard focus and restores it to the menu button. Reduced-motion preference is respected.

Chat Assistant includes a searchable, categorized bank of 100 exact supported questions. Ask by text or ID (Q1 to Q100), or click a question. Free-form matching remains limited; this is an offline intent-based assistant, not a generative LLM. The matching PDF is in docs/ and can be downloaded separately. Export chat saves visible answers and their original data contexts.

The fixed added forecast candidates were selected using validation MAE only. Compared with the earlier shipped model, test solar MAE improved from 0.132139 to 0.126065 kW; load MAE improved from 0.594333 to 0.571446 kW. Load RMSE slightly worsened from 17.139148 to 17.142829 kW. The previously inspected test period is reused for comparison, not a new independent prospective trial.

Intervals use the 90th-percentile validation absolute residual (finite-sample quantile adjustment). Empirical test coverage is 73.75% for solar and 92.22% for load. Solar coverage below the nominal 90% reflects temporal shift; no individual prediction guarantee is made. Validation candidate scores and measured coverage appear in AI Prediction.

Import/export cards and totals are derived from positive/negative **net hourly grid exchange**. They are not gross bidirectional meter totals.

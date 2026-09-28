# Dataset-only risk and data guide

No sensors are needed. Start `python backend/server.py`, then open http://localhost:8000.

## Data source

Bundled measured OPSD/CoSSMic residential3 hourly solar and grid counters. The website displays 2,198 held-out forecast targets with original 2017 timestamps. They are historical observations, never live readings. Derived demand assumes no unmetered storage. Missing/interpolated intervals are excluded; source outliers remain.

## Energy exposure index

This replaces the unavailable equipment-health score:

`100 * (0.7 * max(load - solar, 0)/load + 0.3 * min(abs(solar - solar_prediction)/threshold, 1))`

For zero load, the dependence term is zero. Threshold defaults to 0.5 kW and can be changed in Anomalies (minimum 0.01 kW). Low <30; moderate 30–69; high >=70. These are illustrative weights and display bands. The score describes historical grid dependence and forecast error, not a future fault, calibrated risk probability or unsafe condition. Grid dependence is often normal.

## Alerts and predictions

A review alert appears when the observed solar forecast error exceeds the selected threshold. Alerts use the selected window; changing the window or threshold changes the matching records. Mark reviewed / Undo review persists in this browser. It does not resolve any equipment fault.

AI predictions are genuine held-out model outputs issued one hour before each target. They do not predict today's generation. No current weather or sensor connection is used. Test metrics and source outlier limitations appear on the AI page.

## Objectives

PPT objectives are retained verbatim. Sensor acquisition, storage dispatch and hardware predictive maintenance remain objectives outside the dataset demonstration's validated scope.

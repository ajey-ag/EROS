---
id: TASK-007
title: Implement champion/challenger tracker
status: todo
depends_on:
- TASK-006
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/tracker.py`: `Tracker(primary_metric: str = "rmse", state_path: str | Path =
"champion.json")` with `evaluate(result: BacktestResult) -> Report`. On evaluate: load
champion.json if present, else champion defaults to the first model in the result; compare
each model's overall primary metric (lower is better); if a challenger beats the champion,
mark it highlighted and write the new champion to champion.json ({model_name,
primary_metric, value, timestamp} — ISO timestamp). `Report` exposes `to_json(path)`
writing comparison.json (per-model aggregate + per-fold + per-horizon metrics, champion
flag, challenger highlights, run metadata; all values JSON-serializable) and
`print_table()` printing an aligned text table with the champion marked. Tests in
`tests/test_tracker.py` build a small fake BacktestResult with known metrics, use tmp_path
for both JSON files, and assert champion selection, challenger promotion (champion.json
updated), no-update when champion still wins, and that comparison.json parses via
json.load with expected keys.

## Acceptance criteria

- With no existing champion.json, the first model becomes champion and is flagged in the report
- A challenger with a lower rmse overwrites champion.json with its name and value
- When the existing champion still has the best rmse, champion.json is unchanged
- comparison.json written by to_json is valid JSON containing per-model aggregate metrics, per-horizon breakdown, and the champion flag
- print_table runs without error and its captured output contains every model name

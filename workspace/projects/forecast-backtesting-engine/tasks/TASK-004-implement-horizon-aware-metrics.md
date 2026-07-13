---
id: TASK-004
title: Implement horizon-aware metrics
status: todo
depends_on:
- TASK-001
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/metrics.py`: `horizon_metrics(actuals: np.ndarray, preds: np.ndarray)
-> pd.DataFrame` returning a DataFrame indexed by horizon step h=1..H with columns
`mae`, `rmse`, `mape` (per-step values; with one fold each step has one sample, so
per-step mae == abs error). MAPE masks zero actuals: a zero-actual step gets NaN mape,
and the frame carries the masked count (e.g. `df.attrs["mape_masked"]`). Raise ValueError
on shape mismatch. Also `aggregate_folds(frames: list[pd.DataFrame]) -> pd.DataFrame`
averaging metrics per horizon step across folds (NaN-aware mean for mape), plus an
`overall` row averaging across all steps. Tests in `tests/test_metrics.py` pin
hand-computed values on a small fixture (e.g. actuals [100, 200, 0], preds [110, 180, 5]:
h=1 mae=10, h=2 mae=20, mape masked at h=3).

## Acceptance criteria

- horizon_metrics on the 3-step fixture matches hand-computed mae/rmse/mape per step to within 1e-9
- A zero actual yields NaN mape at that step and mape_masked count of 1
- aggregate_folds over two known FoldMetrics frames returns the exact per-step means and an overall row
- ValueError raised when actuals and preds lengths differ

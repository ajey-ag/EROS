# Forecast Backtesting Engine

**Promoted from:** IDEA-025 · **Domain:** ML Systems & Reliability · **Score:** 22/25

## Pitch

Walk-forward backtesting with leakage guards, horizon-aware metrics, and champion/challenger tracking for time-series models — builds directly on the Rossmann forecasting work.

## Goals

- A `WalkForwardSplitter` that generates expanding or rolling train/test windows
  over a time-indexed dataset, with a configurable forecast horizon and a gap to
  prevent leakage between train and test windows.
- A **leakage guard**: static assertions that no test-window timestamp ever
  appears in the corresponding train window, and that any feature engineering
  step is fit only on train data (raise if a caller tries to fit on the full
  series).
- **Horizon-aware metrics**: compute MAE/RMSE/MAPE per forecast step (h=1, h=2, ...)
  not just averaged over the whole horizon, so error growth with horizon is visible.
- A **champion/challenger tracker**: register named models, run them all through
  the same walk-forward splits, and produce a comparison report (per-fold and
  aggregate metrics) with the current "champion" flagged and any "challenger"
  that beats it on the primary metric highlighted.
- A worked demonstration on the Rossmann store-sales data at
  `C:\Users\dell\Documents\project\rossmann_data\train.csv` (and `store.csv` in
  the same folder) comparing at least a naive baseline (seasonal last-value)
  against one real model (e.g. gradient boosting on lag/calendar features).
  Pass this path in via a CLI argument or config, defaulting to that absolute
  path — do not assume a fixed relative depth from the build directory.

## Success criteria

- `WalkForwardSplitter` unit-tested for both expanding and rolling modes,
  correct window boundaries, and horizon/gap handling on synthetic date ranges.
- Leakage guard has tests proving it raises on at least 2 constructed leakage
  scenarios (overlapping windows, feature fit on full series).
- Horizon-aware metrics tested against hand-computed expected values on a small
  fixture forecast.
- `python -m backtest.demo` runs the Rossmann comparison end-to-end and writes a
  `comparison.json` + printed champion/challenger table.
- `pytest` green for the full package.

## Constraints

- Python-first; runs on a single Windows laptop without cloud infrastructure.
- Keep external dependencies minimal and justified (pandas + numpy are fine;
  a gradient boosting model may use scikit-learn or lightgbm — pick one and
  justify it in architecture.md).
- Do not modify or copy the parent `rossmann_data/` folder; read it in place.

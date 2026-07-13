# Architecture: Forecast Backtesting Engine

## Overview

This is a single Python package, `backtest`, that provides walk-forward backtesting primitives for time-series models: window generation, leakage prevention, per-horizon metrics, and multi-model comparison. The design philosophy is that each capability is a small, independently testable module with plain-data interfaces (dataclasses, numpy arrays, pandas DataFrames) rather than a framework. Models plug in through a minimal protocol — `fit(train_df)` / `predict(horizon_index)` — so the engine never needs to know whether it's talking to a naive baseline or a gradient-boosted regressor.

The core loop is deliberately boring: the `WalkForwardSplitter` yields `(train_window, test_window)` pairs as timestamp ranges; the runner slices the dataset, hands train data to each registered model, collects horizon-aligned predictions, and passes them to the metrics module. The leakage guard sits at two choke points — it validates every split the splitter emits, and it wraps feature-engineering objects so any attempt to fit on data extending past the train boundary raises immediately. Putting the guard on the data path (rather than trusting callers) is what makes the leakage claims testable.

Everything runs in-process on one laptop. State between runs is just files: a `comparison.json` report and a champion record. No database, no services, no parallelism beyond what scikit-learn does internally. The Rossmann demo is a thin script on top of the library, proving the pieces compose without becoming part of the core API.

## Components

1. **`backtest.splitter` — WalkForwardSplitter**
   Responsibility: generate expanding or rolling train/test window pairs over a time index, honoring `horizon` (test window length in steps) and `gap` (steps skipped between train end and test start).
   Key interfaces: `WalkForwardSplitter(mode, min_train_size, horizon, gap, step)` with `split(index: pd.DatetimeIndex) -> Iterator[Fold]`, where `Fold` is a frozen dataclass holding `fold_id`, `train_start/end`, `test_start/end`.

2. **`backtest.guard` — Leakage guard**
   Responsibility: enforce train/test separation. Two parts: `assert_no_overlap(fold, index)` verifies no test timestamp falls inside the train window (called on every fold by the runner); `GuardedTransformer` wraps any fit/transform object and raises `LeakageError` if `fit` is called with data whose max timestamp exceeds the current fold's train boundary.
   Key interfaces: `assert_no_overlap(fold, index)`, `GuardedTransformer(inner, train_end).fit/transform`, `LeakageError`.

3. **`backtest.metrics` — Horizon-aware metrics**
   Responsibility: compute MAE, RMSE, MAPE per forecast step (h=1..H) and aggregated, from aligned actual/predicted arrays; aggregate across folds.
   Key interfaces: `horizon_metrics(actuals, preds) -> pd.DataFrame` (rows=h, cols=metrics), `aggregate_folds(list[pd.DataFrame]) -> pd.DataFrame`.

4. **`backtest.models` — Model protocol and reference models**
   Responsibility: define the `ForecastModel` protocol (`fit(train: pd.DataFrame)`, `predict(test_index) -> np.ndarray`) and ship two implementations: `SeasonalNaive` (last value from the same weekday/season) and `GradientBoostingModel` (lag + calendar features via a `GuardedTransformer`-wrapped feature builder, scikit-learn `HistGradientBoostingRegressor`).
   Key interfaces: `ForecastModel` protocol, the two concrete classes, `build_features(df, train_end)`.

5. **`backtest.runner` — Backtest runner**
   Responsibility: given a dataset, a splitter, and named models, run every model over every fold (asserting the leakage guard on each), collect per-fold horizon metrics, and return a structured `BacktestResult`.
   Key interfaces: `run_backtest(df, target_col, splitter, models: dict[str, ForecastModel]) -> BacktestResult`.

6. **`backtest.tracker` — Champion/challenger tracker**
   Responsibility: take a `BacktestResult` plus a primary metric, flag the current champion (persisted in `champion.json`, defaulting to the first registered model), highlight any challenger beating it, and emit `comparison.json` plus a printed table.
   Key interfaces: `Tracker(primary_metric, state_path).evaluate(result) -> Report`, `Report.to_json(path)`, `Report.print_table()`.

7. **`backtest.demo` — Rossmann demonstration CLI**
   Responsibility: `python -m backtest.demo [--data-dir PATH]` (default `C:\Users\dell\Documents\project\rossmann_data`) loads `train.csv` + `store.csv` read-only, prepares one store's series (or a small sample of stores), runs SeasonalNaive vs. GradientBoostingModel through the runner and tracker, writes `comparison.json`, prints the table.
   Key interfaces: `main(argv)`, argparse with `--data-dir`, `--store-id`, `--horizon`.

## Data model

All core entities are in-memory dataclasses; the only persisted artifacts are two JSON files.

- **Fold** — `fold_id: int`, `train_start/train_end/test_start/test_end: pd.Timestamp`. Emitted by the splitter, consumed by runner and guard. Never stored.
- **Time-series dataset** — a pandas DataFrame with a `DatetimeIndex` and a target column; feature columns are added per-fold by the guarded feature builder and discarded after the fold.
- **FoldMetrics** — a DataFrame indexed by horizon step with columns `mae`, `rmse`, `mape`, tagged with `model_name` and `fold_id`.
- **BacktestResult** — `{model_name: {per_fold: [FoldMetrics], aggregate: DataFrame}}` plus run metadata (splitter config, dataset span).
- **comparison.json** — serialized report: per-model aggregate and per-fold metrics, per-horizon breakdown, champion flag, challenger highlights, run config. Written fresh each run.
- **champion.json** — `{model_name, primary_metric, value, timestamp}`; read at tracker start, updated only when a challenger wins.

## Technology choices

- **Python 3.11+** — charter mandates Python-first; dataclasses and typing are all that's needed.
- **pandas + numpy** — the natural representation for time-indexed data and windowed slicing; explicitly allowed.
- **scikit-learn (`HistGradientBoostingRegressor`)** — chosen over LightGBM: comparable accuracy on tabular lag features, no extra native dependency to install on Windows, and it handles NaN lags natively. One fewer wheel to break.
- **pytest** — the success criteria require it; standard, zero config.
- **stdlib `json` + `argparse`** — persistence and CLI needs are trivial; no click, no pydantic.

## Build order

1. **`splitter`** — everything downstream consumes folds; it's pure logic, testable on synthetic date ranges with no other modules.
2. **`guard`** — depends only on `Fold`; building it second means every later component can be developed with the guard already enforcing correctness.
3. **`metrics`** — pure array math, independently testable against hand-computed fixtures; needed before the runner can produce anything meaningful.
4. **`models`** — the protocol plus SeasonalNaive first (trivial, unblocks the runner), then the gradient-boosting model with the guarded feature builder.
5. **`runner`** — composes splitter, guard, models, metrics; by now every dependency is tested in isolation, so runner tests can focus on orchestration (fold counts, guard invocation, result shape).
6. **`tracker`** — consumes a `BacktestResult`, which now exists; JSON I/O and table formatting are low-risk finishing work.
7. **`demo`** — last, because it's integration: it exercises the full stack on real data and will surface any Rossmann-specific data-cleaning surprises without contaminating core modules.

## Risks

1. **Silent leakage through feature engineering.** Lag/rolling features computed on the full series before splitting would defeat the whole point. Mitigation: features are built per-fold inside the model's `fit`, behind `GuardedTransformer`, which raises if fit data crosses the train boundary; tests construct exactly this violation and assert `LeakageError`.
2. **Rossmann data irregularities break the demo.** Closed stores (Sales=0, Open=0), missing dates, and ~1M rows can produce misaligned horizons or slow runs. Mitigation: the demo filters to open days of a single store (configurable), reindexes to a continuous date range, and the runner asserts prediction length equals test-window length before metrics — misalignment fails loudly instead of skewing MAPE.
3. **MAPE instability on zero/near-zero actuals.** Rossmann sales include zeros; naive MAPE divides by them. Mitigation: metrics module masks zero actuals from MAPE (reporting the masked count) and the comparison uses RMSE as the primary champion metric, with MAPE as supplementary; the fixture tests pin this masking behavior.

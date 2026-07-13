# Forecast Backtesting Engine

Walk-forward backtesting for time-series forecasting models: expanding/rolling
window generation with leakage guards, horizon-aware metrics (MAE/RMSE/MAPE per
forecast step), and champion/challenger model tracking.

## Install

```
pip install -e .[dev]
```

## Usage

```
pytest                    # run the test suite
python -m backtest.demo   # Rossmann store-sales comparison (see --help)
```

## Modules

| Module | Responsibility |
| --- | --- |
| `backtest.splitter` | `WalkForwardSplitter` — expanding/rolling train/test windows with horizon and gap |
| `backtest.guard` | Leakage guard — overlap assertions and `GuardedTransformer` |
| `backtest.metrics` | Per-horizon MAE/RMSE/MAPE and fold aggregation |
| `backtest.models` | `ForecastModel` protocol, `SeasonalNaive`, gradient boosting |
| `backtest.runner` | Runs every model over every fold, collecting metrics |
| `backtest.tracker` | Champion/challenger comparison report (`comparison.json`) |
| `backtest.demo` | End-to-end demonstration on Rossmann store-sales data |

"""Walk-forward backtesting engine for time-series forecasting models.

Modules:
    splitter -- WalkForwardSplitter: expanding/rolling train/test windows
    guard    -- leakage guard: overlap assertions and GuardedTransformer
    metrics  -- horizon-aware MAE/RMSE/MAPE
    models   -- ForecastModel protocol and reference models
    runner   -- backtest orchestration over folds and models
    tracker  -- champion/challenger tracking and reporting
    demo     -- Rossmann demonstration CLI
"""

__version__ = "0.1.0"

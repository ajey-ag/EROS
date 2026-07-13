---
id: TASK-005
title: Implement model protocol, SeasonalNaive, and GradientBoostingModel
status: todo
depends_on:
- TASK-003
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/models.py`: a `ForecastModel` Protocol with `fit(train: pd.DataFrame) -> None`
and `predict(test_index: pd.DatetimeIndex) -> np.ndarray`. Implement `SeasonalNaive(
season_length: int = 7, target_col: str = "y")`: for each test timestamp, predict the last
observed train value from the same position in the seasonal cycle (same weekday for
season_length=7). Implement `build_features(df, target_col) -> pd.DataFrame` producing lag
features (lags 1, 7, 14) and calendar features (day-of-week, month) as a fit/transform-style
object `LagCalendarFeatures` so it can be wrapped by GuardedTransformer. Implement
`GradientBoostingModel(target_col: str = "y")` using sklearn HistGradientBoostingRegressor:
`fit` builds features via a GuardedTransformer(LagCalendarFeatures(...), train_end=train.index.max())
and trains; `predict` forecasts the test index recursively (feeding predictions back as lags)
or via direct features from train history — pick one, document it in a docstring. Tests in
`tests/test_models.py` use synthetic series.

## Acceptance criteria

- SeasonalNaive on a synthetic weekly-periodic series predicts exactly the value from 7 days prior for every test step
- GradientBoostingModel.fit + predict on a synthetic series returns a finite np.ndarray of length equal to the test index
- Test proves calling the model's internal feature builder fit with data past train_end raises LeakageError
- Both classes satisfy the ForecastModel protocol (isinstance check with runtime_checkable, or duck-typed call test)

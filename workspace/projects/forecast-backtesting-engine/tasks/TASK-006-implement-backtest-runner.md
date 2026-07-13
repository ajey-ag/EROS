---
id: TASK-006
title: Implement backtest runner
status: todo
depends_on:
- TASK-002
- TASK-003
- TASK-004
- TASK-005
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/runner.py`: a `BacktestResult` dataclass holding
`results: dict[str, dict]` (per model: `per_fold` list of FoldMetrics DataFrames and
`aggregate` DataFrame) and `metadata: dict` (splitter config, dataset span, target_col).
`run_backtest(df: pd.DataFrame, target_col: str, splitter: WalkForwardSplitter,
models: dict[str, ForecastModel]) -> BacktestResult`: for each fold from
splitter.split(df.index), call assert_no_overlap, slice train/test, fit each model on the
train slice only, predict on the test index, assert len(preds) == len(test window) (raise
ValueError otherwise), compute horizon_metrics, then aggregate_folds per model. Tests in
`tests/test_runner.py` use a stub model recording what data it saw: assert fold count
matches the splitter, assert the stub never received a timestamp past its fold's train_end,
assert result shape, and assert a stub returning wrong-length predictions raises ValueError.

## Acceptance criteria

- run_backtest with a stub model over a synthetic series produces per_fold count equal to the number of splitter folds
- Stub model's recorded fit data never contains timestamps beyond the fold's train_end
- A stub returning predictions of wrong length causes ValueError
- BacktestResult contains an aggregate DataFrame per model with mae/rmse/mape columns

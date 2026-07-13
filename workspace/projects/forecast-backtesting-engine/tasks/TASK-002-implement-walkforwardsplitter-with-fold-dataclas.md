---
id: TASK-002
title: Implement WalkForwardSplitter with Fold dataclass
status: done
depends_on:
- TASK-001
runs:
- RUN-002
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/splitter.py`: a frozen dataclass `Fold(fold_id: int, train_start, train_end,
test_start, test_end)` with pd.Timestamp fields, and
`WalkForwardSplitter(mode: Literal["expanding","rolling"], min_train_size: int,
horizon: int, gap: int = 0, step: int = 1)` exposing
`split(index: pd.DatetimeIndex) -> Iterator[Fold]`. Expanding mode grows the train window
from `min_train_size`; rolling mode keeps train length fixed at `min_train_size`. Each
test window is exactly `horizon` steps, starting `gap` steps after `train_end`. Successive
folds advance by `step` steps. Stop yielding when a full test window no longer fits.
Validate constructor args (raise ValueError on non-positive horizon/min_train_size,
negative gap, unknown mode). Tests in `tests/test_splitter.py` use small synthetic daily
DatetimeIndex ranges with hand-computed expected boundaries.

## Acceptance criteria

- Test asserts exact train/test boundary timestamps for an expanding split over a 20-day index with min_train_size=10, horizon=3, gap=0, step=3
- Test asserts rolling mode keeps train window length constant at min_train_size across all folds
- Test asserts gap=2 leaves exactly 2 index steps between train_end and test_start in every fold
- Test asserts no fold is yielded whose test window would extend past the end of the index
- ValueError raised for horizon=0 and mode='bogus'

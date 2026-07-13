---
id: TASK-003
title: Implement leakage guard
status: todo
depends_on:
- TASK-002
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/guard.py`: `class LeakageError(Exception)`;
`assert_no_overlap(fold: Fold, index: pd.DatetimeIndex) -> None` which raises LeakageError
if any index timestamp within the test window [test_start, test_end] also falls within the
train window [train_start, train_end], or if test_start <= train_end;
and `GuardedTransformer(inner, train_end: pd.Timestamp)` wrapping any object with
fit/transform methods — its `fit(df)` raises LeakageError if `df.index.max() > train_end`,
otherwise delegates to `inner.fit`; `transform(df)` delegates unconditionally.
Tests in `tests/test_guard.py` construct at least two leakage scenarios: (a) a manually
built Fold whose test window overlaps its train window, asserting assert_no_overlap raises;
(b) a GuardedTransformer whose fit is called with a DataFrame spanning the full series past
train_end, asserting LeakageError. Also test the happy paths (valid fold passes; fit on
train-only data delegates to inner).

## Acceptance criteria

- assert_no_overlap raises LeakageError for an overlapping Fold and passes silently for a valid splitter-emitted fold
- GuardedTransformer.fit raises LeakageError when the input's max timestamp exceeds train_end
- GuardedTransformer.fit on train-only data calls inner.fit exactly once (verified with a stub/spy inner)
- pytest green for tests/test_guard.py

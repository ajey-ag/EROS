"""WalkForwardSplitter: expanding or rolling train/test window generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Literal

import pandas as pd


@dataclass(frozen=True)
class Fold:
    """One walk-forward fold as inclusive timestamp boundaries."""

    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


class WalkForwardSplitter:
    """Generate expanding or rolling train/test window pairs over a time index.

    Each fold's train window ends ``gap`` steps before the test window starts;
    the test window is exactly ``horizon`` steps long. Successive folds advance
    the train end by ``step`` steps. Folds whose test window would extend past
    the end of the index are not yielded.
    """

    def __init__(
        self,
        mode: Literal["expanding", "rolling"],
        min_train_size: int,
        horizon: int,
        gap: int = 0,
        step: int = 1,
    ):
        if mode not in ("expanding", "rolling"):
            raise ValueError(f"unknown mode: {mode!r}")
        if min_train_size <= 0:
            raise ValueError(f"min_train_size must be positive, got {min_train_size}")
        if horizon <= 0:
            raise ValueError(f"horizon must be positive, got {horizon}")
        if gap < 0:
            raise ValueError(f"gap must be non-negative, got {gap}")
        if step <= 0:
            raise ValueError(f"step must be positive, got {step}")
        self.mode = mode
        self.min_train_size = min_train_size
        self.horizon = horizon
        self.gap = gap
        self.step = step

    def split(self, index: pd.DatetimeIndex) -> Iterator[Fold]:
        """Yield Folds over ``index``; positions map to inclusive timestamps."""
        if not index.is_monotonic_increasing:
            raise ValueError("index must be sorted in increasing order")
        n = len(index)
        fold_id = 0
        train_end_pos = self.min_train_size - 1  # inclusive position
        while True:
            test_start_pos = train_end_pos + self.gap + 1
            test_end_pos = test_start_pos + self.horizon - 1
            if test_end_pos >= n:
                break
            if self.mode == "expanding":
                train_start_pos = 0
            else:
                train_start_pos = train_end_pos - self.min_train_size + 1
            yield Fold(
                fold_id=fold_id,
                train_start=index[train_start_pos],
                train_end=index[train_end_pos],
                test_start=index[test_start_pos],
                test_end=index[test_end_pos],
            )
            fold_id += 1
            train_end_pos += self.step

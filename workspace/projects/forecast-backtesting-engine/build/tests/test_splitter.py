"""Tests for backtest.splitter on small synthetic daily date ranges."""

import pandas as pd
import pytest

from backtest.splitter import Fold, WalkForwardSplitter


def daily_index(n, start="2024-01-01"):
    return pd.date_range(start, periods=n, freq="D")


def ts(day):
    return pd.Timestamp(f"2024-01-{day:02d}")


class TestExpanding:
    def test_exact_boundaries_20_days(self):
        index = daily_index(20)
        splitter = WalkForwardSplitter(
            mode="expanding", min_train_size=10, horizon=3, gap=0, step=3
        )
        folds = list(splitter.split(index))
        expected = [
            Fold(0, ts(1), ts(10), ts(11), ts(13)),
            Fold(1, ts(1), ts(13), ts(14), ts(16)),
            Fold(2, ts(1), ts(16), ts(17), ts(19)),
        ]
        assert folds == expected

    def test_train_window_grows(self):
        index = daily_index(30)
        splitter = WalkForwardSplitter(
            mode="expanding", min_train_size=5, horizon=2, step=2
        )
        folds = list(splitter.split(index))
        lengths = [(f.train_end - f.train_start).days + 1 for f in folds]
        assert lengths[0] == 5
        assert lengths == sorted(lengths)
        assert lengths[-1] > lengths[0]
        assert all(f.train_start == index[0] for f in folds)


class TestRolling:
    def test_train_length_constant(self):
        index = daily_index(30)
        splitter = WalkForwardSplitter(
            mode="rolling", min_train_size=7, horizon=3, step=4
        )
        folds = list(splitter.split(index))
        assert len(folds) > 1
        for fold in folds:
            assert (fold.train_end - fold.train_start).days + 1 == 7

    def test_rolling_window_slides(self):
        index = daily_index(20)
        splitter = WalkForwardSplitter(
            mode="rolling", min_train_size=10, horizon=3, step=3
        )
        folds = list(splitter.split(index))
        expected = [
            Fold(0, ts(1), ts(10), ts(11), ts(13)),
            Fold(1, ts(4), ts(13), ts(14), ts(16)),
            Fold(2, ts(7), ts(16), ts(17), ts(19)),
        ]
        assert folds == expected


class TestGap:
    def test_gap_leaves_exact_steps(self):
        index = daily_index(30)
        splitter = WalkForwardSplitter(
            mode="expanding", min_train_size=8, horizon=3, gap=2, step=3
        )
        folds = list(splitter.split(index))
        assert len(folds) > 1
        for fold in folds:
            # exactly 2 index steps (days) strictly between train_end and test_start
            assert (fold.test_start - fold.train_end).days == 3

    def test_gap_zero_test_starts_next_step(self):
        index = daily_index(15)
        splitter = WalkForwardSplitter(mode="expanding", min_train_size=10, horizon=2)
        for fold in splitter.split(index):
            assert (fold.test_start - fold.train_end).days == 1


class TestBounds:
    def test_no_fold_extends_past_index_end(self):
        index = daily_index(20)
        splitter = WalkForwardSplitter(
            mode="expanding", min_train_size=10, horizon=4, gap=1, step=2
        )
        folds = list(splitter.split(index))
        assert folds, "expected at least one fold"
        for fold in folds:
            assert fold.test_end <= index[-1]
        # the next fold after the last yielded one would not fit
        last = folds[-1]
        next_test_end = last.test_end + pd.Timedelta(days=splitter.step)
        assert next_test_end > index[-1]

    def test_no_folds_when_index_too_short(self):
        index = daily_index(10)
        splitter = WalkForwardSplitter(mode="expanding", min_train_size=10, horizon=3)
        assert list(splitter.split(index)) == []

    def test_horizon_exactly_fits(self):
        index = daily_index(13)
        splitter = WalkForwardSplitter(mode="expanding", min_train_size=10, horizon=3)
        folds = list(splitter.split(index))
        assert len(folds) == 1
        assert folds[0].test_end == index[-1]


class TestValidation:
    def test_horizon_zero_raises(self):
        with pytest.raises(ValueError):
            WalkForwardSplitter(mode="expanding", min_train_size=10, horizon=0)

    def test_bogus_mode_raises(self):
        with pytest.raises(ValueError):
            WalkForwardSplitter(mode="bogus", min_train_size=10, horizon=3)

    def test_min_train_size_zero_raises(self):
        with pytest.raises(ValueError):
            WalkForwardSplitter(mode="rolling", min_train_size=0, horizon=3)

    def test_negative_gap_raises(self):
        with pytest.raises(ValueError):
            WalkForwardSplitter(mode="expanding", min_train_size=5, horizon=3, gap=-1)

    def test_non_positive_step_raises(self):
        with pytest.raises(ValueError):
            WalkForwardSplitter(mode="expanding", min_train_size=5, horizon=3, step=0)

    def test_unsorted_index_raises(self):
        index = daily_index(20)[::-1]
        splitter = WalkForwardSplitter(mode="expanding", min_train_size=5, horizon=3)
        with pytest.raises(ValueError):
            list(splitter.split(index))

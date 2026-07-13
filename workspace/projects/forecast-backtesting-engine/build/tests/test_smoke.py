"""Smoke test: the package and every submodule import cleanly."""

import importlib

import pytest

SUBMODULES = [
    "splitter",
    "guard",
    "metrics",
    "models",
    "runner",
    "tracker",
    "demo",
]


def test_import_package():
    import backtest

    assert backtest.__version__


@pytest.mark.parametrize("name", SUBMODULES)
def test_import_submodule(name):
    module = importlib.import_module(f"backtest.{name}")
    assert module is not None

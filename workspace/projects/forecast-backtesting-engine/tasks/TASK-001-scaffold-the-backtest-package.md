---
id: TASK-001
title: Scaffold the backtest package
status: done
depends_on: []
runs:
- RUN-001
created: '2026-07-13T17:38:29Z'
---

## Description

Create the project skeleton under workspace/projects/forecast-backtesting-engine (or the
current build directory): a `backtest/` package with empty modules `splitter.py`,
`guard.py`, `metrics.py`, `models.py`, `runner.py`, `tracker.py`, `demo.py`, plus
`backtest/__init__.py`, a `tests/` directory with `__init__.py`, `pyproject.toml`
declaring the package (Python >=3.11, deps: pandas, numpy, scikit-learn; dev dep: pytest),
and a `README.md` stub. Add a trivial smoke test `tests/test_smoke.py` that imports
`backtest` and each submodule.

## Acceptance criteria

- `pip install -e .` (or equivalent) succeeds in a fresh venv
- `pytest` runs and the smoke test passes, importing all seven submodules
- `python -c "import backtest"` exits 0

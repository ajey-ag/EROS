---
id: TASK-001
title: Scaffold ratezoo package with core interface and FakeClock
status: done
depends_on: []
runs:
- RUN-001
created: '2026-07-07T12:26:06Z'
---

## Description

Create the project skeleton:
- `pyproject.toml` (project name `ratezoo`, requires-python >=3.11, no runtime
  dependencies, optional-dependencies group `test` = ["pytest", "hypothesis"]).
- Package layout: `ratezoo/__init__.py`, `ratezoo/core.py`, `tests/__init__.py`.
- In `ratezoo/core.py` define:
  - `class RateLimiter(abc.ABC)` with constructor contract
    `__init__(self, capacity: int, rate: float, *, clock: Callable[[], float] = time.monotonic)`,
    storing `capacity`, `rate`, and `_clock`; expose read-only properties
    `capacity` and `rate`; abstract method `allow(self, n: int = 1) -> bool`.
    Constructor must raise `ValueError` for capacity <= 0 or rate <= 0.
    `allow` contract: return False (never raise) when n > capacity.
  - `class FakeClock` with `__init__(start: float = 0.0)`, `advance(seconds: float) -> None`
    (raises ValueError on negative seconds), and `__call__() -> float` returning current time.
- `ratezoo/__init__.py` re-exports `RateLimiter` and `FakeClock` and defines
  `ALGORITHMS: dict[str, type[RateLimiter]] = {}` (empty for now; each algorithm
  entry maps name -> class).
- `tests/test_core.py` with unit tests for FakeClock (advance accumulates, negative
  advance raises) and for RateLimiter constructor validation via a trivial concrete subclass.

## Acceptance criteria

- `pip install -e .[test]` succeeds on a clean venv
- `python -c "from ratezoo import RateLimiter, FakeClock, ALGORITHMS"` exits 0
- `pytest tests/test_core.py` passes
- `python -c "import ratezoo, sys; mods = {m.split('.')[0] for m in sys.modules}; assert mods <= (set(sys.stdlib_module_names) | {'ratezoo'})"` exits 0 (stdlib-only runtime import)

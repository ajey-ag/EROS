---
id: TASK-008
title: Implement the Rossmann demo CLI and end-to-end run
status: todo
depends_on:
- TASK-006
- TASK-007
runs: []
created: '2026-07-13T17:38:29Z'
---

## Description

In `backtest/demo.py`: `main(argv=None)` with argparse flags `--data-dir` (default
r"C:\Users\dell\Documents\project\rossmann_data"), `--store-id` (default 1), `--horizon`
(default 7), `--output` (default "comparison.json"). Load train.csv (and store.csv)
read-only from data-dir; filter to the chosen store's open days (Open==1), parse Date,
set a continuous DatetimeIndex (reindex + forward-fill or drop, documented), rename Sales
to the target col. Build a WalkForwardSplitter (expanding, sensible min_train_size, the
given horizon, gap=0), run SeasonalNaive vs GradientBoostingModel through run_backtest and
Tracker (primary metric rmse), write comparison.json, print the table. Guard with
`if __name__ == "__main__": main()` so `python -m backtest.demo` works. Add
`tests/test_demo.py` that runs main() against a tiny synthetic CSV pair written to
tmp_path (mimicking Rossmann's columns: Store, Date, Sales, Open) via --data-dir, so
pytest stays green without the real dataset. Verify manually that the real command runs
against the actual Rossmann path and update README.md with usage.

## Acceptance criteria

- `python -m backtest.demo --data-dir <tmp synthetic dir>` exits 0, writes comparison.json, and prints a table naming both models
- tests/test_demo.py passes using only synthetic CSVs in tmp_path (no dependency on the real Rossmann files)
- `python -m backtest.demo` against the real C:\Users\dell\Documents\project\rossmann_data completes and comparison.json contains both models with per-horizon metrics
- The Rossmann directory is opened read-only: no file inside it is created or modified by the run
- `pytest` is green for the entire package

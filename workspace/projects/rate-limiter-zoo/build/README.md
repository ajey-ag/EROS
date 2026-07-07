# ratezoo

Five classic rate-limiting algorithms — token bucket, leaky bucket, fixed
window, sliding window log, sliding window counter — behind one interface,
property-tested against their declared guarantees, and benchmarked.

Zero runtime dependencies (stdlib only). Python 3.11+.

```python
from ratezoo import TokenBucket

limiter = TokenBucket(capacity=100, rate=100.0)  # 100-burst, 100 permits/sec
if limiter.allow():
    handle_request()
```

All algorithms live in the `ALGORITHMS` registry and declare their behavioral
bounds in `GUARANTEES`; the hypothesis property suite in `tests/` checks every
registered algorithm against its own declared guarantee automatically.

- **[WRITEUP.md](WRITEUP.md)** — the comparison writeup: findings, benchmark
  tables, and guidance on choosing an algorithm.
- **[comparison.md](comparison.md)** — machine-generated benchmark tables.

```bash
pip install -e .[test]
pytest
python -m ratezoo.bench --json results.json
python -m ratezoo.bench.report results.json > comparison.md
```

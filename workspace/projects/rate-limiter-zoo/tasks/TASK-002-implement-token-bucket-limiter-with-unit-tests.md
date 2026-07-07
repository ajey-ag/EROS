---
id: TASK-002
title: Implement token bucket limiter with unit tests
status: done
depends_on:
- TASK-001
runs:
- RUN-002
created: '2026-07-07T12:26:06Z'
---

## Description

Create `ratezoo/token_bucket.py` with `class TokenBucket(RateLimiter)`:
- State: `tokens: float` (init to capacity), `last_refill: float` (init to clock()).
- `allow(n=1)`: under a `threading.Lock`, lazily refill
  `tokens = min(capacity, tokens + (now - last_refill) * rate)`, update `last_refill`,
  then grant iff `tokens >= n` (subtract on grant). Return False for n > capacity
  or n <= 0 without mutating state.
- Read-only property `available: float` returning current tokens after a lazy refill.
- Clamp tokens to `[0, capacity]` on every update (float-drift mitigation).
Register it: `ALGORITHMS["token_bucket"] = TokenBucket` in `ratezoo/__init__.py`.
Add `tests/test_units.py` with token-bucket tests using FakeClock:
burst of `capacity` calls all allowed then next denied; after advancing
`capacity / rate` seconds with no requests, `available == capacity`;
partial refill grants proportionally (advance 1s at rate=2 grants 2 more permits);
`allow(capacity + 1)` returns False and does not change `available`.

## Acceptance criteria

- `pytest tests/test_units.py` passes
- `python -c "from ratezoo import ALGORITHMS; assert 'token_bucket' in ALGORITHMS"` exits 0

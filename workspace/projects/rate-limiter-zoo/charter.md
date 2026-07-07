# Rate Limiter Zoo

**Promoted from:** IDEA-082 · **Domain:** Distributed Systems & Performance · **Score:** 16/25

## Pitch

Every classic rate-limiting algorithm implemented against one interface, property-tested, and load-tested — the definitive comparison writeup.

## Goals

- One `RateLimiter` interface; implementations: token bucket, leaky bucket, fixed window, sliding window log, sliding window counter.
- Property-based tests (hypothesis) proving each limiter's invariants (never exceeds capacity, refill correctness).
- A benchmark harness comparing throughput and burst behavior, emitting results as JSON.

## Success criteria

- `pytest` green including property tests for all five algorithms.
- `python -m ratezoo.bench` produces a comparison table across algorithms.
- Zero third-party runtime dependencies (stdlib only); test deps: pytest, hypothesis.

## Constraints

- Python-first; runs on a single Windows laptop without cloud infrastructure.
- Keep external dependencies minimal and justified.

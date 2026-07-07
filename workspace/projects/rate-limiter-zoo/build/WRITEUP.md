# Rate Limiter Zoo: five classic algorithms, one interface, measured honestly

Every backpressure conversation eventually reaches "just put a rate limiter on
it" — and then quietly assumes all rate limiters behave the same. They don't.
This project implements the five classic algorithms behind a single Python
interface, proves each one's *actual* guarantee with property-based tests, and
benchmarks their throughput and burst behavior. Every number in this document
is regenerable from two commands (see [Reproducing](#reproducing)); the tables
are emitted by the benchmark harness, not hand-collected.

The design decision everything else hangs on: **time is injectable**. Every
limiter takes `clock: Callable[[], float]` defaulting to `time.monotonic`.
Property tests drive a `FakeClock` through thousands of arbitrary schedules,
and burst benchmarks replay identical, fully deterministic traffic against
every algorithm — the spike traces are byte-identical across runs.

## The zoo

All five implement `allow(n: int = 1) -> bool` with `capacity` (max burst) and
`rate` (sustained permits/second), lock-guarded, stdlib only. `W = capacity/rate`
is the natural window length.

| Algorithm | Mechanics | Memory | Extra burst admitted | Full reset after idle |
| --- | --- | --- | --- | --- |
| `token_bucket` | tokens refill continuously, spend on grant | O(1) | none | 1×W |
| `leaky_bucket` | fill level drains continuously, admit under capacity | O(1) | none | 1×W |
| `fixed_window` | counter resets on grid-aligned boundaries | O(1) | up to 1× capacity at boundaries | 1×W |
| `sliding_log` | deque of grant timestamps, pruned on access | O(capacity) | none (exact) | 1×W |
| `sliding_counter` | interpolates previous + current window counts | O(1) | approximation error, bounded | 2×W |

These guarantees are not documentation claims — they are machine-checked. Each
algorithm declares its bound in a `GUARANTEES` registry, and a hypothesis
property suite asserts that grants in any sliding window of length `W` never
exceed `capacity * max_burst_factor + rate * W` across arbitrary schedules
(plus a 2000-operation float-drift regression). Lowering any declared factor
makes the suite fail, which is how we know the tests have teeth.

## Finding 1: the fixed-window boundary burst is real and exactly 2×

The textbook flaw, demonstrated by a test rather than asserted: with
capacity 10 and a 1-second window, 10 requests at t=0.9 **and** 10 more at
t=1.1 all succeed — 20 permits inside 0.2 seconds. The sliding log, given the
identical schedule, denies the second burst outright. If a downstream service
sizes itself on "100 req/s means 100 req/s", a fixed-window limiter will hand
it 200 in a bad moment.

## Finding 2: the sliding counter's estimate misses concentrated traffic

The sliding counter assumes requests in the previous window were uniformly
spread. Concentrate them instead and the interpolation under-counts: after 10
grants at t=0.99 (capacity 10, W=1s), at t=1.1 the true trailing-window count
is still 10 — the exact log denies — but the estimate is `10 × 0.9 = 9`, so
the counter admits one more. The flip side of the same approximation is
conservatism elsewhere: it needs **two** idle windows before a full burst is
admissible again (the previous-window count keeps weighing on the estimate),
where every other algorithm needs one.

## Finding 3: burst workloads separate the families, steady traffic barely does

Deterministic FakeClock workloads, capacity 100, rate 100/s:

| Workload | token_bucket | leaky_bucket | fixed_window | sliding_log | sliding_counter |
| --- | --- | --- | --- | --- | --- |
| steady (1 req every 1/rate s, 300 reqs) | 300 | 300 | 299 | 299 | 297 |
| ramp (accelerating, 300 reqs) | **300** | **300** | 228 | 226 | 226 |
| spike (2× capacity at one instant) | 100 | 100 | 100 | 100 | 100 |

- **Steady at exactly `rate`**: the bucket algorithms grant everything; the
  windowed ones drop a request or three at boundary crossings. Real clients
  running at precisely the advertised rate will see occasional 429s from
  windowed limiters — worth knowing before writing an SLA.
- **Ramp** is the discriminator: continuous-refill algorithms absorb an
  accelerating client indefinitely at `rate` (300/300), while all three
  windowed algorithms hold it to ~226–228. Same nominal configuration, ~25%
  difference in admitted traffic.
- **Spike at a single instant** is a deliberate negative result: every
  algorithm admits exactly `capacity`. A one-instant spike cannot expose the
  fixed-window flaw — the burst must *straddle a boundary* (Finding 1). If
  your load test only fires simultaneous spikes, all five limiters look
  identical and you'll pick one for the wrong reason.

## Finding 4: throughput — the flawed one is the fastest

Median of 5 × 1-second tight loops of `allow(1)`, CPython 3.14 on a Windows
laptop (contended = 4 threads sharing one limiter):

| algorithm | ops/sec (1 thread) | ops/sec (4 threads) |
| --- | --- | --- |
| fixed_window | 1,859,518 | 1,620,358 |
| sliding_log | 1,114,653 | 1,047,439 |
| token_bucket | 675,588 | 822,907 |
| leaky_bucket | 635,941 | 739,500 |
| sliding_counter | 545,734 | 630,129 |

The ordering follows arithmetic per call: fixed window does one comparison and
an int increment on the hot path (~1.9M ops/s); the sliding log's deque prune
is cheap when almost nothing expires; the float-arithmetic algorithms (both
buckets, the counter) sit around 550–830K. Every algorithm still clears half a
million decisions per second in pure Python under a per-instance lock —
in-process rate limiting is unlikely to be your bottleneck. Treat the absolute
numbers as laptop-grade; the *ordering* and the ~3× spread are the durable
result.

## Choosing

- **Default: `token_bucket`.** Exact guarantee, O(1), allows the burst you
  configured and nothing more.
- **Traffic-shaping semantics (drain, not spend): `leaky_bucket`** — same
  guarantee, inverted bookkeeping.
- **Need exactness with auditability: `sliding_log`** — pays O(capacity)
  memory for a complete recent-grant record.
- **Distributed counters / hot path at all costs: `fixed_window`** — fastest
  and simplest to shard, *if* downstream tolerates 2× boundary bursts.
- **`sliding_counter`** buys fixed-window's O(1) memory with much softer
  boundary behavior — the right trade when an approximate bound is
  acceptable — but budget for its over-admission and slow reset.

## Reproducing

```bash
pip install -e .[test]
pytest                                             # 63 tests: units, properties, threading
python -m ratezoo.bench --json results.json        # throughput (1 thread) + burst traces
python -m ratezoo.bench --threads 4 --json results-threads4.json
python -m ratezoo.bench.report results.json results-threads4.json > comparison.md
```

Burst tables and traces are deterministic (FakeClock); throughput numbers will
reflect your machine.

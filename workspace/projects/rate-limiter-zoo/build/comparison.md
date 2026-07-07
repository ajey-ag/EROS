# ratezoo benchmark comparison

## Throughput

| algorithm | ops/sec (1 thread) | ops/sec (4 threads) |
| --- | --- | --- |
| fixed_window | 1,859,518 | 1,620,358 |
| leaky_bucket | 635,941 | 739,500 |
| sliding_counter | 545,734 | 630,129 |
| sliding_log | 1,114,653 | 1,047,439 |
| token_bucket | 675,588 | 822,907 |

## Burst workload: ramp

| algorithm | allowed | denied | sim duration (s) |
| --- | --- | --- | --- |
| fixed_window | 228 | 72 | 3.00 |
| leaky_bucket | 300 | 0 | 3.00 |
| sliding_counter | 226 | 74 | 3.00 |
| sliding_log | 226 | 74 | 3.00 |
| token_bucket | 300 | 0 | 3.00 |

## Burst workload: spike

| algorithm | allowed | denied | sim duration (s) |
| --- | --- | --- | --- |
| fixed_window | 100 | 100 | 2.00 |
| leaky_bucket | 100 | 100 | 2.00 |
| sliding_counter | 100 | 100 | 2.00 |
| sliding_log | 100 | 100 | 2.00 |
| token_bucket | 100 | 100 | 2.00 |

## Burst workload: steady

| algorithm | allowed | denied | sim duration (s) |
| --- | --- | --- | --- |
| fixed_window | 299 | 1 | 3.00 |
| leaky_bucket | 300 | 0 | 3.00 |
| sliding_counter | 297 | 3 | 3.00 |
| sliding_log | 299 | 1 | 3.00 |
| token_bucket | 300 | 0 | 3.00 |

## Spike behavior

- **fixed_window**: granted 100 of the 200 spike requests (capacity 100) after two idle windows (50% admitted).
- **leaky_bucket**: granted 100 of the 200 spike requests (capacity 100) after two idle windows (50% admitted).
- **sliding_counter**: granted 100 of the 200 spike requests (capacity 100) after two idle windows (50% admitted).
- **sliding_log**: granted 100 of the 200 spike requests (capacity 100) after two idle windows (50% admitted).
- **token_bucket**: granted 100 of the 200 spike requests (capacity 100) after two idle windows (50% admitted).

Algorithms that track burst state exactly admit precisely `capacity` here; deviations expose the fixed-window boundary burst and the sliding-counter interpolation approximation.

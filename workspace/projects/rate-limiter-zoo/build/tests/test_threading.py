"""Concurrency safety: hammer each algorithm from 8 threads with a real clock."""

from __future__ import annotations

import threading
import time

import pytest

from ratezoo import ALGORITHMS, GUARANTEES

THREADS = 8
CALLS_PER_THREAD = 5000
CAPACITY = 100
RATE = 100.0


@pytest.mark.parametrize("name,cls", sorted(ALGORITHMS.items()))
def test_thread_safety(name, cls):
    limiter = cls(CAPACITY, RATE)  # real time.monotonic clock
    granted_per_thread = [0] * THREADS
    errors: list[BaseException] = []
    start_barrier = threading.Barrier(THREADS)

    def worker(tid: int) -> None:
        try:
            start_barrier.wait()
            granted = 0
            for _ in range(CALLS_PER_THREAD):
                if limiter.allow(1):
                    granted += 1
            granted_per_thread[tid] = granted
        except BaseException as exc:  # noqa: BLE001 - anything escaping is a failure
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.perf_counter() - t0

    assert not errors, f"exceptions escaped worker threads: {errors!r}"

    total_granted = sum(granted_per_thread)
    slack = CAPACITY  # absorbs timing jitter between barrier release and t0
    bound = (
        CAPACITY * GUARANTEES[name]["max_burst_factor"] + RATE * duration + slack
    )
    assert total_granted <= bound, (
        f"{name}: granted {total_granted} > bound {bound:.1f} "
        f"(duration {duration:.3f}s)"
    )

    # Internal state must land back inside [0, capacity].
    for prop in ("available", "current_count", "log_size"):
        if hasattr(limiter, prop):
            value = getattr(limiter, prop)
            assert 0 <= value <= CAPACITY, f"{name}.{prop} = {value!r}"

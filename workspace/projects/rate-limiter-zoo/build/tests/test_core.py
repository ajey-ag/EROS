import pytest

from ratezoo import ALGORITHMS, FakeClock, RateLimiter


class AllowAll(RateLimiter):
    """Trivial concrete subclass for exercising the base-class contract."""

    def allow(self, n: int = 1) -> bool:
        return n <= self.capacity


class TestFakeClock:
    def test_starts_at_zero_by_default(self):
        clock = FakeClock()
        assert clock() == 0.0

    def test_custom_start(self):
        clock = FakeClock(start=42.5)
        assert clock() == 42.5

    def test_advance_accumulates(self):
        clock = FakeClock()
        clock.advance(1.5)
        clock.advance(2.5)
        assert clock() == 4.0

    def test_advance_zero_is_allowed(self):
        clock = FakeClock(start=1.0)
        clock.advance(0.0)
        assert clock() == 1.0

    def test_negative_advance_raises(self):
        clock = FakeClock()
        with pytest.raises(ValueError):
            clock.advance(-0.1)


class TestRateLimiterConstructor:
    def test_valid_construction(self):
        limiter = AllowAll(capacity=10, rate=5.0)
        assert limiter.capacity == 10
        assert limiter.rate == 5.0

    @pytest.mark.parametrize("capacity", [0, -1])
    def test_nonpositive_capacity_raises(self, capacity):
        with pytest.raises(ValueError):
            AllowAll(capacity=capacity, rate=1.0)

    @pytest.mark.parametrize("rate", [0.0, -1.0])
    def test_nonpositive_rate_raises(self, rate):
        with pytest.raises(ValueError):
            AllowAll(capacity=1, rate=rate)

    def test_clock_is_injectable(self):
        clock = FakeClock(start=7.0)
        limiter = AllowAll(capacity=1, rate=1.0, clock=clock)
        assert limiter._clock() == 7.0

    def test_cannot_instantiate_abstract_base(self):
        with pytest.raises(TypeError):
            RateLimiter(capacity=1, rate=1.0)

    def test_allow_rejects_n_over_capacity(self):
        limiter = AllowAll(capacity=3, rate=1.0)
        assert limiter.allow(3) is True
        assert limiter.allow(4) is False


def test_registry_exists_and_is_dict():
    assert isinstance(ALGORITHMS, dict)

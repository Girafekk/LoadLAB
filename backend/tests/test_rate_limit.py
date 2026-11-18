from concurrent.futures import ThreadPoolExecutor

from app.core.rate_limit import FailureRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_reserve_allows_exactly_max_attempts_and_unblocks_after_window():
    clock = FakeClock()
    limiter = FailureRateLimiter(max_failures=5, window_seconds=900, clock=clock)

    assert [limiter.reserve_attempt("key") for _ in range(5)] == [0, 0, 0, 0, 0]

    blocked = limiter.reserve_attempt("key")
    assert 0 < blocked <= 901

    clock.now += 899
    assert limiter.reserve_attempt("key") > 0

    clock.now += 1
    assert limiter.reserve_attempt("key") == 0


def test_reserve_is_atomic_under_concurrent_calls():
    # Проверка и учёт попытки идут под одним замком: из 40 одновременных
    # запросов пройти должны ровно 5, а не больше.
    limiter = FailureRateLimiter(max_failures=5, window_seconds=900, clock=FakeClock())

    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda _: limiter.reserve_attempt("key"), range(40)))

    assert sum(1 for value in results if value == 0) == 5
    assert sum(1 for value in results if value > 0) == 35


def test_keys_are_independent_and_reset_clears_one_key():
    limiter = FailureRateLimiter(max_failures=1, window_seconds=900, clock=FakeClock())
    assert limiter.reserve_attempt("a") == 0
    assert limiter.reserve_attempt("b") == 0

    limiter.reset("a")

    assert limiter.retry_after("a") == 0
    assert limiter.reserve_attempt("a") == 0
    assert limiter.retry_after("b") > 0


def test_state_is_bounded_and_evicts_the_oldest_key():
    # Число ключей ограничено: память не растёт от потока разных адресов,
    # а вытеснение не перебирает весь словарь.
    limiter = FailureRateLimiter(max_failures=5, window_seconds=900, clock=FakeClock(), max_keys=3)

    for key in ["a", "b", "c"]:
        assert limiter.reserve_attempt(key) == 0
    # Обращение к «a» делает его свежим, поэтому далее вытесняется «b».
    assert limiter.reserve_attempt("a") == 0
    assert limiter.reserve_attempt("d") == 0

    assert len(limiter._failures) == 3
    assert "b" not in limiter._failures
    assert {"a", "c", "d"} == set(limiter._failures)

"""Защита от перебора паролей.

Счётчик неудачных попыток живёт в памяти процесса. Это простое решение для одного
процесса backend: при нескольких процессах (воркерах) у каждого будет свой счётчик,
а при перезапуске счётчики обнуляются. Для такой конфигурации понадобится общее
хранилище, например Redis.
"""

import time
from collections import OrderedDict, deque
from collections.abc import Callable
from threading import Lock

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60

# Предел числа ключей. Память ограничена, а вытеснение самого старого ключа —
# одна операция: перебирать весь словарь под замком не нужно.
MAX_KEYS = 10_000


class FailureRateLimiter:
    """Блокирует ключ после `max_failures` неудач за `window_seconds` секунд."""

    def __init__(
        self,
        max_failures: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_KEYS,
    ) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._clock = clock
        self._max_keys = max_keys
        # OrderedDict хранит ключи в порядке последнего обращения: при переполнении
        # вытесняется самый давний, а не случайный.
        self._failures: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def _drop_expired(self, key: str, now: float) -> deque[float] | None:
        attempts = self._failures.get(key)
        if attempts is None:
            return None
        while attempts and now - attempts[0] >= self._window_seconds:
            attempts.popleft()
        if not attempts:
            del self._failures[key]
            return None
        return attempts

    def _retry_after_locked(self, key: str, now: float) -> int:
        """Сколько секунд ключ ещё заблокирован. Вызывается под замком."""
        attempts = self._drop_expired(key, now)
        if attempts is None or len(attempts) < self._max_failures:
            return 0
        return max(1, int(self._window_seconds - (now - attempts[0])) + 1)

    def retry_after(self, key: str) -> int:
        """Сколько секунд ключ ещё заблокирован. 0 — не заблокирован."""
        with self._lock:
            return self._retry_after_locked(key, self._clock())

    def reserve_attempt(self, key: str) -> int:
        """Проверяет лимит и занимает попытку одной операцией.

        Возвращает 0, если попытка разрешена и уже учтена, иначе — сколько
        секунд осталось до разблокировки. Проверка и учёт идут под одним замком,
        поэтому параллельные запросы не могут пройти проверку до того, как
        учтена предыдущая попытка: за окно проходят ровно `max_failures` попыток.
        """
        with self._lock:
            now = self._clock()
            retry_after = self._retry_after_locked(key, now)
            if retry_after:
                return retry_after

            attempts = self._failures.get(key)
            if attempts is None:
                attempts = deque()
                self._failures[key] = attempts
            else:
                self._failures.move_to_end(key)
            attempts.append(now)

            # Вытесняем самые давние ключи, не перебирая словарь целиком.
            while len(self._failures) > self._max_keys:
                self._failures.popitem(last=False)
            return 0

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = FailureRateLimiter(LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS)

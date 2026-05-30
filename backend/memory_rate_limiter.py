import threading
import time
from collections import defaultdict
from typing import Tuple


class InMemorySlidingWindowRateLimiter:
    """Sliding window log rate limiter backed by in-process storage."""

    def __init__(self):
        self._events: dict[str, list[int]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_and_consume(
        self,
        key: str,
        window_seconds: int,
        limit: int,
        max_retries: int = 5,
    ) -> Tuple[bool, int]:
        del max_retries  # single-process lock makes retries unnecessary

        with self._lock:
            now_ms = int(time.time() * 1000)
            window_start_ms = now_ms - window_seconds * 1000
            events = [ts for ts in self._events[key] if ts > window_start_ms]

            if len(events) >= limit:
                self._events[key] = events
                return False, len(events)

            events.append(now_ms)
            self._events[key] = events
            return True, len(events)

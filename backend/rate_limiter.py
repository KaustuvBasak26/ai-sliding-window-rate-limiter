import time
from typing import Tuple

import redis


class SlidingWindowRateLimiterTx:
    """
    Sliding window log rate limiter using Redis WATCH/MULTI/EXEC
    for atomicity (no Lua needed).
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    def check_and_consume(
        self,
        key: str,
        window_seconds: int,
        limit: int,
        max_retries: int = 5,
    ) -> Tuple[bool, int]:
        """
        Returns (allowed, current_count_after_operation).

        If high contention prevents a commit after `max_retries`,
        returns (False, -1) as a conservative fallback.
        """

        for _ in range(max_retries):
            now_ms = int(time.time() * 1000)
            window_start_ms = now_ms - window_seconds * 1000
            ttl_seconds = window_seconds * 2

            with self.redis.pipeline() as pipe:
                try:
                    # Watch the key for concurrent modifications
                    pipe.watch(key)

                    # These commands run immediately (not queued yet, we haven't called multi())
                    pipe.zremrangebyscore(key, 0, window_start_ms)
                    current = pipe.zcard(key)
                    current = int(current)

                    # If already at or above limit → reject without modifying
                    if current >= limit:
                        pipe.unwatch()
                        return False, current

                    # Now start transactional block for the write
                    pipe.multi()
                    pipe.zadd(key, {now_ms: now_ms})
                    pipe.expire(key, ttl_seconds)

                    # EXEC – if key changed since WATCH, this raises WatchError or returns None
                    pipe.execute()

                    # Commit succeeded
                    return True, current + 1

                except redis.WatchError:
                    # Key changed between WATCH and EXEC, retry
                    continue

        # Could not commit after max_retries → fail conservative
        return False, -1

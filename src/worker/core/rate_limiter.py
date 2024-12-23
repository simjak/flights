import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    rate: float  # tokens per second
    capacity: int
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens from the bucket."""
        now = time.monotonic()
        time_passed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + time_passed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """Rate limiter using token bucket algorithm."""

    def __init__(
        self,
        rate_limit: int,
        time_window: int,
        burst_limit: Optional[int] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            rate_limit: Number of requests allowed per time window
            time_window: Time window in seconds
            burst_limit: Maximum burst size (defaults to rate_limit)
        """
        self.rate = rate_limit / time_window
        self.capacity = burst_limit or rate_limit
        self.buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = "default", tokens: int = 1) -> None:
        """
        Acquire permission to proceed. Blocks until token is available.

        Args:
            key: Bucket key for separate rate limits
            tokens: Number of tokens to acquire
        """
        while True:
            async with self._lock:
                bucket = self.buckets.get(key)
                if not bucket:
                    bucket = TokenBucket(rate=self.rate, capacity=self.capacity)
                    self.buckets[key] = bucket

                if bucket.try_acquire(tokens):
                    logger.debug(
                        f"Acquired {tokens} token(s) from bucket {key}. "
                        f"Remaining: {bucket.tokens:.2f}"
                    )
                    return

            # Wait before trying again
            await asyncio.sleep(1.0 / self.rate)

    async def try_acquire(self, key: str = "default", tokens: int = 1) -> bool:
        """
        Try to acquire permission to proceed without blocking.

        Args:
            key: Bucket key for separate rate limits
            tokens: Number of tokens to acquire

        Returns:
            True if tokens were acquired, False otherwise
        """
        async with self._lock:
            bucket = self.buckets.get(key)
            if not bucket:
                bucket = TokenBucket(rate=self.rate, capacity=self.capacity)
                self.buckets[key] = bucket

            success = bucket.try_acquire(tokens)
            if success:
                logger.debug(
                    f"Acquired {tokens} token(s) from bucket {key}. "
                    f"Remaining: {bucket.tokens:.2f}"
                )
            return success

    def get_bucket_status(self, key: str = "default") -> Optional[dict]:
        """Get current status of a rate limit bucket."""
        bucket = self.buckets.get(key)
        if not bucket:
            return None

        return {
            "tokens": bucket.tokens,
            "capacity": bucket.capacity,
            "rate": bucket.rate,
            "last_update": bucket.last_update,
        }

"""Async token bucket rate limiter shared across tool invocations."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass(slots=True)
class TokenBucket:
    """Simple async token bucket.

    `capacity` is the burst size. `refill_per_second` is the sustained rate.
    `acquire(n)` blocks until `n` tokens are available.
    """

    capacity: int
    refill_per_second: float
    _tokens: float = 0.0
    _last_refill: float = 0.0
    _lock: asyncio.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        if self.refill_per_second <= 0:
            raise ValueError("refill_per_second must be positive")
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        if elapsed <= 0:
            return
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
        self._last_refill = now

    async def acquire(self, tokens: int = 1) -> None:
        if tokens <= 0:
            return
        if tokens > self.capacity:
            raise ValueError(f"requested {tokens} tokens exceeds capacity {self.capacity}")

        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait_seconds = deficit / self.refill_per_second
            await asyncio.sleep(wait_seconds)

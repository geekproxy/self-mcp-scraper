"""Token bucket behaviour under burst and steady-state load."""
from __future__ import annotations

import asyncio
import time

import pytest

from self_mcp_scraper.rate_limit import TokenBucket


@pytest.mark.asyncio
async def test_burst_within_capacity_is_immediate() -> None:
    bucket = TokenBucket(capacity=5, refill_per_second=1.0)
    start = time.monotonic()
    for _ in range(5):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1, f"5 immediate acquires should be near-instant, took {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_exceeding_capacity_blocks_for_refill() -> None:
    bucket = TokenBucket(capacity=2, refill_per_second=4.0)
    for _ in range(2):
        await bucket.acquire()

    start = time.monotonic()
    await bucket.acquire()
    elapsed = time.monotonic() - start
    assert 0.15 <= elapsed <= 0.5, f"should wait ~0.25s for one refill, waited {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_acquire_rejects_exceeding_capacity() -> None:
    bucket = TokenBucket(capacity=3, refill_per_second=1.0)
    with pytest.raises(ValueError):
        await bucket.acquire(tokens=4)


@pytest.mark.asyncio
async def test_concurrent_acquires_serialized() -> None:
    bucket = TokenBucket(capacity=1, refill_per_second=10.0)
    await bucket.acquire()

    async def one() -> None:
        await bucket.acquire()

    start = time.monotonic()
    await asyncio.gather(one(), one(), one())
    elapsed = time.monotonic() - start
    assert 0.2 <= elapsed <= 1.0

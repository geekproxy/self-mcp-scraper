"""Benchmark: N requests through the configured proxy across multiple targets.

Usage:
    PROXY_HOST=... PROXY_PORT=... PROXY_USER=... PROXY_PASS=... \
        python examples/bench.py
"""
from __future__ import annotations

import asyncio
import statistics
import time

from self_mcp_scraper import config as config_module
from self_mcp_scraper.rate_limit import TokenBucket
from self_mcp_scraper.tools import FetchURLArgs, fetch_url

TARGETS = [
    "https://example.com",
    "https://httpbin.org/status/200",
    "https://api.ipify.org?format=json",
    "https://www.google.com",
    "https://www.wikipedia.org",
    "https://www.reddit.com/",
    "https://duckduckgo.com/",
    "https://www.bing.com/",
]

REQUESTS_PER_TARGET = 3


async def run() -> None:
    cfg = config_module.load()
    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)

    results: dict[str, list[float]] = {url: [] for url in TARGETS}
    successes: dict[str, int] = {url: 0 for url in TARGETS}

    total_start = time.monotonic()
    for url in TARGETS:
        for _ in range(REQUESTS_PER_TARGET):
            start = time.monotonic()
            result = await fetch_url(cfg, bucket, FetchURLArgs(url=url))
            elapsed = time.monotonic() - start
            results[url].append(elapsed)
            if "error" not in result and result.get("status", 0) < 400:
                successes[url] += 1
    total_elapsed = time.monotonic() - total_start

    print(f"\n{'Target':<45} {'Success':<10} {'Avg (s)':<10} {'p95 (s)':<10}")
    print("-" * 75)
    total_success = 0
    total_requests = 0
    for url in TARGETS:
        times = results[url]
        succ = successes[url]
        total_success += succ
        total_requests += REQUESTS_PER_TARGET
        avg = statistics.mean(times) if times else 0.0
        p95 = sorted(times)[int(len(times) * 0.95) - 1] if len(times) > 1 else avg
        print(f"{url:<45} {succ}/{REQUESTS_PER_TARGET:<8} {avg:<10.2f} {p95:<10.2f}")

    print("-" * 75)
    rate = total_success / total_requests * 100
    print(f"Overall: {total_success}/{total_requests} ({rate:.1f}%) in {total_elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(run())

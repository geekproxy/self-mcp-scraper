"""Run the tools directly from Python without an MCP client.

Useful for verifying your proxy setup works before wiring up Claude Desktop
or another client.

Usage:
    PROXY_HOST=... PROXY_PORT=... python examples/standalone_probe.py
"""
from __future__ import annotations

import asyncio
import json

from self_mcp_scraper import config as config_module
from self_mcp_scraper.rate_limit import TokenBucket
from self_mcp_scraper.tools import (
    CheckProxyArgs,
    FetchURLArgs,
    ScrapePageArgs,
    check_proxy,
    fetch_url,
    scrape_page,
)


async def main() -> None:
    cfg = config_module.load()
    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)

    print("=== check_proxy ===")
    print(json.dumps(await check_proxy(cfg, bucket, CheckProxyArgs()), indent=2))

    print("\n=== fetch_url https://example.com ===")
    fetched = await fetch_url(cfg, bucket, FetchURLArgs(url="https://example.com"))
    preview = {
        "status": fetched.get("status"),
        "bytes": fetched.get("bytes"),
        "body_preview": (fetched.get("body") or "")[:200],
    }
    print(json.dumps(preview, indent=2))

    print("\n=== scrape_page https://example.com ===")
    scraped = await scrape_page(
        cfg,
        bucket,
        ScrapePageArgs(url="https://example.com", selectors={"headings": "h1, h2"}),
    )
    print(json.dumps(scraped, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

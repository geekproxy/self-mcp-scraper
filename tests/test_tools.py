"""Tool behaviour: SSRF guard, HTTP fetch, HTML extraction."""
from __future__ import annotations

import pytest

from self_mcp_scraper import tools
from self_mcp_scraper.config import Config, ProxyConfig
from self_mcp_scraper.rate_limit import TokenBucket
from self_mcp_scraper.tools import FetchURLArgs, ScrapePageArgs


def _mk_config(proxy_host: str = "") -> Config:
    return Config(
        proxy=ProxyConfig("http", proxy_host, 8080, None, None),
        default_timeout_seconds=10.0,
        rate_limit_capacity=100,
        rate_limit_refill_per_second=100.0,
        default_fingerprint_country=None,
        max_response_bytes=1024 * 1024,
        user_agent_override=None,
        log_level="WARNING",
        log_json=False,
    )


@pytest.mark.asyncio
async def test_fetch_url_blocks_loopback() -> None:
    cfg = _mk_config()
    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)
    args = FetchURLArgs(url="http://127.0.0.1/secret")
    result = await tools.fetch_url(cfg, bucket, args)
    assert result["error"] == "blocked"


@pytest.mark.asyncio
async def test_fetch_url_blocks_link_local() -> None:
    cfg = _mk_config()
    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)
    args = FetchURLArgs(url="http://169.254.169.254/latest/meta-data/")
    result = await tools.fetch_url(cfg, bucket, args)
    assert result["error"] == "blocked"


@pytest.mark.asyncio
async def test_fetch_url_rejects_non_http_scheme() -> None:
    with pytest.raises(ValueError):
        FetchURLArgs(url="file:///etc/passwd")


@pytest.mark.asyncio
async def test_fetch_url_rejects_unknown_method() -> None:
    with pytest.raises(ValueError):
        FetchURLArgs(url="https://example.com", method="CONNECT")


@pytest.mark.asyncio
async def test_scrape_page_empty_selectors_on_missing_target() -> None:
    cfg = _mk_config()
    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)
    args = ScrapePageArgs(url="http://127.0.0.1")
    result = await tools.scrape_page(cfg, bucket, args)
    assert result["error"] == "blocked"

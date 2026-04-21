"""HTTP client factory with proxy support for both HTTP(S) and SOCKS5."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx

from .config import ProxyConfig


def build_client(
    proxy: ProxyConfig,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Construct an httpx.AsyncClient routed through the configured proxy.

    httpx itself supports HTTP/HTTPS/SOCKS5 transports through the `proxy`
    argument when the `socksio` extra is present. We install `httpx-socks`
    so SOCKS5 works transparently. For HTTP proxies no extra setup is needed.
    """

    timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

    proxy_url = proxy.as_url()
    client_kwargs: dict[str, object] = {
        "timeout": timeout,
        "limits": limits,
        "follow_redirects": follow_redirects,
        "headers": headers or {},
    }
    if proxy_url:
        client_kwargs["proxy"] = proxy_url

    return httpx.AsyncClient(**client_kwargs)


@asynccontextmanager
async def client_context(
    proxy: ProxyConfig,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = True,
) -> AsyncIterator[httpx.AsyncClient]:
    client = build_client(proxy, timeout_seconds, headers, follow_redirects)
    try:
        yield client
    finally:
        await client.aclose()

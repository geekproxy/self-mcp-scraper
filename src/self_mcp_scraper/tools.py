"""Tool implementations exposed through MCP.

Each tool is an async function that takes a validated arguments model and
returns a JSON-serialisable dict. The MCP server layer wraps these dicts
into the protocol's TextContent payloads.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, field_validator

from . import fingerprint
from .config import Config
from .proxy import client_context
from .rate_limit import TokenBucket


class FetchURLArgs(BaseModel):
    url: str = Field(description="Absolute http(s) URL to fetch")
    method: str = Field(default="GET", description="HTTP method")
    headers: dict[str, str] | None = Field(default=None, description="Extra request headers")
    body: str | None = Field(default=None, description="Raw request body (string)")
    timeout_seconds: float | None = Field(default=None, description="Override default timeout")
    country: str | None = Field(
        default=None,
        description="ISO country code to apply matching fingerprint headers (e.g., US, DE).",
    )

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("url must use http or https scheme")
        if not parsed.hostname:
            raise ValueError("url must include a hostname")
        return v

    @field_validator("method")
    @classmethod
    def _validate_method(cls, v: str) -> str:
        method = v.upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
            raise ValueError(f"unsupported method: {v}")
        return method


class ScrapePageArgs(BaseModel):
    url: str
    selectors: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of field name to CSS selector. The value at each selector is "
            "returned as text. If empty, returns the whole page as text and title."
        ),
    )
    country: str | None = None
    timeout_seconds: float | None = None

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("url must use http or https scheme")
        return v


class ListFingerprintsArgs(BaseModel):
    pass


class CheckProxyArgs(BaseModel):
    timeout_seconds: float | None = None


def _host_is_safe(url: str) -> bool:
    """Reject URLs pointing at private, loopback, or link-local hosts.

    This is a basic SSRF guard. The MCP server is a generic tool exposed to
    an LLM; without this, a prompt injection could ask it to fetch
    http://169.254.169.254/ or internal services.
    """
    hostname = urlparse(url).hostname
    if not hostname:
        return False
    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False
    for entry in resolved:
        addr = entry[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved:
            return False
    return True


def _merge_headers(config: Config, country: str | None, extra: dict[str, str] | None) -> dict[str, str]:
    target_country = country or config.default_fingerprint_country
    fp = fingerprint.get(target_country)
    headers: dict[str, str] = {}
    if fp:
        headers.update(fingerprint.to_headers(fp, config.user_agent_override))
    elif config.user_agent_override:
        headers["User-Agent"] = config.user_agent_override
    if extra:
        headers.update(extra)
    return headers


def _truncate_body(body: bytes, limit: int) -> tuple[str, bool]:
    truncated = len(body) > limit
    if truncated:
        body = body[:limit]
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        text = repr(body)
    return text, truncated


async def fetch_url(config: Config, bucket: TokenBucket, args: FetchURLArgs) -> dict[str, Any]:
    if not _host_is_safe(args.url):
        return {"error": "blocked", "reason": "target resolves to private or reserved address"}

    await bucket.acquire()
    timeout = args.timeout_seconds or config.default_timeout_seconds
    merged = _merge_headers(config, args.country, args.headers)

    async with client_context(config.proxy, timeout_seconds=timeout, headers=merged) as client:
        try:
            request_kwargs: dict[str, Any] = {"url": args.url, "method": args.method}
            if args.body is not None and args.method not in {"GET", "HEAD"}:
                request_kwargs["content"] = args.body.encode("utf-8")
            response = await client.request(**request_kwargs)
        except httpx.TimeoutException:
            return {"error": "timeout", "timeout_seconds": timeout}
        except httpx.ProxyError as exc:
            return {"error": "proxy_error", "detail": str(exc)}
        except httpx.HTTPError as exc:
            return {"error": "http_error", "detail": str(exc)}

    body_bytes = response.content or b""
    text, truncated = _truncate_body(body_bytes, config.max_response_bytes)
    return {
        "status": response.status_code,
        "final_url": str(response.url),
        "headers": dict(response.headers),
        "body": text,
        "truncated": truncated,
        "bytes": len(body_bytes),
    }


async def scrape_page(config: Config, bucket: TokenBucket, args: ScrapePageArgs) -> dict[str, Any]:
    fetch_args = FetchURLArgs(
        url=args.url,
        country=args.country,
        timeout_seconds=args.timeout_seconds,
    )
    result = await fetch_url(config, bucket, fetch_args)
    if "error" in result:
        return result
    if result["status"] >= 400:
        return {
            "status": result["status"],
            "final_url": result["final_url"],
            "error": "http_status",
            "message": f"target returned {result['status']}",
        }

    soup = BeautifulSoup(result["body"], "lxml")
    extracted: dict[str, Any] = {}

    if args.selectors:
        for key, selector in args.selectors.items():
            matches = soup.select(selector)
            extracted[key] = [el.get_text(strip=True) for el in matches]
    else:
        title_tag = soup.find("title")
        extracted = {
            "title": title_tag.get_text(strip=True) if title_tag else "",
            "text": soup.get_text(" ", strip=True)[: config.max_response_bytes // 4],
        }

    return {
        "status": result["status"],
        "final_url": result["final_url"],
        "extracted": extracted,
    }


async def check_proxy(config: Config, bucket: TokenBucket, args: CheckProxyArgs) -> dict[str, Any]:
    """Smoke test: ask a neutral IP-echo endpoint what IP the proxy exits from."""
    await bucket.acquire()
    timeout = args.timeout_seconds or config.default_timeout_seconds
    headers = _merge_headers(config, None, None)

    async with client_context(config.proxy, timeout_seconds=timeout, headers=headers) as client:
        try:
            response = await client.get("https://api.ipify.org?format=json")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return {"error": "probe_failed", "detail": str(exc)}

    data = response.json()
    return {
        "proxy_enabled": config.proxy.enabled,
        "proxy_host": config.proxy.host if config.proxy.enabled else None,
        "exit_ip": data.get("ip"),
    }


def list_fingerprints(_config: Config, _bucket: TokenBucket, _args: ListFingerprintsArgs) -> dict[str, Any]:
    return {"supported_countries": fingerprint.supported_countries()}

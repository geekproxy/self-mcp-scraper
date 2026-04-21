"""MCP server entry point.

Supports stdio transport (default, used by Claude Desktop, Cursor, Cline)
and streamable HTTP transport (used by remote MCP clients like ChatGPT).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from . import config as config_module
from .rate_limit import TokenBucket
from .tools import (
    CheckProxyArgs,
    FetchURLArgs,
    ListFingerprintsArgs,
    ScrapePageArgs,
    check_proxy,
    fetch_url,
    list_fingerprints,
    scrape_page,
)

logger = logging.getLogger("self_mcp_scraper")


def _configure_logging(level: str, as_json: bool) -> None:
    handler = logging.StreamHandler(stream=sys.stderr)
    if as_json:
        formatter = logging.Formatter(
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=[handler], force=True)


TOOL_DEFINITIONS: list[types.Tool] = [
    types.Tool(
        name="fetch_url",
        description=(
            "Fetch a URL through the configured proxy. Returns status, final URL, "
            "headers, and the response body as UTF-8 text (truncated to the configured limit)."
        ),
        inputSchema=FetchURLArgs.model_json_schema(),
    ),
    types.Tool(
        name="scrape_page",
        description=(
            "Fetch a URL and extract fields using CSS selectors. If no selectors are "
            "provided, returns the page title and extracted text."
        ),
        inputSchema=ScrapePageArgs.model_json_schema(),
    ),
    types.Tool(
        name="check_proxy",
        description=(
            "Probe the proxy by calling an IP-echo endpoint. Returns the exit IP "
            "as seen by the public internet."
        ),
        inputSchema=CheckProxyArgs.model_json_schema(),
    ),
    types.Tool(
        name="list_fingerprints",
        description="List country codes for which a matching fingerprint preset is available.",
        inputSchema=ListFingerprintsArgs.model_json_schema(),
    ),
]


def build_server() -> Server:
    cfg = config_module.load()
    _configure_logging(cfg.log_level, cfg.log_json)

    if cfg.proxy.enabled:
        logger.info(
            "proxy configured: scheme=%s host=%s port=%s",
            cfg.proxy.scheme,
            cfg.proxy.host,
            cfg.proxy.port,
        )
    else:
        logger.warning("no proxy configured; requests will use direct network egress")

    bucket = TokenBucket(cfg.rate_limit_capacity, cfg.rate_limit_refill_per_second)
    server: Server = Server("self-mcp-scraper")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return TOOL_DEFINITIONS

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        logger.info("tool_call name=%s", name)
        try:
            if name == "fetch_url":
                args = FetchURLArgs(**arguments)
                result = await fetch_url(cfg, bucket, args)
            elif name == "scrape_page":
                args = ScrapePageArgs(**arguments)
                result = await scrape_page(cfg, bucket, args)
            elif name == "check_proxy":
                args = CheckProxyArgs(**arguments)
                result = await check_proxy(cfg, bucket, args)
            elif name == "list_fingerprints":
                args = ListFingerprintsArgs(**arguments)
                result = list_fingerprints(cfg, bucket, args)
            else:
                result = {"error": "unknown_tool", "name": name}
        except Exception as exc:
            logger.exception("tool_error name=%s", name)
            result = {"error": "exception", "detail": str(exc)}

        payload = json.dumps(result, ensure_ascii=False, default=str)
        return [types.TextContent(type="text", text=payload)]

    return server


async def run_stdio() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_http(host: str, port: int) -> None:
    """Run as a streamable HTTP MCP server.

    Used by remote MCP clients that cannot launch a stdio subprocess.
    """
    try:
        from mcp.server.streamable_http import StreamableHTTPServerTransport  # type: ignore
    except Exception as exc:  # pragma: no cover - import path shifts with SDK version
        raise RuntimeError(
            "streamable HTTP transport is not available in this mcp version; "
            "use stdio mode or upgrade the mcp package"
        ) from exc
    try:
        import uvicorn
        from starlette.applications import Starlette
        from starlette.routing import Mount
    except ImportError as exc:
        raise RuntimeError(
            "HTTP transport requires 'uvicorn' and 'starlette'. Install with: "
            "pip install 'self-mcp-scraper[http]'"
        ) from exc

    server = build_server()
    transport = StreamableHTTPServerTransport(mcp_server=server)
    app = Starlette(routes=[Mount("/mcp", app=transport.handle_request)])
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


def main() -> None:
    parser = argparse.ArgumentParser(prog="self-mcp-scraper")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode. Use stdio for Claude Desktop/Cursor, http for remote clients.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host")
    parser.add_argument("--port", type=int, default=8765, help="HTTP bind port")
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(run_stdio())
    else:
        asyncio.run(run_http(args.host, args.port))


if __name__ == "__main__":
    main()

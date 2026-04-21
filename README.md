# self-mcp-scraper

A self-hosted MCP server that exposes web fetch and scrape tools to AI agents, routing every request through your own HTTP or SOCKS5 proxy.

Built for a specific use case: you already have a proxy subscription, you want Claude Desktop or Cursor to use it, and you do not want to pay a managed scraping API on top of your existing proxy bill.

## What it does

- Exposes four MCP tools to any compatible client: `fetch_url`, `scrape_page`, `check_proxy`, `list_fingerprints`.
- Routes all HTTP traffic through a single upstream proxy configured via environment variables.
- Supports HTTP, HTTPS, and SOCKS5 proxies out of the box.
- Applies geo-matched fingerprint headers (User-Agent, Accept-Language, timezone hints) so a request through a German IP does not arrive with en-US locale.
- Enforces a per-request timeout and a token-bucket rate limiter so a runaway agent cannot burn your proxy quota in a retry storm.
- Blocks tool calls that resolve to private, loopback, link-local, or reserved IP ranges. The server is exposed to an LLM, and prompt injection is real.

## What it does not do

- It does not manage proxy rotation across a pool. One upstream proxy, one sticky session, by design.
- It does not render JavaScript. Use the optional Playwright extra or wrap a headless browser yourself if you need that.
- It does not cache responses.

## Install

```bash
git clone https://github.com/YOUR-ACCOUNT/self-mcp-scraper
cd self-mcp-scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

Copy `.env.example` to `.env` and fill in your proxy credentials, or pass the same variables via your MCP client's `env` block. The minimum viable config is just `PROXY_HOST` and `PROXY_PORT`.

```bash
PROXY_SCHEME=socks5
PROXY_HOST=proxy.example.com
PROXY_PORT=1080
PROXY_USER=alice
PROXY_PASS=secret
DEFAULT_FINGERPRINT_COUNTRY=US
```

## Verify

Before wiring up an MCP client, confirm the tools work against your proxy:

```bash
python examples/standalone_probe.py
```

You should see your proxy's exit IP under `check_proxy`, a 200 from `example.com`, and extracted headings from the scrape.

## Wire up Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on Windows and Linux. See `examples/claude_desktop_config.json` for a template. Replace the path to the binary with the absolute path to `.venv/bin/self-mcp-scraper` inside your clone.

Restart Claude Desktop. The four tools should appear in the slash menu under the server name `self-mcp-scraper`.

## Wire up Cursor

Add the `mcpServers` block from `examples/cursor_config.json` to your Cursor settings. Restart Cursor.

## Tools

### `fetch_url`

Raw HTTP fetch. Accepts `url`, `method`, `headers`, `body`, `timeout_seconds`, `country`. Returns `status`, `final_url`, `headers`, `body`, `truncated`, `bytes`.

### `scrape_page`

Fetches a URL and extracts fields with CSS selectors. Accepts `url`, `selectors` (map of field name to selector), `country`, `timeout_seconds`. If `selectors` is empty, returns the page title and text body.

### `check_proxy`

Calls `api.ipify.org` through the proxy and returns the exit IP. Use this to confirm your proxy is reachable and to verify the IP geolocates where you expect.

### `list_fingerprints`

Returns the ISO country codes for which a matching fingerprint preset exists.

## Fingerprint presets

Passing `country: "DE"` attaches `Accept-Language: de-DE,de;q=0.9,en;q=0.7`, a Chrome/131 User-Agent, and `Europe/Berlin`-appropriate hints. Currently supported: US, GB, DE, FR, ES, IT, NL, PL, RU, UA, TR, AZ, CN, JP, KR, IN, BR, MX, CA, AU, AE, SG, ZA. Pull requests to add more are welcome.

## Rate limiting

A shared token bucket across all tool calls. Default: burst of 10, sustained 2 req/s. Tune via `RATE_LIMIT_CAPACITY` and `RATE_LIMIT_REFILL_PER_SECOND`. When the bucket is empty, calls block until a token refills. This is cheaper than discovering a runaway agent through your proxy invoice.

## Response size cap

`MAX_RESPONSE_BYTES` bounds the body returned to the agent (default 5 MB). Larger responses are truncated and flagged with `truncated: true`. Without a cap, a single page can blow your model context budget.

## Transport

Stdio by default, which is what Claude Desktop, Cursor, Cline, and most local MCP clients want. For remote clients that need HTTP:

```bash
self-mcp-scraper --transport http --port 8765
```

Streamable HTTP support depends on the installed `mcp` package version. If it is unavailable on your install, the server will tell you on start.

## Security notes

The server blocks URLs that resolve to private, loopback, link-local, multicast, or reserved IP ranges. This is the minimum acceptable SSRF guard for a tool exposed to an LLM. It will not save you from a targeted attacker, but it will stop a prompt-injected agent from fetching `http://169.254.169.254/latest/meta-data/`.

Do not commit your `.env`. The `.gitignore` already excludes it.

## License

MIT. See `LICENSE`.

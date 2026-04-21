"""Configuration loader. Reads environment variables and optional .env file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv(override=False)


ProxyScheme = Literal["http", "https", "socks5", "socks5h"]


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got {raw!r}") from exc


@dataclass(slots=True)
class ProxyConfig:
    """Single upstream proxy. Leave host empty to disable proxying."""

    scheme: ProxyScheme
    host: str
    port: int
    username: str | None
    password: str | None

    @property
    def enabled(self) -> bool:
        return bool(self.host)

    def as_url(self) -> str | None:
        if not self.enabled:
            return None
        auth = ""
        if self.username:
            if self.password:
                auth = f"{self.username}:{self.password}@"
            else:
                auth = f"{self.username}@"
        return f"{self.scheme}://{auth}{self.host}:{self.port}"


@dataclass(slots=True)
class Config:
    proxy: ProxyConfig
    default_timeout_seconds: float
    rate_limit_capacity: int
    rate_limit_refill_per_second: float
    default_fingerprint_country: str | None
    max_response_bytes: int
    user_agent_override: str | None
    log_level: str
    log_json: bool
    allowed_schemes: tuple[str, ...] = field(default=("http", "https"))


def load() -> Config:
    scheme = os.getenv("PROXY_SCHEME", "http").strip().lower()
    if scheme not in {"http", "https", "socks5", "socks5h"}:
        raise ValueError(f"PROXY_SCHEME must be one of http/https/socks5/socks5h, got {scheme!r}")

    proxy = ProxyConfig(
        scheme=scheme,  # type: ignore[arg-type]
        host=os.getenv("PROXY_HOST", "").strip(),
        port=_get_int("PROXY_PORT", 0),
        username=os.getenv("PROXY_USER") or None,
        password=os.getenv("PROXY_PASS") or None,
    )

    return Config(
        proxy=proxy,
        default_timeout_seconds=_get_float("DEFAULT_TIMEOUT_SECONDS", 30.0),
        rate_limit_capacity=_get_int("RATE_LIMIT_CAPACITY", 10),
        rate_limit_refill_per_second=_get_float("RATE_LIMIT_REFILL_PER_SECOND", 2.0),
        default_fingerprint_country=(os.getenv("DEFAULT_FINGERPRINT_COUNTRY") or None),
        max_response_bytes=_get_int("MAX_RESPONSE_BYTES", 5 * 1024 * 1024),
        user_agent_override=os.getenv("USER_AGENT_OVERRIDE") or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_json=_get_bool("LOG_JSON", True),
    )

"""Config parsing from environment variables."""
from __future__ import annotations

import pytest

from self_mcp_scraper import config as config_module


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in [
        "PROXY_SCHEME",
        "PROXY_HOST",
        "PROXY_PORT",
        "PROXY_USER",
        "PROXY_PASS",
        "DEFAULT_TIMEOUT_SECONDS",
        "RATE_LIMIT_CAPACITY",
        "RATE_LIMIT_REFILL_PER_SECOND",
        "DEFAULT_FINGERPRINT_COUNTRY",
        "MAX_RESPONSE_BYTES",
        "USER_AGENT_OVERRIDE",
        "LOG_LEVEL",
        "LOG_JSON",
    ]:
        monkeypatch.delenv(var, raising=False)


def test_load_defaults_disables_proxy() -> None:
    cfg = config_module.load()
    assert cfg.proxy.enabled is False
    assert cfg.proxy.scheme == "http"
    assert cfg.default_timeout_seconds == 30.0
    assert cfg.rate_limit_capacity == 10


def test_load_reads_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY_SCHEME", "socks5")
    monkeypatch.setenv("PROXY_HOST", "proxy.example.com")
    monkeypatch.setenv("PROXY_PORT", "1080")
    monkeypatch.setenv("PROXY_USER", "user")
    monkeypatch.setenv("PROXY_PASS", "secret")
    cfg = config_module.load()
    assert cfg.proxy.enabled is True
    assert cfg.proxy.as_url() == "socks5://user:secret@proxy.example.com:1080"


def test_invalid_scheme_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROXY_SCHEME", "ftp")
    with pytest.raises(ValueError):
        config_module.load()


def test_bool_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_JSON", "false")
    cfg = config_module.load()
    assert cfg.log_json is False

    monkeypatch.setenv("LOG_JSON", "yes")
    cfg = config_module.load()
    assert cfg.log_json is True

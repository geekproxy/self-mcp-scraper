"""Fingerprint preset lookup and header shape."""
from __future__ import annotations

from self_mcp_scraper import fingerprint


def test_lookup_case_insensitive() -> None:
    us_upper = fingerprint.get("US")
    us_lower = fingerprint.get("us")
    assert us_upper is not None
    assert us_upper == us_lower


def test_unknown_country_returns_none() -> None:
    assert fingerprint.get("XX") is None
    assert fingerprint.get(None) is None


def test_to_headers_has_required_fields() -> None:
    fp = fingerprint.get("DE")
    assert fp is not None
    headers = fingerprint.to_headers(fp)
    assert "User-Agent" in headers
    assert headers["Accept-Language"].startswith("de-DE")
    assert "Accept" in headers


def test_user_agent_override() -> None:
    fp = fingerprint.get("US")
    assert fp is not None
    headers = fingerprint.to_headers(fp, user_agent_override="CustomAgent/1.0")
    assert headers["User-Agent"] == "CustomAgent/1.0"


def test_supported_countries_sorted() -> None:
    countries = fingerprint.supported_countries()
    assert countries == sorted(countries)
    assert "US" in countries
    assert "AZ" in countries

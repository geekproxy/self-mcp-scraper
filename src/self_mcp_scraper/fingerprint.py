"""Geo-matched fingerprint presets.

Anti-bot systems flag requests where the exit IP geolocates to one country
but the HTTP headers advertise a different locale or timezone. These presets
align the most-checked header surface with the IP's country of origin.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Fingerprint:
    country: str
    accept_language: str
    timezone: str
    user_agent: str


_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_MAC_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
)


_PRESETS: dict[str, Fingerprint] = {
    "US": Fingerprint("US", "en-US,en;q=0.9", "America/New_York", _DEFAULT_UA),
    "GB": Fingerprint("GB", "en-GB,en;q=0.9", "Europe/London", _DEFAULT_UA),
    "DE": Fingerprint("DE", "de-DE,de;q=0.9,en;q=0.7", "Europe/Berlin", _DEFAULT_UA),
    "FR": Fingerprint("FR", "fr-FR,fr;q=0.9,en;q=0.7", "Europe/Paris", _DEFAULT_UA),
    "ES": Fingerprint("ES", "es-ES,es;q=0.9,en;q=0.7", "Europe/Madrid", _DEFAULT_UA),
    "IT": Fingerprint("IT", "it-IT,it;q=0.9,en;q=0.7", "Europe/Rome", _DEFAULT_UA),
    "NL": Fingerprint("NL", "nl-NL,nl;q=0.9,en;q=0.7", "Europe/Amsterdam", _DEFAULT_UA),
    "PL": Fingerprint("PL", "pl-PL,pl;q=0.9,en;q=0.7", "Europe/Warsaw", _DEFAULT_UA),
    "RU": Fingerprint("RU", "ru-RU,ru;q=0.9,en;q=0.7", "Europe/Moscow", _DEFAULT_UA),
    "UA": Fingerprint("UA", "uk-UA,uk;q=0.9,ru;q=0.7,en;q=0.5", "Europe/Kyiv", _DEFAULT_UA),
    "TR": Fingerprint("TR", "tr-TR,tr;q=0.9,en;q=0.7", "Europe/Istanbul", _DEFAULT_UA),
    "AZ": Fingerprint("AZ", "az-AZ,az;q=0.9,ru;q=0.7,en;q=0.5", "Asia/Baku", _DEFAULT_UA),
    "CN": Fingerprint("CN", "zh-CN,zh;q=0.9,en;q=0.7", "Asia/Shanghai", _DEFAULT_UA),
    "JP": Fingerprint("JP", "ja-JP,ja;q=0.9,en;q=0.7", "Asia/Tokyo", _MAC_UA),
    "KR": Fingerprint("KR", "ko-KR,ko;q=0.9,en;q=0.7", "Asia/Seoul", _DEFAULT_UA),
    "IN": Fingerprint("IN", "en-IN,en;q=0.9,hi;q=0.7", "Asia/Kolkata", _DEFAULT_UA),
    "BR": Fingerprint("BR", "pt-BR,pt;q=0.9,en;q=0.7", "America/Sao_Paulo", _DEFAULT_UA),
    "MX": Fingerprint("MX", "es-MX,es;q=0.9,en;q=0.7", "America/Mexico_City", _DEFAULT_UA),
    "CA": Fingerprint("CA", "en-CA,en;q=0.9,fr;q=0.7", "America/Toronto", _DEFAULT_UA),
    "AU": Fingerprint("AU", "en-AU,en;q=0.9", "Australia/Sydney", _MAC_UA),
    "AE": Fingerprint("AE", "ar-AE,ar;q=0.9,en;q=0.7", "Asia/Dubai", _DEFAULT_UA),
    "SG": Fingerprint("SG", "en-SG,en;q=0.9,zh;q=0.7", "Asia/Singapore", _DEFAULT_UA),
    "ZA": Fingerprint("ZA", "en-ZA,en;q=0.9", "Africa/Johannesburg", _DEFAULT_UA),
}


def supported_countries() -> list[str]:
    return sorted(_PRESETS.keys())


def get(country: str | None) -> Fingerprint | None:
    if not country:
        return None
    return _PRESETS.get(country.upper())


def to_headers(fp: Fingerprint, user_agent_override: str | None = None) -> dict[str, str]:
    return {
        "User-Agent": user_agent_override or fp.user_agent,
        "Accept-Language": fp.accept_language,
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-CH-UA-Platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
    }

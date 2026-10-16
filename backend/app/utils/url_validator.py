from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

import requests

from app.config import get_settings

_URL_RE = re.compile(r"^https?://", re.I)


class URLValidationError(ValueError):
    pass


def normalize_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        raise URLValidationError("URL is required.")
    if not _URL_RE.match(raw):
        raw = "https://" + raw
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise URLValidationError("URL must use http or https.")
    if not parsed.netloc:
        raise URLValidationError("URL host is missing.")
    # Drop fragment; keep path
    cleaned = parsed._replace(fragment="")
    return urlunparse(cleaned)


def check_reachability(url: str) -> tuple[str, int]:
    """Return final URL and status code after redirects."""
    settings = get_settings()
    headers = {"User-Agent": settings.crawler_user_agent}
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=settings.request_timeout_sec,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        raise URLValidationError(f"Could not reach URL: {exc}") from exc

    if resp.status_code >= 500:
        raise URLValidationError(f"Server error ({resp.status_code}) when reaching URL.")
    return str(resp.url), resp.status_code


def validate_and_normalize(raw: str) -> tuple[str, str, int]:
    """Validate format + reachability. Returns (normalized_start, final_url, status)."""
    normalized = normalize_url(raw)
    final_url, status = check_reachability(normalized)
    # Prefer HTTPS if user entered http but site redirects
    return normalized, final_url, status

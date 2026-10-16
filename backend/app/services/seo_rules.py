from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from app.config import get_settings


def _check(
    check_id: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    passed: bool,
    page_url: str | None = None,
) -> dict[str, Any]:
    return {
        "pillar": "SEO",
        "category": category,
        "check_id": check_id,
        "severity": severity,
        "weight": {"Critical": 3, "Warning": 2, "Info": 1}.get(severity, 2),
        "title": title,
        "message": message,
        "passed": passed,
        "page_url": page_url,
    }


def run_seo_rules(
    pages: list[dict[str, Any]],
    robots_status: int | None,
    sitemap_status: int | None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not pages:
        checks.append(
            _check(
                "seo.no_pages",
                "Technical",
                "Critical",
                "No pages crawled",
                "The crawler could not retrieve any HTML pages from this site.",
                False,
            )
        )
        return checks

    homepage = next((p for p in pages if p.get("is_homepage")), pages[0])
    # Full on-page analysis on homepage; lightweight status scan on others
    checks.extend(_analyze_page(homepage, full=True))

    other_errors = 0
    for page in pages:
        if page is homepage:
            continue
        code = page.get("status_code")
        if code is None or code >= 400:
            other_errors += 1
    checks.append(
        _check(
            "seo.inner_page_errors",
            "Technical",
            "Warning",
            "Inner page HTTP errors",
            f"{other_errors} of {max(len(pages) - 1, 0)} additional crawled pages returned errors."
            if other_errors
            else f"All {max(len(pages) - 1, 0)} additional crawled pages responded OK.",
            other_errors == 0,
        )
    )

    # Site-level: robots.txt — 404 means no restrictions (Info only)
    if robots_status is None:
        checks.append(
            _check(
                "seo.robots_fetch_failed",
                "Technical",
                "Info",
                "robots.txt unreachable",
                "Could not fetch robots.txt.",
                False,
            )
        )
    elif robots_status == 404:
        checks.append(
            _check(
                "seo.robots_missing",
                "Technical",
                "Info",
                "robots.txt missing",
                "robots.txt returned 404. This means no crawl restrictions (small issue only).",
                False,
            )
        )
    elif robots_status == 200:
        checks.append(
            _check(
                "seo.robots_present",
                "Technical",
                "Info",
                "robots.txt present",
                "robots.txt was found.",
                True,
            )
        )
    else:
        checks.append(
            _check(
                "seo.robots_status",
                "Technical",
                "Info",
                f"robots.txt status {robots_status}",
                f"Unexpected robots.txt status code {robots_status}.",
                False,
            )
        )

    if sitemap_status == 200:
        checks.append(
            _check(
                "seo.sitemap_present",
                "Technical",
                "Warning",
                "sitemap.xml present",
                "sitemap.xml was found.",
                True,
            )
        )
    else:
        checks.append(
            _check(
                "seo.sitemap_missing",
                "Technical",
                "Warning",
                "sitemap.xml missing",
                f"sitemap.xml not found (status {sitemap_status}).",
                False,
            )
        )

    checks.extend(_sample_broken_links(homepage))
    return checks


def _analyze_page(page: dict[str, Any], full: bool = True) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    url = page.get("url")
    code = page.get("status_code")

    if code is None:
        checks.append(
            _check(
                "seo.http_unreachable",
                "Technical",
                "Critical",
                "Page unreachable",
                f"Could not fetch a response for {url}.",
                False,
                url,
            )
        )
        return checks

    if code >= 400:
        checks.append(
            _check(
                "seo.http_error",
                "Technical",
                "Critical",
                f"HTTP {code}",
                f"Page returned status {code}. Title/H1 on error pages are ignored for ranking readiness.",
                False,
                url,
            )
        )
        return checks

    if not full:
        return checks

    title = page.get("title")
    if title is None:
        checks.append(
            _check(
                "seo.title_missing",
                "On-page",
                "Critical",
                "Title tag missing",
                "No <title> element was found on this page.",
                False,
                url,
            )
        )
    else:
        t = title.strip()
        if not t:
            checks.append(
                _check(
                    "seo.title_empty",
                    "On-page",
                    "Critical",
                    "Title tag empty",
                    "A <title> tag exists but its text is empty after trimming.",
                    False,
                    url,
                )
            )
        else:
            checks.append(
                _check(
                    "seo.title_present",
                    "On-page",
                    "Critical",
                    "Title tag present",
                    "Page has a non-empty title.",
                    True,
                    url,
                )
            )
            if len(t) < 30:
                checks.append(
                    _check(
                        "seo.title_short",
                        "On-page",
                        "Warning",
                        "Title too short",
                        f"Title is {len(t)} characters; aim for roughly 30–60.",
                        False,
                        url,
                    )
                )
            elif len(t) > 60:
                checks.append(
                    _check(
                        "seo.title_long",
                        "On-page",
                        "Warning",
                        "Title too long",
                        f"Title is {len(t)} characters; aim for roughly 30–60.",
                        False,
                        url,
                    )
                )
            else:
                checks.append(
                    _check(
                        "seo.title_length_ok",
                        "On-page",
                        "Warning",
                        "Title length OK",
                        "Title length is within a typical 30–60 character range.",
                        True,
                        url,
                    )
                )

    present = page.get("meta_description_present")
    meta = page.get("meta_description")
    if not present:
        checks.append(
            _check(
                "seo.meta_missing",
                "On-page",
                "Critical",
                "Meta description missing",
                "No meta name=\"description\" tag was found.",
                False,
                url,
            )
        )
    else:
        content = "" if meta is None else str(meta).strip()
        if content == "":
            checks.append(
                _check(
                    "seo.meta_empty",
                    "On-page",
                    "Critical",
                    "Meta description empty",
                    "A meta description tag exists but content is blank after strip().",
                    False,
                    url,
                )
            )
        else:
            checks.append(
                _check(
                    "seo.meta_present",
                    "On-page",
                    "Critical",
                    "Meta description present",
                    "Meta description has non-empty content.",
                    True,
                    url,
                )
            )
            if len(content) < 70:
                checks.append(
                    _check(
                        "seo.meta_short",
                        "On-page",
                        "Info",
                        "Meta description short",
                        f"Meta description is {len(content)} characters; often 70–160 works well.",
                        False,
                        url,
                    )
                )
            elif len(content) > 160:
                checks.append(
                    _check(
                        "seo.meta_long",
                        "On-page",
                        "Info",
                        "Meta description long",
                        f"Meta description is {len(content)} characters; often 70–160 works well.",
                        False,
                        url,
                    )
                )
            else:
                checks.append(
                    _check(
                        "seo.meta_length_ok",
                        "On-page",
                        "Info",
                        "Meta description length OK",
                        "Meta description length looks reasonable.",
                        True,
                        url,
                    )
                )

    headings = page.get("headings") or {}
    h1s = headings.get("h1") or []
    if len(h1s) == 0:
        checks.append(
            _check(
                "seo.h1_missing",
                "On-page",
                "Critical",
                "H1 missing",
                "No H1 heading found on this page.",
                False,
                url,
            )
        )
    elif len(h1s) > 1:
        checks.append(
            _check(
                "seo.h1_multiple",
                "On-page",
                "Warning",
                "Multiple H1s",
                f"Found {len(h1s)} H1 headings; one clear H1 is preferred.",
                False,
                url,
            )
        )
    else:
        checks.append(
            _check(
                "seo.h1_ok",
                "On-page",
                "Critical",
                "Single H1 present",
                "Page has exactly one H1.",
                True,
                url,
            )
        )

    order_ok = True
    last_level = 0
    for level in range(1, 7):
        if headings.get(f"h{level}"):
            if last_level and level > last_level + 1:
                order_ok = False
                break
            last_level = level
    checks.append(
        _check(
            "seo.heading_order",
            "On-page",
            "Info",
            "Heading order",
            "Headings skip levels (e.g. H2 to H4)." if not order_ok else "Heading hierarchy looks sequential.",
            order_ok,
            url,
        )
    )

    images = page.get("images") or []
    missing_alt = sum(1 for im in images if im.get("alt_missing") or im.get("alt_empty"))
    if images:
        checks.append(
            _check(
                "seo.img_alt",
                "Images and Links",
                "Warning",
                "Image ALT text",
                f"{missing_alt} of {len(images)} images missing or empty ALT."
                if missing_alt
                else "All images have ALT text.",
                missing_alt == 0,
                url,
            )
        )

    empty_anchors = [
        ln
        for ln in (page.get("links") or [])
        if ln.get("is_internal") and not (ln.get("text") or "").strip()
    ]
    checks.append(
        _check(
            "seo.empty_anchors",
            "Images and Links",
            "Info",
            "Empty anchor text",
            f"{len(empty_anchors)} internal links have empty anchor text."
            if empty_anchors
            else "Internal links have visible anchor text.",
            len(empty_anchors) == 0,
            url,
        )
    )

    if not page.get("canonical"):
        checks.append(
            _check(
                "seo.canonical_missing",
                "Technical",
                "Warning",
                "Canonical missing",
                "No rel=canonical link found.",
                False,
                url,
            )
        )
    else:
        checks.append(
            _check(
                "seo.canonical_present",
                "Technical",
                "Warning",
                "Canonical present",
                "Canonical URL is set.",
                True,
                url,
            )
        )

    checks.append(
        _check(
            "seo.viewport",
            "Technical",
            "Warning",
            "Viewport meta",
            "Viewport meta tag is missing." if not page.get("viewport") else "Viewport meta tag present.",
            bool(page.get("viewport")),
            url,
        )
    )

    robots = (page.get("robots_meta") or "").lower()
    blocked = "noindex" in robots
    checks.append(
        _check(
            "seo.noindex",
            "Technical",
            "Critical",
            "Indexability (robots meta)",
            "Page has noindex and may be blocked from search indexing."
            if blocked
            else "Page is not marked noindex (NOARCHIVE/NOCACHE alone are not treated as blocked).",
            not blocked,
            url,
        )
    )

    schema = page.get("schema_jsonld") or []
    checks.append(
        _check(
            "seo.schema",
            "Technical",
            "Warning",
            "Structured data (JSON-LD)",
            "No JSON-LD schema found." if not schema else f"Found {len(schema)} JSON-LD block(s).",
            bool(schema),
            url,
        )
    )

    scheme = urlparse(page.get("final_url") or url or "").scheme
    checks.append(
        _check(
            "seo.https",
            "Technical",
            "Critical",
            "HTTPS",
            "Page is not served over HTTPS." if scheme != "https" else "Page uses HTTPS.",
            scheme == "https",
            url,
        )
    )

    load_ms = page.get("load_ms")
    if load_ms is not None:
        ok = load_ms < 3000
        checks.append(
            _check(
                "seo.load_time",
                "Performance",
                "Warning",
                "Page load time",
                f"Measured response time ~{int(load_ms)} ms"
                + (" (slow; aim under ~3s)." if not ok else " (acceptable for this check)."),
                ok,
                url,
            )
        )

    return checks


def _sample_broken_links(page: dict[str, Any]) -> list[dict[str, Any]]:
    settings = get_settings()
    links = [ln for ln in (page.get("links") or []) if ln.get("is_internal")][:5]
    broken = 0
    checked = 0
    for ln in links:
        href = ln.get("href")
        if not href:
            continue
        checked += 1
        try:
            resp = requests.head(
                href,
                timeout=3,
                allow_redirects=True,
                headers={"User-Agent": settings.crawler_user_agent},
            )
            if resp.status_code == 405:
                resp = requests.get(
                    href,
                    timeout=3,
                    allow_redirects=True,
                    headers={"User-Agent": settings.crawler_user_agent},
                    stream=True,
                )
                resp.close()
            if resp.status_code >= 400:
                broken += 1
        except requests.RequestException:
            broken += 1
    if checked == 0:
        return [
            _check(
                "seo.broken_links_skip",
                "Images and Links",
                "Info",
                "Broken links",
                "No internal links sampled on the homepage.",
                True,
                page.get("url"),
            )
        ]
    return [
        _check(
            "seo.broken_links",
            "Images and Links",
            "Critical",
            "Broken internal links",
            f"{broken} of {checked} sampled internal links returned an error."
            if broken
            else f"All {checked} sampled internal links responded OK.",
            broken == 0,
            page.get("url"),
        )
    ]

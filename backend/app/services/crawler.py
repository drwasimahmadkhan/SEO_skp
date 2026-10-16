from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from collections import deque
from typing import Any, Callable
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

import requests

from app.config import get_settings
from app.services.extractor import extract_page


ProgressCb = Callable[[int, str], None]


class CrawlResult:
    def __init__(self) -> None:
        self.pages: list[dict[str, Any]] = []
        self.robots_status: int | None = None
        self.robots_body: str | None = None
        self.sitemap_status: int | None = None
        self.sitemap_urls: list[str] = []
        self.robots_parser: RobotFileParser | None = None


def _session() -> requests.Session:
    settings = get_settings()
    s = requests.Session()
    s.headers.update({"User-Agent": settings.crawler_user_agent})
    return s


def _origin(url: str) -> str:
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"


def _normalize_link(url: str) -> str:
    url, _ = urldefrag(url)
    p = urlparse(url)
    path = p.path or "/"
    return f"{p.scheme}://{p.netloc.lower()}{path}" + (f"?{p.query}" if p.query else "")


def fetch_robots(session: requests.Session, start_url: str) -> tuple[int, str | None, RobotFileParser | None]:
    settings = get_settings()
    robots_url = urljoin(_origin(start_url) + "/", "robots.txt")
    try:
        resp = session.get(robots_url, timeout=settings.request_timeout_sec, allow_redirects=True)
        status = resp.status_code
        body = resp.text if status == 200 else None
        parser = RobotFileParser()
        parser.set_url(robots_url)
        if status == 200 and body is not None:
            parser.parse(body.splitlines())
        else:
            # 404 = no restrictions
            parser.parse([])
        return status, body, parser
    except requests.RequestException:
        return None, None, None  # type: ignore[return-value]


def fetch_sitemap(session: requests.Session, start_url: str) -> tuple[int | None, list[str]]:
    settings = get_settings()
    sitemap_url = urljoin(_origin(start_url) + "/", "sitemap.xml")
    try:
        resp = session.get(sitemap_url, timeout=settings.request_timeout_sec, allow_redirects=True)
        if resp.status_code != 200:
            return resp.status_code, []
        urls: list[str] = []
        try:
            root = ET.fromstring(resp.content)
            for loc in root.iter():
                if loc.tag.endswith("loc") and loc.text:
                    urls.append(loc.text.strip())
        except ET.ParseError:
            pass
        return resp.status_code, urls
    except requests.RequestException:
        return None, []


def crawl_site(
    start_url: str,
    on_progress: ProgressCb | None = None,
) -> CrawlResult:
    settings = get_settings()
    session = _session()
    result = CrawlResult()

    robots_status, robots_body, robots_parser = fetch_robots(session, start_url)
    result.robots_status = robots_status
    result.robots_body = robots_body
    result.robots_parser = robots_parser

    sitemap_status, sitemap_urls = fetch_sitemap(session, start_url)
    result.sitemap_status = sitemap_status
    result.sitemap_urls = sitemap_urls

    host = urlparse(start_url).netloc.lower()
    seen: set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    start_norm = _normalize_link(start_url)
    queue.append((start_norm, 0))

    # Seed a few sitemap URLs of same host
    for su in sitemap_urls[:10]:
        if urlparse(su).netloc.lower() == host:
            queue.append((_normalize_link(su), 1))

    page_limit = settings.page_limit
    delay = settings.request_delay_ms / 1000.0
    # Cap link objects stored per page to keep DB/report light
    max_links_store = 40

    while queue and len(result.pages) < page_limit:
        url, depth = queue.popleft()
        if url in seen:
            continue
        seen.add(url)

        if robots_parser is not None:
            try:
                if not robots_parser.can_fetch(settings.crawler_user_agent, url):
                    continue
            except Exception:
                pass

        if on_progress:
            pct = int(100 * len(result.pages) / page_limit)
            on_progress(min(pct, 90), f"Crawling ({len(result.pages) + 1}/{page_limit}): {url}")

        t0 = time.perf_counter()
        try:
            resp = session.get(
                url,
                timeout=settings.request_timeout_sec,
                allow_redirects=True,
            )
            load_ms = (time.perf_counter() - t0) * 1000
            final_url = str(resp.url)
            html = resp.text if "text/html" in (resp.headers.get("Content-Type") or "") else ""
            extracted = extract_page(html, final_url) if html else {
                "title": None,
                "meta_description": None,
                "meta_description_present": False,
                "canonical": None,
                "viewport": None,
                "robots_meta": None,
                "headings": {f"h{i}": [] for i in range(1, 7)},
                "images": [],
                "links": [],
                "schema_jsonld": [],
                "body_text": "",
            }
            # Keep crawl queue discovery from full link list, but trim stored payload
            all_links = extracted.get("links") or []
            extracted["links"] = all_links[:max_links_store]
            extracted["images"] = (extracted.get("images") or [])[:30]
            if extracted.get("body_text"):
                extracted["body_text"] = extracted["body_text"][:20000]

            page = {
                "url": url,
                "final_url": final_url,
                "status_code": resp.status_code,
                "load_ms": load_ms,
                "is_homepage": len(result.pages) == 0,
                "depth": depth,
                **extracted,
            }
            result.pages.append(page)

            for link in all_links:
                if not link.get("is_internal"):
                    continue
                href = link.get("href") or ""
                if urlparse(href).netloc.lower() != host:
                    continue
                if href.startswith(("mailto:", "tel:", "javascript:")):
                    continue
                norm = _normalize_link(href)
                if norm not in seen:
                    queue.append((norm, depth + 1))
        except requests.RequestException as exc:
            result.pages.append(
                {
                    "url": url,
                    "final_url": url,
                    "status_code": None,
                    "load_ms": None,
                    "is_homepage": len(result.pages) == 0,
                    "depth": depth,
                    "title": None,
                    "meta_description": None,
                    "meta_description_present": False,
                    "canonical": None,
                    "viewport": None,
                    "robots_meta": None,
                    "headings": {f"h{i}": [] for i in range(1, 7)},
                    "images": [],
                    "links": [],
                    "schema_jsonld": [],
                    "body_text": "",
                    "error": str(exc),
                }
            )

        if delay:
            time.sleep(delay)

    return result

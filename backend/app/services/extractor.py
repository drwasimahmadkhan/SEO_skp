from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


def extract_page(html: str, base_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_desc_tag = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    meta_description_present = meta_desc_tag is not None
    meta_description = None
    if meta_desc_tag is not None:
        meta_description = meta_desc_tag.get("content")
        if meta_description is not None:
            meta_description = str(meta_description)

    canonical_tag = soup.find("link", attrs={"rel": re.compile(r"canonical", re.I)})
    canonical = canonical_tag.get("href") if canonical_tag else None
    if canonical:
        canonical = urljoin(base_url, str(canonical))

    viewport_tag = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.I)})
    viewport = viewport_tag.get("content") if viewport_tag else None

    robots_tag = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    robots_meta = robots_tag.get("content") if robots_tag else None

    headings: dict[str, list[str]] = {f"h{i}": [] for i in range(1, 7)}
    for i in range(1, 7):
        for tag in soup.find_all(f"h{i}"):
            text = tag.get_text(" ", strip=True)
            if text:
                headings[f"h{i}"].append(text)

    images = []
    for img in soup.find_all("img"):
        src = img.get("src") or ""
        alt = img.get("alt")
        images.append(
            {
                "src": urljoin(base_url, src) if src else "",
                "alt": alt if alt is not None else None,
                "alt_missing": alt is None,
                "alt_empty": alt is not None and str(alt).strip() == "",
            }
        )

    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)
        abs_url = urljoin(base_url, href)
        links.append(
            {
                "href": abs_url,
                "text": text,
                "is_internal": _same_host(base_url, abs_url),
            }
        )

    schema_jsonld = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                schema_jsonld.extend(data)
            else:
                schema_jsonld.append(data)
        except json.JSONDecodeError:
            continue

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    body = soup.body or soup
    body_text = body.get_text("\n", strip=True)

    return {
        "title": title,
        "meta_description": meta_description,
        "meta_description_present": meta_description_present,
        "canonical": canonical,
        "viewport": viewport,
        "robots_meta": robots_meta,
        "headings": headings,
        "images": images,
        "links": links,
        "schema_jsonld": schema_jsonld,
        "body_text": body_text,
    }


def _same_host(a: str, b: str) -> bool:
    try:
        return urlparse(a).netloc.lower() == urlparse(b).netloc.lower()
    except Exception:
        return False

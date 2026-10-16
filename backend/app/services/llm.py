from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import get_settings

_AVAIL_CACHE: bool | None = None


def llm_available() -> bool:
    global _AVAIL_CACHE
    if _AVAIL_CACHE is not None:
        return _AVAIL_CACHE
    settings = get_settings()
    try:
        r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
        _AVAIL_CACHE = r.status_code == 200
    except Exception:
        _AVAIL_CACHE = False
    return _AVAIL_CACHE


def _chat(prompt: str, system: str) -> str | None:
    settings = get_settings()
    try:
        r = httpx.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "stream": False,
                "format": "json",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=60.0,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        return data.get("message", {}).get("content")
    except Exception:
        return None


def generate_visitor_questions(body_text: str, title: str | None) -> list[str]:
    system = (
        "You generate realistic visitor questions using ONLY the provided page text. "
        "Return JSON: {\"questions\": [\"...\"]}. Max 8 questions. "
        "Never invent business facts not present in the text."
    )
    prompt = f"Page title: {title or ''}\n\nPage text:\n{body_text[:6000]}\n\nGenerate questions."
    raw = _chat(prompt, system)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        qs = data.get("questions") or []
        return [str(q).strip() for q in qs if str(q).strip()][:8]
    except json.JSONDecodeError:
        return []


def generate_recommendations(
    failed_issues: list[dict[str, Any]],
    body_text: str,
) -> list[dict[str, Any]]:
    """Return list of {issue_check_id, text, is_quick_win} from LLM or empty for fallback."""
    if not failed_issues or not llm_available():
        return []
    system = (
        "You write plain-language website fix recommendations. "
        "Use ONLY facts from the page text. If a fact is unknown, use placeholders like "
        "[your confirmed lead time] or [your confirmed phone]. "
        "Never invent addresses, prices, or claims. "
        "Return JSON: {\"recommendations\": [{\"check_id\": \"...\", \"text\": \"...\", \"is_quick_win\": true/false}]}"
    )
    issue_lines = [
        f"- {i['check_id']}: {i['title']} ({i['severity']}) — {i['message']}" for i in failed_issues[:20]
    ]
    prompt = (
        "Failed checks:\n"
        + "\n".join(issue_lines)
        + f"\n\nPage excerpt:\n{body_text[:4000]}\n\nWrite recommendations."
    )
    raw = _chat(prompt, system)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        out = []
        for item in data.get("recommendations") or []:
            out.append(
                {
                    "check_id": item.get("check_id"),
                    "text": item.get("text"),
                    "is_quick_win": bool(item.get("is_quick_win")),
                }
            )
        return out
    except json.JSONDecodeError:
        return []


def extract_business_services(body_text: str, title: str | None) -> list[str]:
    if not llm_available():
        return _heuristic_services(body_text)
    system = (
        "Extract service names offered by the business from the page text only. "
        "Return JSON {\"services\": [\"...\"]}. If none found, return empty list. Do not invent."
    )
    prompt = f"Title: {title or ''}\n\n{body_text[:5000]}"
    raw = _chat(prompt, system)
    if not raw:
        return _heuristic_services(body_text)
    try:
        data = json.loads(raw)
        return [str(s).strip() for s in (data.get("services") or []) if str(s).strip()][:15]
    except json.JSONDecodeError:
        return _heuristic_services(body_text)


def _heuristic_services(body: str) -> list[str]:
    services = []
    for m in re.finditer(r"(?:we offer|services? include|our services)[:\s]+([^.!\n]{10,120})", body, re.I):
        services.append(m.group(1).strip())
    return services[:5]


RULE_RECOMMENDATIONS = {
    "seo.meta_empty": "Write a unique 70–160 character meta description that summarizes the page. Do not leave content=\"\".",
    "seo.meta_missing": "Add a <meta name=\"description\" content=\"...\"> tag with a clear summary of the page.",
    "seo.canonical_missing": "Add <link rel=\"canonical\" href=\"[your preferred page URL]\"> pointing to the preferred version of this page.",
    "seo.schema": "Add JSON-LD structured data (e.g. Organization or LocalBusiness) using only confirmed business facts.",
    "seo.robots_missing": "Optional: add a robots.txt. A 404 means no crawl restrictions — low priority.",
    "seo.sitemap_missing": "Publish a sitemap.xml listing important URLs and reference it in robots.txt.",
    "seo.title_missing": "Add a descriptive <title> tag (about 30–60 characters).",
    "seo.h1_missing": "Add a single clear H1 that matches the main topic of the page.",
    "seo.img_alt": "Add meaningful ALT text to images that describe the image content.",
    "seo.noindex": "Remove noindex from the robots meta tag if you want this page indexed.",
    "aeo.faq_present": "Add an FAQ section answering real visitor questions with confirmed facts only.",
    "aeo.answer_coverage": "Rewrite thin sections so each common visitor question gets a direct answer.",
    "geo.ai_bots_blocked": "If you want AI assistants to cite your site, allow GPTBot/PerplexityBot/ClaudeBot in robots.txt (your choice).",
    "geo.org_schema": "Add Organization or LocalBusiness JSON-LD with name, address, telephone only if confirmed on-site.",
    "geo.trust_signals": "Add clear About, Contact, and author/owner information with consistent NAP details.",
}


def rule_based_recommendations(failed_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for issue in failed_issues:
        cid = issue["check_id"]
        text = RULE_RECOMMENDATIONS.get(
            cid,
            f"Fix: {issue['title']}. {issue['message']} Use placeholders like [your confirmed detail] for unknown facts.",
        )
        quick = issue.get("severity") in ("Critical", "Warning") and cid.startswith(
            ("seo.meta", "seo.title", "seo.h1", "seo.canonical", "seo.viewport")
        )
        out.append({"check_id": cid, "text": text, "is_quick_win": quick})
    return out

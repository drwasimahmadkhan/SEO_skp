from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import networkx as nx
from rapidfuzz import fuzz

from app.services.llm import extract_business_services

PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-\.]?)?(?:\(?\d{2,4}\)?[\s\-\.]?)?\d{3,4}[\s\-\.]?\d{3,4}"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
CITY_HINTS = re.compile(
    r"\b(Karachi|Lahore|Islamabad|Rawalpindi|Peshawar|Quetta|Multan|Faisalabad|"
    r"London|New York|Toronto|Dubai|Berlin|Paris|Sydney|Chicago|Houston)\b",
    re.I,
)
AI_BOTS = ("GPTBot", "PerplexityBot", "ClaudeBot", "Google-Extended", "anthropic-ai")


def _check(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pillar", "GEO")
    kwargs.setdefault(
        "weight",
        {"Critical": 3, "Warning": 2, "Info": 1}.get(kwargs.get("severity", "Warning"), 2),
    )
    return kwargs


def _bot_blocked(robots_body: str | None, bot: str) -> bool:
    if not robots_body:
        return False
    # Simple parse: User-agent: Bot ... Disallow: /
    blocks = False
    current = False
    for line in robots_body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lower = line.lower()
        if lower.startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current = agent == "*" or agent.lower() == bot.lower()
        elif current and lower.startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path == "/":
                blocks = True
    return blocks


def _schema_types(schema: list) -> set[str]:
    types: set[str] = set()
    for block in schema or []:
        if not isinstance(block, dict):
            continue
        t = block.get("@type")
        if isinstance(t, list):
            types.update(str(x) for x in t)
        elif t:
            types.add(str(t))
    return types


def _extract_name(page: dict[str, Any]) -> str | None:
    for block in page.get("schema_jsonld") or []:
        if isinstance(block, dict) and block.get("name"):
            return str(block["name"]).strip()
    title = (page.get("title") or "").strip()
    if title:
        # Take part before | or -
        return re.split(r"\s[\|\-–—]\s", title)[0].strip() or title
    return None


def run_geo(
    pages: list[dict[str, Any]],
    robots_body: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (checks, entity_payload)."""
    checks: list[dict[str, Any]] = []
    if not pages:
        return checks, {}

    home = next((p for p in pages if p.get("is_homepage")), pages[0])
    body = home.get("body_text") or ""
    schema = home.get("schema_jsonld") or []
    url = home.get("url")
    combined = "\n".join((p.get("body_text") or "") for p in pages)

    # AI bots blocked
    blocked_bots = [b for b in AI_BOTS if _bot_blocked(robots_body, b)]
    checks.append(
        _check(
            category="AI Access",
            check_id="geo.ai_bots_blocked",
            severity="Warning",
            title="AI crawler access",
            message=(
                f"Blocked AI bots in robots.txt: {', '.join(blocked_bots)}. "
                "This can reduce how AI tools discover and cite the site."
                if blocked_bots
                else "No blanket Disallow:/ found for common AI bots (GPTBot, PerplexityBot, ClaudeBot)."
            ),
            passed=len(blocked_bots) == 0,
            page_url=url,
        )
    )

    types = _schema_types(schema)
    has_org = bool(types & {"Organization", "LocalBusiness", "Store", "Corporation"})
    checks.append(
        _check(
            category="Structured Data",
            check_id="geo.org_schema",
            severity="Warning",
            title="Organization / LocalBusiness schema",
            message="Organization or LocalBusiness schema found."
            if has_org
            else "No Organization/LocalBusiness JSON-LD found — AI tools get fewer clear entity cues.",
            passed=has_org,
            page_url=url,
        )
    )

    # Trust signals
    trust_hits = {
        "about": bool(re.search(r"\babout\b", combined, re.I)),
        "contact": bool(re.search(r"\bcontact\b", combined, re.I)),
        "author": bool(re.search(r"\b(author|written by|meet the team)\b", combined, re.I)),
    }
    trust_score = sum(trust_hits.values())
    checks.append(
        _check(
            category="Trust",
            check_id="geo.trust_signals",
            severity="Warning",
            title="About / Contact / Author signals",
            message=f"Trust signals found: {', '.join(k for k,v in trust_hits.items() if v) or 'none'}.",
            passed=trust_score >= 2,
            page_url=url,
        )
    )

    # Specific facts vs vague claims
    vague = len(re.findall(r"\b(best|leading|top|world.?class|#1|guaranteed)\b", body, re.I))
    specific = len(EMAIL_RE.findall(body)) + len(PHONE_RE.findall(body)) + len(CITY_HINTS.findall(body))
    checks.append(
        _check(
            category="Specificity",
            check_id="geo.specific_facts",
            severity="Info",
            title="Specific facts vs vague claims",
            message=f"Specific contact/location cues: {specific}; vague superlatives: {vague}.",
            passed=specific >= 1 and vague <= 5,
            page_url=url,
        )
    )

    # Last updated
    updated = bool(
        re.search(r"\b(last updated|updated on|published|©\s*\d{4})\b", combined, re.I)
    )
    checks.append(
        _check(
            category="Freshness",
            check_id="geo.last_updated",
            severity="Info",
            title="Last-updated / date signal",
            message="Found a date or last-updated style signal."
            if updated
            else "No clear last-updated date found on crawled pages.",
            passed=updated,
            page_url=url,
        )
    )

    # Brand consistency
    names = []
    phones = []
    emails = []
    for p in pages:
        n = _extract_name(p)
        if n:
            names.append(n)
        phones.extend(PHONE_RE.findall(p.get("body_text") or ""))
        emails.extend(EMAIL_RE.findall(p.get("body_text") or ""))

    brand_ok = True
    if len(names) >= 2:
        base = names[0]
        brand_ok = all(fuzz.token_set_ratio(base, n) >= 80 for n in names[1:])
    phone_ok = len(set(re.sub(r"\D", "", p) for p in phones if len(re.sub(r"\D", "", p)) >= 7)) <= 2
    checks.append(
        _check(
            category="Consistency",
            check_id="geo.brand_consistency",
            severity="Warning",
            title="Brand / NAP consistency",
            message="Business name and contact details look consistent across crawled pages."
            if brand_ok and phone_ok
            else "Inconsistent business name or phone patterns across pages — AI may learn conflicting facts.",
            passed=brand_ok and phone_ok,
            page_url=url,
        )
    )

    entity_payload = build_entity_graph(home, pages, robots_body)
    return checks, entity_payload


def build_entity_graph(
    home: dict[str, Any],
    pages: list[dict[str, Any]],
    robots_body: str | None,  # noqa: ARG001
) -> dict[str, Any]:
    body = home.get("body_text") or ""
    combined = "\n".join((p.get("body_text") or "") for p in pages)

    phones = sorted({p.strip() for p in PHONE_RE.findall(combined) if len(re.sub(r"\D", "", p)) >= 7})[:5]
    emails = sorted({e.lower() for e in EMAIL_RE.findall(combined)})[:5]
    cities = sorted({m.group(0) for m in CITY_HINTS.finditer(combined)})[:10]
    name = _extract_name(home) or urlparse(home.get("url") or "").netloc
    services = extract_business_services(body, home.get("title"))

    # Normalize near-duplicate names
    G = nx.DiGraph()
    G.add_node(name, entity_type="Business")
    for city in cities:
        G.add_node(city, entity_type="City")
        G.add_edge(name, city, relation="located_in")
    for phone in phones:
        G.add_node(phone, entity_type="Phone")
        G.add_edge(name, phone, relation="phone")
    for email in emails:
        G.add_node(email, entity_type="Email")
        G.add_edge(name, email, relation="email")
    for svc in services:
        G.add_node(svc, entity_type="Service")
        G.add_edge(name, svc, relation="sells")

    missing = []
    if not name or name == urlparse(home.get("url") or "").netloc:
        missing.append("business_name_clarity")
    if not phones:
        missing.append("phone")
    if not emails:
        missing.append("email")
    if not cities:
        missing.append("address_or_city")
    if not services:
        missing.append("services")
    if not re.search(r"\b(hours|open|mon|tue|wed|thu|fri|sat|sun)\b", combined, re.I):
        missing.append("hours")
    if not re.search(r"\b(serving|we serve|area served|delivery)\b", combined, re.I):
        missing.append("area_served")

    schema_draft: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
    }
    if name:
        schema_draft["name"] = name
    if phones:
        schema_draft["telephone"] = phones[0]
    if emails:
        schema_draft["email"] = emails[0]
    if cities:
        schema_draft["address"] = {
            "@type": "PostalAddress",
            "addressLocality": cities[0],
            "streetAddress": "[your confirmed street address]",
        }
    if services:
        schema_draft["makesOffer"] = [{"@type": "Offer", "itemOffered": s} for s in services[:5]]

    relations = [
        {"from": u, "to": v, "relation": d.get("relation")}
        for u, v, d in G.edges(data=True)
    ]

    return {
        "name": name,
        "entity_type": "Business",
        "attributes": {
            "phones": phones,
            "emails": emails,
            "cities": cities,
            "services": services,
            "limitation": (
                "City detection uses regex for known place names; small local / Roman Urdu names "
                "may be missed without spaCy custom models + LLM assist."
            ),
        },
        "relations": relations,
        "missing": missing,
        "graph_summary": {
            "nodes": list(G.nodes(data=True)),
            "edges": relations,
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
        },
        "schema_draft": schema_draft,
    }

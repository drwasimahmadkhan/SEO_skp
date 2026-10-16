from __future__ import annotations

import re
from collections import Counter
from typing import Any

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import textstat
except ImportError:  # pragma: no cover
    textstat = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z]{3,}", (text or "").lower())


def analyze_content(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return SEO Content-category checks from NLP signals."""
    checks: list[dict[str, Any]] = []
    texts = []
    for page in pages:
        if page.get("status_code") and page["status_code"] >= 400:
            continue
        body = page.get("body_text") or ""
        texts.append((page, body))

    if not texts:
        return checks

    # Readability on homepage
    home, home_body = texts[0]
    url = home.get("url")
    if textstat and home_body.strip():
        try:
            flesch = textstat.flesch_reading_ease(home_body[:5000])
            ok = flesch >= 50
            checks.append(
                {
                    "pillar": "SEO",
                    "category": "Content",
                    "check_id": "nlp.readability",
                    "severity": "Info",
                    "weight": 1,
                    "title": "Readability (Flesch)",
                    "message": f"Flesch reading ease ≈ {flesch:.0f}. "
                    + ("Aim for ~50+ for general audiences." if not ok else "Looks reasonably readable."),
                    "passed": ok,
                    "page_url": url,
                }
            )
        except Exception:
            pass

    # Title vs content overlap
    title = (home.get("title") or "").strip()
    if title and home_body:
        title_tokens = set(_tokenize(title))
        body_tokens = set(_tokenize(home_body[:3000]))
        if title_tokens:
            overlap = len(title_tokens & body_tokens) / len(title_tokens)
            ok = overlap >= 0.3
            checks.append(
                {
                    "pillar": "SEO",
                    "category": "Content",
                    "check_id": "nlp.title_content_match",
                    "severity": "Warning",
                    "weight": 2,
                    "title": "Title vs content match",
                    "message": f"About {overlap:.0%} of title words appear in the page body."
                    + ("" if ok else " Title and body may be misaligned."),
                    "passed": ok,
                    "page_url": url,
                }
            )

    # Keyword density (top terms — informational, warn if one word > 5%)
    tokens = _tokenize(home_body)
    if len(tokens) >= 50:
        counts = Counter(tokens)
        top_word, top_count = counts.most_common(1)[0]
        density = top_count / len(tokens)
        ok = density <= 0.05
        checks.append(
            {
                "pillar": "SEO",
                "category": "Content",
                "check_id": "nlp.keyword_density",
                "severity": "Info",
                "weight": 1,
                "title": "Keyword density",
                "message": f"Top term '{top_word}' appears at {density:.1%} density."
                + ("" if ok else " Very high repetition can look spammy."),
                "passed": ok,
                "page_url": url,
            }
        )

    # Duplicate content across pages (TF-IDF when available)
    if len(texts) >= 2:
        bodies = [b[:4000] for _, b in texts if b.strip()]
        if len(bodies) >= 2 and TfidfVectorizer is not None:
            try:
                vec = TfidfVectorizer(stop_words="english", max_features=2000)
                matrix = vec.fit_transform(bodies)
                sim = cosine_similarity(matrix)
                dup_pairs = 0
                n = sim.shape[0]
                for i in range(n):
                    for j in range(i + 1, n):
                        if sim[i, j] >= 0.92:
                            dup_pairs += 1
                checks.append(
                    {
                        "pillar": "SEO",
                        "category": "Content",
                        "check_id": "nlp.duplicate_content",
                        "severity": "Warning",
                        "weight": 2,
                        "title": "Near-duplicate pages",
                        "message": f"Found {dup_pairs} near-duplicate page pair(s) (cosine ≥ 0.92)."
                        if dup_pairs
                        else "No near-duplicate page pairs detected among crawled pages.",
                        "passed": dup_pairs == 0,
                        "page_url": None,
                    }
                )
            except Exception:
                pass
        elif len(bodies) >= 2:
            # Jaccard fallback without sklearn
            def toks(t: str) -> set[str]:
                return set(_tokenize(t))

            dup_pairs = 0
            for i in range(len(bodies)):
                for j in range(i + 1, len(bodies)):
                    a, b = toks(bodies[i]), toks(bodies[j])
                    if not a or not b:
                        continue
                    if len(a & b) / len(a | b) >= 0.85:
                        dup_pairs += 1
            checks.append(
                {
                    "pillar": "SEO",
                    "category": "Content",
                    "check_id": "nlp.duplicate_content",
                    "severity": "Warning",
                    "weight": 2,
                    "title": "Near-duplicate pages",
                    "message": f"Found {dup_pairs} near-duplicate page pair(s) (Jaccard ≥ 0.85)."
                    if dup_pairs
                    else "No near-duplicate page pairs detected among crawled pages.",
                    "passed": dup_pairs == 0,
                    "page_url": None,
                }
            )

    # Thin content
    word_count = len(tokens)
    checks.append(
        {
            "pillar": "SEO",
            "category": "Content",
            "check_id": "nlp.thin_content",
            "severity": "Warning",
            "weight": 2,
            "title": "Content length",
            "message": f"Homepage body has ~{word_count} words."
            + (" Thin pages may struggle to answer visitor questions." if word_count < 150 else ""),
            "passed": word_count >= 150,
            "page_url": url,
        }
    )

    # Simple search-intent signal: presence of question words / how-to
    intent_hits = len(
        re.findall(r"\b(how to|what is|why|guide|pricing|contact|services)\b", home_body, re.I)
    )
    checks.append(
        {
            "pillar": "SEO",
            "category": "Content",
            "check_id": "nlp.search_intent",
            "severity": "Info",
            "weight": 1,
            "title": "Intent clarity signals",
            "message": f"Found {intent_hits} intent-related phrases (how-to, pricing, services, etc.)."
            if intent_hits
            else "Few clear intent phrases detected; consider stating what the page helps visitors do.",
            "passed": intent_hits >= 1,
            "page_url": url,
        }
    )

    return checks

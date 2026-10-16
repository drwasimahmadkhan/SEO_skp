from __future__ import annotations

from typing import Any

SEVERITY_POINTS = {"Critical": 3, "Warning": 2, "Info": 1}

# Pillar weights for overall
PILLAR_WEIGHTS = {"SEO": 0.70, "AEO": 0.15, "GEO": 0.15}

# SEO subcategory weights (sum = 70 of overall; used to weight within SEO)
SEO_CATEGORY_WEIGHTS = {
    "On-page": 20,
    "Content": 15,
    "Technical": 15,
    "Performance": 10,
    "Images and Links": 10,
}


def grade_for(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Needs Work"
    return "Poor"


def category_score(checks: list[dict[str, Any]]) -> float:
    """Severity-weighted percentage of passed checks. Empty => 100."""
    if not checks:
        return 100.0
    total = 0
    earned = 0
    for c in checks:
        pts = SEVERITY_POINTS.get(c.get("severity", "Warning"), 2)
        total += pts
        if c.get("passed"):
            earned += pts
    if total == 0:
        return 100.0
    return round(100.0 * earned / total, 1)


def compute_scores(all_checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute pillar and overall scores from check results (passed + failed)."""
    by_pillar: dict[str, list] = {"SEO": [], "AEO": [], "GEO": []}
    by_seo_cat: dict[str, list] = {k: [] for k in SEO_CATEGORY_WEIGHTS}

    for c in all_checks:
        pillar = c.get("pillar", "SEO")
        by_pillar.setdefault(pillar, []).append(c)
        if pillar == "SEO":
            cat = c.get("category", "On-page")
            by_seo_cat.setdefault(cat, []).append(c)

    seo_cats = {}
    seo_weighted = 0.0
    seo_weight_sum = 0.0
    for cat, weight in SEO_CATEGORY_WEIGHTS.items():
        s = category_score(by_seo_cat.get(cat, []))
        seo_cats[cat] = s
        seo_weighted += s * weight
        seo_weight_sum += weight
    seo = round(seo_weighted / seo_weight_sum, 1) if seo_weight_sum else 100.0

    aeo = category_score(by_pillar.get("AEO", []))
    geo = category_score(by_pillar.get("GEO", []))

    overall = round(
        seo * PILLAR_WEIGHTS["SEO"]
        + aeo * PILLAR_WEIGHTS["AEO"]
        + geo * PILLAR_WEIGHTS["GEO"],
        1,
    )

    return {
        "overall": overall,
        "seo": seo,
        "aeo": aeo,
        "geo": geo,
        "grade": grade_for(overall),
        "breakdown": {
            "seo_categories": seo_cats,
            "pillar_weights": PILLAR_WEIGHTS,
            "severity_points": SEVERITY_POINTS,
            "failed_checks": [
                {
                    "check_id": c["check_id"],
                    "pillar": c["pillar"],
                    "category": c["category"],
                    "severity": c["severity"],
                    "weight": SEVERITY_POINTS.get(c["severity"], 2),
                    "title": c["title"],
                }
                for c in all_checks
                if not c.get("passed")
            ],
        },
    }

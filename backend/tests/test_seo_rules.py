"""books.toscrape.com-style expectations from the project brief."""

from app.services.seo_rules import run_seo_rules
from app.services.scoring import compute_scores


def _books_like_homepage():
    return {
        "url": "https://books.toscrape.com/",
        "final_url": "https://books.toscrape.com/",
        "status_code": 200,
        "title": "All products | Books to Scrape - Sandbox",
        "meta_description": "",
        "meta_description_present": True,
        "canonical": None,
        "viewport": "width=device-width, initial-scale=1",
        "robots_meta": None,
        "headings": {"h1": ["All products"], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []},
        "images": [{"src": "/img.jpg", "alt": "Book", "alt_missing": False, "alt_empty": False}],
        "links": [
            {
                "href": "https://books.toscrape.com/catalogue/page-2.html",
                "text": "next",
                "is_internal": True,
            }
        ],
        "schema_jsonld": [],
        "body_text": "Welcome to a fake book store used for scraping practice. " * 20,
        "load_ms": 400,
        "is_homepage": True,
        "depth": 0,
    }


def test_books_toscrape_expected_failures(monkeypatch):
    # Skip live HEAD checks for broken links
    monkeypatch.setattr(
        "app.services.seo_rules._sample_broken_links",
        lambda page: [
            {
                "pillar": "SEO",
                "category": "Images and Links",
                "check_id": "seo.broken_links",
                "severity": "Critical",
                "weight": 3,
                "title": "Broken internal links",
                "message": "skipped",
                "passed": True,
                "page_url": page.get("url"),
            }
        ],
    )

    pages = [_books_like_homepage()]
    checks = run_seo_rules(pages, robots_status=404, sitemap_status=404)
    failed_ids = {c["check_id"] for c in checks if not c["passed"]}

    # Exactly the five issues from the brief (plus we may have length infos — assert core five)
    for required in [
        "seo.meta_empty",
        "seo.canonical_missing",
        "seo.schema",
        "seo.robots_missing",
        "seo.sitemap_missing",
    ]:
        assert required in failed_ids, f"missing expected failure {required}"

    # Should NOT treat missing meta as the issue when empty meta tag exists
    assert "seo.meta_missing" not in failed_ids

    # Title and H1 should pass
    assert "seo.title_missing" not in failed_ids
    assert "seo.h1_missing" not in failed_ids


def test_404_page_still_checked_as_http_error_first():
    page = _books_like_homepage()
    page["status_code"] = 404
    page["title"] = "Not Found"
    page["headings"] = {"h1": ["404"], "h2": [], "h3": [], "h4": [], "h5": [], "h6": []}
    checks = run_seo_rules([page], robots_status=200, sitemap_status=200)
    failed = [c for c in checks if not c["passed"]]
    assert any(c["check_id"] == "seo.http_error" for c in failed)
    # Should not also flag title missing on 404 path evaluation for that page's title checks
    # (we skip on-page checks when status >= 400)
    assert not any(c["check_id"] == "seo.title_missing" and c["page_url"] == page["url"] for c in failed)


def test_robots_meta_only_noindex_blocks():
    page = _books_like_homepage()
    page["meta_description"] = "A fine description of books for sale on this sandbox site."
    page["meta_description_present"] = True
    page["canonical"] = "https://books.toscrape.com/"
    page["schema_jsonld"] = [{"@type": "WebSite"}]
    page["robots_meta"] = "NOARCHIVE, NOCACHE"
    checks = run_seo_rules([page], robots_status=200, sitemap_status=200)
    noindex = next(c for c in checks if c["check_id"] == "seo.noindex")
    assert noindex["passed"] is True

    page["robots_meta"] = "noindex, follow"
    checks2 = run_seo_rules([page], robots_status=200, sitemap_status=200)
    noindex2 = next(c for c in checks2 if c["check_id"] == "seo.noindex")
    assert noindex2["passed"] is False


def test_scoring_explainable():
    checks = [
        {
            "pillar": "SEO",
            "category": "On-page",
            "check_id": "a",
            "severity": "Critical",
            "passed": True,
            "title": "a",
        },
        {
            "pillar": "SEO",
            "category": "On-page",
            "check_id": "b",
            "severity": "Critical",
            "passed": False,
            "title": "b",
        },
        {
            "pillar": "AEO",
            "category": "Answerability",
            "check_id": "c",
            "severity": "Warning",
            "passed": True,
            "title": "c",
        },
        {
            "pillar": "GEO",
            "category": "Trust",
            "check_id": "d",
            "severity": "Warning",
            "passed": True,
            "title": "d",
        },
    ]
    # Fill remaining SEO categories with passing checks so SEO isn't zeroed oddly
    for cat in ["Content", "Technical", "Performance", "Images and Links"]:
        checks.append(
            {
                "pillar": "SEO",
                "category": cat,
                "check_id": f"ok-{cat}",
                "severity": "Info",
                "passed": True,
                "title": "ok",
            }
        )
    scores = compute_scores(checks)
    assert "failed_checks" in scores["breakdown"]
    assert scores["breakdown"]["failed_checks"][0]["check_id"] == "b"
    assert 0 <= scores["overall"] <= 100

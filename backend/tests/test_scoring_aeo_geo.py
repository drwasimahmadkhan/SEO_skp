from app.services.aeo import run_aeo
from app.services.geo import run_geo
from app.services.nlp import analyze_content


def test_aeo_answerability_marks_missing():
    pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "title": "Acme Plumbing",
            "body_text": "Acme Plumbing fixes leaks in Karachi. Call us today.",
            "schema_jsonld": [],
            "is_homepage": True,
        }
    ]
    checks, questions = run_aeo(pages)
    assert questions
    assert any(q["answerability"] in ("Clear", "Partial", "No answer") for q in questions)
    assert any(c["check_id"] == "aeo.answer_coverage" for c in checks)


def test_geo_entity_missing_list():
    pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "title": "Green Leaf Cafe",
            "body_text": "Welcome to Green Leaf Cafe in Lahore. Email hello@greenleaf.test",
            "schema_jsonld": [],
            "is_homepage": True,
        }
    ]
    checks, entity = run_geo(pages, robots_body=None)
    assert entity["name"]
    assert "email" in entity["attributes"]["emails"][0] or entity["attributes"]["emails"]
    assert isinstance(entity["missing"], list)
    assert any(c["pillar"] == "GEO" for c in checks)


def test_nlp_thin_content():
    pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "title": "Hi",
            "body_text": "short",
            "is_homepage": True,
        }
    ]
    checks = analyze_content(pages)
    thin = next(c for c in checks if c["check_id"] == "nlp.thin_content")
    assert thin["passed"] is False

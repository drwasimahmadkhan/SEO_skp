from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Audit, Entity, Issue, Page, Question, Recommendation, Score
from app.services.aeo import run_aeo
from app.services.crawler import crawl_site
from app.services.geo import run_geo
from app.services.llm import generate_recommendations, rule_based_recommendations
from app.services.nlp import analyze_content
from app.services.scoring import compute_scores
from app.services.seo_rules import run_seo_rules
from app.database import SessionLocal


def _update(db: Session, audit: Audit, **kwargs: Any) -> None:
    for k, v in kwargs.items():
        setattr(audit, k, v)
    audit.updated_at = datetime.utcnow()
    db.commit()


def run_audit_job(audit_id: str) -> None:
    db = SessionLocal()
    try:
        audit = db.get(Audit, audit_id)
        if not audit:
            return
        _update(db, audit, status="crawling", progress=5, progress_message="Starting crawl")

        def on_progress(pct: int, msg: str) -> None:
            a = db.get(Audit, audit_id)
            if a:
                _update(db, a, progress=max(5, min(pct, 55)), progress_message=msg)

        crawl = crawl_site(audit.normalized_url, on_progress=on_progress)
        audit = db.get(Audit, audit_id)
        if not audit:
            return
        audit.robots_txt_status = crawl.robots_status
        audit.sitemap_status = crawl.sitemap_status
        audit.robots_txt_body = crawl.robots_body

        page_rows: list[Page] = []
        for pdata in crawl.pages:
            page = Page(
                audit_id=audit.id,
                url=pdata["url"],
                final_url=pdata.get("final_url"),
                status_code=pdata.get("status_code"),
                title=pdata.get("title"),
                meta_description=pdata.get("meta_description"),
                meta_description_present=bool(pdata.get("meta_description_present")),
                canonical=pdata.get("canonical"),
                viewport=pdata.get("viewport"),
                robots_meta=pdata.get("robots_meta"),
                headings=pdata.get("headings"),
                images=pdata.get("images"),
                links=pdata.get("links"),
                schema_jsonld=pdata.get("schema_jsonld"),
                body_text=pdata.get("body_text"),
                load_ms=pdata.get("load_ms"),
                is_homepage=bool(pdata.get("is_homepage")),
                depth=int(pdata.get("depth") or 0),
            )
            db.add(page)
            page_rows.append(page)
        db.commit()
        for p in page_rows:
            db.refresh(p)

        url_to_page_id = {p.url: p.id for p in page_rows}

        _update(db, audit, status="analyzing", progress=60, progress_message="Running SEO rules")

        all_checks: list[dict[str, Any]] = []
        all_checks.extend(
            run_seo_rules(crawl.pages, crawl.robots_status, crawl.sitemap_status)
        )
        _update(db, audit, progress=68, progress_message="Running NLP content checks")
        all_checks.extend(analyze_content(crawl.pages))

        _update(db, audit, progress=75, progress_message="Running AEO answerability")
        aeo_checks, questions = run_aeo(crawl.pages)
        all_checks.extend(aeo_checks)

        _update(db, audit, progress=82, progress_message="Running GEO + entity graph")
        geo_checks, entity_payload = run_geo(crawl.pages, crawl.robots_body)
        all_checks.extend(geo_checks)

        # Persist issues (failed + passed for explainability; UI filters failed)
        issue_by_check: dict[str, Issue] = {}
        for c in all_checks:
            page_id = url_to_page_id.get(c.get("page_url") or "")
            issue = Issue(
                audit_id=audit.id,
                page_id=page_id,
                pillar=c["pillar"],
                category=c["category"],
                check_id=c["check_id"],
                severity=c["severity"],
                weight=c.get("weight", 2),
                title=c["title"],
                message=c["message"],
                passed=bool(c.get("passed")),
            )
            db.add(issue)
            issue_by_check[c["check_id"]] = issue
        db.flush()

        for q in questions:
            db.add(
                Question(
                    audit_id=audit.id,
                    page_id=url_to_page_id.get(q.get("page_url") or ""),
                    question=q["question"],
                    answerability=q["answerability"],
                    evidence=q.get("evidence"),
                    suggested_rewrite=q.get("suggested_rewrite"),
                    source=q.get("source") or "rules",
                )
            )

        if entity_payload:
            db.add(
                Entity(
                    audit_id=audit.id,
                    name=entity_payload.get("name") or "Unknown",
                    entity_type=entity_payload.get("entity_type") or "Business",
                    attributes=entity_payload.get("attributes"),
                    relations=entity_payload.get("relations"),
                    missing=entity_payload.get("missing"),
                    graph_summary=entity_payload.get("graph_summary"),
                    schema_draft=entity_payload.get("schema_draft"),
                )
            )

        _update(db, audit, progress=90, progress_message="Generating recommendations")
        failed = [c for c in all_checks if not c.get("passed")]
        home_body = ""
        if crawl.pages:
            home_body = crawl.pages[0].get("body_text") or ""

        llm_recs = generate_recommendations(failed, home_body)
        if llm_recs:
            source = "llm"
            recs = llm_recs
        else:
            source = "rules"
            recs = rule_based_recommendations(failed)

        for r in recs:
            cid = r.get("check_id")
            issue = issue_by_check.get(cid) if cid else None
            if not r.get("text"):
                continue
            db.add(
                Recommendation(
                    audit_id=audit.id,
                    issue_id=issue.id if issue else None,
                    source=source,
                    text=r["text"],
                    is_quick_win=bool(r.get("is_quick_win")),
                )
            )

        scores = compute_scores(all_checks)
        db.add(
            Score(
                audit_id=audit.id,
                overall=scores["overall"],
                seo=scores["seo"],
                aeo=scores["aeo"],
                geo=scores["geo"],
                grade=scores["grade"],
                breakdown=scores["breakdown"],
            )
        )

        audit = db.get(Audit, audit_id)
        if audit:
            audit.status = "done"
            audit.progress = 100
            audit.progress_message = "Complete"
            audit.completed_at = datetime.utcnow()
            db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        audit = db.get(Audit, audit_id)
        if audit:
            audit.status = "failed"
            audit.error_message = str(exc)
            audit.progress_message = "Failed"
            audit.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

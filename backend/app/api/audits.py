from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Audit
from app.schemas import (
    AuditCreate,
    AuditStatusOut,
    CompareOut,
    EntityOut,
    IssueOut,
    PageSummaryOut,
    QuestionOut,
    RecommendationOut,
    ReportOut,
    ScoreOut,
)
from app.services.audit_runner import run_audit_job
from app.services.pdf_report import build_pdf
from app.utils.url_validator import URLValidationError, validate_and_normalize

router = APIRouter(prefix="/api/audits", tags=["audits"])


def _session_id(x_session_id: str | None = Header(default=None, alias="X-Session-Id")) -> str:
    if not x_session_id or len(x_session_id) < 8:
        raise HTTPException(status_code=400, detail="X-Session-Id header required (anonymous UUID).")
    return x_session_id.strip()


def _get_owned_audit(db: Session, audit_id: str, session_id: str) -> Audit:
    audit = db.get(Audit, audit_id)
    if not audit or audit.session_id != session_id:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return audit


@router.post("", response_model=AuditStatusOut)
def create_audit(
    payload: AuditCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> Audit:
    try:
        normalized, final_url, _status = validate_and_normalize(payload.url)
    except URLValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    audit = Audit(
        session_id=session_id,
        url=payload.url.strip(),
        normalized_url=final_url or normalized,
        status="queued",
        progress=0,
        progress_message="Queued",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    background_tasks.add_task(run_audit_job, audit.id)
    return audit


@router.get("", response_model=list[AuditStatusOut])
def list_audits(
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> list[Audit]:
    rows = db.scalars(
        select(Audit)
        .where(Audit.session_id == session_id)
        .order_by(Audit.created_at.desc())
        .limit(50)
    ).all()
    return list(rows)


@router.get("/{audit_id}", response_model=AuditStatusOut)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> Audit:
    return _get_owned_audit(db, audit_id, session_id)


def _load_report(db: Session, audit_id: str, session_id: str) -> Audit:
    audit = db.scalars(
        select(Audit)
        .where(Audit.id == audit_id, Audit.session_id == session_id)
        .options(
            selectinload(Audit.score),
            selectinload(Audit.issues),
            selectinload(Audit.recommendations),
            selectinload(Audit.questions),
            selectinload(Audit.entities),
            selectinload(Audit.pages),
        )
    ).first()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return audit


def _report_out(audit: Audit) -> ReportOut:
    return ReportOut(
        audit=AuditStatusOut.model_validate(audit),
        score=ScoreOut.model_validate(audit.score) if audit.score else None,
        issues=[IssueOut.model_validate(i) for i in audit.issues],
        recommendations=[RecommendationOut.model_validate(r) for r in audit.recommendations],
        questions=[QuestionOut.model_validate(q) for q in audit.questions],
        entities=[EntityOut.model_validate(e) for e in audit.entities],
        pages=[PageSummaryOut.model_validate(p) for p in audit.pages],
    )


@router.get("/{audit_id}/report", response_model=ReportOut)
def get_report(
    audit_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> ReportOut:
    audit = _load_report(db, audit_id, session_id)
    if audit.status != "done":
        raise HTTPException(status_code=409, detail=f"Audit status is {audit.status}.")
    return _report_out(audit)


@router.get("/{audit_id}/compare/{other_id}", response_model=CompareOut)
def compare_audits(
    audit_id: str,
    other_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> CompareOut:
    before = _load_report(db, audit_id, session_id)
    after = _load_report(db, other_id, session_id)
    if before.normalized_url.rstrip("/") != after.normalized_url.rstrip("/"):
        raise HTTPException(status_code=400, detail="Can only compare audits of the same URL.")
    if before.status != "done" or after.status != "done":
        raise HTTPException(status_code=409, detail="Both audits must be complete.")

    before_failed = {i.check_id for i in before.issues if not i.passed}
    after_failed = {i.check_id for i in after.issues if not i.passed}
    resolved = sorted(before_failed - after_failed)
    new_issues = sorted(after_failed - before_failed)

    def delta(attr: str) -> float:
        b = getattr(before.score, attr) if before.score else 0
        a = getattr(after.score, attr) if after.score else 0
        return round(a - b, 1)

    return CompareOut(
        before=_report_out(before),
        after=_report_out(after),
        score_delta={
            "overall": delta("overall"),
            "seo": delta("seo"),
            "aeo": delta("aeo"),
            "geo": delta("geo"),
        },
        resolved_issue_ids=resolved,
        new_issue_ids=new_issues,
    )


@router.get("/{audit_id}/pdf")
def download_pdf(
    audit_id: str,
    db: Session = Depends(get_db),
    session_id: str = Depends(_session_id),
) -> Response:
    audit = _load_report(db, audit_id, session_id)
    if audit.status != "done":
        raise HTTPException(status_code=409, detail="PDF available only for completed audits.")
    pdf_bytes = build_pdf(audit)
    date_stamp = (audit.completed_at or audit.created_at).strftime("%Y%m%d")
    filename = f"audit-report-{date_stamp}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class AuditCreate(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)


class AuditStatusOut(BaseModel):
    id: str
    session_id: str
    url: str
    normalized_url: str
    status: str
    progress: int
    progress_message: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class IssueOut(BaseModel):
    id: str
    pillar: str
    category: str
    check_id: str
    severity: str
    weight: int
    title: str
    message: str
    passed: bool
    page_id: str | None = None

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: str
    issue_id: str | None
    source: str
    text: str
    is_quick_win: bool

    model_config = {"from_attributes": True}


class ScoreOut(BaseModel):
    overall: float
    seo: float
    aeo: float
    geo: float
    grade: str
    breakdown: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class QuestionOut(BaseModel):
    id: str
    page_id: str | None
    question: str
    answerability: str
    evidence: str | None
    suggested_rewrite: str | None
    source: str

    model_config = {"from_attributes": True}


class EntityOut(BaseModel):
    id: str
    name: str
    entity_type: str
    attributes: dict[str, Any] | None
    relations: list[Any] | None
    missing: list[Any] | None
    graph_summary: dict[str, Any] | None
    schema_draft: dict[str, Any] | None

    model_config = {"from_attributes": True}


class PageSummaryOut(BaseModel):
    id: str
    url: str
    status_code: int | None
    title: str | None
    is_homepage: bool
    load_ms: float | None

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    audit: AuditStatusOut
    score: ScoreOut | None
    issues: list[IssueOut]
    recommendations: list[RecommendationOut]
    questions: list[QuestionOut]
    entities: list[EntityOut]
    pages: list[PageSummaryOut]
    disclaimer: str = (
        "These scores are our readiness assessment, not official Google rankings or AI citation "
        "scores. The system audits and recommends only — it does not fix your website."
    )


class CompareOut(BaseModel):
    before: ReportOut
    after: ReportOut
    score_delta: dict[str, float]
    resolved_issue_ids: list[str]
    new_issue_ids: list[str]

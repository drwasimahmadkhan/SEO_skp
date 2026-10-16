from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    normalized_url: Mapped[str] = mapped_column(String(2048), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[str] = mapped_column(String(255), default="Queued")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    robots_txt_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sitemap_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    robots_txt_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    pages: Mapped[list[Page]] = relationship(back_populates="audit", cascade="all, delete-orphan")
    issues: Mapped[list[Issue]] = relationship(back_populates="audit", cascade="all, delete-orphan")
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )
    score: Mapped[Score | None] = relationship(
        back_populates="audit", uselist=False, cascade="all, delete-orphan"
    )
    entities: Mapped[list[Entity]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )
    questions: Mapped[list[Question]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("audit_id", "url", name="uq_page_audit_url"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(2048))
    final_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_description_present: Mapped[bool] = mapped_column(Boolean, default=False)
    canonical: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    viewport: Mapped[str | None] = mapped_column(String(512), nullable=True)
    robots_meta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    headings: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    images: Mapped[list | None] = mapped_column(JSON, nullable=True)
    links: Mapped[list | None] = mapped_column(JSON, nullable=True)
    schema_jsonld: Mapped[list | None] = mapped_column(JSON, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    load_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_homepage: Mapped[bool] = mapped_column(Boolean, default=False)
    depth: Mapped[int] = mapped_column(Integer, default=0)

    audit: Mapped[Audit] = relationship(back_populates="pages")
    issues: Mapped[list[Issue]] = relationship(back_populates="page")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(
        ForeignKey("pages.id", ondelete="SET NULL"), nullable=True
    )
    pillar: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    check_id: Mapped[str] = mapped_column(String(128), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    weight: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)

    audit: Mapped[Audit] = relationship(back_populates="issues")
    page: Mapped[Page | None] = relationship(back_populates="issues")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="issue")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    issue_id: Mapped[str | None] = mapped_column(
        ForeignKey("issues.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[str] = mapped_column(String(16), default="rules")
    text: Mapped[str] = mapped_column(Text)
    is_quick_win: Mapped[bool] = mapped_column(Boolean, default=False)

    audit: Mapped[Audit] = relationship(back_populates="recommendations")
    issue: Mapped[Issue | None] = relationship(back_populates="recommendations")


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(
        ForeignKey("audits.id", ondelete="CASCADE"), unique=True, index=True
    )
    overall: Mapped[float] = mapped_column(Float, default=0)
    seo: Mapped[float] = mapped_column(Float, default=0)
    aeo: Mapped[float] = mapped_column(Float, default=0)
    geo: Mapped[float] = mapped_column(Float, default=0)
    grade: Mapped[str] = mapped_column(String(32), default="Poor")
    breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    audit: Mapped[Audit] = relationship(back_populates="score")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(512))
    entity_type: Mapped[str] = mapped_column(String(64))
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    relations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    missing: Mapped[list | None] = mapped_column(JSON, nullable=True)
    graph_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    schema_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    audit: Mapped[Audit] = relationship(back_populates="entities")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    audit_id: Mapped[str] = mapped_column(ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    page_id: Mapped[str | None] = mapped_column(
        ForeignKey("pages.id", ondelete="SET NULL"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text)
    answerability: Mapped[str] = mapped_column(String(32))
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_rewrite: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="rules")

    audit: Mapped[Audit] = relationship(back_populates="questions")

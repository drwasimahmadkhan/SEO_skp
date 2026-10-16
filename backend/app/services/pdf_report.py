from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Audit


def build_pdf(audit: Audit) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Audit Report — {audit.url}")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleCustom",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
    )
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=9, textColor=colors.grey)

    story = []
    stamp = (audit.completed_at or audit.created_at or datetime.utcnow()).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    story.append(Paragraph("Website Readiness Audit Report", title_style))
    story.append(Paragraph(f"<b>URL:</b> {escape(audit.url)}", body))
    story.append(Paragraph(f"<b>Audit date:</b> {stamp}", body))
    story.append(Paragraph(f"<b>Audit ID:</b> {escape(audit.id)}", body))
    story.append(Spacer(1, 0.2 * inch))

    score = audit.score
    if score:
        data = [
            ["Overall", "SEO", "AEO", "GEO", "Grade"],
            [
                f"{score.overall:.0f}",
                f"{score.seo:.0f}",
                f"{score.aeo:.0f}",
                f"{score.geo:.0f}",
                score.grade,
            ],
        ]
        table = Table(data, colWidths=[1.1 * inch] * 5)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f0f4f8")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Issues", styles["Heading2"]))
    failed = [i for i in audit.issues if not i.passed]
    if not failed:
        story.append(Paragraph("No failed checks recorded.", body))
    else:
        for issue in failed[:60]:
            story.append(
                Paragraph(
                    f"<b>[{escape(issue.severity)}] {escape(issue.pillar)}/{escape(issue.category)}</b>"
                    f" — {escape(issue.title)}",
                    body,
                )
            )
            story.append(Paragraph(escape(issue.message), small))
            story.append(Spacer(1, 0.08 * inch))

    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Recommendations", styles["Heading2"]))
    for rec in (audit.recommendations or [])[:40]:
        badge = "Quick win: " if rec.is_quick_win else ""
        story.append(Paragraph(f"• {escape(badge + rec.text)}", body))

    story.append(Spacer(1, 0.3 * inch))
    story.append(
        Paragraph(
            "Disclaimer: These scores are our readiness assessment (best-practice signals), "
            "not official Google rankings or AI citation scores. This report audits and recommends "
            "only — it does not fix your website, guarantee rankings, or invent business facts.",
            small,
        )
    )

    doc.build(story)
    return buffer.getvalue()

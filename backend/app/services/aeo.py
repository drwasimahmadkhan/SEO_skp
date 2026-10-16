from __future__ import annotations

import re
from typing import Any

from app.services.llm import generate_visitor_questions, llm_available


def _check(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("pillar", "AEO")
    kwargs.setdefault("weight", {"Critical": 3, "Warning": 2, "Info": 1}.get(kwargs.get("severity", "Warning"), 2))
    return kwargs


def _has_faq_signals(text: str, schema: list) -> bool:
    if re.search(r"\bfaq\b|frequently asked|q&a|questions?\s*&?\s*answers?", text, re.I):
        return True
    for block in schema or []:
        t = block.get("@type") if isinstance(block, dict) else None
        if t == "FAQPage" or (isinstance(t, list) and "FAQPage" in t):
            return True
    return False


def _answerability(question: str, body: str) -> tuple[str, str | None]:
    """Heuristic: Clear / Partial / No answer based on keyword overlap."""
    q_tokens = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    stop = {"what", "when", "where", "which", "does", "do", "the", "and", "for", "how", "are", "you", "your"}
    q_tokens -= stop
    if not q_tokens or not body:
        return "No answer", None
    body_l = body.lower()
    hits = [t for t in q_tokens if t in body_l]
    ratio = len(hits) / len(q_tokens)
    # Look for a sentence containing several tokens
    sentences = re.split(r"[.!?]\s+", body)
    best = None
    best_score = 0
    for s in sentences:
        sl = s.lower()
        score = sum(1 for t in q_tokens if t in sl)
        if score > best_score:
            best_score = score
            best = s.strip()
    if ratio >= 0.6 and best_score >= 2:
        return "Clear", best
    if ratio >= 0.35 or best_score >= 1:
        return "Partial", best
    return "No answer", None


def _default_questions(body: str, title: str | None) -> list[str]:
    topic = (title or "this business").strip()
    qs = [
        f"What does {topic} offer?",
        f"How can I contact {topic}?",
        f"Where is {topic} located?",
        f"What are the prices or fees for {topic}?",
        f"What are the opening hours for {topic}?",
    ]
    # Pull question-like lines from content
    for m in re.finditer(r"([A-Z][^.?!]{10,80}\?)", body[:4000]):
        qs.append(m.group(1).strip())
    # Dedupe preserve order
    seen = set()
    out = []
    for q in qs:
        key = q.lower()
        if key not in seen:
            seen.add(key)
            out.append(q)
    return out[:8]


def run_aeo(
    pages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (checks, questions)."""
    checks: list[dict[str, Any]] = []
    questions_out: list[dict[str, Any]] = []
    if not pages:
        return checks, questions_out

    home = next((p for p in pages if p.get("is_homepage")), pages[0])
    body = home.get("body_text") or ""
    schema = home.get("schema_jsonld") or []
    url = home.get("url")

    faq = _has_faq_signals(body, schema)
    checks.append(
        _check(
            category="Answerability",
            check_id="aeo.faq_present",
            severity="Warning",
            title="FAQ / Q&A signals",
            message="FAQ or Q&A section/schema detected." if faq else "No clear FAQ section or FAQPage schema found.",
            passed=faq,
            page_url=url,
        )
    )

    q_marks = len(re.findall(r"\?", body))
    checks.append(
        _check(
            category="Answerability",
            check_id="aeo.question_structure",
            severity="Info",
            title="Question-style content",
            message=f"Found {q_marks} question mark(s) in page text."
            if q_marks
            else "Page rarely uses question phrasing; visitors may not find direct answers.",
            passed=q_marks >= 1,
            page_url=url,
        )
    )

    # Generate questions
    source = "rules"
    if llm_available():
        generated = generate_visitor_questions(body, home.get("title"))
        if generated:
            qs = generated
            source = "llm"
        else:
            qs = _default_questions(body, home.get("title"))
    else:
        qs = _default_questions(body, home.get("title"))

    clear = partial = none = 0
    for q in qs:
        status, evidence = _answerability(q, body)
        if status == "Clear":
            clear += 1
            rewrite = None
        elif status == "Partial":
            partial += 1
            rewrite = (
                f"Expand the answer to: \"{q}\" with a short paragraph using only confirmed facts. "
                f"Use placeholders like [your confirmed lead time] for anything not on the page."
            )
        else:
            none += 1
            rewrite = (
                f"Add a clear answer for: \"{q}\". Only use facts from your business; "
                f"for unknown details write placeholders such as [your confirmed address] or [your confirmed lead time]."
            )
        questions_out.append(
            {
                "page_url": url,
                "question": q,
                "answerability": status,
                "evidence": evidence,
                "suggested_rewrite": rewrite,
                "source": source,
            }
        )

    total = max(len(qs), 1)
    answer_rate = (clear + 0.5 * partial) / total
    checks.append(
        _check(
            category="Answerability",
            check_id="aeo.answer_coverage",
            severity="Critical",
            title="Answer coverage",
            message=f"Of {total} visitor questions: {clear} Clear, {partial} Partial, {none} No answer.",
            passed=answer_rate >= 0.5,
            page_url=url,
        )
    )
    checks.append(
        _check(
            category="Answerability",
            check_id="aeo.clear_answers",
            severity="Warning",
            title="Clear answers",
            message=f"{clear} questions have a Clear answer on-page.",
            passed=clear >= max(1, total // 3),
            page_url=url,
        )
    )

    # Short direct sentences help AEO
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", body) if s.strip()]
    short = sum(1 for s in sentences[:40] if 40 <= len(s) <= 160)
    checks.append(
        _check(
            category="Answerability",
            check_id="aeo.clear_sentences",
            severity="Info",
            title="Answer-sized sentences",
            message=f"{short} sentences are a good length for direct answers (≈40–160 chars).",
            passed=short >= 3,
            page_url=url,
        )
    )

    return checks, questions_out

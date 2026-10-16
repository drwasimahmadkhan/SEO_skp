# Evaluation plan (issue correctness)

We do **not** compare our overall score to Ahrefs/Screaming Frog/Lighthouse scores. We check whether reported **issues** are correct.

## Procedure

1. Select 10–15 sites (good, weak, varied platforms) with permission.
2. Build ground truth with Lighthouse, browser View Source, and optionally Screaming Frog. Manual inspection wins disagreements.
3. Run ReadinessCheck; mark each issue TP / FP / FN.
4. Precision = TP/(TP+FP), Recall = TP/(TP+FN).
5. AEO/GEO: two reviewers, shared rubric; report “according to our rubric” + agreement.
6. AI suggestions: three raters, 1–5 for relevant / accurate / easy; count invented facts (target: zero).
7. Entities: hand-label 5–10 pages; precision/recall.
8. Before/after: fix a practice site and re-audit.

## Fixture: books.toscrape.com

Expect these failures (and not invent extras on clean checks):

- Empty meta description (tag present, blank content)
- Canonical missing
- No schema
- robots.txt missing (404 = Info)
- sitemap.xml missing

Lighthouse SEO may still be ~91 with a different audit set — that difference is expected.

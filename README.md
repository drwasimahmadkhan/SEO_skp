# SEO_skp — Website Readiness Audit (SEO · AEO · GEO)

**SEO_skp** helps small business owners understand what is wrong with their website — without expensive or overly technical SEO suites.

Enter a URL. The system crawls the site and returns:

- Three separate readiness scores: **SEO**, **AEO**, and **GEO**, plus an **overall** score  
- Plain-language reasons for every issue, with severity (**Critical** / **Warning** / **Info**)  
- Site-specific recommendations (local open-source LLM when available, otherwise rule-based)  
- Before/after comparison after you fix and re-audit  
- Audit history and a downloadable **PDF** report  

> **Think of it as a doctor:** it does the check-up and writes the prescription. Applying the fixes is your job.

---

## What this system does *not* do

- It does **not** fix your website  
- It does **not** guarantee Google rankings or AI citations  
- It does **not** invent business facts  
- It does **not** produce official Google scores  

Scores are **our own readiness assessment** based on best-practice signals — not ranking factors and not an official Google product.

---

## The three pillars

| Pillar | Question it answers |
|--------|---------------------|
| **SEO** (70%) | Can search engines find and understand the site? Titles, meta descriptions, headings, images/ALT, links, speed signals, robots, sitemap, schema |
| **AEO** (15%) | Does the site answer visitor questions clearly? Includes an **Answerability Analyzer** (Clear / Partial / No answer) |
| **GEO** (15%) | Can AI tools understand and cite the business? Schema, trust signals, AI bot access, brand consistency, plus an **Entity Graph** |

AEO, GEO, and LLMO are industry labels, not official Google ranking systems. Google still emphasizes solid basic SEO.

---

## Quick start

### Requirements

- Python 3.11+  
- Node.js 18+  
- (Optional) [Ollama](https://ollama.com) for LLM-written questions/recommendations  
- (Optional) Docker for PostgreSQL  

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy ..\.env.example ..\.env    # Windows
# cp ../.env.example ../.env    # macOS / Linux

uvicorn app.main:app --reload --port 8000
```

- API: http://127.0.0.1:8000  
- Interactive docs: http://127.0.0.1:8000/docs  

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173  

V1 uses an anonymous session ID in the browser (`localStorage`). No login is required yet.

### 3. Optional PostgreSQL

```bash
docker compose up -d
# Then set DATABASE_URL in .env to the Postgres URL from .env.example
```

---

## Features

**User**

- Enter URL with format / reachability / HTTPS checks  
- Live crawl & analysis progress  
- Overall + SEO / AEO / GEO scores with grades  
- Issue filters by severity and pillar  
- Quick Wins, AI/rule recommendations  
- AEO answerability tab  
- Entity Graph tab  
- PDF download (includes audit date)  
- History and before/after compare  

**Crawler**

- `robots.txt` and `sitemap.xml` parsing  
- Internal link discovery, dedupe, redirects  
- Page limit (default 25), delay, timeout  

---

## Scoring (explainable)

- **Weights:** SEO 70% · AEO 15% · GEO 15%  
- **Severity points:** Critical 3 · Warning 2 · Info 1  
- Category score = severity-weighted % of passed checks  
- **Grades:** 0–49 Poor · 50–74 Needs Work · 75–89 Good · 90+ Excellent  

Scores always come from **rules and measured checks**, never from the LLM. The LLM only generates text (questions, recommendations, drafts) and uses placeholders such as `[your confirmed lead time]` when a fact is missing.

---

## Tech stack

| Layer | Tools |
|-------|--------|
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI |
| Crawler | requests, BeautifulSoup |
| Database | SQLite (default) or PostgreSQL |
| NLP | textstat, rapidfuzz (optional scikit-learn) |
| Graph | NetworkX |
| LLM | Ollama (optional) |
| PDF | ReportLab |

---

## Project structure

```
SEO_skp/
├── backend/           # FastAPI API, crawler, rules, NLP, AEO, GEO, PDF
├── frontend/          # React UI
├── docs/              # HTML documentation (open docs/index.html)
├── docker-compose.yml # Optional Postgres
├── EVALUATION.md      # How we measure issue accuracy
└── README.md
```

---

## Documentation

Full product and developer documentation (English):

**[Open HTML docs → `docs/index.html`](docs/index.html)**

Topics covered: problem & solution, pillars, architecture, API, scoring, evaluation, and setup.

---

## Tests

```bash
cd backend
pytest -q
```

Worked example expectation for [books.toscrape.com](https://books.toscrape.com): empty meta description, missing canonical, no schema, missing robots.txt, missing sitemap.xml — without inventing failures on clean checks.

---

## Evaluation

We evaluate **issue correctness** (precision / recall), not score-vs-score against Ahrefs or Lighthouse alone. See [EVALUATION.md](EVALUATION.md).

---

## License & disclaimer

Built as an academic / open learning project for website readiness auditing.

This software audits and recommends only. Use results as guidance, not as a guarantee of search rankings or AI visibility.

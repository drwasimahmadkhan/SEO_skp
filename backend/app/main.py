from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audits import router as audits_router
from app.config import get_settings
from app.database import init_db

settings = get_settings()

app = FastAPI(
    title="SEO / AEO / GEO Audit API",
    description=(
        "Website readiness auditor. Scores are our own best-practice assessment, "
        "not official Google or AI-engine rankings."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audits_router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "seo-aeo-geo-audit"}

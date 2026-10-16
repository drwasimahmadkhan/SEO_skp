from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{ROOT / 'seo_audit.db'}"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    page_limit: int = 25
    request_delay_ms: int = 300
    request_timeout_sec: int = 15
    crawler_user_agent: str = "SEO-AEO-GEO-Auditor/1.0 (+local-audit)"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

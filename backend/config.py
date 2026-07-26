# backend/config.py

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "FarmerVerify AI"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # ── Directories ───────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    log_dir: str = "logs"
    max_file_size_mb: int = 10

    # ── File Upload ───────────────────────────────────────────────────────
    supported_extensions: List[str] = [".jpg", ".jpeg", ".png", ".webp"]

    # ── OCR / LLM Vision API ───────────────────────────────────────────────────
    ocr_mode: str = "mock"
    ocr_model: str = "gpt-4.1"
    ocr_api_url: str = ""
# Example: https://api.openai.com/v1/chat/completions
    ocr_api_key: str = ""
    ocr_max_tokens: int = 2000
    ocr_temperature: float = 0.1
    ocr_timeout: int = 60

    # ── Matching ──────────────────────────────────────────────────────────
    match_threshold_exact: float = 95.0
    match_threshold_good: float = 80.0
    match_threshold_partial: float = 60.0

    # ── Database ──────────────────────────────────────────────────────────
    database_mode: str = "mock"
    supabase_url: str = ""
    supabase_key: str = ""

    # ── Bots ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


def get_settings() -> Settings:
    """Return fresh Settings instance from .env."""
    return Settings()


def validate_settings() -> dict:
    s = get_settings()
    checks: dict = {}

    try:
        Path(s.upload_dir).mkdir(parents=True, exist_ok=True)
        checks["upload_dir"] = {"status": "pass", "path": s.upload_dir}
    except Exception as e:
        checks["upload_dir"] = {"status": "fail", "error": str(e)}

    try:
        Path(s.log_dir).mkdir(parents=True, exist_ok=True)
        checks["log_dir"] = {"status": "pass", "path": s.log_dir}
    except Exception as e:
        checks["log_dir"] = {"status": "fail", "error": str(e)}

    if s.ocr_mode == "live":
        if not s.ocr_api_key:
            checks["ocr"] = {
                "status": "fail",
                "error": "OCR_MODE=live but OCR_API_KEY is empty",
            }
        else:
            checks["ocr"] = {
                "status": "pass",
                "mode": "live",
                "model": s.ocr_model,
            }
    else:
        checks["ocr"] = {"status": "pass", "mode": "mock"}

    return checks
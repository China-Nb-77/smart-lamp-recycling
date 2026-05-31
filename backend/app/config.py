from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppSettings:
    base_dir: Path
    config_dir: Path
    redis_url: str
    database_url: str
    session_secret: str
    session_ttl_seconds: int
    request_timeout_seconds: float
    max_upload_bytes: int
    workflow_mode: str
    payment_mode: str
    allow_review_fallback: bool
    qna_url: str
    qna_timeout_seconds: float
    siliconflow_api_key: str
    siliconflow_base_url: str
    siliconflow_model: str
    siliconflow_temperature: float
    log_dir: Path
    allowed_origins: tuple[str, ...]

    @property
    def upload_dir(self) -> Path:
        return self.base_dir / "artifacts" / "uploads" / "agent-api"

    @property
    def frontend_dir(self) -> Path:
        return self.base_dir / "frontend"

    @property
    def allowed_mime_types(self) -> set[str]:
        return {"image/jpeg", "image/png", "image/webp"}

    @property
    def session_cookie_name(self) -> str:
        return "ai_light_session"

    def ensure_directories(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)


def load_settings() -> AppSettings:
    base_dir = Path(os.getenv("AI_LIGHT_BASE_DIR", Path(__file__).resolve().parents[2])).resolve()
    config_dir = Path(os.getenv("AI_LIGHT_CONFIG_DIR", base_dir / "configs")).resolve()
    allowed_origins_raw = os.getenv(
        "AI_LIGHT_ALLOWED_ORIGINS",
        "http://localhost,http://127.0.0.1,http://localhost:5173,http://127.0.0.1:5173,capacitor://localhost,ionic://localhost",
    )
    allowed_origins = tuple(item.strip() for item in allowed_origins_raw.split(",") if item.strip())
    settings = AppSettings(
        base_dir=base_dir,
        config_dir=config_dir,
        redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0").strip(),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/ai_light",
        ).strip(),
        session_secret=os.getenv("AI_LIGHT_SESSION_SECRET", "change-me-in-production").strip(),
        session_ttl_seconds=max(int(os.getenv("AI_LIGHT_SESSION_TTL_SECONDS", "86400")), 60),
        request_timeout_seconds=max(float(os.getenv("AI_LIGHT_REQUEST_TIMEOUT_SECONDS", "20")), 1.0),
        max_upload_bytes=max(int(os.getenv("AI_LIGHT_MAX_UPLOAD_BYTES", str(5 * 1024 * 1024))), 1024),
        workflow_mode=os.getenv("AI_LIGHT_WORKFLOW_MODE", "real").strip().lower() or "real",
        payment_mode=os.getenv("AI_LIGHT_PAYMENT_MODE", "mock").strip().lower() or "mock",
        allow_review_fallback=_env_bool("AI_LIGHT_ALLOW_REVIEW_FALLBACK", True),
        qna_url=os.getenv("AI_LIGHT_QNA_URL", "").strip(),
        qna_timeout_seconds=max(float(os.getenv("AI_LIGHT_QNA_TIMEOUT_SECONDS", "30")), 1.0),
        siliconflow_api_key=os.getenv("SILICONFLOW_API_KEY", "").strip(),
        siliconflow_base_url=(os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1").strip().rstrip("/")),
        siliconflow_model=os.getenv("SILICONFLOW_MODEL", "deepseek-ai/DeepSeek-V3").strip(),
        siliconflow_temperature=float(os.getenv("SILICONFLOW_TEMPERATURE", "0.2")),
        log_dir=(base_dir / "artifacts" / "logs"),
        allowed_origins=allowed_origins,
    )
    settings.ensure_directories()
    return settings

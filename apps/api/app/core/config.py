"""Application configuration.

All settings come from environment variables (see the root ``.env.example``).
A single cached :class:`Settings` instance is exposed via :func:`get_settings`.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root = .../apps/api/app/core/config.py -> parents[4]
_API_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _API_DIR.parent

# Tests set every value they need through environment variables (see
# ``app/tests/conftest.py``) and must stay hermetic: never let a developer's
# local ``.env`` leak real values (a cloud LLM base URL, credit limits, ...)
# into assertions. ``conftest`` sets ``APP_ENV=test`` before importing this.
_TESTING = os.environ.get("APP_ENV", "").lower() == "test" or "pytest" in sys.modules
_ENV_FILES = None if _TESTING else (_API_DIR / ".env", _REPO_ROOT / ".env")

_OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"


def resolve_llm_base_url(provider: str, base_url: str) -> str:
    """Pick a provider-appropriate base URL when one isn't set explicitly.

    ``ollama``/``local`` fall back to the local Ollama endpoint and ``nvidia``
    to NVIDIA NIM, but only while the generic OpenAI default is in place. An
    explicitly configured ``base_url`` always wins. Resolution uses the
    *active* provider, which may differ from the configured default.
    """
    if base_url and base_url != _OPENAI_DEFAULT_BASE_URL:
        return base_url
    if provider == "nvidia":
        return "https://integrate.api.nvidia.com/v1"
    if provider in ("ollama", "local"):
        return "http://localhost:11434/v1"
    return base_url


AppEnv = Literal["development", "staging", "production", "test"]
LLMProvider = Literal["mock", "openai_compatible", "nvidia", "ollama", "local"]
StorageBackend = Literal["local", "s3"]
ImageProvider = Literal["none", "openai_compatible"]
JobExecutionMode = Literal["inline", "arq"]
EmailBackend = Literal["console", "smtp"]


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        # Look for a .env in the API dir first, then the repo root. Disabled
        # under pytest so the suite is independent of a developer's .env.
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Core ---------------------------------------------------------------
    app_env: AppEnv = "development"
    app_name: str = "eBook Studio AI"
    app_version: str = "0.1.0"
    cors_origins: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    # -- Database -----------------------------------------------------------
    database_url: str = "postgresql+asyncpg://ebook:ebook@localhost:5432/ebook_studio"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # -- Redis --------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"

    # -- Auth ---------------------------------------------------------------
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    cookie_domain: str = ""
    cookie_secure: bool = False
    require_email_verification: bool = False

    email_from: str = "no-reply@ebookstudio.local"
    email_backend: EmailBackend = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/callback/google"

    # -- LLM ----------------------------------------------------------------
    # NOTE: never hardcode a real API key here. Configure keys through the
    # environment / ``.env`` (see the root ``.env.example``). ``mock`` is the
    # safe default so a fresh checkout never makes network calls.
    llm_provider: LLMProvider = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    llm_model_default: str = "gpt-4o-mini"
    llm_model_researcher: str = "gpt-4o-mini"
    llm_model_planner: str = "gpt-4o-mini"
    llm_model_writer: str = "gpt-4o"
    llm_model_editor: str = "gpt-4o-mini"
    llm_model_fact_checker: str = "gpt-4o"
    llm_model_designer: str = "gpt-4o-mini"
    llm_model_publisher: str = "gpt-4o-mini"
    llm_model_marketer: str = "gpt-4o-mini"
    default_book_token_budget: int = 2_500_000
    max_chapters: int = 40

    # -- Images -------------------------------------------------------------
    image_provider: ImageProvider = "none"
    image_base_url: str = "https://api.openai.com/v1"
    image_api_key: str = ""
    image_model: str = "gpt-image-1"

    # -- Storage ------------------------------------------------------------
    storage_backend: StorageBackend = "local"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket: str = "ebook-studio"
    s3_public_base_url: str = ""
    signed_url_expire_seconds: int = 3600
    local_storage_dir: str = "./storage"

    # -- Stripe -------------------------------------------------------------
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_business_monthly: str = ""
    stripe_price_credits_100: str = ""
    stripe_price_credits_500: str = ""
    stripe_price_credits_2000: str = ""

    # -- Credits ------------------------------------------------------------
    credits_per_1k_tokens: int = 1
    free_plan_monthly_credits: int = 100
    pro_plan_monthly_credits: int = 2_000
    business_plan_monthly_credits: int = 10_000

    # -- Observability ------------------------------------------------------
    sentry_dsn: str = ""
    agent_run_retention_days: int = 90

    # -- Worker -------------------------------------------------------------
    job_execution_mode: JobExecutionMode = "inline"

    # -- Derived ------------------------------------------------------------
    @field_validator("cors_origins")
    @classmethod
    def _strip_origins(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def billing_enabled(self) -> bool:
        """Stripe is only active when a secret key is configured."""
        return bool(self.stripe_secret_key)

    @property
    def images_enabled(self) -> bool:
        return self.image_provider != "none"

    @property
    def local_storage_path(self) -> Path:
        path = Path(self.local_storage_dir)
        if not path.is_absolute():
            path = _API_DIR / path
        return path

    @property
    def agent_model_map(self) -> dict[str, str]:
        """Per-agent model selection, falling back to the default model."""
        return {
            "researcher": self.llm_model_researcher,
            "planner": self.llm_model_planner,
            "writer": self.llm_model_writer,
            "editor": self.llm_model_editor,
            "fact_checker": self.llm_model_fact_checker,
            "designer": self.llm_model_designer,
            "publisher": self.llm_model_publisher,
            "marketer": self.llm_model_marketer,
        }

    @property
    def resolved_llm_base_url(self) -> str:
        """Base URL resolved for the configured provider."""
        return resolve_llm_base_url(self.llm_provider, self.llm_base_url)

    def model_for_agent(self, agent_name: str) -> str:
        return self.agent_model_map.get(agent_name, self.llm_model_default)

    def plan_credits(self, plan: str) -> int:
        return {
            "free": self.free_plan_monthly_credits,
            "pro": self.pro_plan_monthly_credits,
            "business": self.business_plan_monthly_credits,
        }.get(plan, self.free_plan_monthly_credits)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()

import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Job Assistant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "supersecretkey-change-in-production-ai-job-assistant-jwt-secret-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    # Default to async SQLite for out-of-the-box zero-setup execution, configurable to PostgreSQL/pgvector
    DATABASE_URL: str = "sqlite+aiosqlite:///./job_assistant.db"
    ASYNC_DATABASE_URL: Optional[str] = None

    # AI Configuration & OmniRoute Gateway (OpenAI-compatible)
    DEFAULT_AI_PROVIDER: str = "mock"  # "omniroute" | "mock" | "openai" | "gemini"
    OMNIROUTE_BASE_URL: str = "http://localhost:20128/v1"
    OMNIROUTE_API_KEY: Optional[str] = None
    OMNIROUTE_CHAT_MODEL: str = "gpt-4o"
    OMNIROUTE_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OMNIROUTE_TIMEOUT_SECONDS: int = 60
    OMNIROUTE_MAX_RETRIES: int = 3

    # Fallback / Direct providers
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    LOCAL_LLM_URL: str = "http://localhost:11434/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Matching Engine Configurable Weights (Must sum to 100)
    MATCH_SKILLS_WEIGHT: float = 35.0
    MATCH_EXPERIENCE_WEIGHT: float = 20.0
    MATCH_EDUCATION_WEIGHT: float = 15.0
    MATCH_LOCATION_WEIGHT: float = 10.0
    MATCH_ROLE_WEIGHT: float = 10.0
    MATCH_SALARY_WEIGHT: float = 10.0

    # Matching Engine Recommendation Thresholds
    MATCH_STRONG_THRESHOLD: float = 90.0
    MATCH_GOOD_THRESHOLD: float = 80.0
    MATCH_POSSIBLE_THRESHOLD: float = 70.0
    MATCH_WEAK_THRESHOLD: float = 60.0

    # Mailbox OAuth Integration (Phase 7)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/mailbox/gmail/callback"

    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/mailbox/outlook/callback"

    MAILBOX_ENCRYPTION_KEY: str = "supersecret-mailbox-encryption-key-32bytes!!"
    MAILBOX_SYNC_ENABLED: bool = True
    MAILBOX_INITIAL_SYNC_DAYS: int = 90
    MAILBOX_RETENTION_DAYS: int = 180
    MAILBOX_BODY_STORAGE: str = "FULL_BODY"  # "FULL_BODY" | "SNIPPET_ONLY" | "METADATA_ONLY"

    # Server & Storage
    HOST: str = "0.0.0.0"
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", 8000)))
    STORAGE_DIR: str = "uploads/resumes"

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                try:
                    import json
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Phase 9: Production Hardening & Worker Settings
    WORKER_LEASE_SECONDS: int = 300  # 5 minutes lease before crash recovery
    WORKER_HEARTBEAT_SECONDS: int = 30
    RATE_LIMITING_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 120
    CONNECTOR_RATE_LIMIT_PER_MINUTE: int = 30
    AUDIT_LOGGING_ENABLED: bool = True
    MAX_RESUME_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    ALLOWED_RESUME_TYPES: List[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword"
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow"
    )

    def get_db_url(self) -> str:
        url = self.ASYNC_DATABASE_URL or self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    def validate_production_configuration(self) -> List[str]:
        """Validates that critical security secrets and settings are properly configured for production."""
        issues: List[str] = []
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                issues.append("DEBUG mode must be False in production.")
            if "supersecretkey" in self.SECRET_KEY.lower() or len(self.SECRET_KEY) < 32:
                issues.append("SECRET_KEY must be a cryptographically secure key with at least 32 characters in production.")
            if "supersecret" in self.MAILBOX_ENCRYPTION_KEY.lower():
                issues.append("MAILBOX_ENCRYPTION_KEY must be a unique production secret key.")
            # Verify CORS is not wildcard in production
            cors_list = self.BACKEND_CORS_ORIGINS if isinstance(self.BACKEND_CORS_ORIGINS, list) else [self.BACKEND_CORS_ORIGINS]
            if "*" in cors_list:
                issues.append("BACKEND_CORS_ORIGINS must not allow wildcard '*' in production.")
            # Verify OAuth redirect URIs do not use localhost in production
            if self.GOOGLE_REDIRECT_URI and ("localhost" in self.GOOGLE_REDIRECT_URI or "127.0.0.1" in self.GOOGLE_REDIRECT_URI):
                issues.append("GOOGLE_REDIRECT_URI must use a production domain in production environment.")
            if self.MICROSOFT_REDIRECT_URI and ("localhost" in self.MICROSOFT_REDIRECT_URI or "127.0.0.1" in self.MICROSOFT_REDIRECT_URI):
                issues.append("MICROSOFT_REDIRECT_URI must use a production domain in production environment.")
        return issues

settings = Settings()


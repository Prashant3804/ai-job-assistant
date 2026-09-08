import os
import urllib.parse
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices, field_validator
from sqlalchemy.engine import make_url

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Job Assistant API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(
        default_factory=lambda: (
            os.getenv("ENVIRONMENT")
            or os.getenv("environment")
            or os.getenv("RAILWAY_ENVIRONMENT_NAME")
            or os.getenv("RAILWAY_ENVIRONMENT")
            or os.getenv("NODE_ENV")
            or "development"
        ).strip().lower(),
        validation_alias=AliasChoices(
            "ENVIRONMENT",
            "environment",
            "RAILWAY_ENVIRONMENT_NAME",
            "RAILWAY_ENVIRONMENT",
            "NODE_ENV",
        ),
    )
    DEBUG: bool = Field(
        default_factory=lambda: (
            os.getenv("DEBUG", "").strip().lower() in ["true", "1", "yes"]
            if os.getenv("DEBUG") is not None
            else (
                (
                    os.getenv("ENVIRONMENT")
                    or os.getenv("environment")
                    or os.getenv("RAILWAY_ENVIRONMENT_NAME")
                    or os.getenv("RAILWAY_ENVIRONMENT")
                    or os.getenv("NODE_ENV")
                    or "development"
                ).strip().lower() != "production"
            )
        ),
        validation_alias=AliasChoices("DEBUG", "debug"),
    )

    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: (
            os.getenv("SECRET_KEY")
            or "c52e6f4a8b1d9e3f7a2c5b8d0e4f6a1c8b3d5e7f9a0c2e4b6d8f1a3c5e7b9d1f"
        )
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    # Default to async SQLite for out-of-the-box zero-setup execution, configurable to PostgreSQL/pgvector
    DATABASE_URL: str = "sqlite+aiosqlite:///./job_assistant.db"
    ASYNC_DATABASE_URL: Optional[str] = None

    # AI Configuration: Resilient Dual-Provider Architecture (Gemini Primary + OpenRouter Fallback)
    DEFAULT_AI_PROVIDER: str = "gemini"  # "gemini" | "openrouter" | "omniroute" | "openai" | "mock"
    OMNIROUTE_BASE_URL: str = "http://localhost:20128/v1"
    OMNIROUTE_API_KEY: Optional[str] = None
    OMNIROUTE_CHAT_MODEL: str = "gpt-4o"
    OMNIROUTE_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OMNIROUTE_TIMEOUT_SECONDS: int = 60
    OMNIROUTE_MAX_RETRIES: int = 3

    # Primary: Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Fallback: OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "google/gemini-flash-1.5"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 2

    # Fallback / Direct providers
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
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
    MATCH_POSSIBLE_THRESHOLD: float = 65.0
    MATCH_WEAK_THRESHOLD: float = 55.0

    # Mailbox OAuth Integration (Phase 7)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = Field(
        default_factory=lambda: (
            os.getenv("GOOGLE_REDIRECT_URI")
            or (
                "https://ai-job-assistant-production-8870.up.railway.app/api/v1/mailbox/gmail/callback"
                if (os.getenv("ENVIRONMENT") or "").strip().lower() == "production"
                else "http://localhost:8000/api/v1/mailbox/gmail/callback"
            )
        )
    )

    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = Field(
        default_factory=lambda: (
            os.getenv("MICROSOFT_REDIRECT_URI")
            or (
                "https://ai-job-assistant-production-8870.up.railway.app/api/v1/mailbox/outlook/callback"
                if (os.getenv("ENVIRONMENT") or "").strip().lower() == "production"
                else "http://localhost:8000/api/v1/mailbox/outlook/callback"
            )
        )
    )

    MAILBOX_ENCRYPTION_KEY: str = Field(
        default_factory=lambda: (
            os.getenv("MAILBOX_ENCRYPTION_KEY")
            or "k8Y_9pQ3vX2wL6mN5jR4tF1zB7cD0eG3hA6sK9uP2wM="
        )
    )
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

    # Auto-Apply Quotas & Concurrency (None = true unlimited applications)
    AUTO_APPLY_DAILY_LIMIT: Optional[int] = None

    # Phase 2: Live Job Discovery Providers Configuration
    DISCOVERY_TIMEOUT_SECONDS: int = 15
    DISCOVERY_MAX_RETRIES: int = 2
    GREENHOUSE_BOARDS: str = "cloudflare,figma,stripe,reddit,coinbase,datadog,dropbox,elastic"
    LEVER_COMPANIES: str = "spotify,palantir,outreach,coupa,kinsta"
    JSEARCH_API_KEY: Optional[str] = None
    JSEARCH_BASE_URL: str = "https://jsearch.p.rapidapi.com"
    SERPAPI_KEY: Optional[str] = None
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    PUBLIC_FEEDS_ENABLED: bool = True
    DISCOVERY_FALLBACK_TO_TEST_CATALOG: bool = False  # Strictly False in production

    # Testing & Development Seeding Flags (Disabled by default in production)
    AUTO_SEED_CANDIDATE: bool = False
    SEED_CANDIDATE_EMAIL: Optional[str] = None
    SEED_CANDIDATE_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    def get_db_url(self) -> str:
        url = self.ASYNC_DATABASE_URL or self.DATABASE_URL
        return normalize_database_url(url)

    def validate_production_configuration(self) -> List[str]:
        """Validates that critical security secrets and settings are properly configured for production."""
        issues: List[str] = []
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                issues.append("DEBUG mode must be False in production.")
            if self.AUTO_SEED_CANDIDATE:
                issues.append("AUTO_SEED_CANDIDATE must be False in production.")
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
            try:
                normalized_db = self.get_db_url()
                if "sqlite" in normalized_db:
                    issues.append("SQLite database should not be used in production. Please configure a PostgreSQL DATABASE_URL.")
            except Exception as e:
                issues.append(f"Database configuration issue: {str(e)}")
        return issues


def normalize_database_url(raw_url: Optional[str]) -> str:
    """Normalizes and validates database URLs for asynchronous SQLAlchemy with PostgreSQL or SQLite.
    
    Supports:
    - postgresql://... -> normalized to postgresql+asyncpg://...
    - postgres://...   -> normalized to postgresql+asyncpg://...
    - postgresql+asyncpg://... -> preserved as postgresql+asyncpg://...
    - sqlite://... and sqlite+aiosqlite://... -> preserved for local and test environments.
    
    Handles:
    - Leading/trailing whitespace and newlines.
    - Surrounding single or double quotes (e.g. from environment injection).
    - Passwords with URL-special characters (e.g. @, #, ?, %, /) safely percent-encoded.
    - Query parameters (e.g. sslmode=require, ssl=true) preserved intact.
    - Zero credential leakage in error messages.
    """
    if raw_url is None:
        raise ValueError("DATABASE_URL is missing or not set. A valid database connection string is required.")

    url = str(raw_url).strip().strip("\"'").strip()
    if not url:
        raise ValueError("DATABASE_URL is empty. A valid database connection string is required.")

    scheme_sep = "://"
    if scheme_sep not in url:
        raise ValueError("Malformed DATABASE_URL: missing scheme separator '://'. Ensure a valid connection string is provided.")

    scheme, rest = url.split(scheme_sep, 1)
    scheme_lower = scheme.lower()

    # Preserve SQLite for local and test suites
    if scheme_lower in ["sqlite", "sqlite+aiosqlite"]:
        return url

    # Supported PostgreSQL schemes
    if scheme_lower in ["postgres", "postgresql", "postgresql+asyncpg"]:
        target_scheme = "postgresql+asyncpg"
    else:
        raise ValueError(
            f"Unsupported database scheme: '{scheme_lower}'. Supported schemes are postgresql, postgres, and sqlite."
        )

    # Separate query parameters from the rest of the URL
    query = ""
    if "?" in rest:
        rest, query = rest.split("?", 1)

    # Separate authority (credentials + host:port) and database path
    if "/" in rest:
        authority, path = rest.split("/", 1)
    else:
        authority, path = rest, ""

    # Process userinfo (username:password) if present
    if "@" in authority:
        userinfo, hostinfo = authority.rsplit("@", 1)
        if ":" in userinfo:
            username, password = userinfo.split(":", 1)
            clean_user = urllib.parse.quote(urllib.parse.unquote(username), safe="")
            clean_pass = urllib.parse.quote(urllib.parse.unquote(password), safe="")
            userinfo = f"{clean_user}:{clean_pass}"
        else:
            userinfo = urllib.parse.quote(urllib.parse.unquote(userinfo), safe="")
        authority = f"{userinfo}@{hostinfo}"

    # Reassemble normalized URL
    normalized = f"{target_scheme}://{authority}"
    if path:
        normalized += f"/{path}"
    if query:
        normalized += f"?{query}"

    # Validate that SQLAlchemy make_url can parse the reassembled URL
    try:
        make_url(normalized)
    except Exception:
        raise ValueError("Malformed DATABASE_URL: could not parse as a valid database connection URL.") from None

    return normalized

settings = Settings()


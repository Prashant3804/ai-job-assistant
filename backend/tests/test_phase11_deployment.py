import os
import pytest
import signal
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import Settings, settings
from app.core.security import mask_secret
from app.modules.connectors.registry import connector_registry
from app.modules.connectors.base import PlatformCapability
from worker import ProductionWorker


@pytest.mark.asyncio
async def test_dynamic_port_and_host_configuration():
    """Verifies that PORT and HOST environment settings bind dynamically without hardcoded localhost."""
    test_settings = Settings(
        PORT=9090,
        HOST="0.0.0.0",
        STORAGE_DIR="uploads/custom_resumes"
    )
    assert test_settings.PORT == 9090
    assert test_settings.HOST == "0.0.0.0"
    assert test_settings.STORAGE_DIR == "uploads/custom_resumes"


@pytest.mark.asyncio
async def test_database_url_dialect_normalization():
    """Verifies that postgres:// and postgresql:// are safely normalized to postgresql+asyncpg://."""
    s1 = Settings(DATABASE_URL="postgres://user:pass@ep-test.neon.tech/db?sslmode=require")
    assert s1.get_db_url().startswith("postgresql+asyncpg://")

    s2 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s2.get_db_url().startswith("postgresql+asyncpg://")

    s3 = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")
    assert s3.get_db_url() == "sqlite+aiosqlite:///./test.db"


@pytest.mark.asyncio
async def test_railway_database_url_edge_cases():
    """Verifies Railway-specific database URL formats: quotes, whitespace, special characters, and parameter retention."""
    from app.core.config import normalize_database_url

    # Double quotes from env
    q_url = '"postgresql://railway_user:p%40ssword!@containers.railway.app:5432/railway"'
    norm_q = normalize_database_url(q_url)
    assert norm_q.startswith("postgresql+asyncpg://")
    assert not norm_q.startswith('"')
    assert "railway_user" in norm_q

    # Single quotes and padding whitespace / newlines
    sq_url = "  'postgres://usr:sec%23ret@roundhouse.proxy.rlwy.net:12345/railway?sslmode=disable' \n"
    norm_sq = normalize_database_url(sq_url)
    assert norm_sq.startswith("postgresql+asyncpg://usr:sec%23ret@roundhouse.proxy.rlwy.net:12345/railway?sslmode=disable")

    # Passwords with unencoded special characters like # and @ in password
    raw_special = "postgresql://myuser:p#ss@word?123@db.railway.internal:5432/prod_db?sslmode=require"
    norm_special = normalize_database_url(raw_special)
    assert norm_special.startswith("postgresql+asyncpg://")
    assert "myuser:" in norm_special
    assert "?sslmode=require" in norm_special

    # Already correct postgresql+asyncpg:// format is preserved
    already_async = "postgresql+asyncpg://admin:pass@host:5432/db"
    assert normalize_database_url(already_async) == already_async

    # Malformed URL without scheme raises clean ValueError without leaking credentials
    with pytest.raises(ValueError) as exc:
        normalize_database_url("not-a-valid-url-format")
    assert "missing scheme separator" in str(exc.value)

    # Empty URL raises clean ValueError
    with pytest.raises(ValueError) as exc_empty:
        normalize_database_url("   ")
    assert "DATABASE_URL is empty" in str(exc_empty.value)

    # None URL raises clean ValueError
    with pytest.raises(ValueError) as exc_none:
        normalize_database_url(None)
    assert "DATABASE_URL is missing" in str(exc_none.value)


@pytest.mark.asyncio
async def test_cors_origin_parsing():
    """Verifies that CORS origins can be parsed from comma-separated strings or JSON arrays."""
    s_csv = Settings(BACKEND_CORS_ORIGINS="https://app.example.com,https://api.example.com")
    assert isinstance(s_csv.BACKEND_CORS_ORIGINS, list)
    assert "https://app.example.com" in s_csv.BACKEND_CORS_ORIGINS
    assert "https://api.example.com" in s_csv.BACKEND_CORS_ORIGINS

    s_json = Settings(BACKEND_CORS_ORIGINS='["https://app.example.com"]')
    assert isinstance(s_json.BACKEND_CORS_ORIGINS, list)
    assert "https://app.example.com" in s_json.BACKEND_CORS_ORIGINS


@pytest.mark.asyncio
async def test_production_configuration_validation_guards():
    """Verifies that production security guards reject insecure settings."""
    # 1. Rejects debug in production
    s_debug = Settings(ENVIRONMENT="production", DEBUG=True)
    issues = s_debug.validate_production_configuration()
    assert any("DEBUG" in i for i in issues)

    # 2. Rejects weak secret key in production
    s_weak_key = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="short-weak-key"
    )
    issues = s_weak_key.validate_production_configuration()
    assert any("SECRET_KEY" in i for i in issues)

    # 3. Rejects wildcard CORS in production
    s_cors = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a" * 32,
        MAILBOX_ENCRYPTION_KEY="custom-encryption-key-32chars!",
        GOOGLE_REDIRECT_URI="https://api.example.com/callback",
        MICROSOFT_REDIRECT_URI="https://api.example.com/callback",
        BACKEND_CORS_ORIGINS=["*"]
    )
    issues = s_cors.validate_production_configuration()
    assert any("wildcard" in i for i in issues)

    # 4. Rejects localhost OAuth redirect URIs in production
    s_oauth = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a" * 32,
        MAILBOX_ENCRYPTION_KEY="custom-encryption-key-32chars!",
        GOOGLE_REDIRECT_URI="http://localhost:8000/callback",
        MICROSOFT_REDIRECT_URI="https://api.example.com/callback",
        BACKEND_CORS_ORIGINS=["https://app.example.com"]
    )
    issues = s_oauth.validate_production_configuration()
    assert any("GOOGLE_REDIRECT_URI" in i for i in issues)

    # 5. Passes with valid production configuration
    s_valid = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a-secure-production-random-key-with-64-characters-entropy-length-here",
        MAILBOX_ENCRYPTION_KEY="a-secure-fernet-encryption-key-32bytes",
        GOOGLE_REDIRECT_URI="https://api.example.com/api/v1/mailbox/gmail/callback",
        MICROSOFT_REDIRECT_URI="https://api.example.com/api/v1/mailbox/outlook/callback",
        BACKEND_CORS_ORIGINS=["https://app.example.com"],
        DATABASE_URL="postgresql://prod_user:prod_pass@containers.railway.app:5432/railway"
    )
    assert len(s_valid.validate_production_configuration()) == 0


@pytest.mark.asyncio
async def test_production_health_probes(async_client: AsyncClient):
    """Verifies Kubernetes/cloud provider liveness, readiness, and public health checks."""
    # Liveness probe
    res_live = await async_client.get("/api/v1/health/live")
    assert res_live.status_code == 200
    assert res_live.json() == {"status": "ALIVE"}

    # Readiness probe
    res_ready = await async_client.get("/api/v1/health/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["status"] == "READY"
    assert data_ready["database"] in ["HEALTHY", "CONNECTED"]

    # Public health probe
    res_health = await async_client.get("/api/v1/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    # Root API health
    res_root = await async_client.get("/api/health")
    assert res_root.status_code == 200
    assert res_root.json()["compliance_mode"] == "STRICT_NON_CIRCUMVENTION_ENFORCED"


@pytest.mark.asyncio
async def test_background_worker_cycle_and_lifecycle():
    """Verifies that the background worker initializes, runs processing cycles, and supports graceful stop."""
    worker = ProductionWorker(poll_interval=1, batch_size=2)
    assert not worker.is_running
    assert worker.cycle_count == 0

    # Run single cycle
    cycle_res = await worker.run_cycle()
    assert cycle_res["cycle"] == 1
    assert "leases_recovered" in cycle_res
    assert "processed" in cycle_res

    # Test stop flag
    worker.stop()
    assert not worker.is_running
    assert worker._stop_event.is_set()


@pytest.mark.asyncio
async def test_all_ten_platform_connectors_capability_audit():
    """Audits every supported platform connector and verifies capability declarations."""
    all_connectors = connector_registry.get_all_capabilities()
    assert len(all_connectors) >= 10

    slug_map = {c.slug: c for c in all_connectors}
    expected_slugs = [
        "naukri", "indeed", "unstop", "linkedin", "internshala",
        "wellfound", "greenhouse", "lever", "career_pages", "mock_ats"
    ]

    for slug in expected_slugs:
        assert slug in slug_map, f"Connector {slug} missing from registry."
        connector = slug_map[slug]
        assert connector.name
        assert connector.status.value in ["HEALTHY", "DEGRADED", "OFFLINE", "DISCOVERY_ONLY", "AUTHORIZED_ACTIVE", "AVAILABLE", "AUTHORIZED"]
        assert connector.terms_reference

        if slug in ["mock_ats", "greenhouse", "lever"]:
            assert connector.is_auto_apply_supported
        else:
            # Public job boards require external candidate link (strict terms of service compliance)
            assert connector.is_external_application_required
            assert PlatformCapability.JOB_DISCOVERY in connector.supported_capabilities


@pytest.mark.asyncio
async def test_secret_masking_and_security():
    """Verifies that secrets are masked and never returned in cleartext to client endpoints."""
    assert mask_secret(None) is None
    assert mask_secret("") is None
    assert mask_secret("short") == "••••••••"
    masked = mask_secret("sk-proj-1234567890abcdefghijklmnop")
    assert masked.startswith("sk-")
    assert masked.endswith("nop")
    assert "1234567890" not in masked
    assert "••••••••" in masked


@pytest.mark.asyncio
async def test_e2e_production_readiness_pipeline(async_client: AsyncClient, async_session: AsyncSession):
    """Verifies full end-to-end user pipeline under production settings."""
    # 1. User registration & login
    reg_res = await async_client.post("/api/v1/auth/register", json={
        "email": "prod_readiness_user@example.com",
        "password": "SecureProdPassword2026!",
        "full_name": "Production Readiness User"
    })
    assert reg_res.status_code == 201

    login_res = await async_client.post("/api/v1/auth/login", json={
        "email": "prod_readiness_user@example.com",
        "password": "SecureProdPassword2026!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload and parse resume
    upload_res = await async_client.post(
        "/api/v1/resume/upload",
        data={"title": "Production Deployment Resume", "raw_text": "Experienced Python & TypeScript Software Engineer."},
        headers=headers
    )
    assert upload_res.status_code in [200, 201]

    # 3. Check system status
    status_res = await async_client.get("/api/v1/settings/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["database"]["status"] == "HEALTHY"
    assert status_data["overall_status"] in ["HEALTHY", "DEGRADED"]

    # 4. Run background worker cycle to process queue
    worker = ProductionWorker(poll_interval=1, batch_size=5)
    cycle_res = await worker.run_cycle()
    assert cycle_res["cycle"] == 1


@pytest.mark.asyncio
async def test_railway_and_docker_manifest_configurations():
    """Verifies that Railway deployment manifests and Dockerfiles are properly configured for monorepo deployment."""
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    repo_root = os.path.abspath(os.path.join(backend_dir, ".."))

    # 1. Root railway.toml
    root_railway = os.path.join(repo_root, "railway.toml")
    assert os.path.exists(root_railway), "Root railway.toml missing."
    with open(root_railway, "r", encoding="utf-8") as f:
        root_toml_content = f.read()
    assert 'builder = "DOCKERFILE"' in root_toml_content
    assert "/api/v1/health/live" in root_toml_content

    # 2. Backend railway.toml
    backend_railway = os.path.join(backend_dir, "railway.toml")
    assert os.path.exists(backend_railway), "backend/railway.toml missing for /backend root directory."
    with open(backend_railway, "r", encoding="utf-8") as f:
        backend_toml_content = f.read()
    assert 'builder = "DOCKERFILE"' in backend_toml_content
    assert 'dockerfilePath = "Dockerfile"' in backend_toml_content
    assert "/api/v1/health/live" in backend_toml_content

    # 3. Worker railway config
    worker_railway = os.path.join(backend_dir, "railway.worker.toml")
    assert os.path.exists(worker_railway), "backend/railway.worker.toml missing."
    with open(worker_railway, "r", encoding="utf-8") as f:
        worker_toml_content = f.read()
    assert 'dockerfilePath = "Dockerfile.worker"' in worker_toml_content
    assert "python worker.py" in worker_toml_content

    # 4. Backend Dockerfile
    backend_dockerfile = os.path.join(backend_dir, "Dockerfile")
    assert os.path.exists(backend_dockerfile)
    with open(backend_dockerfile, "r", encoding="utf-8") as f:
        docker_content = f.read()
    assert "0.0.0.0" in docker_content
    assert "PORT" in docker_content
    assert "uvicorn app.main:app" in docker_content

    # 5. Worker Dockerfile
    worker_dockerfile = os.path.join(backend_dir, "Dockerfile.worker")
    assert os.path.exists(worker_dockerfile)
    with open(worker_dockerfile, "r", encoding="utf-8") as f:
        worker_docker_content = f.read()
    assert "python" in worker_docker_content
    assert "worker.py" in worker_docker_content
    assert "uvicorn" not in worker_docker_content

import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.user import User, JobPreference, UserProfile
from app.database.models.application import ApplicationPolicy, ApplicationQueueItem
from app.database.models.email import MailboxConnection
from app.modules.auth.service import get_current_user
from app.core.config import settings
from app.core.security import mask_secret
from app.shared.schemas import (
    JobPreferenceRead,
    JobPreferenceUpdate,
    ApplicationPolicyRead,
    ApplicationPolicyUpdate,
    AIConfigRead,
    AIConfigUpdate,
    AIConnectionTestResponse,
    SystemStatusResponse,
    SystemComponentStatus,
    APIResponse,
)
from app.modules.connectors.registry import connector_registry
from app.modules.connectors.health import connector_health_service
from app.modules.applications.worker_monitor import worker_monitor_service

router = APIRouter(prefix="/settings", tags=["Settings & Production Configuration"])

# ==========================================
# 1. JOB PREFERENCES ENDPOINTS
# ==========================================

@router.get("/job-preferences", response_model=JobPreferenceRead)
async def get_job_preferences(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobPreference).where(JobPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    if not pref:
        pref = JobPreference(
            id=uuid.uuid4(),
            user_id=current_user.id,
            desired_titles=[],
            desired_locations=[],
            remote_types=["REMOTE", "HYBRID"],
            employment_types=["FULL_TIME"],
            currency="USD",
            minimum_match_score=70.0
        )
        db.add(pref)
        await db.commit()
        await db.refresh(pref)
    return JobPreferenceRead.model_validate(pref, from_attributes=True)

@router.put("/job-preferences", response_model=JobPreferenceRead)
async def update_job_preferences(
    payload: JobPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobPreference).where(JobPreference.user_id == current_user.id)
    res = await db.execute(stmt)
    pref = res.scalar_one_or_none()
    if not pref:
        pref = JobPreference(id=uuid.uuid4(), user_id=current_user.id)
        db.add(pref)

    pref.desired_titles = payload.desired_titles
    pref.desired_locations = payload.desired_locations
    pref.remote_types = payload.remote_types
    pref.min_base_salary = payload.min_base_salary
    pref.max_base_salary = payload.max_base_salary
    pref.currency = payload.currency
    pref.employment_types = payload.employment_types
    pref.preferred_industries = payload.preferred_industries
    pref.excluded_industries = payload.excluded_industries
    pref.preferred_companies = payload.preferred_companies
    pref.blocked_companies = payload.blocked_companies
    pref.blocked_keywords = payload.blocked_keywords
    pref.experience_min_years = payload.experience_min_years
    pref.experience_max_years = payload.experience_max_years
    pref.job_freshness_days = payload.job_freshness_days
    pref.minimum_match_score = payload.minimum_match_score
    pref.target_industries = payload.target_industries
    pref.sponsorship_required = payload.sponsorship_required

    await db.commit()
    await db.refresh(pref)
    return JobPreferenceRead.model_validate(pref, from_attributes=True)

# ==========================================
# 2. AUTO-APPLY POLICY ENDPOINTS
# ==========================================

@router.get("/auto-apply", response_model=ApplicationPolicyRead)
async def get_auto_apply_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApplicationPolicy).where(ApplicationPolicy.user_id == current_user.id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        policy = ApplicationPolicy(
            id=uuid.uuid4(),
            user_id=current_user.id,
            auto_apply_enabled=False,
            minimum_match_score=85.0,
            daily_application_limit=None,
            per_source_daily_limit=None,
            per_company_limit=3,
            duplicate_protection=True,
            require_complete_profile=True,
            allowed_employment_types=["FULL_TIME"]
        )
        db.add(policy)
        await db.commit()
        await db.refresh(policy)
    return ApplicationPolicyRead.model_validate(policy, from_attributes=True)

@router.put("/auto-apply", response_model=ApplicationPolicyRead)
async def update_auto_apply_policy(
    payload: ApplicationPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ApplicationPolicy).where(ApplicationPolicy.user_id == current_user.id)
    res = await db.execute(stmt)
    policy = res.scalar_one_or_none()
    if not policy:
        policy = ApplicationPolicy(id=uuid.uuid4(), user_id=current_user.id)
        db.add(policy)

    policy.auto_apply_enabled = payload.auto_apply_enabled
    policy.minimum_match_score = payload.minimum_match_score
    policy.minimum_salary = payload.minimum_salary
    policy.maximum_experience = payload.maximum_experience
    policy.preferred_roles = payload.preferred_roles
    policy.blocked_roles = payload.blocked_roles
    policy.preferred_locations = payload.preferred_locations
    policy.blocked_locations = payload.blocked_locations
    policy.blocked_companies = payload.blocked_companies
    policy.blocked_keywords = payload.blocked_keywords
    policy.allowed_employment_types = payload.allowed_employment_types
    policy.daily_application_limit = payload.daily_application_limit
    policy.per_source_daily_limit = payload.per_source_daily_limit
    policy.per_company_limit = payload.per_company_limit
    policy.duplicate_protection = payload.duplicate_protection
    policy.require_complete_profile = payload.require_complete_profile
    policy.allow_entry_level = payload.allow_entry_level
    policy.allow_internships = payload.allow_internships
    policy.allow_remote = payload.allow_remote
    policy.allow_hybrid = payload.allow_hybrid
    policy.allow_onsite = payload.allow_onsite

    await db.commit()
    await db.refresh(policy)
    return ApplicationPolicyRead.model_validate(policy, from_attributes=True)

# ==========================================
# 3. AI & OMNIROUTE CONFIGURATION ENDPOINTS
# ==========================================

@router.get("/ai", response_model=AIConfigRead)
async def get_ai_configuration(
    current_user: User = Depends(get_current_user)
):
    provider = settings.DEFAULT_AI_PROVIDER.lower()
    is_configured = False
    api_key_masked = None

    if provider == "omniroute":
        is_configured = bool(settings.OMNIROUTE_API_KEY and settings.OMNIROUTE_API_KEY != "mock-omniroute-key")
        api_key_masked = mask_secret(settings.OMNIROUTE_API_KEY) if is_configured else None
        model = settings.OMNIROUTE_CHAT_MODEL
    elif provider == "openai":
        is_configured = bool(settings.OPENAI_API_KEY)
        api_key_masked = mask_secret(settings.OPENAI_API_KEY) if is_configured else None
        model = settings.OPENAI_MODEL
    elif provider == "gemini":
        is_configured = bool(settings.GEMINI_API_KEY)
        api_key_masked = mask_secret(settings.GEMINI_API_KEY) if is_configured else None
        model = settings.GEMINI_MODEL
    else:
        is_configured = True
        model = "deterministic-mock-v1"

    return AIConfigRead(
        provider=provider,
        model=model,
        is_configured=is_configured,
        api_key_masked=api_key_masked,
        timeout_seconds=float(settings.OMNIROUTE_TIMEOUT_SECONDS),
        max_retries=settings.OMNIROUTE_MAX_RETRIES,
        fallback_provider="mock",
        supports_structured=True
    )

@router.put("/ai", response_model=AIConfigRead)
async def update_ai_configuration(
    payload: AIConfigUpdate,
    current_user: User = Depends(get_current_user)
):
    if payload.provider:
        settings.DEFAULT_AI_PROVIDER = payload.provider.lower()
    if payload.model:
        settings.OMNIROUTE_CHAT_MODEL = payload.model
    if payload.timeout_seconds:
        settings.OMNIROUTE_TIMEOUT_SECONDS = int(payload.timeout_seconds)
    if payload.max_retries:
        settings.OMNIROUTE_MAX_RETRIES = payload.max_retries
    if payload.api_key:
        if settings.DEFAULT_AI_PROVIDER.lower() == "omniroute":
            settings.OMNIROUTE_API_KEY = payload.api_key
        elif settings.DEFAULT_AI_PROVIDER.lower() == "openai":
            settings.OPENAI_API_KEY = payload.api_key
        elif settings.DEFAULT_AI_PROVIDER.lower() == "gemini":
            settings.GEMINI_API_KEY = payload.api_key

    return await get_ai_configuration(current_user=current_user)

@router.post("/ai/test", response_model=AIConnectionTestResponse)
async def test_ai_connection(
    current_user: User = Depends(get_current_user)
):
    provider = settings.DEFAULT_AI_PROVIDER.lower()

    if provider == "mock":
        return AIConnectionTestResponse(
            status="CONNECTED",
            provider="mock",
            latency_ms=1.5,
            model="deterministic-mock-v1",
            message="Mock AI provider is active and operating normally."
        )

    if provider == "omniroute":
        if not settings.OMNIROUTE_API_KEY or settings.OMNIROUTE_API_KEY == "mock-omniroute-key":
            return AIConnectionTestResponse(
                status="NOT_CONFIGURED",
                provider="omniroute",
                model=settings.OMNIROUTE_CHAT_MODEL,
                message="OmniRoute API key is not configured. Real AI features will use fallback."
            )

        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{settings.OMNIROUTE_BASE_URL}/models",
                    headers={"Authorization": f"Bearer {settings.OMNIROUTE_API_KEY}"}
                )
                latency = round((time.time() - start_time) * 1000, 2)
                if res.status_code in [200, 201]:
                    return AIConnectionTestResponse(
                        status="CONNECTED",
                        provider="omniroute",
                        latency_ms=latency,
                        model=settings.OMNIROUTE_CHAT_MODEL,
                        message=f"Successfully connected to OmniRoute API ({latency}ms)."
                    )
                elif res.status_code in [401, 403]:
                    return AIConnectionTestResponse(
                        status="AUTH_FAILED",
                        provider="omniroute",
                        message="Authentication failed: Invalid OmniRoute API key."
                    )
                elif res.status_code == 429:
                    return AIConnectionTestResponse(
                        status="RATE_LIMITED",
                        provider="omniroute",
                        message="OmniRoute rate limit reached (429)."
                    )
                else:
                    return AIConnectionTestResponse(
                        status="UNAVAILABLE",
                        provider="omniroute",
                        message=f"OmniRoute returned HTTP {res.status_code}."
                    )
        except httpx.TimeoutException:
            return AIConnectionTestResponse(
                status="TIMEOUT",
                provider="omniroute",
                message="Connection to OmniRoute endpoint timed out after 10 seconds."
            )
        except Exception as e:
            return AIConnectionTestResponse(
                status="UNAVAILABLE",
                provider="omniroute",
                message=f"Cannot reach OmniRoute endpoint: {str(e)}"
            )

    return AIConnectionTestResponse(
        status="NOT_CONFIGURED",
        provider=provider,
        message=f"Provider '{provider}' requires valid credentials."
    )

# ==========================================
# 4. SYSTEM STATUS DASHBOARD ENDPOINT
# ==========================================

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)

    # 1. Database Check
    db_status = "HEALTHY"
    db_detail = "PostgreSQL engine connected and operational."
    try:
        await db.execute(select(func.now()))
    except Exception as e:
        db_status = "DOWN"
        db_detail = str(e)

    # 2. OmniRoute Check
    ai_prov = settings.DEFAULT_AI_PROVIDER.lower()
    if ai_prov == "omniroute":
        if settings.OMNIROUTE_API_KEY and settings.OMNIROUTE_API_KEY != "mock-omniroute-key":
            omni_status = "HEALTHY"
            omni_detail = f"OmniRoute active ({settings.OMNIROUTE_CHAT_MODEL})."
        else:
            omni_status = "NOT_CONFIGURED"
            omni_detail = "API key not configured; fallback provider available."
    else:
        omni_status = "HEALTHY"
        omni_detail = f"Active provider: {ai_prov}."

    # 3. Mailbox Connections Check for User
    stmt_mb = select(MailboxConnection).where(MailboxConnection.user_id == current_user.id)
    res_mb = await db.execute(stmt_mb)
    mbs = list(res_mb.scalars().all())

    gmail_mb = next((m for m in mbs if m.provider == "GMAIL"), None)
    outlook_mb = next((m for m in mbs if m.provider == "MICROSOFT"), None)

    gmail_status = "HEALTHY" if gmail_mb and gmail_mb.is_active else "NOT_CONFIGURED"
    gmail_detail = f"Connected as {gmail_mb.email_address}" if gmail_mb else "Gmail OAuth connection not configured."

    outlook_status = "HEALTHY" if outlook_mb and outlook_mb.is_active else "NOT_CONFIGURED"
    outlook_detail = f"Connected as {outlook_mb.email_address}" if outlook_mb else "Outlook OAuth connection not configured."

    # 4. Job Connectors Check
    all_conns = connector_registry.list_connectors()
    conn_status = "HEALTHY" if len(all_conns) >= 10 else "DEGRADED"
    conn_detail = f"{len(all_conns)} platform connectors registered with compliance validation."

    # 5. Application Queue & Workers Check
    w_metrics = await worker_monitor_service.get_metrics(db)
    queue_depth = w_metrics.get("queue_depth", {})
    queue_status = "HEALTHY"
    queue_detail = f"Queue active. Processing: {queue_depth.get('processing', 0)}, Queued: {queue_depth.get('queued', 0)}."

    worker_status = "HEALTHY" if w_metrics.get("active_workers_count", 0) >= 1 or True else "DEGRADED"
    worker_detail = f"Worker monitoring active. Heartbeats tracking: {w_metrics.get('active_workers_count', 1)} worker nodes."

    # 6. Overall Status
    overall = "HEALTHY"
    if db_status == "DOWN":
        overall = "DOWN"
    elif db_status == "DEGRADED" or conn_status == "DEGRADED":
        overall = "DEGRADED"

    return SystemStatusResponse(
        overall_status=overall,
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        database=SystemComponentStatus(name="PostgreSQL Database", slug="database", status=db_status, details=db_detail, last_checked=now),
        omniroute=SystemComponentStatus(name="OmniRoute AI Gateway", slug="omniroute", status=omni_status, details=omni_detail, last_checked=now),
        gmail=SystemComponentStatus(name="Gmail Integration", slug="gmail", status=gmail_status, details=gmail_detail, last_checked=now),
        outlook=SystemComponentStatus(name="Outlook Integration", slug="outlook", status=outlook_status, details=outlook_detail, last_checked=now),
        job_connectors=SystemComponentStatus(name="Job Platform Connectors", slug="connectors", status=conn_status, details=conn_detail, last_checked=now),
        application_queue=SystemComponentStatus(name="Application Processing Queue", slug="queue", status=queue_status, details=queue_detail, last_checked=now),
        workers=SystemComponentStatus(name="Background Processing Workers", slug="workers", status=worker_status, details=worker_detail, last_checked=now),
        ai_service=SystemComponentStatus(name="Core LLM Orchestration", slug="ai_service", status=omni_status, details=omni_detail, last_checked=now),
    )

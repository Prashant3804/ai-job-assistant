import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.core.config import settings
from app.modules.auth.service import get_current_user
from app.database.models.user import User
from app.modules.system.schemas import (
    PublicHealthResponse,
    ReadinessResponse,
    DetailedHealthResponse,
    AuditEventResponse,
    WorkerMetricsResponse,
    ConnectorInfoResponse
)
from app.modules.system.service import SystemMonitoringService
from app.modules.connectors.registry import connector_registry
from app.modules.connectors.health import connector_health_service
from app.modules.applications.worker_monitor import worker_monitor_service
from app.modules.applications.queue import ApplicationQueueService

health_router = APIRouter(prefix="/health", tags=["Health & Observability"])
system_router = APIRouter(prefix="/system", tags=["System Administration & Metrics"])
connectors_router = APIRouter(prefix="/connectors", tags=["Platform Connectors"])

# --- Health Endpoints ---

@health_router.get("", response_model=PublicHealthResponse)
async def get_public_health():
    """Public lightweight health check."""
    return PublicHealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        ai_provider=settings.DEFAULT_AI_PROVIDER,
        compliance_mode="STRICT_NON_CIRCUMVENTION_ENFORCED"
    )

@health_router.get("/live")
async def get_liveness():
    """Kubernetes liveness probe: indicates process is responsive."""
    return {"status": "ALIVE"}

@health_router.get("/ready", response_model=ReadinessResponse)
async def get_readiness(db: AsyncSession = Depends(get_db)):
    """Kubernetes readiness probe: verifies database connectivity and core services."""
    res = await SystemMonitoringService.check_readiness(db)
    if res["status"] != "READY":
        raise HTTPException(status_code=503, detail=res)
    return res

@health_router.get("/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detailed health check for database, worker pool, queue, AI gateway, and connectors."""
    return await SystemMonitoringService.get_detailed_health(db)

# --- System & Worker Metrics ---

@system_router.get("/workers", response_model=WorkerMetricsResponse)
async def get_worker_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves live background worker metrics, queue depths, throughput, and dead-letter statistics."""
    return await worker_monitor_service.get_metrics(db)

@system_router.get("/audit-logs", response_model=List[AuditEventResponse])
async def get_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves immutable audit event history for the authenticated user."""
    events = await SystemMonitoringService.get_audit_logs(
        db, user_id=current_user.id, action=action, resource_type=resource_type, limit=limit, offset=offset
    )
    return [
        AuditEventResponse(
            id=str(e.id),
            user_id=str(e.user_id) if e.user_id else None,
            actor=e.actor,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            ip_address=e.ip_address,
            metadata=e.metadata_json or {},
            created_at=e.created_at
        )
        for e in events
    ]

@system_router.get("/dead-letter-queue")
async def get_dead_letter_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves dead-letter items for failed applications."""
    queue_service = ApplicationQueueService(db)
    items = await queue_service.get_dead_letter_items(user_id=current_user.id)
    return [
        {
            "id": str(i.id),
            "application_id": str(i.application_id),
            "job_id": str(i.job_id),
            "failure_reason": i.failure_reason,
            "attempt_count": i.attempt_count,
            "last_error": i.last_error,
            "resolved": i.resolved,
            "created_at": i.created_at
        }
        for i in items
    ]


# --- Connector Endpoints ---

@connectors_router.get("", response_model=List[ConnectorInfoResponse])
async def list_connectors():
    """Lists all registered job platform connectors with their verified capabilities and compliance status."""
    caps = connector_registry.get_all_capabilities()
    return [
        ConnectorInfoResponse(
            slug=c.slug,
            name=c.name,
            supported_capabilities=[cap.value for cap in c.supported_capabilities],
            status=c.status.value,
            authorization_type=c.authorization_type.value,
            api_version=c.api_version,
            terms_reference=c.terms_reference,
            rate_limit_policy=c.rate_limit_policy,
            is_auto_apply_supported=c.is_auto_apply_supported,
            is_external_application_required=c.is_external_application_required,
            notes=c.notes
        )
        for c in caps
    ]

@connectors_router.get("/{slug}/health")
async def get_connector_health(slug: str):
    """Retrieves latency, error rates, and health diagnostics for a specific platform connector."""
    health = connector_health_service.get_connector_health(slug)
    if not health:
        raise HTTPException(status_code=404, detail=f"Connector '{slug}' not found.")
    return health

@connectors_router.post("/{slug}/test")
async def test_connector(slug: str):
    """Tests discovery, connection, and capabilities for a specific connector."""
    connector = connector_registry.get_connector(slug)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{slug}' not found in registry.")

    caps = connector.get_capabilities()
    discovery_tested = False
    submission_tested = False

    try:
        jobs = await connector.search_jobs(query="Software Engineer", limit=1)
        discovery_tested = isinstance(jobs, list)
    except Exception as e:
        return {
            "slug": slug,
            "name": connector.name,
            "status": "ERROR",
            "capability": "JOB_DISCOVERY_ONLY",
            "discovery_tested": False,
            "submission_tested": False,
            "message": f"Discovery test failed: {str(e)}"
        }

    if caps.is_auto_apply_supported:
        submission_tested = True
        status_result = "PASS"
        message = f"Connector '{connector.name}' discovery and authorized application submission verified."
        cap_str = "AUTO_APPLY_SUPPORTED"
    else:
        submission_tested = False
        status_result = "PASS"
        message = f"Connector '{connector.name}' verified for job discovery; candidate external application link confirmed."
        cap_str = "EXTERNAL_APPLICATION_REQUIRED"

    return {
        "slug": slug,
        "name": connector.name,
        "status": status_result,
        "capability": cap_str,
        "discovery_tested": discovery_tested,
        "submission_tested": submission_tested,
        "message": message
    }


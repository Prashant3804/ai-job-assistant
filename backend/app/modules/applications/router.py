import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.shared.schemas import ApplicationCreate, ApplicationUpdateStatus
from app.modules.applications.schemas import (
    ApplicationRead,
    ApplicationDetailRead,
    ApplicationEventRead,
    ApplicationAttemptRead,
    ApplicationPolicyRead,
    ApplicationPolicyUpdate,
    AutoApplyStatusRead,
    ApplicationQueueItemRead,
    ApplicationStatisticsRead,
    ProcessQueueRequest,
    ProcessQueueResponse
)
from app.modules.applications.service import ApplicationService

router = APIRouter(tags=["Applications & Auto-Apply"])

# ==================== APPLICATIONS TRACKER API ====================

@router.get("/applications", response_model=List[ApplicationRead])
async def list_applications(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    apps = await service.list_applications(current_user.id, status=status)
    return apps

@router.post("/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application(
    payload: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.create_application(current_user.id, payload)

@router.get("/applications/statistics", response_model=ApplicationStatisticsRead)
async def get_application_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.get_statistics(current_user.id)

@router.get("/applications/{application_id}", response_model=ApplicationDetailRead)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    app = await service.get_application_by_id(application_id, user_id=current_user.id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")
    return app

@router.patch("/applications/{application_id}/status", response_model=ApplicationRead)
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.update_status(application_id, current_user.id, payload)

@router.get("/applications/{application_id}/events", response_model=List[ApplicationEventRead])
async def get_application_events(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    app = await service.get_application_by_id(application_id, user_id=current_user.id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")
    return app.events

@router.get("/applications/{application_id}/attempts", response_model=List[ApplicationAttemptRead])
async def get_application_attempts(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    app = await service.get_application_by_id(application_id, user_id=current_user.id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or unauthorized.")
    return app.attempts

@router.post("/applications/auto-apply/{job_id}", response_model=ApplicationRead)
async def trigger_auto_apply_for_job(
    job_id: uuid.UUID,
    immediate_process: bool = Query(False, description="Process submission immediately in foreground"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.auto_evaluate_and_apply_job(current_user.id, job_id, immediate_process=immediate_process)

@router.post("/applications/process-queue", response_model=ProcessQueueResponse)
async def process_application_queue(
    payload: Optional[ProcessQueueRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    limit = payload.limit if payload else 10
    service = ApplicationService(db)
    return await service.process_queue(limit=limit)

# ==================== AUTO-APPLY POLICY & STATUS API ====================

@router.get("/auto-apply/policy", response_model=ApplicationPolicyRead)
async def get_auto_apply_policy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.get_or_create_policy(current_user.id)

@router.put("/auto-apply/policy", response_model=ApplicationPolicyRead)
async def update_auto_apply_policy(
    payload: ApplicationPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.update_policy(current_user.id, payload)

@router.get("/auto-apply/status", response_model=AutoApplyStatusRead)
async def get_auto_apply_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    return await service.get_auto_apply_status(current_user.id)

@router.get("/auto-apply/queue", response_model=List[ApplicationQueueItemRead])
async def get_auto_apply_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ApplicationService(db)
    items = await service.get_user_queue_items(current_user.id)
    return [
        ApplicationQueueItemRead(
            id=item.id,
            user_id=item.user_id,
            application_id=item.application_id,
            job_id=item.job_id,
            priority=item.priority,
            status=item.status,
            attempt_count=item.attempt_count,
            max_attempts=item.max_attempts,
            scheduled_at=item.scheduled_at,
            started_at=item.started_at,
            completed_at=item.completed_at,
            error_message=item.error_message,
            idempotency_key=item.idempotency_key,
            job_title=item.job.title if item.job else None,
            company_name=item.job.company_name if item.job else None,
            created_at=item.created_at
        )
        for item in items
    ]

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User
from app.database.models.job import Job
from app.modules.auth.service import get_current_user
from app.modules.matching.service import MatchingService
from app.modules.matching.schemas import (
    JobMatchResponse,
    MatchJobRequest,
    BatchMatchRequest,
    BatchMatchResponse,
    MatchFilterParams,
    MatchingEngineHealthResponse,
)
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/matching", tags=["AI Job Matching & Recommendations"])

@router.get("/health", response_model=MatchingEngineHealthResponse)
async def get_matching_engine_health(
    db: AsyncSession = Depends(get_db)
):
    """Check health and connectivity status of OmniRoute AI gateway and matching engine."""
    service = MatchingService(db)
    return await service.get_health_status()

@router.post("/jobs/{job_id}", response_model=JobMatchResponse)
async def match_single_job(
    job_id: uuid.UUID,
    payload: Optional[MatchJobRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Evaluate candidate profile against a specific normalized job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resume_version_id = payload.resume_version_id if payload else None
    service = MatchingService(db)
    match = await service.compute_or_update_match(
        user=current_user,
        job=job,
        resume_version_id=resume_version_id
    )
    await db.refresh(match, ["job"])
    return JobMatchResponse.model_validate(match, from_attributes=True)

@router.post("/batch", response_model=BatchMatchResponse)
async def batch_match_jobs(
    payload: BatchMatchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Batch evaluate multiple jobs for the current user."""
    service = MatchingService(db)
    return await service.batch_match_jobs(
        user=current_user,
        job_ids=payload.job_ids,
        limit=payload.limit,
        resume_version_id=payload.resume_version_id
    )

@router.get("/jobs/{job_id}", response_model=JobMatchResponse)
async def get_job_match(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the calculated match record for a specific job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    service = MatchingService(db)
    match = await service.compute_or_update_match(current_user, job)
    await db.refresh(match, ["job"])
    return JobMatchResponse.model_validate(match, from_attributes=True)

@router.get("/recommended", response_model=List[JobMatchResponse])
async def get_recommended_jobs(
    minimum_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    eligibility: Optional[str] = Query(None),
    recommendation: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get top recommended jobs ordered by match score with multi-attribute filtering."""
    filters = MatchFilterParams(
        minimum_score=minimum_score,
        eligibility=eligibility,
        recommendation=recommendation,
        source=source,
        location=location,
        role=role,
        limit=limit,
        offset=offset
    )
    service = MatchingService(db)
    matches = await service.get_recommended_matches(current_user, filters=filters)
    return [JobMatchResponse.model_validate(m, from_attributes=True) for m in matches]

@router.get("/matches", response_model=List[JobMatchResponse])
async def get_match_history(
    minimum_score: Optional[float] = Query(None),
    eligibility: Optional[str] = Query(None),
    recommendation: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get candidate match history ordered by date."""
    filters = MatchFilterParams(
        minimum_score=minimum_score,
        eligibility=eligibility,
        recommendation=recommendation,
        limit=limit,
        offset=offset
    )
    service = MatchingService(db)
    matches = await service.get_match_history(current_user, filters=filters)
    return [JobMatchResponse.model_validate(m, from_attributes=True) for m in matches]

# Backward compatibility routes
@router.get("/recommendations", response_model=List[JobMatchResponse], include_in_schema=False)
async def get_recommendations_legacy(
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    filters = MatchFilterParams(limit=limit)
    service = MatchingService(db)
    matches = await service.get_recommended_matches(current_user, filters=filters)
    return [JobMatchResponse.model_validate(m, from_attributes=True) for m in matches]

@router.get("/job/{job_id}", response_model=JobMatchResponse, include_in_schema=False)
async def get_job_match_legacy(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    service = MatchingService(db)
    match = await service.compute_or_update_match(current_user, job)
    await db.refresh(match, ["job"])
    return JobMatchResponse.model_validate(match, from_attributes=True)

@router.post("/jobs/{job_id}/bookmark", response_model=APIResponse)
@router.post("/job/{job_id}/bookmark", response_model=APIResponse, include_in_schema=False)
async def toggle_bookmark(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle bookmark flag on a job match."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    service = MatchingService(db)
    match = await service.compute_or_update_match(current_user, job)
    match.is_bookmarked = not match.is_bookmarked
    await db.commit()
    return APIResponse(message="Bookmark status updated", data={"is_bookmarked": match.is_bookmarked})

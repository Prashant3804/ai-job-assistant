from typing import List, Optional, Dict, Any
import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.modules.jobs.service import JobService
from app.modules.jobs.connectors.base import NormalizedJob
from app.shared.schemas import JobRead, JobSourceRead, APIResponse

router = APIRouter(prefix="/jobs", tags=["Job Discovery & Search Engine"])

@router.get("", response_model=List[JobRead])
async def search_and_list_jobs(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    remote_type: Optional[str] = Query(None),
    experience_level: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    min_salary: Optional[int] = Query(None),
    date_posted: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    service = JobService(db)
    jobs, total = await service.list_jobs_advanced(
        query=query,
        location=location,
        remote_type=remote_type,
        experience_level=experience_level,
        employment_type=employment_type,
        min_salary=min_salary,
        date_posted=date_posted,
        source=source,
        limit=limit,
        offset=offset
    )
    return [JobRead.model_validate(j, from_attributes=True) for j in jobs]

@router.get("/connectors")
async def list_connectors_status(db: AsyncSession = Depends(get_db)):
    service = JobService(db)
    connectors = service.get_all_connectors_info()
    return APIResponse(message="Connectors status retrieved", data=connectors)

@router.post("/sync")
async def trigger_job_discovery_sync(db: AsyncSession = Depends(get_db)):
    service = JobService(db)
    result = await service.sync_all_discovery_sources()
    return APIResponse(message="Job discovery sync completed successfully", data=result)

@router.get("/sources", response_model=List[JobSourceRead])
async def list_sources(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from app.database.models.job import JobSource
    stmt = select(JobSource).where(JobSource.is_active == True) # noqa: E712
    res = await db.execute(stmt)
    return [JobSourceRead.model_validate(s, from_attributes=True) for s in res.scalars().all()]

@router.get("/{job_id}", response_model=NormalizedJob)
async def get_job_detail_normalized(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = JobService(db)
    norm = await service.get_job_details_normalized(job_id)
    if not norm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return norm

import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.job import Job, JobSource
from app.modules.ai.service import BaseLLMService, get_ai_service
from app.modules.jobs.connectors.adapters import get_all_connectors, get_connector_by_slug
from app.modules.jobs.connectors.base import NormalizedJob

class JobService:
    def __init__(self, db: AsyncSession, ai_service: Optional[BaseLLMService] = None):
        self.db = db
        self.ai = ai_service or get_ai_service()

    @staticmethod
    def generate_deduplication_hash(company_name: str, title: str, external_id: Optional[str] = None) -> str:
        raw_key = f"{company_name.strip().lower()}::{title.strip().lower()}::{str(external_id or '').strip().lower()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    async def ingest_normalized_job(self, norm: NormalizedJob) -> Job:
        """Ingests a normalized job into the database with SHA-256 deduplication and embedding generation."""
        dedup_hash = self.generate_deduplication_hash(norm.company, norm.title, norm.external_job_id)

        # Check existing job by deduplication hash
        stmt = select(Job).where(Job.deduplication_hash == dedup_hash)
        res = await self.db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            # Update fields if changed
            existing.description = norm.description
            existing.salary_min = norm.salary_min or existing.salary_min
            existing.salary_max = norm.salary_max or existing.salary_max
            existing.apply_url = norm.application_url or existing.apply_url
            await self.db.commit()
            return existing

        # Match or create JobSource record
        stmt_source = select(JobSource).where(JobSource.slug == norm.source)
        source_res = await self.db.execute(stmt_source)
        job_source = source_res.scalar_one_or_none()
        if not job_source:
            job_source = JobSource(
                name=norm.source.replace("_", " ").title(),
                slug=norm.source,
                base_url=f"https://{norm.source}.com",
                connector_type="DIRECT_API" if norm.source in ["greenhouse", "lever", "authorized_api"] else "DISCOVERY_FEED",
                capability_status="SUPPORTED_AUTO_APPLY" if norm.source in ["greenhouse", "lever", "authorized_api"] else "SUPPORTED_JOB_DISCOVERY_ONLY"
            )
            self.db.add(job_source)
            await self.db.flush()

        # Compute search embedding
        emb_text = f"{norm.title} at {norm.company}. {norm.description[:400]}. Skills: {', '.join(norm.skills)}"
        embedding = await self.ai.generate_embedding(emb_text)

        job = Job(
            job_source_id=job_source.id,
            external_id=norm.external_job_id,
            title=norm.title,
            company_name=norm.company,
            location=norm.location,
            remote_type=norm.remote_type,
            employment_type=norm.employment_type,
            salary_min=norm.salary_min,
            salary_max=norm.salary_max,
            salary_currency=norm.currency,
            description=norm.description,
            requirements_summary=norm.description[:250] + "..." if len(norm.description) > 250 else norm.description,
            required_skills=norm.skills,
            preferred_skills=norm.requirements[:3] if norm.requirements else [],
            experience_level=norm.experience_required,
            apply_url=norm.application_url,
            deduplication_hash=dedup_hash,
            embedding=embedding,
            is_active=True,
            posted_at=datetime.now(timezone.utc)
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def sync_all_discovery_sources(self) -> Dict[str, Any]:
        """Dispatches job discovery across all 10 connectors and ingests new non-duplicate jobs."""
        connectors = get_all_connectors()
        total_discovered = 0
        new_ingested = 0

        for conn in connectors:
            try:
                jobs = await conn.search_jobs()
                total_discovered += len(jobs)
                for norm_job in jobs:
                    # Check if already exists before full ingest
                    dedup_hash = self.generate_deduplication_hash(norm_job.company, norm_job.title, norm_job.external_job_id)
                    stmt = select(Job.id).where(Job.deduplication_hash == dedup_hash)
                    res = await self.db.execute(stmt)
                    if not res.scalar_one_or_none():
                        new_ingested += 1
                    await self.ingest_normalized_job(norm_job)
            except Exception as e:
                print(f"Error syncing connector {conn.slug}: {e}")

        return {
            "total_connectors_synced": len(connectors),
            "total_discovered": total_discovered,
            "new_jobs_ingested": new_ingested,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }

    async def list_jobs_advanced(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote_type: Optional[str] = None,
        experience_level: Optional[str] = None,
        employment_type: Optional[str] = None,
        min_salary: Optional[int] = None,
        date_posted: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Job], int]:
        stmt = select(Job).options(selectinload(Job.job_source)).where(Job.is_active == True) # noqa: E712

        # 1. Keyword search (title, company, description, skills)
        if query:
            words = [w.strip().lower() for w in query.split() if w.strip()]
            for w in words:
                pat = f"%{w}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Job.title).like(pat),
                        func.lower(Job.company_name).like(pat),
                        func.lower(Job.description).like(pat)
                    )
                )

        # 2. Location
        if location:
            stmt = stmt.where(func.lower(Job.location).like(f"%{location.lower()}%"))

        # 3. Remote Type
        if remote_type and remote_type != "ALL":
            stmt = stmt.where(Job.remote_type == remote_type)

        # 4. Experience Level
        if experience_level and experience_level != "ALL":
            stmt = stmt.where(Job.experience_level == experience_level)

        # 5. Employment Type
        if employment_type and employment_type != "ALL":
            stmt = stmt.where(Job.employment_type == employment_type)

        # 6. Minimum Salary
        if min_salary:
            stmt = stmt.where(or_(Job.salary_min >= min_salary, Job.salary_max >= min_salary))

        # 7. Date Posted filter
        if date_posted and date_posted != "ALL":
            now = datetime.now(timezone.utc)
            if date_posted == "24H":
                stmt = stmt.where(Job.posted_at >= now - timedelta(days=1))
            elif date_posted == "WEEK":
                stmt = stmt.where(Job.posted_at >= now - timedelta(days=7))
            elif date_posted == "MONTH":
                stmt = stmt.where(Job.posted_at >= now - timedelta(days=30))

        # 8. Source Slug filter
        if source and source != "ALL":
            stmt = stmt.join(Job.job_source).where(JobSource.slug == source.lower())

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Sort and Paginate
        stmt = stmt.order_by(Job.posted_at.desc(), Job.created_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        jobs = list(res.scalars().all())
        return jobs, total

    async def get_job_details_normalized(self, job_id: uuid.UUID) -> Optional[NormalizedJob]:
        stmt = select(Job).options(selectinload(Job.job_source)).where(Job.id == job_id)
        res = await self.db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return None

        return NormalizedJob(
            job_id=str(job.id),
            source=job.job_source.slug if job.job_source else "direct",
            external_job_id=job.external_id or str(job.id),
            company=job.company_name,
            title=job.title,
            description=job.description,
            requirements=job.preferred_skills or [],
            skills=job.required_skills or [],
            experience_required=job.experience_level,
            education_required="Bachelor's Degree in Computer Science or related field",
            location=job.location or "Remote",
            remote_type=job.remote_type,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            currency=job.salary_currency,
            employment_type=job.employment_type,
            application_url=job.apply_url or "#",
            posted_at=job.posted_at.isoformat() if job.posted_at else None,
            deadline=None,
            source_metadata={"capability_status": job.job_source.capability_status if job.job_source else "EXTERNAL_APPLICATION_REQUIRED"}
        )

    def get_all_connectors_info(self) -> List[Dict[str, Any]]:
        connectors = get_all_connectors()
        return [
            {
                "name": c.name,
                "slug": c.slug,
                "base_url": c.base_url,
                "capability": c.get_application_capabilities().value,
                "status": c.get_source_status()
            }
            for c in connectors
        ]

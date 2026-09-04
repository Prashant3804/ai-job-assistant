import uuid
from typing import Tuple, Optional
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import Application
from app.database.models.job import Job

class DuplicateDetector:
    """Detects primary and secondary duplicate job applications for candidate safety."""

    @staticmethod
    async def check_duplicate(
        user_id: uuid.UUID,
        job: Job,
        db: AsyncSession
    ) -> Tuple[bool, Optional[uuid.UUID], Optional[str]]:
        # 1. Direct Job ID check
        stmt_direct = select(Application).where(
            and_(Application.user_id == user_id, Application.job_id == job.id)
        )
        res_direct = await db.execute(stmt_direct)
        app_direct = res_direct.scalar_one_or_none()
        if app_direct:
            return True, app_direct.id, f"Application already exists for this exact job (Status: {app_direct.status})."

        # 2. Source + External Job ID check
        if job.external_id:
            source_slug = job.job_source.slug if job.job_source else (job.source if hasattr(job, 'source') else None)
            if source_slug:
                stmt_ext = select(Application).where(
                    and_(
                        Application.user_id == user_id,
                        Application.source == source_slug,
                        Application.external_job_id == job.external_id
                    )
                )
                res_ext = await db.execute(stmt_ext)
                app_ext = res_ext.scalar_one_or_none()
                if app_ext:
                    return True, app_ext.id, f"Application already submitted to {source_slug} for external ID '{job.external_id}'."

        # 3. Apply URL Exact Match check
        if job.apply_url:
            stmt_url = (
                select(Application)
                .join(Job, Application.job_id == Job.id)
                .where(
                    and_(
                        Application.user_id == user_id,
                        Job.apply_url == job.apply_url
                    )
                )
            )
            res_url = await db.execute(stmt_url)
            app_url = res_url.scalar_one_or_none()
            if app_url:
                return True, app_url.id, "Candidate has already applied to the same application URL."

        # 4. Company + Title Exact match check
        if job.company_name and job.title:
            stmt_fuzzy = (
                select(Application)
                .join(Job, Application.job_id == Job.id)
                .where(
                    and_(
                        Application.user_id == user_id,
                        func.lower(Job.company_name) == job.company_name.lower().strip(),
                        func.lower(Job.title) == job.title.lower().strip()
                    )
                )
            )
            res_fuzzy = await db.execute(stmt_fuzzy)
            app_fuzzy = res_fuzzy.scalar_one_or_none()
            if app_fuzzy:
                return True, app_fuzzy.id, f"Candidate already has an active application for '{job.title}' at {job.company_name}."

        return False, None, None

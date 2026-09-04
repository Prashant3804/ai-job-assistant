import uuid
from typing import Tuple, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.resume import Resume, ResumeVersion
from app.database.models.job import Job

class ResumeSelectionService:
    """Selects the most suitable tailored resume version for a target job application."""

    @staticmethod
    async def select_best_resume(
        user_id: uuid.UUID,
        job: Job,
        db: AsyncSession
    ) -> Tuple[Optional[uuid.UUID], Optional[uuid.UUID], str]:
        # 1. Check for a version explicitly tailored for this specific job ID
        stmt_job_tailored = (
            select(ResumeVersion)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .where(
                and_(
                    Resume.user_id == user_id,
                    ResumeVersion.tailored_for_job_id == job.id
                )
            )
            .order_by(ResumeVersion.version_number.desc())
        )
        res_job_tailored = await db.execute(stmt_job_tailored)
        tailored_ver = res_job_tailored.scalar_one_or_none()
        if tailored_ver:
            return tailored_ver.resume_id, tailored_ver.id, f"Tailored Version v{tailored_ver.version_number} (Job Match)"

        # 2. Check all available resume versions for domain/role alignment
        stmt_versions = (
            select(ResumeVersion, Resume)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .where(Resume.user_id == user_id)
            .order_by(ResumeVersion.version_number.desc())
        )
        res_versions = await db.execute(stmt_versions)
        version_pairs = res_versions.all()

        job_title_lower = (job.title or "").lower()

        # Keywords mapping to tailored specialties
        role_clusters = {
            "frontend": ["frontend", "react", "vue", "angular", "ui", "web"],
            "backend": ["backend", "python", "fastapi", "django", "java", "golang", "node", "api"],
            "machine learning": ["machine learning", "ml", "ai", "data scientist", "deep learning", "llm"],
            "devops": ["devops", "cloud", "aws", "kubernetes", "k8s", "infrastructure", "sre"],
            "full stack": ["full stack", "fullstack", "software engineer"]
        }

        for cluster_name, keywords in role_clusters.items():
            if any(kw in job_title_lower for kw in keywords):
                for ver, res in version_pairs:
                    content_str = str(ver.tailored_content or "").lower()
                    if cluster_name in content_str or any(kw in content_str for kw in keywords):
                        return res.id, ver.id, f"{res.title} (v{ver.version_number} - {cluster_name.title()} Focus)"

        # 3. Fallback to Primary Resume latest version
        stmt_primary = (
            select(Resume)
            .where(and_(Resume.user_id == user_id, Resume.is_primary == True)) # noqa: E712
        )
        res_primary = await db.execute(stmt_primary)
        primary_resume = res_primary.scalar_one_or_none()

        if primary_resume:
            # Check if primary has any version
            stmt_v = (
                select(ResumeVersion)
                .where(ResumeVersion.resume_id == primary_resume.id)
                .order_by(ResumeVersion.version_number.desc())
            )
            res_v = await db.execute(stmt_v)
            latest_v = res_v.scalar_one_or_none()
            return primary_resume.id, (latest_v.id if latest_v else None), primary_resume.title

        # 4. Fallback to any user resume
        stmt_any = select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        res_any = await db.execute(stmt_any)
        any_resume = res_any.scalar_one_or_none()
        if any_resume:
            return any_resume.id, None, any_resume.title

        return None, None, "No Resume Found"

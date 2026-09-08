import logging
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.session import AsyncSessionLocal
from app.database.models.job import Job
from app.database.models.user import UserProfile
from app.modules.jobs.discovery.tech_extractor import extract_technologies
from app.modules.resume.date_utils import calculate_total_experience_years

logger = logging.getLogger("app.jobs.data_sync")

async def sync_database_normalization() -> None:
    """Safely re-normalizes existing jobs and candidate profiles in the database."""
    try:
        async with AsyncSessionLocal() as db:
            # 1. Re-normalize UserProfiles with 0 experience or missing target roles
            prof_stmt = select(UserProfile).options(
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.skills)
            )
            prof_res = await db.execute(prof_stmt)
            profiles = prof_res.scalars().all()

            profiles_updated = 0
            for prof in profiles:
                changed = False
                # Fix years of experience
                if (not prof.years_of_experience or float(prof.years_of_experience) <= 0.0) and prof.experiences:
                    derived_years = calculate_total_experience_years(prof.experiences)
                    if derived_years > 0.0:
                        prof.years_of_experience = derived_years
                        changed = True

                # Fix fallback target roles if empty
                if not prof.target_roles and prof.headline:
                    prof.target_roles = [prof.headline]
                    changed = True

                if changed:
                    profiles_updated += 1

            # 2. Re-normalize Jobs containing company names or generic skills
            job_stmt = select(Job)
            job_res = await db.execute(job_stmt)
            jobs = job_res.scalars().all()

            jobs_updated = 0
            for job in jobs:
                old_skills = list(job.required_skills or [])
                cleaned_skills = extract_technologies(
                    job.title,
                    job.description or "",
                    existing_skills=old_skills
                )
                if set(cleaned_skills) != set(old_skills):
                    job.required_skills = cleaned_skills
                    jobs_updated += 1

            if profiles_updated > 0 or jobs_updated > 0:
                await db.commit()
                logger.info(
                    f"[data_sync] Successfully synchronized normalization: "
                    f"{profiles_updated} candidate profiles, {jobs_updated} jobs updated."
                )
            else:
                logger.info("[data_sync] Normalization sync checked: all data is up-to-date.")
    except Exception as e:
        logger.warning(f"[data_sync] Non-fatal error during normalization sync: {e}")

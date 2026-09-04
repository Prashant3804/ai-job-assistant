import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.user import (
    User,
    UserProfile,
    CandidateSkill,
    Education,
    Experience,
    Project,
)
from app.database.models.resume import Resume, ResumeVersion
from app.modules.resume.schemas import (
    SaveProfileRequest,
    CreateResumeVersionRequest,
    StructuredResumeData,
    ResumeVersionResponse,
)
from app.core.exceptions import EntityNotFoundError

class CandidateProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_approved_profile(self, user_id: uuid.UUID, payload: SaveProfileRequest) -> UserProfile:
        """Saves user-approved structured candidate profile to relational database tables."""
        # 1. Fetch or create UserProfile
        stmt_profile = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await self.db.execute(stmt_profile)
        profile = prof_res.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()

        # Update User full name if provided
        if payload.personal.name:
            user = await self.db.get(User, user_id)
            if user:
                user.full_name = payload.personal.name

        # Update Profile fields
        profile.headline = payload.personal.headline or profile.headline
        profile.summary = payload.personal.summary or profile.summary
        profile.location = payload.personal.location or profile.location
        profile.linkedin_url = payload.personal.linkedin_url or profile.linkedin_url
        profile.github_url = payload.personal.github_url or profile.github_url
        profile.portfolio_url = payload.personal.portfolio_url or profile.portfolio_url

        # 2. Synchronize Skills
        await self.db.execute(delete(CandidateSkill).where(CandidateSkill.user_profile_id == profile.id))
        
        skill_mappings = [
            (payload.skills.programming_languages, "TECHNICAL", 4.0),
            (payload.skills.frameworks, "TECHNICAL", 3.0),
            (payload.skills.databases, "TECHNICAL", 3.0),
            (payload.skills.cloud, "TOOL", 3.0),
            (payload.skills.tools, "TOOL", 3.0),
            (payload.skills.soft_skills, "SOFT_SKILL", 5.0),
        ]

        seen_skills = set()
        for skill_list, category, default_exp in skill_mappings:
            for skill_name in skill_list:
                clean_name = skill_name.strip()
                if clean_name and clean_name.lower() not in seen_skills:
                    seen_skills.add(clean_name.lower())
                    self.db.add(CandidateSkill(
                        user_profile_id=profile.id,
                        name=clean_name,
                        category=category,
                        proficiency_level="ADVANCED",
                        years_experience=default_exp,
                        is_verified=True
                    ))

        # 3. Synchronize Educations
        await self.db.execute(delete(Education).where(Education.user_profile_id == profile.id))
        for edu in payload.education:
            self.db.add(Education(
                user_profile_id=profile.id,
                institution=edu.institution,
                degree=edu.degree,
                field_of_study=edu.field_of_study or "Computer Science",
                start_date=edu.start_date,
                end_date=edu.end_date or edu.graduation_year,
                gpa=edu.cgpa,
                description=edu.description
            ))

        # 4. Synchronize Experiences
        await self.db.execute(delete(Experience).where(Experience.user_profile_id == profile.id))
        for exp in payload.experience:
            self.db.add(Experience(
                user_profile_id=profile.id,
                company_name=exp.company,
                title=exp.role,
                employment_type="FULL_TIME",
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                bullet_points=exp.responsibilities,
                technologies=exp.technologies
            ))

        # 5. Synchronize Projects
        await self.db.execute(delete(Project).where(Project.user_profile_id == profile.id))
        for proj in payload.projects:
            self.db.add(Project(
                user_profile_id=profile.id,
                title=proj.name,
                description=proj.description,
                technologies=proj.technologies,
                url=proj.links[0] if proj.links else None,
                github_url=proj.links[0] if proj.links and "github" in proj.links[0] else None
            ))

        # 6. Update Resume record parsed_data if resume_id provided
        if payload.resume_id:
            resume = await self.db.get(Resume, payload.resume_id)
            if resume and resume.user_id == user_id:
                resume.parsed_data = payload.model_dump(mode="json")

        await self.db.commit()

        # Reload profile with relationships
        stmt_reload = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.projects),
            )
            .where(UserProfile.id == profile.id)
        )
        res = await self.db.execute(stmt_reload)
        return res.scalar_one()

    async def update_candidate_profile(self, user_id: uuid.UUID, payload: Any) -> UserProfile:
        """Updates user profile directly from review form and marks source as USER_CONFIRMED."""
        stmt = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.projects),
            )
            .where(UserProfile.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()

        if getattr(payload, "full_name", None):
            user = await self.db.get(User, user_id)
            if user:
                user.full_name = payload.full_name

        profile.headline = getattr(payload, "headline", profile.headline) or profile.headline
        profile.summary = getattr(payload, "summary", profile.summary) or profile.summary
        profile.location = getattr(payload, "location", profile.location) or profile.location
        profile.country = getattr(payload, "country", profile.country) or profile.country
        profile.phone = getattr(payload, "phone", profile.phone) or profile.phone
        profile.remote_preference = getattr(payload, "remote_preference", profile.remote_preference) or profile.remote_preference
        profile.target_roles = getattr(payload, "target_roles", profile.target_roles) or profile.target_roles
        profile.preferred_roles = getattr(payload, "preferred_roles", profile.preferred_roles) or profile.preferred_roles
        profile.preferred_locations = getattr(payload, "preferred_locations", profile.preferred_locations) or profile.preferred_locations
        profile.preferred_work_arrangement = getattr(payload, "preferred_work_arrangement", profile.preferred_work_arrangement) or profile.preferred_work_arrangement
        profile.years_of_experience = getattr(payload, "years_of_experience", profile.years_of_experience) or profile.years_of_experience
        profile.work_authorization = getattr(payload, "work_authorization", profile.work_authorization) or profile.work_authorization
        profile.notice_period = getattr(payload, "notice_period", profile.notice_period) or profile.notice_period
        profile.salary_expectation = getattr(payload, "salary_expectation", profile.salary_expectation) or profile.salary_expectation
        profile.source = "USER_CONFIRMED"
        profile.linkedin_url = getattr(payload, "linkedin_url", profile.linkedin_url) or profile.linkedin_url
        profile.github_url = getattr(payload, "github_url", profile.github_url) or profile.github_url
        profile.portfolio_url = getattr(payload, "portfolio_url", profile.portfolio_url) or profile.portfolio_url

        if getattr(payload, "skills", None) is not None and len(payload.skills) > 0:
            profile.skills = [
                CandidateSkill(
                    user_profile_id=profile.id,
                    name=sk.name if hasattr(sk, "name") else str(sk),
                    category=getattr(sk, "category", "TECHNICAL"),
                    proficiency_level=getattr(sk, "proficiency_level", "ADVANCED"),
                    years_experience=getattr(sk, "years_experience", 1.0),
                    is_verified=True
                )
                for sk in payload.skills
            ]

        if getattr(payload, "educations", None) is not None and len(payload.educations) > 0:
            profile.educations = [
                Education(
                    user_profile_id=profile.id,
                    institution=edu.institution,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    gpa=edu.gpa,
                    description=edu.description
                )
                for edu in payload.educations
            ]

        if getattr(payload, "experiences", None) is not None and len(payload.experiences) > 0:
            profile.experiences = [
                Experience(
                    user_profile_id=profile.id,
                    company_name=exp.company_name,
                    title=exp.title,
                    location=exp.location,
                    employment_type=exp.employment_type,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    description=exp.description,
                    bullet_points=exp.bullet_points,
                    technologies=exp.technologies
                )
                for exp in payload.experiences
            ]

        if getattr(payload, "projects", None) is not None and len(payload.projects) > 0:
            profile.projects = [
                Project(
                    user_profile_id=profile.id,
                    title=prj.title,
                    description=prj.description,
                    url=prj.url,
                    github_url=prj.github_url,
                    technologies=prj.technologies,
                    start_date=prj.start_date,
                    end_date=prj.end_date
                )
                for prj in payload.projects
            ]

        await self.db.commit()

        stmt_reload = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.projects),
            )
            .where(UserProfile.id == profile.id)
        )
        res = await self.db.execute(stmt_reload)
        return res.scalar_one()

    async def create_resume_version(self, user_id: uuid.UUID, payload: CreateResumeVersionRequest) -> ResumeVersion:
        """Creates a snapshot version of the resume tailored for specific job or general purpose."""
        resume = await self.db.get(Resume, payload.resume_id)
        if not resume or resume.user_id != user_id:
            raise EntityNotFoundError("Resume", payload.resume_id)

        # Get current highest version number
        stmt = select(func.max(ResumeVersion.version_number)).where(ResumeVersion.resume_id == payload.resume_id)
        max_v_res = await self.db.execute(stmt)
        current_max = max_v_res.scalar() or 0

        version = ResumeVersion(
            resume_id=payload.resume_id,
            version_number=current_max + 1,
            tailored_for_job_id=payload.tailored_for_job_id,
            tailored_content=payload.structured_data.model_dump(mode="json"),
            file_url=resume.file_url
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def get_resume_versions(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> List[ResumeVersion]:
        stmt = (
            select(ResumeVersion)
            .join(ResumeVersion.resume)
            .where(and_(ResumeVersion.resume_id == resume_id, Resume.user_id == user_id))
            .order_by(ResumeVersion.version_number.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())


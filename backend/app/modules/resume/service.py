import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.user import User, UserProfile, CandidateSkill, Education, Experience, Project
from app.database.models.resume import Resume, ResumeVersion
from app.modules.ai.service import BaseLLMService, get_ai_service
from app.shared.schemas import UserProfileUpdate, UserProfileRead, ResumeRead

class ResumeService:
    def __init__(self, db: AsyncSession, ai_service: Optional[BaseLLMService] = None):
        self.db = db
        self.ai = ai_service or get_ai_service()

    async def extract_structured_resume(self, raw_text: str) -> Dict[str, Any]:
        """Parses raw resume text into structured candidate profile data using dynamic AI extraction."""
        from app.modules.resume.extraction_service import ResumeExtractionService
        extractor = ResumeExtractionService(ai_service=self.ai)
        structured = await extractor.extract_and_structure_resume(raw_text)

        skills_list = []
        if structured.skills:
            categories_map = [
                ("TECHNICAL", structured.skills.programming_languages),
                ("TECHNICAL", structured.skills.frameworks),
                ("TECHNICAL", structured.skills.databases),
                ("TOOL", structured.skills.cloud),
                ("TOOL", structured.skills.tools),
                ("SOFT", structured.skills.soft_skills),
            ]
            for cat, items in categories_map:
                for item in items:
                    skills_list.append({
                        "name": item,
                        "category": cat,
                        "proficiency_level": "ADVANCED",
                        "years_experience": 2.0
                    })

        experiences_list = []
        for exp in structured.experience:
            experiences_list.append({
                "company_name": exp.company,
                "title": exp.role,
                "location": getattr(exp, "location", None),
                "employment_type": "FULL_TIME",
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "is_current": exp.is_current,
                "description": " ".join(exp.responsibilities) if exp.responsibilities else None,
                "bullet_points": exp.responsibilities,
                "technologies": exp.technologies
            })

        educations_list = []
        for edu in structured.education:
            educations_list.append({
                "institution": edu.institution,
                "degree": edu.degree,
                "field_of_study": edu.field_of_study,
                "start_date": edu.start_date,
                "end_date": edu.graduation_year or edu.end_date,
                "gpa": edu.cgpa,
                "description": getattr(edu, "description", None)
            })

        projects_list = []
        for proj in structured.projects:
            projects_list.append({
                "title": proj.name,
                "description": proj.description,
                "url": proj.links[0] if proj.links else None,
                "github_url": next((l for l in proj.links if "github" in l.lower()), None) if proj.links else None,
                "technologies": proj.technologies,
                "start_date": proj.start_date,
                "end_date": proj.end_date
            })

        return {
            "full_name": structured.personal.name if structured.personal else None,
            "headline": structured.personal.headline or "Software Engineer",
            "summary": structured.personal.summary or "Professional candidate profile.",
            "location": structured.personal.location or "Remote",
            "years_of_experience": structured.total_years_experience or 1.0,
            "skills": skills_list,
            "experiences": experiences_list,
            "educations": educations_list,
            "projects": projects_list,
        }

    async def save_and_apply_resume(self, user_id: uuid.UUID, title: str, raw_text: str, file_format: str = "PDF", file_url: Optional[str] = None) -> Resume:
        parsed_data = await self.extract_structured_resume(raw_text)

        # Mark older primary resumes as non-primary
        stmt_reset = select(Resume).where(Resume.user_id == user_id)
        res = await self.db.execute(stmt_reset)
        for r in res.scalars():
            r.is_primary = False

        resume = Resume(
            user_id=user_id,
            title=title,
            is_primary=True,
            raw_text=raw_text,
            file_url=file_url,
            file_format=file_format,
            parsed_data=parsed_data
        )
        self.db.add(resume)
        await self.db.flush()

        # Update or create user profile based on parsed data
        stmt_profile = select(UserProfile).where(UserProfile.user_id == user_id)
        prof_res = await self.db.execute(stmt_profile)
        profile = prof_res.scalar_one_or_none()

        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            await self.db.flush()

        profile.headline = parsed_data.get("headline", profile.headline)
        profile.summary = parsed_data.get("summary", profile.summary)
        profile.location = parsed_data.get("location", profile.location)
        profile.years_of_experience = float(parsed_data.get("years_of_experience", profile.years_of_experience))

        # Clear existing child records and populate fresh parsed ones
        await self.db.execute(delete(CandidateSkill).where(CandidateSkill.user_profile_id == profile.id))
        await self.db.execute(delete(Education).where(Education.user_profile_id == profile.id))
        await self.db.execute(delete(Experience).where(Experience.user_profile_id == profile.id))
        await self.db.execute(delete(Project).where(Project.user_profile_id == profile.id))

        for sk in parsed_data.get("skills", []):
            self.db.add(CandidateSkill(
                user_profile_id=profile.id,
                name=sk["name"],
                category=sk.get("category", "TECHNICAL"),
                proficiency_level=sk.get("proficiency_level", "ADVANCED"),
                years_experience=float(sk.get("years_experience", 1.0)),
                is_verified=True
            ))

        for exp in parsed_data.get("experiences", []):
            self.db.add(Experience(
                user_profile_id=profile.id,
                company_name=exp["company_name"],
                title=exp["title"],
                location=exp.get("location"),
                employment_type=exp.get("employment_type", "FULL_TIME"),
                start_date=exp.get("start_date"),
                end_date=exp.get("end_date"),
                is_current=exp.get("is_current", False),
                description=exp.get("description"),
                bullet_points=exp.get("bullet_points", []),
                technologies=exp.get("technologies", [])
            ))

        for edu in parsed_data.get("educations", []):
            self.db.add(Education(
                user_profile_id=profile.id,
                institution=edu["institution"],
                degree=edu["degree"],
                field_of_study=edu["field_of_study"],
                start_date=edu.get("start_date"),
                end_date=edu.get("end_date"),
                gpa=edu.get("gpa"),
                description=edu.get("description")
            ))

        for proj in parsed_data.get("projects", []):
            self.db.add(Project(
                user_profile_id=profile.id,
                title=proj["title"],
                description=proj.get("description"),
                url=proj.get("url"),
                github_url=proj.get("github_url"),
                technologies=proj.get("technologies", []),
                start_date=proj.get("start_date"),
                end_date=proj.get("end_date")
            ))

        await self.db.commit()
        await self.db.refresh(resume)
        return resume

    async def get_user_resumes(self, user_id: uuid.UUID) -> List[Resume]:
        stmt = select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_user_profile(self, user_id: uuid.UUID) -> Optional[UserProfile]:
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
        return res.scalar_one_or_none()

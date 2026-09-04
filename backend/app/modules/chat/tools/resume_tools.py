import uuid
from typing import Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.user import User, UserProfile, CandidateSkill, Education, Experience, Project, JobPreference
from app.database.models.resume import Resume, ResumeVersion
from app.modules.chat.tools.base import BaseTool, ToolResult
from app.modules.chat.tools.schemas import (
    GetCandidateProfileInput,
    GetResumeVersionsInput,
    GetActiveResumeInput,
    GetCandidateSkillsInput,
    GetCandidateExperienceInput,
    GetCandidateEducationInput,
    GetCandidateProjectsInput,
)

class GetCandidateProfileTool(BaseTool):
    name = "get_candidate_profile"
    description = "Retrieve the authenticated candidate master profile including headline, experience years, skills, education, and target roles."
    category = "RESUME"
    parameters_schema = GetCandidateProfileInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCandidateProfileInput) -> ToolResult:
        stmt = (
            select(UserProfile)
            .options(
                selectinload(UserProfile.skills),
                selectinload(UserProfile.educations),
                selectinload(UserProfile.experiences),
                selectinload(UserProfile.projects)
            )
            .where(UserProfile.user_id == user_id)
        )
        res = await db.execute(stmt)
        profile = res.scalar_one_or_none()

        if not profile:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="No candidate profile has been created yet. The user should upload a resume.",
                data={"profile_exists": False}
            )

        data = {
            "profile_exists": True,
            "headline": profile.headline or "Software Engineer",
            "summary": profile.summary,
            "years_of_experience": profile.years_of_experience,
            "location": profile.location,
            "remote_preference": profile.remote_preference,
            "target_roles": profile.target_roles or [],
        }

        if params.include_skills:
            data["skills"] = [s.name for s in profile.skills]
        if params.include_experiences:
            data["experiences"] = [
                {
                    "title": exp.title,
                    "company": exp.company_name,
                    "duration": f"{exp.start_date or ''} - {exp.end_date or 'Present'}",
                    "skills": exp.technologies or []
                }
                for exp in profile.experiences
            ]
        if params.include_educations:
            data["educations"] = [
                {
                    "degree": ed.degree,
                    "field": ed.field_of_study,
                    "institution": ed.institution,
                    "end_date": ed.end_date
                }
                for ed in profile.educations
            ]

        summary = f"Candidate Profile: {data['headline']} ({data['years_of_experience']} yrs exp) in {data['location'] or 'Remote'}. {len(data.get('skills', []))} skills listed."
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)

class GetResumeVersionsTool(BaseTool):
    name = "get_resume_versions"
    description = "List all stored resume versions and tailored copies for the candidate."
    category = "RESUME"
    parameters_schema = GetResumeVersionsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetResumeVersionsInput) -> ToolResult:
        stmt = select(Resume).options(selectinload(Resume.versions)).where(Resume.user_id == user_id)
        res = await db.execute(stmt)
        resumes = list(res.scalars().all())

        if not resumes:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="No resumes found in the user account.",
                data={"resumes": []}
            )

        output = []
        for r in resumes:
            versions_data = [
                {"version_number": v.version_number, "id": str(v.id), "file_url": v.file_url}
                for v in r.versions
            ]
            output.append({
                "resume_id": str(r.id),
                "title": r.title,
                "is_primary": r.is_primary,
                "format": r.file_format,
                "version_count": len(r.versions),
                "versions": versions_data
            })

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(output)} resume(s) with version history.",
            data={"resumes": output}
        )

class GetActiveResumeTool(BaseTool):
    name = "get_active_resume"
    description = "Fetch the candidate's active/primary resume parsed structured data and raw text."
    category = "RESUME"
    parameters_schema = GetActiveResumeInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetActiveResumeInput) -> ToolResult:
        stmt = (
            select(Resume)
            .options(selectinload(Resume.versions))
            .where(Resume.user_id == user_id)
            .order_by(Resume.is_primary.desc(), Resume.updated_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        resume = res.scalar_one_or_none()

        if not resume:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="No active resume uploaded yet.",
                data={"has_active_resume": False}
            )

        data = {
            "has_active_resume": True,
            "resume_id": str(resume.id),
            "title": resume.title,
            "file_format": resume.file_format,
            "parsed_data": resume.parsed_data or {},
            "raw_text_snippet": (resume.raw_text or "")[:500]
        }
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Active Resume: '{resume.title}' ({resume.file_format})",
            data=data
        )

class GetCandidateSkillsTool(BaseTool):
    name = "get_candidate_skills"
    description = "List verified and extracted skills for the candidate, grouped or filtered by category."
    category = "RESUME"
    parameters_schema = GetCandidateSkillsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCandidateSkillsInput) -> ToolResult:
        stmt = select(UserProfile).where(UserProfile.user_id == user_id)
        p_res = await db.execute(stmt)
        profile = p_res.scalar_one_or_none()

        if not profile:
            return ToolResult(tool_name=self.name, success=True, summary="No candidate profile found.", data={"skills": []})

        stmt_skills = select(CandidateSkill).where(CandidateSkill.user_profile_id == profile.id)
        if params.category:
            stmt_skills = stmt_skills.where(CandidateSkill.category.ilike(f"%{params.category}%"))
        s_res = await db.execute(stmt_skills)
        skills = list(s_res.scalars().all())

        skill_list = [
            {"name": s.name, "category": s.category, "proficiency": s.proficiency_level, "years": s.years_experience}
            for s in skills
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(skill_list)} skill(s) for candidate.",
            data={"skills": skill_list, "skill_names": [s["name"] for s in skill_list]}
        )

class GetCandidateExperienceTool(BaseTool):
    name = "get_candidate_experience"
    description = "Retrieve candidate work experience history, companies, roles, and duration."
    category = "RESUME"
    parameters_schema = GetCandidateExperienceInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCandidateExperienceInput) -> ToolResult:
        stmt = select(UserProfile).options(selectinload(UserProfile.experiences)).where(UserProfile.user_id == user_id)
        p_res = await db.execute(stmt)
        profile = p_res.scalar_one_or_none()

        if not profile or not profile.experiences:
            return ToolResult(tool_name=self.name, success=True, summary="No work experience records found.", data={"experiences": []})

        exp_data = [
            {
                "title": exp.title,
                "company": exp.company_name,
                "location": exp.location,
                "start_date": exp.start_date,
                "end_date": exp.end_date or "Present",
                "technologies": exp.technologies or []
            }
            for exp in profile.experiences
        ]
        return ToolResult(tool_name=self.name, success=True, summary=f"Found {len(exp_data)} work experience position(s).", data={"experiences": exp_data})

class GetCandidateEducationTool(BaseTool):
    name = "get_candidate_education"
    description = "Retrieve candidate academic qualifications, degrees, institutions, and graduation years."
    category = "RESUME"
    parameters_schema = GetCandidateEducationInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCandidateEducationInput) -> ToolResult:
        stmt = select(UserProfile).options(selectinload(UserProfile.educations)).where(UserProfile.user_id == user_id)
        p_res = await db.execute(stmt)
        profile = p_res.scalar_one_or_none()

        if not profile or not profile.educations:
            return ToolResult(tool_name=self.name, success=True, summary="No education records found.", data={"educations": []})

        ed_data = [
            {
                "degree": ed.degree,
                "field_of_study": ed.field_of_study,
                "institution": ed.institution,
                "end_date": ed.end_date,
                "gpa": ed.gpa
            }
            for ed in profile.educations
        ]
        return ToolResult(tool_name=self.name, success=True, summary=f"Found {len(ed_data)} education record(s).", data={"educations": ed_data})

class GetCandidateProjectsTool(BaseTool):
    name = "get_candidate_projects"
    description = "Retrieve candidate portfolio projects, repositories, descriptions, and technologies used."
    category = "RESUME"
    parameters_schema = GetCandidateProjectsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCandidateProjectsInput) -> ToolResult:
        stmt = select(UserProfile).options(selectinload(UserProfile.projects)).where(UserProfile.user_id == user_id)
        p_res = await db.execute(stmt)
        profile = p_res.scalar_one_or_none()

        if not profile or not profile.projects:
            return ToolResult(tool_name=self.name, success=True, summary="No portfolio projects found.", data={"projects": []})

        proj_data = [
            {
                "title": p.title,
                "description": p.description,
                "technologies": p.technologies or [],
                "github_url": p.github_url,
                "url": p.url
            }
            for p in profile.projects
        ]
        return ToolResult(tool_name=self.name, success=True, summary=f"Found {len(proj_data)} project(s).", data={"projects": proj_data})

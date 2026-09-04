import uuid
from typing import Dict, Any, List
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.job import Job, JobSource
from app.modules.jobs.service import JobService
from app.modules.chat.tools.base import BaseTool, ToolResult
from app.modules.chat.tools.schemas import (
    SearchJobsInput,
    GetJobDetailsInput,
    GetJobsBySourceInput,
    GetJobsByLocationInput,
    GetJobsByRoleInput,
    GetJobsBySalaryInput,
)

def _format_job_item(job: Job) -> Dict[str, Any]:
    source_name = job.job_source.name if job.job_source else (job.source if hasattr(job, 'source') else 'Direct')
    salary_str = "Not specified"
    if job.salary_min and job.salary_max:
        salary_str = f"{job.salary_currency} {job.salary_min:,} - {job.salary_max:,}"
    elif job.salary_min:
        salary_str = f"{job.salary_currency} {job.salary_min:,}+"

    return {
        "job_id": str(job.id),
        "title": job.title,
        "company": job.company_name,
        "location": job.location or "Remote",
        "remote_type": job.remote_type,
        "source": source_name,
        "source_slug": job.job_source.slug if job.job_source else "direct",
        "salary_range": salary_str,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "experience_level": job.experience_level,
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "apply_url": job.apply_url,
        "description_snippet": (job.description or "")[:200]
    }

class SearchJobsTool(BaseTool):
    name = "search_jobs"
    description = "Search normalized jobs by title/keywords, location, remote preference, minimum salary, experience level, or source platform."
    category = "JOB"
    parameters_schema = SearchJobsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: SearchJobsInput) -> ToolResult:
        service = JobService(db)
        jobs, total = await service.list_jobs_advanced(
            query=params.query,
            location=params.location,
            remote_type=params.remote_type,
            experience_level=params.experience_level,
            min_salary=params.min_salary,
            source=params.source,
            limit=params.limit,
            offset=0
        )

        formatted = [_format_job_item(j) for j in jobs]
        summary = f"Found {len(formatted)} job(s) matching criteria (total in database: {total})."
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=summary,
            data={"jobs": formatted, "count": len(formatted), "total_available": total}
        )

class GetJobDetailsTool(BaseTool):
    name = "get_job_details"
    description = "Retrieve full description, requirements, company info, and salary for a specific job."
    category = "JOB"
    parameters_schema = GetJobDetailsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobDetailsInput) -> ToolResult:
        stmt = select(Job).options(selectinload(Job.job_source))
        if params.job_id:
            try:
                stmt = stmt.where(Job.id == uuid.UUID(params.job_id))
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid job UUID format.", error="INVALID_UUID")
        elif params.company_name and params.job_title:
            stmt = stmt.where(
                func.lower(Job.company_name).like(f"%{params.company_name.lower()}%"),
                func.lower(Job.title).like(f"%{params.job_title.lower()}%")
            )
        elif params.job_title:
            stmt = stmt.where(func.lower(Job.title).like(f"%{params.job_title.lower()}%"))
        else:
            return ToolResult(tool_name=self.name, success=False, summary="Please provide either job_id or company/title to look up.", error="MISSING_SEARCH_PARAM")

        res = await db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="Job could not be found with the given identifiers.",
                data={"found": False}
            )

        data = _format_job_item(job)
        data["full_description"] = job.description
        data["found"] = True
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Job Details: '{job.title}' at {job.company_name} ({job.location or 'Remote'})",
            data=data
        )

class GetJobsBySourceTool(BaseTool):
    name = "get_jobs_by_source"
    description = "Find jobs discovered from a specific source connector (e.g. greenhouse, lever, linkedin, indeed, naukri, unstop, internshala, wellfound)."
    category = "JOB"
    parameters_schema = GetJobsBySourceInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobsBySourceInput) -> ToolResult:
        service = JobService(db)
        jobs, total = await service.list_jobs_advanced(source=params.source, limit=params.limit)
        formatted = [_format_job_item(j) for j in jobs]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(formatted)} job(s) from source '{params.source}'.",
            data={"jobs": formatted, "source": params.source, "count": len(formatted)}
        )

class GetJobsByLocationTool(BaseTool):
    name = "get_jobs_by_location"
    description = "Find jobs based on geographical location (city, state, country) or remote status."
    category = "JOB"
    parameters_schema = GetJobsByLocationInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobsByLocationInput) -> ToolResult:
        service = JobService(db)
        jobs, total = await service.list_jobs_advanced(
            location=params.location,
            remote_type=params.remote_type,
            limit=params.limit
        )
        formatted = [_format_job_item(j) for j in jobs]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(formatted)} job(s) in/near '{params.location}'.",
            data={"jobs": formatted, "location": params.location, "count": len(formatted)}
        )

class GetJobsByRoleTool(BaseTool):
    name = "get_jobs_by_role"
    description = "Find jobs matching a specific role or occupational title (e.g. Backend Engineer, Full Stack, Data Scientist)."
    category = "JOB"
    parameters_schema = GetJobsByRoleInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobsByRoleInput) -> ToolResult:
        service = JobService(db)
        jobs, total = await service.list_jobs_advanced(query=params.role, limit=params.limit)
        formatted = [_format_job_item(j) for j in jobs]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(formatted)} job(s) for role '{params.role}'.",
            data={"jobs": formatted, "role": params.role, "count": len(formatted)}
        )

class GetJobsBySalaryTool(BaseTool):
    name = "get_jobs_by_salary"
    description = "Find jobs meeting or exceeding a specific minimum base salary."
    category = "JOB"
    parameters_schema = GetJobsBySalaryInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobsBySalaryInput) -> ToolResult:
        service = JobService(db)
        jobs, total = await service.list_jobs_advanced(min_salary=params.min_salary, limit=params.limit)
        formatted = [_format_job_item(j) for j in jobs]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(formatted)} job(s) with salary >= {params.currency} {params.min_salary:,}.",
            data={"jobs": formatted, "min_salary": params.min_salary, "currency": params.currency, "count": len(formatted)}
        )

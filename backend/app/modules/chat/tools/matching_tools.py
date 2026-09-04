import uuid
from typing import Dict, Any, List
from collections import Counter
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.user import User
from app.database.models.job import Job
from app.database.models.match import JobMatch
from app.modules.matching.service import MatchingService
from app.modules.matching.schemas import MatchFilterParams
from app.modules.chat.tools.base import BaseTool, ToolResult
from app.modules.chat.tools.schemas import (
    GetJobMatchInput,
    GetRecommendedJobsInput,
    GetMatchHistoryInput,
    GetMissingSkillsInput,
    ExplainJobMatchInput,
)

def _format_match_item(match: JobMatch) -> Dict[str, Any]:
    job = match.job
    source_name = job.job_source.name if job and job.job_source else "Direct"
    return {
        "match_id": str(match.id),
        "job_id": str(match.job_id),
        "job_title": job.title if job else "Unknown Job",
        "company": job.company_name if job else "Unknown Company",
        "location": job.location if job else "Remote",
        "remote_type": job.remote_type if job else "REMOTE",
        "source": source_name,
        "overall_score": match.overall_score,
        "skill_score": match.skill_score,
        "experience_score": match.experience_score,
        "education_score": match.education_score,
        "location_score": match.location_score,
        "role_score": match.role_score,
        "salary_score": match.salary_score,
        "eligibility_status": match.eligibility_status,
        "recommendation": match.recommendation,
        "matched_skills": match.matched_skills or [],
        "missing_required_skills": match.missing_required_skills or [],
        "missing_preferred_skills": match.missing_preferred_skills or [],
        "explanation": match.explanation,
        "confidence": match.confidence,
        "is_bookmarked": match.is_bookmarked,
    }

class GetJobMatchTool(BaseTool):
    name = "get_job_match"
    description = "Calculate or retrieve the explainable match score (0-100%) and 6-dimension breakdown for a candidate against a job."
    category = "MATCHING"
    parameters_schema = GetJobMatchInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetJobMatchInput) -> ToolResult:
        user = await db.get(User, user_id)
        if not user:
            return ToolResult(tool_name=self.name, success=False, summary="User not found.", error="USER_NOT_FOUND")

        stmt = select(Job).options(selectinload(Job.job_source))
        if params.job_id:
            try:
                stmt = stmt.where(Job.id == uuid.UUID(params.job_id))
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid job UUID.", error="INVALID_UUID")
        elif params.job_title:
            stmt = stmt.where(func.lower(Job.title).like(f"%{params.job_title.lower()}%"))
        else:
            return ToolResult(tool_name=self.name, success=False, summary="Please provide a job ID or title.", error="MISSING_PARAM")

        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        if not job:
            return ToolResult(tool_name=self.name, success=True, summary="Job not found in database.", data={"match_found": False})

        service = MatchingService(db)
        match = await service.compute_or_update_match(user=user, job=job)
        await db.refresh(match, ["job"])

        data = _format_match_item(match)
        data["match_found"] = True
        summary = f"Match Score: {match.overall_score}% ({match.recommendation}, {match.eligibility_status}) for '{job.title}' at {job.company_name}."
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)

class GetRecommendedJobsTool(BaseTool):
    name = "get_recommended_jobs"
    description = "Retrieve the candidate's top recommended jobs ordered by match score (with optional minimum score or tier filter)."
    category = "MATCHING"
    parameters_schema = GetRecommendedJobsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetRecommendedJobsInput) -> ToolResult:
        user = await db.get(User, user_id)
        if not user:
            return ToolResult(tool_name=self.name, success=False, summary="User not found.", error="USER_NOT_FOUND")

        service = MatchingService(db)
        filters = MatchFilterParams(
            minimum_score=params.minimum_score,
            recommendation=params.recommendation,
            limit=params.limit
        )
        matches = await service.get_recommended_matches(user=user, filters=filters)
        formatted = [_format_match_item(m) for m in matches]

        summary = f"Retrieved {len(formatted)} recommended job match(es)"
        if params.minimum_score:
            summary += f" with score >= {params.minimum_score}%"
        summary += "."

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=summary,
            data={"matches": formatted, "count": len(formatted)}
        )

class GetMatchHistoryTool(BaseTool):
    name = "get_match_history"
    description = "List the candidate's historical job match evaluations."
    category = "MATCHING"
    parameters_schema = GetMatchHistoryInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetMatchHistoryInput) -> ToolResult:
        user = await db.get(User, user_id)
        if not user:
            return ToolResult(tool_name=self.name, success=False, summary="User not found.", error="USER_NOT_FOUND")

        service = MatchingService(db)
        filters = MatchFilterParams(limit=params.limit)
        matches = await service.get_match_history(user=user, filters=filters)
        formatted = [_format_match_item(m) for m in matches]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(formatted)} past match record(s).",
            data={"matches": formatted, "count": len(formatted)}
        )

class GetMissingSkillsTool(BaseTool):
    name = "get_missing_skills"
    description = "Analyze and rank missing skills across the candidate's target job matches, separating required vs preferred skills to prioritize learning."
    category = "MATCHING"
    parameters_schema = GetMissingSkillsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetMissingSkillsInput) -> ToolResult:
        user = await db.get(User, user_id)
        if not user:
            return ToolResult(tool_name=self.name, success=False, summary="User not found.", error="USER_NOT_FOUND")

        service = MatchingService(db)

        if params.job_id:
            # Single job skill gap
            try:
                job_uuid = uuid.UUID(params.job_id)
                job = await db.get(Job, job_uuid)
                if not job:
                    return ToolResult(tool_name=self.name, success=True, summary="Job not found.", data={"missing_skills": []})
                match = await service.compute_or_update_match(user=user, job=job)
                data = {
                    "job_title": job.title,
                    "company": job.company_name,
                    "overall_score": match.overall_score,
                    "matched_skills": match.matched_skills or [],
                    "missing_required_skills": match.missing_required_skills or [],
                    "missing_preferred_skills": match.missing_preferred_skills or [],
                }
                return ToolResult(
                    tool_name=self.name,
                    success=True,
                    summary=f"Missing for '{job.title}': Required={match.missing_required_skills}, Preferred={match.missing_preferred_skills}",
                    data=data
                )
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid job UUID.", error="INVALID_UUID")

        # Aggregate across top matches
        matches = await service.get_recommended_matches(user=user, filters=MatchFilterParams(limit=25))
        if not matches:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="No match records found to aggregate missing skills. Run job search first.",
                data={"top_missing_required": [], "top_missing_preferred": []}
            )

        req_counter = Counter()
        pref_counter = Counter()
        for m in matches:
            for s in (m.missing_required_skills or []):
                req_counter[s] += 1
            for s in (m.missing_preferred_skills or []):
                pref_counter[s] += 1

        top_req = [{"skill": s, "frequency": c, "type": "REQUIRED"} for s, c in req_counter.most_common(params.top_n)]
        top_pref = [{"skill": s, "frequency": c, "type": "PREFERRED"} for s, c in pref_counter.most_common(params.top_n)]

        summary = f"Top missing required skills across {len(matches)} matches: {', '.join([x['skill'] for x in top_req[:5]]) or 'None'}"
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=summary,
            data={
                "total_jobs_analyzed": len(matches),
                "top_missing_required": top_req,
                "top_missing_preferred": top_pref
            }
        )

class ExplainJobMatchTool(BaseTool):
    name = "explain_job_match"
    description = "Provide detailed breakdown, reasoning, strengths, and improvement areas for a specific job match."
    category = "MATCHING"
    parameters_schema = ExplainJobMatchInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ExplainJobMatchInput) -> ToolResult:
        user = await db.get(User, user_id)
        if not user:
            return ToolResult(tool_name=self.name, success=False, summary="User not found.", error="USER_NOT_FOUND")

        try:
            job_uuid = uuid.UUID(params.job_id)
        except ValueError:
            return ToolResult(tool_name=self.name, success=False, summary="Invalid job UUID format.", error="INVALID_UUID")

        job = await db.get(Job, job_uuid)
        if not job:
            return ToolResult(tool_name=self.name, success=True, summary="Job not found in database.", data={"found": False})

        service = MatchingService(db)
        match = await service.compute_or_update_match(user=user, job=job)
        await db.refresh(match, ["job"])

        data = {
            "job_id": str(job.id),
            "job_title": job.title,
            "company": job.company_name,
            "overall_score": match.overall_score,
            "recommendation": match.recommendation,
            "eligibility_status": match.eligibility_status,
            "dimension_scores": {
                "skills": match.skill_score,
                "experience": match.experience_score,
                "education": match.education_score,
                "location": match.location_score,
                "role": match.role_score,
                "salary": match.salary_score
            },
            "matched_skills": match.matched_skills or [],
            "missing_required": match.missing_required_skills or [],
            "missing_preferred": match.missing_preferred_skills or [],
            "explanation": match.explanation,
            "confidence": match.confidence,
        }

        summary = f"Match explanation for '{job.title}': {match.overall_score}% ({match.recommendation}). Explanation: {match.explanation}"
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)

import uuid
from typing import Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.application import Application
from app.database.models.job import Job
from app.database.models.match import JobMatch
from app.modules.chat.tools.base import BaseTool, ToolResult
from app.modules.chat.tools.schemas import (
    GetApplicationHistoryInput,
    GetApplicationStatusInput,
    GetApplicationStatisticsInput,
    GetAnalyticsOverviewInput,
    GetAutoApplyStatusInput,
    GetAutoApplyPolicyInput,
    GetApplicationDetailsInput,
)

class GetApplicationHistoryTool(BaseTool):
    name = "get_application_history"
    description = "Retrieve the candidate's existing job application records, company names, and current pipeline status (read-only)."
    category = "APPLICATION"
    parameters_schema = GetApplicationHistoryInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetApplicationHistoryInput) -> ToolResult:
        stmt = (
            select(Application)
            .options(selectinload(Application.job))
            .where(Application.user_id == user_id)
        )
        if params.status:
            stmt = stmt.where(Application.status == params.status.upper())
        stmt = stmt.order_by(Application.created_at.desc()).limit(params.limit)

        res = await db.execute(stmt)
        apps = list(res.scalars().all())

        output = []
        for app in apps:
            job = app.job
            output.append({
                "application_id": str(app.id),
                "job_id": str(app.job_id),
                "job_title": job.title if job else "Unknown Job",
                "company": job.company_name if job else "Unknown Company",
                "status": app.status,
                "applied_date": app.applied_date.isoformat() if app.applied_date else app.created_at.isoformat(),
                "method": app.submission_method,
                "notes": app.notes
            })

        summary = f"Found {len(output)} application record(s)."
        return ToolResult(tool_name=self.name, success=True, summary=summary, data={"applications": output, "count": len(output)})

class GetApplicationStatusTool(BaseTool):
    name = "get_application_status"
    description = "Check the current pipeline status for a specific company or job application (e.g. APPLIED, INTERVIEWING, OFFER, REJECTED)."
    category = "APPLICATION"
    parameters_schema = GetApplicationStatusInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetApplicationStatusInput) -> ToolResult:
        stmt = select(Application).options(selectinload(Application.job)).where(Application.user_id == user_id)

        if params.application_id:
            try:
                stmt = stmt.where(Application.id == uuid.UUID(params.application_id))
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid application UUID.", error="INVALID_UUID")
        elif params.company_name:
            stmt = stmt.join(Job).where(func.lower(Job.company_name).like(f"%{params.company_name.lower()}%"))
        elif params.job_title:
            stmt = stmt.join(Job).where(func.lower(Job.title).like(f"%{params.job_title.lower()}%"))

        res = await db.execute(stmt)
        app = res.scalar_one_or_none()

        if not app:
            return ToolResult(
                tool_name=self.name,
                success=True,
                summary="No application matching criteria was found in database.",
                data={"found": False}
            )

        job = app.job
        data = {
            "found": True,
            "application_id": str(app.id),
            "company": job.company_name if job else "Unknown",
            "job_title": job.title if job else "Unknown",
            "status": app.status,
            "applied_date": app.applied_date.isoformat() if app.applied_date else str(app.created_at),
            "notes": app.notes
        }
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Application at {data['company']} for '{data['job_title']}': Current Status = {data['status']}",
            data=data
        )

class GetApplicationStatisticsTool(BaseTool):
    name = "get_application_statistics"
    description = "Retrieve summary metrics of all applications submitted by candidate (counts by status: APPLIED, INTERVIEWING, OFFER, REJECTED)."
    category = "APPLICATION"
    parameters_schema = GetApplicationStatisticsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetApplicationStatisticsInput) -> ToolResult:
        stmt = select(Application.status, func.count(Application.id)).where(Application.user_id == user_id).group_by(Application.status)
        res = await db.execute(stmt)
        counts = dict(res.all())

        total = sum(counts.values())
        data = {
            "total_applications": total,
            "by_status": counts,
            "interviewing": counts.get("INTERVIEWING", 0),
            "offers": counts.get("OFFER", 0),
            "rejected": counts.get("REJECTED", 0),
            "applied": counts.get("APPLIED", 0) + counts.get("DRAFT", 0)
        }
        summary = f"Total Applications: {total} (Applied: {data['applied']}, Interviewing: {data['interviewing']}, Offers: {data['offers']}, Rejected: {data['rejected']})"
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)

class GetAnalyticsOverviewTool(BaseTool):
    name = "get_analytics_overview"
    description = "Provide overall job assistant analytics for the user (total matches, average match score, top sources, total jobs available)."
    category = "APPLICATION"
    parameters_schema = GetAnalyticsOverviewInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetAnalyticsOverviewInput) -> ToolResult:
        # 1. Total jobs in DB
        total_jobs_res = await db.execute(select(func.count(Job.id)).where(Job.is_active == True)) # noqa: E712
        total_jobs = total_jobs_res.scalar() or 0

        # 2. User matches and avg score
        match_stats_res = await db.execute(
            select(
                func.count(JobMatch.id),
                func.avg(JobMatch.overall_score)
            ).where(JobMatch.user_id == user_id)
        )
        match_count, avg_score = match_stats_res.first() or (0, 0.0)

        # 3. User applications
        app_stats_res = await db.execute(select(func.count(Application.id)).where(Application.user_id == user_id))
        app_count = app_stats_res.scalar() or 0

        data = {
            "total_indexed_jobs": total_jobs,
            "candidate_matched_jobs": match_count,
            "average_match_score": round(float(avg_score or 0.0), 1),
            "total_applications_tracked": app_count
        }
        summary = f"Analytics: {total_jobs} total active jobs in system, {match_count} candidate matches computed (Avg Score: {data['average_match_score']}%), {app_count} applications tracked."
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)

class GetAutoApplyStatusTool(BaseTool):
    name = "get_auto_apply_status"
    description = "Check whether auto-apply is enabled, today's submission counts, remaining daily limit quota, and active queue length."
    category = "APPLICATION"
    parameters_schema = GetAutoApplyStatusInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetAutoApplyStatusInput) -> ToolResult:
        from app.modules.applications.service import ApplicationService
        service = ApplicationService(db)
        status_data = await service.get_auto_apply_status(user_id)
        d = status_data.model_dump()
        enabled_str = "ENABLED" if d["auto_apply_enabled"] else "DISABLED"
        limit_str = d["daily_limit_label"] if "daily_limit_label" in d else ("Unlimited" if d.get("daily_application_limit") is None else str(d["daily_application_limit"]))
        quota_str = str(d["remaining_daily_quota"]) if d.get("remaining_daily_quota") is not None else "Unlimited"
        summary = (
            f"Auto-Apply Status: {enabled_str}. Daily Limit: {limit_str}, "
            f"Submitted Today: {d['applications_submitted_today']}, Remaining Quota: {quota_str}, "
            f"Queued: {d['queued_applications_count']}."
        )
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=d)

class GetAutoApplyPolicyTool(BaseTool):
    name = "get_auto_apply_policy"
    description = "Retrieve candidate's active auto-apply policy rules (min match score threshold, salary floor, blocked companies/keywords, remote rules)."
    category = "APPLICATION"
    parameters_schema = GetAutoApplyPolicyInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetAutoApplyPolicyInput) -> ToolResult:
        from app.modules.applications.service import ApplicationService
        service = ApplicationService(db)
        policy = await service.get_or_create_policy(user_id)
        d = {
            "auto_apply_enabled": policy.auto_apply_enabled,
            "minimum_match_score": policy.minimum_match_score,
            "minimum_salary": policy.minimum_salary,
            "daily_application_limit": policy.daily_application_limit,
            "blocked_companies": policy.blocked_companies,
            "blocked_keywords": policy.blocked_keywords,
            "preferred_roles": policy.preferred_roles,
            "allow_remote": policy.allow_remote,
            "allow_hybrid": policy.allow_hybrid,
            "allow_onsite": policy.allow_onsite
        }
        limit_str = f"{policy.daily_application_limit}/day" if policy.daily_application_limit is not None else "Unlimited"
        summary = (
            f"Auto-Apply Policy: Enabled={d['auto_apply_enabled']}, Min Score={d['minimum_match_score']}%, "
            f"Daily Limit={limit_str}, Blocked Companies={len(d['blocked_companies'])}, "
            f"Blocked Keywords={len(d['blocked_keywords'])}."
        )
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=d)

class GetApplicationDetailsTool(BaseTool):
    name = "get_application_details"
    description = "Retrieve complete application timeline, attempts, match scores, resume version used, and failure/skip reason for a specific job or application."
    category = "APPLICATION"
    parameters_schema = GetApplicationDetailsInput

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetApplicationDetailsInput) -> ToolResult:
        from app.database.models.application import Application
        stmt = (
            select(Application)
            .options(
                selectinload(Application.job),
                selectinload(Application.events),
                selectinload(Application.attempts)
            )
            .where(Application.user_id == user_id)
        )
        if params.application_id:
            try:
                stmt = stmt.where(Application.id == uuid.UUID(params.application_id))
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid application UUID format.", error="INVALID_UUID")
        elif params.job_id:
            try:
                stmt = stmt.where(Application.job_id == uuid.UUID(params.job_id))
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid job UUID format.", error="INVALID_UUID")
        else:
            return ToolResult(tool_name=self.name, success=False, summary="Please specify application_id or job_id.", error="MISSING_PARAM")

        res = await db.execute(stmt)
        app = res.scalar_one_or_none()
        if not app:
            return ToolResult(tool_name=self.name, success=True, summary="No application found for specified ID.", data={"found": False})

        job = app.job
        data = {
            "found": True,
            "application_id": str(app.id),
            "job_id": str(app.job_id),
            "job_title": job.title if job else "Unknown",
            "company": job.company_name if job else "Unknown",
            "status": app.status,
            "match_score": app.match_score,
            "eligibility_status": app.eligibility_status,
            "policy_decision": app.policy_decision,
            "failure_reason": app.failure_reason,
            "external_application_id": app.external_application_id,
            "events_count": len(app.events),
            "attempts_count": len(app.attempts)
        }
        summary = f"Application for '{data['job_title']}' at {data['company']}: Status = {data['status']}, Match = {data['match_score']}%, Policy = {data['policy_decision']}."
        return ToolResult(tool_name=self.name, success=True, summary=summary, data=data)


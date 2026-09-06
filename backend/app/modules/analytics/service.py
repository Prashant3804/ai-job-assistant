import uuid
from typing import Dict, Any, List
from collections import Counter
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database.models.job import Job
from app.database.models.match import JobMatch
from app.database.models.application import Application, ApplicationEvent
from app.database.models.user import User
from app.shared.constants import ApplicationStatus
from app.shared.schemas import DashboardAnalytics, DashboardSummaryMetrics, JobMatchRead

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_data(self, user: User) -> DashboardAnalytics:
        # 1. Metric Counts
        # Total active jobs found
        jobs_count_res = await self.db.execute(select(func.count(Job.id)).where(Job.is_active == True)) # noqa: E712
        jobs_found = jobs_count_res.scalar() or 0

        # Recommended jobs (score >= 80%)
        rec_count_res = await self.db.execute(
            select(func.count(JobMatch.id)).where(
                and_(JobMatch.user_id == user.id, JobMatch.overall_score >= 80.0)
            )
        )
        recommended_jobs = rec_count_res.scalar() or 0

        # Total applications
        apps_res = await self.db.execute(
            select(Application).where(Application.user_id == user.id)
        )
        user_apps = list(apps_res.scalars().all())
        total_apps = len(user_apps)

        interviews = sum(1 for a in user_apps if a.status == ApplicationStatus.INTERVIEW_SCHEDULED.value)
        offers = sum(1 for a in user_apps if a.status == ApplicationStatus.OFFER_RECEIVED.value)
        pending = sum(1 for a in user_apps if a.status in (ApplicationStatus.DRAFT.value, ApplicationStatus.SUBMITTED.value, ApplicationStatus.UNDER_REVIEW.value))

        metrics = DashboardSummaryMetrics(
            jobs_found=jobs_found,
            recommended_jobs=recommended_jobs,
            applications_total=total_apps,
            interviews=interviews,
            offers=offers,
            pending_applications=pending
        )

        # 2. Funnel Breakdown
        funnel = {
            "Draft": sum(1 for a in user_apps if a.status == ApplicationStatus.DRAFT.value),
            "Submitted": sum(1 for a in user_apps if a.status == ApplicationStatus.SUBMITTED.value),
            "Under Review": sum(1 for a in user_apps if a.status == ApplicationStatus.UNDER_REVIEW.value),
            "Interview": interviews,
            "Offer": offers,
            "Rejected": sum(1 for a in user_apps if a.status == ApplicationStatus.REJECTED.value),
        }

        # 3. Top Skills In Demand across jobs
        top_jobs_res = await self.db.execute(select(Job.required_skills).where(Job.is_active == True).limit(50)) # noqa: E712
        skills_counter: Counter = Counter()
        for skills_list in top_jobs_res.scalars().all():
            if skills_list:
                for s in skills_list:
                    skills_counter[s] += 1

        top_skills = [{"skill": k, "count": v} for k, v in skills_counter.most_common(8)]

        # 4. Recent Activities
        events_stmt = (
            select(ApplicationEvent)
            .join(ApplicationEvent.application)
            .where(Application.user_id == user.id)
            .order_by(ApplicationEvent.created_at.desc())
            .limit(5)
        )
        events_res = await self.db.execute(events_stmt)
        recent_events = events_res.scalars().all()
        recent_activities = [
            {
                "id": str(e.id),
                "title": e.title,
                "description": e.description,
                "created_at": e.created_at.isoformat(),
                "event_type": e.event_type
            }
            for e in recent_events
        ]

        # 5. Top 5 Recommended Jobs
        matches_stmt = (
            select(JobMatch)
            .options(
                selectinload(JobMatch.job).selectinload(Job.job_source),
                selectinload(JobMatch.resume)
            )
            .where(JobMatch.user_id == user.id)
            .order_by(JobMatch.overall_score.desc())
            .limit(5)
        )
        matches_res = await self.db.execute(matches_stmt)
        top_matches = [JobMatchRead.model_validate(m, from_attributes=True) for m in matches_res.scalars().all()]

        # 6. Auto-Apply Routine Info & Recent Auto-Apply Applications
        from app.modules.applications.daily_routine import AutoApplyDailyRoutineService
        routine_svc = AutoApplyDailyRoutineService(self.db)
        routine_info = await routine_svc.get_routine_info(user.id)

        PLATFORM_NAMES = {
            "naukri": "Naukri",
            "indeed": "Indeed",
            "unstop": "Unstop",
            "linkedin": "LinkedIn Jobs",
            "internshala": "Internshala",
            "wellfound": "Wellfound",
            "career_pages": "Company Careers",
        }

        # Recent applications processed via auto-apply / direct API / external portal
        recent_auto_stmt = (
            select(Application)
            .options(selectinload(Application.job).selectinload(Job.job_source))
            .where(Application.user_id == user.id)
            .order_by(Application.created_at.desc())
            .limit(10)
        )
        recent_auto_res = await self.db.execute(recent_auto_stmt)
        recent_auto_apps = recent_auto_res.scalars().all()

        from zoneinfo import ZoneInfo
        kolkata_tz = ZoneInfo("Asia/Kolkata")

        recent_auto_list = []
        for a in recent_auto_apps:
            # Format timestamp in IST
            ts = a.applied_date or a.submitted_at or a.created_at
            ist_dt = ts.astimezone(kolkata_tz) if ts else None
            formatted_date = ist_dt.strftime("%b %d, %Y • %I:%M %p IST") if ist_dt else "Recent"

            source_slug = a.source
            if not source_slug and a.job and a.job.job_source:
                source_slug = a.job.job_source.slug
            source_name = (
                PLATFORM_NAMES.get(source_slug or "", None)
                or (a.job.job_source.name if a.job and a.job.job_source else None)
                or (source_slug.replace("_", " ").title() if source_slug else "Direct Application")
            )

            recent_auto_list.append({
                "id": str(a.id),
                "company_name": a.job.company_name if a.job else "Company",
                "job_title": a.job.title if a.job else "Job Application",
                "platform": source_name,
                "source": source_slug or "career_pages",
                "status": a.status,
                "match_score": a.match_score,
                "applied_at": ts.isoformat() if ts else None,
                "applied_at_display": formatted_date,
                "submission_method": a.submission_method
            })

        return DashboardAnalytics(
            metrics=metrics,
            funnel=funnel,
            top_skills_in_demand=top_skills,
            recent_activities=recent_activities,
            top_recommendations=top_matches,
            auto_apply_routine=routine_info.model_dump(mode="json"),
            recent_auto_apply_applications=recent_auto_list
        )

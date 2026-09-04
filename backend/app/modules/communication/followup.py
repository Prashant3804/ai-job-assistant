import logging
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.application import Application
from app.database.models.email import Recruiter, MailboxMessage
from app.database.models.job import Job
from app.database.models.user import User
from app.shared.constants import ApplicationStatus, DraftIntent, DraftTone
from app.modules.communication.schemas import FollowUpRecommendation
from app.modules.communication.drafter import ResponseDraftingEngine

logger = logging.getLogger(__name__)


class FollowUpDetector:
    """
    Follow-up & Ghosting Detection Engine.
    Scans active applications, detects communication stagnation,
    calculates nudge priorities, and generates proactive follow-up recommendations.
    """

    @classmethod
    async def get_follow_up_recommendations(
        cls,
        db: AsyncSession,
        user_id,
        user_name: str = "Candidate",
    ) -> List[FollowUpRecommendation]:
        """Identify stalled job applications and generate follow-up recommendations."""
        recommendations: List[FollowUpRecommendation] = []
        now = datetime.now(timezone.utc)

        # 1. Fetch active applications for the user
        stmt = (
            select(Application, Job)
            .join(Job, Application.job_id == Job.id)
            .where(
                Application.user_id == user_id,
                Application.status.in_([
                    ApplicationStatus.APPLIED.value,
                    ApplicationStatus.SUBMITTED.value,
                    ApplicationStatus.UNDER_REVIEW.value,
                    ApplicationStatus.INTERVIEWING.value,
                    ApplicationStatus.INTERVIEW_SCHEDULED.value,
                    ApplicationStatus.OFFER.value,
                    ApplicationStatus.OFFER_RECEIVED.value,
                ]),
            )
        )
        res = await db.execute(stmt)
        active_apps = res.all()

        for app, job in active_apps:
            # Check latest email message or recruiter activity for this application
            msg_stmt = (
                select(MailboxMessage)
                .where(
                    MailboxMessage.user_id == user_id,
                    MailboxMessage.application_id == app.id,
                )
                .order_by(MailboxMessage.received_at.desc())
                .limit(1)
            )
            msg_res = await db.execute(msg_stmt)
            latest_msg = msg_res.scalars().first()

            # Determine last contact date
            last_contact = app.applied_date or app.submitted_at or app.created_at
            if latest_msg and latest_msg.received_at:
                last_contact = latest_msg.received_at

            if not last_contact:
                continue

            # Ensure timezone awareness
            if last_contact.tzinfo is None:
                last_contact = last_contact.replace(tzinfo=timezone.utc)

            delta = now - last_contact
            days_inactive = max(0, delta.days)

            # Follow-up thresholds
            if days_inactive >= 3:
                if days_inactive >= 10:
                    nudge_priority = "HIGH"
                    action_msg = f"No communication for {days_inactive} days. High probability of stalled pipeline. Send follow-up check-in."
                elif days_inactive >= 5:
                    nudge_priority = "MEDIUM"
                    action_msg = f"Last activity was {days_inactive} days ago. Ideal window for a polite status follow-up."
                else:
                    nudge_priority = "LOW"
                    action_msg = f"Recent submission ({days_inactive} days). Standard waiting period."

                # Look up recruiter if known
                recruiter_name = None
                recruiter_email = None
                if latest_msg and latest_msg.sender_email:
                    recruiter_email = latest_msg.sender_email
                    recruiter_name = latest_msg.sender_name

                # Pre-generate draft body using drafter
                draft_data = ResponseDraftingEngine._generate_template_draft(
                    candidate_name=user_name,
                    recruiter_name=recruiter_name or "Hiring Team",
                    company_name=job.company_name,
                    job_title=job.title,
                    intent=DraftIntent.FOLLOW_UP,
                    tone=DraftTone.PROFESSIONAL,
                    availability=[],
                )

                recommendations.append(
                    FollowUpRecommendation(
                        application_id=app.id,
                        company_name=job.company_name,
                        job_title=job.title,
                        recruiter_name=recruiter_name,
                        recruiter_email=recruiter_email,
                        last_contact_date=last_contact,
                        days_inactive=days_inactive,
                        nudge_priority=nudge_priority,
                        suggested_action=action_msg,
                        recommended_intent=DraftIntent.FOLLOW_UP,
                        suggested_draft_subject=draft_data["subject"],
                        suggested_draft_body=draft_data["body_text"],
                    )
                )

        # Sort recommendations by priority (HIGH -> MEDIUM -> LOW) and days_inactive desc
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        recommendations.sort(key=lambda r: (priority_order.get(r.nudge_priority, 3), -r.days_inactive))
        return recommendations

import re
import uuid
from typing import Optional, List, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.application import Application
from app.database.models.job import Job
from app.modules.mailbox.normalizer import NormalizedEmail
from app.modules.mailbox.classifier import EmailClassificationResult

class ApplicationEmailMatcher:
    """Matches incoming recruiter/job emails to existing candidate Applications."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def match_email_to_application(
        self,
        user_id: uuid.UUID,
        email: NormalizedEmail,
        classification: EmailClassificationResult
    ) -> Optional[Application]:
        """
        Attempts to associate an email with a user's Application record.
        Returns the matched Application or None.
        """
        if not classification.is_job_related and not classification.is_recruiter:
            return None

        # 1. Strategy A: Match by Detected Company Name
        if classification.detected_company:
            comp_norm = classification.detected_company.strip().lower()
            stmt = (
                select(Application)
                .join(Job, Application.job_id == Job.id)
                .options(selectinload(Application.job))
                .where(
                    and_(
                        Application.user_id == user_id,
                        Job.company_name.ilike(f"%{comp_norm}%")
                    )
                )
                .order_by(Application.created_at.desc())
            )
            res = await self.db.execute(stmt)
            candidates: List[Application] = list(res.scalars().all())

            if candidates:
                if len(candidates) == 1:
                    return candidates[0]
                
                # If multiple applications at same company, check job title match
                if classification.detected_job_title:
                    title_norm = classification.detected_job_title.lower()
                    for app in candidates:
                        if app.job and (title_norm in app.job.title.lower() or app.job.title.lower() in title_norm):
                            return app
                return candidates[0]

        # 2. Strategy B: Sender Domain Match against Job URL / Company name
        sender_domain = email.sender_email.split("@")[-1].lower() if "@" in email.sender_email else ""
        if sender_domain and "." in sender_domain and not sender_domain.endswith(("gmail.com", "yahoo.com", "outlook.com", "greenhouse.io", "lever.co", "workday.com", "workday.net")):
            comp_from_domain = sender_domain.split(".")[0]
            if len(comp_from_domain) >= 3:
                stmt = (
                    select(Application)
                    .join(Job, Application.job_id == Job.id)
                    .options(selectinload(Application.job))
                    .where(
                        and_(
                            Application.user_id == user_id,
                            or_(
                                Job.company_name.ilike(f"%{comp_from_domain}%"),
                                Job.apply_url.ilike(f"%{sender_domain}%")
                            )
                        )
                    )
                    .order_by(Application.created_at.desc())
                )
                res = await self.db.execute(stmt)
                match = res.scalars().first()
                if match:
                    return match

        # 3. Strategy C: Match company names present in subject or body against user's applications
        stmt_all = (
            select(Application)
            .join(Job, Application.job_id == Job.id)
            .options(selectinload(Application.job))
            .where(Application.user_id == user_id)
            .order_by(Application.created_at.desc())
        )
        res_all = await self.db.execute(stmt_all)
        all_apps = list(res_all.scalars().all())

        combined_text = f"{email.subject} {email.body_text[:1000]}".lower()
        for app in all_apps:
            if app.job and app.job.company_name:
                app_comp = app.job.company_name.strip().lower()
                if len(app_comp) > 2 and app_comp in combined_text:
                    return app

        return None

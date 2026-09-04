import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models.email import EmailAccount, EmailMessage, Recruiter
from app.database.models.application import Application, ApplicationEvent
from app.modules.ai.service import BaseLLMService, get_ai_service
from app.shared.constants import EmailClassification, ApplicationStatus, ApplicationEventType
from app.shared.schemas import EmailClassifyRequest, EmailClassifyResponse

class EmailIntelligenceService:
    def __init__(self, db: AsyncSession, ai_service: Optional[BaseLLMService] = None):
        self.db = db
        self.ai = ai_service or get_ai_service()

    async def classify_message_content(self, payload: EmailClassifyRequest) -> EmailClassifyResponse:
        prompt = (
            f"Sender: {payload.sender_name} <{payload.sender_email}>\n"
            f"Subject: {payload.subject}\n\n"
            f"Body:\n{payload.body_text}"
        )
        system_prompt = (
            "You are an AI Email Recruiter Classifier. Determine if this email is from a recruiter or hiring team. "
            "Classify the message strictly into one of: [INTERVIEW_INVITATION, REJECTION, OA_REQUEST, OFFER, GENERAL_INQUIRY, SPAM]. "
            "Provide a confidence score (0.0 to 1.0), short summary, suggested status update, and detected company name."
        )
        return await self.ai.generate_structured(prompt, system_prompt, EmailClassifyResponse)

    async def ingest_email(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        sender_email: str,
        sender_name: Optional[str],
        subject: str,
        body_text: str,
        external_message_id: Optional[str] = None
    ) -> EmailMessage:
        classification = await self.classify_message_content(
            EmailClassifyRequest(
                sender_email=sender_email,
                sender_name=sender_name,
                subject=subject,
                body_text=body_text
            )
        )

        # Attempt to link to an active application based on company name
        application_id = None
        if classification.is_recruiter and classification.detected_company:
            stmt_app = (
                select(Application)
                .join(Application.job)
                .where(
                    and_(
                        Application.user_id == user_id,
                        Application.job.has(company_name=classification.detected_company)
                    )
                )
            )
            res_app = await self.db.execute(stmt_app)
            app = res_app.scalar_one_or_none()
            if app:
                application_id = app.id
                if classification.suggested_status_update:
                    app.status = classification.suggested_status_update
                    event = ApplicationEvent(
                        application_id=app.id,
                        event_type=ApplicationEventType.EMAIL_RECEIVED.value,
                        new_status=app.status,
                        title=f"Email: {classification.classification.replace('_', ' ').title()}",
                        description=f"{subject} - {classification.summary}"
                    )
                    self.db.add(event)

        msg = EmailMessage(
            email_account_id=account_id,
            external_message_id=external_message_id or str(uuid.uuid4()),
            sender_email=sender_email,
            sender_name=sender_name,
            recipient_email="candidate@example.com",
            subject=subject,
            body_text=body_text,
            is_recruiter=classification.is_recruiter,
            classification=classification.classification,
            confidence_score=classification.confidence_score,
            application_id=application_id
        )
        self.db.add(msg)

        # Create or update Recruiter entity
        if classification.is_recruiter and sender_name:
            stmt_rec = select(Recruiter).where(and_(Recruiter.user_id == user_id, Recruiter.email == sender_email))
            res_rec = await self.db.execute(stmt_rec)
            rec = res_rec.scalar_one_or_none()
            if not rec:
                rec = Recruiter(
                    user_id=user_id,
                    name=sender_name,
                    email=sender_email,
                    company_name=classification.detected_company,
                    title="Talent Acquisition / Recruiter"
                )
                self.db.add(rec)

        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def list_messages(self, user_id: uuid.UUID) -> List[EmailMessage]:
        stmt = (
            select(EmailMessage)
            .join(EmailMessage.account)
            .where(EmailAccount.user_id == user_id)
            .order_by(EmailMessage.received_at.desc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def list_recruiters(self, user_id: uuid.UUID) -> List[Recruiter]:
        stmt = select(Recruiter).where(Recruiter.user_id == user_id).order_by(Recruiter.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

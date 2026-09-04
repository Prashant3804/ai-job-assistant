import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.user import User, UserProfile
from app.database.models.email import Recruiter, MailboxMessage
from app.database.models.application import Application
from app.database.models.job import Job
from app.database.models.communication import CommunicationDraft, InterviewSession, InterviewPrepBrief
from app.shared.constants import (
    DraftIntent,
    DraftTone,
    DraftStatus,
    RecruiterRelationshipStage,
    InterviewRoundType,
    InterviewStatus,
)
from app.modules.communication.schemas import (
    RecruiterCreate,
    RecruiterUpdate,
    RecruiterResponse,
    DraftGenerationRequest,
    DraftResponse,
    DraftUpdateRequest,
    InterviewSessionCreate,
    InterviewSessionUpdate,
    InterviewSessionResponse,
    InterviewPrepBriefGenerateRequest,
    InterviewPrepBriefResponse,
    FollowUpRecommendation,
)
from app.modules.communication.drafter import ResponseDraftingEngine
from app.modules.communication.interview_service import InterviewIntelligenceService
from app.modules.communication.followup import FollowUpDetector

logger = logging.getLogger(__name__)


class CommunicationService:
    """
    Central orchestration service for Recruiter CRM, Contextual AI Response Drafting,
    Interview Intelligence Briefings, and Follow-Up / Ghosting Detection.
    """

    # =========================================================================
    # 1. Recruiter CRM
    # =========================================================================

    @classmethod
    async def list_recruiters(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        stage: Optional[RecruiterRelationshipStage] = None,
        search: Optional[str] = None,
    ) -> List[Recruiter]:
        query = select(Recruiter).where(Recruiter.user_id == user_id)
        if stage:
            query = query.where(Recruiter.relationship_stage == stage.value)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                (Recruiter.name.ilike(pattern))
                | (Recruiter.email.ilike(pattern))
                | (Recruiter.company_name.ilike(pattern))
            )
        query = query.order_by(Recruiter.updated_at.desc())
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_recruiter(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        recruiter_id: uuid.UUID,
    ) -> Optional[Recruiter]:
        query = select(Recruiter).where(
            Recruiter.id == recruiter_id,
            Recruiter.user_id == user_id,
        )
        res = await db.execute(query)
        return res.scalars().first()

    @classmethod
    async def create_recruiter(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: RecruiterCreate,
    ) -> Recruiter:
        now = datetime.now(timezone.utc)
        recruiter = Recruiter(
            user_id=user_id,
            name=payload.name,
            email=str(payload.email),
            company_name=payload.company_name,
            title=payload.title,
            linkedin_url=payload.linkedin_url,
            phone=payload.phone,
            relationship_stage=payload.relationship_stage.value,
            notes=payload.notes,
            last_interaction_at=now,
            interaction_count=1,
        )
        db.add(recruiter)
        await db.commit()
        await db.refresh(recruiter)
        return recruiter

    @classmethod
    async def update_recruiter(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        recruiter_id: uuid.UUID,
        payload: RecruiterUpdate,
    ) -> Optional[Recruiter]:
        recruiter = await cls.get_recruiter(db, user_id, recruiter_id)
        if not recruiter:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "relationship_stage" and value is not None:
                setattr(recruiter, key, value.value if hasattr(value, "value") else value)
            elif key == "email" and value is not None:
                setattr(recruiter, key, str(value))
            elif value is not None:
                setattr(recruiter, key, value)

        recruiter.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(recruiter)
        return recruiter

    @classmethod
    async def delete_recruiter(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        recruiter_id: uuid.UUID,
    ) -> bool:
        recruiter = await cls.get_recruiter(db, user_id, recruiter_id)
        if not recruiter:
            return False
        await db.delete(recruiter)
        await db.commit()
        return True

    # =========================================================================
    # 2. Contextual AI Response Drafting (Human-in-the-Loop)
    # =========================================================================

    @classmethod
    async def create_draft(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: DraftGenerationRequest,
    ) -> CommunicationDraft:
        """
        Generate contextual reply draft and persist to database with DRAFT status.
        Never sends automatically — enforces Human-in-the-Loop.
        """
        # 1. Fetch user profile for context
        user_stmt = select(User).where(User.id == user_id).options(
            selectinload(User.profile).selectinload(UserProfile.skills),
            selectinload(User.profile).selectinload(UserProfile.experiences),
        )
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        candidate_name = user.full_name if user else "Candidate"
        skills = [getattr(s, "name", getattr(s, "skill_name", "")) for s in user.profile.skills] if (user and user.profile and user.profile.skills) else []

        # 2. Determine recruiter / job context
        recruiter_name = payload.recruiter_name
        company_name = payload.company_name
        job_title = payload.job_title

        if payload.recruiter_id:
            recruiter = await cls.get_recruiter(db, user_id, payload.recruiter_id)
            if recruiter:
                recruiter_name = recruiter_name or recruiter.name
                company_name = company_name or recruiter.company_name

        if payload.application_id:
            app_stmt = select(Application).where(Application.id == payload.application_id).options(selectinload(Application.job))
            app_res = await db.execute(app_stmt)
            app = app_res.scalars().first()
            if app and app.job:
                company_name = company_name or app.job.company_name
                job_title = job_title or app.job.title

        # 3. Generate draft content
        draft_content = await ResponseDraftingEngine.generate_draft(
            candidate_name=candidate_name,
            recruiter_name=recruiter_name,
            company_name=company_name,
            job_title=job_title,
            intent=payload.intent,
            tone=payload.tone,
            candidate_availability=payload.candidate_availability,
            incoming_email_snippet=payload.incoming_email_snippet,
            custom_instructions=payload.custom_instructions,
            salary_expectation=payload.salary_expectation,
            offer_details=payload.offer_details,
            candidate_skills=skills,
        )

        # 4. Save draft in database
        draft = CommunicationDraft(
            user_id=user_id,
            recruiter_id=payload.recruiter_id,
            application_id=payload.application_id,
            message_id=payload.message_id,
            intent=payload.intent.value,
            tone=payload.tone.value,
            subject=draft_content["subject"],
            body_text=draft_content["body_text"],
            status=DraftStatus.DRAFT.value,
            key_points_addressed=draft_content.get("key_points_addressed", []),
            candidate_availability_used=draft_content.get("candidate_availability_used", []),
            is_approved=False,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def list_drafts(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        intent: Optional[DraftIntent] = None,
        status: Optional[DraftStatus] = None,
    ) -> List[CommunicationDraft]:
        query = select(CommunicationDraft).where(CommunicationDraft.user_id == user_id)
        if intent:
            query = query.where(CommunicationDraft.intent == intent.value)
        if status:
            query = query.where(CommunicationDraft.status == status.value)
        query = query.order_by(CommunicationDraft.created_at.desc())
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_draft(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
    ) -> Optional[CommunicationDraft]:
        query = select(CommunicationDraft).where(
            CommunicationDraft.id == draft_id,
            CommunicationDraft.user_id == user_id,
        )
        res = await db.execute(query)
        return res.scalars().first()

    @classmethod
    async def update_draft(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
        payload: DraftUpdateRequest,
    ) -> Optional[CommunicationDraft]:
        draft = await cls.get_draft(db, user_id, draft_id)
        if not draft:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "tone" and value is not None:
                setattr(draft, key, value.value if hasattr(value, "value") else value)
            elif key == "status" and value is not None:
                setattr(draft, key, value.value if hasattr(value, "value") else value)
            elif key == "is_approved" and value is True:
                draft.is_approved = True
                draft.status = DraftStatus.APPROVED.value
                draft.approved_at = datetime.now(timezone.utc)
            elif value is not None:
                setattr(draft, key, value)

        draft.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def approve_draft(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
    ) -> Optional[CommunicationDraft]:
        draft = await cls.get_draft(db, user_id, draft_id)
        if not draft:
            return None
        draft.is_approved = True
        draft.status = DraftStatus.APPROVED.value
        draft.approved_at = datetime.now(timezone.utc)
        draft.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(draft)
        return draft

    @classmethod
    async def delete_draft(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        draft_id: uuid.UUID,
    ) -> bool:
        draft = await cls.get_draft(db, user_id, draft_id)
        if not draft:
            return False
        await db.delete(draft)
        await db.commit()
        return True

    # =========================================================================
    # 3. Interview Sessions & Prep Briefs
    # =========================================================================

    @classmethod
    async def list_interviews(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        status: Optional[InterviewStatus] = None,
    ) -> List[InterviewSession]:
        query = select(InterviewSession).where(InterviewSession.user_id == user_id)
        if status:
            query = query.where(InterviewSession.status == status.value)
        query = query.order_by(InterviewSession.scheduled_at.asc())
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_interview(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
    ) -> Optional[InterviewSession]:
        query = select(InterviewSession).where(
            InterviewSession.id == interview_id,
            InterviewSession.user_id == user_id,
        )
        res = await db.execute(query)
        return res.scalars().first()

    @classmethod
    async def create_interview(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: InterviewSessionCreate,
    ) -> InterviewSession:
        interview = InterviewSession(
            user_id=user_id,
            application_id=payload.application_id,
            recruiter_id=payload.recruiter_id,
            round_type=payload.round_type.value,
            title=payload.title,
            company_name=payload.company_name,
            job_title=payload.job_title,
            scheduled_at=payload.scheduled_at,
            duration_minutes=payload.duration_minutes,
            meeting_url=payload.meeting_url,
            meeting_platform=payload.meeting_platform,
            interviewers=payload.interviewers or [],
            status=InterviewStatus.SCHEDULED.value,
            notes=payload.notes,
        )
        db.add(interview)
        await db.commit()
        await db.refresh(interview)
        return interview

    @classmethod
    async def update_interview(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
        payload: InterviewSessionUpdate,
    ) -> Optional[InterviewSession]:
        interview = await cls.get_interview(db, user_id, interview_id)
        if not interview:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "round_type" and value is not None:
                setattr(interview, key, value.value if hasattr(value, "value") else value)
            elif key == "status" and value is not None:
                setattr(interview, key, value.value if hasattr(value, "value") else value)
            elif value is not None:
                setattr(interview, key, value)

        interview.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(interview)
        return interview

    @classmethod
    async def delete_interview(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        interview_id: uuid.UUID,
    ) -> bool:
        interview = await cls.get_interview(db, user_id, interview_id)
        if not interview:
            return False
        await db.delete(interview)
        await db.commit()
        return True

    @classmethod
    async def generate_prep_brief(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: InterviewPrepBriefGenerateRequest,
    ) -> InterviewPrepBrief:
        """Generate comprehensive interview preparation brief with STAR stories."""
        # 1. Fetch user profile for context
        user_stmt = select(User).where(User.id == user_id).options(
            selectinload(User.profile).selectinload(UserProfile.skills),
            selectinload(User.profile).selectinload(UserProfile.experiences),
            selectinload(User.profile).selectinload(UserProfile.projects),
        )
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        candidate_name = user.full_name if user else "Candidate"
        skills = [getattr(s, "name", getattr(s, "skill_name", "")) for s in user.profile.skills] if (user and user.profile and user.profile.skills) else []
        experiences = [{"title": e.title, "company": getattr(e, "company_name", getattr(e, "company", "")), "description": getattr(e, "description", "")} for e in user.profile.experiences] if (user and user.profile and user.profile.experiences) else []
        projects = [{"name": getattr(p, "title", getattr(p, "name", "")), "description": getattr(p, "description", "")} for p in user.profile.projects] if (user and user.profile and user.profile.projects) else []

        # 2. If interview_id passed, get interview details
        round_type = payload.round_type or InterviewRoundType.TECHNICAL_SCREEN
        if payload.interview_id:
            interview = await cls.get_interview(db, user_id, payload.interview_id)
            if interview and interview.round_type:
                try:
                    round_type = InterviewRoundType(interview.round_type)
                except Exception:
                    pass

        # 3. Generate Brief via AI service
        brief_data = await InterviewIntelligenceService.generate_interview_prep_brief(
            candidate_name=candidate_name,
            company_name=payload.company_name,
            job_title=payload.job_title,
            job_description=payload.job_description,
            round_type=round_type,
            candidate_skills=skills,
            candidate_experiences=experiences,
            candidate_projects=projects,
        )

        # 4. Save to DB
        prep_brief = InterviewPrepBrief(
            user_id=user_id,
            interview_id=payload.interview_id,
            application_id=payload.application_id,
            company_name=payload.company_name,
            job_title=payload.job_title,
            company_overview=brief_data.get("company_overview"),
            role_summary=brief_data.get("role_summary"),
            technical_focus_areas=brief_data.get("technical_focus_areas", []),
            expected_questions=brief_data.get("expected_questions", []),
            star_stories=brief_data.get("star_stories", []),
            reverse_questions_to_ask=brief_data.get("reverse_questions_to_ask", []),
            cheat_sheet_markdown=brief_data.get("cheat_sheet_markdown"),
        )
        db.add(prep_brief)
        await db.commit()
        await db.refresh(prep_brief)
        return prep_brief

    @classmethod
    async def get_prep_brief(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        brief_id: Optional[uuid.UUID] = None,
        interview_id: Optional[uuid.UUID] = None,
    ) -> Optional[InterviewPrepBrief]:
        query = select(InterviewPrepBrief).where(InterviewPrepBrief.user_id == user_id)
        if brief_id:
            query = query.where(InterviewPrepBrief.id == brief_id)
        elif interview_id:
            query = query.where(InterviewPrepBrief.interview_id == interview_id)
        query = query.order_by(InterviewPrepBrief.created_at.desc())
        res = await db.execute(query)
        return res.scalars().first()

    # =========================================================================
    # 4. Follow-up & Ghosting Detection
    # =========================================================================

    @classmethod
    async def get_follow_up_recommendations(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> List[FollowUpRecommendation]:
        user_stmt = select(User).where(User.id == user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        user_name = user.full_name if user else "Candidate"
        return await FollowUpDetector.get_follow_up_recommendations(db=db, user_id=user_id, user_name=user_name)

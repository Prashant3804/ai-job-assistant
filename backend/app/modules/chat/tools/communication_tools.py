import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.email import Recruiter
from app.database.models.communication import CommunicationDraft, InterviewSession, InterviewPrepBrief
from app.database.models.application import Application
from app.database.models.job import Job
from app.database.models.user import User
from app.shared.constants import (
    DraftIntent,
    DraftTone,
    DraftStatus,
    RecruiterRelationshipStage,
    InterviewRoundType,
    InterviewStatus,
)
from app.modules.chat.tools.base import BaseTool, ToolResult
from app.modules.communication.service import CommunicationService
from app.modules.communication.schemas import (
    DraftGenerationRequest,
    RecruiterUpdate,
    InterviewPrepBriefGenerateRequest,
)


# -------------------------------------------------------------
# Parameter Schemas
# -------------------------------------------------------------

class EmptyParams(BaseModel):
    pass


class DraftRecruiterReplyParams(BaseModel):
    recruiter_name: Optional[str] = Field(default=None, description="Name of the recruiter or hiring manager")
    company_name: Optional[str] = Field(default=None, description="Company name")
    job_title: Optional[str] = Field(default=None, description="Job title or role")
    intent: DraftIntent = Field(default=DraftIntent.GENERAL, description="Intent: SCHEDULE_INTERVIEW, THANK_YOU, NEGOTIATE_OFFER, FOLLOW_UP, ACCEPT_OFFER, DECLINE_OFFER, COLD_REPLY, GENERAL")
    tone: DraftTone = Field(default=DraftTone.PROFESSIONAL, description="Tone: PROFESSIONAL, CONFIDENT, ENTHUSIASTIC, ASSERTIVE, CONCISE")
    candidate_availability: Optional[List[str]] = Field(default=None, description="Candidate availability time slots")
    custom_instructions: Optional[str] = Field(default=None, description="Specific nuances, salary targets, or instructions")
    incoming_email_snippet: Optional[str] = Field(default=None, description="Context from recruiter's recent message")


class RecruiterProfileParams(BaseModel):
    recruiter_id: Optional[str] = Field(default=None, description="UUID of the recruiter")
    email: Optional[str] = Field(default=None, description="Email of the recruiter")
    name: Optional[str] = Field(default=None, description="Name of the recruiter")


class ListRecruitersParams(BaseModel):
    stage: Optional[RecruiterRelationshipStage] = Field(default=None, description="Filter by relationship stage")
    search: Optional[str] = Field(default=None, description="Search term in name, company, or email")


class InterviewPrepParams(BaseModel):
    interview_id: Optional[str] = Field(default=None, description="UUID of existing interview session")
    company_name: Optional[str] = Field(default=None, description="Company name")
    job_title: Optional[str] = Field(default=None, description="Job title")
    round_type: Optional[InterviewRoundType] = Field(default=InterviewRoundType.TECHNICAL_SCREEN, description="Interview round type")
    job_description: Optional[str] = Field(default=None, description="Job description or technical focus")


class ListInterviewsParams(BaseModel):
    status: Optional[InterviewStatus] = Field(default=None, description="Filter by interview status (SCHEDULED, COMPLETED, etc.)")


class UpdateRecruiterNotesParams(BaseModel):
    recruiter_id: str = Field(description="UUID of the recruiter")
    notes: Optional[str] = Field(default=None, description="Updated notes / conversation logs")
    relationship_stage: Optional[RecruiterRelationshipStage] = Field(default=None, description="Updated relationship stage")


class GetCommunicationDraftsParams(BaseModel):
    intent: Optional[DraftIntent] = Field(default=None, description="Filter drafts by intent")
    status: Optional[DraftStatus] = Field(default=None, description="Filter drafts by status (DRAFT, APPROVED, etc.)")


class ApproveDraftParams(BaseModel):
    draft_id: str = Field(description="UUID of the draft to approve")


# -------------------------------------------------------------
# Tool 1: DraftRecruiterReplyTool
# -------------------------------------------------------------
class DraftRecruiterReplyTool(BaseTool):
    name = "draft_recruiter_reply"
    description = (
        "Generate a tailored, professional response draft to a recruiter or hiring manager. "
        "Supports 8 intents (interview scheduling, thank-you, negotiation, follow-up, accept, decline, cold-reply) "
        "and 5 tones. Strictly enforces Human-in-the-Loop — creates draft for review."
    )
    category = "COMMUNICATION"
    parameters_schema = DraftRecruiterReplyParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: DraftRecruiterReplyParams) -> ToolResult:
        payload = DraftGenerationRequest(
            recruiter_name=params.recruiter_name,
            company_name=params.company_name,
            job_title=params.job_title,
            intent=params.intent,
            tone=params.tone,
            candidate_availability=params.candidate_availability or [],
            custom_instructions=params.custom_instructions,
            incoming_email_snippet=params.incoming_email_snippet,
        )
        draft = await CommunicationService.create_draft(db, user_id, payload)
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Draft generated for {draft.intent} with tone {draft.tone}.",
            data={
                "draft_id": str(draft.id),
                "intent": draft.intent,
                "tone": draft.tone,
                "subject": draft.subject,
                "body_text": draft.body_text,
                "key_points_addressed": draft.key_points_addressed,
                "status": draft.status,
                "is_approved": draft.is_approved,
                "notice": "Draft generated and saved. Please review, edit if desired, and approve before sending.",
            },
        )


# -------------------------------------------------------------
# Tool 2: GetRecruiterProfileTool
# -------------------------------------------------------------
class GetRecruiterProfileTool(BaseTool):
    name = "get_recruiter_profile"
    description = "Retrieve detailed recruiter profile, company, relationship stage, responsiveness, and interaction notes."
    category = "COMMUNICATION"
    parameters_schema = RecruiterProfileParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: RecruiterProfileParams) -> ToolResult:
        query = select(Recruiter).where(Recruiter.user_id == user_id)
        if params.recruiter_id:
            try:
                rec_uuid = uuid.UUID(params.recruiter_id)
                query = query.where(Recruiter.id == rec_uuid)
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid recruiter_id format", error="Invalid recruiter_id format")
        elif params.email:
            query = query.where(Recruiter.email.ilike(params.email.strip()))
        elif params.name:
            query = query.where(Recruiter.name.ilike(f"%{params.name.strip()}%"))
        else:
            return ToolResult(tool_name=self.name, success=False, summary="Provide recruiter_id, email, or name to search.", error="Missing search parameter")

        res = await db.execute(query)
        recruiter = res.scalars().first()
        if not recruiter:
            return ToolResult(tool_name=self.name, success=False, summary="Recruiter not found.", error="Recruiter not found.")

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found profile for recruiter {recruiter.name}.",
            data={
                "id": str(recruiter.id),
                "name": recruiter.name,
                "email": recruiter.email,
                "company_name": recruiter.company_name,
                "title": recruiter.title,
                "relationship_stage": recruiter.relationship_stage,
                "responsiveness_rating": recruiter.responsiveness_rating,
                "last_interaction_at": recruiter.last_interaction_at.isoformat() if recruiter.last_interaction_at else None,
                "notes": recruiter.notes,
            },
        )


# -------------------------------------------------------------
# Tool 3: ListRecruitersTool
# -------------------------------------------------------------
class ListRecruitersTool(BaseTool):
    name = "list_recruiters"
    description = "List tracked recruiters for candidate with filtering by relationship stage or keyword."
    category = "COMMUNICATION"
    parameters_schema = ListRecruitersParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListRecruitersParams) -> ToolResult:
        recruiters = await CommunicationService.list_recruiters(
            db=db, user_id=user_id, stage=params.stage, search=params.search
        )
        data = [
            {
                "id": str(r.id),
                "name": r.name,
                "email": r.email,
                "company_name": r.company_name,
                "title": r.title,
                "relationship_stage": r.relationship_stage,
                "responsiveness_rating": r.responsiveness_rating,
            }
            for r in recruiters
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Retrieved {len(data)} recruiters.",
            data={"count": len(data), "recruiters": data},
        )


# -------------------------------------------------------------
# Tool 4: GetInterviewPrepBriefTool
# -------------------------------------------------------------
class GetInterviewPrepBriefTool(BaseTool):
    name = "get_interview_prep_brief"
    description = "Retrieve the comprehensive AI interview preparation cheat sheet, STAR stories, and focus areas for an interview."
    category = "COMMUNICATION"
    parameters_schema = InterviewPrepParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: InterviewPrepParams) -> ToolResult:
        int_id = uuid.UUID(params.interview_id) if params.interview_id else None
        brief = await CommunicationService.get_prep_brief(db=db, user_id=user_id, interview_id=int_id)
        if not brief:
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary="No existing prep brief found. Use generate_interview_prep to create one.",
                error="PREP_BRIEF_NOT_FOUND",
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Retrieved prep brief for {brief.job_title} at {brief.company_name}.",
            data={
                "id": str(brief.id),
                "company_name": brief.company_name,
                "job_title": brief.job_title,
                "company_overview": brief.company_overview,
                "role_summary": brief.role_summary,
                "technical_focus_areas": brief.technical_focus_areas,
                "expected_questions": brief.expected_questions,
                "star_stories": brief.star_stories,
                "reverse_questions_to_ask": brief.reverse_questions_to_ask,
                "cheat_sheet_markdown": brief.cheat_sheet_markdown,
            },
        )


# -------------------------------------------------------------
# Tool 5: GenerateInterviewPrepTool
# -------------------------------------------------------------
class GenerateInterviewPrepTool(BaseTool):
    name = "generate_interview_prep"
    description = "Generate an on-demand AI preparation brief with company intel, expected questions, tailored STAR stories, and reverse questions."
    category = "COMMUNICATION"
    parameters_schema = InterviewPrepParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: InterviewPrepParams) -> ToolResult:
        if not params.company_name or not params.job_title:
            return ToolResult(
                tool_name=self.name,
                success=False,
                summary="company_name and job_title are required.",
                error="MISSING_REQUIRED_FIELDS",
            )

        int_id = uuid.UUID(params.interview_id) if params.interview_id else None
        payload = InterviewPrepBriefGenerateRequest(
            interview_id=int_id,
            company_name=params.company_name,
            job_title=params.job_title,
            job_description=params.job_description,
            round_type=params.round_type or InterviewRoundType.TECHNICAL_SCREEN,
        )
        brief = await CommunicationService.generate_prep_brief(db=db, user_id=user_id, payload=payload)
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Generated preparation brief for {brief.job_title} at {brief.company_name}.",
            data={
                "id": str(brief.id),
                "company_name": brief.company_name,
                "job_title": brief.job_title,
                "technical_focus_areas": brief.technical_focus_areas,
                "expected_questions": brief.expected_questions,
                "star_stories": brief.star_stories,
                "reverse_questions_to_ask": brief.reverse_questions_to_ask,
                "cheat_sheet_markdown": brief.cheat_sheet_markdown,
            },
        )


# -------------------------------------------------------------
# Tool 6: ListUpcomingInterviewsTool
# -------------------------------------------------------------
class ListUpcomingInterviewsTool(BaseTool):
    name = "list_upcoming_interviews"
    description = "List all scheduled upcoming interview sessions with round types, dates, durations, and meeting links."
    category = "COMMUNICATION"
    parameters_schema = ListInterviewsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListInterviewsParams) -> ToolResult:
        interviews = await CommunicationService.list_interviews(db=db, user_id=user_id, status=params.status)
        data = [
            {
                "id": str(i.id),
                "title": i.title,
                "company_name": i.company_name,
                "job_title": i.job_title,
                "round_type": i.round_type,
                "scheduled_at": i.scheduled_at.isoformat() if i.scheduled_at else None,
                "duration_minutes": i.duration_minutes,
                "meeting_url": i.meeting_url,
                "meeting_platform": i.meeting_platform,
                "status": i.status,
            }
            for i in interviews
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(data)} scheduled interviews.",
            data={"count": len(data), "interviews": data},
        )


# -------------------------------------------------------------
# Tool 7: GetFollowupRecommendationsTool
# -------------------------------------------------------------
class GetFollowupRecommendationsTool(BaseTool):
    name = "get_followup_recommendations"
    description = "Check stalled job applications and generate follow-up recommendations and ghosting detection warnings."
    category = "COMMUNICATION"
    parameters_schema = EmptyParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: EmptyParams) -> ToolResult:
        recs = await CommunicationService.get_follow_up_recommendations(db=db, user_id=user_id)
        data = [
            {
                "company_name": r.company_name,
                "job_title": r.job_title,
                "recruiter_name": r.recruiter_name,
                "days_inactive": r.days_inactive,
                "nudge_priority": r.nudge_priority,
                "suggested_action": r.suggested_action,
                "suggested_draft_subject": r.suggested_draft_subject,
                "suggested_draft_body": r.suggested_draft_body,
            }
            for r in recs
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(data)} follow-up opportunities.",
            data={"count": len(data), "recommendations": data},
        )


# -------------------------------------------------------------
# Tool 8: UpdateRecruiterNotesTool
# -------------------------------------------------------------
class UpdateRecruiterNotesTool(BaseTool):
    name = "update_recruiter_notes"
    description = "Update interaction notes and relationship stage for a recruiter contact."
    category = "COMMUNICATION"
    parameters_schema = UpdateRecruiterNotesParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: UpdateRecruiterNotesParams) -> ToolResult:
        try:
            rec_id = uuid.UUID(params.recruiter_id)
        except ValueError:
            return ToolResult(tool_name=self.name, success=False, summary="Invalid recruiter_id format", error="Invalid recruiter_id format")

        payload = RecruiterUpdate(
            notes=params.notes,
            relationship_stage=params.relationship_stage,
        )
        recruiter = await CommunicationService.update_recruiter(
            db=db, user_id=user_id, recruiter_id=rec_id, payload=payload
        )
        if not recruiter:
            return ToolResult(tool_name=self.name, success=False, summary="Recruiter not found", error="Recruiter not found")

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Updated notes for recruiter {recruiter.name}.",
            data={
                "id": str(recruiter.id),
                "name": recruiter.name,
                "company_name": recruiter.company_name,
                "relationship_stage": recruiter.relationship_stage,
                "notes": recruiter.notes,
            },
        )


# -------------------------------------------------------------
# Tool 9: GetCommunicationDraftsTool
# -------------------------------------------------------------
class GetCommunicationDraftsTool(BaseTool):
    name = "get_communication_drafts"
    description = "List saved candidate communication drafts with filtering by intent or approval status."
    category = "COMMUNICATION"
    parameters_schema = GetCommunicationDraftsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: GetCommunicationDraftsParams) -> ToolResult:
        drafts = await CommunicationService.list_drafts(
            db=db, user_id=user_id, intent=params.intent, status=params.status
        )
        data = [
            {
                "id": str(d.id),
                "intent": d.intent,
                "tone": d.tone,
                "subject": d.subject,
                "body_text": d.body_text,
                "status": d.status,
                "is_approved": d.is_approved,
                "created_at": d.created_at.isoformat(),
            }
            for d in drafts
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(data)} communication drafts.",
            data={"count": len(data), "drafts": data},
        )


# -------------------------------------------------------------
# Tool 10: ApproveCommunicationDraftTool
# -------------------------------------------------------------
class ApproveCommunicationDraftTool(BaseTool):
    name = "approve_communication_draft"
    description = "Explicitly approve a communication draft (Human-in-the-Loop review confirmation)."
    category = "COMMUNICATION"
    parameters_schema = ApproveDraftParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ApproveDraftParams) -> ToolResult:
        try:
            draft_id = uuid.UUID(params.draft_id)
        except ValueError:
            return ToolResult(tool_name=self.name, success=False, summary="Invalid draft_id format", error="Invalid draft_id format")

        draft = await CommunicationService.approve_draft(db=db, user_id=user_id, draft_id=draft_id)
        if not draft:
            return ToolResult(tool_name=self.name, success=False, summary="Draft not found", error="Draft not found")

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary="Draft successfully approved.",
            data={
                "draft_id": str(draft.id),
                "status": draft.status,
                "is_approved": draft.is_approved,
                "approved_at": draft.approved_at.isoformat() if draft.approved_at else None,
                "message": "Draft successfully approved.",
            },
        )

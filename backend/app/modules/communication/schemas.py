import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from app.shared.constants import (
    DraftIntent,
    DraftTone,
    DraftStatus,
    RecruiterRelationshipStage,
    InterviewRoundType,
    InterviewStatus,
)


# ==========================================
# Recruiter CRM Schemas
# ==========================================

class RecruiterBase(BaseModel):
    name: str
    email: EmailStr
    company_name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    relationship_stage: RecruiterRelationshipStage = RecruiterRelationshipStage.INITIAL_CONTACT
    notes: Optional[str] = None


class RecruiterCreate(RecruiterBase):
    pass


class RecruiterUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    relationship_stage: Optional[RecruiterRelationshipStage] = None
    responsiveness_rating: Optional[float] = None
    notes: Optional[str] = None


class RecruiterResponse(RecruiterBase):
    id: uuid.UUID
    user_id: uuid.UUID
    responsiveness_rating: Optional[float] = None
    last_interaction_at: Optional[datetime] = None
    interaction_count: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Response Drafter Schemas
# ==========================================

class DraftGenerationRequest(BaseModel):
    recruiter_id: Optional[uuid.UUID] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None
    intent: DraftIntent = DraftIntent.GENERAL
    tone: DraftTone = DraftTone.PROFESSIONAL
    candidate_availability: Optional[List[str]] = Field(default_factory=list, description="Available date/time slots")
    custom_instructions: Optional[str] = None
    salary_expectation: Optional[str] = None
    offer_details: Optional[str] = None
    incoming_email_snippet: Optional[str] = None


class DraftResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    recruiter_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None
    intent: DraftIntent
    tone: DraftTone
    subject: str
    body_text: str
    status: DraftStatus
    key_points_addressed: List[str] = Field(default_factory=list)
    candidate_availability_used: List[str] = Field(default_factory=list)
    is_approved: bool = False
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DraftUpdateRequest(BaseModel):
    subject: Optional[str] = None
    body_text: Optional[str] = None
    tone: Optional[DraftTone] = None
    is_approved: Optional[bool] = None
    status: Optional[DraftStatus] = None


# ==========================================
# Interview Intelligence Schemas
# ==========================================

class InterviewSessionBase(BaseModel):
    application_id: Optional[uuid.UUID] = None
    recruiter_id: Optional[uuid.UUID] = None
    round_type: InterviewRoundType = InterviewRoundType.TECHNICAL_SCREEN
    title: str
    company_name: str
    job_title: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int = 45
    meeting_url: Optional[str] = None
    meeting_platform: Optional[str] = None
    interviewers: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    notes: Optional[str] = None


class InterviewSessionCreate(InterviewSessionBase):
    pass


class InterviewSessionUpdate(BaseModel):
    round_type: Optional[InterviewRoundType] = None
    title: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    meeting_url: Optional[str] = None
    meeting_platform: Optional[str] = None
    interviewers: Optional[List[Dict[str, Any]]] = None
    status: Optional[InterviewStatus] = None
    notes: Optional[str] = None


class InterviewSessionResponse(InterviewSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    status: InterviewStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StarStoryItem(BaseModel):
    title: str
    situation: str
    task: str
    action: str
    result: str
    relevant_skills: List[str] = Field(default_factory=list)


class ExpectedQuestionItem(BaseModel):
    question: str
    category: str
    suggested_talking_points: List[str] = Field(default_factory=list)


class InterviewPrepBriefGenerateRequest(BaseModel):
    interview_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    company_name: str
    job_title: str
    job_description: Optional[str] = None
    round_type: Optional[InterviewRoundType] = InterviewRoundType.TECHNICAL_SCREEN


class InterviewPrepBriefResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    interview_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    company_name: str
    job_title: str
    company_overview: Optional[str] = None
    role_summary: Optional[str] = None
    technical_focus_areas: List[str] = Field(default_factory=list)
    expected_questions: List[Dict[str, Any]] = Field(default_factory=list)
    star_stories: List[Dict[str, Any]] = Field(default_factory=list)
    reverse_questions_to_ask: List[str] = Field(default_factory=list)
    cheat_sheet_markdown: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Follow-Up & Ghosting Detection Schemas
# ==========================================

class FollowUpRecommendation(BaseModel):
    application_id: Optional[uuid.UUID] = None
    company_name: str
    job_title: str
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    last_contact_date: Optional[datetime] = None
    days_inactive: int
    nudge_priority: str = Field(..., description="HIGH, MEDIUM, or LOW")
    suggested_action: str
    recommended_intent: DraftIntent = DraftIntent.FOLLOW_UP
    suggested_draft_subject: str
    suggested_draft_body: str

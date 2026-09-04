import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import String, Boolean, Text, Integer, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin
from app.shared.constants import (
    DraftIntent,
    DraftTone,
    DraftStatus,
    InterviewRoundType,
    InterviewStatus,
)


class CommunicationDraft(Base, TimestampMixin):
    __tablename__ = "communication_drafts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recruiter_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("mailbox_messages.id", ondelete="SET NULL"), nullable=True, index=True)

    intent: Mapped[str] = mapped_column(String(50), default=DraftIntent.GENERAL.value, nullable=False, index=True)
    tone: Mapped[str] = mapped_column(String(50), default=DraftTone.PROFESSIONAL.value, nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=DraftStatus.DRAFT.value, nullable=False, index=True)

    key_points_addressed: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    candidate_availability_used: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="drafts")
    recruiter: Mapped[Optional["Recruiter"]] = relationship("Recruiter", back_populates="drafts")
    application: Mapped[Optional["Application"]] = relationship("Application")
    message: Mapped[Optional["MailboxMessage"]] = relationship("MailboxMessage")


class InterviewSession(Base, TimestampMixin):
    __tablename__ = "interview_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    recruiter_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True, index=True)

    round_type: Mapped[str] = mapped_column(String(50), default=InterviewRoundType.TECHNICAL_SCREEN.value, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False)
    meeting_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    meeting_platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    interviewers: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=InterviewStatus.SCHEDULED.value, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interviews")
    application: Mapped[Optional["Application"]] = relationship("Application")
    recruiter: Mapped[Optional["Recruiter"]] = relationship("Recruiter", back_populates="interviews")
    prep_briefs: Mapped[List["InterviewPrepBrief"]] = relationship("InterviewPrepBrief", back_populates="interview", cascade="all, delete-orphan")


class InterviewPrepBrief(Base, TimestampMixin):
    __tablename__ = "interview_prep_briefs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technical_focus_areas: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    expected_questions: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)
    star_stories: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)
    reverse_questions_to_ask: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    cheat_sheet_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interview_prep_briefs")
    interview: Mapped[Optional["InterviewSession"]] = relationship("InterviewSession", back_populates="prep_briefs")
    application: Mapped[Optional["Application"]] = relationship("Application")

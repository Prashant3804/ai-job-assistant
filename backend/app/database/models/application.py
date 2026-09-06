import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Text, ForeignKey, JSON, DateTime, UniqueConstraint, Float, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin
from app.shared.constants import ApplicationStatus, SubmissionMethod, QueueStatus

class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    status: Mapped[str] = mapped_column(String(50), default=ApplicationStatus.DISCOVERED.value, nullable=False, index=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    eligibility_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    policy_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    applied_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submission_method: Mapped[str] = mapped_column(String(50), default=SubmissionMethod.MANUAL.value, nullable=False)
    external_application_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_application"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="applications")
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship("ResumeVersion", back_populates="applications")
    events: Mapped[List["ApplicationEvent"]] = relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan", order_by="desc(ApplicationEvent.created_at)")
    attempts: Mapped[List["ApplicationAttempt"]] = relationship("ApplicationAttempt", back_populates="application", cascade="all, delete-orphan", order_by="desc(ApplicationAttempt.created_at)")
    answers: Mapped[List["ApplicationAnswer"]] = relationship("ApplicationAnswer", back_populates="application", cascade="all, delete-orphan")
    documents: Mapped[List["ApplicationDocument"]] = relationship("ApplicationDocument", back_populates="application", cascade="all, delete-orphan")
    queue_items: Mapped[List["ApplicationQueueItem"]] = relationship("ApplicationQueueItem", back_populates="application", cascade="all, delete-orphan")
    emails: Mapped[List["MailboxMessage"]] = relationship("MailboxMessage", back_populates="application")

class ApplicationPolicy(Base, TimestampMixin):
    __tablename__ = "application_policies"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    auto_apply_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    minimum_match_score: Mapped[float] = mapped_column(Float, default=85.0, nullable=False)
    minimum_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maximum_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    preferred_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_roles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_locations: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_locations: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_companies: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    allowed_employment_types: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    daily_application_limit: Mapped[Optional[int]] = mapped_column(Integer, default=210, nullable=True)
    per_source_daily_limit: Mapped[Optional[int]] = mapped_column(Integer, default=30, nullable=True)
    per_company_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    duplicate_protection: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_complete_profile: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    allow_entry_level: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_internships: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_remote: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_hybrid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_onsite: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __init__(self, **kw):
        if "daily_application_limit" not in kw:
            kw["daily_application_limit"] = 210
        if "per_source_daily_limit" not in kw:
            kw["per_source_daily_limit"] = 30
        kw.setdefault("auto_apply_enabled", False)
        kw.setdefault("minimum_match_score", 85.0)
        kw.setdefault("allow_remote", True)
        kw.setdefault("allow_hybrid", True)
        kw.setdefault("allow_onsite", True)
        kw.setdefault("allow_entry_level", True)
        kw.setdefault("allow_internships", True)
        kw.setdefault("blocked_companies", [])
        kw.setdefault("blocked_keywords", [])
        kw.setdefault("blocked_roles", [])
        kw.setdefault("preferred_roles", [])
        kw.setdefault("blocked_locations", [])
        kw.setdefault("preferred_locations", [])
        kw.setdefault("allowed_employment_types", [])
        super().__init__(**kw)

    # Relationships
    user: Mapped["User"] = relationship("User")

class ApplicationQueueItem(Base, TimestampMixin):
    __tablename__ = "application_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=QueueStatus.QUEUED.value, nullable=False, index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="queue_items")
    job: Mapped["Job"] = relationship("Job")
    user: Mapped["User"] = relationship("User")

class ApplicationAttempt(Base, TimestampMixin):
    __tablename__ = "application_attempts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    submission_method: Mapped[str] = mapped_column(String(50), default=SubmissionMethod.DIRECT_API.value, nullable=False)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_application_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="attempts")

class ApplicationAnswer(Base, TimestampMixin):
    __tablename__ = "application_answers"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)

    question_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence_source: Mapped[str] = mapped_column(String(50), default="PROFILE_VERIFIED", nullable=False)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="answers")

class ApplicationDocument(Base, TimestampMixin):
    __tablename__ = "application_documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)

    document_type: Mapped[str] = mapped_column(String(50), default="RESUME", nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="documents")

class ApplicationAuditLog(Base, TimestampMixin):
    __tablename__ = "application_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    policy_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    connector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    submission_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    result: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")

class ApplicationEvent(Base, TimestampMixin):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    old_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship("Application", back_populates="events")

class DeadLetterApplicationQueue(Base, TimestampMixin):
    __tablename__ = "dead_letter_application_queue"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship("Application")
    job: Mapped["Job"] = relationship("Job")
    user: Mapped["User"] = relationship("User")

class AutoApplyDailyRun(Base, TimestampMixin):
    __tablename__ = "auto_apply_daily_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="RUNNING", nullable=False, index=True) # RUNNING, COMPLETED, FAILED, PARTIAL
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matching_jobs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    applied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    already_applied_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    manual_required_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_summary_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")


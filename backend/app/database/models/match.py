import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy import Float, Boolean, String, Text, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

class JobMatch(Base, TimestampMixin):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Explainable match scores (0.0 to 100.0)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    skill_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    skills_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # alias for backward compat
    experience_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    role_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    salary_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    preference_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # legacy alias
    
    # Skills breakdown
    matched_skills: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    missing_required_skills: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    missing_preferred_skills: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    
    # Status & Evaluation
    eligibility_status: Mapped[str] = mapped_column(String(50), default="ELIGIBLE", nullable=False, index=True)
    recommendation: Mapped[str] = mapped_column(String(50), default="POSSIBLE_MATCH", nullable=False, index=True)
    
    # Rationale & Explanations
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    scoring_version: Mapped[str] = mapped_column(String(50), default="v4.0.0", nullable=False)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Structured breakdown dictionary & legacy reasons
    score_breakdown: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    match_reasons: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),
        Index("ix_job_matches_user_score", "user_id", "overall_score"),
        Index("ix_job_matches_user_eligibility", "user_id", "eligibility_status"),
        Index("ix_job_matches_user_rec", "user_id", "recommendation"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="matches")
    job: Mapped["Job"] = relationship("Job", back_populates="matches")
    resume: Mapped[Optional["Resume"]] = relationship("Resume", back_populates="matches")
    resume_version: Mapped[Optional["ResumeVersion"]] = relationship("ResumeVersion")

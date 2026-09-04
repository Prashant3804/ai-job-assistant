import uuid
from typing import List, Optional
from datetime import date
from sqlalchemy import String, Boolean, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="CANDIDATE", nullable=False)

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    job_preferences: Mapped[Optional["JobPreference"]] = relationship("JobPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    resumes: Mapped[List["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    matches: Mapped[List["JobMatch"]] = relationship("JobMatch", back_populates="user", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    mailbox_connections: Mapped[List["MailboxConnection"]] = relationship("MailboxConnection", back_populates="user", cascade="all, delete-orphan")
    recruiters: Mapped[List["Recruiter"]] = relationship("Recruiter", back_populates="user", cascade="all, delete-orphan")
    drafts: Mapped[List["CommunicationDraft"]] = relationship("CommunicationDraft", back_populates="user", cascade="all, delete-orphan")
    interviews: Mapped[List["InterviewSession"]] = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    interview_prep_briefs: Mapped[List["InterviewPrepBrief"]] = relationship("InterviewPrepBrief", back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[List["ChatConversation"]] = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    headline: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remote_preference: Mapped[str] = mapped_column(String(50), default="REMOTE", nullable=False)
    target_roles: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    preferred_roles: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    preferred_locations: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    preferred_work_arrangement: Mapped[Optional[str]] = mapped_column(String(50), default="REMOTE", nullable=True)
    years_of_experience: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    work_authorization: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notice_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    salary_expectation: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="USER_CONFIRMED", nullable=False)
    onboarding_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="profile")
    skills: Mapped[List["CandidateSkill"]] = relationship("CandidateSkill", back_populates="profile", cascade="all, delete-orphan")
    educations: Mapped[List["Education"]] = relationship("Education", back_populates="profile", cascade="all, delete-orphan")
    experiences: Mapped[List["Experience"]] = relationship("Experience", back_populates="profile", cascade="all, delete-orphan")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="profile", cascade="all, delete-orphan")

class CandidateSkill(Base, TimestampMixin):
    __tablename__ = "candidate_skills"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), default="TECHNICAL", nullable=False)
    proficiency_level: Mapped[str] = mapped_column(String(50), default="ADVANCED", nullable=False)
    years_experience: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="skills")

class Education(Base, TimestampMixin):
    __tablename__ = "educations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gpa: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="educations")

class Experience(Base, TimestampMixin):
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[str] = mapped_column(String(50), default="FULL_TIME", nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bullet_points: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    technologies: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="experiences")

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_profile_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    technologies: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    start_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    profile: Mapped["UserProfile"] = relationship("UserProfile", back_populates="projects")

class JobPreference(Base, TimestampMixin):
    __tablename__ = "job_preferences"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    desired_titles: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    desired_locations: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    remote_types: Mapped[Optional[list]] = mapped_column(JSON, default=lambda: ["REMOTE", "HYBRID"], nullable=True)
    min_base_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_base_salary: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    employment_types: Mapped[Optional[list]] = mapped_column(JSON, default=lambda: ["FULL_TIME"], nullable=True)
    preferred_industries: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    excluded_industries: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    preferred_companies: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    blocked_companies: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    blocked_keywords: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    experience_min_years: Mapped[Optional[float]] = mapped_column(Float, default=0.0, nullable=True)
    experience_max_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    job_freshness_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    minimum_match_score: Mapped[float] = mapped_column(Float, default=70.0, nullable=False)
    target_industries: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    sponsorship_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="job_preferences")


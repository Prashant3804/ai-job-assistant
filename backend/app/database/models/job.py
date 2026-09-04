import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin
from app.shared.constants import ConnectorCapabilityStatus

class JobSource(Base, TimestampMixin):
    __tablename__ = "job_sources"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    connector_type: Mapped[str] = mapped_column(String(50), default="API", nullable=False)
    capability_status: Mapped[str] = mapped_column(
        String(50),
        default=ConnectorCapabilityStatus.SUPPORTED_JOB_DISCOVERY_ONLY.value,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    api_config: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    jobs: Mapped[List["Job"]] = relationship("Job", back_populates="job_source")

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    job_source_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("job_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str] = mapped_column(String(50), default="REMOTE", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="FULL_TIME", nullable=False)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    preferred_skills: Mapped[Optional[list]] = mapped_column(JSON, default=list, nullable=True)
    experience_level: Mapped[str] = mapped_column(String(50), default="MID_LEVEL", nullable=False)
    apply_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Deduplication: SHA-256 / composite hash prevents duplicate jobs from any source
    deduplication_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    
    # Embedding vector stored as JSON array (compatible with both SQLite & pgvector via converter)
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=True)

    # Relationships
    job_source: Mapped[Optional["JobSource"]] = relationship("JobSource", back_populates="jobs")
    matches: Mapped[List["JobMatch"]] = relationship("JobMatch", back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    tailored_resumes: Mapped[List["ResumeVersion"]] = relationship("ResumeVersion", back_populates="job")

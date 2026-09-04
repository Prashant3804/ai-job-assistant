import uuid
from typing import List, Optional
from sqlalchemy import String, Boolean, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin

class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Master Resume")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_format: Mapped[str] = mapped_column(String(50), default="PDF", nullable=False)
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="resume")
    matches: Mapped[List["JobMatch"]] = relationship("JobMatch", back_populates="resume")

class ResumeVersion(Base, TimestampMixin):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    resume_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tailored_for_job_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    tailored_content: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="versions")
    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="tailored_resumes")
    applications: Mapped[List["Application"]] = relationship("Application", back_populates="resume_version")

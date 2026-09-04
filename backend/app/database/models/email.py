import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Boolean, Text, Float, Integer, ForeignKey, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin
from app.shared.constants import (
    MailboxProviderType,
    MailboxConnectionStatus,
    EmailCategory,
    RecruiterStatus,
    EmailClassification
)

class MailboxConnection(Base, TimestampMixin):
    __tablename__ = "mailbox_connections"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default=MailboxProviderType.GMAIL.value, nullable=False, index=True)
    email_address: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    access_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scopes: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=MailboxConnectionStatus.CONNECTED.value, nullable=False, index=True)

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_cursor: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sync_state_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "provider", "email_address", name="uq_user_provider_email"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mailbox_connections")
    messages: Mapped[List["MailboxMessage"]] = relationship("MailboxMessage", back_populates="connection", cascade="all, delete-orphan")
    threads: Mapped[List["MailboxThread"]] = relationship("MailboxThread", back_populates="connection", cascade="all, delete-orphan")
    sync_states: Mapped[List["MailboxSyncState"]] = relationship("MailboxSyncState", back_populates="connection", cascade="all, delete-orphan")

# Backwards compatibility alias
EmailAccount = MailboxConnection

class MailboxMessage(Base, TimestampMixin):
    __tablename__ = "mailbox_messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("mailbox_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    
    provider: Mapped[str] = mapped_column(String(50), default=MailboxProviderType.GMAIL.value, nullable=False)
    external_message_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    external_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    sender_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    attachments_metadata: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Recruiter & Classification
    is_recruiter: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    recruiter_status: Mapped[str] = mapped_column(String(50), default=RecruiterStatus.NOT_RECRUITER.value, nullable=False)
    is_job_related: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    classification: Mapped[str] = mapped_column(String(50), default=EmailCategory.NOT_JOB_RELATED.value, nullable=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    classification_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    detected_job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    raw_headers: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    __table_args__ = (
        UniqueConstraint("connection_id", "external_message_id", name="uq_connection_external_message"),
    )

    # Relationships
    connection: Mapped["MailboxConnection"] = relationship("MailboxConnection", back_populates="messages")
    user: Mapped["User"] = relationship("User")
    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="emails")

    @property
    def email_account_id(self) -> uuid.UUID:
        return self.connection_id

# Backwards compatibility alias
EmailMessage = MailboxMessage

class MailboxThread(Base, TimestampMixin):
    __tablename__ = "mailbox_threads"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("mailbox_connections.id", ondelete="CASCADE"), nullable=False, index=True)

    external_thread_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_recruiter_thread: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    connection: Mapped["MailboxConnection"] = relationship("MailboxConnection", back_populates="threads")
    user: Mapped["User"] = relationship("User")

class MailboxSyncState(Base, TimestampMixin):
    __tablename__ = "mailbox_sync_states"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("mailbox_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    
    delta_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    history_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_sync_status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synced_messages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    connection: Mapped["MailboxConnection"] = relationship("MailboxConnection", back_populates="sync_states")

class MailboxNotification(Base, TimestampMixin):
    __tablename__ = "mailbox_notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("mailbox_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    message: Mapped[Optional["MailboxMessage"]] = relationship("MailboxMessage")

class Recruiter(Base, TimestampMixin):
    __tablename__ = "recruiters"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    relationship_stage: Mapped[str] = mapped_column(String(50), default="INITIAL_CONTACT", nullable=False)
    responsiveness_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    interaction_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recruiters")
    drafts: Mapped[List["CommunicationDraft"]] = relationship("CommunicationDraft", back_populates="recruiter")
    interviews: Mapped[List["InterviewSession"]] = relationship("InterviewSession", back_populates="recruiter")

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.shared.constants import (
    MailboxProviderType,
    MailboxConnectionStatus,
    EmailCategory,
    RecruiterStatus,
    MailboxNotificationType,
)

class OAuthAuthorizeUrlResponse(BaseModel):
    authorization_url: str
    state: str
    provider: str

class OAuthCallbackRequest(BaseModel):
    code: str
    state: str
    provider: Optional[str] = None

class MailboxConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    provider: str
    email_address: str
    status: str
    last_sync_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class MailboxMessageListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    connection_id: uuid.UUID
    provider: str
    external_message_id: str
    external_thread_id: Optional[str] = None
    sender_email: str
    sender_name: Optional[str] = None
    recipient_email: str
    subject: str
    snippet: Optional[str] = None
    received_at: datetime
    has_attachments: bool = False
    is_read: bool = False
    is_recruiter: bool = False
    recruiter_status: str
    is_job_related: bool = False
    classification: str
    confidence_score: float = 0.0
    detected_company: Optional[str] = None
    detected_job_title: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    created_at: datetime

class MailboxMessageRead(MailboxMessageListItem):
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    classification_reason: Optional[str] = None
    attachments_metadata: Optional[List[Dict[str, Any]]] = None

class MailboxThreadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    connection_id: uuid.UUID
    external_thread_id: str
    subject: str
    last_message_at: datetime
    message_count: int
    is_recruiter_thread: bool
    application_id: Optional[uuid.UUID] = None
    messages: List[MailboxMessageListItem] = Field(default_factory=list)

class SyncTriggerRequest(BaseModel):
    connection_id: Optional[uuid.UUID] = None
    full_sync: bool = False
    max_messages: int = 50

class SyncStatusResponse(BaseModel):
    connection_id: Optional[uuid.UUID] = None
    status: str
    last_sync_at: Optional[datetime] = None
    synced_count: int = 0
    message: str

class MailboxStatsResponse(BaseModel):
    total_connections: int = 0
    total_messages: int = 0
    job_related_messages: int = 0
    interview_invitations: int = 0
    rejections: int = 0
    offers: int = 0
    recruiter_messages: int = 0
    unlinked_messages: int = 0

class MailboxNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    message_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    notification_type: str
    title: str
    content: str
    is_read: bool
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

class RecruiterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    email: str
    company_name: Optional[str] = None
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

class ManualClassificationRequest(BaseModel):
    classification: str
    recruiter_status: Optional[str] = None
    detected_company: Optional[str] = None
    detected_job_title: Optional[str] = None
    application_id: Optional[uuid.UUID] = None

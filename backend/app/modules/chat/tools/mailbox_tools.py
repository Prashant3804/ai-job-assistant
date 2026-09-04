import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.email import (
    MailboxConnection,
    MailboxMessage,
    MailboxThread,
    Recruiter,
)
from app.database.models.application import Application
from app.shared.constants import EmailCategory
from app.modules.chat.tools.base import BaseTool, ToolResult

# -------------------------------------------------------------
# Parameter Schemas
# -------------------------------------------------------------
class EmptyMailboxParams(BaseModel):
    pass

class ListJobEmailsParams(BaseModel):
    limit: int = Field(default=10, ge=1, le=50, description="Max number of emails to retrieve")
    search: Optional[str] = Field(default=None, description="Search keyword in subject, sender, or company")

class ApplicationEmailsParams(BaseModel):
    application_id: Optional[str] = Field(default=None, description="UUID of the tracked application")
    company_name: Optional[str] = Field(default=None, description="Company name to find associated emails for")
    limit: int = Field(default=10, ge=1, le=50)

class EmailDetailParams(BaseModel):
    message_id: str = Field(description="UUID of the email message")

class EmailThreadParams(BaseModel):
    thread_id: Optional[str] = Field(default=None, description="UUID of the internal mailbox thread")
    external_thread_id: Optional[str] = Field(default=None, description="External provider thread ID")

# -------------------------------------------------------------
# Tool 1: GetMailboxConnectionsTool
# -------------------------------------------------------------
class GetMailboxConnectionsTool(BaseTool):
    name = "get_mailbox_connections"
    description = "List the user's connected mailbox accounts (Gmail, Outlook) and their current synchronization status."
    category = "MAILBOX"
    parameters_schema = EmptyMailboxParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: EmptyMailboxParams) -> ToolResult:
        stmt = select(MailboxConnection).where(
            and_(MailboxConnection.user_id == user_id, MailboxConnection.is_active.is_(True))
        )
        res = await db.execute(stmt)
        connections = list(res.scalars().all())

        data = [
            {
                "id": str(c.id),
                "provider": c.provider,
                "email_address": c.email_address,
                "status": c.status,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
            for c in connections
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(connections)} active connected mailbox accounts.",
            data={"connections": data, "count": len(connections)}
        )

# -------------------------------------------------------------
# Tool 2: GetRecentJobEmailsTool
# -------------------------------------------------------------
class GetRecentJobEmailsTool(BaseTool):
    name = "get_recent_job_emails"
    description = "Retrieve recent job-related emails received across connected mailboxes."
    category = "MAILBOX"
    parameters_schema = ListJobEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListJobEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(
            and_(MailboxMessage.user_id == user_id, MailboxMessage.is_job_related.is_(True))
        )
        if params.search:
            pat = f"%{params.search}%"
            stmt = stmt.where(
                or_(
                    MailboxMessage.subject.ilike(pat),
                    MailboxMessage.sender_name.ilike(pat),
                    MailboxMessage.detected_company.ilike(pat),
                )
            )
        stmt = stmt.order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "sender": m.sender_name or m.sender_email,
                "subject": m.subject,
                "classification": m.classification,
                "detected_company": m.detected_company,
                "received_at": m.received_at.isoformat(),
                "snippet": m.snippet,
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Retrieved {len(messages)} recent job emails.",
            data={"messages": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 3: GetRecruiterMessagesTool
# -------------------------------------------------------------
class GetRecruiterMessagesTool(BaseTool):
    name = "get_recruiter_messages"
    description = "List emails received directly from human recruiters or talent acquisition teams."
    category = "MAILBOX"
    parameters_schema = ListJobEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListJobEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(
            and_(MailboxMessage.user_id == user_id, MailboxMessage.is_recruiter.is_(True))
        )
        if params.search:
            pat = f"%{params.search}%"
            stmt = stmt.where(
                or_(
                    MailboxMessage.subject.ilike(pat),
                    MailboxMessage.sender_name.ilike(pat),
                    MailboxMessage.detected_company.ilike(pat),
                )
            )
        stmt = stmt.order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "recruiter_name": m.sender_name,
                "recruiter_email": m.sender_email,
                "company": m.detected_company,
                "subject": m.subject,
                "classification": m.classification,
                "received_at": m.received_at.isoformat(),
                "snippet": m.snippet,
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(messages)} recruiter messages.",
            data={"messages": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 4: GetApplicationEmailsTool
# -------------------------------------------------------------
class GetApplicationEmailsTool(BaseTool):
    name = "get_application_emails"
    description = "List emails linked to a specific job application or target company."
    category = "MAILBOX"
    parameters_schema = ApplicationEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ApplicationEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(MailboxMessage.user_id == user_id)
        if params.application_id:
            try:
                app_uuid = uuid.UUID(params.application_id)
                stmt = stmt.where(MailboxMessage.application_id == app_uuid)
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid application_id format")
        elif params.company_name:
            stmt = stmt.where(MailboxMessage.detected_company.ilike(f"%{params.company_name}%"))

        stmt = stmt.order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "subject": m.subject,
                "classification": m.classification,
                "detected_company": m.detected_company,
                "sender": m.sender_name or m.sender_email,
                "received_at": m.received_at.isoformat(),
                "snippet": m.snippet,
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(messages)} emails for application/company.",
            data={"messages": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 5: GetInterviewEmailsTool
# -------------------------------------------------------------
class GetInterviewEmailsTool(BaseTool):
    name = "get_interview_emails"
    description = "Retrieve all interview invitation emails and technical screening invitations."
    category = "MAILBOX"
    parameters_schema = ListJobEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListJobEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(
            and_(
                MailboxMessage.user_id == user_id,
                MailboxMessage.classification == EmailCategory.INTERVIEW_INVITATION.value
            )
        ).order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "company": m.detected_company,
                "sender": m.sender_name or m.sender_email,
                "subject": m.subject,
                "received_at": m.received_at.isoformat(),
                "snippet": m.snippet,
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(messages)} interview invitation emails.",
            data={"interview_emails": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 6: GetRejectionEmailsTool
# -------------------------------------------------------------
class GetRejectionEmailsTool(BaseTool):
    name = "get_rejection_emails"
    description = "Retrieve all job application rejection emails."
    category = "MAILBOX"
    parameters_schema = ListJobEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListJobEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(
            and_(
                MailboxMessage.user_id == user_id,
                MailboxMessage.classification == EmailCategory.REJECTION.value
            )
        ).order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "company": m.detected_company,
                "subject": m.subject,
                "received_at": m.received_at.isoformat(),
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(messages)} rejection emails.",
            data={"rejection_emails": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 7: GetOfferEmailsTool
# -------------------------------------------------------------
class GetOfferEmailsTool(BaseTool):
    name = "get_offer_emails"
    description = "Retrieve job offer emails and formal offer letters."
    category = "MAILBOX"
    parameters_schema = ListJobEmailsParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: ListJobEmailsParams) -> ToolResult:
        stmt = select(MailboxMessage).where(
            and_(
                MailboxMessage.user_id == user_id,
                MailboxMessage.classification == EmailCategory.OFFER.value
            )
        ).order_by(MailboxMessage.received_at.desc()).limit(params.limit)
        res = await db.execute(stmt)
        messages = list(res.scalars().all())

        data = [
            {
                "id": str(m.id),
                "company": m.detected_company,
                "sender": m.sender_name or m.sender_email,
                "subject": m.subject,
                "has_attachments": m.has_attachments,
                "received_at": m.received_at.isoformat(),
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Found {len(messages)} job offer emails.",
            data={"offer_emails": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 8: GetEmailDetailsTool
# -------------------------------------------------------------
class GetEmailDetailsTool(BaseTool):
    name = "get_email_details"
    description = "Get detailed information and text content of a specific email message."
    category = "MAILBOX"
    parameters_schema = EmailDetailParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: EmailDetailParams) -> ToolResult:
        try:
            msg_uuid = uuid.UUID(params.message_id)
        except ValueError:
            return ToolResult(tool_name=self.name, success=False, summary="Invalid message_id format")

        stmt = select(MailboxMessage).where(
            and_(MailboxMessage.id == msg_uuid, MailboxMessage.user_id == user_id)
        )
        res = await db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            return ToolResult(tool_name=self.name, success=False, summary="Email message not found")

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Retrieved email: {msg.subject}",
            data={
                "id": str(msg.id),
                "sender_name": msg.sender_name,
                "sender_email": msg.sender_email,
                "subject": msg.subject,
                "classification": msg.classification,
                "detected_company": msg.detected_company,
                "detected_job_title": msg.detected_job_title,
                "body_text": msg.body_text[:2000] if msg.body_text else "",
                "has_attachments": msg.has_attachments,
                "received_at": msg.received_at.isoformat(),
            }
        )

# -------------------------------------------------------------
# Tool 9: GetEmailThreadTool
# -------------------------------------------------------------
class GetEmailThreadTool(BaseTool):
    name = "get_email_thread"
    description = "Retrieve all messages in a conversation thread."
    category = "MAILBOX"
    parameters_schema = EmailThreadParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: EmailThreadParams) -> ToolResult:
        if params.thread_id:
            try:
                th_uuid = uuid.UUID(params.thread_id)
                stmt_th = select(MailboxThread).where(
                    and_(MailboxThread.id == th_uuid, MailboxThread.user_id == user_id)
                )
                res_th = await db.execute(stmt_th)
                thread = res_th.scalar_one_or_none()
                if not thread:
                    return ToolResult(tool_name=self.name, success=False, summary="Thread not found")
                ext_thread_id = thread.external_thread_id
            except ValueError:
                return ToolResult(tool_name=self.name, success=False, summary="Invalid thread_id format")
        elif params.external_thread_id:
            ext_thread_id = params.external_thread_id
        else:
            return ToolResult(tool_name=self.name, success=False, summary="Please provide thread_id or external_thread_id")

        stmt_msgs = select(MailboxMessage).where(
            and_(MailboxMessage.user_id == user_id, MailboxMessage.external_thread_id == ext_thread_id)
        ).order_by(MailboxMessage.received_at.asc())
        res_msgs = await db.execute(stmt_msgs)
        messages = list(res_msgs.scalars().all())

        data = [
            {
                "id": str(m.id),
                "sender": m.sender_name or m.sender_email,
                "subject": m.subject,
                "received_at": m.received_at.isoformat(),
                "snippet": m.snippet,
            }
            for m in messages
        ]
        return ToolResult(
            tool_name=self.name,
            success=True,
            summary=f"Retrieved {len(messages)} messages in thread.",
            data={"thread_id": ext_thread_id, "messages": data, "count": len(messages)}
        )

# -------------------------------------------------------------
# Tool 10: GetMailboxSyncStatusTool
# -------------------------------------------------------------
class GetMailboxSyncStatusTool(BaseTool):
    name = "get_mailbox_sync_status"
    description = "Check overall mailbox synchronization status, connected accounts, and email intelligence metrics."
    category = "MAILBOX"
    parameters_schema = EmptyMailboxParams

    async def run(self, user_id: uuid.UUID, db: AsyncSession, params: EmptyMailboxParams) -> ToolResult:
        stmt_conns = select(MailboxConnection).where(
            and_(MailboxConnection.user_id == user_id, MailboxConnection.is_active.is_(True))
        )
        res_conns = await db.execute(stmt_conns)
        conns = list(res_conns.scalars().all())

        stmt_msgs = select(MailboxMessage).where(MailboxMessage.user_id == user_id)
        res_msgs = await db.execute(stmt_msgs)
        all_msgs = list(res_msgs.scalars().all())

        job_related = [m for m in all_msgs if m.is_job_related]
        interviews = [m for m in all_msgs if m.classification == EmailCategory.INTERVIEW_INVITATION.value]
        offers = [m for m in all_msgs if m.classification == EmailCategory.OFFER.value]
        rejections = [m for m in all_msgs if m.classification == EmailCategory.REJECTION.value]
        recruiters = [m for m in all_msgs if m.is_recruiter]

        return ToolResult(
            tool_name=self.name,
            success=True,
            summary="Mailbox synchronization status retrieved.",
            data={
                "connected_accounts": len(conns),
                "total_messages": len(all_msgs),
                "job_related_emails": len(job_related),
                "interview_invitations": len(interviews),
                "job_offers": len(offers),
                "rejections": len(rejections),
                "recruiter_contacts": len(recruiters),
            }
        )

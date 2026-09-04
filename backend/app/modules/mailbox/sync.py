import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.models.email import (
    MailboxConnection,
    MailboxMessage,
    MailboxThread,
    MailboxSyncState,
    MailboxNotification,
    Recruiter,
)
from app.database.models.application import Application, ApplicationEvent
from app.shared.constants import (
    MailboxProviderType,
    MailboxConnectionStatus,
    EmailCategory,
    ApplicationEventType,
    MailboxNotificationType,
)
from app.modules.mailbox.security import decrypt_token, encrypt_token
from app.modules.mailbox.oauth.gmail import GoogleOAuthClient
from app.modules.mailbox.oauth.microsoft import MicrosoftOAuthClient
from app.modules.mailbox.providers.base import BaseMailboxProvider
from app.modules.mailbox.providers.gmail import GmailMailboxProvider
from app.modules.mailbox.providers.microsoft import MicrosoftMailboxProvider
from app.modules.mailbox.providers.mock import MockMailboxProvider
from app.modules.mailbox.classifier import EmailClassifier
from app.modules.mailbox.matcher import ApplicationEmailMatcher
from app.modules.mailbox.exceptions import (
    MailboxAuthError,
    TokenExpiredError,
    ProviderRateLimitError,
    MailboxSyncError,
    MailboxConnectionNotFoundError,
)

def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

class MailboxSyncService:
    def __init__(self, db: AsyncSession, classifier: Optional[EmailClassifier] = None):
        self.db = db
        self.classifier = classifier or EmailClassifier()
        self.matcher = ApplicationEmailMatcher(db)

    async def _get_provider_instance(self, connection: MailboxConnection) -> BaseMailboxProvider:
        raw_access = decrypt_token(connection.access_token_encrypted)
        
        # If token is a test/mock token or in offline/mock mode
        if not raw_access or raw_access.startswith("mock_") or raw_access.startswith("test_") or not settings.MAILBOX_SYNC_ENABLED:
            return MockMailboxProvider(account_email=connection.email_address)

        # Check token expiration
        if connection.token_expires_at and ensure_utc(connection.token_expires_at) <= datetime.now(timezone.utc):
            raw_access = await self._refresh_connection_token(connection)

        if connection.provider == MailboxProviderType.GMAIL.value:
            return GmailMailboxProvider(access_token=raw_access)
        elif connection.provider == MailboxProviderType.OUTLOOK.value:
            return MicrosoftMailboxProvider(access_token=raw_access)
        else:
            return MockMailboxProvider(account_email=connection.email_address)

    async def _refresh_connection_token(self, connection: MailboxConnection) -> str:
        raw_refresh = decrypt_token(connection.refresh_token_encrypted)
        if not raw_refresh:
            connection.status = MailboxConnectionStatus.NEEDS_REAUTH.value
            await self.db.commit()
            raise TokenExpiredError("Missing refresh token. Mailbox connection requires re-authentication.")

        if connection.provider == MailboxProviderType.GMAIL.value:
            oauth_client = GoogleOAuthClient()
        else:
            oauth_client = MicrosoftOAuthClient()

        try:
            tokens = await oauth_client.refresh_access_token(raw_refresh)
            new_access = tokens["access_token"]
            expires_in = tokens.get("expires_in", 3600)
            
            connection.access_token_encrypted = encrypt_token(new_access)
            if tokens.get("refresh_token"):
                connection.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
            connection.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            connection.status = MailboxConnectionStatus.CONNECTED.value
            await self.db.commit()
            return new_access
        except Exception as exc:
            connection.status = MailboxConnectionStatus.NEEDS_REAUTH.value
            await self.db.commit()
            raise TokenExpiredError(f"Failed to refresh mailbox token: {exc}")

    async def sync_connection(
        self,
        connection_id: uuid.UUID,
        max_messages: int = 50,
        full_sync: bool = False
    ) -> Dict[str, Any]:
        """Synchronizes messages for a specific MailboxConnection."""
        stmt = select(MailboxConnection).where(MailboxConnection.id == connection_id)
        res = await self.db.execute(stmt)
        conn = res.scalar_one_or_none()
        if not conn:
            raise MailboxConnectionNotFoundError(f"MailboxConnection {connection_id} not found")

        conn.status = MailboxConnectionStatus.SYNCING.value
        await self.db.commit()

        try:
            provider = await self._get_provider_instance(conn)
            
            since = None
            if not full_sync and conn.last_sync_at:
                since = ensure_utc(conn.last_sync_at) - timedelta(hours=1) # small overlap for safety
            elif not full_sync:
                since = datetime.now(timezone.utc) - timedelta(days=settings.MAILBOX_INITIAL_SYNC_DAYS)

            normalized_messages, next_cursor = await provider.fetch_messages(
                cursor=conn.sync_cursor if not full_sync else None,
                max_results=max_messages,
                since=since
            )

            new_message_count = 0
            # Process in chronological order so timeline and status transitions progress forward
            sorted_messages = sorted(
                normalized_messages,
                key=lambda m: m.received_at if m.received_at.tzinfo is not None else m.received_at.replace(tzinfo=timezone.utc)
            )
            for norm_msg in sorted_messages:
                # Deduplication check
                stmt_dup = select(MailboxMessage).where(
                    and_(
                        MailboxMessage.connection_id == conn.id,
                        MailboxMessage.external_message_id == norm_msg.external_message_id
                    )
                )
                res_dup = await self.db.execute(stmt_dup)
                existing = res_dup.scalar_one_or_none()
                if existing:
                    continue

                # Classify
                classification = await self.classifier.classify(norm_msg)

                # Match Application
                matched_app = await self.matcher.match_email_to_application(
                    user_id=conn.user_id,
                    email=norm_msg,
                    classification=classification
                )

                app_id = matched_app.id if matched_app else None

                # Update Application status and timeline if appropriate
                if matched_app and classification.suggested_application_status:
                    old_st = matched_app.status
                    new_st = classification.suggested_application_status
                    if old_st != new_st:
                        matched_app.status = new_st
                        event = ApplicationEvent(
                            application_id=matched_app.id,
                            event_type=ApplicationEventType.EMAIL_RECEIVED.value,
                            old_status=old_st,
                            new_status=new_st,
                            title=f"Email Update: {classification.classification.replace('_', ' ').title()}",
                            description=f"{norm_msg.subject} - {classification.classification_reason or ''}"
                        )
                        self.db.add(event)

                # Store Message
                msg_entity = MailboxMessage(
                    user_id=conn.user_id,
                    connection_id=conn.id,
                    provider=conn.provider,
                    external_message_id=norm_msg.external_message_id,
                    external_thread_id=norm_msg.external_thread_id,
                    sender_email=norm_msg.sender_email,
                    sender_name=norm_msg.sender_name,
                    recipient_email=norm_msg.recipient_email,
                    subject=norm_msg.subject,
                    snippet=norm_msg.snippet,
                    body_text=norm_msg.body_text,
                    body_html=norm_msg.body_html,
                    received_at=norm_msg.received_at,
                    has_attachments=norm_msg.has_attachments,
                    attachments_metadata=norm_msg.attachments,
                    is_read=False,
                    is_recruiter=classification.is_recruiter,
                    recruiter_status=classification.recruiter_status,
                    is_job_related=classification.is_job_related,
                    classification=classification.classification,
                    confidence_score=classification.confidence_score,
                    classification_reason=classification.classification_reason,
                    detected_company=classification.detected_company,
                    detected_job_title=classification.detected_job_title,
                    application_id=app_id,
                    raw_headers=norm_msg.raw_headers,
                )
                self.db.add(msg_entity)
                await self.db.flush()

                # Upsert Thread
                if norm_msg.external_thread_id:
                    stmt_th = select(MailboxThread).where(
                        and_(
                            MailboxThread.connection_id == conn.id,
                            MailboxThread.external_thread_id == norm_msg.external_thread_id
                        )
                    )
                    res_th = await self.db.execute(stmt_th)
                    thread_entity = res_th.scalar_one_or_none()
                    if not thread_entity:
                        thread_entity = MailboxThread(
                            user_id=conn.user_id,
                            connection_id=conn.id,
                            external_thread_id=norm_msg.external_thread_id,
                            subject=norm_msg.subject,
                            last_message_at=norm_msg.received_at,
                            message_count=1,
                            is_recruiter_thread=classification.is_recruiter,
                            application_id=app_id,
                        )
                        self.db.add(thread_entity)
                    else:
                        thread_entity.message_count += 1
                        if ensure_utc(norm_msg.received_at) > ensure_utc(thread_entity.last_message_at):
                            thread_entity.last_message_at = norm_msg.received_at
                        if classification.is_recruiter:
                            thread_entity.is_recruiter_thread = True
                        if app_id and not thread_entity.application_id:
                            thread_entity.application_id = app_id

                # Upsert Recruiter record if direct recruiter email
                if classification.is_recruiter and norm_msg.sender_name:
                    stmt_rec = select(Recruiter).where(
                        and_(
                            Recruiter.user_id == conn.user_id,
                            Recruiter.email == norm_msg.sender_email
                        )
                    )
                    res_rec = await self.db.execute(stmt_rec)
                    rec = res_rec.scalar_one_or_none()
                    if not rec:
                        rec = Recruiter(
                            user_id=conn.user_id,
                            name=norm_msg.sender_name,
                            email=norm_msg.sender_email,
                            company_name=classification.detected_company,
                            title="Recruiter / Talent Acquisition",
                        )
                        self.db.add(rec)
                    elif classification.detected_company and not rec.company_name:
                        rec.company_name = classification.detected_company

                # Create Notification for important recruiter milestones
                if classification.is_job_related and classification.classification in [
                    EmailCategory.INTERVIEW_INVITATION.value,
                    EmailCategory.OFFER.value,
                    EmailCategory.ASSESSMENT_REQUEST.value,
                    EmailCategory.REJECTION.value,
                ]:
                    notif_type = f"EMAIL_{classification.classification}"
                    notif = MailboxNotification(
                        user_id=conn.user_id,
                        message_id=msg_entity.id,
                        application_id=app_id,
                        notification_type=notif_type,
                        title=f"{classification.classification.replace('_', ' ').title()}: {classification.detected_company or 'Recruiter'}",
                        content=norm_msg.snippet or norm_msg.subject,
                        metadata_json={
                            "company": classification.detected_company,
                            "subject": norm_msg.subject,
                            "classification": classification.classification,
                        }
                    )
                    self.db.add(notif)

                new_message_count += 1

            conn.status = MailboxConnectionStatus.CONNECTED.value
            conn.last_sync_at = datetime.now(timezone.utc)
            conn.sync_cursor = next_cursor

            # Record sync state
            sync_state = MailboxSyncState(
                connection_id=conn.id,
                delta_token=next_cursor,
                last_sync_status="SUCCESS",
                synced_messages_count=new_message_count,
            )
            self.db.add(sync_state)

            await self.db.commit()
            return {
                "status": "SUCCESS",
                "synced_count": new_message_count,
                "connection_id": conn.id,
                "message": f"Successfully synced {new_message_count} new messages.",
            }

        except TokenExpiredError as exc:
            conn.status = MailboxConnectionStatus.NEEDS_REAUTH.value
            sync_state = MailboxSyncState(
                connection_id=conn.id,
                last_sync_status="AUTH_ERROR",
                last_error=str(exc),
                synced_messages_count=0,
            )
            self.db.add(sync_state)
            await self.db.commit()
            raise

        except Exception as exc:
            conn.status = MailboxConnectionStatus.ERROR.value
            sync_state = MailboxSyncState(
                connection_id=conn.id,
                last_sync_status="ERROR",
                last_error=str(exc),
                synced_messages_count=0,
            )
            self.db.add(sync_state)
            await self.db.commit()
            raise MailboxSyncError(f"Sync failed for connection {connection_id}: {exc}")

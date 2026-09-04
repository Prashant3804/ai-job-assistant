import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.email import (
    MailboxConnection,
    MailboxMessage,
    MailboxThread,
    MailboxNotification,
    Recruiter,
)
from app.database.models.application import Application
from app.shared.constants import (
    MailboxProviderType,
    MailboxConnectionStatus,
    EmailCategory,
)
from app.modules.mailbox.security import (
    encrypt_token,
    decrypt_token,
    generate_oauth_state,
    validate_oauth_state,
)
from app.modules.mailbox.oauth.gmail import GoogleOAuthClient
from app.modules.mailbox.oauth.microsoft import MicrosoftOAuthClient
from app.modules.mailbox.sync import MailboxSyncService
from app.modules.mailbox.schemas import (
    OAuthAuthorizeUrlResponse,
    MailboxStatsResponse,
    ManualClassificationRequest,
)
from app.modules.mailbox.exceptions import (
    MailboxAuthError,
    OAuthStateMismatchError,
    MailboxConnectionNotFoundError,
)

class MailboxService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sync_service = MailboxSyncService(db)

    def get_oauth_authorize_url(self, user_id: uuid.UUID, provider: str) -> OAuthAuthorizeUrlResponse:
        prov_lower = provider.lower()
        state = generate_oauth_state(user_id=user_id, provider=prov_lower)

        if prov_lower in ["gmail", "google"]:
            client = GoogleOAuthClient()
            url = client.get_authorization_url(state)
            return OAuthAuthorizeUrlResponse(authorization_url=url, state=state, provider=MailboxProviderType.GMAIL.value)
        elif prov_lower in ["outlook", "microsoft", "office365"]:
            client = MicrosoftOAuthClient()
            url = client.get_authorization_url(state)
            return OAuthAuthorizeUrlResponse(authorization_url=url, state=state, provider=MailboxProviderType.OUTLOOK.value)
        else:
            raise ValueError(f"Unsupported mailbox provider: {provider}")

    async def handle_oauth_callback(
        self,
        current_user_id: uuid.UUID,
        code: str,
        state: str,
        provider: Optional[str] = None
    ) -> MailboxConnection:
        # Validate OAuth state HMAC signature & expiry
        try:
            state_user_id = validate_oauth_state(state, expected_provider=provider)
        except Exception as exc:
            raise OAuthStateMismatchError(f"OAuth state validation failed: {exc}")

        if state_user_id != current_user_id:
            raise OAuthStateMismatchError("OAuth state user mismatch: potential CSRF attempt.")

        # Determine provider
        prov = (provider or "gmail").lower()
        if "outlook" in prov or "microsoft" in prov:
            oauth_client = MicrosoftOAuthClient()
            prov_type = MailboxProviderType.OUTLOOK.value
        else:
            oauth_client = GoogleOAuthClient()
            prov_type = MailboxProviderType.GMAIL.value

        tokens = await oauth_client.exchange_code(code)

        email_address = tokens.get("email_address") or f"user-{current_user_id}@example.com"
        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)
        token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Check existing connection for this user and provider
        stmt = select(MailboxConnection).where(
            and_(
                MailboxConnection.user_id == current_user_id,
                MailboxConnection.provider == prov_type,
                MailboxConnection.email_address == email_address
            )
        )
        res = await self.db.execute(stmt)
        conn = res.scalar_one_or_none()

        if not conn:
            conn = MailboxConnection(
                user_id=current_user_id,
                provider=prov_type,
                email_address=email_address,
                provider_account_id=tokens.get("provider_account_id"),
                access_token_encrypted=encrypt_token(access_token),
                refresh_token_encrypted=encrypt_token(refresh_token) if refresh_token else None,
                token_expires_at=token_expires_at,
                scopes=tokens.get("scopes", []),
                status=MailboxConnectionStatus.CONNECTED.value,
                is_active=True,
            )
            self.db.add(conn)
        else:
            conn.access_token_encrypted = encrypt_token(access_token)
            if refresh_token:
                conn.refresh_token_encrypted = encrypt_token(refresh_token)
            conn.token_expires_at = token_expires_at
            conn.status = MailboxConnectionStatus.CONNECTED.value
            conn.is_active = True

        await self.db.commit()
        await self.db.refresh(conn)

        # Trigger immediate initial sync
        try:
            await self.sync_service.sync_connection(conn.id, max_messages=25)
        except Exception:
            pass # Non-blocking on initial connect

        return conn

    async def list_connections(self, user_id: uuid.UUID) -> List[MailboxConnection]:
        stmt = (
            select(MailboxConnection)
            .where(and_(MailboxConnection.user_id == user_id, MailboxConnection.is_active.is_(True)))
            .order_by(MailboxConnection.created_at.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def disconnect_mailbox(self, user_id: uuid.UUID, connection_id: uuid.UUID) -> bool:
        stmt = select(MailboxConnection).where(
            and_(MailboxConnection.id == connection_id, MailboxConnection.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        conn = res.scalar_one_or_none()
        if not conn:
            return False

        conn.is_active = False
        conn.status = MailboxConnectionStatus.DISCONNECTED.value
        conn.access_token_encrypted = None
        conn.refresh_token_encrypted = None
        await self.db.commit()
        return True

    async def sync_connection(self, user_id: uuid.UUID, connection_id: uuid.UUID, full_sync: bool = False) -> Dict[str, Any]:
        stmt = select(MailboxConnection).where(
            and_(MailboxConnection.id == connection_id, MailboxConnection.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        conn = res.scalar_one_or_none()
        if not conn:
            raise MailboxConnectionNotFoundError(f"Connection {connection_id} not found")

        return await self.sync_service.sync_connection(conn.id, full_sync=full_sync)

    async def sync_all_connections(self, user_id: uuid.UUID, full_sync: bool = False) -> List[Dict[str, Any]]:
        connections = await self.list_connections(user_id)
        results = []
        for conn in connections:
            try:
                res = await self.sync_service.sync_connection(conn.id, full_sync=full_sync)
                results.append(res)
            except Exception as exc:
                results.append({"connection_id": conn.id, "status": "ERROR", "error": str(exc)})
        return results

    async def list_messages(
        self,
        user_id: uuid.UUID,
        category: Optional[str] = None,
        recruiter_only: bool = False,
        application_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[MailboxMessage]:
        stmt = select(MailboxMessage).where(MailboxMessage.user_id == user_id)

        if category:
            stmt = stmt.where(MailboxMessage.classification == category)
        if recruiter_only:
            stmt = stmt.where(MailboxMessage.is_recruiter.is_(True))
        if application_id:
            stmt = stmt.where(MailboxMessage.application_id == application_id)
        if search:
            search_pat = f"%{search}%"
            stmt = stmt.where(
                or_(
                    MailboxMessage.subject.ilike(search_pat),
                    MailboxMessage.sender_email.ilike(search_pat),
                    MailboxMessage.sender_name.ilike(search_pat),
                    MailboxMessage.detected_company.ilike(search_pat),
                )
            )

        stmt = stmt.order_by(MailboxMessage.received_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_message_detail(self, user_id: uuid.UUID, message_id: uuid.UUID) -> Optional[MailboxMessage]:
        stmt = select(MailboxMessage).where(
            and_(MailboxMessage.id == message_id, MailboxMessage.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        msg = res.scalar_one_or_none()
        if msg and not msg.is_read:
            msg.is_read = True
            await self.db.commit()
        return msg

    async def list_threads(
        self,
        user_id: uuid.UUID,
        recruiter_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[MailboxThread]:
        stmt = select(MailboxThread).where(MailboxThread.user_id == user_id)
        if recruiter_only:
            stmt = stmt.where(MailboxThread.is_recruiter_thread.is_(True))
        stmt = stmt.order_by(MailboxThread.last_message_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_thread_detail(self, user_id: uuid.UUID, thread_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        stmt_th = select(MailboxThread).where(
            and_(MailboxThread.id == thread_id, MailboxThread.user_id == user_id)
        )
        res_th = await self.db.execute(stmt_th)
        thread = res_th.scalar_one_or_none()
        if not thread:
            return None

        stmt_msg = (
            select(MailboxMessage)
            .where(
                and_(
                    MailboxMessage.user_id == user_id,
                    MailboxMessage.connection_id == thread.connection_id,
                    MailboxMessage.external_thread_id == thread.external_thread_id
                )
            )
            .order_by(MailboxMessage.received_at.asc())
        )
        res_msg = await self.db.execute(stmt_msg)
        messages = list(res_msg.scalars().all())

        return {
            "thread": thread,
            "messages": messages
        }

    async def get_mailbox_stats(self, user_id: uuid.UUID) -> MailboxStatsResponse:
        stmt_conn = select(func.count(MailboxConnection.id)).where(
            and_(MailboxConnection.user_id == user_id, MailboxConnection.is_active.is_(True))
        )
        res_conn = await self.db.execute(stmt_conn)
        total_connections = res_conn.scalar() or 0

        stmt_msgs = select(
            func.count(MailboxMessage.id).label("total"),
            func.count(MailboxMessage.id).filter(MailboxMessage.is_job_related.is_(True)).label("job_related"),
            func.count(MailboxMessage.id).filter(MailboxMessage.classification == EmailCategory.INTERVIEW_INVITATION.value).label("interviews"),
            func.count(MailboxMessage.id).filter(MailboxMessage.classification == EmailCategory.REJECTION.value).label("rejections"),
            func.count(MailboxMessage.id).filter(MailboxMessage.classification == EmailCategory.OFFER.value).label("offers"),
            func.count(MailboxMessage.id).filter(MailboxMessage.is_recruiter.is_(True)).label("recruiters"),
            func.count(MailboxMessage.id).filter(and_(MailboxMessage.is_job_related.is_(True), MailboxMessage.application_id.is_(None))).label("unlinked"),
        ).where(MailboxMessage.user_id == user_id)

        res_msgs = await self.db.execute(stmt_msgs)
        row = res_msgs.first()

        if not row:
            return MailboxStatsResponse(total_connections=total_connections)

        return MailboxStatsResponse(
            total_connections=total_connections,
            total_messages=row.total or 0,
            job_related_messages=row.job_related or 0,
            interview_invitations=row.interviews or 0,
            rejections=row.rejections or 0,
            offers=row.offers or 0,
            recruiter_messages=row.recruiters or 0,
            unlinked_messages=row.unlinked or 0,
        )

    async def list_notifications(self, user_id: uuid.UUID, unread_only: bool = False) -> List[MailboxNotification]:
        stmt = select(MailboxNotification).where(MailboxNotification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(MailboxNotification.is_read.is_(False))
        stmt = stmt.order_by(MailboxNotification.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def mark_notification_as_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
        stmt = select(MailboxNotification).where(
            and_(MailboxNotification.id == notification_id, MailboxNotification.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        notif = res.scalar_one_or_none()
        if not notif:
            return False
        notif.is_read = True
        await self.db.commit()
        return True

    async def list_recruiters(self, user_id: uuid.UUID) -> List[Recruiter]:
        stmt = select(Recruiter).where(Recruiter.user_id == user_id).order_by(Recruiter.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def reclassify_message(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        payload: ManualClassificationRequest
    ) -> MailboxMessage:
        stmt = select(MailboxMessage).where(
            and_(MailboxMessage.id == message_id, MailboxMessage.user_id == user_id)
        )
        res = await self.db.execute(stmt)
        msg = res.scalar_one_or_none()
        if not msg:
            raise MailboxConnectionNotFoundError(f"Message {message_id} not found")

        msg.classification = payload.classification
        if payload.recruiter_status:
            msg.recruiter_status = payload.recruiter_status
            msg.is_recruiter = payload.recruiter_status != "NOT_RECRUITER"
        if payload.detected_company:
            msg.detected_company = payload.detected_company
        if payload.detected_job_title:
            msg.detected_job_title = payload.detected_job_title
        if payload.application_id is not None:
            msg.application_id = payload.application_id

        msg.is_job_related = payload.classification != EmailCategory.NOT_JOB_RELATED.value
        msg.confidence_score = 1.0
        msg.classification_reason = "Manually verified by user"

        await self.db.commit()
        await self.db.refresh(msg)
        return msg

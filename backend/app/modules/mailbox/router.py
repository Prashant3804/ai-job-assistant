import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.modules.mailbox.service import MailboxService
from app.modules.mailbox.schemas import (
    OAuthAuthorizeUrlResponse,
    OAuthCallbackRequest,
    MailboxConnectionRead,
    MailboxMessageListItem,
    MailboxMessageRead,
    MailboxThreadRead,
    SyncTriggerRequest,
    SyncStatusResponse,
    MailboxStatsResponse,
    MailboxNotificationRead,
    RecruiterRead,
    ManualClassificationRequest,
)
from app.modules.mailbox.exceptions import (
    MailboxAuthError,
    OAuthStateMismatchError,
    MailboxConnectionNotFoundError,
    MailboxSyncError,
)

router = APIRouter(prefix="/mailbox", tags=["Mailbox & OAuth Integration"])

@router.get("/connect/gmail", response_model=OAuthAuthorizeUrlResponse)
async def get_gmail_connect_url(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    return service.get_oauth_authorize_url(current_user.id, "gmail")

@router.get("/connect/outlook", response_model=OAuthAuthorizeUrlResponse)
async def get_outlook_connect_url(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    return service.get_oauth_authorize_url(current_user.id, "outlook")

@router.post("/callback", response_model=MailboxConnectionRead)
async def handle_oauth_callback(
    payload: OAuthCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    try:
        conn = await service.handle_oauth_callback(
            current_user_id=current_user.id,
            code=payload.code,
            state=payload.state,
            provider=payload.provider
        )
        return MailboxConnectionRead.model_validate(conn, from_attributes=True)
    except OAuthStateMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except MailboxAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/connections", response_model=List[MailboxConnectionRead])
async def list_mailbox_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    connections = await service.list_connections(current_user.id)
    return [MailboxConnectionRead.model_validate(c, from_attributes=True) for c in connections]

@router.delete("/connections/{connection_id}", response_model=dict)
async def disconnect_mailbox(
    connection_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    success = await service.disconnect_mailbox(current_user.id, connection_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mailbox connection not found")
    return {"message": "Mailbox disconnected successfully", "connection_id": str(connection_id)}

@router.post("/sync", response_model=List[dict])
async def trigger_mailbox_sync(
    payload: SyncTriggerRequest = SyncTriggerRequest(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    try:
        if payload.connection_id:
            res = await service.sync_connection(current_user.id, payload.connection_id, full_sync=payload.full_sync)
            return [res]
        else:
            return await service.sync_all_connections(current_user.id, full_sync=payload.full_sync)
    except MailboxConnectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except MailboxSyncError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

@router.get("/messages", response_model=List[MailboxMessageListItem])
async def list_mailbox_messages(
    category: Optional[str] = Query(None),
    recruiter_only: bool = Query(False),
    application_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    messages = await service.list_messages(
        user_id=current_user.id,
        category=category,
        recruiter_only=recruiter_only,
        application_id=application_id,
        search=search,
        limit=limit,
        offset=offset
    )
    return [MailboxMessageListItem.model_validate(m, from_attributes=True) for m in messages]

@router.get("/messages/{message_id}", response_model=MailboxMessageRead)
async def get_mailbox_message(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    msg = await service.get_message_detail(current_user.id, message_id)
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return MailboxMessageRead.model_validate(msg, from_attributes=True)

@router.post("/messages/{message_id}/reclassify", response_model=MailboxMessageRead)
async def reclassify_message(
    message_id: uuid.UUID,
    payload: ManualClassificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    try:
        updated = await service.reclassify_message(current_user.id, message_id, payload)
        return MailboxMessageRead.model_validate(updated, from_attributes=True)
    except MailboxConnectionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@router.get("/threads", response_model=List[MailboxThreadRead])
async def list_mailbox_threads(
    recruiter_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    threads = await service.list_threads(current_user.id, recruiter_only=recruiter_only, limit=limit, offset=offset)
    return [MailboxThreadRead.model_validate(t, from_attributes=True) for t in threads]

@router.get("/threads/{thread_id}", response_model=dict)
async def get_mailbox_thread(
    thread_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    res = await service.get_thread_detail(current_user.id, thread_id)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    
    thread_dict = MailboxThreadRead.model_validate(res["thread"], from_attributes=True).model_dump()
    thread_dict["messages"] = [MailboxMessageListItem.model_validate(m, from_attributes=True).model_dump() for m in res["messages"]]
    return thread_dict

@router.get("/stats", response_model=MailboxStatsResponse)
async def get_mailbox_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    return await service.get_mailbox_stats(current_user.id)

@router.get("/notifications", response_model=List[MailboxNotificationRead])
async def list_mailbox_notifications(
    unread_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    notifs = await service.list_notifications(current_user.id, unread_only=unread_only)
    return [MailboxNotificationRead.model_validate(n, from_attributes=True) for n in notifs]

@router.post("/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    success = await service.mark_notification_as_read(current_user.id, notification_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return {"message": "Notification marked as read"}

@router.get("/recruiters", response_model=List[RecruiterRead])
async def list_recruiters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = MailboxService(db)
    recruiters = await service.list_recruiters(current_user.id)
    return [RecruiterRead.model_validate(r, from_attributes=True) for r in recruiters]

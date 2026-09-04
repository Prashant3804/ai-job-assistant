from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.modules.email.service import EmailIntelligenceService
from app.shared.schemas import (
    EmailMessageRead,
    EmailClassifyRequest,
    EmailClassifyResponse,
    RecruiterRead,
    APIResponse,
)

router = APIRouter(prefix="/email", tags=["Email Intelligence & Recruiters"])

@router.get("/messages", response_model=List[EmailMessageRead])
async def list_emails(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmailIntelligenceService(db)
    messages = await service.list_messages(current_user.id)
    return [EmailMessageRead.model_validate(m, from_attributes=True) for m in messages]

@router.post("/classify", response_model=EmailClassifyResponse)
async def classify_email_content(
    payload: EmailClassifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmailIntelligenceService(db)
    return await service.classify_message_content(payload)

@router.get("/recruiters", response_model=List[RecruiterRead])
async def list_recruiters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    service = EmailIntelligenceService(db)
    recruiters = await service.list_recruiters(current_user.id)
    return [RecruiterRead.model_validate(r, from_attributes=True) for r in recruiters]

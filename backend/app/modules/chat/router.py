from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.user import User
from app.modules.auth.service import get_current_user
from app.modules.chat.service import ChatAssistantService
from app.modules.chat.schemas import (
    CreateConversationRequest,
    ChatSendMessageRequest,
    ChatMessageRead,
    ChatConversationRead,
    ChatConversationDetail,
)
from app.shared.schemas import APIResponse

router = APIRouter(prefix="/chat", tags=["AI Conversational Assistant"])

@router.post("/conversations", response_model=ChatConversationRead, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: Optional[CreateConversationRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new dedicated chat conversation session."""
    service = ChatAssistantService(db)
    conv = await service.create_conversation(current_user.id, payload)
    return ChatConversationRead(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        context_type=conv.context_type,
        reference_id=conv.reference_id,
        metadata_json=conv.metadata_json or {},
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=1
    )

@router.get("/conversations", response_model=List[ChatConversationRead])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all chat conversations for the current authenticated user."""
    service = ChatAssistantService(db)
    return await service.list_conversations(current_user.id)

@router.get("/conversations/{conversation_id}", response_model=ChatConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation details and full message history."""
    service = ChatAssistantService(db)
    return await service.get_conversation_detail(current_user.id, conversation_id)

@router.delete("/conversations/{conversation_id}", response_model=APIResponse)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and its messages."""
    service = ChatAssistantService(db)
    await service.delete_conversation(current_user.id, conversation_id)
    return APIResponse(message="Conversation deleted successfully")

@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageRead)
async def send_message_to_conversation(
    conversation_id: uuid.UUID,
    payload: ChatSendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send user message to a specific conversation, execute controlled tools, and receive AI synthesized response."""
    payload.conversation_id = conversation_id
    service = ChatAssistantService(db)
    return await service.handle_user_message(current_user, payload)

@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessageRead])
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all messages in a conversation with tool execution metadata."""
    service = ChatAssistantService(db)
    return await service.get_conversation_messages(current_user.id, conversation_id)

@router.post("/messages", response_model=ChatMessageRead)
async def send_message_general(
    payload: ChatSendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Legacy compatibility endpoint for single-turn or auto-created conversation messages."""
    service = ChatAssistantService(db)
    return await service.handle_user_message(current_user, payload)

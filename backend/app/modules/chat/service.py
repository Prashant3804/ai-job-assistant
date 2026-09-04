import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.database.models.chat import ChatConversation, ChatMessage, ChatToolCall
from app.database.models.user import User
from app.modules.chat.orchestrator import ChatOrchestrator
from app.modules.chat.schemas import (
    CreateConversationRequest,
    ChatSendMessageRequest,
    ChatConversationRead,
    ChatConversationDetail,
    ChatMessageRead
)
from app.ai.services.ai_service import AIService

class ChatAssistantService:
    def __init__(self, db: AsyncSession, ai_service: Optional[AIService] = None):
        self.db = db
        self.ai = ai_service or AIService()
        self.orchestrator = ChatOrchestrator(db=db, ai_service=self.ai)

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        payload: Optional[CreateConversationRequest] = None
    ) -> ChatConversation:
        title = payload.title if payload and payload.title else "Job Assistant Copilot"
        context_type = payload.context_type if payload else "GENERAL"
        reference_id = payload.reference_id if payload else None

        conv = ChatConversation(
            user_id=user_id,
            title=title,
            context_type=context_type,
            reference_id=reference_id,
            metadata_json={}
        )
        self.db.add(conv)
        await self.db.flush()

        # Seed initial greeting message
        welcome = ChatMessage(
            conversation_id=conv.id,
            role="assistant",
            sender_type="ASSISTANT",
            content="Hello! I am your AI Job Assistant copilot. I can search jobs, analyze resume matches, calculate score breakdowns, and check missing skills. What would you like to explore?",
            structured_payload={
                "suggestions": [
                    "Find remote software developer jobs",
                    "Show my best matching jobs",
                    "What skills am I missing?",
                    "How many applications have I submitted?"
                ]
            }
        )
        self.db.add(welcome)
        await self.db.commit()
        await self.db.refresh(conv)
        return conv

    async def get_or_create_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: Optional[uuid.UUID] = None,
        context_type: str = "GENERAL",
        reference_id: Optional[uuid.UUID] = None
    ) -> ChatConversation:
        if conversation_id:
            stmt = select(ChatConversation).where(and_(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id))
            res = await self.db.execute(stmt)
            conv = res.scalar_one_or_none()
            if conv:
                return conv
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or unauthorized.")

        # Find recent conversation or create
        stmt = (
            select(ChatConversation)
            .where(ChatConversation.user_id == user_id)
            .order_by(ChatConversation.updated_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        conv = res.scalar_one_or_none()
        if conv:
            return conv

        return await self.create_conversation(
            user_id=user_id,
            payload=CreateConversationRequest(title="Job Assistant Copilot", context_type=context_type, reference_id=reference_id)
        )

    async def list_conversations(self, user_id: uuid.UUID) -> List[ChatConversationRead]:
        stmt = (
            select(ChatConversation)
            .where(ChatConversation.user_id == user_id)
            .order_by(ChatConversation.updated_at.desc())
        )
        res = await self.db.execute(stmt)
        convs = list(res.scalars().all())

        results = []
        for c in convs:
            # Count messages
            cnt_stmt = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == c.id)
            cnt_res = await self.db.execute(cnt_stmt)
            count = cnt_res.scalar() or 0
            results.append(ChatConversationRead(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                context_type=c.context_type,
                reference_id=c.reference_id,
                metadata_json=c.metadata_json or {},
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=count
            ))
        return results

    async def get_conversation_detail(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> ChatConversationDetail:
        stmt = (
            select(ChatConversation)
            .options(
                selectinload(ChatConversation.messages).selectinload(ChatMessage.tool_calls)
            )
            .where(and_(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id))
        )
        res = await self.db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or unauthorized.")

        return ChatConversationDetail.model_validate(conv, from_attributes=True)

    async def delete_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Dict[str, Any]:
        stmt = select(ChatConversation).where(and_(ChatConversation.id == conversation_id, ChatConversation.user_id == user_id))
        res = await self.db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or unauthorized.")

        await self.db.delete(conv)
        await self.db.commit()
        return {"status": "success", "message": "Conversation deleted"}

    async def get_conversation_messages(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> List[ChatMessageRead]:
        # Validate ownership
        await self.get_conversation_detail(user_id, conversation_id)

        stmt = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.tool_calls))
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc())
        )
        res = await self.db.execute(stmt)
        messages = list(res.scalars().all())
        return [ChatMessageRead.model_validate(m, from_attributes=True) for m in messages]

    async def handle_user_message(self, user: User, payload: ChatSendMessageRequest) -> ChatMessageRead:
        conv = await self.get_or_create_conversation(
            user_id=user.id,
            conversation_id=payload.conversation_id,
            context_type=payload.context_type,
            reference_id=payload.reference_id
        )
        assistant_msg = await self.orchestrator.process_message(
            user=user,
            conversation=conv,
            user_message_text=payload.message
        )
        await self.db.refresh(assistant_msg, ["tool_calls"])
        return ChatMessageRead.model_validate(assistant_msg, from_attributes=True)

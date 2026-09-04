import uuid
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, TimestampMixin
from app.shared.constants import ChatSenderType, ChatContextType

class ChatConversation(Base, TimestampMixin):
    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Job Assistant Chat", nullable=False)
    context_type: Mapped[str] = mapped_column(String(50), default=ChatContextType.GENERAL.value, nullable=False)
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    tool_calls: Mapped[List["ChatToolCall"]] = relationship("ChatToolCall", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatToolCall.created_at")

class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(50), default=ChatSenderType.USER.value, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    conversation: Mapped["ChatConversation"] = relationship("ChatConversation", back_populates="messages")
    tool_calls: Mapped[List["ChatToolCall"]] = relationship("ChatToolCall", back_populates="message", cascade="all, delete-orphan")

class ChatToolCall(Base, TimestampMixin):
    __tablename__ = "chat_tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    arguments: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    conversation: Mapped["ChatConversation"] = relationship("ChatConversation", back_populates="tool_calls")
    message: Mapped[Optional["ChatMessage"]] = relationship("ChatMessage", back_populates="tool_calls")

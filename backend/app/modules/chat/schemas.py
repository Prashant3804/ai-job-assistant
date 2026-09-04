import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="Job Search Copilot", max_length=255)
    context_type: str = Field(default="GENERAL")
    reference_id: Optional[uuid.UUID] = None

class ChatSendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User query or message")
    conversation_id: Optional[uuid.UUID] = None
    context_type: str = Field(default="GENERAL")
    reference_id: Optional[uuid.UUID] = None

class ChatToolCallRead(BaseModel):
    id: uuid.UUID
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None
    result_summary: Optional[str] = None
    status: str
    duration_ms: float
    created_at: datetime

    class Config:
        from_attributes = True

class ChatMessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    sender_type: str
    content: str
    structured_payload: Optional[Dict[str, Any]] = None
    token_count: Optional[int] = None
    created_at: datetime
    tool_calls: List[ChatToolCallRead] = []

    class Config:
        from_attributes = True

class ChatConversationRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    context_type: str
    reference_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True

class ChatConversationDetail(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    context_type: str
    reference_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageRead] = []

    class Config:
        from_attributes = True

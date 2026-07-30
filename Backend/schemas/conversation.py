from datetime import datetime
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    agent_id: str
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: list[dict] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    tokens_used: int = 0
    model: str = ""
    timestamp: datetime


class ConversationResponse(BaseModel):
    id: str
    user_id: str
    agent_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: str


class ConversationListResponse(BaseModel):
    id: str
    title: str
    agent: str
    agent_id: str
    updated_at: datetime
    last_message: str
    created_at: datetime


class ConversationListData(BaseModel):
    conversations: list[ConversationListResponse]
    total: int


class ConversationMessagesResponse(BaseModel):
    messages: list[MessageResponse]
    total: int

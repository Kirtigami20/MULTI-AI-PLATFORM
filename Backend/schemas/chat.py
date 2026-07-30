from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: str | None = None


class ChatToolCallResponse(BaseModel):
    id: str
    name: str
    arguments: dict


class ChatToolResultResponse(BaseModel):
    tool_call_id: str
    name: str
    result: str
    success: bool


class ChatResponse(BaseModel):
    id: str
    agent_id: str
    conversation_id: str = ""
    role: str
    content: str
    tool_calls: list[ChatToolCallResponse] = Field(default_factory=list)
    tool_results: list[ChatToolResultResponse] = Field(default_factory=list)
    tokens_used: int = 0
    model: str = ""
    created_at: datetime


class ChatMessageResponse(BaseModel):
    id: str
    agent_id: str
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int
    agent_id: str

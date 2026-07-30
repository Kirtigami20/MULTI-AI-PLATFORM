from datetime import datetime
from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="", max_length=1000)
    tool_type: str = Field(default="builtin", pattern="^(builtin|api)$")
    config: dict = Field(default_factory=dict)


class ToolUpdate(BaseModel):
    name: str = Field(default=None, min_length=2, max_length=200)
    description: str = Field(default=None, max_length=1000)
    config: dict = Field(default=None)


class ToolResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    tool_type: str
    config: dict
    created_at: datetime


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]
    total: int

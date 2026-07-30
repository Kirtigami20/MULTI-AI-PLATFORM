from datetime import datetime
from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    enabled: bool = True
    window_size: int = Field(default=10, ge=1, le=100)


class GuardrailsConfig(BaseModel):
    enabled: bool = True
    max_tokens: int = Field(default=2000, ge=100, le=10000)
    blocked_topics: list[str] = Field(default_factory=list)
    custom_rules: list[str] = Field(default_factory=list)


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="", max_length=1000)
    role: str = Field(..., min_length=2, max_length=200)
    goal: str = Field(..., min_length=2, max_length=1000)
    instructions: str = Field(..., min_length=2, max_length=5000)
    system_prompt: str = Field(default="", max_length=10000)
    knowledge_base_ids: list[str] = Field(default_factory=list)
    tool_ids: list[str] = Field(default_factory=list)
    engine: str = Field(default="langchain", pattern="^(langchain|langgraph|custom_llm)$")
    model_name: str = Field(
        default="qwen2.5:3b",
        pattern="^[a-zA-Z0-9._:-]+$",
    )
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    guardrails: GuardrailsConfig = Field(default_factory=GuardrailsConfig)


class AgentUpdate(BaseModel):
    name: str = Field(default=None, min_length=2, max_length=200)
    description: str = Field(default=None, max_length=1000)
    role: str = Field(default=None, min_length=2, max_length=200)
    goal: str = Field(default=None, min_length=2, max_length=1000)
    instructions: str = Field(default=None, min_length=2, max_length=5000)
    system_prompt: str = Field(default=None, max_length=10000)
    knowledge_base_ids: list[str] = Field(default=None)
    tool_ids: list[str] = Field(default=None)
    engine: str = Field(default=None, pattern="^(langchain|langgraph|custom_llm)$")
    model_name: str = Field(
        default=None,
        pattern="^[a-zA-Z0-9._:-]+$",
    )
    memory: MemoryConfig = Field(default=None)
    guardrails: GuardrailsConfig = Field(default=None)


class ResolvedKnowledgeBase(BaseModel):
    id: str
    name: str
    chunk_count: int


class ResolvedTool(BaseModel):
    id: str
    name: str
    tool_type: str


class AgentResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    role: str
    goal: str
    instructions: str
    system_prompt: str
    knowledge_bases: list[ResolvedKnowledgeBase]
    tools: list[ResolvedTool]
    engine: str
    model_name: str
    memory: MemoryConfig
    guardrails: GuardrailsConfig
    status: str
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    agents: list[AgentResponse]
    total: int

from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="", max_length=1000)
    file_ids: list[str] = Field(..., min_length=1)
    chunk_strategy: str = Field(default="recursive", pattern="^(recursive|fixed_size|sentence|markdown)$")
    chunk_size: int = Field(default=1000, ge=100, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=5000)
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        pattern="^(sentence-transformers/all-MiniLM-L6-v2)$",
    )


class KnowledgeBaseResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    file_ids: list[str]
    chunk_strategy: str
    chunk_size: int
    chunk_overlap: int
    embedding_model: str
    chunk_count: int
    status: str
    created_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    knowledge_bases: list[KnowledgeBaseResponse]
    total: int

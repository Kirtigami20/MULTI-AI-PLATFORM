from datetime import datetime, timezone
from bson import ObjectId


class KnowledgeBase:
    def __init__(
        self,
        user_id: str,
        name: str,
        description: str,
        file_ids: list[str],
        chunk_strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "text-embedding-3-small",
    ):
        self._id = ObjectId()
        self.user_id = user_id
        self.name = name
        self.description = description
        self.file_ids = file_ids
        self.chunk_strategy = chunk_strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.chunk_count = 0
        self.status = "processing"
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "file_ids": self.file_ids,
            "chunk_strategy": self.chunk_strategy,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "user_id": data["user_id"],
            "name": data["name"],
            "description": data["description"],
            "file_ids": data["file_ids"],
            "chunk_strategy": data.get("chunk_strategy", "recursive"),
            "chunk_size": data.get("chunk_size", 1000),
            "chunk_overlap": data.get("chunk_overlap", 200),
            "embedding_model": data.get("embedding_model", "text-embedding-3-small"),
            "chunk_count": data.get("chunk_count", 0),
            "status": data.get("status", "processing"),
            "created_at": data["created_at"],
        }

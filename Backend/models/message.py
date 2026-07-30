from datetime import datetime, timezone
from bson import ObjectId


class Message:
    def __init__(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] = None,
        tool_results: list[dict] = None,
        tokens_used: int = 0,
        model: str = "",
    ):
        self._id = ObjectId()
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.tool_calls = tool_calls or []
        self.tool_results = tool_results or []
        self.tokens_used = tokens_used
        self.model = model
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "conversation_id": data["conversation_id"],
            "role": data["role"],
            "content": data["content"],
            "tool_calls": data.get("tool_calls", []),
            "tool_results": data.get("tool_results", []),
            "tokens_used": data.get("tokens_used", 0),
            "model": data.get("model", ""),
            "timestamp": data["timestamp"],
        }

from datetime import datetime, timezone
from bson import ObjectId


class Conversation:
    def __init__(
        self,
        user_id: str,
        agent_id: str,
        title: str = "New Conversation",
    ):
        self._id = ObjectId()
        self.user_id = user_id
        self.agent_id = agent_id
        self.title = title
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.last_message = ""

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_message": self.last_message,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "user_id": data["user_id"],
            "agent_id": data["agent_id"],
            "title": data["title"],
            "created_at": data["created_at"],
            "updated_at": data.get("updated_at", data["created_at"]),
            "last_message": data.get("last_message", ""),
        }

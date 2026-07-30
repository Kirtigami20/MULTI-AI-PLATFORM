from datetime import datetime, timezone
from bson import ObjectId


class Tool:
    def __init__(
        self,
        user_id: str,
        name: str,
        description: str,
        tool_type: str = "builtin",
        config: dict = None,
    ):
        self._id = ObjectId()
        self.user_id = user_id
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.config = config or {}
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type,
            "config": self.config,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "user_id": data["user_id"],
            "name": data["name"],
            "description": data["description"],
            "tool_type": data.get("tool_type", "builtin"),
            "config": data.get("config", {}),
            "created_at": data["created_at"],
        }

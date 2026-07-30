from datetime import datetime, timezone
from bson import ObjectId


class User:
    def __init__(self, name: str, email: str, password: str):
        self._id = ObjectId()
        self.name = name
        self.email = email
        self.password = password
        self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "name": self.name,
            "email": self.email,
            "password": self.password,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "name": data["name"],
            "email": data["email"],
            "created_at": data["created_at"],
        }

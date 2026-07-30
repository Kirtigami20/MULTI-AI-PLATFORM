from bson import ObjectId
from database import get_collection
from models.conversation import Conversation


class ConversationRepository:

    @staticmethod
    async def create(conversation: Conversation) -> Conversation:
        collection = get_collection("conversations")
        await collection.insert_one(conversation.to_dict())
        return conversation

    @staticmethod
    async def find_by_id(conversation_id: str, user_id: str) -> dict | None:
        collection = get_collection("conversations")
        return await collection.find_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )

    @staticmethod
    async def find_by_user(user_id: str) -> list[dict]:
        collection = get_collection("conversations")
        cursor = (
            collection.find({"user_id": user_id})
            .sort("updated_at", -1)
        )
        return await cursor.to_list(length=None)

    @staticmethod
    async def update(
        conversation_id: str,
        update_data: dict,
    ) -> bool:
        collection = get_collection("conversations")
        result = await collection.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": update_data},
        )
        return result.modified_count > 0

    @staticmethod
    async def delete(conversation_id: str, user_id: str) -> bool:
        collection = get_collection("conversations")
        result = await collection.delete_one(
            {"_id": ObjectId(conversation_id), "user_id": user_id}
        )
        return result.deleted_count > 0

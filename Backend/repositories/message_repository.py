from bson import ObjectId
from database import get_collection
from models.message import Message


class MessageRepository:

    @staticmethod
    async def create(message: Message) -> Message:
        collection = get_collection("messages")
        await collection.insert_one(message.to_dict())
        return message

    @staticmethod
    async def find_by_conversation(conversation_id: str) -> list[dict]:
        collection = get_collection("messages")
        cursor = (
            collection.find({"conversation_id": conversation_id})
            .sort("timestamp", 1)
        )
        return await cursor.to_list(length=None)

    @staticmethod
    async def delete_by_conversation(conversation_id: str):
        collection = get_collection("messages")
        await collection.delete_many({"conversation_id": conversation_id})

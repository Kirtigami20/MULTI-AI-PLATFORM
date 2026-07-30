from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from models.conversation import Conversation
from models.message import Message
from schemas.conversation import (
    MessageResponse,
    ConversationResponse,
    ConversationListResponse,
    ConversationListData,
    ConversationMessagesResponse,
)
from repositories.conversation_repository import ConversationRepository
from repositories.message_repository import MessageRepository


class ConversationService:

    @staticmethod
    async def create_conversation(user_id: str, agent_id: str, title: str = "New Conversation") -> ConversationResponse:
        conversation = Conversation(user_id=user_id, agent_id=agent_id, title=title)
        created = await ConversationRepository.create(conversation)
        return ConversationResponse(**Conversation.from_dict(created.to_dict()))

    @staticmethod
    async def get_conversation(conversation_id: str, user_id: str) -> ConversationResponse:
        conversation = await ConversationRepository.find_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return ConversationResponse(**Conversation.from_dict(conversation))

    @staticmethod
    async def list_conversations(user_id: str) -> ConversationListData:
        conversations = await ConversationRepository.find_by_user(user_id)
        agents = get_collection("agents")
        agent_cache = {}

        items = []
        for conv in conversations:
            agent_id = conv.get("agent_id", "")
            if agent_id not in agent_cache:
                agent_doc = await agents.find_one({"_id": ObjectId(agent_id)})
                agent_cache[agent_id] = agent_doc["name"] if agent_doc else "Unknown"
            agent_name = agent_cache[agent_id]

            items.append(ConversationListResponse(
                id=str(conv["_id"]),
                title=conv.get("title", "New Conversation"),
                agent=agent_name,
                agent_id=agent_id,
                updated_at=conv.get("updated_at", conv["created_at"]),
                last_message=conv.get("last_message", ""),
                created_at=conv["created_at"],
            ))

        return ConversationListData(conversations=items, total=len(items))

    @staticmethod
    async def update_conversation(conversation_id: str, user_id: str, title: str) -> ConversationResponse:
        conversation = await ConversationRepository.find_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        await ConversationRepository.update(conversation_id, {
            "title": title,
            "updated_at": datetime.now(timezone.utc),
        })
        conversation["title"] = title
        conversation["updated_at"] = datetime.now(timezone.utc)
        return ConversationResponse(**Conversation.from_dict(conversation))

    @staticmethod
    async def delete_conversation(conversation_id: str, user_id: str):
        conversation = await ConversationRepository.find_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        await MessageRepository.delete_by_conversation(conversation_id)
        await ConversationRepository.delete(conversation_id, user_id)

    @staticmethod
    async def get_conversation_messages(conversation_id: str, user_id: str) -> ConversationMessagesResponse:
        conversation = await ConversationRepository.find_by_id(conversation_id, user_id)
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        messages = await MessageRepository.find_by_conversation(conversation_id)
        msg_responses = [
            MessageResponse(**Message.from_dict(m))
            for m in messages
        ]
        return ConversationMessagesResponse(messages=msg_responses, total=len(msg_responses))

    @staticmethod
    async def save_message(
        conversation_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] = None,
        tool_results: list[dict] = None,
        tokens_used: int = 0,
        model: str = "",
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            model=model,
        )
        return await MessageRepository.create(message)

    @staticmethod
    async def update_conversation_metadata(
        conversation_id: str,
        last_message: str,
    ):
        await ConversationRepository.update(conversation_id, {
            "last_message": last_message[:200],
            "updated_at": datetime.now(timezone.utc),
        })

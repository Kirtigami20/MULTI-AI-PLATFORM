from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from models.chat import ChatMessage
from schemas.chat import (
    ChatResponse,
    ChatToolCallResponse,
    ChatToolResultResponse,
    ChatMessageResponse,
    ChatHistoryResponse,
)
from rag.retriever import Retriever


class ChatService:

    @staticmethod
    async def save_message(
        agent_id: str,
        user_id: str,
        role: str,
        content: str,
        tool_calls: list[dict] = None,
        tool_results: list[dict] = None,
        tokens_used: int = 0,
        model: str = "",
    ) -> ChatMessage:
        messages = get_collection("chat_messages")
        msg = ChatMessage(
            agent_id=agent_id,
            user_id=user_id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=tokens_used,
            model=model,
        )
        await messages.insert_one(msg.to_dict())
        return msg

    @staticmethod
    async def get_history(
        agent_id: str,
        user_id: str,
        limit: int = 50,
    ) -> ChatHistoryResponse:
        messages = get_collection("chat_messages")
        cursor = (
            messages.find({"agent_id": agent_id, "user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        results = await cursor.to_list(length=limit)
        results.reverse()

        chat_msgs = [
            ChatMessageResponse(
                id=str(m["_id"]),
                agent_id=m["agent_id"],
                role=m["role"],
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in results
        ]

        return ChatHistoryResponse(
            messages=chat_msgs,
            total=len(chat_msgs),
            agent_id=agent_id,
        )

    @staticmethod
    async def get_messages_as_engine_messages(
        agent_id: str,
        user_id: str,
        limit: int = 50,
    ) -> list:
        from engines.base import EngineMessage

        messages = get_collection("chat_messages")
        cursor = (
            messages.find({"agent_id": agent_id, "user_id": user_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        results = await cursor.to_list(length=limit)
        results.reverse()

        return [
            EngineMessage(role=m["role"], content=m["content"])
            for m in results
        ]

    @staticmethod
    def retrieve_rag_context(agent_config: dict, query: str, n_results: int = 5) -> str:
        kb_ids = agent_config.get("knowledge_base_ids", [])
        if not kb_ids:
            return ""

        all_chunks = []
        for kb_id in kb_ids:
            try:
                chunks = Retriever.search(
                    collection_name=kb_id,
                    query=query,
                    n_results=n_results,
                )
                all_chunks.extend(chunks)
            except Exception:
                continue

        all_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
        return all_chunks[:n_results]

    @staticmethod
    async def build_chat_response(msg, agent_id: str = "") -> ChatResponse:
        tool_calls = [
            ChatToolCallResponse(
                id=tc.get("id", ""),
                name=tc.get("name", ""),
                arguments=tc.get("arguments", {}),
            )
            for tc in msg.tool_calls
        ]

        tool_results = [
            ChatToolResultResponse(
                tool_call_id=tr.get("tool_call_id", ""),
                name=tr.get("name", ""),
                result=tr.get("result", ""),
                success=tr.get("success", True),
            )
            for tr in msg.tool_results
        ]

        return ChatResponse(
            id=str(msg._id),
            agent_id=getattr(msg, "agent_id", agent_id),
            role=msg.role,
            content=msg.content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            tokens_used=msg.tokens_used,
            model=msg.model,
            created_at=getattr(msg, "created_at", getattr(msg, "timestamp", None)),
        )

    @staticmethod
    async def clear_history(agent_id: str, user_id: str):
        messages = get_collection("chat_messages")
        await messages.delete_many({"agent_id": agent_id, "user_id": user_id})

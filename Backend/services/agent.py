from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from models.agent import Agent
from schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    ResolvedKnowledgeBase,
    ResolvedTool,
)


class AgentService:

    @staticmethod
    async def create(data: AgentCreate, user_id: str) -> AgentResponse:
        agents = get_collection("agents")

        existing = await agents.find_one({"user_id": user_id, "name": data.name})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent with this name already exists",
            )

        agent = Agent(
            user_id=user_id,
            name=data.name,
            description=data.description,
            role=data.role,
            goal=data.goal,
            instructions=data.instructions,
            system_prompt=data.system_prompt,
            knowledge_base_ids=data.knowledge_base_ids,
            tool_ids=data.tool_ids,
            engine=data.engine,
            model_name=data.model_name,
            memory=data.memory.model_dump(),
            guardrails=data.guardrails.model_dump(),
        )

        await agents.insert_one(agent.to_dict())

        return await AgentService._build_response(agent.to_dict())

    @staticmethod
    async def list_by_user(user_id: str) -> list[AgentResponse]:
        agents = get_collection("agents")
        cursor = agents.find({"user_id": user_id}).sort("created_at", -1)
        results = await cursor.to_list(length=100)
        return [await AgentService._build_response(a) for a in results]

    @staticmethod
    async def get_by_id(agent_id: str, user_id: str) -> AgentResponse:
        agents = get_collection("agents")
        agent = await agents.find_one({"_id": ObjectId(agent_id), "user_id": user_id})

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        return await AgentService._build_response(agent)

    @staticmethod
    async def update(agent_id: str, data: AgentUpdate, user_id: str) -> AgentResponse:
        agents = get_collection("agents")
        agent = await agents.find_one({"_id": ObjectId(agent_id), "user_id": user_id})

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}

        if "memory" in update_data and update_data["memory"] is not None:
            update_data["memory"] = update_data["memory"]

        if "guardrails" in update_data and update_data["guardrails"] is not None:
            update_data["guardrails"] = update_data["guardrails"]

        if update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            await agents.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": update_data},
            )

        updated_agent = await agents.find_one({"_id": ObjectId(agent_id)})
        return await AgentService._build_response(updated_agent)

    @staticmethod
    async def delete(agent_id: str, user_id: str):
        agents = get_collection("agents")
        agent = await agents.find_one({"_id": ObjectId(agent_id), "user_id": user_id})

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found",
            )

        await agents.delete_one({"_id": ObjectId(agent_id)})

    @staticmethod
    async def _build_response(agent_data: dict) -> AgentResponse:
        kbs = get_collection("knowledge_bases")
        tools = get_collection("tools")

        resolved_kbs = []
        for kb_id in agent_data.get("knowledge_base_ids", []):
            try:
                kb = await kbs.find_one({"_id": ObjectId(kb_id)})
                if kb:
                    resolved_kbs.append(ResolvedKnowledgeBase(
                        id=str(kb["_id"]),
                        name=kb["name"],
                        chunk_count=kb.get("chunk_count", 0),
                    ))
            except Exception:
                pass

        resolved_tools = []
        for tool_id in agent_data.get("tool_ids", []):
            try:
                tool = await tools.find_one({"_id": ObjectId(tool_id)})
                if tool:
                    resolved_tools.append(ResolvedTool(
                        id=str(tool["_id"]),
                        name=tool["name"],
                        tool_type=tool.get("tool_type", "builtin"),
                    ))
            except Exception:
                pass

        memory = agent_data.get("memory", {"enabled": True, "window_size": 10})
        guardrails = agent_data.get("guardrails", {
            "enabled": True, "max_tokens": 2000, "blocked_topics": [], "custom_rules": [],
        })

        return AgentResponse(
            id=str(agent_data["_id"]),
            user_id=agent_data["user_id"],
            name=agent_data["name"],
            description=agent_data["description"],
            role=agent_data["role"],
            goal=agent_data["goal"],
            instructions=agent_data["instructions"],
            system_prompt=agent_data.get("system_prompt", ""),
            knowledge_bases=resolved_kbs,
            tools=resolved_tools,
            engine=agent_data.get("engine", "langchain"),
            model_name=agent_data.get("model_name", "llama-3.3-70b-versatile"),
            memory=memory,
            guardrails=guardrails,
            status=agent_data.get("status", "active"),
            created_at=agent_data["created_at"],
            updated_at=agent_data.get("updated_at", agent_data["created_at"]),
        )

from datetime import datetime, timezone
from bson import ObjectId


class Agent:
    def __init__(
        self,
        user_id: str,
        name: str,
        description: str,
        role: str,
        goal: str,
        instructions: str,
        system_prompt: str = "",
        knowledge_base_ids: list[str] = None,
        tool_ids: list[str] = None,
        engine: str = "langchain",
        model_name: str = "llama-3.3-70b-versatile",
        memory: dict = None,
        guardrails: dict = None,
    ):
        self._id = ObjectId()
        self.user_id = user_id
        self.name = name
        self.description = description
        self.role = role
        self.goal = goal
        self.instructions = instructions
        self.system_prompt = system_prompt
        self.knowledge_base_ids = knowledge_base_ids or []
        self.tool_ids = tool_ids or []
        self.engine = engine
        self.model_name = model_name
        self.memory = memory or {"enabled": True, "window_size": 10}
        self.guardrails = guardrails or {
            "enabled": True,
            "max_tokens": 2000,
            "blocked_topics": [],
            "custom_rules": [],
        }
        self.status = "active"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "goal": self.goal,
            "instructions": self.instructions,
            "system_prompt": self.system_prompt,
            "knowledge_base_ids": self.knowledge_base_ids,
            "tool_ids": self.tool_ids,
            "engine": self.engine,
            "model_name": self.model_name,
            "memory": self.memory,
            "guardrails": self.guardrails,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> dict:
        return {
            "id": str(data["_id"]),
            "user_id": data["user_id"],
            "name": data["name"],
            "description": data["description"],
            "role": data["role"],
            "goal": data["goal"],
            "instructions": data["instructions"],
            "system_prompt": data.get("system_prompt", ""),
            "knowledge_base_ids": data.get("knowledge_base_ids", []),
            "tool_ids": data.get("tool_ids", []),
            "engine": data.get("engine", "langchain"),
            "model_name": data.get("model_name", "llama-3.3-70b-versatile"),
            "memory": data.get("memory", {"enabled": True, "window_size": 10}),
            "guardrails": data.get("guardrails", {
                "enabled": True,
                "max_tokens": 2000,
                "blocked_topics": [],
                "custom_rules": [],
            }),
            "status": data.get("status", "active"),
            "created_at": data["created_at"],
            "updated_at": data.get("updated_at", data["created_at"]),
        }

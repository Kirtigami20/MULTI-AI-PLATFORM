from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from models.tool import Tool
from schemas.tool import ToolCreate, ToolUpdate, ToolResponse
from utils.builtin_tools import is_builtin_tool, list_builtin_tool_names


class ToolService:

    @staticmethod
    async def create(data: ToolCreate, user_id: str) -> ToolResponse:
        tools = get_collection("tools")

        existing = await tools.find_one({"user_id": user_id, "name": data.name})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tool with this name already exists",
            )

        if data.tool_type == "builtin":
            if not is_builtin_tool(data.name):
                available = ", ".join(list_builtin_tool_names())
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown built-in tool: '{data.name}'. Available: {available}",
                )

        tool = Tool(
            user_id=user_id,
            name=data.name,
            description=data.description,
            tool_type=data.tool_type,
            config=data.config,
        )

        await tools.insert_one(tool.to_dict())

        return Tool.from_dict(tool.to_dict())

    @staticmethod
    async def list_by_user(user_id: str) -> list[ToolResponse]:
        tools = get_collection("tools")
        cursor = tools.find({"user_id": user_id}).sort("created_at", -1)
        results = await cursor.to_list(length=100)
        return [Tool.from_dict(t) for t in results]

    @staticmethod
    async def get_by_id(tool_id: str, user_id: str) -> ToolResponse:
        tools = get_collection("tools")
        tool = await tools.find_one({"_id": ObjectId(tool_id), "user_id": user_id})

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )

        return Tool.from_dict(tool)

    @staticmethod
    async def update(tool_id: str, data: ToolUpdate, user_id: str) -> ToolResponse:
        tools = get_collection("tools")
        tool = await tools.find_one({"_id": ObjectId(tool_id), "user_id": user_id})

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )

        update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}

        if update_data:
            await tools.update_one(
                {"_id": ObjectId(tool_id)},
                {"$set": update_data},
            )

        updated_tool = await tools.find_one({"_id": ObjectId(tool_id)})
        return Tool.from_dict(updated_tool)

    @staticmethod
    async def delete(tool_id: str, user_id: str):
        tools = get_collection("tools")
        tool = await tools.find_one({"_id": ObjectId(tool_id), "user_id": user_id})

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tool not found",
            )

        await tools.delete_one({"_id": ObjectId(tool_id)})

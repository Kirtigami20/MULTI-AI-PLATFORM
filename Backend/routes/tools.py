from fastapi import APIRouter, Depends
from schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
)
from services.tool import ToolService
from utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/tools", tags=["Tools"])


@router.post("", response_model=ToolResponse, status_code=201)
async def create_tool(
    data: ToolCreate,
    current_user: dict = Depends(get_current_user),
):
    return await ToolService.create(data, str(current_user["_id"]))


@router.get("", response_model=ToolListResponse)
async def list_tools(
    current_user: dict = Depends(get_current_user),
):
    tools = await ToolService.list_by_user(str(current_user["_id"]))
    return ToolListResponse(tools=tools, total=len(tools))


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str,
    current_user: dict = Depends(get_current_user),
):
    return await ToolService.get_by_id(tool_id, str(current_user["_id"]))


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: str,
    data: ToolUpdate,
    current_user: dict = Depends(get_current_user),
):
    return await ToolService.update(tool_id, data, str(current_user["_id"]))


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: str,
    current_user: dict = Depends(get_current_user),
):
    await ToolService.delete(tool_id, str(current_user["_id"]))

from fastapi import APIRouter, Depends
from schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentListResponse,
)
from services.agent import AgentService
from utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Builder"])


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    data: AgentCreate,
    current_user: dict = Depends(get_current_user),
):
    return await AgentService.create(data, str(current_user["_id"]))


@router.get("", response_model=AgentListResponse)
async def list_agents(
    current_user: dict = Depends(get_current_user),
):
    agents = await AgentService.list_by_user(str(current_user["_id"]))
    return AgentListResponse(agents=agents, total=len(agents))


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
):
    return await AgentService.get_by_id(agent_id, str(current_user["_id"]))


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    current_user: dict = Depends(get_current_user),
):
    return await AgentService.update(agent_id, data, str(current_user["_id"]))


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
):
    await AgentService.delete(agent_id, str(current_user["_id"]))

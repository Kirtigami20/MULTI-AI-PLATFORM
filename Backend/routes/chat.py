from fastapi import APIRouter, Depends
from schemas.chat import ChatRequest, ChatResponse, ChatHistoryResponse
from runtime.executor import RuntimeExecutor
from services.chat import ChatService
from utils.dependencies import get_current_user
from utils.logger import set_request_id, PipelineLogger

router = APIRouter(prefix="/api/v1/agents/{agent_id}/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def send_message(
    agent_id: str,
    data: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    request_id = set_request_id()
    user_id = str(current_user["_id"])
    PipelineLogger.log_stage_1_request(
        agent_id=agent_id,
        user_id=user_id,
        message=data.message,
        request_id=request_id,
    )
    return await RuntimeExecutor.execute_chat(
        agent_id=agent_id,
        user_id=user_id,
        user_message=data.message,
        conversation_id=data.conversation_id,
    )


@router.get("", response_model=ChatHistoryResponse)
async def get_history(
    agent_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    return await ChatService.get_history(
        agent_id=agent_id,
        user_id=str(current_user["_id"]),
        limit=limit,
    )


@router.delete("", status_code=204)
async def clear_history(
    agent_id: str,
    current_user: dict = Depends(get_current_user),
):
    await ChatService.clear_history(
        agent_id=agent_id,
        user_id=str(current_user["_id"]),
    )

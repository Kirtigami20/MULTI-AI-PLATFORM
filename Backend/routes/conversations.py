from fastapi import APIRouter, Depends, status
from schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListData,
    ConversationMessagesResponse,
)
from services.conversation_service import ConversationService
from utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
):
    return await ConversationService.create_conversation(
        user_id=str(current_user["_id"]),
        agent_id=data.agent_id,
        title=data.title,
    )


@router.get("", response_model=ConversationListData)
async def list_conversations(
    current_user: dict = Depends(get_current_user),
):
    return await ConversationService.list_conversations(
        user_id=str(current_user["_id"]),
    )


@router.get("/{conversation_id}", response_model=ConversationMessagesResponse)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    return await ConversationService.get_conversation_messages(
        conversation_id=conversation_id,
        user_id=str(current_user["_id"]),
    )


@router.get("/{conversation_id}/meta", response_model=ConversationResponse)
async def get_conversation_meta(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    return await ConversationService.get_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user["_id"]),
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    await ConversationService.delete_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user["_id"]),
    )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    data: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
):
    return await ConversationService.update_conversation(
        conversation_id=conversation_id,
        user_id=str(current_user["_id"]),
        title=data.title,
    )

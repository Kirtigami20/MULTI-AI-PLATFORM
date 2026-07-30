from fastapi import APIRouter, Depends
from schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseListResponse,
)
from services.knowledge import KnowledgeService
from utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Builder"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService.create(data, str(current_user["_id"]))


@router.get("", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    current_user: dict = Depends(get_current_user),
):
    kbs = await KnowledgeService.list_by_user(str(current_user["_id"]))
    return KnowledgeBaseListResponse(knowledge_bases=kbs, total=len(kbs))


@router.get("/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService.get_by_id(kb_id, str(current_user["_id"]))


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
):
    await KnowledgeService.delete(kb_id, str(current_user["_id"]))


@router.get("/{kb_id}/chunks")
async def get_chunks(
    kb_id: str,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService.get_chunks(kb_id, str(current_user["_id"]), limit, offset)

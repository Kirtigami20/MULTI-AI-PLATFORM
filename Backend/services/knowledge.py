import os
from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from models.knowledge import KnowledgeBase
from schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseResponse
from rag.pipeline import RAGPipeline
from rag.vectordb import VectorDB
from services.upload import UploadService
from config import settings


class KnowledgeService:

    @staticmethod
    async def create(data: KnowledgeBaseCreate, user_id: str) -> KnowledgeBaseResponse:
        kb = KnowledgeBase(
            user_id=user_id,
            name=data.name,
            description=data.description,
            file_ids=data.file_ids,
            chunk_strategy=data.chunk_strategy,
            chunk_size=data.chunk_size,
            chunk_overlap=data.chunk_overlap,
            embedding_model=data.embedding_model,
        )

        kbs = get_collection("knowledge_bases")
        await kbs.insert_one(kb.to_dict())

        file_paths = []
        for file_id in data.file_ids:
            user_dir = os.path.join(settings.UPLOAD_DIR, user_id)
            if os.path.exists(user_dir):
                matching = [f for f in os.listdir(user_dir) if f.startswith(file_id)]
                if matching:
                    file_paths.append(os.path.join(user_dir, matching[0]))

        try:
            chunk_count = await RAGPipeline.process(
                kb_id=str(kb._id),
                file_paths=file_paths,
                chunk_strategy=data.chunk_strategy,
                chunk_size=data.chunk_size,
                chunk_overlap=data.chunk_overlap,
                embedding_model=data.embedding_model,
            )

            kb.chunk_count = chunk_count
            kb.status = "ready"
        except Exception as e:
            kb.status = "failed"
            print(f"Pipeline failed: {e}")

        await kbs.update_one(
            {"_id": kb._id},
            {"$set": {"chunk_count": kb.chunk_count, "status": kb.status}},
        )

        return KnowledgeBase.from_dict(kb.to_dict())

    @staticmethod
    async def list_by_user(user_id: str) -> list[KnowledgeBaseResponse]:
        kbs = get_collection("knowledge_bases")
        cursor = kbs.find({"user_id": user_id}).sort("created_at", -1)
        results = await cursor.to_list(length=100)
        return [KnowledgeBase.from_dict(kb) for kb in results]

    @staticmethod
    async def get_by_id(kb_id: str, user_id: str) -> KnowledgeBaseResponse:
        kbs = get_collection("knowledge_bases")
        kb = await kbs.find_one({"_id": ObjectId(kb_id), "user_id": user_id})

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        return KnowledgeBase.from_dict(kb)

    @staticmethod
    async def delete(kb_id: str, user_id: str):
        kbs = get_collection("knowledge_bases")
        kb = await kbs.find_one({"_id": ObjectId(kb_id), "user_id": user_id})

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        VectorDB.delete_collection(kb_id)

        for file_id in kb.get("file_ids", []):
            user_dir = os.path.join(settings.UPLOAD_DIR, user_id)
            if os.path.exists(user_dir):
                matching = [f for f in os.listdir(user_dir) if f.startswith(file_id)]
                for f in matching:
                    UploadService.delete_file(f, user_id)

        await kbs.delete_one({"_id": ObjectId(kb_id)})

    @staticmethod
    async def get_chunks(kb_id: str, user_id: str, limit: int = 100, offset: int = 0) -> dict:
        kbs = get_collection("knowledge_bases")
        kb = await kbs.find_one({"_id": ObjectId(kb_id), "user_id": user_id})

        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        results = VectorDB.get_all_documents(kb_id, limit, offset)

        chunks = []
        for doc_id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"]):
            chunks.append({
                "id": doc_id,
                "text": doc,
                "metadata": meta,
            })

        return {
            "kb_id": kb_id,
            "total": results["total"],
            "chunks": chunks,
        }

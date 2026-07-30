import uuid
from rag.loader import DocumentLoader
from rag.chunker import TextChunker
from rag.embedding import EmbeddingService
from rag.vectordb import VectorDB


class RAGPipeline:

    @staticmethod
    async def process(
        kb_id: str,
        file_paths: list[str],
        chunk_strategy: str = "recursive",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embedding_model: str = "text-embedding-3-small",
    ) -> int:
        all_documents = []

        for file_path in file_paths:
            documents = DocumentLoader.load(file_path)
            all_documents.extend(documents)

        if not all_documents:
            return 0

        chunks = TextChunker.chunk(
            documents=all_documents,
            strategy=chunk_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        if not chunks:
            return 0

        embeddings = EmbeddingService.get_embeddings(embedding_model)
        texts = [chunk["chunk_text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [str(uuid.uuid4()) for _ in chunks]

        VectorDB.add_documents(
            collection_name=kb_id,
            texts=texts,
            metadatas=metadatas,
            ids=ids,
        )

        return len(chunks)

from rag.vectordb import VectorDB


class Retriever:

    @staticmethod
    def search(
        collection_name: str,
        query: str,
        n_results: int = 5,
    ) -> list[dict]:
        results = VectorDB.query(
            collection_name=collection_name,
            query_texts=[query],
            n_results=n_results,
        )

        if not results or not results.get("documents"):
            return []

        chunks = []
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            chunks.append({
                "chunk_text": doc,
                "metadata": meta,
                "score": 1 - dist,
            })

        return chunks

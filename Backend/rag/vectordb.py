import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorDB:

    _client = None

    @staticmethod
    def get_client() -> chromadb.ClientAPI:
        if VectorDB._client is None:
            VectorDB._client = chromadb.PersistentClient(
                path="./chroma_db",
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return VectorDB._client

    @staticmethod
    def create_collection(name: str) -> chromadb.Collection:
        client = VectorDB.get_client()
        return client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def get_collection(name: str) -> chromadb.Collection:
        client = VectorDB.get_client()
        try:
            return client.get_collection(name=name)
        except Exception:
            return None

    @staticmethod
    def add_documents(
        collection_name: str,
        texts: list[str],
        metadatas: list[dict],
        ids: list[str],
    ):
        collection = VectorDB.create_collection(collection_name)
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )

    @staticmethod
    def delete_collection(name: str):
        client = VectorDB.get_client()
        try:
            client.delete_collection(name=name)
        except Exception:
            pass

    @staticmethod
    def get_all_documents(
        collection_name: str,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        collection = VectorDB.get_collection(collection_name)
        if collection is None:
            return {"ids": [], "documents": [], "metadatas": [], "total": 0}

        total = collection.count()

        results = collection.get(
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )

        return {
            "ids": results["ids"],
            "documents": results["documents"],
            "metadatas": results["metadatas"],
            "total": total,
        }

    @staticmethod
    def query(
        collection_name: str,
        query_texts: list[str],
        n_results: int = 5,
    ) -> dict:
        collection = VectorDB.get_collection(collection_name)
        if collection is None:
            return {"documents": [], "metadatas": [], "distances": []}

        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
        )

        return results

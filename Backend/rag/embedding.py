from langchain_community.embeddings import HuggingFaceEmbeddings
from config import settings


class EmbeddingService:

    @staticmethod
    def get_embeddings(model: str = None) -> object:
        model = model or settings.EMBEDDING_MODEL

        if model.startswith("sentence-transformers"):
            return HuggingFaceEmbeddings(model_name=model)
        else:
            raise ValueError(
                f"Unknown embedding model: {model}. "
                "Only sentence-transformers models are supported."
            )

    @staticmethod
    def get_model_info(model: str = None) -> dict:
        model = model or settings.EMBEDDING_MODEL

        models = {
            "sentence-transformers/all-MiniLM-L6-v2": {
                "provider": "local",
                "dimension": 384,
                "cost": "free",
            },
        }

        return models.get(model, {"provider": "unknown", "dimension": 0, "cost": "unknown"})

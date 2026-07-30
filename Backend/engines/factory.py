from engines.base import BaseEngine
from engines.langchain_engine import LangChainEngine
from engines.langgraph_engine import LangGraphEngine
from engines.custom_llm_engine import CustomLLMEngine


ENGINES = {
    "langchain": LangChainEngine,
    "langgraph": LangGraphEngine,
    "custom_llm": CustomLLMEngine,
}


def get_engine(engine_type: str) -> BaseEngine:
    engine_cls = ENGINES.get(engine_type)
    if not engine_cls:
        raise ValueError(
            f"Unknown engine type: '{engine_type}'. "
            f"Available: {', '.join(ENGINES.keys())}"
        )
    return engine_cls()

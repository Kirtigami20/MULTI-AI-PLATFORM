from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class EngineMessage:
    role: str
    content: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    result: str
    success: bool = True


@dataclass
class EngineResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    tokens_used: int = 0
    model: str = ""


class BaseEngine(ABC):

    @abstractmethod
    async def chat(
        self,
        agent_config: dict,
        messages: list[EngineMessage],
        rag_context: str = "",
        available_tools: list[dict] = None,
    ) -> EngineResponse:
        pass

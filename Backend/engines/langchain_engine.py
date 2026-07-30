from typing import Optional
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool as lc_tool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field, create_model
from config import settings
from engines.base import BaseEngine, EngineMessage, EngineResponse, ToolCall, ToolResult
from prompts.system import build_system_prompt
from utils.constants import DEFAULT_MODEL, MAX_TOOL_ITERATIONS
from utils.builtin_tools import get_builtin_tool, is_builtin_tool
from utils.tool_executor import ToolExecutor
from utils.logger import PipelineLogger, StageTimer


class LangChainEngine(BaseEngine):

    async def chat(
        self,
        agent_config: dict,
        messages: list[EngineMessage],
        rag_context: str = "",
        available_tools: list[dict] = None,
    ) -> EngineResponse:
        model_name = agent_config.get("model_name", DEFAULT_MODEL)
        guardrails = agent_config.get("guardrails", {})

        llm = ChatGroq(
            model=model_name,
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.7,
        )

        system_text = build_system_prompt(
            role=agent_config.get("role", "Assistant"),
            goal=agent_config.get("goal", ""),
            instructions=agent_config.get("instructions", ""),
            custom_prompt=agent_config.get("system_prompt", ""),
        )

        formatted_rag = self._format_rag(rag_context)
        if formatted_rag:
            system_text += (
                "\n\n## Knowledge Base Context\n"
                "Use the following context to answer the user's question when relevant.\n\n"
                f"{formatted_rag}"
            )

        lc_tools = self._build_tools(available_tools or [])

        graph = create_react_agent(
            model=llm,
            tools=lc_tools if lc_tools else [],
        )

        history_messages = self._build_history(messages)
        history_messages.insert(0, SystemMessage(content=system_text))

        PipelineLogger.log_stage_5_llm_request(
            engine_name="langchain",
            model_name=model_name,
            iteration=1,
            payload_summary={
                "messages_count": len(history_messages),
                "tools_count": len(lc_tools),
                "tool_names": [t.get("name") for t in (available_tools or [])],
            },
        )

        try:
            with StageTimer() as timer:
                result = await graph.ainvoke(
                    {"messages": history_messages},
                    config={"recursion_limit": MAX_TOOL_ITERATIONS * 2},
                )
        except Exception as e:
            PipelineLogger.log_pipeline_error("LANGCHAIN_ENGINE_AINVOKE", e)
            return EngineResponse(
                content=f"Engine error: {str(e)}",
                model=model_name,
            )

        all_msgs = result.get("messages", [])
        output = ""
        parsed_tool_calls = []
        parsed_tool_results = []

        for msg in all_msgs:
            if isinstance(msg, AIMessage) and msg.content:
                output = msg.content
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        parsed_tool_calls.append(ToolCall(
                            id=tc.get("id", ""),
                            name=tc.get("name", ""),
                            arguments=tc.get("args", {}),
                        ))

            if hasattr(msg, "name") and hasattr(msg, "content"):
                if msg.__class__.__name__ == "ToolMessage":
                    parsed_tool_results.append(ToolResult(
                        tool_call_id=getattr(msg, "tool_call_id", ""),
                        name=getattr(msg, "name", ""),
                        result=str(msg.content),
                        success=True,
                    ))

        if not output and all_msgs:
            last = all_msgs[-1]
            if hasattr(last, "content"):
                output = str(last.content)

        PipelineLogger.log_stage_6_llm_response(
            engine_name="langchain",
            duration_ms=timer.duration_ms,
            tokens_used=0,
            tool_calls_count=len(parsed_tool_calls),
            content_preview=output or "(tool output)",
        )

        if guardrails.get("enabled", False):
            output = self._apply_guardrails(output, guardrails)

        return EngineResponse(
            content=output,
            tool_calls=parsed_tool_calls,
            tool_results=parsed_tool_results,
            model=model_name,
        )

    @staticmethod
    def _build_api_tool_schema(parameters: list[dict]) -> type[BaseModel]:
        fields = {}
        for p in parameters:
            ptype = {
                "string": str,
                "number": float,
                "integer": int,
                "boolean": bool,
                "list": list,
                "dict": dict,
            }.get(p.get("type", "string"), str)

            if p.get("required", False):
                fields[p["name"]] = (ptype, Field(description=p.get("description", "")))
            else:
                fields[p["name"]] = (
                    Optional[ptype],
                    Field(default=None, description=p.get("description", "")),
                )

        return create_model("APIToolInput", **fields)

    def _build_tools(self, tools: list[dict]) -> list:
        lc_tools = []

        for t in tools:
            tool_type = t.get("tool_type", "builtin")
            name = t.get("name", "")
            description = t.get("description", "")

            if tool_type == "builtin" and is_builtin_tool(name):
                lc_tools.append(self._build_builtin_tool(name, description))

            elif tool_type == "api":
                lc_tools.append(self._build_api_tool(t))

        return lc_tools

    @staticmethod
    def _build_builtin_tool(name: str, description_override: str = "") -> lc_tool:
        registry = get_builtin_tool(name)
        if not registry:
            raise ValueError(f"Built-in tool '{name}' not found in registry")

        desc = description_override or registry["description"]
        handler = registry["handler"]
        is_async = registry.get("async", False)
        params = registry["parameters"]

        if is_async:
            if not params:
                @lc_tool(name, description=desc)
                async def _tool() -> str:
                    return await handler()
                return _tool

            param_str = ", ".join(f"{p['name']}: str" for p in params)
            @lc_tool(name, description=desc)
            async def _tool(**kwargs) -> str:
                return await handler(**kwargs)
            _tool.__name__ = name
            return _tool
        else:
            if not params:
                @lc_tool(name, description=desc)
                def _tool() -> str:
                    return handler()
                return _tool

            @lc_tool(name, description=desc)
            def _tool(**kwargs) -> str:
                return handler(**kwargs)
            _tool.__name__ = name
            return _tool

    def _build_api_tool(self, t: dict):
        tool_def = t
        name = t.get("name", "")
        description = t.get("description", "")
        params = t.get("config", {}).get("parameters", [])

        if params:
            args_schema = self._build_api_tool_schema(params)

            @lc_tool(name, description=description or f"API tool: {name}", args_schema=args_schema)
            async def api_tool(**kwargs) -> str:
                return await ToolExecutor.execute(name, kwargs, [tool_def])
        else:
            @lc_tool(name, description=description or f"API tool: {name}")
            async def api_tool(input: str) -> str:
                return await ToolExecutor.execute(name, {"input": input}, [tool_def])

        return api_tool

    def _build_history(self, messages: list[EngineMessage]) -> list:
        history = []
        for msg in messages:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                history.append(SystemMessage(content=msg.content))
        return history

    @staticmethod
    def _format_rag(rag_context) -> str:
        if not rag_context:
            return ""
        if isinstance(rag_context, list) and rag_context:
            parts = ["Relevant context from knowledge base:", ""]
            for i, chunk in enumerate(rag_context, 1):
                score = chunk.get("score", 0)
                source = chunk.get("metadata", {}).get("source", "unknown")
                text = chunk.get("chunk_text", "")
                parts.append(f"[{i}] (source: {source}, relevance: {score:.2f})")
                parts.append(text)
                parts.append("")
            return "\n".join(parts)
        return ""

    def _apply_guardrails(self, output: str, guardrails: dict) -> str:
        max_tokens = guardrails.get("max_tokens", 2000)
        blocked_topics = guardrails.get("blocked_topics", [])

        words = output.split()
        if len(words) > max_tokens:
            output = " ".join(words[:max_tokens]) + "..."

        output_lower = output.lower()
        for topic in blocked_topics:
            if topic.lower() in output_lower:
                return "I'm unable to discuss that topic. Please ask something else."

        return output

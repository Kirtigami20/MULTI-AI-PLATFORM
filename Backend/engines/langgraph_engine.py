from typing import TypedDict, Annotated, Sequence, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool as lc_tool
from pydantic import BaseModel, Field, create_model
from config import settings
from engines.base import BaseEngine, EngineMessage, EngineResponse, ToolCall, ToolResult
from prompts.system import build_system_prompt
from utils.constants import DEFAULT_MODEL, MAX_TOOL_ITERATIONS
from utils.builtin_tools import get_builtin_tool, is_builtin_tool
from utils.tool_executor import ToolExecutor
from utils.logger import PipelineLogger, StageTimer


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    rag_context: str
    tool_results: list[dict]
    iteration: int
    agent_config: dict


class LangGraphEngine(BaseEngine):

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

        tools_map = {}
        for t in (available_tools or []):
            name = t.get("name", "")
            if name:
                tools_map[name] = t

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
                f"{formatted_rag}"
            )

        lc_messages = self._build_history(messages)
        lc_tools = self._build_langchain_tools(list(tools_map.values()))

        graph = self._build_graph(llm, lc_tools, tools_map, system_text)

        initial_state: AgentState = {
            "messages": lc_messages,
            "rag_context": formatted_rag,
            "tool_results": [],
            "iteration": 0,
            "agent_config": agent_config,
        }

        PipelineLogger.log_stage_5_llm_request(
            engine_name="langgraph",
            model_name=model_name,
            iteration=1,
            payload_summary={
                "messages_count": len(lc_messages),
                "tools_count": len(lc_tools),
                "tool_names": list(tools_map.keys()),
            },
        )

        try:
            with StageTimer() as timer:
                final_state = await graph.ainvoke(initial_state)
        except Exception as e:
            PipelineLogger.log_pipeline_error("LANGGRAPH_ENGINE_AINVOKE", e)
            return EngineResponse(
                content=f"Engine error: {str(e)}",
                model=model_name,
            )

        all_messages = final_state.get("messages", [])
        output = ""

        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage) and msg.content:
                output = msg.content
                break

        if not output and all_messages:
            last = all_messages[-1]
            if hasattr(last, "content"):
                output = str(last.content)

        raw_tool_results = final_state.get("tool_results", [])
        all_tool_calls = [
            ToolCall(
                id="",
                name=tr.get("name", ""),
                arguments=tr.get("arguments", {}),
            )
            for tr in raw_tool_results
        ]
        all_tool_result_objs = [
            ToolResult(
                tool_call_id="",
                name=tr.get("name", ""),
                result=tr.get("result", ""),
                success=tr.get("success", True),
            )
            for tr in raw_tool_results
        ]

        PipelineLogger.log_stage_6_llm_response(
            engine_name="langgraph",
            duration_ms=timer.duration_ms,
            tokens_used=0,
            tool_calls_count=len(all_tool_calls),
            content_preview=output or "(tool output)",
        )

        if guardrails.get("enabled", False):
            output = self._apply_guardrails(output, guardrails)

        return EngineResponse(
            content=output,
            tool_calls=all_tool_calls,
            tool_results=all_tool_result_objs,
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

    def _build_langchain_tools(self, tools: list[dict]) -> list:
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

    def _build_graph(
        self, llm, lc_tools: list, tools_map: dict, system_text: str
    ) -> StateGraph:
        bound_llm = llm.bind_tools(lc_tools if lc_tools else [])

        async def agent_node(state: AgentState) -> dict:
            msgs = list(state["messages"])
            if not any(isinstance(m, SystemMessage) for m in msgs):
                msgs = [SystemMessage(content=system_text)] + msgs

            response = await bound_llm.ainvoke(msgs)
            return {"messages": [response]}

        async def tool_node(state: AgentState) -> dict:
            last_msg = state["messages"][-1]
            tool_results = []
            new_messages = []
            iteration = state.get("iteration", 0)

            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    tool_def = tools_map.get(tool_name)

                    if tool_def:
                        result = await ToolExecutor.execute(
                            tool_name, tool_args, [tool_def]
                        )
                    else:
                        result = '{"error": "Tool not found"}'

                    new_messages.append(ToolMessage(
                        content=result,
                        tool_call_id=tc["id"],
                    ))
                    tool_results.append({
                        "name": tool_name,
                        "arguments": tool_args,
                        "result": result,
                        "success": True,
                    })

            existing_results = state.get("tool_results", [])
            return {
                "messages": new_messages,
                "tool_results": existing_results + tool_results,
                "iteration": iteration + 1,
            }

        def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
            last_msg = state["messages"][-1]
            iteration = state.get("iteration", 0)

            if iteration >= MAX_TOOL_ITERATIONS:
                return "__end__"

            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                return "tools"

            return "__end__"

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

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

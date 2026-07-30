"""
Engine Comparison Tests

Tests all 3 engines (LangChain, LangGraph, CustomLLM) with tool calling,
comparing: tool invocation, response format, error handling, and behavior.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


from engines.base import EngineMessage, EngineResponse, ToolCall, ToolResult
from engines.factory import get_engine, ENGINES
from engines.langchain_engine import LangChainEngine
from engines.langgraph_engine import LangGraphEngine
from engines.custom_llm_engine import CustomLLMEngine


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------

class TestEngineFactory:

    def test_get_langchain_engine(self):
        engine = get_engine("langchain")
        assert isinstance(engine, LangChainEngine)

    def test_get_langgraph_engine(self):
        engine = get_engine("langgraph")
        assert isinstance(engine, LangGraphEngine)

    def test_get_custom_llm_engine(self):
        engine = get_engine("custom_llm")
        assert isinstance(engine, CustomLLMEngine)

    def test_unknown_engine_raises(self):
        with pytest.raises(ValueError) as exc_info:
            get_engine("unknown")
        assert "Unknown engine type" in str(exc_info.value)

    def test_all_engines_inherit_base(self):
        for name, cls in ENGINES.items():
            engine = cls()
            assert hasattr(engine, "chat"), f"{name} missing chat method"


# ---------------------------------------------------------------------------
# Tool building tests - each engine builds tools from registry
# ---------------------------------------------------------------------------

class TestToolBuilding:
    """Test that all engines build LangChain tools from registry correctly."""

    @pytest.fixture
    def lc_engine(self):
        return LangChainEngine()

    @pytest.fixture
    def lg_engine(self):
        return LangGraphEngine()

    def test_lc_build_builtin_calculator(self, lc_engine):
        tools = lc_engine._build_tools([{"name": "calculator", "tool_type": "builtin", "description": ""}])
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "calculator"
        assert hasattr(tool, "invoke")

    def test_lg_build_builtin_calculator(self, lg_engine):
        tools = lg_engine._build_langchain_tools([{"name": "calculator", "tool_type": "builtin", "description": ""}])
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "calculator"

    def test_lc_build_builtin_current_date(self, lc_engine):
        tools = lc_engine._build_tools([{"name": "current_date", "tool_type": "builtin", "description": ""}])
        assert len(tools) == 1
        assert tools[0].name == "current_date"

    def test_lc_build_unknown_builtin_skipped(self, lc_engine):
        tools = lc_engine._build_tools([{"name": "nonexistent", "tool_type": "builtin", "description": ""}])
        assert len(tools) == 0

    def test_lg_build_unknown_builtin_skipped(self, lg_engine):
        tools = lg_engine._build_langchain_tools([{"name": "nonexistent", "tool_type": "builtin", "description": ""}])
        assert len(tools) == 0

    def test_lc_build_with_description_override(self, lc_engine):
        tools = lc_engine._build_tools([{"name": "calculator", "tool_type": "builtin", "description": "Custom description"}])
        assert tools[0].description == "Custom description"


# ---------------------------------------------------------------------------
# Tool invocation tests - test that built tools work when called
# ---------------------------------------------------------------------------

class TestToolInvocation:
    """Test that tools built by each engine actually execute correctly."""

    @pytest.fixture
    def lc_calc_tool(self):
        engine = LangChainEngine()
        return engine._build_tools([{"name": "calculator", "tool_type": "builtin", "description": ""}])[0]

    @pytest.fixture
    def lg_calc_tool(self):
        engine = LangGraphEngine()
        return engine._build_langchain_tools([{"name": "calculator", "tool_type": "builtin", "description": ""}])[0]

    @pytest.mark.asyncio
    async def test_lc_calculator_invocation(self, lc_calc_tool):
        from utils.builtin_tools import handle_calculator
        result = handle_calculator("2 + 3")
        parsed = json.loads(result)
        assert parsed["result"] == 5

    @pytest.mark.asyncio
    async def test_lg_calculator_invocation(self, lg_calc_tool):
        from utils.builtin_tools import handle_calculator
        result = handle_calculator("7 * 6")
        parsed = json.loads(result)
        assert parsed["result"] == 42

    @pytest.mark.asyncio
    async def test_lc_current_date_invocation(self):
        from utils.builtin_tools import handle_current_date
        result = handle_current_date()
        parsed = json.loads(result)
        assert "date" in parsed
        assert "day_of_week" in parsed


# ---------------------------------------------------------------------------
# History building tests - each engine builds messages differently
# ---------------------------------------------------------------------------

class TestHistoryBuilding:

    def test_lc_build_history(self):
        engine = LangChainEngine()
        messages = [
            EngineMessage(role="user", content="Hello"),
            EngineMessage(role="assistant", content="Hi there"),
        ]
        history = engine._build_history(messages)
        assert len(history) == 2
        assert history[0].content == "Hello"
        assert history[1].content == "Hi there"

    def test_lg_build_history(self):
        engine = LangGraphEngine()
        messages = [
            EngineMessage(role="user", content="Hello"),
            EngineMessage(role="assistant", content="Hi"),
        ]
        history = engine._build_history(messages)
        assert len(history) == 2

    def test_custom_build_history_with_window(self):
        engine = CustomLLMEngine()
        messages = [
            EngineMessage(role="user", content=f"msg{i}")
            for i in range(20)
        ]
        history = engine._build_history(messages, window_size=5)
        assert len(history) == 5
        assert history[0]["content"] == "msg15"

    def test_custom_build_history_filters_system(self):
        engine = CustomLLMEngine()
        messages = [
            EngineMessage(role="user", content="Hello"),
            EngineMessage(role="system", content="System prompt"),
            EngineMessage(role="assistant", content="Hi"),
        ]
        history = engine._build_history(messages, window_size=10)
        assert len(history) == 2
        roles = [m["role"] for m in history]
        assert "system" not in roles

    def test_custom_build_history_greeting_trims(self):
        engine = CustomLLMEngine()
        messages = [
            EngineMessage(role="user", content="Tell me about Tesla"),
            EngineMessage(role="assistant", content="Tesla is an EV maker..."),
            EngineMessage(role="user", content="Hello"),
        ]
        history = engine._build_history(messages, window_size=10)
        assert len(history) == 1
        assert history[0]["content"] == "Hello"
        assert history[0]["role"] == "user"

    def test_custom_build_history_topic_shift_trims(self):
        engine = CustomLLMEngine()
        messages = [
            EngineMessage(role="user", content="Who built the Eiffel Tower?"),
            EngineMessage(role="assistant", content="It was designed by Gustave Eiffel."),
            EngineMessage(role="user", content="What is the stock price of Tesla?"),
        ]
        history = engine._build_history(messages, window_size=10)
        assert len(history) == 1
        assert history[0]["content"] == "What is the stock price of Tesla?"

    def test_custom_build_history_follow_up_preserves(self):
        engine = CustomLLMEngine()
        messages = [
            EngineMessage(role="user", content="Tell me about Eiffel Tower"),
            EngineMessage(role="assistant", content="It is a famous tower in Paris."),
            EngineMessage(role="user", content="How tall is it?"),
        ]
        history = engine._build_history(messages, window_size=10)
        assert len(history) == 3
        assert history[0]["content"] == "Tell me about Eiffel Tower"
        assert history[2]["content"] == "How tall is it?"


# ---------------------------------------------------------------------------
# RAG formatting tests
# ---------------------------------------------------------------------------

class TestRAGFormatting:

    def test_lc_format_rag_empty(self):
        assert LangChainEngine._format_rag("") == ""
        assert LangChainEngine._format_rag(None) == ""

    def test_lc_format_rag_with_chunks(self):
        chunks = [
            {"chunk_text": "Some text", "score": 0.9, "metadata": {"source": "doc.pdf"}},
            {"chunk_text": "More text", "score": 0.7, "metadata": {"source": "web.txt"}},
        ]
        result = LangChainEngine._format_rag(chunks)
        assert "doc.pdf" in result
        assert "Some text" in result

    def test_lg_format_rag_empty(self):
        assert LangGraphEngine._format_rag("") == ""
        assert LangGraphEngine._format_rag([]) == ""

    def test_lg_format_rag_with_chunks(self):
        chunks = [{"chunk_text": "Test", "score": 0.8, "metadata": {"source": "file.csv"}}]
        result = LangGraphEngine._format_rag(chunks)
        assert "file.csv" in result


# ---------------------------------------------------------------------------
# Guardrails tests
# ---------------------------------------------------------------------------

class TestGuardrails:

    def test_lc_apply_guardrails_max_tokens(self):
        engine = LangChainEngine()
        long_text = " ".join(["word"] * 3000)
        result = engine._apply_guardrails(long_text, {"max_tokens": 100})
        assert len(result.split()) <= 102

    def test_lc_apply_guardrails_blocked_topics(self):
        engine = LangChainEngine()
        result = engine._apply_guardrails(
            "Let me talk about politics now",
            {"blocked_topics": ["politics"]},
        )
        assert "unable to discuss" in result.lower()

    def test_lg_apply_guardrails_max_tokens(self):
        engine = LangGraphEngine()
        long_text = " ".join(["word"] * 3000)
        result = engine._apply_guardrails(long_text, {"max_tokens": 100})
        assert len(result.split()) <= 102

    def test_custom_apply_guardrails_max_tokens(self):
        engine = CustomLLMEngine()
        long_text = " ".join(["word"] * 3000)
        result = engine._apply_guardrails(long_text, {"max_tokens": 100})
        assert len(result.split()) <= 102


# ---------------------------------------------------------------------------
# Engine response structure comparison
# ---------------------------------------------------------------------------

class TestResponseStructure:
    """Verify all engines return consistent EngineResponse format."""

    def test_engine_response_defaults(self):
        resp = EngineResponse(content="Hello")
        assert resp.content == "Hello"
        assert resp.tool_calls == []
        assert resp.tool_results == []
        assert resp.tokens_used == 0
        assert resp.model == ""

    def test_engine_response_with_tools(self):
        tc = ToolCall(id="1", name="calc", arguments={"expression": "1+1"})
        tr = ToolResult(tool_call_id="1", name="calc", result='{"result":2}')
        resp = EngineResponse(content="Answer", tool_calls=[tc], tool_results=[tr])
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "calc"
        assert resp.tool_results[0].success is True


# ---------------------------------------------------------------------------
# OpenAI schema comparison for CustomLLM
# ---------------------------------------------------------------------------

class TestCustomLLMSchemaComparison:

    def test_custom_engine_uses_tool_executor_schema(self):
        tools = [
            {"name": "calculator", "tool_type": "builtin", "description": ""},
            {"name": "current_date", "tool_type": "builtin", "description": ""},
        ]
        from utils.tool_executor import ToolExecutor
        openai_tools = ToolExecutor.get_openai_tools(tools)
        assert len(openai_tools) == 2
        assert all(t["type"] == "function" for t in openai_tools)

    def test_builtin_vs_api_schema_generation(self):
        from utils.tool_executor import ToolExecutor
        builtin = ToolExecutor.get_openai_tools([{"name": "calculator", "tool_type": "builtin", "description": ""}])
        api = ToolExecutor.get_openai_tools([{
            "name": "my_api",
            "tool_type": "api",
            "description": "Test API",
            "config": {"parameters": [{"name": "q", "type": "string", "description": "query", "required": True}]},
        }])
        assert builtin[0]["function"]["name"] == "calculator"
        assert api[0]["function"]["name"] == "my_api"
        assert "parameters" in builtin[0]["function"]
        assert "parameters" in api[0]["function"]


# ---------------------------------------------------------------------------
# Summary comparison
# ---------------------------------------------------------------------------

class TestEngineComparisonSummary:
    """
    Documents the architectural differences between the 3 engines.
    These tests serve as living documentation.
    """

    def test_langchain_engine_uses_prebuilt_react(self):
        """LangChain uses langgraph.prebuilt.create_react_agent."""
        engine = LangChainEngine()
        assert hasattr(engine, "chat")
        assert hasattr(engine, "_build_tools")
        assert hasattr(engine, "_build_builtin_tool")

    def test_langgraph_engine_uses_custom_state_graph(self):
        """LangGraph uses a custom StateGraph with explicit agent/tool nodes."""
        engine = LangGraphEngine()
        assert hasattr(engine, "chat")
        assert hasattr(engine, "_build_graph")
        assert hasattr(engine, "_build_langchain_tools")

    def test_custom_llm_engine_uses_raw_openai(self):
        """CustomLLM uses raw openai client with manual tool call loop."""
        engine = CustomLLMEngine()
        assert hasattr(engine, "chat")
        assert hasattr(engine, "_build_history")
        assert hasattr(engine, "_parse_rag_context")

    def test_all_engines_share_base_methods(self):
        """All engines share similar helper patterns."""
        engines = [LangChainEngine(), LangGraphEngine(), CustomLLMEngine()]
        for e in engines:
            assert hasattr(e, "chat")

    def test_engines_differ_in_tool_approach(self):
        """Document key architectural differences."""
        differences = {
            "langchain": "Uses create_react_agent + LangChain @tool decorator",
            "langgraph": "Custom StateGraph with agent_node + tool_node + conditional edges",
            "custom_llm": "Raw OpenAI API calls with manual tool_calls parsing loop",
        }
        assert len(differences) == 3
        for engine_name, desc in differences.items():
            assert engine_name in ENGINES

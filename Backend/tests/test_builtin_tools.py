import json
import pytest
from utils.builtin_tools import (
    BUILTIN_TOOLS,
    get_builtin_tool,
    list_builtin_tool_names,
    is_builtin_tool,
    get_builtin_openai_schema,
    execute_builtin_tool,
    handle_calculator,
    handle_current_date,
)


# ---------------------------------------------------------------------------
# Registry structure tests
# ---------------------------------------------------------------------------

class TestRegistryStructure:

    def test_registry_has_all_expected_tools(self):
        expected = {"web_search", "calculator", "current_date", "send_email"}
        assert set(BUILTIN_TOOLS.keys()) == expected

    def test_each_tool_has_required_keys(self):
        required_keys = {"name", "description", "parameters", "handler", "async"}
        for name, tool in BUILTIN_TOOLS.items():
            missing = required_keys - set(tool.keys())
            assert not missing, f"Tool '{name}' missing keys: {missing}"

    def test_each_handler_is_callable(self):
        for name, tool in BUILTIN_TOOLS.items():
            assert callable(tool["handler"]), f"Handler for '{name}' is not callable"

    def test_parameters_are_lists(self):
        for name, tool in BUILTIN_TOOLS.items():
            assert isinstance(tool["parameters"], list), f"Parameters for '{name}' is not a list"

    def test_parameter_dicts_have_required_fields(self):
        for name, tool in BUILTIN_TOOLS.items():
            for param in tool["parameters"]:
                assert "name" in param, f"Parameter in '{name}' missing 'name'"
                assert "type" in param, f"Parameter in '{name}' missing 'type'"
                assert "description" in param, f"Parameter in '{name}' missing 'description'"


# ---------------------------------------------------------------------------
# Public API tests
# ---------------------------------------------------------------------------

class TestRegistryAPI:

    def test_is_builtin_tool_valid(self):
        assert is_builtin_tool("calculator") is True
        assert is_builtin_tool("web_search") is True
        assert is_builtin_tool("current_date") is True
        assert is_builtin_tool("send_email") is True

    def test_is_builtin_tool_invalid(self):
        assert is_builtin_tool("nonexistent") is False
        assert is_builtin_tool("") is False

    def test_list_builtin_tool_names(self):
        names = list_builtin_tool_names()
        assert isinstance(names, list)
        assert len(names) == 4
        assert "calculator" in names
        assert "web_search" in names

    def test_get_builtin_tool_valid(self):
        tool = get_builtin_tool("calculator")
        assert tool is not None
        assert tool["name"] == "calculator"
        assert callable(tool["handler"])

    def test_get_builtin_tool_invalid(self):
        assert get_builtin_tool("nonexistent") is None


# ---------------------------------------------------------------------------
# Calculator handler tests
# ---------------------------------------------------------------------------

class TestCalculatorHandler:

    def test_addition(self):
        result = json.loads(handle_calculator("2 + 3"))
        assert result["result"] == 5

    def test_subtraction(self):
        result = json.loads(handle_calculator("10 - 4"))
        assert result["result"] == 6

    def test_multiplication(self):
        result = json.loads(handle_calculator("3 * 7"))
        assert result["result"] == 21

    def test_division(self):
        result = json.loads(handle_calculator("10 / 2"))
        assert result["result"] == 5.0

    def test_complex_expression(self):
        result = json.loads(handle_calculator("2 + 3 * 4"))
        assert result["result"] == 14

    def test_parentheses(self):
        result = json.loads(handle_calculator("(2 + 3) * 4"))
        assert result["result"] == 20

    def test_modulo(self):
        result = json.loads(handle_calculator("10 % 3"))
        assert result["result"] == 1

    def test_invalid_expression(self):
        result = json.loads(handle_calculator("abc"))
        assert "error" in result

    def test_empty_expression(self):
        result = json.loads(handle_calculator(""))
        assert "error" in result

    def test_malicious_expression(self):
        result = json.loads(handle_calculator("__import__('os').system('ls')"))
        assert "error" in result or "result" in result


# ---------------------------------------------------------------------------
# Current date handler tests
# ---------------------------------------------------------------------------

class TestCurrentDateHandler:

    def test_returns_valid_json(self):
        result = json.loads(handle_current_date())
        assert "date" in result
        assert "time" in result
        assert "datetime" in result
        assert "day_of_week" in result

    def test_date_format(self):
        result = json.loads(handle_current_date())
        parts = result["date"].split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4
        assert len(parts[1]) == 2
        assert len(parts[2]) == 2

    def test_day_of_week_is_valid(self):
        result = json.loads(handle_current_date())
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        assert result["day_of_week"] in valid_days


# ---------------------------------------------------------------------------
# Execute builtin tool tests
# ---------------------------------------------------------------------------

class TestExecuteBuiltinTool:

    @pytest.mark.asyncio
    async def test_execute_calculator(self):
        result = await execute_builtin_tool("calculator", {"expression": "2 + 3"})
        parsed = json.loads(result)
        assert parsed["result"] == 5

    @pytest.mark.asyncio
    async def test_execute_current_date(self):
        result = await execute_builtin_tool("current_date", {})
        parsed = json.loads(result)
        assert "date" in parsed

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        result = await execute_builtin_tool("nonexistent", {})
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_execute_filters_extra_args(self):
        result = await execute_builtin_tool("calculator", {"expression": "1+1", "extra": "ignored"})
        parsed = json.loads(result)
        assert parsed["result"] == 2


# ---------------------------------------------------------------------------
# OpenAI schema generation tests
# ---------------------------------------------------------------------------

class TestOpenAISchema:

    def test_calculator_schema(self):
        schema = get_builtin_openai_schema("calculator")
        assert schema["name"] == "calculator"
        assert schema["description"] != ""
        assert schema["parameters"]["type"] == "object"
        assert "expression" in schema["parameters"]["properties"]
        assert "required" in schema["parameters"]
        assert "expression" in schema["parameters"]["required"]

    def test_current_date_schema(self):
        schema = get_builtin_openai_schema("current_date")
        assert schema["name"] == "current_date"
        assert schema["parameters"]["type"] == "object"
        assert schema["parameters"]["properties"] == {}
        assert "required" not in schema["parameters"]

    def test_send_email_schema(self):
        schema = get_builtin_openai_schema("send_email")
        assert schema["name"] == "send_email"
        props = schema["parameters"]["properties"]
        assert "to" in props
        assert "subject" in props
        assert "body" in props
        assert set(schema["parameters"]["required"]) == {"to", "subject", "body"}

    def test_web_search_schema(self):
        schema = get_builtin_openai_schema("web_search")
        assert schema["name"] == "web_search"
        assert "query" in schema["parameters"]["properties"]

    def test_unknown_tool_returns_none(self):
        assert get_builtin_openai_schema("nonexistent") is None

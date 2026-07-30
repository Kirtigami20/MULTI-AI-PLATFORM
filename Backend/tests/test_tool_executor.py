"""
Comprehensive tests for ToolExecutor.

Covers:
- OpenAI schema generation
- OpenAI tool list building
- Built-in tool execution
- Authentication (all 4 modes: none, api_key header/query, bearer, basic)
- Request parameter routing (query, path, header, body)
- GET query parameter merging (the critical regression)
- POST body construction (template + raw JSON)
- Request validation (missing params, missing auth, missing URL)
- Error response building
- Secret masking
- Body building
"""

import json
import base64
import pytest
import httpx
import respx
from utils.tool_executor import ToolExecutor


# ---------------------------------------------------------------------------
# generate_openai_schema tests
# ---------------------------------------------------------------------------

class TestGenerateOpenAISchema:

    def test_basic_schema(self):
        schema = ToolExecutor.generate_openai_schema(
            "my_tool",
            "Does something",
            [{"name": "query", "type": "string", "description": "The query", "required": True}],
        )
        assert schema["name"] == "my_tool"
        assert schema["description"] == "Does something"
        assert schema["parameters"]["type"] == "object"
        assert "query" in schema["parameters"]["properties"]
        assert schema["parameters"]["properties"]["query"]["type"] == "string"
        assert "required" in schema["parameters"]
        assert "query" in schema["parameters"]["required"]

    def test_no_required_params(self):
        schema = ToolExecutor.generate_openai_schema(
            "optional_tool",
            "Has optional params",
            [{"name": "name", "type": "string", "description": "A name", "required": False}],
        )
        assert "required" not in schema["parameters"]

    def test_multiple_param_types(self):
        params = [
            {"name": "text", "type": "string", "description": "text", "required": True},
            {"name": "count", "type": "integer", "description": "count", "required": False},
            {"name": "flag", "type": "boolean", "description": "flag", "required": False},
        ]
        schema = ToolExecutor.generate_openai_schema("multi", "Multi param tool", params)
        assert schema["parameters"]["properties"]["text"]["type"] == "string"
        assert schema["parameters"]["properties"]["count"]["type"] == "integer"
        assert schema["parameters"]["properties"]["flag"]["type"] == "boolean"


# ---------------------------------------------------------------------------
# get_openai_tools tests
# ---------------------------------------------------------------------------

class TestGetOpenAITools:

    def test_builtin_tool(self):
        tools = [{"name": "calculator", "tool_type": "builtin", "description": ""}]
        result = ToolExecutor.get_openai_tools(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "calculator"

    def test_builtin_tool_with_description_override(self):
        tools = [{"name": "calculator", "tool_type": "builtin", "description": "Custom calc"}]
        result = ToolExecutor.get_openai_tools(tools)
        assert result[0]["function"]["description"] == "Custom calc"

    def test_builtin_tool_unknown(self):
        tools = [{"name": "nonexistent", "tool_type": "builtin", "description": ""}]
        result = ToolExecutor.get_openai_tools(tools)
        assert len(result) == 0

    def test_api_tool_with_params(self):
        tools = [{
            "name": "my_api",
            "tool_type": "api",
            "description": "My API",
            "config": {
                "parameters": [
                    {"name": "q", "type": "string", "description": "query", "required": True}
                ]
            },
        }]
        result = ToolExecutor.get_openai_tools(tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "my_api"

    def test_api_tool_with_existing_schema(self):
        tools = [{
            "name": "my_api",
            "tool_type": "api",
            "description": "",
            "config": {
                "schema": {
                    "name": "my_api",
                    "description": "From schema",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
        }]
        result = ToolExecutor.get_openai_tools(tools)
        assert len(result) == 1
        assert result[0]["function"]["description"] == "From schema"

    def test_mixed_tools(self):
        tools = [
            {"name": "calculator", "tool_type": "builtin", "description": ""},
            {"name": "web_search", "tool_type": "builtin", "description": ""},
            {
                "name": "my_api",
                "tool_type": "api",
                "description": "API",
                "config": {"parameters": [{"name": "x", "type": "string", "description": "x", "required": True}]},
            },
        ]
        result = ToolExecutor.get_openai_tools(tools)
        assert len(result) == 3

    def test_empty_tools(self):
        assert ToolExecutor.get_openai_tools([]) == []


# ---------------------------------------------------------------------------
# ToolExecutor.execute tests
# ---------------------------------------------------------------------------

class TestToolExecutorExecute:

    @pytest.mark.asyncio
    async def test_execute_builtin_calculator(self):
        tools = [{"name": "calculator", "tool_type": "builtin"}]
        result = await ToolExecutor.execute("calculator", {"expression": "2 * 3"}, tools)
        parsed = json.loads(result)
        assert parsed["result"] == 6

    @pytest.mark.asyncio
    async def test_execute_builtin_current_date(self):
        tools = [{"name": "current_date", "tool_type": "builtin"}]
        result = await ToolExecutor.execute("current_date", {}, tools)
        parsed = json.loads(result)
        assert "date" in parsed

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_name(self):
        tools = [{"name": "calculator", "tool_type": "builtin"}]
        result = await ToolExecutor.execute("nonexistent", {}, tools)
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_type(self):
        tools = [{"name": "something", "tool_type": "mystery"}]
        result = await ToolExecutor.execute("something", {}, tools)
        parsed = json.loads(result)
        assert "error" in parsed


# ---------------------------------------------------------------------------
# Auth header building tests
# ---------------------------------------------------------------------------

class TestAuthHeaders:

    def test_bearer_auth(self):
        result = ToolExecutor._build_auth({"type": "bearer", "token": "abc123"})
        assert result["headers"] == {"Authorization": "Bearer abc123"}
        assert result["query"] == {}

    def test_api_key_auth_header(self):
        result = ToolExecutor._build_auth({"type": "api_key", "token": "key123", "header": "X-API-Key", "location": "header"})
        assert result["headers"] == {"X-API-Key": "key123"}
        assert result["query"] == {}

    def test_api_key_auth_query(self):
        result = ToolExecutor._build_auth({"type": "api_key", "token": "key123", "header": "api_token", "location": "query"})
        assert result["headers"] == {}
        assert result["query"] == {"api_token": "key123"}
        assert result["body"] == {}

    def test_api_key_auth_body(self):
        result = ToolExecutor._build_auth({"type": "api_key", "token": "key123", "header": "api_key", "location": "body"})
        assert result["headers"] == {}
        assert result["query"] == {}
        assert result["body"] == {"api_key": "key123"}

    def test_api_key_default_location(self):
        result = ToolExecutor._build_auth({"type": "api_key", "token": "key123", "header": "X-API-Key"})
        assert result["headers"] == {"X-API-Key": "key123"}
        assert result["query"] == {}

    def test_api_key_custom_header(self):
        result = ToolExecutor._build_auth({"type": "api_key", "token": "k", "header": "X-Custom", "location": "header"})
        assert result["headers"] == {"X-Custom": "k"}
        assert result["query"] == {}

    def test_basic_auth(self):
        result = ToolExecutor._build_auth({"type": "basic", "username": "user", "token": "pass"})
        expected = base64.b64encode(b"user:pass").decode()
        assert result["headers"] == {"Authorization": f"Basic {expected}"}
        assert result["query"] == {}

    def test_none_auth(self):
        result = ToolExecutor._build_auth({"type": "none", "token": ""})
        assert result == {"headers": {}, "query": {}}

    def test_empty_auth(self):
        result = ToolExecutor._build_auth({})
        assert result == {"headers": {}, "query": {}}

    def test_no_token(self):
        result = ToolExecutor._build_auth({"type": "bearer", "token": ""})
        assert result == {"headers": {}, "query": {}}


# ---------------------------------------------------------------------------
# Request params building tests
# ---------------------------------------------------------------------------

class TestRequestParams:

    def test_query_params(self):
        params = [
            {"name": "q", "type": "string", "description": "", "required": True, "location": "query"},
            {"name": "limit", "type": "integer", "description": "", "required": False, "location": "query"},
        ]
        result = ToolExecutor._build_request_params({"q": "hello", "limit": 10}, params, None, {"type": "none"})
        assert result["query"] == {"q": "hello", "limit": 10}

    def test_path_params(self):
        params = [
            {"name": "id", "type": "string", "description": "", "required": True, "location": "path"},
        ]
        result = ToolExecutor._build_request_params({"id": "123"}, params, None, {"type": "none"})
        assert result["path_values"] == {"id": "123"}

    def test_body_params(self):
        params = [
            {"name": "name", "type": "string", "description": "", "required": True, "location": "body"},
        ]
        result = ToolExecutor._build_request_params({"name": "test"}, params, None, {"type": "none"})
        assert result["body_params"] == {"name": "test"}

    def test_header_params(self):
        params = [
            {"name": "x-custom", "type": "string", "description": "", "required": False, "location": "header"},
        ]
        result = ToolExecutor._build_request_params({"x-custom": "value"}, params, None, {"type": "none"})
        assert result["header_params"] == {"x-custom": "value"}

    def test_mixed_params(self):
        params = [
            {"name": "q", "type": "string", "description": "", "required": True, "location": "query"},
            {"name": "body", "type": "string", "description": "", "required": True, "location": "body"},
            {"name": "id", "type": "string", "description": "", "required": True, "location": "path"},
        ]
        result = ToolExecutor._build_request_params(
            {"q": "search", "body": "data", "id": "42"},
            params, None, {"type": "none"}
        )
        assert result["query"] == {"q": "search"}
        assert result["body_params"] == {"body": "data"}
        assert result["path_values"] == {"id": "42"}

    def test_auth_headers_included(self):
        result = ToolExecutor._build_request_params({}, [], None, {"type": "bearer", "token": "tok"})
        assert result["auth_headers"] == {"Authorization": "Bearer tok"}

    def test_query_auth_merged_with_user_query(self):
        """Auth query params are merged with user query params, not overwritten."""
        params = [
            {"name": "symbols", "type": "string", "description": "", "required": True, "location": "query"},
        ]
        auth = {"type": "api_key", "token": "mykey123", "header": "api_token", "location": "query"}
        result = ToolExecutor._build_request_params({"symbols": "TSLA"}, params, None, auth)
        assert result["query"] == {"symbols": "TSLA", "api_token": "mykey123"}


# ---------------------------------------------------------------------------
# Body building tests
# ---------------------------------------------------------------------------

class TestBuildBody:

    def test_with_template(self):
        body = ToolExecutor._build_body({"name": "John", "age": 30}, '{"name": "{name}", "age": {age}}')
        assert '"name": "John"' in body
        assert '"age": 30' in body

    def test_without_template(self):
        body = ToolExecutor._build_body({"key": "value"}, None)
        parsed = json.loads(body)
        assert parsed == {"key": "value"}

    def test_empty_params(self):
        body = ToolExecutor._build_body({}, None)
        assert body == ""


# ---------------------------------------------------------------------------
# Request validation tests
# ---------------------------------------------------------------------------

class TestValidation:

    def test_missing_url(self):
        tool_def = {"config": {"url": "", "auth": {"type": "none"}}}
        result = ToolExecutor._validate_request(tool_def, {})
        assert result is not None
        assert result["error_type"] == "configuration"

    def test_missing_api_key_token(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "api_key", "token": "", "header": "X-Key", "location": "header"},
            }
        }
        result = ToolExecutor._validate_request(tool_def, {})
        assert result is not None
        assert result["error_type"] == "authentication"

    def test_missing_bearer_token(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "bearer", "token": ""},
            }
        }
        result = ToolExecutor._validate_request(tool_def, {})
        assert result is not None
        assert result["error_type"] == "authentication"

    def test_missing_basic_username(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "basic", "token": "pass", "username": ""},
            }
        }
        result = ToolExecutor._validate_request(tool_def, {})
        assert result is not None
        assert result["error_type"] == "authentication"

    def test_missing_required_params(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "none"},
                "parameters": [
                    {"name": "query", "type": "string", "required": True},
                    {"name": "limit", "type": "integer", "required": False},
                ],
            }
        }
        result = ToolExecutor._validate_request(tool_def, {"limit": 5})
        assert result is not None
        assert result["error_type"] == "parameters"
        assert "query" in result["missing_parameters"]

    def test_valid_request_passes(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "api_key", "token": "mykey", "header": "X-Key", "location": "header"},
                "parameters": [
                    {"name": "query", "type": "string", "required": True},
                ],
            }
        }
        result = ToolExecutor._validate_request(tool_def, {"query": "hello"})
        assert result is None

    def test_no_auth_passes(self):
        tool_def = {
            "config": {
                "url": "https://api.example.com",
                "auth": {"type": "none"},
                "parameters": [],
            }
        }
        result = ToolExecutor._validate_request(tool_def, {})
        assert result is None


# ---------------------------------------------------------------------------
# Secret masking tests
# ---------------------------------------------------------------------------

class TestSecretMasking:

    def test_mask_long_secret(self):
        assert ToolExecutor._mask_secret("my_secret_key_12345") == "***************2345"

    def test_mask_short_secret(self):
        assert ToolExecutor._mask_secret("ab") == "****"

    def test_mask_empty_secret(self):
        assert ToolExecutor._mask_secret("") == "****"

    def test_mask_exact_four(self):
        assert ToolExecutor._mask_secret("abcd") == "****"

    def test_mask_five_chars(self):
        assert ToolExecutor._mask_secret("abcde") == "*bcde"


# ---------------------------------------------------------------------------
# Error response building tests
# ---------------------------------------------------------------------------

class TestErrorResponse:

    def test_basic_error(self):
        result = json.loads(ToolExecutor._build_error_response("timeout", "Request timed out"))
        assert result["error"] == "Request timed out"
        assert result["error_type"] == "timeout"
        assert "status_code" not in result

    def test_http_error_with_json_body(self):
        body = '{"message": "Unauthorized"}'
        result = json.loads(ToolExecutor._build_error_response("http_error", "Auth failed", 401, body))
        assert result["status_code"] == 401
        assert result["api_response"]["message"] == "Unauthorized"

    def test_http_error_with_text_body(self):
        result = json.loads(ToolExecutor._build_error_response("http_error", "Not found", 404, "Page not found"))
        assert result["status_code"] == 404
        assert result["api_response"] == "Page not found"


# ===========================================================================
# REGRESSION TESTS: Full API execution with mocked HTTP
# ===========================================================================

class TestGetQueryAuth:
    """Test 1: GET + Query Authentication — both user params and auth token in query."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_with_query_api_key(self):
        """User params (symbols=TSLA) and auth (api_token=key) must both appear in query."""
        mock_route = respx.get("https://api.example.com/v1/news/all").mock(
            return_value=httpx.Response(200, json={"articles": []})
        )

        tool_def = {
            "name": "news_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/news/all",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "symbols", "type": "string", "description": "Ticker", "required": True, "location": "query"},
                ],
                "body_template": None,
                "auth": {
                    "type": "api_key",
                    "token": "test_key_123",
                    "header": "api_token",
                    "location": "query",
                },
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"symbols": "TSLA"})
        parsed = json.loads(result)

        assert mock_route.called
        request = mock_route.calls[0].request
        query_str = str(request.url.params)
        assert "symbols=TSLA" in query_str
        assert "api_token=test_key_123" in query_str
        assert parsed == {"articles": []}


class TestGetHeaderAuth:
    """Test 2: GET + Header Authentication — API key in header, only user params in query."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_with_header_api_key(self):
        mock_route = respx.get("https://api.example.com/v1/data").mock(
            return_value=httpx.Response(200, json={"data": "ok"})
        )

        tool_def = {
            "name": "data_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/data",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "q", "type": "string", "description": "Query", "required": True, "location": "query"},
                ],
                "body_template": None,
                "auth": {
                    "type": "api_key",
                    "token": "header_key_456",
                    "header": "X-API-Key",
                    "location": "header",
                },
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"q": "test"})

        assert mock_route.called
        request = mock_route.calls[0].request
        # API key is in headers, not in query
        assert request.headers["X-API-Key"] == "header_key_456"
        query_str = str(request.url.params)
        assert "q=test" in query_str
        assert "header_key_456" not in query_str


class TestPostBearerAuth:
    """Test 3: POST + Bearer Authentication — Authorization header, body merged."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_with_bearer_and_body(self):
        mock_route = respx.post("https://api.example.com/v1/translate").mock(
            return_value=httpx.Response(200, json={"translated": "Hola"})
        )

        tool_def = {
            "name": "translate_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/translate",
                "method": "POST",
                "headers": {},
                "parameters": [
                    {"name": "text", "type": "string", "description": "Text to translate", "required": True, "location": "body"},
                    {"name": "target_lang", "type": "string", "description": "Target language", "required": True, "location": "body"},
                ],
                "body_template": None,
                "auth": {
                    "type": "bearer",
                    "token": "bearer_token_789",
                },
            },
        }

        result = await ToolExecutor._execute_api(
            tool_def, {"text": "Hello", "target_lang": "es"}
        )
        parsed = json.loads(result)

        assert mock_route.called
        request = mock_route.calls[0].request
        assert request.headers["Authorization"] == "Bearer bearer_token_789"
        body = json.loads(request.content.decode())
        assert body == {"text": "Hello", "target_lang": "es"}
        assert parsed == {"translated": "Hola"}


class TestPostBasicAuth:
    """Test 4: POST + Basic Authentication — username/password, body works."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_with_basic_auth(self):
        mock_route = respx.post("https://api.example.com/v1/submit").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        tool_def = {
            "name": "submit_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/submit",
                "method": "POST",
                "headers": {},
                "parameters": [
                    {"name": "data", "type": "string", "description": "Data", "required": True, "location": "body"},
                ],
                "body_template": None,
                "auth": {
                    "type": "basic",
                    "username": "admin",
                    "token": "secret_pass",
                },
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"data": "payload"})
        parsed = json.loads(result)

        assert mock_route.called
        request = mock_route.calls[0].request
        expected_cred = base64.b64encode(b"admin:secret_pass").decode()
        assert request.headers["Authorization"] == f"Basic {expected_cred}"
        body = json.loads(request.content.decode())
        assert body == {"data": "payload"}
        assert parsed == {"status": "ok"}


class TestGetParamMerging:
    """Critical regression test: GET with both LLM arguments and query auth params."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_merges_all_query_sources(self):
        """Multiple user query params + auth query param must all appear in the final URL."""
        mock_route = respx.get("https://api.example.com/v1/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        tool_def = {
            "name": "search_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/search",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "q", "type": "string", "description": "Search", "required": True, "location": "query"},
                    {"name": "language", "type": "string", "description": "Lang", "required": False, "location": "query"},
                    {"name": "limit", "type": "integer", "description": "Limit", "required": False, "location": "query"},
                ],
                "body_template": None,
                "auth": {
                    "type": "api_key",
                    "token": "key_abc",
                    "header": "apikey",
                    "location": "query",
                },
            },
        }

        result = await ToolExecutor._execute_api(
            tool_def, {"q": "Tesla", "language": "en", "limit": 5}
        )

        assert mock_route.called
        request = mock_route.calls[0].request
        query_str = str(request.url.params)
        assert "q=Tesla" in query_str
        assert "language=en" in query_str
        assert "limit=5" in query_str
        assert "apikey=key_abc" in query_str

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_no_explicit_query_params_uses_arguments(self):
        """When no params are defined with location=query, all LLM args become query params for GET."""
        mock_route = respx.get("https://api.example.com/v1/info").mock(
            return_value=httpx.Response(200, json={"info": "ok"})
        )

        tool_def = {
            "name": "info_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/info",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "symbol", "type": "string", "description": "Ticker", "required": True, "location": "body"},
                ],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"symbol": "AAPL"})

        assert mock_route.called
        request = mock_route.calls[0].request
        query_str = str(request.url.params)
        # Even though location is "body", for GET the body params are folded into query
        assert "symbol=AAPL" in query_str


class TestHttpErrorHandling:
    """Test structured error responses for various HTTP failures."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_401_returns_structured_error(self):
        respx.get("https://api.example.com/v1/data").mock(
            return_value=httpx.Response(401, json={"error": "invalid_token"})
        )

        tool_def = {
            "name": "data_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/data",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "bearer", "token": "bad_token"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "http_error"
        assert parsed["status_code"] == 401
        assert "Authentication failed" in parsed["error"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_403_returns_structured_error(self):
        respx.get("https://api.example.com/v1/restricted").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )

        tool_def = {
            "name": "restricted_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/restricted",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "http_error"
        assert parsed["status_code"] == 403

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_returns_structured_error(self):
        respx.get("https://api.example.com/v1/missing").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        tool_def = {
            "name": "missing_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/missing",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "http_error"
        assert parsed["status_code"] == 404

    @respx.mock
    @pytest.mark.asyncio
    async def test_200_returns_raw_response(self):
        """Successful responses should return raw text, not wrapped in error."""
        respx.get("https://api.example.com/v1/ok").mock(
            return_value=httpx.Response(200, json={"data": "success"})
        )

        tool_def = {
            "name": "ok_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/ok",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed == {"data": "success"}
        assert "error_type" not in parsed


class TestPostWithQueryAuth:
    """POST request with query-based auth — auth goes in query, body separate."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_with_query_auth_and_body(self):
        mock_route = respx.post("https://api.example.com/v1/action").mock(
            return_value=httpx.Response(200, json={"done": True})
        )

        tool_def = {
            "name": "action_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/action",
                "method": "POST",
                "headers": {},
                "parameters": [
                    {"name": "input", "type": "string", "description": "Input", "required": True, "location": "body"},
                ],
                "body_template": None,
                "auth": {
                    "type": "api_key",
                    "token": "post_query_key",
                    "header": "key",
                    "location": "query",
                },
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"input": "hello"})

        assert mock_route.called
        request = mock_route.calls[0].request
        # Auth in query
        query_str = str(request.url.params)
        assert "key=post_query_key" in query_str
        # Body is separate
        body = json.loads(request.content.decode())
        assert body == {"input": "hello"}


class TestPostWithBodyTemplate:
    """POST request with body template substitution."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_body_template(self):
        mock_route = respx.post("https://api.example.com/v1/process").mock(
            return_value=httpx.Response(200, json={"result": "done"})
        )

        tool_def = {
            "name": "process_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/process",
                "method": "POST",
                "headers": {},
                "parameters": [
                    {"name": "text", "type": "string", "description": "Text", "required": True, "location": "body"},
                    {"name": "lang", "type": "string", "description": "Language", "required": True, "location": "body"},
                ],
                "body_template": '{"content": "{text}", "language": "{lang}", "format": "json"}',
                "auth": {
                    "type": "bearer",
                    "token": "tmpl_token",
                },
            },
        }

        result = await ToolExecutor._execute_api(
            tool_def, {"text": "Hello world", "lang": "en"}
        )

        assert mock_route.called
        request = mock_route.calls[0].request
        body = json.loads(request.content.decode())
        assert body["content"] == "Hello world"
        assert body["language"] == "en"
        assert body["format"] == "json"
        assert request.headers["Authorization"] == "Bearer tmpl_token"


class TestPathParams:
    """GET request with path parameter substitution."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_path_param_substitution(self):
        mock_route = respx.get("https://api.example.com/v1/users/42/profile").mock(
            return_value=httpx.Response(200, json={"name": "Alice"})
        )

        tool_def = {
            "name": "profile_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/users/{user_id}/profile",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "user_id", "type": "string", "description": "User ID", "required": True, "location": "path"},
                ],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {"user_id": "42"})
        parsed = json.loads(result)

        assert mock_route.called
        assert parsed == {"name": "Alice"}


class TestValidationInExecute:
    """Validation errors are returned before any HTTP call is made."""

    @pytest.mark.asyncio
    async def test_missing_url_returns_error(self):
        tool_def = {
            "name": "broken_tool",
            "tool_type": "api",
            "config": {
                "url": "",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "configuration"

    @pytest.mark.asyncio
    async def test_missing_auth_token_returns_error(self):
        tool_def = {
            "name": "notoken_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/data",
                "method": "GET",
                "headers": {},
                "parameters": [],
                "body_template": None,
                "auth": {"type": "api_key", "token": "", "header": "key", "location": "query"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "authentication"

    @pytest.mark.asyncio
    async def test_missing_required_param_returns_error(self):
        tool_def = {
            "name": "param_tool",
            "tool_type": "api",
            "config": {
                "url": "https://api.example.com/v1/data",
                "method": "GET",
                "headers": {},
                "parameters": [
                    {"name": "query", "type": "string", "required": True, "location": "query"},
                ],
                "body_template": None,
                "auth": {"type": "none"},
            },
        }

        result = await ToolExecutor._execute_api(tool_def, {})
        parsed = json.loads(result)
        assert parsed["error_type"] == "parameters"
        assert "query" in parsed["missing_parameters"]

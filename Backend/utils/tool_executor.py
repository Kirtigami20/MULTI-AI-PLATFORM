"""
Generic Tool Executor for API tools.

Reads tool configuration from MongoDB and constructs the correct HTTP request
for ANY REST API. No API-specific code — the executor simply reads the stored
configuration (URL, method, parameters, authentication) and builds the request
dynamically.

Supports:
- Authentication: None, API Key (header/query), Bearer Token, Basic Auth
- Methods: GET, POST, PUT, PATCH, DELETE
- Parameter locations: query, path, header, body
- Body templates with placeholder substitution
- Runtime diagnostic logging (secrets masked)
- Structured error responses
"""

import json
import logging
import base64
import httpx
from utils.builtin_tools import (
    get_builtin_tool,
    is_builtin_tool,
    get_builtin_openai_schema,
    execute_builtin_tool,
)
from utils.logger import PipelineLogger, StageTimer

logger = logging.getLogger("tool_executor")


PYTHON_TYPE_MAP = {
    "string": "string",
    "number": "number",
    "integer": "integer",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
}

# HTTP status codes that indicate specific, actionable errors
HTTP_ERROR_MESSAGES = {
    401: "Authentication failed. Check your API key or token.",
    403: "Access forbidden. Your credentials lack permission for this resource.",
    404: "Resource not found. Verify the API URL is correct.",
    429: "Rate limit exceeded. Try again later.",
    500: "Internal server error on the API side.",
    502: "Bad gateway. The API server may be down.",
    503: "Service unavailable. The API server is temporarily overloaded.",
}


class ToolExecutor:
    """Generic executor for built-in and API tools."""

    # -------------------------------------------------------------------
    # OpenAI schema generation (unchanged)
    # -------------------------------------------------------------------

    @staticmethod
    def generate_openai_schema(name: str, description: str, parameters: list[dict]) -> dict:
        """Generate an OpenAI function-calling schema from parameter definitions."""
        properties = {}
        required = []

        for p in parameters:
            prop = {
                "type": PYTHON_TYPE_MAP.get(p.get("type", "string"), "string"),
                "description": p.get("description", ""),
            }
            properties[p["name"]] = prop
            if p.get("required", False):
                required.append(p["name"])

        schema = {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
            },
        }
        if required:
            schema["parameters"]["required"] = required

        return schema

    @staticmethod
    def get_openai_tools(tools: list[dict]) -> list[dict]:
        """Convert tool definitions into OpenAI function-calling tool schemas."""
        openai_tools = []
        for tool in tools:
            tool_type = tool.get("tool_type", "builtin")
            name = tool.get("name", "")
            description = tool.get("description", "")

            if tool_type == "builtin":
                schema = get_builtin_openai_schema(name)
                if schema:
                    if description:
                        schema["description"] = description
                    openai_tools.append({
                        "type": "function",
                        "function": schema,
                    })

            elif tool_type == "api":
                config = tool.get("config", {})
                existing_schema = config.get("schema", {})
                params = config.get("parameters", [])

                if existing_schema and existing_schema.get("name"):
                    openai_tools.append({
                        "type": "function",
                        "function": existing_schema,
                    })
                elif params:
                    schema = ToolExecutor.generate_openai_schema(
                        name, description, params
                    )
                    openai_tools.append({
                        "type": "function",
                        "function": schema,
                    })

        return openai_tools

    # -------------------------------------------------------------------
    # Tool dispatch
    # -------------------------------------------------------------------

    @staticmethod
    async def execute(tool_name: str, arguments: dict, tools: list[dict]) -> str:
        """Execute a tool by name, dispatching to built-in or API handler."""
        tool_def = None
        for t in tools:
            if t.get("name") == tool_name:
                tool_def = t
                break

        if not tool_def:
            return json.dumps({"error": f"Tool '{tool_name}' not found"})

        tool_type = tool_def.get("tool_type", "builtin")

        if tool_type == "builtin":
            return await execute_builtin_tool(tool_name, arguments)
        elif tool_type == "api":
            return await ToolExecutor._execute_api(tool_def, arguments)
        else:
            return json.dumps({"error": f"Unknown tool type: {tool_type}"})

    # -------------------------------------------------------------------
    # Authentication (generic, config-driven)
    # -------------------------------------------------------------------

    @staticmethod 
    def _build_auth(auth: dict) -> dict:
        """
        Build authentication headers, query params, and body params from the stored config.

        Reads exactly the field names stored by the Tool Builder frontend:
          - auth.type      → "none" | "api_key" | "bearer" | "basic"
          - auth.token     → the secret key / password value
          - auth.header    → the key name (e.g. "X-API-Key", "api_token")
          - auth.location  → "header" | "query" | "body"  (only for api_key)
          - auth.username  → username (only for basic)

        Returns: {"headers": {...}, "query": {...}, "body": {...}}
        """
        if not auth:
            return {"headers": {}, "query": {}, "body": {}}

        auth_type = auth.get("type", "none")
        token = auth.get("token", "")
        username = auth.get("username", "")

        if auth_type == "none" or not token:
            return {"headers": {}, "query": {}, "body": {}}

        elif auth_type == "bearer":
            return {"headers": {"Authorization": f"Bearer {token}"}, "query": {}, "body": {}}

        elif auth_type == "api_key":
            location = auth.get("location", "header")
            key_name = auth.get("header", "X-API-Key")
            if location == "query":
                return {"headers": {}, "query": {key_name: token}, "body": {}}
            elif location == "body":
                return {"headers": {}, "query": {}, "body": {key_name: token}}
            return {"headers": {key_name: token}, "query": {}, "body": {}}

        elif auth_type == "basic":
            credentials = base64.b64encode(f"{username}:{token}".encode()).decode()
            return {"headers": {"Authorization": f"Basic {credentials}"}, "query": {}, "body": {}}

        return {"headers": {}, "query": {}, "body": {}}

    # -------------------------------------------------------------------
    # Parameter routing
    # -------------------------------------------------------------------

    @staticmethod
    def _build_request_params(
        arguments: dict, parameters: list[dict], body_template, auth: dict
    ) -> dict:
        """
        Route LLM arguments to their correct HTTP locations based on
        the parameter definitions stored in the tool config.

        Each parameter has a 'location' field: "query", "path", "header", or "body".
        Authentication query/header/body params are merged in — never overwritten.
        """
        query_params = {}
        path_values = {}
        header_params = {}
        body_params = {}

        param_location_map = {}
        for p in parameters:
            param_location_map[p["name"]] = p.get("location", "body")

        for key, value in arguments.items():
            location = param_location_map.get(key, "body")
            if location == "query":
                query_params[key] = value
            elif location == "path":
                path_values[key] = value
            elif location == "header":
                header_params[key] = str(value)
            else:
                body_params[key] = value

        auth_result = ToolExecutor._build_auth(auth)
        auth_headers = auth_result.get("headers", {})
        auth_query = auth_result.get("query", {})
        auth_body = auth_result.get("body", {})

        # Merge: user query/body params first, then auth params.
        # Auth params take precedence to prevent accidental override.
        query = {**query_params, **auth_query}
        body = {**body_params, **auth_body}

        return {
            "query": query,
            "path_values": path_values,
            "header_params": header_params,
            "body_params": body,
            "auth_headers": auth_headers,
        }

    # -------------------------------------------------------------------
    # Body construction
    # -------------------------------------------------------------------

    @staticmethod
    def _build_body(body_params: dict, body_template) -> str:
        """
        Build the request body from parameters and an optional template.

        If a body_template is provided, substitute {param_name} placeholders.
        Otherwise, serialize body_params as JSON.
        """
        if body_template and isinstance(body_template, str):
            body = body_template
            for key, value in body_params.items():
                body = body.replace(
                    f"{{{key}}}", json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                )
            return body

        if body_params:
            return json.dumps(body_params)

        return ""

    # -------------------------------------------------------------------
    # Request validation
    # -------------------------------------------------------------------

    @staticmethod
    def _validate_request(tool_def: dict, arguments: dict) -> dict | None:
        """
        Validate the tool configuration and arguments before sending the request.

        Returns None if valid, or a structured error dict if invalid.
        """
        config = tool_def.get("config", {})
        url = config.get("url", "")
        parameters = config.get("parameters", [])
        auth = config.get("auth", {"type": "none"})

        # Validate URL is configured
        if not url:
            return {"error": "Tool API URL not configured", "error_type": "configuration"}

        # Validate authentication token is present when required
        auth_type = auth.get("type", "none")
        if auth_type != "none":
            token = auth.get("token", "")
            if not token:
                return {
                    "error": f"Authentication type '{auth_type}' is configured but no token/key value is provided. "
                             f"Edit the tool and add your API key.",
                    "error_type": "authentication",
                }
            if auth_type == "basic" and not auth.get("username", ""):
                return {
                    "error": "Basic authentication requires a username.",
                    "error_type": "authentication",
                }

        # Validate required parameters are present
        missing = []
        for p in parameters:
            if p.get("required", False) and p["name"] not in arguments:
                missing.append(p["name"])

        if missing:
            return {
                "error": f"Missing required parameters: {', '.join(missing)}",
                "error_type": "parameters",
                "missing_parameters": missing,
            }

        return None

    # -------------------------------------------------------------------
    # Diagnostic logging
    # -------------------------------------------------------------------

    @staticmethod
    def _mask_secret(value: str) -> str:
        """Mask a secret value, showing only the last 4 characters."""
        if not value or len(value) <= 4:
            return "****"
        return "*" * (len(value) - 4) + value[-4:]

    @staticmethod
    def _log_request(
        tool_name: str,
        method: str,
        url: str,
        headers: dict,
        query: dict,
        body: str | None,
        auth: dict,
    ):
        """Log diagnostic block via PipelineLogger before executing the HTTP request."""
        PipelineLogger.log_stage_8_http_request(
            tool_name=tool_name,
            method=method,
            url=url,
            headers=headers,
            query=query,
            body=body,
            auth_info=auth,
        )

    @staticmethod
    def _log_response(tool_name: str, status_code: int, duration_ms: float, body: str):
        """Log response block via PipelineLogger after receiving HTTP response."""
        PipelineLogger.log_stage_8_http_response(
            tool_name=tool_name,
            status_code=status_code,
            duration_ms=duration_ms,
            response_body=body,
        )

    # -------------------------------------------------------------------
    # Error response builder
    # -------------------------------------------------------------------

    @staticmethod
    def _build_error_response(
        error_type: str,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ) -> str:
        """Build a structured JSON error response."""
        error = {
            "error": message,
            "error_type": error_type,
        }
        if status_code is not None:
            error["status_code"] = status_code
        if response_body:
            try:
                error["api_response"] = json.loads(response_body)
            except (json.JSONDecodeError, TypeError):
                error["api_response"] = response_body[:500] if response_body else ""
        return json.dumps(error)

    # -------------------------------------------------------------------
    # Core API execution (generic, config-driven)
    # -------------------------------------------------------------------

    @staticmethod
    async def _execute_api(tool_def: dict, arguments: dict) -> str:
        """
        Execute an API tool call by reading entirely from the stored config.
        """
        tool_name = tool_def.get("name", "unknown")
        config = tool_def.get("config", {})
        url = config.get("url", "")
        method = config.get("method", "POST").upper()
        static_headers = config.get("headers", {})
        parameters = config.get("parameters", [])
        body_template = config.get("body_template", None)
        auth = config.get("auth", {"type": "none"})

        # --- Stage 7: Validate & Log ---
        validation_error = ToolExecutor._validate_request(tool_def, arguments)
        if validation_error:
            PipelineLogger.log_stage_7_tool_validation(
                tool_name=tool_name,
                arguments=arguments,
                is_valid=False,
                error_msg=validation_error.get("error", "Validation failed"),
            )
            return json.dumps(validation_error)

        PipelineLogger.log_stage_7_tool_validation(
            tool_name=tool_name,
            arguments=arguments,
            is_valid=True,
        )

        # --- Route arguments to locations ---
        params = ToolExecutor._build_request_params(
            arguments, parameters, body_template, auth
        )

        # --- Build URL with path params ---
        url_with_path = url
        for key, value in params["path_values"].items():
            url_with_path = url_with_path.replace(f"{{{key}}}", str(value))

        # --- Merge all headers ---
        all_headers = {**static_headers, **params["auth_headers"], **params["header_params"]}

        # --- Build query and body based on method ---
        body = None
        body_str = ""

        if method == "GET":
            query = dict(params["query"])
            has_routed_user_params = any(
                p.get("location") == "query" for p in parameters
            )
            if not has_routed_user_params:
                for key, value in arguments.items():
                    if key not in query:
                        query[key] = value
            for key, value in params["body_params"].items():
                if key not in query:
                    query[key] = value

        elif method in ("POST", "PUT", "PATCH"):
            body_str = ToolExecutor._build_body(params["body_params"], body_template)
            if body_str:
                all_headers.setdefault("Content-Type", "application/json")
            body = body_str.encode("utf-8") if body_str else None
            query = params["query"]

        elif method == "DELETE":
            query = params["query"]

        else:
            body_str = ToolExecutor._build_body(params["body_params"], body_template)
            body = body_str.encode("utf-8") if body_str else None
            query = params["query"]

        # --- Stage 8: Log HTTP Request ---
        ToolExecutor._log_request(
            tool_name=tool_name,
            method=method,
            url=url_with_path,
            headers=all_headers,
            query=query,
            body=body_str if body_str else None,
            auth=auth,
        )

        # --- Stage 8: Execute HTTP request with timing ---
        try:
            with StageTimer() as timer:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.request(
                        method,
                        url_with_path,
                        params=query if query else None,
                        headers=all_headers if all_headers else None,
                        content=body,
                    )

            # Log Stage 8 HTTP Response
            ToolExecutor._log_response(
                tool_name=tool_name,
                status_code=response.status_code,
                duration_ms=timer.duration_ms,
                body=response.text,
            )

            # Handle HTTP errors
            if response.status_code >= 400:
                error_message = HTTP_ERROR_MESSAGES.get(
                    response.status_code,
                    f"HTTP {response.status_code} error from API.",
                )
                return ToolExecutor._build_error_response(
                    error_type="http_error",
                    message=error_message,
                    status_code=response.status_code,
                    response_body=response.text,
                )

            return response.text

        except httpx.TimeoutException as e:
            PipelineLogger.log_pipeline_error(f"HTTP_TIMEOUT_{tool_name}", e)
            return ToolExecutor._build_error_response(
                error_type="timeout",
                message="Request timed out after 30 seconds. The API may be slow or unreachable.",
            )
        except httpx.ConnectError as e:
            PipelineLogger.log_pipeline_error(f"HTTP_CONNECT_ERROR_{tool_name}", e)
            return ToolExecutor._build_error_response(
                error_type="connection_error",
                message=f"Could not connect to {url_with_path}. Check the URL and your network.",
            )
        except Exception as e:
            PipelineLogger.log_pipeline_error(f"HTTP_EXECUTION_ERROR_{tool_name}", e)
            return ToolExecutor._build_error_response(
                error_type="request_error",
                message=str(e),
            )

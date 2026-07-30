"""
Structured Pipeline Logger.

Provides end-to-end tracing and timing for every stage of the AI Agent execution pipeline:
  Stage 1: Chat Request Intake
  Stage 2: Agent Configuration Loading
  Stage 3: Tool Definition Resolution
  Stage 4: LLM Engine Initialization
  Stage 5: LLM API Request Transmission
  Stage 6: LLM API Response Reception
  Stage 7: Tool Argument Validation
  Stage 8: HTTP API Tool Request / Response
  Stage 9: Execution Completion

Features:
- Asynchronous context tracking via `contextvars.ContextVar("request_id")`
- Stage timing tracking in milliseconds (`duration_ms`)
- Automatic secret masking (API keys, tokens, passwords, secrets)
- Exception stack trace capture (`traceback.format_exc()`)
"""

import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar
from typing import Any, Optional

# Context variable for tracking request ID across async coroutines
request_id_var: ContextVar[str] = ContextVar("request_id", default="req-unknown")

logger = logging.getLogger("agent_pipeline")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.set_Formatter if hasattr(handler, "set_Formatter") else handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def set_request_id(req_id: Optional[str] = None) -> str:
    """Set or generate a unique request ID for the current async context."""
    if not req_id:
        req_id = f"req-{uuid.uuid4().hex[:8]}"
    request_id_var.set(req_id)
    return req_id


def get_request_id() -> str:
    """Get the active request ID for the current context."""
    return request_id_var.get()


def mask_secret(value: Any) -> str:
    """Mask a secret string showing only the last 4 characters."""
    if not value:
        return "****"
    val_str = str(value)
    if len(val_str) <= 4:
        return "****"
    return "*" * (len(val_str) - 4) + val_str[-4:]


def mask_dict(data: dict) -> dict:
    """Recursively mask sensitive keys in a dictionary."""
    if not isinstance(data, dict):
        return data

    sensitive_keys = {
        "authorization", "api_key", "token", "password", "secret",
        "api_token", "key", "x-api-key", "groq_api_key", "jwt_secret",
        "smtp_password", "bearer"
    }

    masked = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(s in k_lower for s in sensitive_keys):
            masked[k] = mask_secret(v)
        elif isinstance(v, dict):
            masked[k] = mask_dict(v)
        elif isinstance(v, list):
            masked[k] = [mask_dict(item) if isinstance(item, dict) else item for item in v]
        else:
            masked[k] = v
    return masked


class StageTimer:
    """Context manager for measuring stage execution duration in milliseconds."""

    def __init__(self):
        self.start_time = 0.0
        self.duration_ms = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = round((time.perf_counter() - self.start_time) * 1000, 2)


class PipelineLogger:
    """Structured logging facade for all pipeline stages."""

    @staticmethod
    def _format_header(stage: str, title: str, request_id: Optional[str] = None) -> str:
        req_id = request_id or get_request_id()
        return f"[{req_id}] [{stage}] {title}"

    @staticmethod
    def log_stage_1_request(agent_id: str, user_id: str, message: str, request_id: str):
        """Stage 1: Chat request intake."""
        header = PipelineLogger._format_header("STAGE 1: INTAKE", "Chat Request Received", request_id)
        msg_preview = message if len(message) <= 150 else message[:150] + "..."
        details = f"Agent ID: {agent_id} | User ID: {user_id} | Message: '{msg_preview}'"
        print(f"\n{'='*70}\n{header}\n{details}\n{'='*70}")

    @staticmethod
    def log_stage_2_agent_loaded(agent: dict, duration_ms: float):
        """Stage 2: Agent loaded from database."""
        header = PipelineLogger._format_header("STAGE 2: AGENT_LOADED", f"Agent Config Retrieved ({duration_ms} ms)")
        info = {
            "name": agent.get("name", "Unnamed"),
            "role": agent.get("role", "Assistant"),
            "engine": agent.get("engine", "langchain"),
            "model_name": agent.get("model_name", "default"),
            "status": agent.get("status", "unknown"),
            "tool_count": len(agent.get("tool_ids", [])),
        }
        print(f"{header}\n  -> Config: {json.dumps(info)}")

    @staticmethod
    def log_stage_3_tools_loaded(tools: list[dict], duration_ms: float):
        """Stage 3: Tools resolved from database."""
        header = PipelineLogger._format_header("STAGE 3: TOOLS_LOADED", f"Tools Resolved ({duration_ms} ms)")
        tool_summary = [
            {"id": t.get("id"), "name": t.get("name"), "type": t.get("tool_type")}
            for t in tools
        ]
        print(f"{header}\n  -> Resolved {len(tools)} Tool(s): {json.dumps(tool_summary)}")

    @staticmethod
    def log_stage_4_engine_init(engine_name: str, model_name: str):
        """Stage 4: Engine initialized."""
        header = PipelineLogger._format_header("STAGE 4: ENGINE_INIT", f"Initializing Engine: {engine_name}")
        print(f"{header}\n  -> Model: {model_name}")

    @staticmethod
    def log_stage_5_llm_request(engine_name: str, model_name: str, iteration: int, payload_summary: dict):
        """Stage 5: Sending request to LLM."""
        header = PipelineLogger._format_header("STAGE 5: LLM_REQUEST", f"Sending Request to LLM (Iteration #{iteration})")
        summary = {
            "engine": engine_name,
            "model": model_name,
            "messages_count": payload_summary.get("messages_count", 0),
            "tools_count": payload_summary.get("tools_count", 0),
            "tool_names": payload_summary.get("tool_names", []),
        }
        print(f"\n  {header}\n    Request Info: {json.dumps(summary)}")

    @staticmethod
    def log_stage_6_llm_response(engine_name: str, duration_ms: float, tokens_used: int, tool_calls_count: int, content_preview: str):
        """Stage 6: Received response from LLM."""
        header = PipelineLogger._format_header("STAGE 6: LLM_RESPONSE", f"LLM Response Received ({duration_ms} ms)")
        preview = content_preview[:120] + "..." if len(content_preview) > 120 else content_preview
        print(f"  {header}\n    Tokens: {tokens_used} | Tool Calls Generated: {tool_calls_count} | Response: '{preview}'")

    @staticmethod
    def log_stage_7_tool_validation(tool_name: str, arguments: dict, is_valid: bool, error_msg: str = ""):
        """Stage 7: Tool parameter validation."""
        header = PipelineLogger._format_header("STAGE 7: TOOL_VALIDATION", f"Validating Tool: {tool_name}")
        status = "PASSED" if is_valid else f"FAILED ({error_msg})"
        masked_args = mask_dict(arguments)
        print(f"  {header}\n    Arguments: {json.dumps(masked_args)} | Validation: {status}")

    @staticmethod
    def log_stage_8_http_request(tool_name: str, method: str, url: str, headers: dict, query: dict, body: Optional[str], auth_info: dict):
        """Stage 8: Transmitting HTTP request for API tool."""
        header = PipelineLogger._format_header("STAGE 8: HTTP_REQUEST", f"Transmitting HTTP Call for Tool: {tool_name}")
        masked_headers = mask_dict(headers)
        masked_query = mask_dict(query)
        auth_summary = {
            "type": auth_info.get("type", "none"),
            "location": auth_info.get("location", "n/a"),
            "key_name": auth_info.get("header", "n/a"),
        }
        print(
            f"  {header}\n"
            f"    Method & URL: {method} {url}\n"
            f"    Headers: {json.dumps(masked_headers)}\n"
            f"    Query: {json.dumps(masked_query)}\n"
            f"    Body: {body if body else '(none)'}\n"
            f"    Auth: {json.dumps(auth_summary)}"
        )

    @staticmethod
    def log_stage_8_http_response(tool_name: str, status_code: int, duration_ms: float, response_body: str):
        """Stage 8: Received HTTP response for API tool."""
        header = PipelineLogger._format_header("STAGE 8: HTTP_RESPONSE", f"HTTP Call Completed ({duration_ms} ms)")
        preview = response_body[:200] + "..." if len(response_body) > 200 else response_body
        print(f"  {header}\n    Tool: {tool_name} | HTTP Status: {status_code} | Body Preview: '{preview}'")

    @staticmethod
    def log_stage_9_complete(total_duration_ms: float, tokens_used: int, tool_calls_executed: int):
        """Stage 9: Pipeline execution complete."""
        header = PipelineLogger._format_header("STAGE 9: COMPLETE", f"Pipeline Execution Finished ({total_duration_ms} ms)")
        summary = f"Total Tokens: {tokens_used} | Total Tool Executions: {tool_calls_executed}"
        print(f"\n{header}\n{summary}\n{'='*70}\n")

    @staticmethod
    def log_pipeline_error(stage_name: str, exception: Exception):
        """Log pipeline errors with stage context and full stack trace."""
        req_id = get_request_id()
        header = f"[{req_id}] [ERROR: {stage_name}] Execution Failure Detected"
        tb = traceback.format_exc()
        print(
            f"\n{'!'*70}\n"
            f"{header}\n"
            f"  Exception Type: {type(exception).__name__}\n"
            f"  Exception Msg:  {str(exception)}\n"
            f"  Full Stack Trace:\n{tb}"
            f"{'!'*70}\n"
        )

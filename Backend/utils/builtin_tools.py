"""
Centralized Built-in Tool Registry.

To add a new built-in tool:
1. Define the handler function (async, returns JSON string)
2. Add an entry to BUILTIN_TOOLS with name, description, parameters, and handler

No other code changes required.
"""

import json
import re
import httpx
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------

async def handle_web_search(query: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json"},
            )
            data = resp.json()
            abstract = data.get("AbstractText", "")
            if abstract:
                return json.dumps({"result": abstract})
            topics = data.get("RelatedTopics", [])[:3]
            texts = [t.get("Text", "") for t in topics if t.get("Text")]
            return json.dumps({"results": texts}) if texts else json.dumps({"result": "No results found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_calculator(expression: str) -> str:
    safe = re.sub(r"[^0-9+\-*/().%\s]", "", expression)
    if not safe:
        return json.dumps({"error": "Invalid expression"})
    try:
        result = eval(safe, {"__builtins__": {}}, {})
        return json.dumps({"result": result})
    except Exception as e:
        return json.dumps({"error": str(e)})


def handle_current_date() -> str:
    now = datetime.now(timezone.utc)
    return json.dumps({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
    })


async def handle_send_email(to: str, subject: str, body: str) -> str:
    import smtplib
    from email.mime.text import MIMEText
    from config import settings

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        return json.dumps({"error": "SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env"})

    msg = MIMEText(body)
    msg["From"] = settings.SMTP_USERNAME
    msg["To"] = to
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return json.dumps({"status": "success", "message": "Email sent successfully"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILTIN_TOOLS = {
    "web_search": {
        "name": "web_search",
        "description": "Search the web for current information on a given topic.",
        "parameters": [
            {
                "name": "query",
                "type": "string",
                "description": "The search query",
                "required": True,
            }
        ],
        "handler": handle_web_search,
        "async": True,
    },
    "calculator": {
        "name": "calculator",
        "description": "Evaluate a mathematical expression.",
        "parameters": [
            {
                "name": "expression",
                "type": "string",
                "description": "The math expression to evaluate, e.g. '2 + 2 * 3'",
                "required": True,
            }
        ],
        "handler": handle_calculator,
        "async": False,
    },
    "current_date": {
        "name": "current_date",
        "description": "Get the current date, time, and day of the week.",
        "parameters": [],
        "handler": handle_current_date,
        "async": False,
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email via Gmail SMTP.",
        "parameters": [
            {
                "name": "to",
                "type": "string",
                "description": "Recipient email address",
                "required": True,
            },
            {
                "name": "subject",
                "type": "string",
                "description": "Email subject line",
                "required": True,
            },
            {
                "name": "body",
                "type": "string",
                "description": "Email body text",
                "required": True,
            },
        ],
        "handler": handle_send_email,
        "async": True,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_builtin_tool(name: str) -> dict | None:
    return BUILTIN_TOOLS.get(name)


def list_builtin_tool_names() -> list[str]:
    return list(BUILTIN_TOOLS.keys())


def is_builtin_tool(name: str) -> bool:
    return name in BUILTIN_TOOLS


def get_builtin_openai_schema(name: str) -> dict | None:
    tool = BUILTIN_TOOLS.get(name)
    if not tool:
        return None

    properties = {}
    required = []
    for p in tool["parameters"]:
        ptype = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
        }.get(p["type"], "string")
        properties[p["name"]] = {
            "type": ptype,
            "description": p.get("description", ""),
        }
        if p.get("required"):
            required.append(p["name"])

    schema = {
        "name": tool["name"],
        "description": tool["description"],
        "parameters": {
            "type": "object",
            "properties": properties,
        },
    }
    if required:
        schema["parameters"]["required"] = required

    return schema


async def execute_builtin_tool(name: str, arguments: dict) -> str:
    tool = BUILTIN_TOOLS.get(name)
    if not tool:
        return json.dumps({"error": f"Unknown built-in tool: {name}"})

    handler = tool["handler"]
    params = tool["parameters"]

    filtered_args = {}
    for p in params:
        pname = p["name"]
        if pname in arguments:
            filtered_args[pname] = arguments[pname]

    if tool.get("async"):
        return await handler(**filtered_args)
    else:
        return handler(**filtered_args)

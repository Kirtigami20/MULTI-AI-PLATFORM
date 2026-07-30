import datetime


def build_system_prompt(
    role: str,
    goal: str,
    instructions: str,
    custom_prompt: str = "",
) -> str:
    today = datetime.date.today().isoformat()

    parts = [
        f"You are {role}.",
        f"Your goal is: {goal}",
        "",
        "## Instructions",
        instructions,
        "",
        "## Tool Usage Guidelines",
        "- **Tool Selection**: Use tools ONLY when they are necessary to fulfill the request.",
        "- **Do NOT Call Tools**: For greetings, expressing thanks/gratitude, casual conversation/chit-chat, or general logical reasoning that does not require live/current external facts.",
        "- **Use Tools**: For requests involving live/current/real-time data (e.g., news, weather, stock prices, exchange rates).",
        "- **Knowledge Base Context**: Use the provided 'Knowledge Base Context' (if present) for questions about internal documentation or custom knowledge base facts.",
        "- **Internal Reasoning**: Use your own pre-trained knowledge and reasoning when neither external tools nor the Knowledge Base Context are required.",
    ]

    if custom_prompt:
        parts.extend(["", "## Additional Context", custom_prompt])

    parts.extend([
        "",
        f"Today's date is {today}.",
        "Be helpful, accurate, and concise.",
    ])

    return "\n".join(parts)

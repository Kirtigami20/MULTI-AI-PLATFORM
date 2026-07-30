DEFAULT_MODEL = "llama-3.3-70b-versatile"
MAX_TOOL_ITERATIONS = 5
DEFAULT_MAX_TOKENS = 2000
DEFAULT_WINDOW_SIZE = 10

MODEL_DISPLAY_NAMES = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B",
    "llama-3.1-8b-instant": "Llama 3.1 8B (Fast)",
    "llama-3.1-70b-versatile": "Llama 3.1 70B",
    "mixtral-8x7b-32768": "Mixtral 8x7B",
}

BLOCKED_TOPICS_RESPONSE = "I'm unable to discuss that topic. Please ask something else."
GUARDRAILS_EXCEEDED_RESPONSE = "Your request has been flagged by the configured guardrails. Please rephrase."

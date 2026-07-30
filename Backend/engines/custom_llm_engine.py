import json
from collections import deque
import openai
from config import settings
from engines.base import BaseEngine, EngineMessage, EngineResponse, ToolCall, ToolResult
from prompts.system import build_system_prompt
from prompts.rag import format_rag_context
from utils.constants import DEFAULT_MODEL, MAX_TOOL_ITERATIONS
from utils.tool_executor import ToolExecutor
from utils.logger import PipelineLogger, StageTimer


class CustomLLMEngine(BaseEngine):

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = openai.AsyncOpenAI(
                api_key="ollama",
                base_url=settings.OLLAMA_BASE_URL,
            )
        return self._client

    async def chat(
        self,
        agent_config: dict,
        messages: list[EngineMessage],
        rag_context: str = "",
        available_tools: list[dict] = None,
    ) -> EngineResponse:
        model_name = agent_config.get("model_name", DEFAULT_MODEL)
        memory_window = agent_config.get("memory", {}).get("window_size", 10)
        guardrails = agent_config.get("guardrails", {})
        tools = available_tools or []

        system_text = build_system_prompt(
            role=agent_config.get("role", "Assistant"),
            goal=agent_config.get("goal", ""),
            instructions=agent_config.get("instructions", ""),
            custom_prompt=agent_config.get("system_prompt", ""),
        )

        formatted_rag = format_rag_context(
            self._parse_rag_context(rag_context) if isinstance(rag_context, list) else []
        )

        if rag_context and not formatted_rag.startswith("No relevant"):
            system_text += (
                "\n\n## Knowledge Base Context\n"
                "Use the following context to answer the user's question when relevant.\n\n"
                f"{formatted_rag}"
            )

        history = self._build_history(messages, memory_window)

        api_messages = [{"role": "system", "content": system_text}]
        api_messages.extend(history)

        openai_tools = ToolExecutor.get_openai_tools(tools) if tools else None

        # === DEBUG: Print tool schemas ===
        print(f"\n{'='*60}")
        print(f"DEBUG TOOL SCHEMAS — {len(openai_tools) if openai_tools else 0} tools")
        print(f"{'='*60}")
        if openai_tools:
            for t in openai_tools:
                print(json.dumps(t, indent=2))
        else:
            print("  (no tools)")
        print(f"{'='*60}\n")

        # === DEBUG: Print all messages ===
        print(f"\n{'='*60}")
        print(f"DEBUG ALL MESSAGES — {len(api_messages)} messages")
        print(f"{'='*60}")
        for i, msg in enumerate(api_messages):
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))
            has_tools = "tool_calls" in msg
            print(f"  [{i}] role={role} has_tool_calls={has_tools}")
            print(f"       content (first 300 chars): {content[:300]}")
            if has_tools:
                print(f"       tool_calls: {json.dumps(msg['tool_calls'], indent=2)[:500]}")
        print(f"{'='*60}\n")

        all_tool_calls_executed = []
        all_tool_results = []

        for iteration in range(1, MAX_TOOL_ITERATIONS + 1):
            kwargs = {
                "model": model_name,
                "messages": api_messages,
            }

            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            # === DEBUG: Print full API payload (without messages) ===
            print(f"\n{'='*60}")
            print(f"DEBUG API PAYLOAD — iteration {iteration}")
            print(f"{'='*60}")
            print(f"  model: {kwargs.get('model')}")
            print(f"  messages count: {len(kwargs.get('messages', []))}")
            print(f"  tools count: {len(kwargs.get('tools', []))}")
            print(f"  tool_choice: {kwargs.get('tool_choice', 'NOT SET')}")
            if kwargs.get("tools"):
                print(f"  tool names: {[t['function']['name'] for t in kwargs['tools']]}")
            print(f"{'='*60}\n")

            # --- Stage 5: LLM Request Logging ---
            PipelineLogger.log_stage_5_llm_request(
                engine_name="custom_llm",
                model_name=model_name,
                iteration=iteration,
                payload_summary={
                    "messages_count": len(api_messages),
                    "tools_count": len(openai_tools) if openai_tools else 0,
                    "tool_names": [t.get("name") for t in tools],
                },
            )

            # --- Stage 6: LLM Response Timing & Logging ---
            try:
                with StageTimer() as timer:
                    response = await self.client.chat.completions.create(**kwargs)
            except Exception as e:
                PipelineLogger.log_pipeline_error("LLM_API_CALL", e)
                return EngineResponse(
                    content=f"LLM API error: {str(e)}",
                    model=model_name,
                )

            choice = response.choices[0]
            assistant_message = choice.message
            tokens_used = response.usage.total_tokens if response.usage else 0
            tool_calls_count = len(assistant_message.tool_calls) if assistant_message.tool_calls else 0

            # === DEBUG: Print LLM response ===
            print(f"\n{'='*60}")
            print(f"DEBUG LLM RESPONSE — iteration {iteration}")
            print(f"{'='*60}")
            print(f"  content: {(assistant_message.content or '(empty)')[:500]}")
            print(f"  tool_calls count: {tool_calls_count}")
            if assistant_message.tool_calls:
                for tc in assistant_message.tool_calls:
                    print(f"    tool: {tc.function.name}")
                    print(f"    args: {tc.function.arguments[:500]}")
            print(f"  tokens_used: {tokens_used}")
            print(f"{'='*60}\n")

            PipelineLogger.log_stage_6_llm_response(
                engine_name="custom_llm",
                duration_ms=timer.duration_ms,
                tokens_used=tokens_used,
                tool_calls_count=tool_calls_count,
                content_preview=assistant_message.content or "(tool call generated)",
            )

            if assistant_message.tool_calls:
                api_messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                })

                for tc in assistant_message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    result_str = await ToolExecutor.execute(
                        tool_name, tool_args, tools
                    )

                    api_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })

                    tool_call = ToolCall(
                        id=tc.id,
                        name=tool_name,
                        arguments=tool_args,
                    )
                    tool_result = ToolResult(
                        tool_call_id=tc.id,
                        name=tool_name,
                        result=result_str,
                        success=True,
                    )
                    all_tool_calls_executed.append(tool_call)
                    all_tool_results.append(tool_result)

            else:
                output = assistant_message.content or ""

                if guardrails.get("enabled", False):
                    output = self._apply_guardrails(output, guardrails)

                return EngineResponse(
                    content=output,
                    tool_calls=all_tool_calls_executed,
                    tool_results=all_tool_results,
                    tokens_used=tokens_used,
                    model=model_name,
                )

        final_output = "I've completed processing but was unable to generate a final response. Maximum tool iterations reached."

        if guardrails.get("enabled", False):
            final_output = self._apply_guardrails(final_output, guardrails)

        return EngineResponse(
            content=final_output,
            tool_calls=all_tool_calls_executed,
            tool_results=all_tool_results,
            model=model_name,
        )

    def _build_history(self, messages: list[EngineMessage], window_size: int) -> list[dict]:
        if not messages:
            return []

        # Default fallback: windowed history
        recent = messages[-window_size:] if len(messages) > window_size else messages

        # Only apply trimming logic if the last message is from the user
        # and there is at least one assistant message in the history (actual conversation exists)
        if messages[-1].role == "user" and any(msg.role == "assistant" for msg in messages):
            latest_msg = messages[-1]
            latest_user_content = latest_msg.content.strip()

            # Check if the latest user query is a standalone greeting or casual start
            is_greeting = False
            if latest_user_content:
                greetings = {"hi", "hello", "hey", "hola", "greetings", "good morning", "good afternoon", "good evening", "yo", "sup", "howdy"}
                clean_msg = "".join(c for c in latest_user_content.lower() if c.isalnum() or c.isspace()).strip()
                words = clean_msg.split()
                if len(words) <= 2 and any(w in greetings for w in words):
                    is_greeting = True

            # If it is a greeting, prune history to only the latest user message
            if is_greeting:
                recent = [messages[-1]]
            else:
                # Check for topic drift/follow-up indicators
                follow_up_indicators = {
                    "it", "this", "that", "these", "those", "he", "she", "him", "her", "they", "them",
                    "his", "their", "its", "then", "there", "former", "latter", "what about", "how about",
                    "why", "who", "where", "more", "explain", "details", "elaborate", "again"
                }
                
                is_follow_up = False
                if latest_user_content:
                    clean_msg = "".join(c for c in latest_user_content.lower() if c.isalnum() or c.isspace()).strip()
                    words = set(clean_msg.split())
                    if words.intersection(follow_up_indicators) or "what about" in clean_msg or "how about" in clean_msg or "tell me" in clean_msg:
                        is_follow_up = True

                # If not a follow-up and we have history, check for Jaccard overlap of keywords
                if not is_follow_up and len(messages) > 2:
                    stopwords = {"the", "and", "a", "of", "to", "in", "is", "you", "that", "it", "he", "was", "for", "on", "are", "as", "with", "his", "they", "i"}
                    
                    latest_clean = "".join(c for c in latest_user_content.lower() if c.isalnum() or c.isspace()).strip()
                    latest_keywords = {w for w in latest_clean.split() if w not in stopwords and len(w) > 3}
                    
                    older_keywords = set()
                    for msg in messages[:-1]:
                        if msg.role == "user" and msg.content:
                            msg_clean = "".join(c for c in msg.content.lower() if c.isalnum() or c.isspace()).strip()
                            older_keywords.update({w for w in msg_clean.split() if w not in stopwords and len(w) > 3})
                    
                    if latest_keywords and older_keywords and not latest_keywords.intersection(older_keywords):
                        # Topic shift: keep only the latest message to start fresh
                        recent = [messages[-1]]

        history = deque(maxlen=window_size)
        for msg in recent:
            if msg.role in ("user", "assistant"):
                history.append({"role": msg.role, "content": msg.content})
        return list(history)

    @staticmethod
    def _parse_rag_context(rag_context) -> list[dict]:
        if isinstance(rag_context, list):
            return rag_context
        return []

    def _apply_guardrails(self, output: str, guardrails: dict) -> str:
        max_tokens = guardrails.get("max_tokens", 2000)
        blocked_topics = guardrails.get("blocked_topics", [])

        words = output.split()
        if len(words) > max_tokens:
            output = " ".join(words[:max_tokens]) + "..."

        output_lower = output.lower()
        for topic in blocked_topics:
            if topic.lower() in output_lower:
                from utils.constants import BLOCKED_TOPICS_RESPONSE
                return BLOCKED_TOPICS_RESPONSE

        return output

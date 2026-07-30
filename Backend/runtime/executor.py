from bson import ObjectId
from fastapi import HTTPException, status
from database import get_collection
from engines.factory import get_engine
from engines.base import EngineMessage
from services.chat import ChatService
from services.conversation_service import ConversationService
from utils.logger import PipelineLogger, StageTimer


class RuntimeExecutor:

    @staticmethod
    async def execute_chat(
        agent_id: str,
        user_id: str,
        user_message: str,
        conversation_id: str | None = None,
    ) -> dict:
        pipeline_timer = StageTimer()
        pipeline_timer.__enter__()

        try:
            # --- Stage 2: Agent Loading ---
            with StageTimer() as timer:
                agents = get_collection("agents")
                agent = await agents.find_one({"_id": ObjectId(agent_id), "user_id": user_id})

            if not agent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Agent not found",
                )

            if agent.get("status") != "active":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent is not active (status: {agent.get('status')})",
                )

            PipelineLogger.log_stage_2_agent_loaded(agent, timer.duration_ms)

            # --- Conversation Management ---
            is_conversation_mode = conversation_id is not None
            if is_conversation_mode:
                conv = await ConversationService.get_conversation(conversation_id, user_id)
                await ConversationService.save_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_message,
                )
                history = await RuntimeExecutor._get_conversation_history(conversation_id)
            else:
                await ChatService.save_message(
                    agent_id=agent_id,
                    user_id=user_id,
                    role="user",
                    content=user_message,
                )

            if is_conversation_mode:
                limit = agent.get("memory", {}).get("window_size", 10)
                history = history[-limit:] if len(history) > limit else history
            else:
                history = await ChatService.get_messages_as_engine_messages(
                    agent_id=agent_id,
                    user_id=user_id,
                    limit=agent.get("memory", {}).get("window_size", 10),
                )

            rag_context = ChatService.retrieve_rag_context(
                agent_config=agent,
                query=user_message,
            )

            # --- Stage 3: Tool Loading ---
            with StageTimer() as timer:
                tools = await RuntimeExecutor._resolve_tools(agent.get("tool_ids", []))
            PipelineLogger.log_stage_3_tools_loaded(tools, timer.duration_ms)

            # --- Stage 4: Engine Initialization & Dispatch ---
            engine_type = agent.get("engine", "langchain")
            model_name = agent.get("model_name", "llama-3.3-70b-versatile")
            PipelineLogger.log_stage_4_engine_init(engine_type, model_name)

            engine = get_engine(engine_type)

            agent_config = {
                "model_name": model_name,
                "role": agent.get("role", "Assistant"),
                "goal": agent.get("goal", ""),
                "instructions": agent.get("instructions", ""),
                "system_prompt": agent.get("system_prompt", ""),
                "memory": agent.get("memory", {"enabled": True, "window_size": 10}),
                "guardrails": agent.get("guardrails", {
                    "enabled": True,
                    "max_tokens": 2000,
                    "blocked_topics": [],
                    "custom_rules": [],
                }),
            }

            # --- Execute Chat in Engine (Handles Stages 5, 6, 7, 8) ---
            response = await engine.chat(
                agent_config=agent_config,
                messages=history,
                rag_context=rag_context,
                available_tools=tools,
            )

            tool_calls_dicts = [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in response.tool_calls
            ]
            tool_results_dicts = [
                {
                    "tool_call_id": tr.tool_call_id,
                    "name": tr.name,
                    "result": tr.result,
                    "success": tr.success,
                }
                for tr in response.tool_results
            ]

            if is_conversation_mode:
                assistant_msg = await ConversationService.save_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=response.content,
                    tool_calls=tool_calls_dicts,
                    tool_results=tool_results_dicts,
                    tokens_used=response.tokens_used,
                    model=response.model,
                )
                await ConversationService.update_conversation_metadata(
                    conversation_id=conversation_id,
                    last_message=response.content or user_message,
                )
                chat_response = await ChatService.build_chat_response(assistant_msg, agent_id=agent_id)
                chat_response.conversation_id = conversation_id
            else:
                assistant_msg = await ChatService.save_message(
                    agent_id=agent_id,
                    user_id=user_id,
                    role="assistant",
                    content=response.content,
                    tool_calls=tool_calls_dicts,
                    tool_results=tool_results_dicts,
                    tokens_used=response.tokens_used,
                    model=response.model,
                )
                chat_response = await ChatService.build_chat_response(assistant_msg, agent_id=agent_id)

            # --- Stage 9: Pipeline Completion ---
            pipeline_timer.__exit__(None, None, None)
            PipelineLogger.log_stage_9_complete(
                total_duration_ms=pipeline_timer.duration_ms,
                tokens_used=response.tokens_used,
                tool_calls_executed=len(response.tool_calls),
            )

            return chat_response

        except HTTPException:
            raise
        except Exception as e:
            PipelineLogger.log_pipeline_error("RUNTIME_EXECUTOR", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Execution error: {str(e)}",
            )

    @staticmethod
    async def _get_conversation_history(conversation_id: str) -> list:
        from engines.base import EngineMessage
        from repositories.message_repository import MessageRepository

        messages = await MessageRepository.find_by_conversation(conversation_id)
        return [
            EngineMessage(role=m["role"], content=m["content"])
            for m in messages
        ]

    @staticmethod
    async def _resolve_tools(tool_ids: list[str]) -> list[dict]:
        if not tool_ids:
            return []

        tools_col = get_collection("tools")
        resolved = []

        for tool_id in tool_ids:
            try:
                tool = await tools_col.find_one({"_id": ObjectId(tool_id)})
                if tool:
                    resolved.append({
                        "id": str(tool["_id"]),
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "tool_type": tool.get("tool_type", "builtin"),
                        "config": tool.get("config", {}),
                    })
            except Exception:
                continue

        return resolved

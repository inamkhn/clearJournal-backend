"""Message service — CRUD + orchestrator for AI message pipeline."""
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.core.config import settings
from app.core.redis import get_redis
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user_instructions import UserAgentInstruction
from app.schemas.message import MessageCreate, MessageRead
from app.services.ai_service import AgentService, AgentError, OpenAIService
from app.services.guardrails import (
    check_moderation,
    check_topic_relevance,
    sanitize_message,
    check_token_budget,
    check_cost_circuit_breaker,
    record_message_cost,
    run_output_guardrails,
)

logger = logging.getLogger(__name__)


class MessageService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_read(self, message: Message) -> MessageRead:
        return MessageRead(
            id=message.id,
            conversation_id=message.conversation_id,
            user_id=message.user_id,
            content=message.content,
            sender_type=message.sender_type,
            response=message.response,
            prompt_tokens=message.prompt_tokens,
            completion_tokens=message.completion_tokens,
            total_tokens=message.total_tokens,
            model_used=message.model_used,
            response_time_ms=message.response_time_ms,
            tool_calls=message.tool_calls,
            created_at=message.created_at,
        )

    def _verify_conversation_ownership(self, conversation_id: int, user_id: int) -> Conversation:
        """Verify that the conversation belongs to the user, or raise 404."""
        conversation = self.session.exec(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        ).first()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        return conversation

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list_messages(
        self, conversation_id: int, user_id: int, limit: int = 50
    ) -> List[MessageRead]:
        """List messages for a conversation. Verifies ownership."""
        self._verify_conversation_ownership(conversation_id, user_id)

        messages = self.session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        ).all()
        return [self._to_read(m) for m in messages]

    # ── Orchestrator ─────────────────────────────────────────────────────────

    async def create_message(
        self, user_id: int, payload: MessageCreate
    ) -> MessageRead:
        """
        Full pipeline: input guardrails → load context → run agent
        → output guardrails → save message.
        """
        message, redis_client = await self._prepare_message(user_id, payload)
        return self._to_read(message)

    async def create_message_stream(
        self, user_id: int, payload: MessageCreate
    ) -> AsyncGenerator[str, None]:
        """
        Same pipeline as create_message, but streams the response
        word-by-word via SSE events after saving to DB.

        Yields:
            SSE-formatted strings: data: {"token": "..."}\n\n
            Final event: data: [DONE]\n\n
        """
        message, redis_client = await self._prepare_message(user_id, payload)

        # Extract response text from the saved message
        response_data = message.response or {}
        text = response_data.get("text", "")

        # Emit metadata event with message ID and tool calls
        metadata = {
            "message_id": message.id,
            "tool_calls": message.tool_calls or [],
            "model": message.model_used,
            "total_tokens": message.total_tokens,
        }
        yield f"data: {json.dumps(metadata)}\n\n"

        # Stream response word-by-word
        words = text.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else f" {word}"
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Final event
        yield "data: [DONE]\n\n"

    # ── Shared Pipeline ─────────────────────────────────────────────────────

    async def _prepare_message(
        self, user_id: int, payload: MessageCreate
    ) -> Tuple[Message, Any]:
        """
        Shared pipeline: input guardrails → agent → output guardrails
        → save to DB → cost tracking.

        Returns:
            (saved Message, redis_client) — redis_client for downstream cost tracking.
        """
        conversation_id = payload.conversation_id
        content = payload.content

        # ── Layer 1: Input Guardrails ───────────────────────────────────────

        content = sanitize_message(content)
        check_topic_relevance(content)

        openai_client = OpenAIService()
        await check_moderation(content, openai_client.client)

        redis_client = get_redis()
        check_cost_circuit_breaker(redis_client)

        # ── Load Context ────────────────────────────────────────────────────

        conversation = self._verify_conversation_ownership(conversation_id, user_id)
        instruction = self._get_active_instruction(user_id)
        system_prompt = self._build_system_prompt(instruction)
        history = self._load_history(conversation_id, last_n=10)
        messages = history + [{"role": "user", "content": content}]
        check_token_budget(messages)

        # ── Run Agent ───────────────────────────────────────────────────────

        start_time = time.time()
        try:
            agent = AgentService(session=self.session)
            result = await agent.run(
                messages=messages,
                system_prompt=system_prompt,
                user_id=user_id,
            )
        except AgentError as e:
            logger.error("Agent error: %s", e)
            result = {
                "text": "I'm sorry, I encountered an issue processing your request. Please try again.",
                "tool_calls": [],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "model": settings.AGENT_MODEL,
                "finish_reason": "error",
            }
        response_time_ms = int((time.time() - start_time) * 1000)

        # ── Layer 3: Output Guardrails ──────────────────────────────────────

        if result.get("finish_reason") != "error":
            result["text"] = run_output_guardrails(
                response_text=result["text"],
                tool_results=result.get("tool_results", []),
            )

        # ── Save to Database ────────────────────────────────────────────────

        usage = result.get("usage", {})
        message = Message(
            conversation_id=conversation_id,
            user_id=user_id,
            content=content,
            sender_type="user",
            response={
                "text": result["text"],
                "tool_calls": result.get("tool_calls", []),
                "model": result.get("model", settings.AGENT_MODEL),
                "finish_reason": result.get("finish_reason", "stop"),
            },
            tool_calls=result.get("tool_calls", []),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            model_used=result.get("model", settings.AGENT_MODEL),
            response_time_ms=response_time_ms,
        )
        self.session.add(message)

        conversation.last_message_at = datetime.now(timezone.utc)
        conversation.message_count += 1
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(message)

        # ── Layer 4: Cost Tracking ──────────────────────────────────────────

        total_tokens = usage.get("total_tokens", 0)
        if total_tokens > 0:
            try:
                record_message_cost(redis_client, total_tokens)
            except Exception as e:
                logger.error("Failed to record message cost: %s", e)

        return message, redis_client

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_active_instruction(self, user_id: int) -> Optional[UserAgentInstruction]:
        """Get the user's active custom instruction, if any."""
        return self.session.exec(
            select(UserAgentInstruction).where(
                UserAgentInstruction.user_id == user_id,
                UserAgentInstruction.is_active == True,
            )
        ).first()

    def _load_history(self, conversation_id: int, last_n: int = 10) -> List[dict]:
        """Load last N message pairs as conversation history."""
        messages_db = self.session.exec(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(last_n)
        ).all()

        history = []
        for msg in reversed(messages_db):
            history.append({"role": "user", "content": msg.content})
            if msg.response and isinstance(msg.response, dict) and msg.response.get("text"):
                history.append({"role": "assistant", "content": msg.response["text"]})
        return history

    @staticmethod
    def _build_system_prompt(instruction: Optional[UserAgentInstruction] = None) -> str:
        """Build the system prompt with optional user instruction."""
        base = (
            "You are an expert AI trading coach for a crypto trader using ClearJournal.\n"
            "You have access to tools that fetch the trader's real data.\n"
            "ALWAYS use these tools when answering — never make up numbers.\n"
            "ALWAYS cite specific metrics from tool results.\n"
            "Be concise, direct, and actionable.\n"
            "DO NOT predict future prices. DO NOT give specific buy/sell recommendations."
        )
        if instruction:
            base += f"\n\nTRADER'S PERSONAL INSTRUCTIONS:\n{instruction.content}"
        return base

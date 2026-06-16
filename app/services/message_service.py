"""Message service — CRUD operations with ownership verification."""
from typing import List
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.conversation import Conversation
from app.models.message import Message
from app.schemas.message import MessageRead


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

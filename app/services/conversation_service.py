"""Conversation service — CRUD operations with ownership verification."""
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationRead
from app.utils.pagination import paginate_query, PaginationResult


class ConversationService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_read(self, conversation: Conversation) -> ConversationRead:
        return ConversationRead(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            openai_conversation_id=conversation.openai_conversation_id,
            message_count=conversation.message_count,
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    def _get_or_404(self, conversation_id: int, user_id: int) -> Conversation:
        """Fetch a conversation by ID, verify ownership, or raise 404."""
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

    def list_conversations(
        self, user_id: int, page: int = 1, page_size: int = 20
    ) -> PaginationResult[ConversationRead]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.created_at.desc())
        )
        return paginate_query(self.session, stmt, page=page, page_size=page_size, schema_class=ConversationRead)

    def create_conversation(self, user_id: int, payload: ConversationCreate) -> ConversationRead:
        conversation = Conversation(
            user_id=user_id,
            title=payload.title or "",
        )
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return self._to_read(conversation)

    def get_conversation(self, conversation_id: int, user_id: int) -> ConversationRead:
        conversation = self._get_or_404(conversation_id, user_id)
        return self._to_read(conversation)

    def update_conversation(
        self, conversation_id: int, user_id: int, payload: ConversationUpdate
    ) -> ConversationRead:
        conversation = self._get_or_404(conversation_id, user_id)
        if payload.title is not None:
            conversation.title = payload.title
        self.session.add(conversation)
        self.session.commit()
        self.session.refresh(conversation)
        return self._to_read(conversation)

    def delete_conversation(self, conversation_id: int, user_id: int) -> None:
        conversation = self._get_or_404(conversation_id, user_id)
        self.session.delete(conversation)
        self.session.commit()

from typing import List
from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.message import MessageRead
from app.services.message_service import MessageService

router = APIRouter(tags=["messages"])


# ── List Messages for a Conversation ──────────────────────────────────────────

@router.get("/", response_model=List[MessageRead])
def list_messages(
    conversation_id: int = Query(..., description="Conversation ID to fetch messages from"),
    limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
    message_service: MessageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all messages in a conversation. Verifies ownership."""
    return message_service.list_messages(
        conversation_id=conversation_id, user_id=current_user.id, limit=limit
    )

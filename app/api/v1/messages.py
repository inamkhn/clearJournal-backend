from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.message import MessageCreate, MessageRead
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


# ── Send Message (triggers AI agent) ─────────────────────────────────────────

@router.post("/", response_model=MessageRead, status_code=201)
async def create_message(
    payload: MessageCreate,
    message_service: MessageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and get an AI response.
    Runs the full agent pipeline: context loading → tool calls → AI response.
    """
    return await message_service.create_message(
        user_id=current_user.id, payload=payload
    )


# ── Stream Message (SSE) ──────────────────────────────────────────────────────

@router.post("/stream")
async def create_message_stream(
    payload: MessageCreate,
    message_service: MessageService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """
    Send a message and stream the AI response word-by-word via SSE.
    Runs the full agent pipeline (guardrails + tools) before streaming.

    SSE events:
      - data: {"message_id": ..., "tool_calls": [...], "model": "..."}  (metadata)
      - data: {"token": "word "}  (repeated per word)
      - data: [DONE]  (final event)
    """
    return StreamingResponse(
        message_service.create_message_stream(
            user_id=current_user.id, payload=payload
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

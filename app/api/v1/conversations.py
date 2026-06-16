from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationRead
from app.services.conversation_service import ConversationService
from app.utils.pagination import PaginationResult

router = APIRouter(tags=["conversations"])


# ── List Conversations ────────────────────────────────────────────────────────

@router.get("/", response_model=PaginationResult[ConversationRead])
def list_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    conversation_service: ConversationService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List all conversations for the current user."""
    return conversation_service.list_conversations(
        user_id=current_user.id, page=page, page_size=page_size
    )


# ── Create Conversation ──────────────────────────────────────────────────────

@router.post("/", response_model=ConversationRead, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    conversation_service: ConversationService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new conversation."""
    return conversation_service.create_conversation(user_id=current_user.id, payload=payload)


# ── Get Conversation ──────────────────────────────────────────────────────────

@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(
    conversation_id: int,
    conversation_service: ConversationService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single conversation by ID."""
    return conversation_service.get_conversation(
        conversation_id=conversation_id, user_id=current_user.id
    )


# ── Update Conversation ──────────────────────────────────────────────────────

@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(
    conversation_id: int,
    payload: ConversationUpdate,
    conversation_service: ConversationService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update a conversation (e.g., rename title)."""
    return conversation_service.update_conversation(
        conversation_id=conversation_id, user_id=current_user.id, payload=payload
    )


# ── Delete Conversation ──────────────────────────────────────────────────────

@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: int,
    conversation_service: ConversationService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a conversation and all its messages (CASCADE)."""
    conversation_service.delete_conversation(
        conversation_id=conversation_id, user_id=current_user.id
    )
    return Response(status_code=204)

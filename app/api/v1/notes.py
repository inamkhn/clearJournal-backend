from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.note import NoteUpdate, NotePublic
from app.schemas.auth import Message
from app.utils.pagination import PaginationResult
from app.services.note_service import NoteService

router = APIRouter(tags=["notes"])


# ── List Notes ────────────────────────────────────────────────────────────────

@router.get("/", response_model=PaginationResult[NotePublic])
def list_notes(
    trade_id: Optional[int] = Query(None, description="Filter by trade ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """List notes with optional trade filter and pagination."""
    return note_service.list_notes(
        user_id=current_user.id,
        trade_id=trade_id,
        page=page,
        page_size=page_size,
    )


# ── Create Note ───────────────────────────────────────────────────────────────

@router.post("/", response_model=NotePublic, status_code=201)
def create(
    title: str = Form(...),
    description: str = Form(...),
    url: str = Form(""),
    trade_id: int = Form(...),
    images: Optional[List[UploadFile]] = File(None),
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Create a new note (multipart/form-data to support image uploads)."""
    from app.schemas.note import NoteCreate

    note_create = NoteCreate(
        title=title,
        description=description,
        url=url,
        trade_id=trade_id,
    )
    return note_service.create_note(
        user_id=current_user.id,
        note_create=note_create,
        images=images,
    )


# ── Get Note ──────────────────────────────────────────────────────────────────

@router.get("/{note_id}", response_model=NotePublic)
def get_note(
    note_id: int,
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get a single note by ID."""
    return note_service.get_note(note_id, current_user.id)


# ── Update Note ───────────────────────────────────────────────────────────────

@router.patch("/{note_id}", response_model=NotePublic)
def update_note(
    note_id: int,
    note_update: NoteUpdate,
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Update a note (partial update)."""
    return note_service.update_note(note_id, current_user.id, note_update)


# ── Delete Note ───────────────────────────────────────────────────────────────

@router.delete("/{note_id}", response_model=Message)
def delete_note(
    note_id: int,
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a note and all its images."""
    return note_service.delete_note(note_id, current_user.id)

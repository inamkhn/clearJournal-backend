from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form

from app.api.deps import get_current_user
from app.models.users import User
from app.schemas.note_image import NoteImageResponse
from app.schemas.auth import Message
from app.services.note_service import NoteService

router = APIRouter(tags=["note_images"])


# ── Get Note Images ───────────────────────────────────────────────────────────

@router.get("/", response_model=List[NoteImageResponse])
def get_note_images(
    note_id: Optional[int] = Query(None, description="Filter by note ID"),
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Get note images, optionally filtered by note_id."""
    return note_service.get_note_images(
        user_id=current_user.id,
        note_id=note_id,
    )


# ── Add Note Image ────────────────────────────────────────────────────────────

@router.post("/", response_model=Message)
def add_note_image(
    note_id: int = Form(...),
    image: UploadFile = File(...),
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Upload an image and attach it to a note."""
    return note_service.add_note_image(
        user_id=current_user.id,
        note_id=note_id,
        file=image,
    )


# ── Delete Note Image ─────────────────────────────────────────────────────────

@router.delete("/{note_image_id}", response_model=Message)
def delete_note_image(
    note_image_id: int,
    note_service: NoteService = Depends(),
    current_user: User = Depends(get_current_user),
):
    """Delete a single note image."""
    return note_service.delete_note_image(note_image_id, current_user.id)

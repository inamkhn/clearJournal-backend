from typing import List, Optional
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.db.session import get_session
from app.models.note import Note
from app.models.note_image import NoteImage
from app.models.trade import Trade
from app.schemas.note import NoteCreate, NoteUpdate, NotePublic
from app.schemas.note_image import NoteImageResponse
from app.schemas.common import Message
from app.utils.pagination import paginate_query, PaginationResult
from app.core.s3 import s3_client


class NoteService:
    def __init__(self, session: Session = Depends(get_session)):
        self.session = session

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _to_public(self, note: Note) -> NotePublic:
        """Convert Note model to NotePublic schema."""
        return NotePublic(
            id=note.id,
            title=note.title,
            description=note.description,
            url=note.url,
            trade_id=note.trade_id,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def _to_image_response(self, img: NoteImage) -> NoteImageResponse:
        """Convert NoteImage model to NoteImageResponse schema."""
        return NoteImageResponse(
            id=img.id,
            note_id=img.note_id,
            s3_key=img.s3_key,
            created_at=img.created_at,
            updated_at=img.updated_at,
            image_url=s3_client.get_presigned_url(img.s3_key),
        )

    def _get_note_or_404(self, note_id: int, user_id: int) -> Note:
        """Fetch a note, verifying ownership. Raises 404 if not found."""
        statement = (
            select(Note)
            .options(selectinload(Note.images))
            .where(Note.id == note_id, Note.user_id == user_id)
        )
        note = self.session.exec(statement).first()
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note not found",
            )
        return note

    def _verify_trade_ownership(self, trade_id: int, user_id: int) -> None:
        """Ensure the trade belongs to the user."""
        trade = self.session.exec(
            select(Trade).where(Trade.id == trade_id, Trade.user_id == user_id)
        ).first()
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trade not found or does not belong to user",
            )

    # ── List Notes ────────────────────────────────────────────────────────────

    def list_notes(
        self,
        user_id: int,
        trade_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginationResult[NotePublic]:
        """List notes with optional trade filter and pagination."""
        statement = select(Note).where(Note.user_id == user_id)

        if trade_id is not None:
            statement = statement.where(Note.trade_id == trade_id)

        statement = statement.order_by(Note.created_at.desc())

        result = paginate_query(
            session=self.session,
            statement=statement,
            page=page,
            page_size=page_size,
        )

        # Convert models to schemas
        items = [self._to_public(n) for n in result.items]
        return PaginationResult[NotePublic](
            items=items,
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            has_next=result.has_next,
            has_prev=result.has_prev,
            next_page=result.next_page,
            prev_page=result.prev_page,
        )

    # ── Get Note ──────────────────────────────────────────────────────────────

    def get_note(self, note_id: int, user_id: int) -> NotePublic:
        """Get a single note by ID."""
        note = self._get_note_or_404(note_id, user_id)
        return self._to_public(note)

    # ── Create Note ───────────────────────────────────────────────────────────

    def create_note(
        self,
        user_id: int,
        note_create: NoteCreate,
        images: Optional[list] = None,
    ) -> NotePublic:
        """Create a note and optionally upload images."""
        self._verify_trade_ownership(note_create.trade_id, user_id)

        note = Note(
            title=note_create.title,
            description=note_create.description,
            url=note_create.url,
            trade_id=note_create.trade_id,
            user_id=user_id,
        )
        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)

        # Upload images if provided
        if images:
            for file in images:
                if file.filename:  # Skip empty file fields
                    s3_key = s3_client.upload_file(
                        file=file,
                        folder="notes",
                        user_id=user_id,
                    )
                    note_image = NoteImage(note_id=note.id, s3_key=s3_key)
                    self.session.add(note_image)

            self.session.commit()
            self.session.refresh(note)

        return self._to_public(note)

    # ── Update Note ───────────────────────────────────────────────────────────

    def update_note(
        self,
        note_id: int,
        user_id: int,
        note_update: NoteUpdate,
    ) -> NotePublic:
        """Update a note (partial update)."""
        note = self._get_note_or_404(note_id, user_id)

        update_data = note_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(note, key, value)

        self.session.add(note)
        self.session.commit()
        self.session.refresh(note)

        return self._to_public(note)

    # ── Delete Note ───────────────────────────────────────────────────────────

    def delete_note(self, note_id: int, user_id: int) -> Message:
        """Delete a note and all its images (DB + S3)."""
        note = self._get_note_or_404(note_id, user_id)

        # Delete images from S3
        s3_keys = [img.s3_key for img in note.images]
        if s3_keys:
            s3_client.delete_files(s3_keys)

        # Delete from DB (cascade handles NoteImage records)
        self.session.delete(note)
        self.session.commit()

        return Message(message="Note deleted successfully")

    # ── Note Images ───────────────────────────────────────────────────────────

    def get_note_images(
        self,
        user_id: int,
        note_id: Optional[int] = None,
    ) -> List[NoteImageResponse]:
        """Get images, optionally filtered by note_id."""
        if note_id is not None:
            # Verify note ownership
            self._get_note_or_404(note_id, user_id)
            statement = select(NoteImage).where(NoteImage.note_id == note_id)
        else:
            # Get all images for notes belonging to this user
            statement = (
                select(NoteImage)
                .join(Note)
                .where(Note.user_id == user_id)
            )

        images = self.session.exec(statement).all()
        return [self._to_image_response(img) for img in images]

    def add_note_image(
        self,
        user_id: int,
        note_id: int,
        file,
    ) -> Message:
        """Upload an image and attach it to a note."""
        self._get_note_or_404(note_id, user_id)

        s3_key = s3_client.upload_file(
            file=file,
            folder="notes",
            user_id=user_id,
        )

        note_image = NoteImage(note_id=note_id, s3_key=s3_key)
        self.session.add(note_image)
        self.session.commit()

        return Message(message="Image uploaded successfully")

    def delete_note_image(
        self,
        note_image_id: int,
        user_id: int,
    ) -> Message:
        """Delete a single note image (DB + S3)."""
        # Find image and verify the note belongs to the user
        statement = (
            select(NoteImage)
            .join(Note)
            .where(NoteImage.id == note_image_id, Note.user_id == user_id)
        )
        image = self.session.exec(statement).first()
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Note image not found",
            )

        # Delete from S3
        s3_client.delete_file(image.s3_key)

        # Delete from DB
        self.session.delete(image)
        self.session.commit()

        return Message(message="Image deleted successfully")

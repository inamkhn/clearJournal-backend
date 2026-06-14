from datetime import datetime
from sqlmodel import SQLModel


class NoteImageResponse(SQLModel):
    """Public response schema for a note image."""
    id: int
    note_id: int
    s3_key: str
    created_at: datetime
    updated_at: datetime
    image_url: str  # Computed from s3_key (pre-signed or CDN URL)

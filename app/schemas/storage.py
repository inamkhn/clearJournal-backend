from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import SQLModel


class StorageRead(SQLModel):
    id: int
    name: str
    description: str
    configs: Dict[str, Any]
    is_active: bool
    image_url: str
    created_at: datetime
    updated_at: datetime

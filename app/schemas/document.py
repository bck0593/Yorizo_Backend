from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    uploaded_at: datetime
    summary: str


class DocumentItem(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    size_bytes: int
    mime_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: List[DocumentItem]

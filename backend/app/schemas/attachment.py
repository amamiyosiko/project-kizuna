from datetime import datetime

from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    conversation_id: int
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = "application/octet-stream"
    file_size: int = 0


class PresignUploadResponse(BaseModel):
    upload_url: str
    bucket: str
    object_key: str
    file_url: str | None = None
    expires_seconds: int


class AttachmentConfirmRequest(BaseModel):
    conversation_id: int
    message_id: int | None = None
    file_name: str
    content_type: str = "application/octet-stream"
    file_size: int = 0
    bucket: str
    object_key: str


class AttachmentRead(BaseModel):
    id: int
    conversation_id: int | None = None
    message_id: int | None = None
    store_id: int | None = None
    file_name: str
    content_type: str | None = None
    file_size: int | None = None
    bucket: str
    object_key: str
    status: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True

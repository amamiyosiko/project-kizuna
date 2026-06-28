import mimetypes
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import settings


def _safe_file_name(file_name: str) -> str:
    return Path(file_name).name.replace(" ", "_")[:180]


def build_object_key(store_code: str, conversation_id: int, file_name: str) -> str:
    safe_name = _safe_file_name(file_name)
    ext = Path(safe_name).suffix.lower()
    now = datetime.utcnow()
    return (
        f"attachments/{store_code}/{now:%Y/%m/%d}/"
        f"conversation-{conversation_id}/{uuid.uuid4().hex}{ext}"
    )


def build_ticket_object_key(store_code: str, ticket_id: int, ticket_no: str, file_name: str) -> str:
    safe_name = _safe_file_name(file_name)
    ext = Path(safe_name).suffix.lower()
    now = datetime.utcnow()
    safe_ticket_no = (ticket_no or f"ticket-{ticket_id}").replace("/", "-").replace(" ", "-")
    return (
        f"attachments/{store_code}/{now:%Y/%m/%d}/"
        f"ticket-{ticket_id}-{safe_ticket_no}/{uuid.uuid4().hex}{ext}"
    )


def guess_content_type(file_name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or fallback


def _s3_client():
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )


def create_presigned_put_url(object_key: str, content_type: str) -> str:
    if not settings.S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is not configured")
    return _s3_client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.S3_UPLOAD_EXPIRES_SECONDS,
    )


def create_presigned_get_url(object_key: str, expires_seconds: int | None = None) -> str | None:
    if not settings.S3_BUCKET_NAME:
        return None
    return _s3_client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": object_key,
        },
        ExpiresIn=expires_seconds or settings.S3_UPLOAD_EXPIRES_SECONDS,
    )


def public_file_url(object_key: str) -> str | None:
    if not settings.S3_BUCKET_NAME:
        return None
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{object_key}"

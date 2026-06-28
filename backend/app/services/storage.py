import mimetypes
import uuid
from datetime import datetime
from pathlib import Path

import boto3
from botocore.client import Config

from app.core.config import settings


def build_object_key(store_code: str, conversation_id: int, file_name: str) -> str:
    safe_name = Path(file_name).name.replace(" ", "_")
    ext = Path(safe_name).suffix.lower()
    now = datetime.utcnow()
    return (
        f"attachments/{store_code}/{now:%Y/%m/%d}/"
        f"conversation-{conversation_id}/{uuid.uuid4().hex}{ext}"
    )


def guess_content_type(file_name: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or fallback


def create_presigned_put_url(object_key: str, content_type: str) -> str:
    if not settings.S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME is not configured")
    client = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.S3_UPLOAD_EXPIRES_SECONDS,
    )


def public_file_url(object_key: str) -> str | None:
    if not settings.S3_BUCKET_NAME:
        return None
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{object_key}"

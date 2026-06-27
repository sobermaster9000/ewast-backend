import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile, HTTPException
from app.config import settings
import uuid
import os

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

def upload_file(file: UploadFile, folder: str = "images") -> str:
    """Upload a file to S3 and return its URL."""
    ext = os.path.splitext(file.filename)[1]
    key = f"{folder}/{uuid.uuid4()}{ext}"

    try:
        s3_client.upload_fileobj(
            file.file,
            settings.S3_BUCKET_NAME,
            key,
            ExtraArgs={"ContentType": file.content_type},
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {e}")

    return get_file_url(key)


def delete_file(key: str) -> None:
    """Delete a file from S3 by its key."""
    try:
        s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 delete failed: {e}")


def get_file_url(key: str) -> str:
    """Return the public URL for a given S3 key."""
    if settings.S3_BASE_URL:
        return f"{settings.S3_BASE_URL.rstrip('/')}/{key}"
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a temporary signed URL (for private buckets)."""
    try:
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"Could not generate URL: {e}")
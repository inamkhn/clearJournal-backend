import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings


class S3Client:
    """Helper for S3 operations (upload, delete, URL generation)."""

    def __init__(self):
        self._client = None
        self._bucket = None

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = settings.S3_BUCKET_NAME
        return self._bucket

    # ── Upload ────────────────────────────────────────────────────────────────

    def upload_file(
        self,
        file: UploadFile,
        folder: str = "notes",
        user_id: Optional[int] = None,
    ) -> str:
        """
        Upload a file to S3 and return the s3_key.

        Args:
            file: The uploaded file from FastAPI.
            folder: S3 folder prefix (e.g. "notes").
            user_id: User ID for organising files in sub-folders.

        Returns:
            The S3 key of the uploaded object.
        """
        filename = file.filename or "file"
        if "." in filename:
            ext = filename.rsplit(".", 1)[-1]
        else:
            ext = "bin"
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        prefix = f"{folder}/user_{user_id}/" if user_id else f"{folder}/"
        s3_key = f"{prefix}{unique_name}"

        self.client.upload_fileobj(
            Fileobj=file.file,
            Bucket=self.bucket,
            Key=s3_key,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        return s3_key

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_file(self, s3_key: str) -> None:
        """Delete a single object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
        except ClientError:
            # Log but don't fail — the DB record is the source of truth
            pass

    def delete_files(self, s3_keys: list[str]) -> None:
        """Delete multiple objects from S3 in a single request."""
        if not s3_keys:
            return
        try:
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": k} for k in s3_keys]},
            )
        except ClientError:
            pass

    # ── URL Generation ────────────────────────────────────────────────────────

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for an S3 object."""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expires_in,
            )
        except ClientError:
            return ""


# Module-level singleton
s3_client = S3Client()

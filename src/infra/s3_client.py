from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

DEFAULT_EXPIRATION = 7 * 24 * 3600  # 7 days


@dataclass
class S3Config:
    endpoint: Optional[str]
    access_key: str
    secret_key: str
    bucket: str
    region: str = "us-east-1"
    presign_expiration: int = DEFAULT_EXPIRATION

    @classmethod
    def from_env(cls) -> "S3Config":
        return cls(
            endpoint=os.environ.get("S3_ENDPOINT"),
            access_key=os.environ.get("S3_ACCESS_KEY", ""),
            secret_key=os.environ.get("S3_SECRET_KEY", ""),
            bucket=os.environ.get("S3_BUCKET", "audio-books"),
            region=os.environ.get("S3_REGION", "us-east-1"),
            presign_expiration=int(os.environ.get("S3_PRESIGN_EXPIRATION", DEFAULT_EXPIRATION)),
        )


class AudioStorageClient:
    def __init__(self, config: Optional[S3Config] = None) -> None:
        self.config = config or S3Config.from_env()
        session = boto3.session.Session(
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region,
        )
        self.client = session.client(
            "s3",
            endpoint_url=self.config.endpoint,
            config=BotoConfig(signature_version="s3v4"),
        )

    @staticmethod
    def generate_audio_key(book_id: int, chapter_index: int) -> str:
        prefix = hashlib.md5(str(book_id).encode("utf-8")).hexdigest()[:2]
        return f"audio/{prefix}/{book_id}/{chapter_index}.mp3"

    def upload_file(self, content_bytes: bytes, key: str) -> str:
        try:
            self.client.put_object(
                Bucket=self.config.bucket,
                Key=key,
                Body=content_bytes,
                ContentType="audio/mpeg",
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to upload to S3: {exc}") from exc
        return key

    def generate_presigned_url(self, key: str, expiration: Optional[int] = None) -> str:
        expires_in = expiration or self.config.presign_expiration
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.config.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        except (BotoCoreError, ClientError) as exc:  # pragma: no cover
            raise RuntimeError(f"Failed to generate presigned URL: {exc}") from exc

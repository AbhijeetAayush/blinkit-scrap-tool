from __future__ import annotations

import boto3

from src.app.settings import Settings


class S3Lake:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client("s3") if self._bucket else None

    def put_bronze(self, key: str, body: bytes) -> None:
        self._put(key, body)

    def put_silver(self, key: str, body: bytes) -> None:
        self._put(key, body)

    def _put(self, key: str, body: bytes) -> None:
        if not self._client or not self._bucket:
            return
        self._client.put_object(Bucket=self._bucket, Key=key, Body=body)

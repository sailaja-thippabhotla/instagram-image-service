import os
from typing import Optional
import boto3
from botocore.client import BaseClient


def _client(service_name: str) -> BaseClient:
    endpoint = os.environ.get("LOCALSTACK_ENDPOINT")
    # When running in AWS, LOCALSTACK_ENDPOINT should be unset.
    if endpoint:
        return boto3.client(
            service_name,
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        )
    return boto3.client(service_name)


class S3Storage:
    def __init__(self, bucket_name: str):
        self.bucket = bucket_name
        self.s3 = _client("s3")

    def put_bytes(self, key: str, data: bytes, content_type: str):
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def delete(self, key: str):
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def presign_get(self, key: str, expires_in: int = 600) -> str:
        return self.s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

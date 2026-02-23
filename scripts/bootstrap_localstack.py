import os
import time
import boto3

LOCALSTACK = os.environ.get("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET = os.environ.get("BUCKET_NAME", "images-bucket")
TABLE = os.environ.get("TABLE_NAME", "images-metadata")


def s3_client():
    return boto3.client(
        "s3",
        region_name=REGION,
        endpoint_url=LOCALSTACK,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


def ddb_client():
    return boto3.client(
        "dynamodb",
        region_name=REGION,
        endpoint_url=LOCALSTACK,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


def wait_localstack():
    # simple wait for localstack to accept connections
    for _ in range(30):
        try:
            s3_client().list_buckets()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("LocalStack not ready on " + LOCALSTACK)


def ensure_bucket():
    s3 = s3_client()
    buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if BUCKET not in buckets:
        s3.create_bucket(Bucket=BUCKET)
        print(f"Created bucket: {BUCKET}")
    else:
        print(f"Bucket exists: {BUCKET}")


def ensure_table():
    ddb = ddb_client()
    tables = ddb.list_tables().get("TableNames", [])
    if TABLE in tables:
        print(f"Table exists: {TABLE}")
        return

    ddb.create_table(
        TableName=TABLE,
        BillingMode="PAY_PER_REQUEST",
        KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "image_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "gsi_user_created",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    print(f"Creating table: {TABLE} ...")
    waiter = ddb.get_waiter("table_exists")
    waiter.wait(TableName=TABLE)
    print(f"Created table: {TABLE}")


if __name__ == "__main__":
    wait_localstack()
    ensure_bucket()
    ensure_table()

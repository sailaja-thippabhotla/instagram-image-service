import base64
import json
import os
from uuid import UUID

import boto3
import pytest
from moto import mock_s3, mock_dynamodb

from src.handlers import upload_image, list_images, view_image, delete_image


@pytest.fixture(autouse=True)
def env():
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["BUCKET_NAME"] = "images-bucket"
    os.environ["TABLE_NAME"] = "images-metadata"
    # For unit tests, we don't use LocalStack endpoint; moto intercepts boto3 calls.
    os.environ.pop("LOCALSTACK_ENDPOINT", None)
    yield


def _create_bucket_and_table():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=os.environ["BUCKET_NAME"])

    ddb = boto3.client("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=os.environ["TABLE_NAME"],
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
    waiter = ddb.get_waiter("table_exists")
    waiter.wait(TableName=os.environ["TABLE_NAME"])


@mock_s3
@mock_dynamodb
def test_upload_and_view_and_delete_happy_path():
    _create_bucket_and_table()

    img_bytes = b"\x89PNG\r\n\x1a\n" + b"fakepngdata"
    event = {
        "body": json.dumps({
            "filename": "cat.png",
            "content_type": "image/png",
            "image_base64": base64.b64encode(img_bytes).decode("utf-8"),
            "user_id": "u-123",
            "tags": ["pets", "cats"],
            "metadata": {"caption": "my cat"}
        })
    }

    res = upload_image(event, None)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    image_id = body["image_id"]
    UUID(image_id)  # validates uuid
    assert body["s3_key"].endswith("/cat.png")

    # view
    res2 = view_image({"pathParameters": {"image_id": image_id}}, None)
    assert res2["statusCode"] == 200
    body2 = json.loads(res2["body"])
    assert body2["image_id"] == image_id
    assert "download_url" in body2

    # delete
    res3 = delete_image({"pathParameters": {"image_id": image_id}}, None)
    assert res3["statusCode"] == 200
    body3 = json.loads(res3["body"])
    assert body3["deleted"] is True

    # view after delete -> 404
    res4 = view_image({"pathParameters": {"image_id": image_id}}, None)
    assert res4["statusCode"] == 404


@mock_s3
@mock_dynamodb
def test_list_filters_user_and_tag():
    _create_bucket_and_table()

    def upload(user, tags):
        img_bytes = b"test"
        return upload_image({
            "body": json.dumps({
                "filename": "x.jpg",
                "content_type": "image/jpeg",
                "image_base64": base64.b64encode(img_bytes).decode("utf-8"),
                "user_id": user,
                "tags": tags,
                "metadata": {}
            })
        }, None)

    r1 = upload("u-1", ["cats"])
    r2 = upload("u-1", ["dogs"])
    r3 = upload("u-2", ["cats"])

    # filter by user_id
    res = list_images({"queryStringParameters": {"user_id": "u-1"}}, None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["count"] == 2

    # filter by user_id + tag
    res2 = list_images({"queryStringParameters": {"user_id": "u-1", "tag": "cats"}}, None)
    body2 = json.loads(res2["body"])
    assert body2["count"] == 1
    assert body2["items"][0]["user_id"] == "u-1"
    assert "cats" in body2["items"][0]["tags"]

    # filter by tag only (scan)
    res3 = list_images({"queryStringParameters": {"tag": "cats"}}, None)
    body3 = json.loads(res3["body"])
    assert body3["count"] == 2


@mock_s3
@mock_dynamodb
def test_upload_validation_errors():
    _create_bucket_and_table()

    # missing fields
    res = upload_image({"body": "{}"}, None)
    assert res["statusCode"] == 400

    # invalid base64
    res2 = upload_image({"body": json.dumps({
        "filename": "a.png",
        "content_type": "image/png",
        "image_base64": "not-base64",
        "user_id": "u",
        "tags": [],
        "metadata": {}
    })}, None)
    assert res2["statusCode"] == 400


@mock_s3
@mock_dynamodb
def test_view_delete_missing_or_not_found():
    _create_bucket_and_table()

    res = view_image({"pathParameters": {}}, None)
    assert res["statusCode"] == 400

    res2 = delete_image({"pathParameters": {}}, None)
    assert res2["statusCode"] == 400

    res3 = view_image({"pathParameters": {"image_id": "does-not-exist"}}, None)
    assert res3["statusCode"] == 404

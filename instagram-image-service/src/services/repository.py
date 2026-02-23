import os
from typing import Dict, List, Optional, Tuple
import boto3
from boto3.dynamodb.conditions import Key, Attr


def _resource(service_name: str):
    endpoint = os.environ.get("LOCALSTACK_ENDPOINT")
    if endpoint:
        return boto3.resource(
            service_name,
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
            endpoint_url=endpoint,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
        )
    return boto3.resource(service_name)


class ImageRepository:
    def __init__(self, table_name: str):
        self.ddb = _resource("dynamodb")
        self.table = self.ddb.Table(table_name)

    def put(self, item: Dict):
        self.table.put_item(Item=item)

    def get(self, image_id: str) -> Optional[Dict]:
        res = self.table.get_item(Key={"image_id": image_id})
        return res.get("Item")

    def delete(self, image_id: str):
        self.table.delete_item(Key={"image_id": image_id})

    def list(self, user_id: Optional[str] = None, tag: Optional[str] = None, limit: int = 50) -> List[Dict]:
        # Fast path: query by user_id via GSI
        if user_id:
            kwargs = {
                "IndexName": "gsi_user_created",
                "KeyConditionExpression": Key("user_id").eq(user_id),
                "Limit": limit,
                "ScanIndexForward": False,  # newest first
            }
            if tag:
                kwargs["FilterExpression"] = Attr("tags").contains(tag)
            res = self.table.query(**kwargs)
            return res.get("Items", [])

        # If no user_id, fall back to scan (exercise scope)
        scan_kwargs = {"Limit": limit}
        if tag:
            scan_kwargs["FilterExpression"] = Attr("tags").contains(tag)
        res = self.table.scan(**scan_kwargs)
        return res.get("Items", [])

import base64
import json
import uuid
from typing import Any, Dict

from src.services.repository import ImageRepository
from src.services.storage import S3Storage
from src.util import get_env, parse_json_body, parse_qs, response, utc_now_iso


def _deps():
    bucket = get_env("BUCKET_NAME")
    table = get_env("TABLE_NAME")
    return S3Storage(bucket), ImageRepository(table)


def upload_image(event: Dict[str, Any], context: Any):
    try:
        body = parse_json_body(event)
        filename = body["filename"]
        content_type = body.get("content_type", "application/octet-stream")
        image_b64 = body["image_base64"]
        user_id = body["user_id"]
        tags = body.get("tags") or []
        metadata = body.get("metadata") or {}

        image_bytes = base64.b64decode(image_b64)
        image_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        s3_key = f"{user_id}/{image_id}/{filename}"

        storage, repo = _deps()
        storage.put_bytes(s3_key, image_bytes, content_type)

        item = {
            "image_id": image_id,
            "user_id": user_id,
            "created_at": created_at,
            "filename": filename,
            "content_type": content_type,
            "s3_key": s3_key,
            "tags": tags,
            "metadata": metadata,
        }
        repo.put(item)

        return response(201, {"image_id": image_id, "created_at": created_at, "s3_key": s3_key})

    except KeyError as e:
        return response(400, {"error": f"Missing required field: {str(e)}"})
    except (ValueError, base64.binascii.Error) as e:
        return response(400, {"error": str(e)})
    except Exception as e:
        return response(500, {"error": "Internal error", "detail": str(e)})


def list_images(event: Dict[str, Any], context: Any):
    try:
        qs = parse_qs(event)
        user_id = qs.get("user_id")
        tag = qs.get("tag")
        limit = int(qs.get("limit", "50"))

        _, repo = _deps()
        items = repo.list(user_id=user_id, tag=tag, limit=limit)

        return response(200, {"count": len(items), "items": items})
    except Exception as e:
        return response(500, {"error": "Internal error", "detail": str(e)})


def view_image(event: Dict[str, Any], context: Any):
    try:
        image_id = (event.get("pathParameters") or {}).get("image_id")
        if not image_id:
            return response(400, {"error": "Missing path param: image_id"})

        storage, repo = _deps()
        item = repo.get(image_id)
        if not item:
            return response(404, {"error": "Not found"})

        url = storage.presign_get(item["s3_key"], expires_in=600)
        return response(200, {"image_id": image_id, "download_url": url, "expires_in_seconds": 600})
    except Exception as e:
        return response(500, {"error": "Internal error", "detail": str(e)})


def delete_image(event: Dict[str, Any], context: Any):
    try:
        image_id = (event.get("pathParameters") or {}).get("image_id")
        if not image_id:
            return response(400, {"error": "Missing path param: image_id"})

        storage, repo = _deps()
        item = repo.get(image_id)
        if not item:
            return response(404, {"error": "Not found"})

        storage.delete(item["s3_key"])
        repo.delete(image_id)

        return response(200, {"deleted": True, "image_id": image_id})
    except Exception as e:
        return response(500, {"error": "Internal error", "detail": str(e)})

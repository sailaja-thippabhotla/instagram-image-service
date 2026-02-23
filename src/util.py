import base64
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_env(name: str, default: Optional[str] = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def response(status_code: int, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    return {
        "statusCode": status_code,
        "headers": h,
        "body": json.dumps(body),
    }


def parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw = event.get("body") or ""
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {e}") from e


def parse_qs(event: Dict[str, Any]) -> Dict[str, str]:
    # API GW may give queryStringParameters as dict or None
    qs = event.get("queryStringParameters") or {}
    return {k: str(v) for k, v in qs.items() if v is not None}

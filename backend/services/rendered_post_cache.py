import hashlib
import json
from typing import Optional

import redis as redis_lib

from config import settings

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_TTL = settings.processed_post_cache_ttl_seconds
_PIPELINE_VERSION = "v1"


def _key(url: str, content: str) -> str:
    base = f"{url}|{hashlib.sha256(content.encode('utf-8')).hexdigest()}|{_PIPELINE_VERSION}"
    return f"rendered_post:{hashlib.sha256(base.encode('utf-8')).hexdigest()}"


def get_rendered_post(url: str, content: str) -> Optional[str]:
    raw = _redis.get(_key(url, content))
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        out = payload.get("content")
        return out if isinstance(out, str) else None
    except Exception:
        return None


def set_rendered_post(url: str, content: str, rendered: str) -> None:
    payload = json.dumps({"url": url, "content": rendered}, ensure_ascii=False)
    _redis.setex(_key(url, content), _TTL, payload)

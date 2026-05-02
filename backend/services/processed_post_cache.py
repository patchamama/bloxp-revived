import hashlib
import json
from typing import Optional

import redis as redis_lib

from config import settings

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_TTL = settings.processed_post_cache_ttl_seconds
_PIPELINE_VERSION = "v1"


def _post_key(url: str, include_images: bool) -> str:
    payload = f"{url}|include_images={int(include_images)}|{_PIPELINE_VERSION}"
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"processed_post:{h}"


def get_processed_post(url: str, include_images: bool) -> Optional[dict]:
    raw = _redis.get(_post_key(url, include_images))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if not all(k in data for k in ("title", "date", "content")):
            return None
        return data
    except Exception:
        return None


def set_processed_post(
    url: str,
    include_images: bool,
    title: str,
    date: str | None,
    content: str,
) -> None:
    payload = json.dumps(
        {"url": url, "title": title, "date": date, "content": content},
        ensure_ascii=False,
    )
    _redis.setex(_post_key(url, include_images), _TTL, payload)

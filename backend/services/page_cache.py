import hashlib
import json
from typing import Optional

import redis as redis_lib

from config import settings

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_TTL = settings.page_cache_ttl_seconds


def _page_key(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"page_cache:{h}"


def get_cached_html(url: str) -> Optional[str]:
    raw = _redis.get(_page_key(url))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("html")
    except Exception:
        return None


def set_cached_html(url: str, html: str) -> None:
    payload = json.dumps({"url": url, "html": html}, ensure_ascii=False)
    _redis.setex(_page_key(url), _TTL, payload)

import base64
import hashlib
import json
from typing import Optional
from urllib.parse import urlparse, urlunparse

import redis as redis_lib

from config import settings

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_TTL = settings.page_cache_ttl_seconds


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    p = urlparse(u)
    scheme = (p.scheme or "https").lower()
    netloc = p.netloc.lower()
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", p.query, ""))


_CACHE_VERSION = "v3"  # bump when image processing params change


def _key(url: str) -> str:
    h = hashlib.sha256(_normalize_url(url).encode("utf-8")).hexdigest()
    return f"image_cache:{_CACHE_VERSION}:{h}"


def get_cached_image(url: str) -> Optional[tuple[bytes, str]]:
    raw = _redis.get(_key(url))
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        mime = payload.get("mime")
        b64 = payload.get("data_b64")
        if not mime or not b64:
            return None
        return base64.b64decode(b64.encode("ascii")), mime
    except Exception:
        return None


def set_cached_image(url: str, data: bytes, mime: str) -> None:
    payload = json.dumps(
        {
            "url": _normalize_url(url),
            "mime": mime,
            "data_b64": base64.b64encode(data).decode("ascii"),
        },
        ensure_ascii=False,
    )
    _redis.setex(_key(url), _TTL, payload)


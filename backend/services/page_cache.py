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


def _page_key(url: str) -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return f"page_cache:{h}"


def get_cached_html(url: str) -> Optional[str]:
    raw = _redis.get(_page_key(url))
    if not raw:
        norm = _normalize_url(url)
        if norm and norm != url:
            raw = _redis.get(_page_key(norm))
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data.get("html")
    except Exception:
        return None


def set_cached_html(url: str, html: str) -> None:
    norm = _normalize_url(url)
    payload = json.dumps({"url": norm or url, "html": html}, ensure_ascii=False)
    pipe = _redis.pipeline()
    pipe.setex(_page_key(url), _TTL, payload)
    if norm and norm != url:
        pipe.setex(_page_key(norm), _TTL, payload)
    pipe.execute()

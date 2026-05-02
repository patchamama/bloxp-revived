import json
from pathlib import Path
from typing import Any
import re
import zipfile
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import redis as redis_lib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config import settings
from services.admin_auth import authenticate_admin, issue_token, require_admin_auth
from storage.file_manager import cleanup_job
from tasks.celery_app import celery_app
from tasks.process_blog import (
    cancel_job,
    get_state,
    create_job,
    submit_job,
    set_job_source_url,
    force_start_queued_job,
)

router = APIRouter(prefix="/admin", tags=["admin"])
_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)
_IMG_SRC_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"']", re.IGNORECASE)
_IMG_SKIP = ("icon18_email", "icon18_edit", "blank.gif", "favicon", "s16/", "s24/", "s28/", "s32/")


def _read_metadata_file(job_dir: Path) -> dict[str, Any]:
    meta = job_dir / "metadata.json"
    if not meta.exists():
        return {}
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_epub_title(job_dir: Path) -> str | None:
    ep = job_dir / "output.epub"
    if not ep.exists():
        return None
    try:
        with zipfile.ZipFile(ep, "r") as zf:
            container_xml = zf.read("META-INF/container.xml")
            croot = ET.fromstring(container_xml)
            rootfile = croot.find(".//{*}rootfile")
            if rootfile is None:
                return None
            opf_path = rootfile.attrib.get("full-path")
            if not opf_path:
                return None
            opf_xml = zf.read(opf_path)
            oroot = ET.fromstring(opf_xml)
            title_node = oroot.find(".//{http://purl.org/dc/elements/1.1/}title")
            title = title_node.text.strip() if title_node is not None and title_node.text else None
            return title or None
    except Exception:
        return None


def _count_meaningful_images(html: str) -> int:
    if not html:
        return 0
    seen: set[str] = set()
    for src in _IMG_SRC_RE.findall(html):
        s = (src or "").strip()
        if not s or s.startswith("data:"):
            continue
        if any(token in s for token in _IMG_SKIP):
            continue
        seen.add(s)
    return len(seen)


class AdminLoginRequest(BaseModel):
    username: str
    password: str

class RegenerateRequest(BaseModel):
    use_cache: bool = True


@router.post("/login")
def admin_login(req: AdminLoginRequest) -> dict[str, Any]:
    if not authenticate_admin(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": issue_token(req.username)}


@router.get("/status")
def admin_status(_: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    inspector = celery_app.control.inspect(timeout=1.0)
    pong = inspector.ping() if inspector else None
    redis_ok = True
    try:
        _redis.ping()
    except Exception:
        redis_ok = False
    return {
        "redis_ok": redis_ok,
        "celery_ok": bool(pong),
        "celery_workers": len(pong or {}),
    }


@router.get("/cache/stats")
def cache_stats(_: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    count = 0
    total_bytes = 0
    for key in _redis.scan_iter("page_cache:*"):
        raw = _redis.get(key)
        if raw is None:
            continue
        count += 1
        total_bytes += len(raw.encode("utf-8"))
    return {
        "keys": count,
        "total_bytes": total_bytes,
        "ttl_seconds": settings.page_cache_ttl_seconds,
    }


@router.get("/cache/entries")
def cache_entries(page: int = 1, page_size: int = 50, _: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    keys = list(_redis.scan_iter("page_cache:*"))
    keys.sort()
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    items = []
    for key in keys[start:end]:
        raw = _redis.get(key)
        if not raw:
            continue
        ttl = _redis.ttl(key)
        try:
            payload = json.loads(raw)
            url = payload.get("url", "")
        except Exception:
            url = ""
        items.append({"key": key, "url": url, "ttl_seconds": ttl, "size_bytes": len(raw.encode("utf-8"))})
    return {"total": len(keys), "page": page, "page_size": page_size, "items": items}


@router.get("/cache/sites")
def cache_sites(_: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for key in _redis.scan_iter("page_cache:*"):
        raw = _redis.get(key)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
            url = payload.get("url", "")
            html = payload.get("html", "")
        except Exception:
            continue
        host = url.split("/")[2] if "://" in url else "unknown"
        ttl = _redis.ttl(key)
        image_count = _count_meaningful_images(html)
        g = grouped.setdefault(
            host,
            {"site": host, "pages_count": 0, "images_count_total": 0, "total_bytes": 0, "pages": []},
        )
        g["pages_count"] += 1
        g["images_count_total"] += image_count
        g["total_bytes"] += len(raw.encode("utf-8"))
        g["pages"].append(
            {
                "key": key,
                "url": url,
                "ttl_seconds": ttl,
                "size_bytes": len(raw.encode("utf-8")),
                "image_count": image_count,
            }
        )
    items = sorted(grouped.values(), key=lambda x: x["site"])
    return {"items": items}


@router.delete("/cache/sites/{site}", status_code=204)
def delete_cache_site(site: str, _: dict = Depends(require_admin_auth)) -> None:
    _delete_cache_by_host(site)


@router.delete("/cache/all", status_code=204)
def delete_cache_all(_: dict = Depends(require_admin_auth)) -> None:
    keys = list(_redis.scan_iter("page_cache:*"))
    keys += list(_redis.scan_iter("processed_post:*"))
    keys += list(_redis.scan_iter("rendered_post:*"))
    if keys:
        _redis.delete(*keys)


@router.delete("/cache/entries/{cache_key:path}", status_code=204)
def delete_cache_entry(cache_key: str, _: dict = Depends(require_admin_auth)) -> None:
    _redis.delete(cache_key)


@router.get("/ebooks")
def list_ebooks(_: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    base = Path(settings.generated_dir)
    base.mkdir(parents=True, exist_ok=True)
    items = []
    for d in sorted([p for p in base.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True):
        job_id = d.name
        state = get_state(job_id)
        meta = _read_metadata_file(d)
        files = []
        for f in d.glob("*"):
            if f.is_file():
                files.append({"name": f.name, "path": str(f), "size_bytes": f.stat().st_size})
        created_fallback = d.stat().st_ctime
        expires_fallback = created_fallback + settings.job_ttl_seconds
        ebook_title_fallback = _extract_epub_title(d) or job_id
        items.append(
            {
                "job_id": job_id,
                "created_at": state.created_at if state else meta.get("created_at", created_fallback),
                "expires_at": state.expires_at if state else meta.get("expires_at", expires_fallback),
                "status": state.status if state else "orphaned",
                "ebook_title": state.ebook_title if state and state.ebook_title else meta.get("ebook_title", ebook_title_fallback),
                "source_url": state.source_url if state else meta.get("source_url"),
                "posts_count": state.posts_crawled if state else meta.get("posts_count"),
                "dir_path": str(d),
                "files": files,
            }
        )
    items.sort(key=lambda x: (x["expires_at"] is None, x["expires_at"] or float("inf")))
    return {"items": items}


@router.delete("/ebooks/all", status_code=204)
def delete_all_ebooks(_: dict = Depends(require_admin_auth)) -> None:
    base = Path(settings.generated_dir)
    base.mkdir(parents=True, exist_ok=True)
    for d in [p for p in base.iterdir() if p.is_dir()]:
        job_id = d.name
        cancel_job(job_id)
        cleanup_job(job_id)
        _redis.delete(f"job:{job_id}")


@router.delete("/ebooks/{job_id}", status_code=204)
def delete_ebook(job_id: str, _: dict = Depends(require_admin_auth)) -> None:
    cancel_job(job_id)
    cleanup_job(job_id)
    _redis.delete(f"job:{job_id}")


def _delete_cache_by_host(host: str) -> int:
    deleted = 0
    for prefix in ("page_cache:*", "processed_post:*", "rendered_post:*"):
        keys_to_delete: list[str] = []
        for key in _redis.scan_iter(prefix):
            raw = _redis.get(key)
            if not raw:
                continue
            try:
                payload = json.loads(raw)
                url = payload.get("url", "")
            except Exception:
                continue
            h = urlparse(url).netloc if url else ""
            if h == host:
                keys_to_delete.append(key)
        if keys_to_delete:
            _redis.delete(*keys_to_delete)
            deleted += len(keys_to_delete)
    return deleted


@router.post("/ebooks/{job_id}/regenerate")
def regenerate_ebook(job_id: str, req: RegenerateRequest, _: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    state = get_state(job_id)
    source_url = state.source_url if state else None
    if not source_url:
        meta = _read_metadata_file(Path(settings.generated_dir) / job_id)
        source_url = meta.get("source_url")
    if not source_url:
        raise HTTPException(status_code=422, detail="Cannot regenerate: source_url missing")

    if not req.use_cache:
        host = urlparse(source_url).netloc
        if host:
            _delete_cache_by_host(host)

    new_state = create_job()
    set_job_source_url(new_state.job_id, source_url)
    payload = {
        "feed_url": source_url,
        "links_to_footnotes": True,
        "add_toc": True,
        "include_images": True,
        "max_posts": settings.max_posts_limit,
        "post_range_start": 1,
        "post_range_end": settings.max_posts_limit,
    }
    submit_job(new_state.job_id, "basic", payload)
    return {"job_id": new_state.job_id, "source_url": source_url, "use_cache": req.use_cache}


@router.post("/jobs/{job_id}/force-start")
def force_start_job(job_id: str, _: dict = Depends(require_admin_auth)) -> dict[str, Any]:
    ok = force_start_queued_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Queued job not found")
    return {"ok": True, "job_id": job_id}

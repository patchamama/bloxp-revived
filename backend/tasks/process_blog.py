import asyncio
import json
import logging
import re
import time
import uuid
from typing import Any
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from bs4 import BeautifulSoup

import redis as redis_lib

from config import settings
from models.job import JobState, JobStatus
from models.ebook_options import BasicJobRequest, AdvancedJobRequest, CustomSelector
from services.feed_parser import parse_feed
from services.crawler import crawl_from_feed, crawl_from_url, Post
from services.content_extractor import is_bad_title
from services.epub_builder import build_epub
from services.mobi_converter import convert_epub_to_mobi
from services.pdf_builder import build_pdf
from storage.file_manager import epub_path, mobi_path, pdf_path
from storage.file_manager import cleanup_job
from tasks.celery_app import celery_app

_redis = redis_lib.from_url(settings.redis_url)
_log = logging.getLogger(__name__)

# ── Job queue keys ────────────────────────────────────────────────────────────
_ACTIVE_KEY = "bloxp:active"    # SET  — job IDs currently being processed
_QUEUE_KEY  = "bloxp:pending"   # LIST — JSON {job_id, task, payload} waiting for a slot
_TASK_KEY_PREFIX = "bloxp:task:"


def _save_state(state: JobState) -> None:
    _redis.setex(
        f"job:{state.job_id}",
        settings.job_ttl_seconds,
        state.model_dump_json(),
    )


def get_state(job_id: str) -> JobState | None:
    raw = _redis.get(f"job:{job_id}")
    if not raw:
        return None
    return JobState.model_validate_json(raw)


def create_job() -> JobState:
    now = time.time()
    state = JobState(
        job_id=str(uuid.uuid4()),
        created_at=now,
        expires_at=now + settings.job_ttl_seconds,
    )
    _save_state(state)
    return state


def set_job_source_url(job_id: str, source_url: str) -> None:
    state = get_state(job_id)
    if not state:
        return
    state.source_url = source_url
    _save_state(state)


# ── Queue management ──────────────────────────────────────────────────────────

def _decode(v) -> str:
    return v.decode() if isinstance(v, bytes) else v


def _active_count() -> int:
    """Count active jobs, pruning stale entries (including never-started queued jobs)."""
    members = _redis.smembers(_ACTIVE_KEY)
    stale = []
    active = 0
    for m in members:
        jid = _decode(m)
        state = get_state(jid)
        if state and state.status in (
            JobStatus.parsing,
            JobStatus.crawling,
            JobStatus.downloading_images,
            JobStatus.generating,
        ):
            active += 1
        else:
            stale.append(m)
    if stale:
        _redis.srem(_ACTIVE_KEY, *stale)
    return active


def get_runtime_queue_stats() -> dict[str, int]:
    """Return runtime queue counters used by diagnostics/admin UI."""
    return {
        "active_jobs": _active_count(),
        "pending_jobs": int(_redis.llen(_QUEUE_KEY)),
        "max_concurrent_jobs": settings.max_concurrent_jobs,
    }


def list_runtime_tasks() -> dict[str, list[dict[str, Any]]]:
    now = time.time()
    running: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    running_ids: set[str] = set()

    for m in _redis.smembers(_ACTIVE_KEY):
        jid = _decode(m)
        state = get_state(jid)
        if not state:
            continue
        running_ids.add(jid)
        running.append(
            {
                "job_id": jid,
                "status": state.status,
                "source_url": state.source_url,
                "created_at": state.created_at,
                "elapsed_seconds": max(0, int(now - state.created_at)),
                "progress": state.progress,
                "posts_crawled": state.posts_crawled,
                "posts_cached": state.posts_cached,
                "posts_found": state.posts_found,
                "images_embedded": state.images_embedded,
                "images_cached": state.images_cached,
                "images_found": state.images_found,
            }
        )

    # Enrich from Celery active tasks so UI matches footer counters even when
    # Redis active set and worker state are briefly out of sync.
    try:
        inspector = celery_app.control.inspect(timeout=1.0)
        active_map = inspector.active() if inspector else None
    except Exception:
        active_map = None

    job_by_task_id: dict[str, str] = {}
    for key in _redis.scan_iter(f"{_TASK_KEY_PREFIX}*"):
        jid = _decode(key).replace(_TASK_KEY_PREFIX, "", 1)
        tid_raw = _redis.get(key)
        if tid_raw:
            job_by_task_id[_decode(tid_raw)] = jid

    for tasks in (active_map or {}).values():
        for task in (tasks or []):
            tid = task.get("id")
            if not tid:
                continue
            jid = job_by_task_id.get(tid)
            if not jid or jid in running_ids:
                continue
            state = get_state(jid)
            if not state:
                continue
            running_ids.add(jid)
            running.append(
                {
                    "job_id": jid,
                    "status": state.status,
                    "source_url": state.source_url,
                    "created_at": state.created_at,
                    "elapsed_seconds": max(0, int(now - state.created_at)),
                    "progress": state.progress,
                    "posts_crawled": state.posts_crawled,
                    "posts_cached": state.posts_cached,
                    "posts_found": state.posts_found,
                    "images_embedded": state.images_embedded,
                    "images_cached": state.images_cached,
                    "images_found": state.images_found,
                }
            )

    # Fallback reconciliation: include any job state currently in running phases
    # even if queue/celery mapping is temporarily inconsistent.
    running_statuses = {
        JobStatus.parsing,
        JobStatus.crawling,
        JobStatus.downloading_images,
        JobStatus.generating,
    }
    for key in _redis.scan_iter("job:*"):
        jid = _decode(key).replace("job:", "", 1)
        if jid in running_ids:
            continue
        state = get_state(jid)
        if not state or state.status not in running_statuses:
            continue
        running_ids.add(jid)
        running.append(
            {
                "job_id": jid,
                "status": state.status,
                "source_url": state.source_url,
                "created_at": state.created_at,
                "elapsed_seconds": max(0, int(now - state.created_at)),
                "progress": state.progress,
                "posts_crawled": state.posts_crawled,
                "posts_cached": state.posts_cached,
                "posts_found": state.posts_found,
                "images_embedded": state.images_embedded,
                "images_cached": state.images_cached,
                "images_found": state.images_found,
            }
        )

    queue = _redis.lrange(_QUEUE_KEY, 0, -1)
    for i, raw in enumerate(queue, start=1):
        entry = json.loads(_decode(raw))
        jid = entry.get("job_id")
        state = get_state(jid) if jid else None
        created_at = state.created_at if state else now
        pending.append(
            {
                "job_id": jid,
                "status": (state.status if state else JobStatus.queued),
                "source_url": (state.source_url if state else None),
                "created_at": created_at,
                "elapsed_seconds": max(0, int(now - created_at)),
                "queue_position": i,
            }
        )

    running.sort(key=lambda x: x["created_at"])
    return {"running": running, "pending": pending}


def get_queue_position(job_id: str) -> int:
    """Return 1-based position in the pending queue, 0 if not waiting."""
    for i, raw in enumerate(_redis.lrange(_QUEUE_KEY, 0, -1)):
        entry = json.loads(_decode(raw))
        if entry["job_id"] == job_id:
            return i + 1
    return 0


def _launch(task: str, job_id: str, payload: dict) -> None:
    if task == "basic":
        res = process_basic.apply_async(args=[job_id, payload])
    else:
        res = process_advanced.apply_async(args=[job_id, payload])
    _redis.setex(f"{_TASK_KEY_PREFIX}{job_id}", settings.job_ttl_seconds, res.id)


def _remove_from_pending(job_id: str) -> None:
    kept: list[str] = []
    for raw in _redis.lrange(_QUEUE_KEY, 0, -1):
        entry = json.loads(_decode(raw))
        if entry.get("job_id") != job_id:
            kept.append(json.dumps(entry))
    pipe = _redis.pipeline()
    pipe.delete(_QUEUE_KEY)
    if kept:
        pipe.rpush(_QUEUE_KEY, *kept)
    pipe.execute()


def cancel_job(job_id: str) -> bool:
    """Cancel queued/running job and delete all artifacts/state."""
    existed = bool(get_state(job_id))
    was_active = bool(_redis.sismember(_ACTIVE_KEY, job_id))
    was_queued = get_queue_position(job_id) > 0

    _remove_from_pending(job_id)
    _redis.srem(_ACTIVE_KEY, job_id)

    task_id = _redis.get(f"{_TASK_KEY_PREFIX}{job_id}")
    if task_id:
        try:
            celery_app.control.revoke(_decode(task_id), terminate=True, signal="SIGTERM")
        except Exception:
            pass
        _redis.delete(f"{_TASK_KEY_PREFIX}{job_id}")

    _redis.delete(f"job:{job_id}")
    cleanup_job(job_id)
    return existed or was_active or was_queued or bool(task_id)


def submit_job(job_id: str, task: str, payload: dict) -> None:
    """Start immediately if under the concurrency limit, otherwise enqueue."""
    if _active_count() < settings.max_concurrent_jobs:
        _redis.sadd(_ACTIVE_KEY, job_id)
        _launch(task, job_id, payload)
    else:
        _redis.rpush(_QUEUE_KEY, json.dumps({"job_id": job_id, "task": task, "payload": payload}))


def force_start_queued_job(job_id: str) -> bool:
    """Admin action: prioritize/start a queued job."""
    entry_found: dict | None = None
    kept: list[str] = []
    for raw in _redis.lrange(_QUEUE_KEY, 0, -1):
        entry = json.loads(_decode(raw))
        if entry.get("job_id") == job_id and entry_found is None:
            entry_found = entry
            continue
        kept.append(json.dumps(entry))
    if entry_found is None:
        return False

    pipe = _redis.pipeline()
    pipe.delete(_QUEUE_KEY)
    if kept:
        pipe.rpush(_QUEUE_KEY, *kept)
    pipe.execute()

    if _active_count() < settings.max_concurrent_jobs:
        _redis.sadd(_ACTIVE_KEY, job_id)
        _launch(entry_found["task"], job_id, entry_found["payload"])
    else:
        # Put it at queue front so it starts next
        _redis.lpush(_QUEUE_KEY, json.dumps(entry_found))
    return True


def _finish_job(job_id: str) -> None:
    """Free the active slot and start the next queued job if one exists."""
    _redis.srem(_ACTIVE_KEY, job_id)
    # Pop entries until we find a still-valid job or the queue is empty
    while True:
        raw = _redis.lpop(_QUEUE_KEY)
        if not raw:
            break
        entry = json.loads(_decode(raw))
        next_id = entry["job_id"]
        if get_state(next_id):
            _redis.sadd(_ACTIVE_KEY, next_id)
            _launch(entry["task"], next_id, entry["payload"])
            break
        # entry expired — skip and try next


def _extract_max_posts(url: str, default_limit: int = 250) -> tuple[str, int]:
    """Strip ?noMaxPosts from URL and return (clean_url, limit).
    ?noMaxPosts=true  → 500
    ?noMaxPosts=N     → N
    (absent)          → 250
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    raw = qs.pop("noMaxPosts", None)
    if raw is not None:
        val = raw[0]
        if val.lower() == "true" or val == "":
            limit = settings.max_posts_limit
        else:
            try:
                limit = min(settings.max_posts_limit, max(1, int(val)))
            except ValueError:
                limit = default_limit
    else:
        limit = default_limit
    clean_query = urlencode({k: v[0] for k, v in qs.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, limit


def _slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "ebook"


def _derive_title_from_content(content: str) -> str | None:
    try:
        soup = BeautifulSoup(content or "", "lxml")
        for selector in ("h1 a", "h2 a", "h1", "h2"):
            tag = soup.select_one(selector)
            if not tag:
                continue
            txt = tag.get_text(" ", strip=True)
            if txt and not is_bad_title(txt):
                return txt
    except Exception:
        return None
    return None


def _persist_job_metadata(state: JobState, posts_count: int) -> None:
    try:
        out_dir = epub_path(state.job_id).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "job_id": state.job_id,
            "created_at": state.created_at,
            "expires_at": state.expires_at,
            "ebook_title": state.ebook_title,
            "source_url": state.source_url,
            "posts_count": posts_count,
        }
        (out_dir / "metadata.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        _log.exception("Could not persist metadata for job %s", state.job_id)


@celery_app.task(bind=True)
def process_basic(self, job_id: str, payload: dict[str, Any]) -> None:
    req = BasicJobRequest(**payload)
    state = get_state(job_id)
    if not state:
        _finish_job(job_id)
        return

    try:
        range_start = req.post_range_start
        range_end = req.post_range_end if req.post_range_end is not None else req.max_posts
        range_start = min(range_start, settings.max_posts_limit)
        range_end = min(range_end, settings.max_posts_limit)
        if range_end < range_start:
            raise ValueError("post_range_end must be greater than or equal to post_range_start")
        fetch_limit = min(settings.max_posts_limit, max(req.max_posts, range_end))

        # Phase 1: parse feed
        state.status = JobStatus.parsing
        state.progress = 5
        _save_state(state)

        clean_url, max_posts = _extract_max_posts(req.feed_url, default_limit=fetch_limit)
        feed = parse_feed(clean_url, max_posts=max_posts)
        if not feed:
            state.status = JobStatus.error
            state.error_message = "Could not find a valid RSS/Atom feed. Try pasting the feed URL directly (e.g. https://example.com/feed)."
            _save_state(state)
            return

        feed_post_items = [(p.url, p.title) for p in feed.posts][range_start - 1:range_end]
        state.posts_found = len(feed_post_items)
        state.status = JobStatus.crawling
        state.progress = 10
        _save_state(state)

        # Phase 2: crawl
        def on_progress(crawled: int, total: int, cached: int) -> None:
            state.posts_crawled = crawled
            state.posts_cached = cached
            state.progress = 10 + int(crawled / max(total, 1) * 60)
            _save_state(state)

        posts = asyncio.run(
                crawl_from_feed(
                    feed_post_items,
                    max_posts=len(feed_post_items),
                    on_progress=on_progress,
                    include_images=req.include_images,
                )
        )

        _generate_ebooks(state, posts, feed.title, feed.description, req.add_toc, req.links_to_footnotes, req.include_images)

    except Exception as exc:
        state.status = JobStatus.error
        state.error_message = str(exc)
        _save_state(state)
        raise
    finally:
        _finish_job(job_id)


@celery_app.task(bind=True)
def process_advanced(self, job_id: str, payload: dict[str, Any]) -> None:
    req = AdvancedJobRequest(**payload)
    state = get_state(job_id)
    if not state:
        _finish_job(job_id)
        return

    try:
        range_start = req.post_range_start
        range_end = req.post_range_end if req.post_range_end is not None else req.max_posts
        range_start = min(range_start, settings.max_posts_limit)
        range_end = min(range_end, settings.max_posts_limit)
        if range_end < range_start:
            raise ValueError("post_range_end must be greater than or equal to post_range_start")
        fetch_limit = min(settings.max_posts_limit, max(req.max_posts, range_end))

        state.status = JobStatus.crawling
        state.progress = 5
        state.posts_found = max(0, range_end - range_start + 1)
        _save_state(state)

        custom = req.custom_selector

        def on_progress(crawled: int, total: int, cached: int) -> None:
            state.posts_crawled = crawled
            state.posts_cached = cached
            state.progress = 5 + int(crawled / max(total, 1) * 65)
            _save_state(state)

        posts = asyncio.run(
            crawl_from_url(
                req.starting_url,
                req.starting_title,
                max_posts=fetch_limit,
                custom_selector=custom,
                on_progress=on_progress,
                include_images=req.include_images,
            )
        )

        posts = posts[range_start - 1:range_end]

        state.posts_found = len(posts)
        _generate_ebooks(
            state, posts, req.site_title, req.site_description,
            req.add_toc, req.links_to_footnotes, req.include_images
        )

    except Exception as exc:
        state.status = JobStatus.error
        state.error_message = str(exc)
        _save_state(state)
        raise
    finally:
        _finish_job(job_id)


def _generate_ebooks(
    state: JobState,
    posts: list[Post],
    title: str,
    description: str,
    add_toc: bool,
    links_to_footnotes: bool,
    include_images: bool = True,
) -> None:
    if not posts:
        state.status = JobStatus.error
        state.error_message = "No posts could be fetched."
        _save_state(state)
        return

    # Final title guardrail: fix any bad/corrupted post title before rendering EPUB/PDF.
    for post in posts:
        if is_bad_title(post.title):
            recovered = _derive_title_from_content(post.content or "")
            if recovered:
                post.title = recovered

    # Authoritative count of posts that made it into the ebook
    state.posts_crawled = len(posts)
    state.progress = 75
    state.ebook_title = _slugify(title)

    if include_images:
        state.status = JobStatus.downloading_images
        # Count total images across all posts so frontend can show progress
        _SKIP = ("icon18_email", "icon18_edit", "blank.gif", "favicon", "s16/", "s24/", "s28/", "s32/")
        total_imgs = 0
        for post in posts:
            soup = BeautifulSoup(post.content or "", "lxml")
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src and not src.startswith("data:") and not any(f in src for f in _SKIP):
                    total_imgs += 1
        state.images_found = total_imgs
        if total_imgs == 0:
            state.status = JobStatus.generating
    else:
        state.status = JobStatus.generating

    _save_state(state)

    images_cached = 0

    def on_image(embedded: int, was_cached: bool = False) -> None:
        nonlocal images_cached
        if was_cached:
            images_cached += 1
        state.images_embedded = embedded
        state.images_cached = images_cached
        if state.images_found > 0:
            state.progress = 75 + int((embedded / state.images_found) * 10)
        _save_state(state)

    ep = epub_path(state.job_id)
    _, image_cache, processed_contents = build_epub(
        posts, title, description, ep, add_toc, links_to_footnotes, include_images,
        on_image=on_image if include_images else None,
    )
    state.epub_path = str(ep)
    state.status = JobStatus.generating
    state.progress = 85
    _save_state(state)

    mp = mobi_path(state.job_id)
    err = convert_epub_to_mobi(ep, mp)
    if not err:
        state.mobi_path = str(mp)
    else:
        _log.warning("MOBI conversion unavailable for job %s: %s", state.job_id, err)
    state.progress = 92
    _save_state(state)

    pp = pdf_path(state.job_id)
    try:
        build_pdf(
            posts, title, pp,
            image_cache=image_cache if include_images else None,
            processed_contents=processed_contents if include_images else None,
        )
        state.pdf_path = str(pp)
    except Exception as exc:
        # PDF is optional. Keep the job successful when EPUB already exists.
        _log.exception("PDF generation failed for job %s: %s", state.job_id, exc)

    state.status = JobStatus.done
    state.progress = 100
    _save_state(state)
    _persist_job_metadata(state, len(posts))

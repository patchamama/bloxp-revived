import asyncio
import json
import time
import uuid
from typing import Any

import redis as redis_lib

from config import settings
from models.job import JobState, JobStatus
from models.ebook_options import BasicJobRequest, AdvancedJobRequest, CustomSelector
from services.feed_parser import parse_feed
from services.crawler import crawl_from_feed, crawl_from_url, Post
from services.epub_builder import build_epub
from services.mobi_converter import convert_epub_to_mobi
from services.pdf_builder import build_pdf
from storage.file_manager import epub_path, mobi_path, pdf_path
from tasks.celery_app import celery_app

_redis = redis_lib.from_url(settings.redis_url)


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


@celery_app.task(bind=True)
def process_basic(self, job_id: str, payload: dict[str, Any]) -> None:
    req = BasicJobRequest(**payload)
    state = get_state(job_id)
    if not state:
        return

    try:
        # Phase 1: parse feed
        state.status = JobStatus.parsing
        state.progress = 5
        _save_state(state)

        feed = parse_feed(req.feed_url, max_posts=250)
        if not feed:
            state.status = JobStatus.error
            state.error_message = "Could not find a valid RSS/Atom feed. Try pasting the feed URL directly (e.g. https://example.com/feed)."
            _save_state(state)
            return

        post_urls = [p.url for p in feed.posts]
        state.posts_found = len(post_urls)
        state.status = JobStatus.crawling
        state.progress = 10
        _save_state(state)

        # Phase 2: crawl
        def on_progress(crawled: int, total: int) -> None:
            state.posts_crawled = crawled
            state.progress = 10 + int(crawled / max(total, 1) * 60)
            _save_state(state)

        posts = asyncio.run(
            crawl_from_feed(post_urls, max_posts=250, on_progress=on_progress)
        )

        _generate_ebooks(state, posts, feed.title, feed.description, req.add_toc, req.links_to_footnotes)

    except Exception as exc:
        state.status = JobStatus.error
        state.error_message = str(exc)
        _save_state(state)
        raise


@celery_app.task(bind=True)
def process_advanced(self, job_id: str, payload: dict[str, Any]) -> None:
    req = AdvancedJobRequest(**payload)
    state = get_state(job_id)
    if not state:
        return

    try:
        state.status = JobStatus.crawling
        state.progress = 5
        state.posts_found = req.max_posts
        _save_state(state)

        custom = req.custom_selector

        def on_progress(crawled: int, total: int) -> None:
            state.posts_crawled = crawled
            state.progress = 5 + int(crawled / max(total, 1) * 65)
            _save_state(state)

        posts = asyncio.run(
            crawl_from_url(
                req.starting_url,
                req.starting_title,
                max_posts=req.max_posts,
                custom_selector=custom,
                on_progress=on_progress,
            )
        )

        state.posts_found = len(posts)
        _generate_ebooks(
            state, posts, req.site_title, req.site_description,
            req.add_toc, req.links_to_footnotes
        )

    except Exception as exc:
        state.status = JobStatus.error
        state.error_message = str(exc)
        _save_state(state)
        raise


def _generate_ebooks(
    state: JobState,
    posts: list[Post],
    title: str,
    description: str,
    add_toc: bool,
    links_to_footnotes: bool,
) -> None:
    if not posts:
        state.status = JobStatus.error
        state.error_message = "No posts could be fetched."
        _save_state(state)
        return

    state.status = JobStatus.generating
    state.progress = 75
    _save_state(state)

    ep = epub_path(state.job_id)
    build_epub(posts, title, description, ep, add_toc, links_to_footnotes)
    state.epub_path = str(ep)
    state.progress = 85
    _save_state(state)

    mp = mobi_path(state.job_id)
    err = convert_epub_to_mobi(ep, mp)
    if not err:
        state.mobi_path = str(mp)
    state.progress = 92
    _save_state(state)

    pp = pdf_path(state.job_id)
    build_pdf(posts, title, pp)
    state.pdf_path = str(pp)

    state.status = JobStatus.done
    state.progress = 100
    _save_state(state)

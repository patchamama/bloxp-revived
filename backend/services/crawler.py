import asyncio
from dataclasses import dataclass
from typing import Callable, Optional
import httpx
from services.link_finder import find_next_post_url
from services.content_extractor import extract_content, is_bad_title
from services.page_cache import get_cached_html, set_cached_html
from services.processed_post_cache import get_processed_post, set_processed_post
from models.ebook_options import CustomSelector

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Bloxp/2.0; +https://bloxp.app)",
}

TIMEOUT = httpx.Timeout(30.0)
MAX_CONCURRENT = 5


@dataclass
class Post:
    url: str
    title: str
    content: str
    date: str | None = None


async def crawl_from_feed(
    post_items: list[tuple[str, str]],
    max_posts: int = 250,
    on_progress: Optional[Callable[[int, int, int], None]] = None,
    include_images: bool = True,
) -> list[Post]:
    items = post_items[:max_posts]
    urls = [u for u, _ in items]
    fallback_title_by_url = {u: t for u, t in items}
    total = len(urls)
    posts: list[Post] = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        sem = asyncio.Semaphore(MAX_CONCURRENT)
        lock = asyncio.Lock()
        crawled = 0
        cached = 0

        async def fetch_one(url: str, idx: int) -> Optional[Post]:
            nonlocal crawled, cached
            async with sem:
                try:
                    from_cache = True
                    cached_post = get_processed_post(url, include_images=include_images)
                    if cached_post is not None:
                        title = cached_post.get("title", "Untitled")
                        date = cached_post.get("date")
                        content = cached_post.get("content", "<p>No content</p>")
                        if is_bad_title(title):
                            html = get_cached_html(url)
                            if html is None:
                                from_cache = False
                                r = await client.get(url)
                                r.raise_for_status()
                                html = r.text
                                set_cached_html(url, html)
                            title, date, content = extract_content(html, url, include_images=include_images)
                            set_processed_post(url, include_images=include_images, title=title, date=date, content=content)
                    else:
                        html = get_cached_html(url)
                        if html is None:
                            from_cache = False
                            r = await client.get(url)
                            r.raise_for_status()
                            html = r.text
                            set_cached_html(url, html)
                        title, date, content = extract_content(html, url, include_images=include_images)
                        set_processed_post(url, include_images=include_images, title=title, date=date, content=content)
                    if on_progress:
                        async with lock:
                            crawled += 1
                            if from_cache:
                                cached += 1
                            on_progress(crawled, total, cached)
                    fallback_title = (fallback_title_by_url.get(url) or "").strip()
                    if is_bad_title(title) and fallback_title:
                        title = fallback_title
                    return Post(url=url, title=title, content=content, date=date)
                except Exception:
                    return None

        results = await asyncio.gather(*[fetch_one(u, i) for i, u in enumerate(urls)])

    return [p for p in results if p is not None]


async def crawl_from_url(
    start_url: str,
    start_title: str,
    max_posts: int = 250,
    custom_selector: Optional[CustomSelector] = None,
    on_progress: Optional[Callable[[int, int, int], None]] = None,
    include_images: bool = True,
) -> list[Post]:
    posts: list[Post] = []
    current_url: Optional[str] = start_url

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        cached = 0
        while current_url and len(posts) < max_posts:
            try:
                from_cache = True
                html = get_cached_html(current_url)
                if html is None:
                    from_cache = False
                    r = await client.get(current_url)
                    r.raise_for_status()
                    html = r.text
                    set_cached_html(current_url, html)
                cached_post = get_processed_post(current_url, include_images=include_images)
                if cached_post is not None:
                    title = cached_post.get("title", "Untitled")
                    date = cached_post.get("date")
                    content = cached_post.get("content", "<p>No content</p>")
                    if is_bad_title(title):
                        title, date, content = extract_content(html, current_url, include_images=include_images)
                        set_processed_post(current_url, include_images=include_images, title=title, date=date, content=content)
                else:
                    title, date, content = extract_content(html, current_url, include_images=include_images)
                    set_processed_post(current_url, include_images=include_images, title=title, date=date, content=content)

                if not posts and start_title:
                    title = start_title

                posts.append(Post(url=current_url, title=title, content=content, date=date))
                if from_cache:
                    cached += 1

                if on_progress:
                    on_progress(len(posts), max_posts, cached)

                current_url = find_next_post_url(html, current_url, custom_selector)
            except Exception:
                break

    return posts

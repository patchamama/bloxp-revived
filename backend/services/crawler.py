import asyncio
from dataclasses import dataclass
from typing import Callable, Optional
import httpx
from services.link_finder import find_next_post_url
from services.content_extractor import extract_content
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


async def crawl_from_feed(
    post_urls: list[str],
    max_posts: int = 250,
    on_progress: Optional[Callable[[int, int], None]] = None,
    include_images: bool = True,
) -> list[Post]:
    urls = post_urls[:max_posts]
    total = len(urls)
    posts: list[Post] = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        sem = asyncio.Semaphore(MAX_CONCURRENT)

        async def fetch_one(url: str, idx: int) -> Optional[Post]:
            async with sem:
                try:
                    r = await client.get(url)
                    r.raise_for_status()
                    title, content = extract_content(r.text, url, include_images=include_images)
                    if on_progress:
                        on_progress(idx + 1, total)
                    return Post(url=url, title=title, content=content)
                except Exception:
                    return None

        results = await asyncio.gather(*[fetch_one(u, i) for i, u in enumerate(urls)])

    return [p for p in results if p is not None]


async def crawl_from_url(
    start_url: str,
    start_title: str,
    max_posts: int = 250,
    custom_selector: Optional[CustomSelector] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    include_images: bool = True,
) -> list[Post]:
    posts: list[Post] = []
    current_url: Optional[str] = start_url

    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT, follow_redirects=True) as client:
        while current_url and len(posts) < max_posts:
            try:
                r = await client.get(current_url)
                r.raise_for_status()
                html = r.text
                title, content = extract_content(html, current_url, include_images=include_images)

                if not posts and start_title:
                    title = start_title

                posts.append(Post(url=current_url, title=title, content=content))

                if on_progress:
                    on_progress(len(posts), max_posts)

                current_url = find_next_post_url(html, current_url, custom_selector)
            except Exception:
                break

    return posts

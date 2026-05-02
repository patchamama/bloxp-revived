from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from services.page_cache import get_cached_html, set_cached_html


@dataclass
class FeedPost:
    url: str
    title: str


@dataclass
class FeedInfo:
    title: str
    description: str
    site_url: str
    posts: list[FeedPost]


def _parse_url(url: str) -> Optional[tuple[feedparser.FeedParserDict, list[FeedPost]]]:
    cached = get_cached_html(url)
    if cached:
        parsed = feedparser.parse(cached)
    else:
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=15)
            resp.raise_for_status()
            set_cached_html(url, resp.text)
            parsed = feedparser.parse(resp.text)
        except Exception:
            return None
    if parsed.bozo and not parsed.entries:
        return None

    posts = [
        FeedPost(url=e.get("link", ""), title=e.get("title", "Untitled"))
        for e in parsed.entries
        if e.get("link")
    ]
    if not posts:
        return None
    return parsed, posts


def _is_wordpress_feed(feed_url: str) -> bool:
    return "?feed=" in feed_url or feed_url.rstrip("/").endswith(("/feed", "/rss", "/rss2"))


def _is_blogger_feed(parsed: feedparser.FeedParserDict) -> bool:
    generator = parsed.feed.get("generator", "").lower()
    links = parsed.feed.get("links", [])
    return "blogger" in generator or any("blogger.com" in l.get("href", "") for l in links)


def _paginate_feed(feed_url: str, max_posts: int = 250) -> Optional[FeedInfo]:
    """Fetch multiple feed pages until max_posts or no new entries."""
    result = _parse_url(feed_url)
    if not result:
        return None

    parsed, all_posts = result
    feed = parsed.feed

    page_size = len(all_posts)
    if page_size == 0:
        return None

    is_blogger = _is_blogger_feed(parsed)
    is_wp = _is_wordpress_feed(feed_url)

    seen_urls: set[str] = {p.url for p in all_posts}
    page = 2

    while len(all_posts) < max_posts:
        if is_blogger:
            next_index = len(all_posts) + 1
            next_url = _blogger_page_url(feed_url, next_index, page_size)
        elif is_wp:
            next_url = _wp_page_url(feed_url, page)
        else:
            # Generic: try ?paged=N first, give up after page 2 if nothing new
            next_url = _wp_page_url(feed_url, page)

        result = _parse_url(next_url)
        if not result:
            break

        _, new_posts = result
        new_unique = [p for p in new_posts if p.url not in seen_urls]
        if not new_unique:
            break

        all_posts.extend(new_unique)
        seen_urls.update(p.url for p in new_unique)
        page += 1

        if len(new_unique) < page_size // 2:
            # Last page is almost empty — stop
            break

    return FeedInfo(
        title=feed.get("title", ""),
        description=feed.get("subtitle", ""),
        site_url=feed.get("link", ""),
        posts=all_posts[:max_posts],
    )


def _wp_page_url(feed_url: str, page: int) -> str:
    parsed = urlparse(feed_url)
    qs = parse_qs(parsed.query)
    qs["paged"] = [str(page)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def _blogger_page_url(feed_url: str, start_index: int, max_results: int) -> str:
    parsed = urlparse(feed_url)
    qs = parse_qs(parsed.query)
    qs["start-index"] = [str(start_index)]
    qs["max-results"] = [str(min(max_results, 25))]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunparse(parsed._replace(query=new_query))


def _discover_feed_url(site_url: str) -> Optional[str]:
    """Fetch the site HTML and look for RSS/Atom feed links."""
    html = get_cached_html(site_url)
    try:
        if html is None:
            resp = httpx.get(site_url, follow_redirects=True, timeout=15)
            resp.raise_for_status()
            html = resp.text
            set_cached_html(site_url, html)
            base_url = str(resp.url)
        else:
            base_url = site_url
    except Exception:
        if html is None:
            return None
        base_url = site_url

    soup = BeautifulSoup(html, "lxml")

    for mime in ("application/rss+xml", "application/atom+xml", "application/feed+json"):
        tag = soup.find("link", rel="alternate", type=mime)
        if tag and tag.get("href"):
            return urljoin(base_url, tag["href"])

    for path in ("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/?feed=rss2"):
        candidate = urljoin(site_url.rstrip("/"), path)
        result = _parse_url(candidate)
        if result:
            return candidate

    return None


def parse_feed(feed_url: str, max_posts: int = 250) -> Optional[FeedInfo]:
    """Parse a feed URL with automatic pagination and site-URL discovery."""
    # Try direct parse first
    result = _parse_url(feed_url)
    if not result:
        discovered = _discover_feed_url(feed_url)
        if not discovered:
            return None
        feed_url = discovered
        result = _parse_url(feed_url)
        if not result:
            return None

    # Single page was enough
    _, posts = result
    if len(posts) >= max_posts:
        parsed, _ = result
        feed = parsed.feed
        return FeedInfo(
            title=feed.get("title", ""),
            description=feed.get("subtitle", ""),
            site_url=feed.get("link", ""),
            posts=posts[:max_posts],
        )

    # Try to paginate for more posts
    return _paginate_feed(feed_url, max_posts=max_posts)

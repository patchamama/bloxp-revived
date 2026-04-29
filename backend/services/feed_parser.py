from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup


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


def _parse_url(url: str) -> Optional[FeedInfo]:
    parsed = feedparser.parse(url)
    if parsed.bozo and not parsed.entries:
        return None

    feed = parsed.feed
    posts = [
        FeedPost(
            url=entry.get("link", ""),
            title=entry.get("title", "Untitled"),
        )
        for entry in parsed.entries
        if entry.get("link")
    ]

    if not posts:
        return None

    return FeedInfo(
        title=feed.get("title", ""),
        description=feed.get("subtitle", ""),
        site_url=feed.get("link", ""),
        posts=posts,
    )


def _discover_feed_url(site_url: str) -> Optional[str]:
    """Fetch the site HTML and look for RSS/Atom feed links."""
    try:
        resp = httpx.get(site_url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # <link rel="alternate" type="application/rss+xml" href="...">
    for mime in ("application/rss+xml", "application/atom+xml", "application/feed+json"):
        tag = soup.find("link", rel="alternate", type=mime)
        if tag and tag.get("href"):
            return urljoin(str(resp.url), tag["href"])

    # Common feed path guesses as last resort
    for path in ("/feed", "/feed/", "/rss", "/rss.xml", "/atom.xml", "/?feed=rss2"):
        candidate = urljoin(site_url.rstrip("/"), path)
        result = _parse_url(candidate)
        if result:
            return candidate

    return None


def parse_feed(feed_url: str) -> Optional[FeedInfo]:
    """Parse a feed URL. If it fails, try to auto-discover the feed from the site HTML."""
    result = _parse_url(feed_url)
    if result:
        return result

    discovered = _discover_feed_url(feed_url)
    if discovered:
        return _parse_url(discovered)

    return None

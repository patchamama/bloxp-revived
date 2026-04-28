from dataclasses import dataclass
from typing import Optional
import feedparser


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


def parse_feed(feed_url: str) -> Optional[FeedInfo]:
    parsed = feedparser.parse(feed_url)
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

    return FeedInfo(
        title=feed.get("title", ""),
        description=feed.get("subtitle", ""),
        site_url=feed.get("link", ""),
        posts=posts,
    )

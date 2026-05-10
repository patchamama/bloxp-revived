from dataclasses import dataclass
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from services.page_cache import get_cached_html, set_cached_html
from services.wix_browser_discovery import discover_wix_posts_with_browser


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
    parsed = None
    if cached:
        parsed = feedparser.parse(cached)
        # If the cache has garbage (HTML error page cached as a feed), discard it
        if parsed.bozo and not parsed.entries:
            parsed = None
    if parsed is None:
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


def _is_wix_feed(parsed: feedparser.FeedParserDict, feed_url: str) -> bool:
    generator = str(parsed.feed.get("generator", "")).lower()
    links = parsed.feed.get("links", [])
    hrefs = [str(l.get("href", "")).lower() for l in links]
    haystack = " ".join([generator, feed_url.lower(), *hrefs])
    return any(x in haystack for x in ("wix", "wixsite", "wixstatic"))


def _is_wix_like_site(parsed: feedparser.FeedParserDict, feed_url: str) -> bool:
    if _is_wix_feed(parsed, feed_url):
        return True

    lowered = feed_url.lower()
    if lowered.endswith("/blog-feed.xml") or "/blog-feed.xml?" in lowered:
        return True

    site_url = str(parsed.feed.get("link", "")).strip()
    html = get_cached_html(site_url) if site_url else None
    if html and "blog-frontend-adapter-public" in html:
        return True
    return False


def _wix_headers(site_url: str) -> dict[str, str]:
    parsed = urlparse(site_url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else site_url
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": origin + "/blog",
        "Origin": origin,
    }


def _json_get(url: str, headers: Optional[dict[str, str]] = None) -> Optional[dict[str, Any]]:
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15, headers=headers)
        if resp.status_code >= 400:
            return None
        return resp.json()
    except Exception:
        return None


def _as_abs_post_url(raw_url: str, site_url: str) -> Optional[str]:
    if not raw_url:
        return None
    abs_url = urljoin(site_url, raw_url)
    return abs_url if _looks_like_post_url(abs_url) else None


def _collect_wix_posts(node: Any, site_url: str, out: list[FeedPost], seen: set[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _collect_wix_posts(item, site_url, out, seen)
        return

    if not isinstance(node, dict):
        return

    # Most Wix payloads keep one post per dict object with URL/title-like fields.
    url_candidates = [
        str(node.get("url", "")).strip(),
        str(node.get("link", "")).strip(),
        str(node.get("postUrl", "")).strip(),
        str(node.get("fullUrl", "")).strip(),
    ]
    slug = str(node.get("slug", "")).strip()
    if slug:
        url_candidates.extend([f"/post/{slug}", f"/blog/post/{slug}"])

    abs_url = None
    for candidate in url_candidates:
        abs_url = _as_abs_post_url(candidate, site_url)
        if abs_url:
            break

    if abs_url and abs_url not in seen:
        title = (
            str(node.get("title", "")).strip()
            or str(node.get("seoTitle", "")).strip()
            or str(node.get("postTitle", "")).strip()
            or _title_from_url(abs_url)
        )
        out.append(FeedPost(url=abs_url, title=title or "Untitled"))
        seen.add(abs_url)

    for value in node.values():
        if isinstance(value, (dict, list)):
            _collect_wix_posts(value, site_url, out, seen)


def _discover_wix_posts_from_api(site_url: str, max_posts: int = 250) -> list[FeedPost]:
    parsed_site = urlparse(site_url)
    base = f"{parsed_site.scheme}://{parsed_site.netloc}" if parsed_site.scheme and parsed_site.netloc else site_url
    headers = _wix_headers(base)
    page_size = min(max(max_posts, 20), 100)
    posts: list[FeedPost] = []
    seen: set[str] = set()

    for page in range(1, 400):
        if len(posts) >= max_posts:
            break
        feed_page_url = (
            f"{base}/_api/blog-frontend-adapter-public/v2/post-feed-page"
            f"?includeContent=false&languageCode=es&page={page}&pageSize={page_size}&type=ALL_POSTS"
        )
        payload = _json_get(feed_page_url, headers=headers)
        if not payload:
            break

        before = len(posts)
        _collect_wix_posts(payload, base, posts, seen)
        if len(posts) == before:
            break

        meta_url = (
            f"{base}/_api/blog-frontend-adapter-public/v2/post-feed-page-metadata"
            f"?page={page}&pageSize={page_size}&languageCode=es&type=ALL_POSTS"
        )
        metadata = _json_get(meta_url, headers=headers) or {}
        total_pages = int(metadata.get("totalPages") or metadata.get("pagesCount") or 0)
        has_next = metadata.get("hasNextPage")
        if isinstance(has_next, bool) and not has_next:
            break
        if total_pages and page >= total_pages:
            break

    return posts[:max_posts]


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


def _download_xml(url: str) -> Optional[str]:
    cached = get_cached_html(url)
    if cached:
        stripped = cached.lstrip()
        # Reject cached HTML error pages — only accept XML
        if stripped.startswith("<") and not stripped.lower().startswith("<html"):
            return cached
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15)
        resp.raise_for_status()
        set_cached_html(url, resp.text)
        return resp.text
    except Exception:
        return None


def _looks_like_post_url(url: str) -> bool:
    lowered = url.lower()
    if any(x in lowered for x in ("/category/", "/tag/", "/archive/", "/author/", "/search", "/feed")):
        return False
    return "/post/" in lowered or "/blog/" in lowered


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug[:1].upper() + slug[1:] if slug else "Untitled"


def _discover_posts_from_sitemaps(site_url: str, max_posts: int = 250) -> list[FeedPost]:
    parsed_site = urlparse(site_url)
    base = f"{parsed_site.scheme}://{parsed_site.netloc}" if parsed_site.scheme and parsed_site.netloc else site_url
    seeds = [
        urljoin(base, "/sitemap.xml"),
        urljoin(base, "/sitemap_index.xml"),
        urljoin(base, "/blog-sitemap.xml"),
        urljoin(base, "/post-sitemap.xml"),
    ]

    queue: list[str] = seeds[:]
    seen_sitemaps: set[str] = set()
    post_urls: list[str] = []
    seen_posts: set[str] = set()

    while queue and len(post_urls) < max_posts:
        sitemap_url = queue.pop(0)
        if sitemap_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sitemap_url)

        xml = _download_xml(sitemap_url)
        if not xml:
            continue

        soup = BeautifulSoup(xml, "xml")
        if soup.find("sitemapindex"):
            for loc in soup.find_all("loc"):
                child = (loc.get_text() or "").strip()
                if child and child not in seen_sitemaps:
                    queue.append(child)
            continue

        for loc in soup.find_all("loc"):
            post_url = (loc.get_text() or "").strip()
            if not post_url or post_url in seen_posts:
                continue
            if not _looks_like_post_url(post_url):
                continue
            seen_posts.add(post_url)
            post_urls.append(post_url)
            if len(post_urls) >= max_posts:
                break

    return [FeedPost(url=u, title=_title_from_url(u)) for u in post_urls[:max_posts]]


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

    parsed, posts = result
    if len(posts) >= max_posts:
        feed = parsed.feed
        return FeedInfo(
            title=feed.get("title", ""),
            description=feed.get("subtitle", ""),
            site_url=feed.get("link", ""),
            posts=posts[:max_posts],
        )

    # Wix RSS only returns the newest 20 posts. Enrich with sitemap URLs when possible.
    if _is_wix_like_site(parsed, feed_url):
        site_base = parsed.feed.get("link") or feed_url
        wix_api_posts = _discover_wix_posts_from_api(site_base, max_posts=max_posts)
        sitemap_posts = _discover_posts_from_sitemaps(site_base, max_posts=max_posts)
        combined = posts[:]
        seen = {p.url for p in combined}
        for post in wix_api_posts:
            if post.url in seen:
                continue
            combined.append(post)
            seen.add(post.url)
            if len(combined) >= max_posts:
                break
        for post in sitemap_posts:
            if post.url in seen:
                continue
            combined.append(post)
            seen.add(post.url)
            if len(combined) >= max_posts:
                break

        # If Wix is still capped at 20 items, use browser infinite-scroll discovery.
        if len(combined) <= 20 and max_posts > 20:
            browser_posts = discover_wix_posts_with_browser(site_base, max_posts=max_posts)
            for url, title in browser_posts:
                if url in seen:
                    continue
                combined.append(FeedPost(url=url, title=title))
                seen.add(url)
                if len(combined) >= max_posts:
                    break

        # Always return Wix results — even if enrichment found nothing new,
        # the RSS 20 posts are more reliable than _paginate_feed on a non-feed URL.
        feed = parsed.feed
        return FeedInfo(
            title=feed.get("title", ""),
            description=feed.get("subtitle", ""),
            site_url=feed.get("link", ""),
            posts=combined[:max_posts],
        )

    # Try to paginate for more posts
    return _paginate_feed(feed_url, max_posts=max_posts)

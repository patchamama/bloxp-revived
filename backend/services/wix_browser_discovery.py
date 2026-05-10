import asyncio
import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse


def _title_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    slug = path.split("/")[-1] if path else ""
    slug = re.sub(r"[-_]+", " ", slug).strip()
    return slug[:1].upper() + slug[1:] if slug else "Untitled"


def _looks_like_post_url(url: str) -> bool:
    lowered = url.lower()
    if any(x in lowered for x in ("/category/", "/tag/", "/archive/", "/author/", "/search", "/feed")):
        return False
    return "/post/" in lowered or "/blog/" in lowered


async def _discover_async(site_url: str, max_posts: int = 250) -> list[tuple[str, str]]:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return []

    parsed = urlparse(site_url)
    base = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else site_url
    blog_url = urljoin(base, "/blog")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        collected_from_api: list[tuple[str, str]] = []
        seen_api_urls: set[str] = set()

        def _to_url_candidates(value) -> list[str]:
            if isinstance(value, str):
                v = value.strip()
                return [v] if v else []
            if isinstance(value, dict):
                path = str(value.get("path", "")).strip()
                base_u = str(value.get("base", "")).strip()
                out: list[str] = []
                if path:
                    out.append(path)
                if base_u and path:
                    out.append(base_u.rstrip("/") + "/" + path.lstrip("/"))
                full = str(value.get("url", "")).strip()
                if full:
                    out.append(full)
                return out
            return []

        async def on_response(resp) -> None:
            url = resp.url
            if "/_api/blog-frontend-adapter-public/v2/post-feed-page?" not in url:
                return
            if resp.status != 200:
                return
            try:
                payload = await resp.json()
            except Exception:
                try:
                    payload = json.loads(await resp.text())
                except Exception:
                    return

            def walk(node) -> None:
                if len(collected_from_api) >= max_posts:
                    return
                if isinstance(node, list):
                    for item in node:
                        walk(item)
                    return
                if not isinstance(node, dict):
                    return

                candidates: list[str] = []
                candidates.extend(_to_url_candidates(node.get("url")))
                candidates.extend(_to_url_candidates(node.get("link")))
                candidates.extend(_to_url_candidates(node.get("postUrl")))
                candidates.extend(_to_url_candidates(node.get("fullUrl")))
                slug = str(node.get("slug", "")).strip()
                if slug:
                    candidates.extend([f"/post/{slug}", f"/blog/post/{slug}"])

                picked: Optional[str] = None
                for c in candidates:
                    if not c:
                        continue
                    u = urljoin(base, c)
                    if _looks_like_post_url(u):
                        picked = u
                        break

                if picked and picked not in seen_api_urls:
                    seen_api_urls.add(picked)
                    title = (
                        str(node.get("title", "")).strip()
                        or str(node.get("seoTitle", "")).strip()
                        or str(node.get("postTitle", "")).strip()
                        or _title_from_url(picked)
                    )
                    collected_from_api.append((picked, title))

                for v in node.values():
                    if isinstance(v, (dict, list)):
                        walk(v)

            walk(payload)

        page.on("response", on_response)
        await page.goto(blog_url, wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(5000)

        stable_rounds = 0
        last_count = 0
        max_scrolls = 140

        for _ in range(max_scrolls):
            urls = await page.eval_on_selector_all(
                "a[href]",
                "els => els.map(a => a.getAttribute('href') || '').filter(Boolean)",
            )
            current_count = len(urls)
            if current_count <= last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                last_count = current_count

            if stable_rounds >= 8:
                break

            await page.evaluate("window.scrollBy(0, Math.floor(window.innerHeight * 1.4))")
            await page.wait_for_timeout(900)

        hrefs = await page.eval_on_selector_all(
            "a[href]",
            "els => els.map(a => ({href: a.getAttribute('href') || '', text: (a.textContent || '').trim()}))",
        )
        await browser.close()

    if len(collected_from_api) > 20:
        return collected_from_api[:max_posts]

    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in hrefs:
        raw_href = (entry.get("href") or "").strip()
        if not raw_href:
            continue
        abs_url = urljoin(base, raw_href)
        if not _looks_like_post_url(abs_url) or abs_url in seen:
            continue
        seen.add(abs_url)
        title = (entry.get("text") or "").strip() or _title_from_url(abs_url)
        out.append((abs_url, title))
        if len(out) >= max_posts:
            break
    return out


def discover_wix_posts_with_browser(site_url: str, max_posts: int = 250) -> list[tuple[str, str]]:
    try:
        return asyncio.run(_discover_async(site_url, max_posts=max_posts))
    except Exception:
        return []

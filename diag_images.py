#!/usr/bin/env python3
"""
Image diagnostic: check which article images fail to load.

Usage:
    cd bloxp-revived
    python diag_images.py                         # runs default article list
    python diag_images.py <url1> <url2> ...       # check specific articles
    python diag_images.py --feed <rss-url>        # check first N articles from a feed
"""
import sys
import httpx
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bloxp/2.0; +https://bloxp.app)"}
SELECTORS = [
    "[itemprop='articleBody']", ".post-body", ".entry-content",
    "article .entry-content", "article .post-content", ".post-content",
    "article", "main",
]
LAZY_ATTRS = ("data-src", "data-original-src", "data-lazy-src", "data-orig", "data-url", "data-original")
LAZY_PLACEHOLDERS = {"", "//:0", "about:blank", "#", "data:,"}
SKIP_FRAGMENTS = ("icon18_email", "icon18_edit", "blank.gif", "favicon",
                  "/s16/", "/s24/", "/s28/", "/s32/")

DEFAULT_ARTICLES = [
    "https://www.librosdelcrepusculo.com.mx/2020/03/los-nueve-monstruos.html",
    "https://www.librosdelcrepusculo.com.mx/2019/11/manach-y-las-aceras-y-azoteas-de-la.html",
    "https://www.librosdelcrepusculo.com.mx/2019/11/lezama-la-habana-y-los-fuegos.html",
    "https://www.librosdelcrepusculo.com.mx/2019/09/miembros-del-presidium-de-honor-del-pcm.html",
    "https://www.librosdelcrepusculo.com.mx/2019/08/glorias-trasplantadas.html",
    "https://www.librosdelcrepusculo.com.mx/2019/07/eugenio-florit-y-las-noches-de.html",
    "https://www.librosdelcrepusculo.com.mx/2018/03/miguel-marmol-explica-roque-dalton-la.html",
]


def resolve_src(img) -> str:
    src = img.get("src", "").strip()
    if src in LAZY_PLACEHOLDERS:
        for attr in LAZY_ATTRS:
            fallback = img.get(attr, "").strip()
            if fallback and fallback not in LAZY_PLACEHOLDERS:
                return fallback
    return src


def check_article(url: str, client: httpx.Client) -> None:
    print(f"\n{'='*70}")
    print(f"  {url}")
    print(f"{'='*70}")
    try:
        r = client.get(url, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"  ✗ FETCH FAILED: {e}")
        return

    soup = BeautifulSoup(r.text, "lxml")
    container = None
    matched_sel = None
    for sel in SELECTORS:
        found = soup.select_one(sel)
        if found:
            text_len = len(found.get_text(strip=True))
            has_img = bool(found.find("img"))
            if has_img or text_len > 50:
                container = found
                matched_sel = sel
                break

    if not container:
        print(f"  ✗ No article container found (tried: {', '.join(SELECTORS[:4])}...)")
        return

    text_len = len(container.get_text(strip=True))
    imgs = container.find_all("img")
    print(f"  Selector: '{matched_sel}' | text: {text_len} chars | images in HTML: {len(imgs)}")

    if not imgs:
        print("  (no images in article)")
        return

    for img in imgs:
        src = resolve_src(img)
        if not src or src.startswith("data:"):
            print(f"  SKIP  no-src / data-uri")
            continue

        # Protocol-relative → https
        if src.startswith("//"):
            src = "https:" + src

        if any(f in src for f in SKIP_FRAGMENTS):
            print(f"  SKIP  noise fragment: {src[:80]}")
            continue

        parent_a = img.find_parent("a")
        a_href = parent_a.get("href", "").strip() if parent_a else ""
        wrapped = f" [<a href={a_href[:60]}>]" if a_href else ""

        try:
            ir = client.head(src, timeout=10, follow_redirects=True)
            ct = ir.headers.get("content-type", "?").split(";")[0].strip()
            ok = "✓" if ct.startswith("image/") else f"✗ WRONG MIME ({ct})"
            print(f"  [{ir.status_code}] {ok}{wrapped}")
            print(f"         {src[:90]}")
        except Exception as e:
            print(f"  ✗ FETCH ERROR: {e}{wrapped}")
            print(f"         {src[:90]}")


def check_feed(feed_url: str, limit: int = 10) -> list[str]:
    """Return first `limit` article URLs from an RSS/Atom feed."""
    try:
        import feedparser
        f = feedparser.parse(feed_url)
        return [e.link for e in f.entries[:limit] if hasattr(e, "link")]
    except ImportError:
        print("feedparser not installed; install it with: pip install feedparser")
        return []


def main() -> None:
    args = sys.argv[1:]
    urls: list[str] = []

    if "--feed" in args:
        idx = args.index("--feed")
        feed_url = args[idx + 1] if idx + 1 < len(args) else ""
        if feed_url:
            urls = check_feed(feed_url)
        remaining = [a for i, a in enumerate(args) if i != idx and i != idx + 1]
        urls.extend(remaining)
    elif args:
        urls = args
    else:
        urls = DEFAULT_ARTICLES

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for url in urls:
            check_article(url, client)

    print("\nDone.")


if __name__ == "__main__":
    main()

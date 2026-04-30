import re

import trafilatura
from bs4 import BeautifulSoup, Tag
from readability import Document

# Strip Word/Office conditional comments before HTML parsing
_MSO_RE = re.compile(r'<!--\[if [^\]]+\]>.*?<!\[endif\]-->', re.DOTALL | re.IGNORECASE)
_XML_BLOB_RE = re.compile(r'<xml\b[^>]*>.*?</xml>', re.DOTALL | re.IGNORECASE)

# Placeholder src values used by lazy-loading scripts
_LAZY_PLACEHOLDERS = {"", "//:0", "about:blank", "#", "data:,"}
# Attributes that hold the real image URL in lazy-loaded content
_LAZY_SRC_ATTRS = ("data-src", "data-original-src", "data-lazy-src", "data-orig", "data-url")

# CSS selectors tried in order to locate the main article body
_ARTICLE_SELECTORS = [
    # Schema.org
    "[itemprop='articleBody']",
    "[itemprop='description articleBody']",
    # Blogger
    ".post-body",
    ".entry-content",
    # WordPress
    "article .entry-content",
    "article .post-content",
    ".post-content",
    # Generic
    "article",
    "main",
    ".content",
    "#content",
]

# Tags to strip from extracted content (navigation, ads, etc.)
_STRIP_TAGS = {
    "script", "style", "noscript", "iframe", "nav", "aside",
    "footer", "header", "form", "button", "select", "textarea",
}


def extract_content(html: str, url: str = "", include_images: bool = True) -> tuple[str, str | None, str]:
    """Returns (title, date_iso_or_None, clean_html_content)."""
    title = _extract_title(html)
    date = _extract_date(html)

    if include_images:
        # Direct DOM extraction preserves images; readability strips them
        content = _extract_with_selector(html)
        if content:
            return title, date, content
        # Fallback: readability (images will be missing but text is clean)
        content = _extract_with_readability(html)
        if content:
            return title, date, content

    # trafilatura: best text quality, images stripped
    text = trafilatura.extract(html, include_links=True, include_images=False, output_format="html")
    if text:
        soup = BeautifulSoup(text, "lxml")
        body = soup.find("body")
        return title, date, (body.decode_contents() if body else text)

    # Last resort
    content = _extract_with_readability(html)
    return title, date, content or "<p>No content</p>"


def _strip_mso(html: str) -> str:
    """Remove Word/Office conditional comments and XML blobs."""
    html = _MSO_RE.sub("", html)
    html = _XML_BLOB_RE.sub("", html)
    return html


def _extract_with_selector(html: str) -> str | None:
    """Find the article body using known CSS selectors, preserving images."""
    try:
        html = _strip_mso(html)
        soup = BeautifulSoup(html, "lxml")

        container: Tag | None = None
        for selector in _ARTICLE_SELECTORS:
            found = soup.select_one(selector)
            if found and len(found.get_text(strip=True)) > 200:
                container = found  # type: ignore[assignment]
                break

        if not container:
            return None

        # Strip noise tags in-place
        for tag in container.find_all(_STRIP_TAGS):
            tag.decompose()

        # Resolve lazy-loaded images: prefer data-src over placeholder src
        for img in container.find_all("img"):
            src = img.get("src", "").strip()
            if src in _LAZY_PLACEHOLDERS:
                for attr in _LAZY_SRC_ATTRS:
                    fallback = img.get(attr, "").strip()
                    if fallback and fallback not in _LAZY_PLACEHOLDERS:
                        img["src"] = fallback
                        src = fallback
                        break
            if not src or src in _LAZY_PLACEHOLDERS:
                img.decompose()

        content = container.decode_contents().strip()
        return content if len(content) > 100 else None
    except Exception:
        return None


def _extract_with_readability(html: str) -> str | None:
    try:
        doc = Document(_strip_mso(html))
        content = doc.summary()
        if not content or len(content) < 100:
            return None
        soup = BeautifulSoup(content, "lxml")
        body = soup.find("body")
        return body.decode_contents() if body else content
    except Exception:
        return None


def _extract_title(html: str) -> str:
    metadata = trafilatura.extract_metadata(html)
    if metadata and metadata.title:
        return metadata.title
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else "Untitled"


def _extract_date(html: str) -> str | None:
    try:
        metadata = trafilatura.extract_metadata(html)
        if metadata and metadata.date:
            return metadata.date  # ISO format: YYYY-MM-DD
    except Exception:
        pass
    return None

import trafilatura
from bs4 import BeautifulSoup, Tag
from readability import Document

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


def extract_content(html: str, url: str = "", include_images: bool = True) -> tuple[str, str]:
    """Returns (title, clean_html_content)."""
    title = _extract_title(html)

    if include_images:
        # Direct DOM extraction preserves images; readability strips them
        content = _extract_with_selector(html)
        if content:
            return title, content
        # Fallback: readability (images will be missing but text is clean)
        content = _extract_with_readability(html)
        if content:
            return title, content

    # trafilatura: best text quality, images stripped
    text = trafilatura.extract(html, include_links=True, include_images=False, output_format="html")
    if text:
        return title, text

    # Last resort
    content = _extract_with_readability(html)
    return title, content or "<p>No content</p>"


def _extract_with_selector(html: str) -> str | None:
    """Find the article body using known CSS selectors, preserving images."""
    try:
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

        # Strip empty src / protocol-relative srcs are kept (urljoin fixes them later)
        for img in container.find_all("img"):
            src = img.get("src", "").strip()
            if not src:
                img.decompose()

        content = container.decode_contents().strip()
        return content if len(content) > 100 else None
    except Exception:
        return None


def _extract_with_readability(html: str) -> str | None:
    try:
        doc = Document(html)
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

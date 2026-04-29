import trafilatura
from bs4 import BeautifulSoup
from readability import Document


def extract_content(html: str, url: str = "", include_images: bool = True) -> tuple[str, str]:
    """Returns (title, clean_html_content)."""
    title = _extract_title(html)

    # readability preserves images; trafilatura often strips them
    if include_images:
        content = _extract_with_readability(html, title)
        if content:
            return title, content

    # trafilatura: best text quality, images stripped
    text = trafilatura.extract(html, include_links=True, include_images=False, output_format="html")
    if text:
        return title, text

    # Last resort: readability even without image preference
    content = _extract_with_readability(html, title)
    return title, content or "<p>No content</p>"


def _extract_with_readability(html: str, title: str) -> str | None:
    try:
        doc = Document(html)
        content = doc.summary()
        if not content or len(content) < 100:
            return None
        # Strip <html>/<body> wrappers readability adds
        soup = BeautifulSoup(content, "lxml")
        body = soup.find("body")
        return str(body) if body else content
    except Exception:
        return None


def _extract_title(html: str) -> str:
    metadata = trafilatura.extract_metadata(html)
    if metadata and metadata.title:
        return metadata.title
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else "Untitled"

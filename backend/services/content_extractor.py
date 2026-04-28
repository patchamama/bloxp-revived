from typing import Optional
import trafilatura
from readability import Document


def extract_content(html: str, url: str = "") -> tuple[str, str]:
    """Returns (title, clean_html_content)."""
    # Try trafilatura first — best for modern sites
    text = trafilatura.extract(html, include_links=True, include_images=True, output_format="html")
    title = _extract_title_trafilatura(html)

    if text:
        return title, text

    # Fallback: python-readability
    doc = Document(html)
    title = doc.title() or title
    content = doc.summary()
    return title, content


def _extract_title_trafilatura(html: str) -> str:
    metadata = trafilatura.extract_metadata(html)
    if metadata and metadata.title:
        return metadata.title
    # Cheap fallback
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("title")
    return tag.get_text(strip=True) if tag else "Untitled"

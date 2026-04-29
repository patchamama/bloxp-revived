import io
import mimetypes
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from ebooklib import epub
from PIL import Image

from services.crawler import Post

# EPUB-compatible image formats
_EPUB_MIME = {
    "image/jpeg", "image/png", "image/gif", "image/svg+xml", "image/webp",
}
# Formats that need conversion to JPEG for maximum compatibility
_CONVERT_TO_JPEG = {"image/webp", "image/avif", "image/bmp", "image/tiff"}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bloxp/2.0; +https://bloxp.app)"}


def _fetch_image(url: str) -> tuple[bytes, str] | None:
    """Download image, return (bytes, mime_type) or None on failure."""
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
        mime = r.headers.get("content-type", "").split(";")[0].strip() or "image/jpeg"
        # Strip parameters from mime
        mime = mime.lower()
        return r.content, mime
    except Exception:
        return None


def _to_epub_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """Convert incompatible formats (WebP, AVIF, BMP…) to JPEG."""
    if mime in _CONVERT_TO_JPEG or mime not in _EPUB_MIME:
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue(), "image/jpeg"
        except Exception:
            pass
    return data, mime


def _ext_for_mime(mime: str) -> str:
    exts = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/svg+xml": "svg",
        "image/webp": "webp",
    }
    return exts.get(mime, mimetypes.guess_extension(mime, strict=False) or "jpg").lstrip(".")


def _embed_images(
    html: str,
    post_url: str,
    book: epub.EpubBook,
    img_counter: list[int],
) -> str:
    """Download all <img> in html, embed them in the book, rewrite src."""
    soup = BeautifulSoup(html, "lxml")

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "").strip()
        if not src or src.startswith("data:"):
            continue

        abs_url = urljoin(post_url, src)
        result = _fetch_image(abs_url)
        if not result:
            img_tag.decompose()
            continue

        raw, mime = result
        data, mime = _to_epub_image(raw, mime)
        ext = _ext_for_mime(mime)

        idx = img_counter[0]
        img_counter[0] += 1
        img_name = f"image{idx:04d}.{ext}"
        img_path = f"images/{img_name}"

        epub_img = epub.EpubImage()
        epub_img.file_name = img_path
        epub_img.media_type = mime
        epub_img.content = data
        book.add_item(epub_img)

        img_tag["src"] = f"../{img_path}"
        # Remove srcset — not supported in EPUB readers
        img_tag.attrs.pop("srcset", None)
        img_tag.attrs.pop("loading", None)

    return str(soup.body) if soup.body else str(soup)


def build_epub(
    posts: list[Post],
    title: str,
    description: str,
    output_path: Path,
    add_toc: bool = True,
    links_to_footnotes: bool = False,
    include_images: bool = True,
) -> Path:
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language("es")
    book.add_metadata("DC", "description", description)

    chapters: list[epub.EpubHtml] = []
    img_counter = [0]  # mutable counter shared across posts

    for i, post in enumerate(posts):
        content = post.content or "<p>No content</p>"

        if include_images:
            content = _embed_images(content, post.url, book, img_counter)

        if links_to_footnotes:
            content = _convert_links_to_footnotes(content)

        chapter = epub.EpubHtml(
            title=post.title,
            file_name=f"chapter_{i:04d}.xhtml",
            lang="es",
        )
        chapter.content = f"<h1>{post.title}</h1>{content}"
        book.add_item(chapter)
        chapters.append(chapter)

    book.toc = (
        [(epub.Section(post.title), [ch]) for post, ch in zip(posts, chapters)]
        if add_toc
        else chapters
    )

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(str(output_path), book)
    return output_path


def _convert_links_to_footnotes(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    footnotes: list[str] = []

    for i, a in enumerate(soup.find_all("a", href=True), 1):
        href = a["href"]
        a.replace_with(f"{a.get_text()}[{i}]")
        footnotes.append(f"[{i}] {href}")

    if footnotes:
        items = "".join(f"<li>{fn}</li>" for fn in footnotes)
        fn_html = f"<hr/><ul>{items}</ul>"
        soup.append(BeautifulSoup(fn_html, "lxml"))

    return str(soup)

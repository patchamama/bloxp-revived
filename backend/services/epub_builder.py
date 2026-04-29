import io
import mimetypes
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

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
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
        mime = r.headers.get("content-type", "").split(";")[0].strip().lower() or "image/jpeg"
        return r.content, mime
    except Exception:
        return None


# Max dimensions suitable for e-readers (600px wide covers most devices)
_EPUB_MAX_WIDTH = 800
_EPUB_MAX_HEIGHT = 1200


def _to_epub_image(data: bytes, mime: str) -> tuple[bytes, str]:
    """Convert to JPEG if needed, resize to e-reader dimensions, optimize quality."""
    needs_convert = mime in _CONVERT_TO_JPEG or mime not in _EPUB_MIME
    try:
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        elif img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            img = bg

        # Resize if larger than e-reader screen — preserve aspect ratio
        if img.width > _EPUB_MAX_WIDTH or img.height > _EPUB_MAX_HEIGHT:
            img.thumbnail((_EPUB_MAX_WIDTH, _EPUB_MAX_HEIGHT), Image.LANCZOS)

        buf = io.BytesIO()
        if needs_convert or img.mode == "RGB":
            img.save(buf, format="JPEG", quality=82, optimize=True)
            return buf.getvalue(), "image/jpeg"
        else:
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue(), "image/png"
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
    return exts.get(mime, (mimetypes.guess_extension(mime, strict=False) or ".jpg")).lstrip(".")


# Blogger/WordPress UI noise — not article content
_SKIP_URL_FRAGMENTS = (
    "icon18_email", "icon18_edit", "blank.gif", "favicon",
    "s16/", "s24/", "s28/", "s32/",
)


def _embed_images(
    html: str,
    post_url: str,
    book: epub.EpubBook,
    img_counter: list[int],
    on_image: Callable[[int], None] | None = None,
) -> str:
    """Download all <img> in html, embed in book, rewrite src to relative path."""
    soup = BeautifulSoup(html, "lxml")

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "").strip()
        if not src or src.startswith("data:"):
            img_tag.decompose()
            continue

        abs_url = urljoin(post_url, src)

        if any(frag in abs_url for frag in _SKIP_URL_FRAGMENTS):
            img_tag.decompose()
            continue

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

        if on_image:
            on_image(img_counter[0])

        img_tag["src"] = img_path
        img_tag.attrs.pop("srcset", None)
        img_tag.attrs.pop("loading", None)

    return soup.body.decode_contents() if soup.body else str(soup)


_INLINE_TAGS = {"a", "abbr", "acronym", "b", "bdo", "big", "br", "cite", "code",
                "dfn", "em", "i", "img", "input", "kbd", "label", "map", "object",
                "output", "q", "samp", "select", "small", "span", "strong", "sub",
                "sup", "textarea", "time", "tt", "u", "var"}

_BLOCK_TAGS = {"address", "article", "aside", "blockquote", "canvas", "dd", "div",
               "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
               "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
               "nav", "noscript", "ol", "p", "pre", "section", "table", "tfoot",
               "thead", "tbody", "tr", "td", "th", "ul", "video"}


def _div_is_paragraph(tag) -> bool:
    """True when a <div> contains only inline content (text + inline tags) — should be a <p>."""
    for child in tag.children:
        if hasattr(child, "name") and child.name and child.name.lower() in _BLOCK_TAGS:
            return False
    return bool(tag.get_text(strip=True))


def _clean_content(html: str) -> str:
    """Normalize HTML for epub: convert text-only divs to <p>, remove empty paragraphs."""
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    root = body if body else soup

    # Isolate images: unwrap <a> around <img>, convert image containers to <figure>
    for div in root.find_all("div"):
        img = div.find("img")
        if img and not div.get_text(strip=True):
            # Unwrap any <a> around the img
            for a in div.find_all("a"):
                if a.find("img"):
                    a.unwrap()
            div.name = "figure"

    # Convert inline-only <div> → <p> so readers don't break mid-sentence at block boundaries
    for div in root.find_all("div"):
        if _div_is_paragraph(div):
            div.name = "p"

    # Remove empty <p> and <div> (only whitespace / <br>)
    for tag in root.find_all(["p", "div"]):
        if not tag.get_text(strip=True) and not tag.find(["img", "figure"]):
            tag.decompose()

    return root.decode_contents() if body else str(root)


def build_epub(
    posts: list[Post],
    title: str,
    description: str,
    output_path: Path,
    add_toc: bool = True,
    links_to_footnotes: bool = False,
    include_images: bool = True,
    on_image: Callable[[int], None] | None = None,
) -> Path:
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language("es")
    book.add_metadata("DC", "description", description)

    chapters: list[epub.EpubHtml] = []
    img_counter = [0]

    for i, post in enumerate(posts):
        content = post.content or "<p>No content</p>"

        if include_images:
            content = _embed_images(content, post.url, book, img_counter, on_image=on_image)

        content = _clean_content(content)

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

    if add_toc:
        # Flat list of direct links — each post is one clickable TOC entry
        book.toc = [
            epub.Link(ch.file_name, post.title, f"chapter_{i}")
            for i, (post, ch) in enumerate(zip(posts, chapters))
        ]
    else:
        book.toc = chapters

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

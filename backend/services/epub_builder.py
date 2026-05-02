import io
import mimetypes
import re
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

# Extensions that identify an image URL
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif", ".bmp", ".tiff"}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Bloxp/2.0; +https://bloxp.app)"}


def _fetch_image(url: str, referer: str = "") -> tuple[bytes, str] | None:
    headers = {**HEADERS}
    if referer:
        headers["Referer"] = referer
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
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
# Use leading slash so "/s16/" only matches a complete path segment, not a hash like "AAAAAAAAs16/"
_SKIP_URL_FRAGMENTS = (
    "icon18_email", "icon18_edit", "blank.gif", "favicon",
    "/s16/", "/s24/", "/s28/", "/s32/",
)

# Lazy-load placeholder src values used by many CMS templates
_LAZY_PLACEHOLDERS = {"", "//:0", "about:blank", "#", "data:,"}
# Attributes that hold the real image URL in lazy-loaded content
_LAZY_SRC_ATTRS = ("data-src", "data-original-src", "data-lazy-src", "data-orig", "data-url")


def _embed_images(
    html: str,
    post_url: str,
    book: epub.EpubBook,
    img_counter: list[int],
    on_image: Callable[[int], None] | None = None,
    image_cache: dict | None = None,
) -> str:
    """Download all <img> in html, embed in book, rewrite src to relative path.

    image_cache: if provided, stores url -> (data, mime) for reuse in PDF generation.
    """
    soup = BeautifulSoup(html, "lxml")

    for img_tag in soup.find_all("img"):
        src = img_tag.get("src", "").strip()
        # Resolve lazy-loaded images: prefer data-src over placeholder src
        if src in _LAZY_PLACEHOLDERS:
            for attr in _LAZY_SRC_ATTRS:
                fallback = img_tag.get(attr, "").strip()
                if fallback and fallback not in _LAZY_PLACEHOLDERS:
                    src = fallback
                    break
        if not src or src in _LAZY_PLACEHOLDERS or src.startswith("data:"):
            _decompose_with_wrapper(img_tag)
            continue

        abs_url = urljoin(post_url, src)

        if any(frag in abs_url for frag in _SKIP_URL_FRAGMENTS):
            _decompose_with_wrapper(img_tag)
            continue

        img_parent = img_tag.parent  # capture before possible decompose

        if image_cache is not None and abs_url in image_cache:
            data, mime = image_cache[abs_url]
        else:
            result = _fetch_image(abs_url, referer=post_url)
            if not result:
                _decompose_with_wrapper(img_tag)
                continue
            raw, mime = result
            if not mime.startswith("image/"):
                _decompose_with_wrapper(img_tag)
                continue
            data, mime = _to_epub_image(raw, mime)
            if image_cache is not None:
                image_cache[abs_url] = (data, mime)

        ext = _ext_for_mime(mime)
        idx = img_counter[0]
        img_counter[0] += 1
        img_name = f"image{idx:04d}.{ext}"
        img_path = f"images/{img_name}"

        # Also index by epub-relative path so pdf_builder can look up by src
        if image_cache is not None:
            image_cache[img_path] = (data, mime)

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
        img_tag.attrs.pop("width", None)
        img_tag.attrs.pop("height", None)

        # Size: content images (≥150px) get minimum 1/3 width; icons stay auto
        try:
            pil_img = Image.open(io.BytesIO(data))
            is_content = pil_img.width >= 150 or pil_img.height >= 150
        except Exception:
            is_content = True
        if is_content:
            img_tag["style"] = "min-width:33%;width:auto;max-width:66%;height:auto;display:block;margin:0.5em auto"
        else:
            img_tag["style"] = "width:auto;height:auto;max-width:66%;display:block;margin:0.5em auto"

    # Remove any empty wrappers left behind by failed image fetches
    root = soup.body if soup.body else soup
    for tag in root.find_all(["p", "div", "figure"]):
        if tag.parent is None:
            continue
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()

    return soup.body.decode_contents() if soup.body else str(soup)


def _decompose_with_wrapper(img_tag) -> None:
    """Decompose an img tag and also remove its wrapper if it becomes empty."""
    parent = img_tag.parent
    img_tag.decompose()
    if parent and parent.parent is not None:
        classes = parent.get("class") or []
        if "img-block" in classes or parent.name == "figure":
            if not parent.get_text(strip=True) and not parent.find("img"):
                parent.decompose()


_INLINE_TAGS = {"a", "abbr", "acronym", "b", "bdo", "big", "br", "cite", "code",
                "dfn", "em", "i", "img", "input", "kbd", "label", "map", "object",
                "output", "q", "samp", "select", "small", "span", "strong", "sub",
                "sup", "textarea", "time", "tt", "u", "var"}

_BLOCK_TAGS = {"address", "article", "aside", "blockquote", "canvas", "dd", "div",
               "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
               "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
               "nav", "noscript", "ol", "p", "pre", "section", "table", "tfoot",
               "thead", "tbody", "tr", "td", "th", "ul", "video"}


_REF_RE = re.compile(r'(\[\d+\])(?!\s)')  # [N] not followed by whitespace

_URL_RE = re.compile(
    r'(?<!["\'=>])'
    r'(https?://[^\s<>"\')\].,;:!?]+(?:[.,;:!?][^\s<>"\')\].,;:!?]+)*'
    r'|www\.[^\s<>"\')\].,;:!?]+(?:[.,;:!?][^\s<>"\')\].,;:!?]+)*\.[a-z]{2,}[^\s<>"\')\]]*)',
    re.IGNORECASE,
)


def _linkify_text_nodes(root) -> None:
    """Replace bare URLs in text nodes with <a href="..."> tags."""
    from bs4 import NavigableString, Tag

    for node in list(root.descendants):
        if not isinstance(node, NavigableString):
            continue
        # Skip nodes already inside an <a>
        if any(p.name == "a" for p in node.parents if hasattr(p, "name")):
            continue
        text = str(node)
        if not _URL_RE.search(text):
            continue

        parts = _URL_RE.split(text)
        if len(parts) <= 1:
            continue

        new_nodes = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # odd indices are the captured URL groups
                href = part if part.startswith("http") else f"https://{part}"
                a_tag = Tag(name="a")
                a_tag["href"] = href
                a_tag.string = part
                new_nodes.append(a_tag)
            else:
                if part:
                    new_nodes.append(NavigableString(part))

        parent = node.parent
        if parent is None:
            continue
        idx = list(parent.children).index(node)
        node.extract()
        for j, new_node in enumerate(new_nodes):
            parent.insert(idx + j, new_node)


def _is_image_url(url: str) -> bool:
    path = url.split("?")[0].split("#")[0].lower()
    return any(path.endswith(ext) for ext in _IMAGE_EXTENSIONS)


def _expand_image_links(root) -> None:
    """Handle <a href="image-url"> links.

    - <a href="img.jpg"><img src="thumb.jpg"></a> → unwrap, keep existing <img> (avoid
      fetching a potentially inaccessible full-res URL when the thumbnail already works).
    - <a href="img.jpg">text or nothing</a> → <img src="img.jpg">
    """
    from bs4 import Tag
    for a in list(root.find_all("a", href=True)):
        href = a.get("href", "").strip()
        if not href or not _is_image_url(href):
            continue
        inner_img = a.find("img")
        if inner_img:
            a.replace_with(inner_img)
            continue
        img = Tag(name="img")
        img["src"] = href
        alt = a.get_text(strip=True)
        if alt and not _is_image_url(alt):
            img["alt"] = alt
        a.replace_with(img)


def _fix_reference_spacing(root) -> None:
    """Ensure a space follows every [N] reference marker in text nodes."""
    from bs4 import NavigableString
    for node in root.find_all(string=_REF_RE):
        if isinstance(node, NavigableString):
            node.replace_with(_REF_RE.sub(r'\1 ', str(node)))


def _div_is_paragraph(tag) -> bool:
    """True when a <div> contains only inline content (text + inline tags) — should be a <p>."""
    for child in tag.children:
        if hasattr(child, "name") and child.name and child.name.lower() in _BLOCK_TAGS:
            return False
    return bool(tag.get_text(strip=True))


def _wrap_loose_paragraphs(root) -> None:
    """Wrap loose text/inline nodes at root level into <p> tags.

    Old Blogger posts use bare text nodes + <br> separators as direct children
    of the body element instead of <p> tags. This function detects that pattern
    and re-wraps the content so CSS paragraph rules (indent, margin) apply.
    """
    from bs4 import NavigableString, Tag

    _WRAP_INLINE = frozenset({
        "a", "abbr", "acronym", "b", "big", "cite", "code", "em", "i",
        "small", "span", "strong", "sub", "sup", "time", "tt", "u",
    })

    def _has_content(items: list) -> bool:
        for x in items:
            if isinstance(x, NavigableString) and str(x).strip():
                return True
            if hasattr(x, "name") and x.name not in ("br",) and x.get_text(strip=True):
                return True
        return False

    def _flush(acc: list, anchor) -> None:
        if not _has_content(acc):
            for x in acc:
                if x.parent is not None:
                    x.extract()
            return
        p = Tag(name="p")
        for x in acc:
            if x.parent is not None:
                x.extract()
            p.append(x)
        anchor.insert_before(p)

    # Only act when there are actual loose text/inline nodes at root level.
    # If all content is already in block elements, skip entirely.
    has_loose = any(
        isinstance(c, NavigableString) and str(c).strip()
        or (hasattr(c, "name") and c.name in _WRAP_INLINE)
        for c in root.children
    )
    if not has_loose:
        return

    sentinel = Tag(name="div")
    sentinel["data-sentinel"] = "1"
    root.append(sentinel)

    acc: list = []
    for child in list(root.children):
        if child is sentinel:
            _flush(acc, sentinel)
            acc = []
            continue
        if isinstance(child, NavigableString):
            acc.append(child)
        elif hasattr(child, "name"):
            if child.name == "br":
                _flush(acc, child)
                acc = []
                child.extract()
            elif child.name in _WRAP_INLINE:
                acc.append(child)
            else:
                # Block element — flush pending buffer before it
                _flush(acc, child)
                acc = []

    sentinel.extract()


_DOUBLE_SPACE_RE = re.compile(r'  +')
# Word/Office conditional comments pasted into blog posts (<!--[if mso]>...<![endif]-->)
_MSO_COMMENT_RE = re.compile(r'<!--\[if [^\]]+\]>.*?<!\[endif\]-->', re.DOTALL | re.IGNORECASE)
# Naked XML blobs that survive comment stripping
_MSO_XML_RE = re.compile(r'<xml\b[^>]*>.*?</xml>', re.DOTALL | re.IGNORECASE)
_MSO_STYLE_RE = re.compile(r'<style\b[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)


# Classes generated by our own pipeline — must survive stripping
_OUR_CLASSES = frozenset({
    "img-block", "verse-block", "verse-stanza",
    "post-date", "quoted-para", "original-url",
    "footnotes", "footnote-ref", "video-embed",
})


def _strip_inline_styles(root) -> None:
    """Remove inline style/font attrs, CMS class names, and bare wrapper tags."""
    for tag in root.find_all(True):
        tag.attrs.pop("style", None)
        tag.attrs.pop("size", None)
        tag.attrs.pop("face", None)
        tag.attrs.pop("color", None)
        tag.attrs.pop("align", None)
        tag.attrs.pop("bgcolor", None)
        tag.attrs.pop("dir", None)
        tag.attrs.pop("lang", None)
        if tag.name == "img":
            tag.attrs.pop("width", None)
            tag.attrs.pop("height", None)
        # Strip CMS class names; keep only classes our CSS actually uses
        if "class" in tag.attrs:
            classes = tag.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            kept = [c for c in classes if c in _OUR_CLASSES]
            if kept:
                tag["class"] = kept
            else:
                del tag.attrs["class"]

    # Unwrap <span> and <font> tags left with no attributes — they were purely
    # decorative/CMS wrappers (color, size, font-family) now stripped.
    # Semantic tags (<em>, <i>, <strong>, <b>, <u>, <sup>, <sub>) are left intact.
    for tag in list(root.find_all(["span", "font"])):
        if tag.parent is not None and not tag.attrs:
            tag.unwrap()


def _collapse_double_spaces(root) -> None:
    """Collapse runs of spaces in text nodes to a single space."""
    from bs4 import NavigableString
    for node in root.find_all(string=True):
        if isinstance(node, NavigableString) and "  " in str(node):
            node.replace_with(_DOUBLE_SPACE_RE.sub(" ", str(node)))


_IMG_WRAPPER_STYLE = "text-align:center;margin:1em auto"


def _isolate_images(root) -> None:
    """Ensure every <img> lives alone in its own <p>, centered, with no sibling text.

    Strategy: for each <img> found anywhere in the tree, if its immediate parent
    contains other content (text or elements), extract the <img> and insert a
    standalone <p><img></p> block right before the parent.  Then clean up the
    parent if it becomes empty.
    """
    from bs4 import NavigableString, Tag

    for img in list(root.find_all("img")):
        parent = img.parent
        if parent is None:
            continue

        # Already the sole child of a block-level wrapper → just rename to <p>
        siblings = [c for c in parent.children
                    if not (isinstance(c, NavigableString) and not c.strip())]
        if len(siblings) == 1 and siblings[0] is img:
            if parent.name not in ("body", "html", "[document]"):
                parent.name = "p"
                parent["style"] = _IMG_WRAPPER_STYLE
            continue

        # Extract <img> from its parent and insert a <p><img></p> block.
        wrapper = Tag(name="p")
        wrapper["class"] = ["img-block"]
        wrapper["style"] = _IMG_WRAPPER_STYLE

        # If the img is a direct child of the root/body element, replace it in-place
        # (insert_before on body would put the wrapper outside the body tag).
        if parent.name in ("body", "html", "[document]"):
            img.replace_with(wrapper)
            wrapper.append(img)
            continue

        img.extract()
        wrapper.append(img)

        # Find the nearest block ancestor to insert next to
        anchor = parent
        while anchor.parent and anchor.parent.name in ("a", "span", "em", "strong",
                                                        "b", "i", "u", "small", "sup", "sub"):
            anchor = anchor.parent

        anchor.insert_before(wrapper)

        # Remove parent if it is now empty (only whitespace left)
        if not parent.get_text(strip=True) and not parent.find(["img", "figure"]):
            parent.decompose()


# ── Date formatting ──────────────────────────────────────────────────────────

_MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _fmt_date(iso_date: str) -> str:
    """Format ISO date (YYYY-MM-DD) to Spanish long form."""
    try:
        y, m, d = iso_date.split("-")
        return f"{int(d)} de {_MONTHS_ES[int(m) - 1]} de {y}"
    except Exception:
        return iso_date


# ── Verse detection ───────────────────────────────────────────────────────────

_SENTENCE_ENDING = re.compile(r'[.!?]["»”)]*\s*$')


def _is_verse_line(text: str) -> bool:
    text = text.strip()
    return bool(text) and len(text) <= 120 and not _SENTENCE_ENDING.search(text)


def _add_class(tag, cls: str) -> None:
    existing = tag.get("class") or []
    if isinstance(existing, str):
        existing = [existing]
    if cls not in existing:
        tag["class"] = existing + [cls]


def _split_br_lines(tag) -> list[str]:
    """Return text segments separated by <br> tags anywhere inside tag."""
    from bs4 import NavigableString
    segments: list[str] = []
    current: list[str] = []

    def walk(node) -> None:
        if isinstance(node, NavigableString):
            current.append(str(node))
        elif hasattr(node, "name"):
            if node.name == "br":
                segments.append("".join(current).strip())
                current.clear()
            else:
                for child in node.children:
                    walk(child)

    for child in tag.children:
        walk(child)
    segments.append("".join(current).strip())
    return segments


def _normalize_verse_wrapper_lines(wrapper, soup) -> None:
    """Convert line-per-<p> verse wrappers into stanza paragraphs with <br/> line breaks.

    Output shape inside .verse-block:
    - One <p> per stanza, with lines separated by <br/>
    - One empty <p class="verse-stanza"> between stanzas
    """
    from bs4 import NavigableString

    children = list(wrapper.children)
    if not children:
        return

    built: list = []
    stanza_p = soup.new_tag("p")
    stanza_has_content = False
    emitted_lines: list[str] = []

    def _norm_line(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()

    def _flush_stanza() -> None:
        nonlocal stanza_p, stanza_has_content
        if stanza_has_content:
            built.append(stanza_p)
        stanza_p = soup.new_tag("p")
        stanza_has_content = False

    def _append_line_from(tag) -> None:
        nonlocal stanza_has_content
        # Convert paragraph content to logical verse lines split by <br>,
        # then drop leading lines that are duplicated from the tail of
        # already-emitted content (common in some Blogger verse markup).
        raw = tag.get_text("\n", strip=True)
        lines = [_norm_line(ln) for ln in raw.split("\n") if _norm_line(ln)]
        if not lines:
            return

        max_k = min(len(lines), len(emitted_lines))
        overlap = 0
        for k in range(max_k, 1, -1):
            if emitted_lines[-k:] == lines[:k]:
                overlap = k
                break
        if overlap:
            lines = lines[overlap:]
            if not lines:
                return

        for line in lines:
            if stanza_has_content:
                stanza_p.append(soup.new_tag("br"))
            stanza_p.append(line)
            stanza_has_content = True
            emitted_lines.append(line)

    for child in children:
        if isinstance(child, NavigableString) and not child.strip():
            child.extract()
            continue
        if not (hasattr(child, "name") and child.name == "p"):
            # Keep unexpected nodes as-is after flushing current stanza
            _flush_stanza()
            built.append(child.extract() if child.parent is not None else child)
            continue

        is_empty = not child.get_text(strip=True) and not child.find(["img", "figure"])
        if is_empty:
            child.decompose()
            _flush_stanza()
            if built and "verse-stanza" not in (built[-1].get("class") or []):
                sep = soup.new_tag("p")
                sep["class"] = ["verse-stanza"]
                built.append(sep)
            continue

        _append_line_from(child)
        child.decompose()

    _flush_stanza()

    # Remove leading/trailing stanza separators
    while built and hasattr(built[0], "get") and "verse-stanza" in (built[0].get("class") or []):
        built.pop(0)
    while built and hasattr(built[-1], "get") and "verse-stanza" in (built[-1].get("class") or []):
        built.pop()

    # Final pass: trim duplicated line prefixes between consecutive stanza paragraphs.
    prev_lines: list[str] | None = None
    for node in built:
        if not hasattr(node, "name") or node.name != "p":
            continue
        if "verse-stanza" in (node.get("class") or []):
            continue
        lines = [_norm_line(ln) for ln in node.get_text("\n", strip=True).split("\n") if _norm_line(ln)]
        if not lines:
            continue
        if prev_lines:
            max_k = min(len(prev_lines), len(lines))
            overlap = 0
            for k in range(max_k, 1, -1):
                if prev_lines[-k:] == lines[:k]:
                    overlap = k
                    break
            if overlap:
                lines = lines[overlap:]
                if not lines:
                    node.decompose()
                    continue
                node.clear()
                for i, line in enumerate(lines):
                    if i:
                        node.append(soup.new_tag("br"))
                    node.append(line)
        prev_lines = lines

    wrapper.clear()
    for node in built:
        if getattr(node, "parent", None) is None:
            wrapper.append(node)


def _detect_verse_blocks(root, soup) -> None:
    """Mark verse content with class 'verse-block'.

    Case 1 — element with 3+ <br> where majority of lines are verse-like.
    Case 2 — sequence of 4+ consecutive <p> that are short and mostly verse-like.
    """
    from bs4 import NavigableString

    # Case 1: <br>-based verse in a single element
    for tag in root.find_all(["p", "div", "blockquote"]):
        if len(tag.find_all("br")) < 3:
            continue
        lines = _split_br_lines(tag)
        non_empty = [l for l in lines if l]
        if len(non_empty) < 3:
            continue
        verse_ratio = sum(1 for l in non_empty if _is_verse_line(l)) / len(non_empty)
        if verse_ratio <= 0.55:
            continue
        _add_class(tag, "verse-block")
        # Normalize <br> runs at each level of the verse element:
        #   2 <br>  (double-spaced line) → 1 <br>  (simple verse line separator)
        #   3+ <br> (stanza break)       → 2 <br>  (visible gap between stanzas)
        def _flush_br_run(run: list) -> None:
            n = len(run)
            if n == 2:
                run[-1].decompose()
            elif n > 2:
                for extra in run[2:]:
                    extra.decompose()

        br_run: list = []
        for child in list(tag.children):
            if hasattr(child, "name") and child.name == "br":
                br_run.append(child)
            elif isinstance(child, NavigableString) and not child.strip():
                continue
            else:
                _flush_br_run(br_run)
                br_run = []
        _flush_br_run(br_run)

    def _is_stanza_div(node) -> bool:
        """Blogger stanza separator: <div> with only <br> children and no text."""
        if not (hasattr(node, "name") and node.name == "div"):
            return False
        if node.get_text(strip=True):
            return False
        kids = [c for c in node.children
                if not (isinstance(c, NavigableString) and not c.strip())]
        return bool(kids) and all(getattr(c, "name", None) == "br" for c in kids)

    # Case 2: run of 4+ consecutive <p> elements (single stanza-break <div>s allowed
    # between lines; 2+ consecutive stanza-break divs = section separator → stop run)
    seen: set[int] = set()
    for p in list(root.find_all("p")):
        if id(p) in seen:
            continue
        if p.find_parent(class_="verse-block"):
            continue
        # Only start a run from a line that looks like verse — prevents prose paragraphs
        # (e.g. editorial intros) from anchoring a run that then captures the real poem.
        if not _is_verse_line(p.get_text(strip=True)):
            continue

        run: list = [p]
        node = p.next_sibling
        while node is not None:
            if isinstance(node, NavigableString) and not node.strip():
                node = node.next_sibling
                continue
            if hasattr(node, "name"):
                if node.name == "p":
                    run.append(node)
                    node = node.next_sibling
                elif _is_stanza_div(node):
                    # Peek ahead: 2+ consecutive stanza divs = section separator → stop
                    stanza_run = [node]
                    look = node.next_sibling
                    while look is not None:
                        if isinstance(look, NavigableString) and not look.strip():
                            look = look.next_sibling
                            continue
                        if _is_stanza_div(look):
                            stanza_run.append(look)
                            look = look.next_sibling
                        else:
                            break
                    if len(stanza_run) > 1:
                        break
                    run.append(stanza_run[0])
                    node = look
                else:
                    break
            else:
                break

        # Require 4+ actual verse-line <p> elements (empty stanza separators don't count)
        p_count = sum(1 for el in run
                      if hasattr(el, "name") and el.name == "p" and el.get_text(strip=True))
        if p_count < 4:
            continue

        texts = [el.get_text(strip=True) for el in run
                 if hasattr(el, "name") and el.name == "p"]
        non_empty_texts = [t for t in texts if t]
        if not non_empty_texts:
            continue
        avg_len = sum(len(t) for t in non_empty_texts) / len(non_empty_texts)
        if avg_len > 100:
            continue
        verse_ratio = sum(1 for t in non_empty_texts if _is_verse_line(t)) / len(non_empty_texts)
        if verse_ratio < 0.45:
            continue

        # Wrap the run in a verse-block div
        wrapper = soup.new_tag("div")
        wrapper["class"] = ["verse-block"]
        run[0].insert_before(wrapper)
        prev_was_stanza = False
        for el in run:
            seen.add(id(el))
            # Stanza-break div → convert to empty <p> then treat as stanza separator
            if hasattr(el, "name") and el.name == "div":
                el.name = "p"
                for br in list(el.find_all("br")):
                    br.decompose()
            is_empty = not el.get_text(strip=True)
            if is_empty:
                if prev_was_stanza:
                    el.extract()  # collapse consecutive stanza separators
                    continue
                _add_class(el, "verse-stanza")
            prev_was_stanza = is_empty
            wrapper.append(el.extract())

    # Also normalize any pre-existing verse wrappers from source HTML.
    for wrapper in root.find_all(class_="verse-block"):
        _normalize_verse_wrapper_lines(wrapper, soup)


# ── Quoted-paragraph detection ────────────────────────────────────────────────

_OPEN_QUOTES = '"«“'
_CLOSE_QUOTE_RE = re.compile(r'["”»]\.?$')
_INNER_QUOTE_RE = re.compile(r'["“”«»]')


def _mark_quoted_paragraphs(root) -> None:
    """Add class 'quoted-para' to paragraphs that are a single uninterrupted quoted passage."""
    for p in root.find_all("p"):
        text = p.get_text(strip=True)
        if not text or text[0] not in _OPEN_QUOTES:
            continue
        if not _CLOSE_QUOTE_RE.search(text):
            continue
        # No internal quote marks (would indicate dialog, not a single quote block)
        inner = text[1:-1]
        if _INNER_QUOTE_RE.search(inner):
            continue
        _add_class(p, "quoted-para")


def _split_br_paragraphs(root) -> None:
    """Split <p>/<div> with direct <br> children into multiple <p> elements.

    <br> run rules:
    - 1-2 consecutive <br> → tight line separator (just split, no extra empty <p>)
    - 3+ consecutive <br> → stanza break → insert empty <p> between segments

    An empty <p> is appended after each split to mark the original element
    boundary as a stanza separator. _detect_verse_blocks promotes it to
    verse-stanza; empty-node cleanup removes it otherwise.

    Elements with no text content (e.g. <div><br/></div>) are left untouched —
    _detect_verse_blocks / _is_stanza_div handles them as stanza separators.
    """
    from bs4 import NavigableString, Tag

    for tag in list(root.find_all(["p", "div"])):
        if tag.parent is None:
            continue
        if not any(hasattr(c, "name") and c.name == "br" for c in tag.children):
            continue
        if any(hasattr(c, "name") and c.name in _BLOCK_TAGS and c.name != "br"
               for c in tag.children):
            continue
        # Skip elements with no text — stanza-break placeholders like <div><br/></div>
        # are preserved for _detect_verse_blocks to handle via _is_stanza_div.
        if not tag.get_text(strip=True):
            continue

        children_snap = list(tag.children)
        segments: list[tuple[list, int]] = []  # (content_nodes, br_run_after)
        current: list = []
        br_run = 0

        for child in children_snap:
            if hasattr(child, "name") and child.name == "br":
                br_run += 1
            else:
                if br_run > 0:
                    segments.append((current, br_run))
                    current = []
                    br_run = 0
                current.append(child)
        segments.append((current, 0))

        if len(segments) <= 1:
            continue

        for i, (seg_nodes, br_after) in enumerate(segments):
            p = Tag(name="p")
            for node in seg_nodes:
                p.append(node.extract() if node.parent is not None else node)
            if p.get_text(strip=True) or p.find(True):
                tag.insert_before(p)
            # 3+ consecutive <br> = stanza break → empty <p> between segments
            if br_after >= 3 and i < len(segments) - 1:
                tag.insert_before(Tag(name="p"))

        # Empty <p> marks original element boundary as stanza separator
        tag.insert_before(Tag(name="p"))
        tag.decompose()


def _remove_social_share_links(root) -> None:
    """Remove social-share links (?share=twitter/facebook/email) and empty containers."""
    for a in list(root.find_all("a", href=True)):
        if a.parent is None:
            continue
        href = a.get("href", "")
        if not any(p in href for p in ("share=twitter", "share=facebook", "share=email",
                                        "?share=", "&share=")):
            continue
        parent = a.parent
        a.decompose()
        if parent and parent.parent is not None:
            if not parent.get_text(strip=True) and not parent.find("img"):
                parent.decompose()


# ── Main HTML normalizer ──────────────────────────────────────────────────────


def _clean_content(html: str) -> str:
    """Normalize HTML for epub: convert text-only divs to <p>, remove empty paragraphs."""
    # Strip Word/Office conditional comments and XML blobs before parsing
    html = _MSO_COMMENT_RE.sub("", html)
    html = _MSO_XML_RE.sub("", html)
    html = _MSO_STYLE_RE.sub("", html)

    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    root = body if body else soup

    # Links whose href points to an image → convert to <img> so they get embedded
    _expand_image_links(root)

    # Remove social-share noise early so it doesn't pollute verse/paragraph detection
    _remove_social_share_links(root)

    # Convert inline-only <div> → <p> so readers don't break mid-sentence at block boundaries
    for div in root.find_all("div"):
        if _div_is_paragraph(div):
            div.name = "p"

    # Split <p>/<div> with direct <br> children into separate <p> elements.
    # This normalises all br-delimited content before verse detection runs.
    _split_br_paragraphs(root)

    # Old Blogger: bare text + <br> at body level — wrap into <p> tags
    _wrap_loose_paragraphs(root)

    # Move every <img> into its own <p> block — must run before empty-node cleanup
    _isolate_images(root)

    # Detect verse blocks BEFORE empty-node cleanup so stanza-separator <p>s survive
    _detect_verse_blocks(root, soup)

    # Remove empty <p> and <div> — but preserve verse stanza separators
    for tag in root.find_all(["p", "div"]):
        if tag.parent is None:  # already decomposed as child of a decomposed parent
            continue
        if "verse-stanza" in (tag.get("class") or []):
            continue
        if not tag.get_text(strip=True) and not tag.find(["img", "figure"]):
            tag.decompose()

    _strip_inline_styles(root)
    _linkify_text_nodes(root)
    _fix_reference_spacing(root)
    _collapse_double_spaces(root)
    _mark_quoted_paragraphs(root)

    return root.decode_contents() if body else str(root)


_EPUB_CSS = """
body {
    font-family: Georgia, serif;
    font-size: 1em;
    line-height: 1.7;
    margin: 1em 2em;
    color: #111;
}
h1 { font-size: 1.6em; font-weight: bold; margin: 1.2em 0 0.6em; line-height: 1.3; }
h2 { font-size: 1.3em; font-weight: bold; margin: 1em 0 0.4em; }
h3, h4, h5, h6 { font-size: 1.1em; font-weight: bold; margin: 0.8em 0 0.3em; }
p  {
    font-size: 1em;
    margin: 0 0 0.75em;
    text-align: justify;
    text-indent: 1.2em;
}
li { font-size: 1em; margin: 0.3em 0; }
blockquote { font-size: 1em; margin: 1em 2em; font-style: italic; text-indent: 0; }
a  { color: #1a0dab; text-decoration: underline; }
figure, p.img-block {
    display: block;
    text-align: center;
    margin: 1.5em auto;
    text-indent: 0;
}
figure img, p.img-block img, img {
    display: block;
    max-width: 66%;
    width: auto;
    height: auto;
    margin: 0.5em auto;
}
hr { margin: 1.5em 0; border: none; border-top: 1px solid #ccc; }
ul, ol { margin: 0.5em 0 0.5em 1.5em; padding: 0; }
/* No indent after headings or on special blocks */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p { text-indent: 0; }
p:first-child { text-indent: 0; }
/* Strip inline font-size overrides set by blog CMS */
* { font-size: inherit !important; }
h1 { font-size: 1.6em !important; }
h2 { font-size: 1.3em !important; }
h3, h4, h5, h6 { font-size: 1.1em !important; }
/* Post date line */
.post-date {
    font-size: 0.8em !important;
    text-align: right;
    color: #666;
    margin: -0.3em 0 1.2em;
    font-style: italic;
    text-indent: 0;
}
/* Quoted paragraph (starts and ends with quote mark, no internal quotes) */
.quoted-para { font-size: 0.875em !important; text-indent: 0; }
/* Verse blocks — tight line-height, override body 1.7 */
.verse-block {
    margin: 1em 0 1em 2em;
    text-align: left;
    line-height: 1.3 !important;
}
p.verse-block { text-indent: 0; }
.verse-block p {
    margin: 0;
    text-indent: 0;
    text-align: left;
    line-height: 1.3 !important;
}
/* Stanza separator: visible gap between stanzas */
.verse-block p.verse-stanza { margin: 0.7em 0 !important; }
/* Footnote reference superscripts */
.footnote-ref {
    font-size: 0.75em !important;
    vertical-align: super;
    text-decoration: none;
}
ul.footnotes { font-size: 0.9em !important; margin-top: 1em; }
.original-url { font-size: 0.85em !important; margin-top: 0.6em; color: #555; font-style: italic; text-indent: 0; }
.original-url a { color: #555; }
ul.footnotes p, ul.footnotes li { text-indent: 0; }
/* Video embed placeholder */
.video-embed { display: block; text-align: center; margin: 1.5em auto; }
.video-embed img { display: block; max-width: 90%; width: auto; height: auto;
                   margin: 0 auto 0.4em; border: 1px solid #ccc; }
.video-embed p { font-size: 0.85em !important; text-align: center;
                 margin: 0.2em 0; text-indent: 0; }
"""


def build_epub(
    posts: list[Post],
    title: str,
    description: str,
    output_path: Path,
    add_toc: bool = True,
    links_to_footnotes: bool = False,
    include_images: bool = True,
    on_image: Callable[[int], None] | None = None,
) -> tuple[Path, dict, list[str]]:
    """Returns (output_path, image_cache, processed_contents).

    image_cache maps url/epub-path -> (data, mime).
    processed_contents is the cleaned HTML body of each post (same order as posts),
    with img src already rewritten to epub-relative paths — reuse in PDF to avoid re-downloading.
    """
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language("es")
    book.add_metadata("DC", "description", description)

    # Normalize typography across all chapters
    css = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=_EPUB_CSS,
    )
    book.add_item(css)

    chapters: list[epub.EpubHtml] = []
    img_counter = [0]
    image_cache: dict = {}
    processed_contents: list[str] = []

    for i, post in enumerate(posts):
        content = post.content or "<p>No content</p>"

        # _clean_content first: converts image-href links to <img> so _embed_images picks them up
        content = _clean_content(content)

        if include_images:
            content = _embed_images(
                content, post.url, book, img_counter,
                on_image=on_image, image_cache=image_cache,
            )

        if links_to_footnotes:
            content = _convert_links_to_footnotes(content, post_url=post.url or "")

        processed_contents.append(content)

        chapter = epub.EpubHtml(
            title=post.title,
            file_name=f"chapter_{i:04d}.xhtml",
            lang="es",
        )
        chapter.add_link(href="../style/main.css", rel="stylesheet", type="text/css")
        date_html = f'<p class="post-date">{_fmt_date(post.date)}</p>' if post.date else ""
        chapter.content = f"<h1>{post.title}</h1>{date_html}{content}"
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
    return output_path, image_cache, processed_contents


_BARE_REF_RE = re.compile(r'^\s*\[\d+\]\s*$')


def _convert_links_to_footnotes(html: str, post_url: str = "") -> str:
    from bs4 import NavigableString
    soup = BeautifulSoup(html, "lxml")
    body = soup.find("body")
    root = body if body else soup
    footnotes: list[tuple[int, str]] = []

    for i, a in enumerate(root.find_all("a", href=True), 1):
        href = a["href"]
        link_text = a.get_text()

        ref_sup = soup.new_tag("sup")
        ref_a = soup.new_tag("a", href=f"#ref-{i}")
        ref_a["class"] = "footnote-ref"
        ref_a.string = f"[{i}]"
        ref_sup.append(ref_a)

        # Don't re-insert link_text when it's already a bare [N] marker — avoids "[7] [7]"
        if link_text and not _BARE_REF_RE.match(link_text):
            a.insert_before(NavigableString(link_text))
        a.replace_with(ref_sup)
        ref_sup.insert_after(NavigableString(" "))

        footnotes.append((i, href))

    # Always emit the references section when footnotes exist OR when we have the original URL
    if footnotes or post_url:
        fn_parts = ['<hr/>']
        if footnotes:
            items = "".join(
                f'<li id="ref-{n}">[{n}] <a href="{href}">{href}</a></li>'
                for n, href in footnotes
            )
            fn_parts.append(f'<ul class="footnotes">{items}</ul>')
        if post_url:
            fn_parts.append(
                f'<p class="original-url">Link: <a href="{post_url}">{post_url}</a></p>'
            )
        fn_soup = BeautifulSoup("".join(fn_parts), "lxml")
        fn_body = fn_soup.find("body")
        for child in list((fn_body or fn_soup).children):
            root.append(child)

    return root.decode_contents() if body else str(root)

import base64
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from services.crawler import Post
from services.epub_builder import _fmt_date

_CSS = """
body { font-family: Georgia, serif; font-size: 11pt; line-height: 1.7; margin: 2cm; color: #111; }
h1 { font-size: 1.6em !important; font-weight: bold; margin-top: 2em; margin-bottom: 0.6em;
     line-height: 1.3; page-break-before: always; }
h1:first-child { page-break-before: avoid; }
h2 { font-size: 1.3em !important; font-weight: bold; margin: 1em 0 0.4em; }
h3, h4, h5, h6 { font-size: 1.1em !important; font-weight: bold; margin: 0.8em 0 0.3em; }
p { font-size: 1em; margin: 0.5em 0; text-align: justify; }
li { font-size: 1em; margin: 0.3em 0; }
blockquote { font-size: 1em; margin: 1em 2em; font-style: italic; }
a { color: #1a0dab; }
figure, p.img-block { display: block !important; text-align: center !important;
                      margin: 1.5em auto !important; }
figure img, p.img-block img, img { display: block !important; max-width: 66% !important;
                                   width: auto !important; height: auto !important;
                                   margin: 0.5em auto !important; }
hr { margin: 1.5em 0; }
ul, ol { margin: 0.5em 0 0.5em 1.5em; padding: 0; }
* { font-size: inherit; }
.post-date { font-size: 0.8em !important; text-align: right; color: #666;
             margin: -0.3em 0 1.2em; font-style: italic; }
.quoted-para { font-size: 0.875em !important; }
.verse-block { margin: 1em 0 1em 2em; text-align: left; line-height: 1.3 !important; }
p.verse-block { text-indent: 0; }
.verse-block p { margin: 0; text-indent: 0; text-align: left; line-height: 1.3 !important; }
.verse-block p.verse-stanza { margin: 0.7em 0 !important; }
.footnote-ref { font-size: 0.75em !important; vertical-align: super; text-decoration: none; }
ul.footnotes { font-size: 0.9em !important; margin-top: 1em; }
.original-url { font-size: 0.85em !important; margin-top: 0.6em; color: #555; font-style: italic; }
.original-url a { color: #555; }
.video-embed { display: block; text-align: center; margin: 1.5em auto; }
.video-embed img { display: block; max-width: 80% !important; width: auto !important;
                   height: auto !important; margin: 0 auto 0.4em; border: 1px solid #ccc; }
.video-embed p { font-size: 0.85em !important; text-align: center; margin: 0.2em 0; }
"""

_BLOCK_TAGS = {"address", "article", "aside", "blockquote", "canvas", "dd", "div",
               "dl", "dt", "fieldset", "figcaption", "figure", "footer", "form",
               "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main",
               "nav", "noscript", "ol", "p", "pre", "section", "table", "tfoot",
               "thead", "tbody", "tr", "td", "th", "ul", "video"}


def _div_is_paragraph(tag) -> bool:
    for child in tag.children:
        if hasattr(child, "name") and child.name and child.name.lower() in _BLOCK_TAGS:
            return False
    return bool(tag.get_text(strip=True))


def _clean_for_pdf(content: str, post_url: str, image_cache: dict) -> str:
    soup = BeautifulSoup(content, "lxml")
    body = soup.find("body")
    root = body if body else soup

    for img in root.find_all("img"):
        src = img.get("src", "").strip()
        if not src:
            img.decompose()
            continue
        if src.startswith("data:"):
            continue

        # Try epub-relative path first (e.g. "images/image0000.jpg"), then absolute URL
        abs_url = urljoin(post_url, src) if not src.startswith("http") else src
        entry = image_cache.get(src) or image_cache.get(abs_url)

        if entry:
            data, mime = entry
            b64 = base64.b64encode(data).decode()
            img["src"] = f"data:{mime};base64,{b64}"
            img.attrs.pop("width", None)
            img.attrs.pop("height", None)
            img["style"] = "max-width:66%;width:auto;height:auto;display:block;margin:0 auto;text-align:center"
        else:
            img.decompose()

    for tag in root.find_all(["figure", "div", "p"]):
        if tag.parent is None:
            continue
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()
    for div in root.find_all("div"):
        if _div_is_paragraph(div):
            div.name = "p"
    for tag in root.find_all(["p", "div"]):
        if not tag.get_text(strip=True) and not tag.find("img"):
            tag.decompose()

    # Strip inline style overrides from CMS
    for tag in root.find_all(True):
        tag.attrs.pop("style", None)
        tag.attrs.pop("size", None)
        tag.attrs.pop("face", None)
        tag.attrs.pop("color", None)
        tag.attrs.pop("align", None)
        tag.attrs.pop("bgcolor", None)
        tag.attrs.pop("dir", None)
        tag.attrs.pop("lang", None)

    # Unwrap bare <span>/<font> with no remaining attributes
    for tag in list(root.find_all(["span", "font"])):
        if tag.parent is not None and not tag.attrs:
            tag.unwrap()

    return root.decode_contents() if body else str(root)


def build_pdf(
    posts: list[Post],
    title: str,
    output_path: Path,
    image_cache: dict | None = None,
    processed_contents: list[str] | None = None,
) -> Path:
    from weasyprint import HTML, CSS

    cache = image_cache or {}
    contents = processed_contents or [None] * len(posts)

    def _chapter(p: Post, html: str | None) -> str:
        date_html = f'<p class="post-date">{_fmt_date(p.date)}</p>' if p.date else ""
        body = _clean_for_pdf(html or p.content or "<p>No content</p>", p.url, cache)
        return f"<h1>{p.title}</h1>{date_html}{body}"

    chapters = "".join(_chapter(p, html) for p, html in zip(posts, contents))

    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body><h1 class="cover">{title}</h1>{chapters}</body></html>"""

    HTML(string=html_content).write_pdf(
        str(output_path), stylesheets=[CSS(string=_CSS)]
    )
    return output_path

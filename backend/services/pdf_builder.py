from pathlib import Path
from bs4 import BeautifulSoup
from services.crawler import Post

_CSS = """
body { font-family: Georgia, serif; line-height: 1.6; margin: 2cm; }
h1 { font-size: 1.8em; margin-top: 2em; page-break-before: always; }
h1:first-child { page-break-before: avoid; }
a { color: #333; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
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


def _clean_for_pdf(content: str) -> str:
    soup = BeautifulSoup(content, "lxml")
    body = soup.find("body")
    root = body if body else soup
    # Strip all images — WeasyPrint fetches them synchronously, kills performance at scale
    for img in root.find_all("img"):
        img.decompose()
    for tag in root.find_all(["figure", "div"]):
        if not tag.get_text(strip=True):
            tag.decompose()
    for div in root.find_all("div"):
        if _div_is_paragraph(div):
            div.name = "p"
    for tag in root.find_all(["p", "div"]):
        if not tag.get_text(strip=True):
            tag.decompose()
    return root.decode_contents() if body else str(root)


def build_pdf(
    posts: list[Post],
    title: str,
    output_path: Path,
) -> Path:
    from weasyprint import HTML, CSS

    chapters = "".join(
        f"<h1>{p.title}</h1>{_clean_for_pdf(p.content or '<p>No content</p>')}"
        for p in posts
    )

    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body><h1 class="cover">{title}</h1>{chapters}</body></html>"""

    HTML(string=html_content, base_url="https://").write_pdf(
        str(output_path), stylesheets=[CSS(string=_CSS)]
    )
    return output_path

from pathlib import Path
from services.crawler import Post

_CSS = """
body { font-family: Georgia, serif; line-height: 1.6; margin: 2cm; }
h1 { font-size: 1.8em; margin-top: 2em; page-break-before: always; }
h1:first-child { page-break-before: avoid; }
a { color: #333; }
img { max-width: 100%; }
"""


def build_pdf(
    posts: list[Post],
    title: str,
    output_path: Path,
) -> Path:
    from weasyprint import HTML, CSS

    chapters = "".join(
        f"<h1>{p.title}</h1>{p.content or '<p>No content</p>'}"
        for p in posts
    )

    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body><h1 class="cover">{title}</h1>{chapters}</body></html>"""

    HTML(string=html_content).write_pdf(str(output_path), stylesheets=[CSS(string=_CSS)])
    return output_path

from pathlib import Path
from ebooklib import epub
from services.crawler import Post


def build_epub(
    posts: list[Post],
    title: str,
    description: str,
    output_path: Path,
    add_toc: bool = True,
    links_to_footnotes: bool = False,
) -> Path:
    book = epub.EpubBook()
    book.set_title(title)
    book.set_language("es")
    book.add_metadata("DC", "description", description)

    chapters: list[epub.EpubHtml] = []

    for i, post in enumerate(posts):
        content = post.content or "<p>No content</p>"
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

    book.toc = [(epub.Section(post.title), [ch]) for post, ch in zip(posts, chapters)] if add_toc else chapters

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    epub.write_epub(str(output_path), book)
    return output_path


def _convert_links_to_footnotes(html: str) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    footnotes: list[str] = []

    for i, a in enumerate(soup.find_all("a", href=True), 1):
        href = a["href"]
        a.replace_with(f"{a.get_text()}[{i}]")
        footnotes.append(f"[{i}] {href}")

    if footnotes:
        fn_html = "<hr/><ol>" + "".join(f"<li>{fn}</li>" for fn in footnotes) + "</ol>"
        soup.append(BeautifulSoup(fn_html, "lxml"))

    return str(soup)

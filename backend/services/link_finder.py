from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from models.ebook_options import CustomSelector

# Heuristic patterns used by common blog platforms
_HEURISTIC_SELECTORS = [
    # WordPress: <link rel="prev" ...>
    {"tag": "link", "attr": "rel", "value": "prev"},
    # Blogger: <a class="blog-pager-older-link" ...>
    {"tag": "a", "attr": "class", "value": "blog-pager-older-link"},
    # Generic prev/older patterns
    {"tag": "a", "attr": "rel", "value": "prev"},
    {"tag": "a", "attr": "class", "value": "prev"},
    {"tag": "a", "attr": "class", "value": "older"},
    {"tag": "a", "attr": "id", "value": "older"},
    {"tag": "a", "attr": "class", "value": "previous"},
]


def find_next_post_url(
    html: str,
    base_url: str,
    custom: Optional[CustomSelector] = None,
) -> Optional[str]:
    soup = BeautifulSoup(html, "lxml")

    if custom and custom.tag_name and custom.attr_name and custom.attr_value:
        return _find_with_custom(soup, base_url, custom)

    return _find_heuristic(soup, base_url)


def _find_with_custom(
    soup: BeautifulSoup,
    base_url: str,
    custom: CustomSelector,
) -> Optional[str]:
    el = soup.find(custom.tag_name, attrs={custom.attr_name: custom.attr_value})
    if not el:
        return None

    target = el.find("a") if custom.parent_tag else el
    href = target.get("href") if target else None
    if not href:
        return None

    return urljoin(base_url, custom.pre_string + href)


def _find_heuristic(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for sel in _HEURISTIC_SELECTORS:
        el = soup.find(sel["tag"], attrs={sel["attr"]: sel["value"]})
        if el:
            href = el.get("href")
            if href:
                return urljoin(base_url, href)
    return None

from typing import TypedDict

from bs4 import BeautifulSoup

from .headings import count_h1
from .images import audit_images
from .meta_description import extract_meta_description
from .title import extract_title
from .word_count import approx_word_count


class ParseResult(TypedDict):
    title: str | None
    meta_description: str | None
    h1_count: int
    total_images: int
    images_missing_alt: int
    approx_word_count: int


def parse_html(html: str) -> ParseResult:
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup)
    meta_description = extract_meta_description(soup)
    h1_count = count_h1(soup)
    total_images, images_missing_alt = audit_images(soup)
    word_count = approx_word_count(soup)

    return ParseResult(
        title=title,
        meta_description=meta_description,
        h1_count=h1_count,
        total_images=total_images,
        images_missing_alt=images_missing_alt,
        approx_word_count=word_count,
    )

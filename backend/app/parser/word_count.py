import re

from bs4 import BeautifulSoup

_INVISIBLE_TAGS = ["script", "style", "noscript"]


def approx_word_count(soup: BeautifulSoup) -> int:
    for tag in soup(_INVISIBLE_TAGS):
        tag.decompose()

    text = soup.get_text(separator=" ")
    words = [w for w in re.split(r"\s+", text) if w.strip()]
    return len(words)

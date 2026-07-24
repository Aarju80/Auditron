from bs4 import BeautifulSoup


def extract_title(soup: BeautifulSoup) -> str | None:
    tag = soup.find("title")
    if tag:
        text = tag.get_text(strip=True)
        if text:
            return text
    return None

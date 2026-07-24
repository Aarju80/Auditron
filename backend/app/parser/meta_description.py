from bs4 import BeautifulSoup


def extract_meta_description(soup: BeautifulSoup) -> str | None:
    tag = soup.find(
        "meta",
        attrs={"name": lambda v: v is not None and v.lower() == "description"},
    )
    if tag:
        content = (tag.get("content") or "").strip()
        if content:
            return content
    return None

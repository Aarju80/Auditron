from bs4 import BeautifulSoup


def audit_images(soup: BeautifulSoup) -> tuple[int, int]:
    images = soup.find_all("img")
    missing_alt = sum(
        1 for img in images if not (img.get("alt") or "").strip()
    )
    return len(images), missing_alt

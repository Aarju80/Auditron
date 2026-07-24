from bs4 import BeautifulSoup


def count_h1(soup: BeautifulSoup) -> int:
    return len(soup.find_all("h1"))

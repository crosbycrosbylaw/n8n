from __future__ import annotations

import re

import bs4


class HTMLParser:
    soup: bs4.BeautifulSoup

    def __init__(self, content: str) -> None:
        self.soup = bs4.BeautifulSoup(content, features="html.parser")

    def tags(self, name: str, string: str | None = None, **attrs: bool):
        return [
            item
            for item in self.soup.find_all(name=name, attrs={**attrs})
            if not string or item.string and re.compile(string).match(item.string)
        ]

    def find_hrefs(self, string: str = "") -> list[str]:
        return [
            href for x in self.tags("a", string=string, href=True) if (href := x["href"]) and isinstance(href, str)
        ]

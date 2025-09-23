import bs4
import re

from argparse import Namespace
from utils.args import parse_content


class HtmlParser(Namespace):
    _content: str

    @property
    def content(self) -> str:
        return self.__dict__.setdefault("_content", parse_content())

    _soup: bs4.BeautifulSoup

    @property
    def soup(self) -> bs4.BeautifulSoup:
        return self.__dict__.setdefault("_soup", bs4.BeautifulSoup(self.content, "html.parser"))

    def tags(self, name: str, **attrs: str | re.Pattern[str] | bool):
        return [
            item
            for item in bs4.Tag(self.soup, name=name).find_all(
                attrs={
                    k: v if isinstance(v, bool | re.Pattern) else re.compile(v)
                    for k, v in attrs.items()
                },
            )
            if isinstance(item, bs4.Tag)
        ]

    def parse_links(self, string: str = "") -> list[str]:
        return [
            href
            for x in self.tags("a", href=string)
            if (href := x["href"]) and isinstance(href, str)
        ]

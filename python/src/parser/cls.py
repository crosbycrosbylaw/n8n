import bs4
import re


class HTMLParser:
    soup: bs4.BeautifulSoup

    def __init__(self, content: str) -> None:
        self.soup = bs4.BeautifulSoup(content, "html.parser")

    def tags(self, name: str, **attrs: str | re.Pattern[str] | bool):
        return [
            item
            for item in bs4.Tag(self.soup, name=name).find_all(
                attrs={
                    k: v if isinstance(v, bool | re.Pattern) else re.compile(v) for k, v in attrs.items()
                },
            )
            if isinstance(item, bs4.Tag)
        ]

    def find_hrefs(self, string: str = "") -> list[str]:
        return [href for x in self.tags("a", href=string) if (href := x["href"]) and isinstance(href, str)]

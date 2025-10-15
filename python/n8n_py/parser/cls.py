from __future__ import annotations

import re
from argparse import Namespace
from rampy.json import JSON
import bs4
from common import stderr, stdout
from rampy import console


class HTMLParser:
    soup: bs4.BeautifulSoup

    def __init__(self, content: str) -> None:
        self.soup = bs4.BeautifulSoup(content, "html.parser")

    def tags(self, name: str, **attrs: str | re.Pattern[str] | bool):
        return [
            item
            for item in bs4.Tag(self.soup, name=name).find_all(
                attrs={k: v if isinstance(v, bool | re.Pattern) else re.compile(v) for k, v in attrs.items()},
            )
            if isinstance(item, bs4.Tag)
        ]

    def find_hrefs(self, string: str = "") -> list[str]:
        return [href for x in self.tags("a", href=string) if (href := x["href"]) and isinstance(href, str)]


class Runner(Namespace):
    mode: str
    input: JSON[str]
    email: str = 'eservice@crosbyandcrosbylaw.com'

    _parser: HTMLParser

    def _parse_download_link(self) -> None:
        hrefs = self._parser.find_hrefs(r"Download Document")
        length = len(hrefs)
        if length == 0:
            stderr("download link not found")
        if length == 1:
            stdout(hrefs[0])
        elif length > 1 and (rest := hrefs[1:]):
            stdout(hrefs[0], **{str(i): rest[i] for i in range(len(rest) - 1)})

    def _parse_http_response(self) -> None:
        tags = self._parser.tags("input", id=r"__(VIEW|EVENT)\w+", value=True)

        def value_for(id: str, *, prefix: str = "__", upper: bool = True) -> str:
            id_str = f"{prefix}{id}"
            upper and (id_str := id_str.upper())

            return str([x for x in tags if x["id"] == id_str][0]["value"])

        links = [raw.replace(";", "").replace("amp", "") for raw in self._parser.find_hrefs(r"ViewDocuments")]

        return stdout(
            links=links,
            data={
                "emailAddress": self.email,
                "__viewstate": value_for("viewstate"),
                "__viewstategenerator": value_for("viewstategenerator"),
                "__eventvalidation": value_for("eventvalidation"),
            },
        )

    @console.catch
    def invoke(self) -> None:
        repr(self)
        self._parser = HTMLParser(self.input['content'])
        match self.mode:
            case "link":
                self._parse_download_link()
            case "response":
                self._parse_http_response()

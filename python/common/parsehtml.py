# %%
from __future__ import annotations

import re
import typing as ty
from contextlib import suppress

import bs4


class Options(ty.TypedDict, total=False):
    recursive: bool
    limit: int | None


class HTMLParser:
    soup: bs4.BeautifulSoup

    def __init__(self, content: str) -> None:
        self.soup = bs4.BeautifulSoup(content, features="html.parser")

    def tags(
        self,
        name: str,
        string: str | None = None,
        options: Options | None = None,
        **attrs: bool,
    ):
        options = options or Options()

        options.setdefault("limit", None)
        options.setdefault("recursive", True)

        kwds: dict[str, ty.Any] = {"attrs": attrs, **options}

        return [
            item
            for item in self.soup.find_all(name=name, **kwds)
            if not string or item.string and re.compile(string).match(item.string)
        ]

    def find_hrefs(self, string: str = "") -> list[str]:
        return [
            href for x in self.tags("a", string=string, href=True) if (href := x["href"]) and isinstance(href, str)
        ]

    def collect_table_dict(
        self,
        include_keys: ty.Sequence[str] | None = None,
        exclude_keys: ty.Sequence[str] = (),
    ) -> dict[str, str]:
        out: dict[str, str] = {}

        def selector(k: str) -> bool:
            return k not in exclude_keys and (not include_keys or k in include_keys)

        for tr in self.tags("tr"):
            key: str | None = None
            for c in tr.children:
                with suppress(StopIteration):
                    string = next(s for s in c.stripped_strings if s)
                    if not key:
                        if selector(string):
                            key = string
                        continue
                    out[key] = string

        return out


class DocumentInfo(ty.TypedDict):
    hrefs: list[str]
    filename: str

    court: str
    case_no: str
    case_name: str
    filed_by: str

    path: str | None
    path_display: str | None


def get_default_doc_info():
    return DocumentInfo(
        hrefs=[],
        filename="untitled",
        case_name="",
        court="",
        case_no="",
        filed_by="",
        path=None,
        path_display=None,
    )


@ty.overload
def collect_document_information(__parser: HTMLParser) -> DocumentInfo: ...
@ty.overload
def collect_document_information(__content: str) -> DocumentInfo: ...
def collect_document_information(argument):
    parser = argument if isinstance(argument, HTMLParser) else HTMLParser(argument)

    relevant_keys = ["Court", "Case Name", "Case Number", "Filed By", "Lead Document"]
    table_dict = parser.collect_table_dict(relevant_keys)

    return DocumentInfo(
        hrefs=parser.find_hrefs("Download Document"),
        filename=table_dict.get("Lead Document", "untitled"),
        court=table_dict.get("Court", ""),
        case_name=table_dict.get("Case Name", ""),
        case_no=table_dict.get("Case Number", ""),
        filed_by=table_dict.get("Filed By", table_dict.get("Filing Attorney", "")),
        path=None,
        path_display=None,
    )

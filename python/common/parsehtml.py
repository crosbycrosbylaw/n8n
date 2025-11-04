# %%
from __future__ import annotations

import re
import typing as ty
from contextlib import suppress

import bs4

if ty.TYPE_CHECKING:
    pass


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

    def find_table_strings(
        self,
        include: ty.Sequence[str] | ty.Mapping[str, str] | None = None,
        exclude: ty.Sequence[str] = (),
        tag: str = "tr",
    ) -> dict[str, str]:
        remap: bool = isinstance(include, ty.Mapping)
        out: dict[str, str] = {}

        def selector(k: str) -> bool:
            return k not in exclude and (not include or k in include)

        for tr in self.tags(tag):
            key: str | None = None
            for c in tr.children:
                with suppress(StopIteration):
                    string = next(s for s in c.stripped_strings if s)
                    if not key:
                        if selector(string):
                            key = string
                        continue
                    out[key if not remap else include[key]] = string

        return out

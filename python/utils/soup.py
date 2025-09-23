from __future__ import annotations

import bs4
from typing import TYPE_CHECKING
from .args import parse_content

if TYPE_CHECKING:
    from typing import *


class ContentSoup:
    soup: bs4.BeautifulSoup

    def __init__(self, content: str = ""):
        self.soup = bs4.BeautifulSoup(content or parse_content(), "html.parser")

    def tag(self, name: str, query: str = ""):
        bs4.Tag(self.soup, name=name, attrs={"href": "a"}).find(string=query)


def find_tag(
    content: str,
    *,
    tag: str,
    string: str = "",
) -> bs4.Tag:
    elem = bs4.BeautifulSoup(content, "html.parser").find(tag, string=string)

    if not isinstance(elem, bs4.Tag):
        from utils.output import stderr

        stderr(TypeError, expected=bs4.Tag, received=type(elem))
    else:
        return elem

    raise RuntimeWarning


def tag_attribute(
    attr: str,
    element: bs4.Tag,
) -> str:
    value = element.get(attr)

    if not (value and isinstance(value, str)):
        from utils.output import stderr

        stderr(ValueError, attribute_name=attr, value_type=type(value))
    else:
        return value

    raise RuntimeWarning

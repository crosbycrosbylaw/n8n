from __future__ import annotations

import re
import typing
from typing import NamedTuple
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from re import Pattern
    from typing import Literal

    from bs4 import Tag


class _Extractor[T = str]:
    target: str | None = None
    require: bool | None = None

    soup: BeautifulSoup
    rules: dict[str, str | Pattern[str]]
    pattern: Pattern[str] | Literal[True] = True

    def __init__(
        self,
        soup: BeautifulSoup,
        target: str | None = None,
        **kwds: str | Pattern[str],
    ) -> None:
        """Initialize the extractor with the given BeautifulSoup object.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object to extract from.
            **kwds (StringMatchRule): Additional keyword arguments specifying rules for selecting tags.
        """
        self.soup = soup
        self.rules = kwds
        if target:
            self.target = target

    def __init_subclass__(
        cls,
        target: str,
        require: bool | None = None,
    ) -> None:
        """Initialize subclass with the target tag name."""
        cls.target = target
        cls.require = require

    def _select(self, tag: Tag) -> bool:
        """Selector method for the target tag.

        Default implementation only checks that the given tag matches the target tag name."""
        return tag.name == self.target

    def _process(self, __tag: Tag | None) -> T | None:
        """Process the given tag and extract the desired information.

        Default implementation extracts and returns the text content of the tag.
        """
        if __tag is not None:
            return typing.cast(T, __tag.get_text(strip=True))

        return None

    @typing.overload
    def _find_one(self, *, required: Literal[True]) -> Tag:
        """Find a single tag matching the selector and additional criteria.

        This overload raises an error if no matching tag is found.
        """

    @typing.overload
    def _find_one(self, *, required: Literal[False] = False) -> Tag | None:
        """Find a single tag matching the selector and additional criteria.

        This overload returns None if no matching tag is found.
        """

    def _find_one(self, required=False):
        tag = self.soup.find(self._select, kwargs=self.rules)

        if required and not tag:
            message = "failed to find required html element"
            raise ValueError(message, tag)

        return tag

    def _find_many(self) -> list[Tag]:
        """Find multiple tags matching the selector and additional criteria."""
        return self.soup.find_all(self._select, kwargs=self.rules)

    def get_one(self) -> ...:
        """Get a single extracted value, optionally matching attributes for the given string criteria.

        Default implementation attempts to extract a tag and, if found, returns its processed value.
        """
        if self.require is not None:
            tag = self._find_one(required=self.require)
        else:
            tag = self._find_one()

        return self._process(tag)

    def get_iterator(self) -> Iterator[T]:
        """Iterate over extracted values matching the given string criteria.

        Default implementation extracts all matching tags and yields their text.
        """
        tags = self._find_many()

        return (value for t in tags if (value := self._process(t)))


# -- Download Info -- #


class _LinkExtractor(_Extractor[str], target="a"):
    def _select(self, tag) -> bool:
        return super()._select(tag) and tag.has_attr("href")

    def _process(self, tag) -> str | None:
        href = tag.get("href")

        if isinstance(href, list):
            href = next(iter(href), None)

        if isinstance(href, str):
            href = href.strip()

        return href

    def get_one(self) -> str | None:
        return super().get_one()


class _DocumentNameExtractor(_Extractor[str], target="td", require=True):
    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and (prev := tag.find_previous("td"))
            and (text := prev.text)
            and ("Lead Document" in text and "Page Count" not in text)
        )

    def get_one(self) -> str:
        """Get the document name from the document details table.

        Raises ValueError if the document name cannot be found.
        """
        return super().get_one()


DownloadInfo = NamedTuple(
    "DownloadInfo",
    [
        ("link", str),
        ("name", str),
    ],
)


def extract_download_info(soup: BeautifulSoup) -> DownloadInfo:
    regex = r"(https:\/\/illinois.tylertech.cloud\/ViewDocuments.aspx\?\w+=[\w-]+)"

    link = _LinkExtractor(soup, href=regex).get_one()

    if not link:
        message = "could not find download link in email content."
        raise ValueError(message)

    doc_name = _DocumentNameExtractor(soup).get_one()

    return DownloadInfo(link, doc_name)


# -- Upload Info -- #


class _CaseNameExtractor(_Extractor[str], target="td"):
    def _process(self, tag: Tag | None) -> str | None:
        if not tag or "CONFIDENTIAL" in tag.text:
            return None
        return tag.get_text(strip=True)

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and (prev := tag.find_previous("td"))
            and ("Case Name" in prev.text)
        )  # fmt: skip


UploadInfo = NamedTuple(
    "UploadInfo",
    [
        ("doc_count", int),
        ("case_name", str | None),
    ],
)


def extract_upload_info(soup: BeautifulSoup, store: Path) -> UploadInfo:
    doc_count = len((*store.iterdir(),))
    case_name = _CaseNameExtractor(soup).get_one()

    return UploadInfo(doc_count, case_name)


# -- Request / Response Info -- #


class _ViewStateValueExtractor(_Extractor[tuple[str, str]], target="input"):
    rules: dict[str, str | Pattern[str]] = {
        "name": r"/(^__VIEWSTATE|__VIEWSTATEGENERATOR|__EVENTVALIDATION$)/",
    }

    def _process(self, tag: Tag | None) -> tuple[str, str] | None:
        if not tag:
            return None

        name, value = items = tag.get("name"), tag.get("value")

        if not all(isinstance(x, str) for x in items):
            message = f"expected strings; recieved {type(name)}, {type(value)}"
            raise TypeError(message)

        return typing.cast(tuple[str, str], items)

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and (name := tag["name"])
            and isinstance(name, str)
            and name.startswith("__")
            and tag.has_attr("value")
        )


def extract_aspnet_form_data(content: str, email: str) -> str:
    soup = BeautifulSoup(content, "html.parser")
    generator = _ViewStateValueExtractor(soup).get_iterator()

    out = {}
    out.update(item for _ in range(3) if (item := next(generator, None)))

    for key in "__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION":
        if key in out:
            continue
        else:
            message = f"missing required ASP.NET field: '{key}'"
            raise ValueError(message)

    out.update((key, email) for key in ["emailAddress", "username"])
    out.update(
        (key, "Validate")
        for key in [
            "SubmitEmailAddressButton",
            "SubmitUsernameButton",
        ]
    )

    return urlencode(out)


class _TargetUrlExtractor(_Extractor[str], target="form"):
    def _process(self, tag: Tag | None) -> str | None:
        if not tag:
            return None

        post_url = tag.get("action")

        if not isinstance(post_url, str):
            return None

        return post_url

    def _select(self, tag: Tag) -> bool:
        return super()._select(tag) and tag.has_attr("action")

    def get_one(self) -> str | None:
        return super().get_one()


def extract_post_request_url(content: str, initial_url: str) -> str:
    soup = BeautifulSoup(content, "html.parser")
    extracted = _TargetUrlExtractor(soup).get_one() or initial_url

    if extracted.startswith("http"):
        return extracted

    return urljoin(initial_url, extracted)


def extract_filename_from_disposition(disposition: str) -> str | None:
    pattern = re.compile(r'filename=["\']?(.+?)["\']?$')

    if found := pattern.search(disposition):
        return found.group(1).strip()

    return None


class _ResponseLinkExtractor(_Extractor[tuple[str, str]], target="a"):
    extensions: tuple[str, ...] = ".pdf", ".tif", ".tiff", ".doc", ".docx", ".jpg", ".png"

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and tag.has_attr("href")
            and (href := tag["href"])
            and isinstance(href, str)
        )  # fmt: skip

    def _process(self, tag: Tag | None) -> tuple[str, str] | None:
        if not tag:
            return None

        href = tag.get("href")

        if not isinstance(href, str):
            return None

        if any(href.lower().endswith(ext) for ext in self.extensions):
            return None

        return href.lower(), tag.get_text(strip=True)


def extract_links_from_response_html(
    content: str,
    initial_url: str,
) -> list[DownloadInfo]:
    soup = BeautifulSoup(content, "html.parser")
    iterator = _ResponseLinkExtractor(soup).get_iterator()

    out: list[DownloadInfo] = []

    for href, text in iterator:
        link = urljoin(initial_url, href)

        if text and len(text) > 5:
            name = text.replace(" ", "_")
        else:
            name = Path(text.split("?")[0]).name

        if not any(tkn in link for tkn in ["viewstate", "validation"]):
            out.append(DownloadInfo(link, name))

    return out

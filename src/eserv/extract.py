"""HTML content extraction utilities for Tyler Technologies Illinois cloud service.

This module provides extractor classes and functions to parse and extract information from
HTML content, particularly from Tyler Technologies' Illinois cloud service emails and web pages.

It includes extractors for download links, document names, case information, ASP.NET form data,
and response URLs.

The module uses a protocol-based extractor pattern with a generic _Extractor base class that
can be subclassed to extract specific types of information from BeautifulSoup objects.

Classes:
    _Extractor: Protocol class defining the interface for all extractors.
    _LinkExtractor: Extracts download links matching Tyler Technologies URL patterns.
    _DocumentNameExtractor: Extracts document names from HTML tables.
    DownloadInfo: Named tuple containing download link and document name.
    _CaseNameExtractor: Extracts case names while filtering confidential cases.
    UploadInfo: Named tuple containing document count and case name.
    _ViewStateValueExtractor: Extracts ASP.NET ViewState fields from forms.
    _TargetUrlExtractor: Extracts form action URLs.
    _ResponseLinkExtractor: Extracts downloadable links from response HTML.

Functions:
    extract_download_info: Extract download link and document name from email HTML.
    extract_upload_info: Extract document count and case name from HTML and file storage.
    extract_aspnet_form_data: Extract and encode ASP.NET form data for submission.
    extract_post_request_url: Extract target URL for POST requests from HTML forms.
    extract_filename_from_disposition: Parse filename from Content-Disposition header.
    extract_links_from_response_html: Extract all downloadable links from response HTML.


- This module requires BeautifulSoup4 for HTML parsing.
- ASP.NET-specific extractors handle ViewState and form validation fields.

"""

from __future__ import annotations

import re
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup, Tag

if typing.TYPE_CHECKING:
    from collections.abc import Iterator
    from re import Pattern
    from typing import Any, Final, Literal

    from bs4 import Tag


class _Extractor[T = str](Protocol):
    target: str | None = None
    require: bool | None = None

    soup: BeautifulSoup
    rules: dict[str, str | Pattern[str]]

    @property
    def attrs(self) -> dict[str, Any]:
        return self.rules

    def __init__(
        self,
        soup: BeautifulSoup,
        target: str | None = None,
        **kwds: str | Pattern[str],
    ) -> None:
        """Initialize the extractor with the given BeautifulSoup object.

        Args:
            soup (BeautifulSoup): The BeautifulSoup object to extract from.
            target (str | None): An optional override for this instance's target attribute.
            **kwds (StringMatchRule): Additional keyword arguments specifying rules for selecting tags.

        """
        self.soup = soup
        self.rules.update(kwds)
        if target:
            self.target = target

    def __init_subclass__(
        cls,
        target: str,
        *,
        require: bool | None = None,
    ) -> None:
        """Initialize subclass with the target tag name."""
        cls.target = target
        cls.require = require
        cls.rules = {}

    def _select(self, tag: Tag) -> bool:
        """Selector method for the target tag.

        Default implementation only checks that the given tag matches the target tag name.
        """
        return tag.name == self.target

    @staticmethod
    def _process(tag: Tag | None, /) -> T | None:
        """Process the given tag and extract the desired information.

        Default implementation extracts and returns the text content of the tag.
        """
        if tag is not None:
            return typing.cast('T', tag.get_text(strip=True))

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

    def _find_one(self, *, required: bool = False):
        tag = self.soup.find(self._select, **self.attrs)

        if required and not tag:
            message = 'failed to find required html element'
            raise ValueError(message, tag)

        return tag

    def _find_many(self) -> list[Tag]:
        """Find multiple tags matching the selector and additional criteria."""
        return self.soup.find_all(self._select, **self.attrs)

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


class _LinkExtractor(_Extractor[str], target='a'):
    regex: Pattern[str] = re.compile(
        r'(https:\/\/illinois.tylertech.cloud\/ViewDocuments.aspx\?\w+=[\w-]+)'
    )

    def _select(self, tag: Tag) -> bool:
        return self.regex.match(f'{tag.get("href", "")}'.strip()) is not None

    @staticmethod
    def _process(tag: Tag | None) -> str | None:
        if not tag:
            return None

        href = tag.get('href')

        if isinstance(href, list):
            href = next(iter(href), None)

        if isinstance(href, str):
            href = href.strip()

        return href

    def get_one(self) -> str | None:
        return super().get_one()


class _DocumentNameExtractor(_Extractor[str], target='td'):
    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and (prev := tag.find_previous('td'))
            and (text := prev.text)
            and ('Lead Document' in text and 'Page Count' not in text),
        )

    def get_one(self) -> str | None:
        """Get the document name from the document details table.

        Raises ValueError if the document name cannot be found.
        """
        return super().get_one()


@dataclass(slots=True, frozen=True)
class DownloadInfo:
    """Information about a file to be downloaded.

    Attributes:
        source (str): The URL or path from which to download the file.
        filename (str): The name to use when saving the downloaded file.

    """

    source: str
    doc_name: str | None


def extract_download_info(soup: BeautifulSoup) -> DownloadInfo:
    """Extract download information from an email's HTML content.

    Parses the BeautifulSoup object to locate and extract the download link and document name
    from an email notification, typically from Tyler Technologies' Illinois cloud service.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML content
            of the email from which to extract download information.

    Returns:
        DownloadInfo: An object containing the extracted download link and document name.

    Raises:
        ValueError: If the download link matching the expected pattern cannot be found
            in the email content.

    Example:
    >>> from bs4 import BeautifulSoup
    >>> html = '<a href="https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123">Doc</a>'
    >>> soup = BeautifulSoup(html, 'html.parser')
    >>> info = extract_download_info(soup)
    >>> print(info.link)
    'https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123'

    """
    source = _LinkExtractor(soup).get_one()

    if not source:
        message = 'could not find download link in email content.'
        raise ValueError(message)

    doc_name = _DocumentNameExtractor(soup).get_one()

    return DownloadInfo(source, doc_name)


# -- Upload Info -- #


class _CaseNameExtractor(_Extractor[str], target='td'):
    @staticmethod
    def _process(tag: Tag | None) -> str | None:
        if not tag or 'CONFIDENTIAL' in tag.text:
            return None
        return tag.get_text(strip=True)

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and (prev := tag.find_previous_sibling("td"))
            and ("Case Name" in prev.text),
        )  # fmt: skip


@dataclass(slots=True, frozen=True)
class UploadInfo:
    """Information about an upload operation.

    Attributes:
        doc_count: The number of documents uploaded.
        case_name: The name of the case associated with the upload, or None if not applicable.

    """

    doc_count: int
    case_name: str | None


def extract_upload_info(soup: BeautifulSoup, store: Path) -> UploadInfo:
    """Extract upload information from a BeautifulSoup object and storage path.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML to parse.
        store (Path): A Path object representing the directory containing documents.

    Returns:
        UploadInfo: An object containing the document count and case name extracted from the soup.
    The function counts the number of items in the store directory and extracts the case name
    using the _CaseNameExtractor utility class.

    """
    doc_count = len((*store.iterdir(),))
    case_name = _CaseNameExtractor(soup).get_one()

    return UploadInfo(doc_count, case_name)


# -- Request / Response Info -- #


class _ViewStateValueExtractor(_Extractor[tuple[str, str]], target='input'):
    regex: Pattern[str] = re.compile(r'^(__VIEWSTATE|__VIEWSTATEGENERATOR|__EVENTVALIDATION)$')

    @staticmethod
    def _process(tag: Tag | None) -> tuple[str, str] | None:
        if not tag:
            return None

        name, value = items = tag.get('name', ''), tag.get('value', '')

        if not all(x and isinstance(x, str) for x in items):
            message = f'expected strings; recieved {type(name)}, {type(value)}'
            raise TypeError(message)

        return typing.cast('tuple[str, str]', items)

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and tag.has_attr('name')
            and tag.has_attr('value')
            and self.regex.match(f'{tag["name"]!s}')
        )


def extract_aspnet_form_data(content: str, email: str) -> str:
    """Extract and encode ASP.NET form data for submission.

    This function parses HTML content to extract ASP.NET ViewState fields and combines them
    with user credentials to generate URL-encoded form data suitable for POST requests.

    Args:
        content (str): HTML content containing ASP.NET form fields (ViewState data).
        email (str): User's email address to be included in the form data.

    Returns:
        str: URL-encoded string containing all required form fields including:
            - __VIEWSTATE: ASP.NET ViewState value
            - __VIEWSTATEGENERATOR: ASP.NET ViewState generator value
            - __EVENTVALIDATION: ASP.NET event validation value
            - emailAddress: User's email
            - username: User's email (duplicate field)
            - SubmitEmailAddressButton: Set to "Validate"
            - SubmitUsernameButton: Set to "Validate"

    Raises:
        ValueError: If any of the required ASP.NET fields (__VIEWSTATE,
                    __VIEWSTATEGENERATOR, __EVENTVALIDATION) are missing from the HTML content.

    Example:
        >>> html = '<input name="__VIEWSTATE" value="xyz123" />'
        >>> form_data = extract_aspnet_form_data(html, 'user@example.com')
        >>> # Returns URL-encoded form data string

    """
    soup = BeautifulSoup(content, 'html.parser')
    generator = _ViewStateValueExtractor(soup).get_iterator()

    out: dict[str, str] = {}
    out.update(item for _ in range(3) if (item := next(generator, None)))

    for key in '__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION':
        if key in out:
            continue
        message = f"missing required ASP.NET field: '{key}'"
        raise ValueError(message)

    out.update((key, email) for key in ['emailAddress', 'username'])
    out.update(
        (key, 'Validate')
        for key in [
            'SubmitEmailAddressButton',
            'SubmitUsernameButton',
        ]
    )

    return urlencode(out)


class _TargetUrlExtractor(_Extractor[str], target='form'):
    @staticmethod
    def _process(tag: Tag | None) -> str | None:
        if not tag:
            return None

        post_url = tag.get('action')

        if not isinstance(post_url, str):
            return None

        return post_url

    def _select(self, tag: Tag) -> bool:
        return super()._select(tag) and tag.has_attr('action')

    def get_one(self) -> str | None:
        return super().get_one()


def extract_post_request_url(content: str, initial_url: str) -> str:
    """Extract the target URL for a POST request from HTML content.

    This function parses HTML content to find the form action URL or target endpoint,
    falling back to the initial URL if no target is found. It handles both absolute
    and relative URLs, converting relative URLs to absolute using the initial URL as base.

    Args:
        content (str): The HTML content to parse for extracting the POST request URL.
        initial_url (str): The initial/base URL to use as fallback and for resolving
                          relative URLs.

    Returns:
        str: The extracted POST request URL. Returns an absolute URL either from
             the extracted target or by joining a relative URL with the initial_url.
             If no URL is found, returns the initial_url.

    """
    soup = BeautifulSoup(content, 'html.parser')
    extracted = _TargetUrlExtractor(soup).get_one() or initial_url

    if extracted.startswith('http'):
        return extracted

    return urljoin(initial_url, extracted)


def extract_filename_from_disposition(disposition: str) -> str | None:
    """Extract filename from Content-Disposition header value.

    Args:
        disposition (str): The Content-Disposition header value, typically in the format
            'attachment; filename="example.txt"' or 'inline; filename=example.txt'
    Returns:
        The extracted filename as a string, if found, None otherwise.
            The filename is stripped of surrounding quotes and whitespace.

    Examples:
        >>> extract_filename_from_disposition('attachment; filename="document.pdf"')
        'document.pdf'
        >>> extract_filename_from_disposition('inline; filename=image.jpg')
        'image.jpg'
        >>> extract_filename_from_disposition('attachment')
        None

    """
    """"""
    pattern = re.compile(r'filename=["\']?(.+?)["\']?$')

    if found := pattern.search(disposition):
        return found.group(1).strip()

    return None


class _ResponseLinkExtractor(_Extractor[tuple[str, str]], target='a'):
    extensions: Final[set[str]] = {'.pdf', '.tif', '.tiff', '.doc', '.docx', '.jpg', '.png'}

    def _select(self, tag: Tag) -> bool:
        return bool(
            super()._select(tag)
            and tag.has_attr("href")
            and (href := tag["href"])
            and isinstance(href, str),
        )  # fmt: skip

    @staticmethod
    def _process(tag: Tag | None) -> tuple[str, str] | None:
        if not tag:
            return None

        href = tag.get('href')

        if not isinstance(href, str):
            return None

        extensions = _ResponseLinkExtractor.extensions

        if any(href.lower().endswith(ext) for ext in extensions):
            return None

        return href.lower(), tag.get_text(strip=True)


def extract_links_from_response_html(
    content: str,
    initial_url: str,
) -> list[DownloadInfo]:
    """Extract download links and their associated names from HTML response content.

    This function parses HTML content to find all links, processes them relative to the
    initial URL, and creates DownloadInfo objects with sanitized names. Links containing
    'viewstate' or 'validation' tokens are filtered out.

    Args:
        content (str): The HTML content to parse for extracting links.
        initial_url (str): The base URL used to resolve relative links found in the content.

    Returns:
        list[DownloadInfo]: A list of DownloadInfo objects, each containing a link URL
            and an associated name. The name is derived from the link's text (if longer
            than 5 characters, with spaces replaced by underscores) or from the URL's
            filename component.

    Notes:
        - Links with text longer than 5 characters use the text as the name (spaces
          replaced with underscores).
        - Links with shorter or no text use the filename from the URL path as the name.
        - Query parameters are stripped from the URL when extracting the filename.
        - Links containing 'viewstate' or 'validation' are excluded from the results.

    """
    soup = BeautifulSoup(content, 'html.parser')
    iterator = _ResponseLinkExtractor(soup).get_iterator()

    min_chars = 5

    out: list[DownloadInfo] = []

    for href, text in iterator:
        link = urljoin(initial_url, href)

        if text and len(text) > min_chars:
            name = text.replace(' ', '_')
        else:
            name = Path(text.split('?')[0]).name

        if not any(tkn in link for tkn in ['viewstate', 'validation']):
            out.append(DownloadInfo(link, name))

    return out

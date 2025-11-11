# ruff: noqa: S101, D102, ANN206

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from bs4 import BeautifulSoup
from eserv.extract import extract_download_info
from rampy import test

from . import SAMPLE_EMAIL, create_sample_email

if TYPE_CHECKING:
    from eserv.extract import DownloadInfo


# -- Test Fixtures -- #


HTML_CONTENT = SAMPLE_EMAIL
FILENAME = 'Test Document.pdf'
DOWNLOAD_URL = 'https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123'


# -- Test Environment -- #


class Namespace(test.namespace[str, str, str, type[Exception] | None]):
    """Namespace for download info test arguments."""

    @property
    def html_content(self) -> str:
        return self.args[0]

    @property
    def expected_link(self) -> str:
        return self.args[1]

    @property
    def expected_name(self) -> str:
        return self.args[2]

    result: DownloadInfo

    @classmethod
    def arguments(
        cls,
        filename: str | tuple[str, str] = FILENAME,
        download_url: str | tuple[str, str] = DOWNLOAD_URL,
        exception: type[Exception] | None = None,
    ):
        if isinstance(filename, tuple):
            expect_filename, actual_filename = filename
        else:
            expect_filename = actual_filename = filename

        if isinstance(download_url, tuple):
            expect_url, actual_url = download_url
        else:
            expect_url = actual_url = download_url

        html_content = create_sample_email(filename=actual_filename, download_url=actual_url)

        return html_content, expect_url, expect_filename, exception


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #


def _ensure_valid_download_info() -> None:
    """Validate that result is a DownloadInfo with expected values."""
    ns = ctx.get()

    assert ns.result.link == ns.expected_link, f'Link mismatch: {ns.result.link} != {ns.expected_link}'
    assert ns.result.name == ns.expected_name, f'Name mismatch: {ns.result.name} != {ns.expected_name}'


reg['simple_valid_email'] = test.case(
    Namespace.arguments(filename='Motion to Dismiss.pdf'),
    hooks=[_ensure_valid_download_info],
)
reg['link_with_extra_whitespace'] = test.case(
    Namespace.arguments(filename='Whitespace Test.pdf', download_url=(DOWNLOAD_URL, f'  {DOWNLOAD_URL}  ')),
    hooks=[_ensure_valid_download_info],
)
reg['page_count_filter'] = test.case(
    Namespace.arguments(filename='Correct Document.pdf'),
    hooks=[_ensure_valid_download_info],
)
reg['missing_filename'] = test.case(Namespace.arguments(filename=''), hooks=[_ensure_valid_download_info])
reg['missing_download_url'] = test.case(Namespace.arguments(download_url='', exception=ValueError))

# -- Test Suite -- #


@test.suite(env)
def test_extract_download_info(
    html_content: str,
    expected_link: str,
    expected_name: str,
    exception: type[Exception] | None,
) -> None:
    """Test extract_download_info function with various HTML inputs.

    This test suite validates:
    - Extraction of Tyler Tech download links from email HTML
    - Extraction of document names from HTML tables
    - Proper handling of multiple links (uses first match)
    - Whitespace trimming in extracted values
    - Edge cases like list href attributes
    - Filtering of 'Page Count' fields from document name extraction
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    if exception is not None:
        with pytest.raises(exception):
            result = extract_download_info(soup)
    else:
        result = extract_download_info(soup)

    ctx(**locals())

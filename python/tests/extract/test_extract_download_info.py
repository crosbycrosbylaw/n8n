"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from eserv.extract import extract_download_info
from rampy import test

from tests.extract import create_sample_email

# -- Test Fixtures -- #


FILENAME = 'Test Document.pdf'
DOWNLOAD_URL = 'https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123'


# -- Test Environment -- #


def _factory(
    filename: str | tuple[str, str] = 'Test Document.pdf',
    download_url: str | tuple[str, str] = DOWNLOAD_URL,
    exception: type[Exception] | None = None,
) -> tuple[str, str, str, type[Exception] | None]:
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


env = test.context.bind(factory=_factory)


# -- Test Cases -- #


def _extracts_download_info() -> None:
    """Validate that result is a DownloadInfo with expected values."""
    ns = env.ns

    result = extract_download_info(ns.soup)

    expected_link = ns.args[1]
    assert result.link == expected_link, f'Link mismatch: {result.link} != {expected_link}'

    expected_name = ns.args[2]
    assert result.name == expected_name, f'Name mismatch: {result.name} != {expected_name}'


def _raises_value_error_on_missing_url() -> None:
    """Validate that the extractor raises a ValueError if no URL is found."""
    with pytest.raises(ValueError, match='could not find download link'):
        extract_download_info(env.ns.soup)


env.register(
    {'name': 'simple valid email', 'hooks': [_extracts_download_info]},
    filename='Motion to Dismiss.pdf',
)
env.register(
    {'name': 'link with extra whitespace', 'hooks': [_extracts_download_info]},
    filename='Whitespace Test.pdf',
    download_url=(DOWNLOAD_URL, f'  {DOWNLOAD_URL}  '),
)
env.register(
    {'name': 'page count filter', 'hooks': [_extracts_download_info]},
    filename='Correct Document.pdf',
)
env.register(
    {'name': 'missing filename', 'hooks': [_extracts_download_info]},
    filename='',
)
env.register(
    {'name': 'missing download url', 'hooks': [_raises_value_error_on_missing_url]},
    download_url='',
    exception=ValueError,
)

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

    if exception:
        with pytest.raises(exception):
            _result = extract_download_info(soup)

    else:
        _result = extract_download_info(soup)

    env.setup(locals())

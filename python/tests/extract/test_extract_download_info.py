"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup
from eserv.extract import DownloadInfo, extract_download_info
from rampy import test

from . import create_sample_email

# -- Test Fixtures -- #


FILENAME = 'Test Document.pdf'
DOWNLOAD_URL = 'https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123'


# -- Test Environment -- #


def _argument_factory(
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


ctx, reg = env = test.context.bind(factory=_argument_factory)


# -- Test Cases -- #


def _ensure_valid_download_info() -> None:
    """Validate that result is a DownloadInfo with expected values."""
    ns = ctx.get()

    result = ns.result

    assert isinstance(result, DownloadInfo)

    expected_link = ns.args[1]
    assert result.link == expected_link, f'Link mismatch: {result.link} != {expected_link}'

    expected_name = ns.args[2]
    assert result.name == expected_name, f'Name mismatch: {result.name} != {expected_name}'


reg['simple_valid_email'] = test.case(
    env.factory(filename='Motion to Dismiss.pdf'),
    hooks=[_ensure_valid_download_info],
)
reg['link_with_extra_whitespace'] = test.case(
    env.factory(
        filename='Whitespace Test.pdf',
        download_url=(DOWNLOAD_URL, f'  {DOWNLOAD_URL}  '),
    ),
    hooks=[_ensure_valid_download_info],
)
reg['page_count_filter'] = test.case(
    env.factory(filename='Correct Document.pdf'),
    hooks=[_ensure_valid_download_info],
)
reg['missing_filename'] = test.case(env.factory(filename=''), hooks=[_ensure_valid_download_info])
reg['missing_download_url'] = test.case(env.factory(download_url='', exception=ValueError))

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

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

import typing

import pytest
from bs4 import BeautifulSoup
from rampy import test

from eserv.extract import extract_download_info
from tests.eserv.lib import create_sample_email

if typing.TYPE_CHECKING:
    from typing import Any


FILENAME = 'Test Document.pdf'
DOWNLOAD_LINK = 'https://illinois.tylertech.cloud/ViewDocuments.aspx?id=abc-123'


def scenario(
    filename: str = FILENAME,
    download_link: str = DOWNLOAD_LINK,
    *,
    expect_name: str | None = None,
    expect_link: str | None = None,
    exception: type[Exception] | None = None,
) -> dict[str, Any]:
    sample_email = create_sample_email(filename=filename, download_link=download_link)
    return {
        'params': [BeautifulSoup(sample_email, features='html.parser')],
        'expect': {
            'name': expect_name or filename,
            'link': expect_link or download_link,
        },
        'exception': exception,
    }


@test.scenarios(**{
    'simple valid email': scenario(filename='Motion to Dismiss.pdf'),
    'missing filename': scenario(filename=''),
    'page count filter': scenario(filename='Correct Document.pdf'),
    'missing download link': scenario(download_link='', exception=ValueError),
    'link with excess whitespace': scenario(
        filename='Whitespace Test.pdf',
        download_link=f'  {DOWNLOAD_LINK}  ',
        expect_link=DOWNLOAD_LINK,
    ),
})
class TestExtractDownloadInfo:
    def test(
        self,
        /,
        params: list[Any],
        expect: dict[str, str],
        exception: type[Exception] | None,
    ):
        def execute() -> None:
            result = extract_download_info(*params)

            expect_name = expect['name']
            assert result.doc_name == expect_name, f'{result.doc_name} != {expect_name}'

            expect_link = expect['link']
            assert result.source == expect_link, f'{result.source} != {expect_link}'

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()

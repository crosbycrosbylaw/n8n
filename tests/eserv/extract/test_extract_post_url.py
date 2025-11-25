"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import Any

from rampy import test

from eserv.extract import extract_post_request_url

INITIAL_URL = 'https://base.com'


def scenario(
    action: str = '',
    initial_url: str = INITIAL_URL,
    expect: str | None = None,
) -> dict[str, Any]:
    return {
        'params': [f'<form {action} method="post"></form>', initial_url],
        'expect': expect or initial_url,
    }


@test.scenarios(**{
    'absolute url': scenario(
        action=rf'action="{INITIAL_URL}/submit"',
        expect=f'{INITIAL_URL}/submit',
    ),
    'relative_url': scenario(
        action=r'action="/api/submit"',
        expect=f'{INITIAL_URL}/api/submit',
    ),
    'no action fallback': scenario(
        action='',
        initial_url=f'{INITIAL_URL}/page',
    ),
})
class TestExtractPostRequestUrl:
    def test(self, /, params: list[Any], expect: str) -> None:
        result = extract_post_request_url(*params)
        assert result == expect, f'URL mismatch: {result} != {expect}'

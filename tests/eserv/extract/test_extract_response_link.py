"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

import typing

from rampy import test

from eserv.extract import extract_links_from_response_html

if typing.TYPE_CHECKING:
    from typing import Any


def scenario(
    *tags: tuple[str, str],
    count: int,
    initial_url: str = 'http://example.com',
) -> dict[str, Any]:
    formatted = f"""
<html>
  <body>
    {
        '<p>no tags</p>'
        if not tags
        else '\n'.join(f'<a href="{href}">{text}</a>' for href, text in tags)
    }
  </body>
</html>
"""
    return {
        'params': [formatted, initial_url],
        'expect': count,
    }


@test.scenarios(**{
    'zero links': scenario(count=0),
    'short text link': scenario(('/doc', 'Doc'), count=1),
    'multiple links': scenario(
        ('/doc1?id=123', 'Document One'),
        ('/doc1?id=456', 'Document Two'),
        ('file.pdf', 'Should be filtered'),
        ('/viewstate?token=abc', 'Should be filtered'),
        count=2,
    ),
})
class TestExtractResponseLink:
    """Test extract_links_from_response_html function.

    Validates:
    - Extraction of multiple links
    - Filtering of direct file extensions
    - Filtering of viewstate/validation links
    - Name derivation from link text
    - URL resolution (relative to absolute)
    """

    def test(self, params: list[str], expect: int) -> None:
        result = extract_links_from_response_html(*params)
        length = len(result)

        assert length == expect, f'Count mismatch: {length} != {expect}'

        for info in result:
            link = info.source.lower()

            assert link.startswith('http'), f'Link should be absolute: {link}'
            assert all(x not in link for x in ('viewstate', 'validation'))

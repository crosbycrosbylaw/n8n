"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from eserv.extract import extract_post_request_url
from rampy import test

# -- Test Environment -- #


def _factory(
    action: str = '',
    initial: str = 'https://base.com',
    expected: str | None = None,
) -> tuple[str, str, str]:
    return f'<form {action} method="post"></form>', initial, expected or initial


env = test.context.bind(factory=_factory)

# -- Test Cases -- #

env.register(
    {'name': 'absolute url'},
    action=r'action="https://example.com/submit"',
    expected='https://example.com/submit',
)
env.register(
    {'name': 'relative_url'},
    action=r'action="/api/submit"',
    expected='https://base.com/api/submit',
)
env.register(
    {'name': 'no action fallback'},
    initial='https://base.com/page',
)

# -- Test Suite -- #


@test.suite(env)
def test_extract_post_request_url(
    html_content: str,
    initial_url: str,
    expected_url: str,
) -> None:
    """Test extract_post_request_url function.

    Validates:
    - Extraction of form action URLs
    - Handling of absolute vs relative URLs
    - Fallback to initial URL when no action found
    """
    result = extract_post_request_url(html_content, initial_url)

    assert result == expected_url, f'URL mismatch: {result} != {expected_url}'

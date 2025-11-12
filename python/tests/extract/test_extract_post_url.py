"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from eserv.extract import extract_post_request_url
from rampy import test

# -- Test Environment -- #


def _args(
    action: str = '',
    *,
    initial: str = 'https://base.com',
    expected: str | None = None,
) -> tuple[str, str, str]:
    return f'<form {action} method="post"></form>', initial, expected or initial


ctx, reg = env = test.context.bind(test.namespace[str, str, str])

# -- Test Cases -- #


env.register(
    'absolute url',
    _args(r'action="https://example.com/submit"', expected='https://example.com/submit'),
)
env.register(
    'relative_url',
    _args(r'action="https://example.com/submit"', expected='https://example.com/submit'),
)
env.register('no action fallback', _args(initial='https://base.com/page'))


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

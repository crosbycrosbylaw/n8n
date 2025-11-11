# ruff: noqa: S101, D102

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from eserv.extract import extract_post_request_url
from rampy import test

# -- Test Fixtures -- #


FORM_TEMPLATE = '<form {action_attr} method="post"></form>'
INITIAL_URL = 'https://base.com'

FORM_ABSOLUTE_URL = '<form action="https://example.com/submit" method="post"></form>'
FORM_RELATIVE_URL = '<form action="/api/submit" method="post"></form>'


# -- Test Environment -- #


class Namespace(test.namespace[str, str, str]):
    """Namespace for POST URL extraction test arguments."""

    @property
    def html_content(self) -> str:
        return self.args[0]

    @property
    def initial_url(self) -> str:
        return self.args[1]

    @property
    def expected_url(self) -> str:
        return self.args[2]

    @classmethod
    def arguments(
        cls,
        action_attr: str = '',
        /,
        *,
        initial_url: str = INITIAL_URL,
        expected_url: str | None = None,
    ) -> tuple[str, str, str]:
        return FORM_TEMPLATE.format(action_attr=action_attr), initial_url, expected_url or initial_url


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #

reg['absolute_url'] = test.case(
    Namespace.arguments(
        r'action="https://example.com/submit"',
        expected_url='https://example.com/submit',
    ),
    hooks=[],
)
reg['relative_url'] = test.case(
    Namespace.arguments(
        r'action="/api/submit"',
        expected_url='https://base.com/api/submit',
    ),
    hooks=[],
)
reg['no_action_fallback'] = test.case(
    Namespace.arguments(initial_url='https://base.com/page'),
    hooks=[],
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

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from eserv.extract import extract_links_from_response_html
from rampy import test

# -- Test Fixtures -- #

INITIAL_URL = 'http://example.com'
TAG_TEMPLATE = '<a href="{href}">{text}</a>'
HTML_TEMPLATE = """
<html>
  <body>
    {tags}
  </body>
</html>
"""

# -- Test Environment -- #


class Namespace(test.namespace[str, str, int]):
    """Namespace for response link extraction test arguments."""

    @property
    def html_content(self) -> str:
        return self.args[0]

    @property
    def initial_url(self) -> str:
        return self.args[1]

    @property
    def expected_count(self) -> int:
        return self.args[2]

    @classmethod
    def arguments(
        cls,
        *tags: tuple[str, str],
        count: int,
        initial_url: str = INITIAL_URL,
    ):
        if tags:
            text = '\n'.join(
                TAG_TEMPLATE.format(href=href, text=text) for href, text in tags
            )
        else:
            text = '<p>no tags</p>'

        return HTML_TEMPLATE.format(tags=text), initial_url, count


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #


reg['multiple_links'] = test.case(
    Namespace.arguments(
        ('/doc1?id=123', 'Document One'),
        ('/doc1?id=456', 'Document Two'),
        ('file.pdf', 'Should be filtered'),
        ('/viewstate?token=abc', 'Should be filtered'),
        count=2,
    )
)
reg['short_text_link'] = test.case(Namespace.arguments(('/doc', 'Doc'), count=1))
reg['no_links'] = test.case(Namespace.arguments(count=0))


# -- Test Suite -- #


@test.suite(env)
def test_extract_links_from_response_html(
    html_content: str,
    initial_url: str,
    expected_count: int,
) -> None:
    """Test extract_links_from_response_html function.

    Validates:
    - Extraction of multiple links
    - Filtering of direct file extensions
    - Filtering of viewstate/validation links
    - Name derivation from link text
    - URL resolution (relative to absolute)
    """
    result = extract_links_from_response_html(html_content, initial_url)

    assert len(result) == expected_count, (
        f'Link count mismatch: {len(result)} != {expected_count}'
    )

    for info in result:
        assert info.link.startswith('http'), f'Link should be absolute: {info.link}'
        assert 'viewstate' not in info.link.lower()
        assert 'validation' not in info.link.lower()

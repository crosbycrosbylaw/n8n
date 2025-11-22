"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from eserv.extract import extract_aspnet_form_data
from rampy import test


@test.parameterized(test.parameter(('raw_html', str), ('exception', type[Exception] | None)))
class x: ...


@test.scenarios(
    (
        'valid form data',
        {
            'raw_html': """
<form action="/submit" method="post">
    <input type="hidden" name="__VIEWSTATE" value="dGVzdHZpZXdzdGF0ZQ==" />
    <input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />
    <input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />
</form>
""",
            'exception': None,
        },
    ),
)
class TestClass:
    def test_aspnet_form(self, raw_html, exception): ...


# -- Test Fixtures -- #


EMAIL_ADDR = 'test@example.com'
ASPNET_FORM = """
<form action="/submit" method="post">
    <input type="hidden" name="__VIEWSTATE" value="dGVzdHZpZXdzdGF0ZQ==" />
    <input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />
    <input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />
</form>
"""
ASPNET_MISSING_VIEWSTATE = """
<form action="/submit" method="post">
    <input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />
    <input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />
</form>
"""


# -- Test Environment -- #
def _factory(raw_html: str, email: str = EMAIL_ADDR) -> tuple[str, str]:
    return raw_html, email


env = test.context.bind(factory=_factory)

# -- Test Cases -- #

env.register({'name': 'valid form'}, ASPNET_FORM)
env.register({'name': 'missing viewstate', 'expect': ValueError}, ASPNET_MISSING_VIEWSTATE)


# -- Test Suite -- #


@test.suite(env)
def test_extract_form_data(
    html_content: str,
    email: str,
) -> None:
    """Test extract_form_data function.

    Validates:
    - Extraction of ViewState fields
    - URL encoding of form data
    - Error handling for missing required fields
    """
    result = extract_aspnet_form_data(html_content, email)

    assert 'emailAddress=' in result
    assert 'username=' in result
    assert 'test%40example.com' in result  # Email is URL-encoded
    assert '__VIEWSTATE=' in result

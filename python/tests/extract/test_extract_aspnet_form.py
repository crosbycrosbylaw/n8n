# ruff: noqa: S101, D102

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

import pytest
from eserv.extract import extract_aspnet_form_data
from rampy import test

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


class Namespace(test.namespace[str, str, type[Exception] | None]):
    """Namespace for ASP.NET form data test arguments."""

    @property
    def html_content(self) -> str:
        return self.args[0]

    @property
    def email(self) -> str:
        return self.args[1]

    @property
    def exception(self) -> type[Exception] | None:
        return self.args[2]

    @classmethod
    def arguments(
        cls,
        raw_html: str,
        *,
        email: str = EMAIL_ADDR,
        raises: type[Exception] | None = None,
    ) -> tuple[str, str, type[Exception] | None]:
        return raw_html, email, raises


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #


reg['valid_form'] = test.case(Namespace.arguments(ASPNET_FORM))
reg['missing_viewstate'] = test.case(Namespace.arguments(ASPNET_MISSING_VIEWSTATE, raises=ValueError))


# -- Test Suite -- #


@test.suite(env)
def test_extract_form_data(
    html_content: str,
    email: str,
    exception: type[Exception] | None,
) -> None:
    """Test extract_form_data function.

    Validates:
    - Extraction of ViewState fields
    - URL encoding of form data
    - Error handling for missing required fields
    """
    if exception:
        with pytest.raises(exception):
            extract_aspnet_form_data(html_content, email)
    else:
        result = extract_aspnet_form_data(html_content, email)

        assert 'emailAddress=' in result
        assert 'username=' in result
        assert 'test%40example.com' in result  # Email is URL-encoded
        assert '__VIEWSTATE=' in result

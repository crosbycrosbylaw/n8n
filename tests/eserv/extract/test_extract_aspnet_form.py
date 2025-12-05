"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from rampy import test

from eserv.extract import extract_aspnet_form_data

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


def aspnet_form_scenario(
    input_tags: Iterable[str],
    /,
    should_raise: type[Exception] | None = None,
    email_address: str = 'test@example.com',
) -> dict[str, Any]:
    """Create test scenario for ASP.NET form extraction."""
    formatted = f"""
<form action="/submit" method="post">
    {'\n'.join(s.strip() for s in input_tags)}
</form>
"""
    return {
        'params': [formatted, email_address],
        'should_raise': should_raise,
    }


@test.scenarios(**{
    'valid form data': aspnet_form_scenario([
        '<input type="hidden" name="__VIEWSTATE" value="dGVzdHZpZXdzdGF0ZQ==" />',
        '<input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />',
        '<input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />',
    ]),
    'missing viewstate': aspnet_form_scenario(
        [
            '<input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />',
            '<input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />',
        ],
        should_raise=ValueError,
    ),
})
class TestExtractAspNetFormData:
    """Test ASP.NET form data extraction."""

    def test(self, /, params: list[str], should_raise: type[Exception] | None):
        """Test form extraction with various inputs."""
        if should_raise is not None:
            with pytest.raises(should_raise):
                extract_aspnet_form_data(*params)
        else:
            result = extract_aspnet_form_data(*params)

            assert 'emailAddress=' in result
            assert 'username=' in result
            assert 'test%40example.com' in result  # Email is URL-encoded
            assert '__VIEWSTATE=' in result

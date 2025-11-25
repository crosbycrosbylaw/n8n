"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from eserv.extract import extract_aspnet_form_data
from rampy import test

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


def scenario(
    input_tags: Iterable[str],
    /,
    exception: type[Exception] | None = None,
    email_address: str = 'test@example.com',
) -> dict[str, Any]:
    formatted = f"""
<form action="/submit" method="post">
    {'\n'.join(s.strip() for s in input_tags)}
</form>
"""
    return {
        'params': [formatted, email_address],
        'exception': exception,
    }


@test.scenarios(**{
    'valid form data': scenario([
        '<input type="hidden" name="__VIEWSTATE" value="dGVzdHZpZXdzdGF0ZQ==" />',
        '<input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />',
        '<input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />',
    ]),
    'missing viewstate': scenario(
        [
            '<input type="hidden" name="__VIEWSTATEGENERATOR" value="ABC123" />',
            '<input type="hidden" name="__EVENTVALIDATION" value="XYZ789" />',
        ],
        exception=ValueError,
    ),
})
class TestExtractAspNetFormData:
    def test(self, /, params: list[str], exception: type[Exception] | None):

        def execute() -> None:
            result = extract_aspnet_form_data(*params)

            assert 'emailAddress=' in result
            assert 'username=' in result
            assert 'test%40example.com' in result  # Email is URL-encoded
            assert '__VIEWSTATE=' in result

        if exception is not None:
            with pytest.raises(exception):
                execute()
        else:
            execute()

"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from eserv.extract import extract_filename_from_disposition
from rampy import test

if TYPE_CHECKING:
    from typing import Literal


# -- Test Fixtures -- #


DISPOSITION_TEMPLATE = 'attachment; filename={text}'


# -- Test Environment -- #


def _factory(
    filename: str | None,
    *,
    quote: Literal['single', 'double', False] | None,
) -> tuple[str, str | None]:
    original_filename = filename

    if filename and quote:
        match quote:
            case 'single':
                filename = f"'{filename}'"
            case 'double':
                filename = f'"{filename}"'

    text = 'attachment' if not filename else DISPOSITION_TEMPLATE.format(text=filename)

    return text, original_filename or None


env = test.context.bind(factory=_factory)


# -- Test Cases -- #


env.register({'name': 'unquoted filename'}, filename='image.jpg', quote=False)
env.register({'name': 'double quoted filename'}, filename='document.pdf', quote='double')
env.register({'name': 'single quoted filename'}, filename='report.doc', quote='single')
env.register({'name': 'no filename'}, filename=None, quote=None)
env.register({'name': 'filename with spaces'}, filename='Some Document.pdf', quote='double')

# -- Test Suite -- #


@test.suite(env)
def test_extract_filename_from_disposition(
    disposition: str,
    expected: str | None,
) -> None:
    """Test extract_filename_from_disposition function.

    Validates:
    - Extraction from quoted filenames
    - Extraction from unquoted filenames
    - Handling of missing filename parameter
    - Proper handling of special characters
    """
    result = extract_filename_from_disposition(disposition)

    assert result == expected, f'Filename mismatch: {result} != {expected}'

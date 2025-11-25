"""Test suite for extract.py HTML extraction utilities.

This module tests the extractor classes and functions that parse HTML content
from Tyler Technologies Illinois cloud service emails and web pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rampy import test

from eserv.extract import extract_filename_from_disposition

if TYPE_CHECKING:
    from typing import Literal


def scenario(
    filename: str | None,
    *,
    quote: Literal['single', 'double', False] | None,
) -> dict[str, Any]:
    original_filename = filename
    if filename and quote:
        match quote:
            case 'single':
                filename = f"'{filename}'"
            case 'double':
                filename = f'"{filename}"'

    return {
        'params': ['attachment' if not filename else f'attachment; filename={filename}'],
        'expect': original_filename or None,
    }


@test.scenarios(**{
    'unquoted filename': scenario('image.jpg', quote=False),
    'double quoted filename': scenario('document.pdf', quote='double'),
    'single quoted filename': scenario('report.doc', quote='single'),
    'missing filename': scenario(None, quote=None),
    'filename with spaces': scenario('Some Document.pdf', quote='double'),
})
class TestExtractContentDisposition:
    def test(self, /, params: list[str], expect: str | None) -> None:
        result = extract_filename_from_disposition(*params)
        assert result == expect, f'Filename mismatch: {result} != {expect}'

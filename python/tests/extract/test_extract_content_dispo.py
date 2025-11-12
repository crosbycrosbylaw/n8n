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


class Namespace(test.namespace[str, str | None]):
    """Namespace for Content-Disposition test arguments."""

    @property
    def disposition(self) -> str:
        return self.args[0]

    @property
    def expected(self) -> str | None:
        return self.args[1]

    @classmethod
    def arguments(
        cls,
        filename: str | None,
        *,
        quote: Literal['single', 'double', False] | None,
    ):
        original_filename = filename

        if filename and quote:
            match quote:
                case 'single':
                    filename = f"'{filename}'"
                case 'double':
                    filename = f'"{filename}"'

        text = (
            'attachment' if not filename else DISPOSITION_TEMPLATE.format(text=filename)
        )

        return text, original_filename or None


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #


reg['quoted_filename'] = test.case(Namespace.arguments('document.pdf', quote='double'))
reg['unquoted_filename'] = test.case(Namespace.arguments('image.jpg', quote=False))
reg['single_quoted'] = test.case(Namespace.arguments('report.doc', quote='single'))
reg['no_filename'] = test.case(Namespace.arguments(filename=None, quote=None))
reg['filename_with_spaces'] = test.case(
    Namespace.arguments(filename='My Document.pdf', quote='double')
)


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

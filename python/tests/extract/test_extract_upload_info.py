from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from eserv.extract import extract_upload_info
from rampy import test

from . import create_sample_email

if TYPE_CHECKING:
    from eserv.extract import UploadInfo


# -- Test Fixtures -- #


CASE_NAME = 'DAILEY EMILY vs. DAILEY DERRICK'


# -- Test Environment -- #


class Namespace(test.namespace[str, Path, int, str | None]):
    """Namespace for upload info test arguments."""

    result: UploadInfo

    @property
    def html_content(self) -> str:
        return self.args[0]

    @property
    def store_path(self) -> Path:
        return self.args[1]

    @property
    def expected_count(self) -> int:
        return self.args[2]

    @property
    def expected_case(self) -> str | None:
        return self.args[3]

    @classmethod
    def arguments(
        cls,
        count: int,
        expect: str | None = CASE_NAME,
        /,
        *,
        case_name: str = CASE_NAME,
        **kwds: str,
    ) -> tuple[str, Path, int, str | None]:
        store = test.path(f'test_store_{count}', mkdir=True)

        for i in range(count):
            (store / f'doc_{i}.pdf').touch()

        kwds.update(case_name=case_name)

        return create_sample_email(kwds), store, count, expect


ctx, reg = env = test.context.bind(Namespace)


# -- Test Cases -- #


def _ensure_valid_upload_info() -> None:
    """Validate UploadInfo extraction."""
    ns = ctx.get()

    assert ns.result.doc_count == ns.expected_count, (
        f'Count mismatch: {ns.result.doc_count} != {ns.expected_count}'
    )
    assert ns.result.case_name == ns.expected_case, (
        f'Case mismatch: {ns.result.case_name} != {ns.expected_case}'
    )


reg['valid_case_with_docs'] = test.case(
    Namespace.arguments(3),
    hooks=[_ensure_valid_upload_info],
)
reg['empty_store'] = test.case(
    Namespace.arguments(0),
    hooks=[_ensure_valid_upload_info],
)
reg['confidential_case'] = test.case(
    Namespace.arguments(1, None, case_name='CONFIDENTIAL'),
    hooks=[_ensure_valid_upload_info],
)


# -- Test Suite -- #


@test.suite(env)
def test_extract_upload_info(
    html_content: str,
    store_path: Path,
    expected_count: int,
    expected_case: str | None,
) -> None:
    """Test extract_upload_info function.

    Validates:
    - Document counting from store directory
    - Case name extraction from HTML
    - Filtering of confidential cases
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    result = extract_upload_info(soup, store_path)

    ctx(**locals())

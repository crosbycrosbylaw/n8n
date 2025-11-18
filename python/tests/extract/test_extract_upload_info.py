from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from eserv.extract import extract_upload_info
from rampy import test

from tests.extract import create_sample_email

if TYPE_CHECKING:
    from pathlib import Path


# -- Test Fixtures -- #


CASE_NAME = 'DAILEY EMILY vs. DAILEY DERRICK'


# -- Test Environment -- #


def _factory(
    count: int,
    expect: str | None = CASE_NAME,
    case_name: str = CASE_NAME,
    **kwds: str,
) -> tuple[str, Path, int, str | None]:
    store = test.path(f'test_store_{count}', mkdir=True)

    for i in range(count):
        (store / f'doc_{i}.pdf').touch()

    kwds.update(case_name=case_name)

    return create_sample_email(kwds), store, count, expect


env = test.context.bind(factory=_factory)


# -- Test Cases -- #


def _ensure_valid_upload_info() -> None:
    """Validate UploadInfo extraction."""
    ns = env.ns

    expected_count = ns.args[2]
    assert ns.result.doc_count == expected_count, (
        f'Count mismatch: {ns.result.doc_count} != {expected_count}'
    )

    expected_case = ns.args[3]
    assert ns.result.case_name == expected_case, (
        f'Case mismatch: {ns.result.case_name} != {expected_case}'
    )


hooks = [_ensure_valid_upload_info]

env.register({'name': 'valid case with docs', 'hooks': hooks}, count=3)
env.register({'name': 'empty store', 'hooks': hooks}, count=0)
env.register({'name': 'confidential case', 'hooks': hooks}, count=1, case_name='CONFIDENTIAL')


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

    env.setup(locals(), result=extract_upload_info(soup, store_path))

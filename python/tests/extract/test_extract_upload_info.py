from __future__ import annotations

from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from eserv.extract import extract_upload_info
from rampy import test

from tests.utils import create_sample_email

if TYPE_CHECKING:
    from typing import Any


CASE_NAME = 'DAILEY EMILY vs. DAILEY DERRICK'
TEMP = test.directory('rampy_pytest')


def scenario(
    count: int,
    cname: str = CASE_NAME,
    /,
    **expect: object,
) -> dict[str, Any]:
    expect.setdefault('case_name', CASE_NAME)
    expect.setdefault('doc_count', count)

    content = create_sample_email(case_name=cname)
    soup = BeautifulSoup(content, features='html.parser')

    store_path = TEMP / f'test_store_{count}'
    store_path.mkdir(parents=True, exist_ok=True)

    for i in range(count):
        doc_path = store_path / f'doc_{i}.pdf'
        doc_path.touch(exist_ok=True)

    return {'params': [soup, store_path], 'expect': expect}


@test.scenarios(**{
    'valid case with docs': scenario(3),
    'empty document store': scenario(0),
    'confidential case': scenario(1, 'CONFIDENTIAL', case_name=None),
})
class TestExtractUploadInfo:
    """Test extract_upload_info function.

    Validates:
    - Document counting from store directory
    - Case name extraction from HTML
    - Filtering of confidential cases
    """

    def test(self, /, params: list[Any], expect: dict[str, Any]) -> None:
        result = extract_upload_info(*params)

        expect_doc_count = expect['doc_count']
        assert result.doc_count == expect_doc_count, \
            f'Count mismatch: {result.doc_count} != {expect_doc_count}'  # fmt: skip

        expect_case_name = expect['case_name']
        assert result.case_name == expect_case_name, \
            f"Case name mismatch: {result.case_name} != {expect_case_name}"  # fmt: skip

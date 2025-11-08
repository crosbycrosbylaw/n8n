from __future__ import annotations

import typing
from pathlib import Path

from bs4 import BeautifulSoup

from . import download_documents, extract_upload_info, resolve_document_desination, serialize_output

if typing.TYPE_CHECKING:
    pass


@serialize_output
def main(path: Path):
    path = path.resolve(strict=True)

    with path.open() as io:
        soup = BeautifulSoup(io, "html.parser")

    store_path = download_documents(soup)

    doc_count, case_name = extract_upload_info(soup, store_path)

    resolve_document_desination(case_name)

    # todo: name extraction, dropbox index lookup, file upload workflow

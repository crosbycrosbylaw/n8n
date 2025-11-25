from __future__ import annotations

import typing

from bs4 import BeautifulSoup

from .download import download_documents
from .extract import extract_upload_info
from .resolve import resolve_document_desination
from .serialize import serialize_output

if typing.TYPE_CHECKING:
    from pathlib import Path


@serialize_output
def main(path: Path) -> None:  # noqa: D103

    with path.resolve(strict=True).open() as io:
        soup = BeautifulSoup(io, 'html.parser')

    store_path = download_documents(soup)

    upload_info = extract_upload_info(soup, store_path)

    resolve_document_desination(upload_info.case_name)

    # todo: name extraction, dropbox index lookup, file upload workflow

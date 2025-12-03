from __future__ import annotations

import typing

import requests
from requests.models import CaseInsensitiveDict

from eserv.extract import *
from eserv.util import document_store

if typing.TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Final

    from bs4 import BeautifulSoup
    from requests import Response
    from requests.sessions import Session


ACCEPT: Final[list[str]] = ['application/pdf', 'application/octet-stream']
OPTIONS: Final[dict[str, Any]] = {'allow_redirects': True, 'timeout': 30}


def _process_accepted_response(
    content: bytes,
    file_no: int | None,
    content_disposition: str,
) -> bytes | tuple[str, bytes]:
    name = extract_filename_from_disposition(content_disposition)

    if name is not None:
        return (name, content)

    if file_no is not None:
        return (f'attachment_{file_no}', content)

    return content


def _bypass_aspnet_form(
    session: Session,
    base_text: str,
    base_link: str,
    email: str = 'eservice@crosbyandcrosbylaw.com',
) -> Response:
    headers = CaseInsensitiveDict[str]()
    headers['user-agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/91.0.4472.124 Safari/537.36'
    headers['accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    headers['content-type'] = 'application/x-www-form-urlencoded'
    headers['referer'] = base_link

    request_data = extract_aspnet_form_data(base_text, email)
    request_link = extract_post_request_url(base_text, base_link)

    response = session.post(request_link, headers=headers, data=request_data, **OPTIONS)
    response.raise_for_status()

    return response


def _process_response(
    session: Session,
    response: Response,
    depth: int = 0,
    file_no: int | None = None,
) -> list[bytes | tuple[str, bytes]]:
    if depth > 1:
        message = 'exceeded maximum recursion depth'

        raise RuntimeError(message)

    content = CaseInsensitiveDict[str]()
    content.update({
        name.lower().removeprefix('content-'): val
        for name, val in response.headers.lower_items()
        if name.lower().startswith('content-')
    })

    content.setdefault('type', '')
    content.setdefault('disposition', '')

    base_text = response.text
    base_link = response.url

    if any(x in content['type'] for x in ACCEPT):
        processed = _process_accepted_response(response.content, file_no, content['disposition'])

        return [processed]

    if 'text/html' not in content['type']:
        message = f"recieved response with unknown content-type: '{content['type']}'"

        raise ValueError(message)

    if '__VIEWSTATE' in base_text:
        post_response = _bypass_aspnet_form(session, base_text, base_link)

        return _process_response(session, post_response, depth + 1)

    out: list[bytes | tuple[str, bytes]] = []
    extracted = extract_links_from_response_html(base_text, base_link)

    if not extracted:
        message = 'HTML parsed, but no valid document links were found.'

        raise ValueError(message)

    rerun_depth = depth + 1

    for i, info in enumerate(extracted):
        new_response = session.get(info.source, **OPTIONS)
        new_response.raise_for_status()

        out.extend(_process_response(session, new_response, rerun_depth, i))

    return out


def download_documents(soup: BeautifulSoup) -> tuple[str | None, Path]:
    """Download documents from a webpage and save them to a local store.

    This function extracts download information from a BeautifulSoup object, creates a
    document store directory, downloads documents via HTTP session, processes the response,
    and saves the documents as PDF files with sanitized filenames.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the parsed HTML page
            with document download information.

    Returns:
        out (tuple[str | None, Path]):
            A tuple containing the extracted document name (if it exists, otherwise `None`) and \
                a `Path` object pointing to the directory where the downloaded documents were stored.

    Note:
        - The function expects extract_download_info() to return an object with 'name' and 'link' attributes.
        - Downloaded files are saved with sanitized filenames (only alphanumeric characters and ., _, -, space).
        - All downloaded files are saved with a .pdf extension.
        - If _process_response() returns bytes, files are named as "{info.name}_{index}.pdf".

    """
    info = extract_download_info(soup)
    store = document_store(info.doc_name)

    with requests.sessions.Session() as session:
        response = session.get(info.source, **OPTIONS)
        response.raise_for_status()

        docs = _process_response(session, response)

        for i, val in enumerate(docs):
            if isinstance(val, bytes):
                name = f'{info.doc_name}_{i}.pdf'
                content = val
            else:
                name, content = val

            name = ''.join(c for c in name if c.isalnum() or c in {' ', '.', '_', '-'})

            path = store / name
            path = path.with_suffix('.pdf')

            path.write_bytes(content)

    return info.doc_name, store

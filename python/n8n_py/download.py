from __future__ import annotations

import typing
from pathlib import Path

import requests

from . import (
    extract_aspnet_form_data,
    extract_download_info,
    extract_filename_from_disposition,
    extract_links_from_response_html,
    extract_post_request_url,
    get_document_store,
)

if typing.TYPE_CHECKING:
    from bs4 import BeautifulSoup
    from requests import Response
    from requests.sessions import Session

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def _process_response(
    session: Session,
    response: Response,
    depth: int = 0,
) -> list[bytes | tuple[str, bytes]]:
    content = {
        name.removeprefix("content-"): val
        for name, val in response.headers.lower_items()
        if name.startswith("content-")
    }

    content.setdefault("type", "")
    content.setdefault("disposition", "")

    base_text = response.text
    base_link = response.url

    out: list[bytes | tuple[str, bytes]] = []

    if "text/html" in content["type"] and "__VIEWSTATE" in base_text:
        if depth == 0:
            headers = HEADERS.copy()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            headers["Referer"] = base_link

            email = "eservice@crosbyandcrosbylaw.com"

            request_data = extract_aspnet_form_data(base_text, email)
            request_link = extract_post_request_url(base_text, base_link)

            post_res = session.post(
                request_link,
                headers=headers,
                data=request_data,
                allow_redirects=True,
                timeout=30,
            )
            post_res.raise_for_status()

            out.extend(_process_response(session, post_res, depth + 1))

        elif depth == 1:
            extracted = extract_links_from_response_html(base_text, base_link)

            if not extracted:
                message = "HTML parsed, but no valid document links were found."
                raise Warning(message)

            rerun_depth = depth + 1

            for i, info in enumerate(extracted):
                new_response = session.get(
                    info.link,
                    allow_redirects=True,
                    timeout=30,
                )
                new_response.raise_for_status()

                info = (info.link, f"{info.name}_{i}")

                out.extend(_process_response(session, new_response, rerun_depth))
        else:
            message = "exceeded maximum recursion depth"
            raise RuntimeError(message)

    elif any(
        x in content["type"]
        for x in [
            "application/pdf",
            "application/octet-stream",
        ]
    ):
        disp = content["disposition"]
        name = extract_filename_from_disposition(disp)

        if name is not None:
            out.append((name, response.content))
        else:
            out.append(response.content)

    else:
        message = f"recieved response with unknown content-type: {content['type']}"
        raise ValueError(message)

    return out


def download_documents(soup: BeautifulSoup) -> Path:
    info = extract_download_info(soup)

    store = get_document_store(info.name)

    with requests.sessions.Session() as session:
        initial_response = session.get(
            info.link,
            allow_redirects=True,
            timeout=30,
        )
        initial_response.raise_for_status()

        docs = _process_response(session, initial_response)

        for i, val in enumerate(docs):
            if isinstance(val, bytes):
                name = f"{info.name}_{i}.pdf"
                content = val
            else:
                name, content = val

            name = "".join(c for c in name if c.isalnum() or c in (" ", ".", "_", "-"))

            path = store / name
            path = path.with_suffix(".pdf")

            path.write_bytes(content)

    return store

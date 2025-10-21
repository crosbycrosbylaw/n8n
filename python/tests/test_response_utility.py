# ruff: noqa: F401, F811

from pathlib import Path
from typing import cast

import n8n_py.parser.cls as parsermod
from requests import Response

from . import path


class FakeResponse:
    def __init__(self, content: bytes, headers: dict[str, str] | None = None, encoding: str = "utf-8"):
        self.content = content
        self.headers = headers or {}
        self.encoding = encoding

    def raise_for_status(self):
        return None


def test_size_mismatch_warning(monkeypatch):
    pdf_bytes = b"ABC"
    headers = {
        "Content-Type": "application/pdf",
        # claim a different length to trigger mismatch warning
        "Content-Length": str(len(pdf_bytes) + 2),
    }

    tempdir = path("resp-util-1")
    tempdir.mkdir()
    monkeypatch.setattr(parsermod, "TMP", tempdir)

    resp = FakeResponse(pdf_bytes, headers=headers)
    ru = parsermod.ResponseUtility(cast(Response, resp))

    path_str, warning = ru.save_attachment()
    p = Path(path_str)

    assert p.exists()
    assert p.read_bytes() == pdf_bytes
    assert warning and "differs" in warning

    # cleanup
    p.unlink()
    tempdir.rmdir()


def test_filename_from_disposition(monkeypatch):
    pdf_bytes = b"PDFDATA"
    headers = {
        "Content-Type": "application/pdf",
        "Content-Length": str(len(pdf_bytes)),
        "Content-Disposition": 'attachment; filename="testfile.pdf"',
    }

    tempdir = path("resp-util-2")
    tempdir.mkdir()

    monkeypatch.setattr(parsermod, "TMP", tempdir)

    resp = FakeResponse(pdf_bytes, headers=headers)
    ru = parsermod.ResponseUtility(cast(Response, resp))

    path_str, warning = ru.save_attachment()
    p = Path(path_str)

    assert p.exists()
    assert p.name == "testfile.pdf"
    assert p.read_bytes() == pdf_bytes
    assert warning is None

    # cleanup
    p.unlink()
    tempdir.rmdir()

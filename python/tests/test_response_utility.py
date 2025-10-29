# ruff: noqa: F401, F811

from pathlib import Path

import pytest
from rampy import test

from . import Response

tmp = test.path("response-util")


@pytest.fixture
def rupatch(monkeypatch):
    import n8n_py.parser.cls as parsermod

    monkeypatch.setattr(parsermod, "TMP", tmp)
    return parsermod.ResponseUtility


b = b""
specs = {}


class namespace(test.ns[bytes, dict[str, str]]):
    p: Path
    warning: str | None


def ext_size_mismatch_warning():
    ns = namespace.get()
    pdf_bytes = ns.args[0]

    assert ns.p.exists()
    assert ns.p.read_bytes() == pdf_bytes
    assert ns.warning and "differs" in ns.warning


b = b"ABC"
specs["size_warning"] = test.spec(
    (b, {"Content-Type": "application/pdf", "Content-Length": str(len(b) + 2)}),
    [test.hook(ext_size_mismatch_warning)],
)


def ext_filename_from_disposition():
    ns = namespace.get()
    assert ns.p.exists()
    assert ns.p.name == "file.pdf"
    assert ns.p.read_bytes() == ns.args[0]
    assert ns.warning is None


b = b"PDFDATA"
specs["gets_filename"] = test.spec(
    (
        b,
        {
            "Content-Type": "application/pdf",
            "Content-Length": str(len(b)),
            "Content-Disposition": 'attachment; filename="file.pdf"',
        },
    ),
    [test.hook(ext_filename_from_disposition)],
)


@test.suite(["pdf_bytes", "headers"], **specs)
def test_parameterized(__extension, pdf_bytes: bytes, headers: dict[str, str], rupatch):
    tmp.mkdir()

    response = Response(pdf_bytes, headers=headers)
    parser = rupatch(response)

    strpath, warning = parser.save_attachment()
    p = Path(strpath)

    __extension(locals())

    tmp.clean()

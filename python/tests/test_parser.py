# ruff: noqa: F401, F811
# TODO !!
from pathlib import Path

import pytest
from n8n_py.parser.cls import EmailParser
from rampy import typeis, test

from . import Response


def with_bytes(*headers: tuple[str, str], size_offset: int = 0) -> tuple[bytes, dict[str, str]]:
    global b

    head = {"Content-Type": "application/pdf", "Content-Length": str(len(b) + size_offset)}
    head.update(headers)

    return b, head


file = test.path("parser", "file.pdf", context=False)


@pytest.fixture
def tempdir():
    with test.path("parser", mkdir=True) as tmp:
        yield tmp


@pytest.fixture
def parserpatch(monkeypatch, tempdir):
    import n8n_py.parser.cls as parsermod

    b, headers = with_bytes(("Content-Disposition", f'attachment; filename="{file.name}"'))

    def fake_get(_):
        return Response(b, headers=headers)

    monkeypatch.setattr(parsermod.requests, "get", fake_get)
    monkeypatch.setattr(parsermod, "TMP", tempdir)

    return parsermod.EmailParser


class namespace:
    class parser(test.ns[list[str], bytes]):
        parser: EmailParser

    class resputil(test.ns[bytes, dict[str, str]]):
        p: Path
        warning: str | None


env1 = test.context.bind(namespace.parser)


def ext_saves_pdf():
    ns = env1.ctx.get()

    assert (paths := ns.parser.json.get("paths"))
    assert typeis(paths, list[str], strict=True)
    assert len(paths) == len(ns.args[0])

    p = Path(paths[0])
    assert p.exists()
    assert p.as_posix() == file.as_posix()
    assert p.read_bytes() == file.read_bytes() == b


b = b"%PDF-1.4 binarycontent"

env1.reg["saves_pdf"] = test.case(
    ['<html><body><a href="http://example/doc1">Download Document</a></body></html>'],
    hooks=[
        ext_saves_pdf,
        lambda *_: print(f"args={env1.ctx.get().args}\nactual_bytes={file.read_bytes()}"),
    ],
)


@test.suite(env1)
def test_parser_parameterized(input_text: list[str], parserpatch):
    parser = parserpatch(input_text)
    env1.ctx(**locals())


# -- Response Utility --

env2 = test.context.bind(namespace.resputil)


@pytest.fixture
def rupatch(monkeypatch, tempdir):
    import n8n_py.parser.cls as parsermod

    monkeypatch.setattr(parsermod, "TMP", tempdir)
    return parsermod.ResponseUtility


def ext_size_mismatch_warning():
    ns = env2.ctx.get()
    pdf_bytes = ns.args[0]

    assert ns.p.exists()
    assert ns.p.read_bytes() == pdf_bytes
    assert ns.warning and "differs" in ns.warning


b = b"ABC"
env2.reg["size_warning"] = test.case(
    with_bytes(size_offset=-2),
    hooks=[ext_size_mismatch_warning],
)


def ext_filename_from_disposition():
    ns = env2.ctx.get()
    assert ns.p.exists()
    assert ns.p.name == "file.pdf"
    assert ns.p.read_bytes() == ns.args[0]
    assert ns.warning is None


b = b"PDFDATA"
env2.reg["gets_filename"] = test.case(
    with_bytes(("Content-Disposition", f'attachment; filename="{file.name}"')),
    hooks=[ext_filename_from_disposition],
)


@test.suite(env2)
def test_response_util_parameterized(pdf_bytes: bytes, headers: dict[str, str], rupatch):
    response = Response(pdf_bytes, headers=headers)
    parser = rupatch(response)

    strpath, warning = parser.save_attachment()
    p = Path(strpath)

    env2.ctx(**locals())

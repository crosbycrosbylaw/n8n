# ruff: noqa: F401, F811

# TODO !!
from pathlib import Path

import pytest
from n8n_py.parser.cls import EmailParser
from rampy import test, typeis

from . import Response

with test.path("parser", mkdir=True) as tmp:
    file = tmp / "file.pdf"

    @pytest.fixture
    def parserpatch(monkeypatch):
        import n8n_py.parser.cls as parsermod

        def fake_get(_):
            return Response(
                b,
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Length": str(len(b)),
                    "Content-Disposition": f'attachment; filename="{file.name}"',
                },
            )

        monkeypatch.setattr(parsermod.requests, "get", fake_get)
        monkeypatch.setattr(parsermod, "TMP", tmp)

        return parsermod.EmailParser

    class namespace:
        class parser(test.ns[list[str], bytes]):
            parser: EmailParser

        class resputil(test.ns[bytes, dict[str, str]]):
            p: Path
            warning: str | None

    ctx = test.context.bind(namespace.parser)

    b = b""
    specs = {}

    def ext_saves_pdf():
        ns = ctx.get()

        assert (paths := ns.parser.json.get("paths"))
        assert typeis(paths, list[str], strict=True)
        assert len(paths) == len(ns.args[0])

        p = Path(paths[0])
        assert p.exists()
        assert p.as_posix() == file.as_posix()
        assert p.read_bytes() == file.read_bytes() == b

    b = b"%PDF-1.4 binarycontent"
    specs["saves_pdf"] = test.case(
        (['<html><body><a href="http://example/doc1">Download Document</a></body></html>'],),
        [
            ext_saves_pdf,
            lambda *_: print(f"args={ctx.get().args}\nactual_bytes={file.read_bytes()}"),
        ],
    )

    @test.suite(["input_text"], **specs)
    def test_parser_parameterized(input_text: list[str], parserpatch):
        with test.path("parser", mkdir=True):
            parser = parserpatch(input_text)
            ctx(**locals())

    # -- Response Utility --

    specs.clear()

    ctx = test.context.bind(namespace.resputil)

    @pytest.fixture
    def rupatch(monkeypatch):
        import n8n_py.parser.cls as parsermod

        monkeypatch.setattr(parsermod, "TMP", tmp)
        return parsermod.ResponseUtility

    def ext_size_mismatch_warning():
        ns = ctx.get()
        pdf_bytes = ns.args[0]

        assert ns.p.exists()
        assert ns.p.read_bytes() == pdf_bytes
        assert ns.warning and "differs" in ns.warning

    b = b"ABC"
    specs["size_warning"] = test.case(
        (b, {"Content-Type": "application/pdf", "Content-Length": str(len(b) + 2)}),
        [(ext_size_mismatch_warning)],
    )

    def ext_filename_from_disposition():
        ns = ctx.get()
        assert ns.p.exists()
        assert ns.p.name == "file.pdf"
        assert ns.p.read_bytes() == ns.args[0]
        assert ns.warning is None

    b = b"PDFDATA"
    specs["gets_filename"] = test.case(
        (
            b,
            {
                "Content-Type": "application/pdf",
                "Content-Length": str(len(b)),
                "Content-Disposition": 'attachment; filename="file.pdf"',
            },
        ),
        [(ext_filename_from_disposition)],
    )

    @test.suite(["pdf_bytes", "headers"], **specs)
    def test_response_util_parameterized(pdf_bytes: bytes, headers: dict[str, str], rupatch):
        response = Response(pdf_bytes, headers=headers)
        parser = rupatch(response)

        strpath, warning = parser.save_attachment()
        p = Path(strpath)

        ctx(**locals())

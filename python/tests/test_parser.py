# ruff: noqa: F401, F811
from pathlib import Path

import n8n_py.parser.cls as parsermod
from rampy import typed
from rampy.test import path


class FakeResponse:
    def __init__(self, content: bytes, headers: dict[str, str] | None = None, encoding: str = "utf-8"):
        self.content = content
        self.headers = headers or {}
        self.encoding = encoding

    def raise_for_status(self):
        return None


def test_email_parser_saves_pdf(monkeypatch):
    input_text = ['<html><body><a href="http://example/doc1">Download Document</a></body></html>']

    pdf_bytes = b"%PDF-1.4 binarycontent"

    tmp = path("parser")
    tmp.mkdir()

    test_file = tmp / "test.pdf"

    def fake_get(_):
        return FakeResponse(
            pdf_bytes,
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(len(pdf_bytes)),
                "Content-Disposition": f'attachment; filename="{test_file.name}"',
            },
        )

    monkeypatch.setattr(parsermod.requests, "get", fake_get)
    monkeypatch.setattr(parsermod, "TMP", tmp)

    parser = parsermod.EmailParser(input_text, testing=True).setup().run()

    assert "paths" in parser.json
    paths = parser.json["paths"]
    assert typed(list[str])(paths)
    assert len(paths) == len(input_text)

    p = Path(paths[0])

    assert p.exists()
    assert p.as_posix() == test_file.as_posix()
    assert p.read_bytes() == test_file.read_bytes() == pdf_bytes

    print(pdf_bytes)
    print(test_file.read_bytes())

    test_file.unlink()
    tmp.rmdir()

from pathlib import Path

import n8n_py.parser.cls as parsermod

from python.tests.shared import temp


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

    tempdir = temp("test-parser")
    tempdir.mkdir(777, exist_ok=True)

    test_file = tempdir / "test.pdf"

    def fake_get(_):
        return FakeResponse(
            pdf_bytes,
            headers={
                "Content-Type": "application/pdf",
                "Content-Length": str(len(pdf_bytes)),
                "Content-Disposition": f'attachment; filename="{test_file.name}"',
            },
        )

    monkeypatch.setattr(parsermod, "requests", parsermod.requests)
    monkeypatch.setattr(parsermod.requests, "get", fake_get)
    monkeypatch.setattr(parsermod, "TMP", tempdir)

    inst = parsermod.EmailParser(input_text, testing=True)

    inst.setup()
    inst.run()

    assert "paths" in inst.json
    paths = inst.json["paths"]
    assert isinstance(paths, list)
    assert len(paths) == 1

    p = Path(paths[0])

    assert p.exists()
    assert p.as_posix() == test_file.as_posix()
    assert p.read_bytes() == test_file.read_bytes() == pdf_bytes

    print(pdf_bytes)
    print(test_file.read_bytes())

    test_file.unlink()
    tempdir.rmdir()

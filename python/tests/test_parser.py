# ruff: noqa: F401, F811
from pathlib import Path

import n8n_py.parser.cls as parsermod
import pytest
from rampy import test, typeis
from rampy.test import path

from . import Response

tmp = test.path("parser")
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


class namespace(test.ns[list[str], bytes]):
    parser: parsermod.EmailParser


b = b""
specs = {}


def ext_saves_pdf():
    ns = namespace.get()

    assert (paths := ns.parser.json.get("paths"))
    assert typeis(paths, list[str], strict=True)
    assert len(paths) == len(ns.args[0])

    p = Path(paths[0])
    assert p.exists()
    assert p.as_posix() == file.as_posix()
    assert p.read_bytes() == file.read_bytes() == b


b = b"%PDF-1.4 binarycontent"
specs["saves_pdf"] = test.spec(
    (['<html><body><a href="http://example/doc1">Download Document</a></body></html>'],),
    [
        test.hook(ext_saves_pdf),
        test.hook(
            lambda *_: print(f"args={namespace.get().args}\nactual_bytes={file.read_bytes()}"),
            event=test.on.error,
        ),
    ],
)


@test.suite(["input_text"], **specs)
def test_parameterized(__extension, input_text: list[str], parserpatch):
    tmp.mkdir()
    parser = parserpatch(input_text)
    __extension(locals())
    tmp.clean()

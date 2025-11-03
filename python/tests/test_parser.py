# ruff: noqa: F401, F811
# TODO !!
from pathlib import Path

import n8n_py.parser.cls as parsermod
import pytest
from common import samples
from n8n_py.parser.cls import EmailParser
from rampy import debug, json, strict, test, typeis

from . import Response


def with_bytes(*headers: tuple[str, str], size_offset: int = 0) -> tuple[bytes, dict[str, str]]:
    global b

    head = {"Content-Type": "application/pdf", "Content-Length": str(len(b) + size_offset)}
    head.update(headers)

    return b, head


tmp = test.path("parser", context=False)
file = tmp / "file.pdf"


@pytest.fixture
def tempdir():
    try:
        tmp.mkdir()
        yield tmp
    finally:
        tmp.clean()


@pytest.fixture
def requestspatch(monkeypatch):
    b, headers = with_bytes(("Content-Disposition", f'attachment; filename="{file.name}"'))

    def fake_get(_):
        return Response(b, headers=headers)

    monkeypatch.setattr(parsermod.requests, "get", fake_get)


@pytest.fixture
def parserpatch(monkeypatch):
    monkeypatch.setattr(parsermod, "TMP", tmp)

    return parsermod.EmailParser


class namespace:
    class parser(test.ns[list[str], bytes]):
        parser: EmailParser

    class resputil(test.ns[bytes, dict[str, str]]):
        p: Path
        warning: str | None


env1 = test.context.bind(namespace.parser)


def case_saves_pdf():
    ns = env1.ctx.get()

    ns.parser.setup().run()

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
        case_saves_pdf,
        lambda *_: print(f"args={env1.ctx.get().args}\nactual_bytes={file.read_bytes()}"),
    ],
)


@test.suite(env1)
def test_parameterized_a(input_text: list[str], requestspatch, parserpatch, tempdir):
    parser = parserpatch(input_text, testing=True)
    env1.ctx(**locals())


# -- Response Utility --

env2 = test.context.bind(namespace.resputil)


@pytest.fixture
def rupatch(monkeypatch, tempdir):
    import n8n_py.parser.cls as parsermod

    monkeypatch.setattr(parsermod, "TMP", tempdir)
    return parsermod.ResponseUtility


def case_size_mismatch_warning():
    ns = env2.ctx.get()
    pdf_bytes = ns.args[0]

    assert ns.p.exists()
    assert ns.p.read_bytes() == pdf_bytes
    assert ns.warning and "differs" in ns.warning


b = b"ABC"
env2.reg["size_warning"] = test.case(
    with_bytes(size_offset=-2),
    hooks=[case_size_mismatch_warning],
)


def case_filename_from_disposition():
    ns = env2.ctx.get()
    assert ns.p.exists()
    assert ns.p.name == "file.pdf"
    assert ns.p.read_bytes() == ns.args[0]
    assert ns.warning is None


b = b"PDFDATA"
env2.reg["gets_filename"] = test.case(
    with_bytes(("Content-Disposition", f'attachment; filename="{file.name}"')),
    hooks=[case_filename_from_disposition],
)


@test.suite(env2)
def test_parameterized_b(pdf_bytes: bytes, headers: dict[str, str], rupatch, tempdir):
    response = Response(pdf_bytes, headers=headers)
    parser = rupatch(response, {})

    strpath, warning = parser.save_attachment()
    p = Path(strpath)

    env2.ctx(**locals())


env3 = test.context.bind(namespace.parser)

sample = samples.FA[0]


def case_saves_real_pdf():
    ns = env3.ctx.get()

    assert strict() and debug()

    ns.parser.setup()

    assert ns.parser.content == sample["raw_text"]

    ns.parser.run()
    paths = ns.parser.json.get("paths")

    assert typeis(paths, list[str])
    assert len(paths) == 1
    assert tmp.is_dir()

    metadata_path = tmp / "metadata.json"
    assert metadata_path.exists()

    metadata_text = metadata_path.read_text()
    assert len(metadata_text) > 0

    download_path = Path(next(iter(paths)))

    assert download_path in [*tmp.iterdir()]
    assert download_path.exists()
    assert len(download_path.read_bytes()) > 0

    metadata_json = json[str, dict].loads(metadata_text)
    assert download_path.name in metadata_json

    metadata = metadata_json[download_path.name]

    assert typeis(metadata, dict[str, object])
    assert "case_name" in metadata

    case_name = metadata.get("case_name", "")
    assert typeis(case_name, str)

    expected_parties = [" ".join(s for s in x if s) for x in sample["related_parties"]]
    assert all(x in case_name for x in expected_parties)


env3.reg["actual_email"] = test.case([sample["raw_text"]], hooks=[case_saves_real_pdf])


@test.suite(env3)
def test_parameterized_c(input_text: list[str], parserpatch, tempdir):
    parser = parserpatch(input_text, testing=True)
    env3.ctx(**locals())

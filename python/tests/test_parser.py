# ruff: noqa: F401, F811
# TODO !!
from pathlib import Path

import n8n_py.parser.cls as parsermod
import pytest
from common import samples
from n8n_py.parser.cls import EmailParser
from rampy import debug, json, strict, test, typeis

from . import Response

SAMPLE = samples.FA[0]

TMP_ROOT = test.path("parser")
TMP_PDF = TMP_ROOT / "file.pdf"
TMP_METADATA = TMP_ROOT / "metadata.json"

BYTES = b""


def with_bytes(*headers: tuple[str, str], size_offset: int = 0) -> tuple[bytes, dict[str, str]]:
    global BYTES

    head = {"Content-Type": "application/pdf", "Content-Length": str(len(BYTES) + size_offset)}
    head.update(headers)

    return BYTES, head


@pytest.fixture
def tempdir():
    with test.path("parser", mkdir=True, context=True) as tmp:
        yield tmp


@pytest.fixture
def requestspatch(monkeypatch):
    global BYTES

    BYTES, headers = with_bytes(("Content-Disposition", f'attachment; filename="{TMP_PDF.name}"'))

    def fake_get(_):
        return Response(BYTES, headers=headers)

    monkeypatch.setattr(parsermod.requests, "get", fake_get)


@pytest.fixture
def parserpatch(monkeypatch):
    monkeypatch.setattr(parsermod, "TMP", TMP_ROOT)

    return parsermod.EmailParser


class namespace:
    class one(test.ns[list[str]]):
        parser: EmailParser
        path: Path | None = None

    class two(test.ns[bytes, dict[str, str]]):
        p: Path
        warning: str | None


parser_env = c1, r1 = test.context.bind(namespace.one)


def ensure_saved_doc():
    assert all([strict(), debug(), TMP_ROOT.is_dir()]), "test environment must be configured"

    ns = c1.get()
    parser, content = ns.parser, ns.args[0][0]

    parser.setup()

    assert parser.content == content, "should use first text as html content"

    parser.run()

    assert (saved := parser.json.get("paths"))
    assert typeis(saved, list[str]) and len(saved), "should save at least one document"

    assert (strpath := next((p for p in saved), None))
    assert (path := Path(strpath).resolve(strict=True)), "saved document path must resolve"

    assert len(path.read_bytes()) > 0, "saved document must not be empty"

    c1.set(path=path)


def matches_expected_path():
    assert (path := c1.get().path)
    try:
        assert path.resolve(strict=True) == TMP_PDF, "saved path matches expected"
    except FileNotFoundError:
        pytest.fail(f"could not resolve saved document path.\n{path=!s}")


BYTES = b"%PDF-1.4 binarycontent"
r1["saves_documents"] = test.case(
    ['<html><body><a href="http://example/doc1">Download Document</a></body></html>'],
    hooks=[ensure_saved_doc, matches_expected_path],
    fixtures=[requestspatch, parserpatch, tempdir],
)


def saves_doc_with_metadata():
    ns = c1.get()

    assert TMP_METADATA.exists()
    assert len(text := TMP_METADATA.read_text()) > 0, "metadata should not be empty"

    assert ns.path is not None
    assert ns.path.name in (metadata_dict := json[str, dict].loads(text)), "dict must contain document metadata"

    assert typeis(metadata := metadata_dict[ns.path.name], dict[str, object])
    assert (case_name := metadata.get("desc"))

    assert typeis(case_name, str)
    assert all(x.full_name in case_name for x in SAMPLE.parties)


r1["actual_email"] = test.case(
    [SAMPLE.text],
    hooks=[saves_doc_with_metadata],
    fixtures=[parserpatch, tempdir],
)


@test.suite(parser_env)
def test_parameterized_a(argv: list[str]):
    c1(parser=parserpatch(argv, testing=True))


# -- Response Utility --

ru_env = c2, r2 = test.context.bind(namespace.two)


@pytest.fixture
def rupatch(monkeypatch, tempdir):
    import n8n_py.parser.cls as parsermod

    monkeypatch.setattr(parsermod, "TMP", tempdir)
    return parsermod.ResponseUtility


def case_size_mismatch_warning():
    ns = c2.get()
    pdf_bytes = ns.args[0]

    assert ns.p.exists()
    assert ns.p.read_bytes() == pdf_bytes
    assert ns.warning and "differs" in ns.warning


BYTES = b"ABC"
r2["size_warning"] = test.case(
    with_bytes(size_offset=-2),
    hooks=[case_size_mismatch_warning],
)


def case_filename_from_disposition():
    ns = c2.get()
    assert ns.p.exists()
    assert ns.p.name == "file.pdf"
    assert ns.p.read_bytes() == ns.args[0]
    assert ns.warning is None


BYTES = b"PDFDATA"
r2["gets_filename"] = test.case(
    with_bytes(("Content-Disposition", f'attachment; filename="{TMP_PDF.name}"')),
    hooks=[case_filename_from_disposition],
)


@test.suite(ru_env)
def test_parameterized_b(pdf_bytes: bytes, headers: dict[str, str], rupatch, tempdir):
    response = Response(pdf_bytes, headers=headers)
    parser = rupatch(response, {})

    strpath, warning = parser.save_attachment()
    p = Path(strpath)

    c2(**locals())

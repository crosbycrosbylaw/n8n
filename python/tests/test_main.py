from __future__ import annotations

from pathlib import Path

import n8n_py.finder.cls as findermod
import n8n_py.parser.cls as parsermod
import pytest
from common import samples
from common.metadata import refresh_metadata_cache
from n8n_py import main as pipemod
from rampy import js, json, test, typeis

from . import Response

SAMPLE = samples.FA[0]
SAMPLE_TEXT = SAMPLE["raw_text"]

PDF_NAME = SAMPLE["document_name"]
PDF_BYTES = b"%PDF-1.4 pipeline"
PDF_HEADERS = {
    "Content-Type": "application/pdf",
    "Content-Length": str(len(PDF_BYTES)),
    "Content-Disposition": f'attachment; filename="{PDF_NAME}"',
}

TMP_ROOT = test.path("pipeline", context=False)
SERVICE_DIR = TMP_ROOT / "service"
DBX_INDEX = SERVICE_DIR / "dbx_index.json"


class namespace(test.ns[str]):
    result: json[str, object]


@pytest.fixture
def pipeline_env(monkeypatch):
    import common
    import common.metadata as metadata_mod
    import common.temp as tempmod

    TMP_ROOT.mkdir()
    tmp = SERVICE_DIR / "tmp"

    try:
        tmp.mkdir()

        monkeypatch.setattr(common, "TMP", tmp, raising=False)
        monkeypatch.setattr(tempmod, "TMP", tmp, raising=False)
        monkeypatch.setattr(metadata_mod, "_METADATA_PATH", tmp / "metadata.json", raising=False)
        monkeypatch.setattr(parsermod, "TMP", tmp, raising=False)
        monkeypatch.setattr(findermod, "root", lambda: TMP_ROOT, raising=False)

        refresh_metadata_cache()

        yield tmp

    finally:
        refresh_metadata_cache()
        TMP_ROOT.clean()


@pytest.fixture
def requestspatch(monkeypatch):
    def fake_get(_):
        return Response(PDF_BYTES, headers=PDF_HEADERS)

    monkeypatch.setattr(parsermod.requests, "get", fake_get)


def ensure_pipeline_output(result: dict[str, object]):
    paths = result["paths"]
    assert typeis(paths, list[str])
    assert paths, "parser should provide saved paths"
    assert all(Path(p).exists() for p in paths), "saved paths must exist"

    documents = result["documents"]
    assert typeis(documents, list[dict[str, object]])

    assert documents, "metadata documents should be available"
    doc = documents[0]
    assert doc["filename"] == PDF_NAME
    assert doc.get("case_name")
    assert doc.get("filed_by")

    queries = result["queries"]
    assert typeis(queries, list[str])

    assert queries
    assert PDF_NAME in queries

    finder_results = result["finder"]
    assert typeis(finder_results, list[dict[str, object]])

    assert finder_results, "finder should return results"
    case_name = str(doc.get("case_name", ""))
    finder_entry = next(
        (entry for entry in finder_results if str(entry.get("query", "")).lower() == case_name.lower()),
        None,
    )
    assert finder_entry is not None
    matches = finder_entry.get("matches", [])

    assert typeis(matches, list[dict[str, object]])
    assert matches, "finder entry should include matches"


testenv = ctx, reg = test.context.bind(namespace)

path_display = "/Clio/Boudreau, Candace/00001-Boudreau"


def ensure_result():
    ensure_pipeline_output(ctx.get().result)


def case_end_to_end():
    ns = ctx.get()

    finder_results = ns.result["finder"]
    assert typeis(finder_results, list[dict[str, object]])

    match_paths = []
    for entry in finder_results:
        matches = entry.get("matches", [])
        assert typeis(matches, list[dict[str, object]])

        match_paths.extend(m.get("pathDisplay", "") for m in matches)

    assert any(path for path in match_paths), "finder matches should supply path display values"


reg["end_to_end"] = test.case(path_display, hooks=[ensure_result, case_end_to_end])


def case_pipeline_reuses_metadata():
    ns = ctx.get()
    r1 = ns.result

    r2 = pipemod.main()

    ensure_pipeline_output(r2)

    for key in "paths", "queries":
        first, repeat = values = r1[key], r2[key]
        for ls in values:
            assert typeis(ls, list[str])
            if any(s.count("\\") > 1 for s in ls):
                ls[:] = [s.replace("\\", "/") for s in ls]
        assert first == repeat


reg["reuses_metadata"] = test.case(
    path_display,
    hooks=[ensure_result, case_pipeline_reuses_metadata],
)


@test.suite(testenv)
def test_pipeline_parameterized(expected_display: str, pipeline_env, requestspatch):
    DBX_INDEX.write_text(repr(js.array([json(pathDisplay=expected_display)])))
    ctx(result=pipemod.main(SAMPLE["raw_text"]))

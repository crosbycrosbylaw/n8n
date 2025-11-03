# %%

from __future__ import annotations

import re

import pytest
from common.metadata import refresh_metadata_cache
from common.parsehtml import DocumentInfo
from n8n_py.extractor import main, result
from rampy import json, test, typeis


@pytest.fixture
def metadata_env(monkeypatch):
    import common.metadata as metadata_mod
    import common.temp as tempmod

    with test.path("service", mkdir=True) as service_dir:
        tmp_dir = service_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(tempmod, "TMP", tmp_dir)
        monkeypatch.setattr(metadata_mod, "_METADATA_PATH", tmp_dir / "metadata.json")
        refresh_metadata_cache()
        try:
            yield tmp_dir / "metadata.json"
        finally:
            refresh_metadata_cache()


class namespace(test.ns[list[str]]):
    results: list[result]


ctx, cases = test.context.bind(namespace)


def case_normalize_parse():
    ns = ctx.get()
    first = ns.results[0]

    assert typeis(first, dict)
    assert first["found_names"]

    parties = first["parties"]
    assert len(parties) == 2

    p1 = parties[0]
    assert typeis(p1["candidates"], list[dict], strict=True)
    if p1["type"] != "company":
        assert any("smith" in c.get("normalized", "") for c in p1["candidates"])


def case_v_vs_and_company():
    ns = ctx.get()

    assert len(ns.results) == 3

    for res in ns.results[:2]:
        assert res["found_names"]
        assert all(p["type"] == "person" for p in res["parties"])

    with_company = ns.results[2]
    assert with_company["found_names"]

    p1, p2 = with_company["parties"]
    assert p1["type"] == "company"
    assert p2["type"] == "person"


def case_normalize_accents_hyphens():
    ns = ctx.get()
    first = ns.results[0]

    assert first["found_names"]
    assert all(
        any(expected in x.get("normalized", "") for x in candidates if typeis(x, dict))
        for expected, candidates in zip(
            ["o neill", "mary-anne"],
            [p["candidates"] for p in first["parties"] if p["type"] != "company"],
            strict=True,
        )
    )


@test.suite(
    cases,
    normalizes_and_parses=test.case(
        ["Smith v. Jones"],
        hooks=[case_normalize_parse],
    ),
    v_vs_company=test.case(
        ["Smith v Jones", "Johnson vs. Brown", "ACME CORPORATION v. Doe"], hooks=[case_v_vs_and_company]
    ),
    accents_and_hyphens=test.case(
        ["José O'Neill v. Mary-Anne"],
        hooks=[case_normalize_accents_hyphens],
    ),
)
def test_parameterized(input_text: list[str]):
    extractor = main(input_text, testing=True)

    extractor.setup()
    assert len(extractor.normalized) > 0

    extractor.run()

    results = extractor.json.get("results", [])
    typeis(results, list[result], strict=True)
    assert len(results) > 0

    ctx(**locals())


def test_extractor_metadata_shortcut(metadata_env):
    doc: DocumentInfo = {
        "hrefs": [],
        "filename": "Motion to Modify Maintenance RTF.pdf",
        "court": "",
        "case_no": "2014-D-0000740",
        "case_name": "Candace R Boudreau vs. Christopher R Boudreau",
        "filed_by": "Mason Crosby",
        "path": None,
        "path_display": None,
    }

    metadata_store = json[str, DocumentInfo]({doc["filename"]: doc})
    metadata_env.write_text(str(metadata_store))
    refresh_metadata_cache()

    extractor = main([doc["filename"]], testing=True)
    extractor.setup()
    extractor.run()

    results = extractor.json.get("results", [])
    assert results
    first = results[0]
    assert first["found_names"]
    norm_expected = re.sub(r"\W+", "", doc["case_name"].lower())
    norm_actual = re.sub(r"\W+", "", (first["raw_case_text"] or "").lower())
    assert norm_actual == norm_expected

# %%

from __future__ import annotations

import re

import pytest
from common import samples
from common.metadata import refresh_metadata_cache
from common.parsehtml import DocumentInfo  # TODO
from n8n_py.extractor import main, result
from rampy import json, test, typeis

SAMPLE = samples.FA[0]


@pytest.fixture
def metadata_env(monkeypatch):
    from common import metadata, temp

    with test.path("service", context=True, mkdir=True) as root:
        tmp = test.path(root, "tmp", mkdir=True)
        monkeypatch.setattr(temp, "TMP", tmp)
        monkeypatch.setattr(metadata, "_METADATA_PATH", tmp / "metadata.json")
        refresh_metadata_cache()

        try:
            yield tmp / "metadata.json"
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
def test_parameterized(argv: list[str]):
    extractor = main(argv, testing=True)

    extractor.setup()
    assert len(extractor.normalized) > 0

    extractor.run()
    assert (results := extractor.json.get("results", []))
    assert typeis(results, list[result])

    ctx(extractor=extractor)


def test_extractor_metadata_shortcut(metadata_env):
    doc: DocumentInfo = SAMPLE.customize(pick=["name", "desc", "path", "path_display"])

    metadata_store = json[str, DocumentInfo]({doc.name: doc})
    metadata_env.write_text(str(metadata_store))

    refresh_metadata_cache()

    extractor = main([doc.name], testing=True).setup().run()

    assert (results := extractor.json.get("results", []))
    assert (first := results[0]) and first["found_names"]

    assert isinstance(doc.desc, str)
    norm_expected = re.sub(r"\W+", "", doc.desc.lower())

    text = first["raw_case_text"]
    assert isinstance(text, str)
    norm_actual = re.sub(r"\W+", "", text.lower())

    assert norm_actual == norm_expected

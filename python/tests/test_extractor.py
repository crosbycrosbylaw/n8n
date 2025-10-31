from __future__ import annotations

from n8n_py.extractor import main, result
from rampy import test, typeis


class namespace(test.ns[list[str]]):
    results: list[result]


ctx = test.context.bind(namespace)

specs = {}


def ext_normalizes_and_parses():
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


specs["normalizes_parses"] = test.case((["Smith v. Jones"],), [ext_normalizes_and_parses])


def ext_handles_v_vs_and_company():
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


specs["v_vs_and_company"] = test.case(
    (["Smith v Jones", "Johnson vs. Brown", "ACME CORPORATION v. Doe"],),
    [ext_handles_v_vs_and_company],
)


def ext_normalization_accents_hyphens():
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


specs["accents_and_hyphens"] = test.case(
    (["José O'Neill v. Mary-Anne"],),
    [ext_normalization_accents_hyphens],
)


@test.suite(["input_text"], **specs)
def test_parameterized(input_text: list[str]):
    extractor = main(input_text, testing=True)

    extractor.setup()
    assert len(extractor.normalized) > 0

    extractor.run()

    results = extractor.json.get("results", [])
    typeis(results, list[result], strict=True)
    assert len(results) > 0

    ctx(**locals())

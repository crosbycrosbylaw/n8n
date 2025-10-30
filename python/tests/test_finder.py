# ruff: noqa: F401, F811
from __future__ import annotations

import functools
from typing import NamedTuple

import pytest
from n8n_py.finder.cls import FinderResult, FolderFinder, IndexEntry
from rampy import js, json, test, typeis

tmp = test.path("service")


@pytest.fixture
def finderpatch(monkeypatch):
    import n8n_py.finder.cls as findermod

    monkeypatch.setattr(findermod, "root", lambda: tmp.parent)
    return functools.partial(findermod.FolderFinder, testing=True)


specs = {}


class namespace(test.ns[list[str], list[str]]):
    finder: FolderFinder
    results: list[FinderResult]
    entries: js.array[json[str, str]]


def ext_proper_length():
    ns = namespace.get()

    nargs, nitems = len(ns.args[0]), len(ns.entries)

    assert len(ns.finder.index) == nitems
    assert len(ns.finder.choices) == (nargs * nitems)
    assert len(ns.results) == nargs


specs["simple_matching"] = test.spec(
    (["finder", "John Smith"], ["/Clio/Smith, John/00001-Smith", "/Clio/Jones, Mary/00002-Jones"]),
    [ext_proper_length, lambda *_: test.ctx.print(include={"results"})],
)


def ext_match_found():
    ns = namespace.get()

    query = ns.args[0][1]
    result = ns.results[1]

    assert query == result["query"]

    for m in result["matches"]:
        try:
            assert "Smith" in m["pathDisplay"]
            break
        except AssertionError:
            if matched := m.get("matched_label"):
                assert "Smith" in matched
                break


specs["fuzzy_matching"] = test.spec(
    (
        ["finder", "Jon Smth"],
        [
            "/Clio/Smith, John/00001-Smith",
            "/Clio/Smith-Jones, Anna/00002-SmithJones",
            "/Clio/ONeil, Patrick/00003-ONeil",
        ],
    ),
    [ext_match_found, lambda _: test.ctx.print(include={"query", "result"})],
)


def ext_unique_matches():
    ns = namespace.get()

    matches = ns.results[1]["matches"]

    assert typeis(matches, list)
    assert len(matches) == 1


specs["dedupe_keep_highest"] = test.spec(
    (["finder", "John Smith"], ["/Clio/Smith, John/00001-Smith", "/Clio/Smith, John/00001-Smith"]),
    [ext_unique_matches, lambda _: test.ctx.print(include={"matches"})],
)


@test.suite(["input_text", "index_items"], **specs)
def test_finder_paramaterized(
    __extension,
    input_text: list[str],
    index_items: list[str],
    finderpatch,
):
    entries = js.array(json(pathDisplay=path) for path in index_items)

    tmp.mkdir()

    dbx_index = tmp / "dbx_index.json"
    dbx_index.write_text(repr(entries))

    finder = finderpatch(input_text).setup()

    assert finder.dbx_path.as_posix() == dbx_index.as_posix()
    assert typeis(finder.index, list[IndexEntry])
    assert typeis(finder.choices, list[str])

    finder.run()
    results = finder.json.get("results")

    assert typeis(results, list[FinderResult])

    __extension(locals())

    tmp.clean()

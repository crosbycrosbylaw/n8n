# ruff: noqa: F401, F811
from __future__ import annotations

import functools

import pytest
from n8n_py.finder.cls import FinderResult, FolderFinder
from rampy import js, json, test, typed, typeis

SVC = test.path("service", override_base="d:/temp")
DBX = SVC / "dbx_index.json"


@pytest.fixture
def finderpatch(monkeypatch):
    import n8n_py.finder.cls as findermod

    monkeypatch.setattr(findermod, "root", lambda: SVC.parent)
    return functools.partial(findermod.FolderFinder, testing=True)


def get_params():
    return test.ctx.args(tuple[list[str], list[str]])


def get_results():
    return test.ctx.get("results", expect=list[FinderResult])


def ext_proper_length():
    f = test.ctx.get("f", expect=FolderFinder)
    results = get_results()
    input_text = get_params()[0]

    nargs = len(input_text)
    nitems = len(test.ctx.entries)

    assert len(f.index) == nitems
    assert len(f.choices) == (nargs * nitems)
    assert len(results) == nargs


def ext_match_found():
    query = get_params()[0][1]
    result = get_results()[1]

    assert query == result["query"]
    assert any(any("Smith" in x for x in (m["pathDisplay"], m.get("matched_label")) if x) for m in result["matches"])


def ext_unique_matches():
    matches = test.ctx.results[1]["matches"]
    assert typeis(matches, list)
    assert len(matches) == 1


@test.suite(
    ["input_text", "index_items"],
    simple_matching=test.spec(
        (
            ["finder", "John Smith"],
            ["/Clio/Smith, John/00001-Smith", "/Clio/Jones, Mary/00002-Jones"],
        ),
        hooks=[
            test.hook(extensions=[ext_proper_length]),
            test.hook(handlers=[lambda *_: test.ctx.print(include={"results"})]),
        ],
    ),
    fuzzy_matching=test.spec(
        (
            ["finder", "Jon Smth"],
            [
                "/Clio/Smith, John/00001-Smith",
                "/Clio/Smith-Jones, Anna/00002-SmithJones",
                "/Clio/ONeil, Patrick/00003-ONeil",
            ],
        ),
        hooks=[
            test.hook(extensions=[ext_match_found]),
            test.hook(handlers=[lambda *_: test.ctx.print(include={"query", "result"})]),
        ],
    ),
    dedupe_keep_highest=test.spec(
        (
            ["finder", "John Smith"],
            ["/Clio/Smith, John/00001-Smith", "/Clio/Smith, John/00001-Smith"],
        ),
        hooks=[
            test.hook(extensions=[ext_unique_matches]),
            test.hook(handlers=[lambda *_: test.ctx.print(include={"matches"})]),
        ],
    ),
)
def test_finder_paramaterized(
    __extension,
    input_text: list[str],
    index_items: list[str],
    finderpatch,
):
    entries = js.array(json(pathDisplay=path) for path in index_items)

    SVC.mkdir()
    DBX.write_text(repr(entries))

    f = finderpatch(input_text).setup()

    assert f.dbx_path.as_posix() == DBX.as_posix()

    try:
        assert typeis(f.index, list)
    except AssertionError:
        print(f"{f.index=!s}")
        raise

    try:
        assert typeis(f.choices, list[str])
    except AssertionError:
        print(f"{f.choices=!s}")
        raise

    f.run()

    results = f.json.get("results")
    assert isinstance(results, list)

    __extension(locals())

    DBX.unlink()
    SVC.rmdir()

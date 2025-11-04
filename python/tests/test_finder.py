# ruff: noqa: F401, F811
# %%
from __future__ import annotations

import functools

import pytest
from common.document import Document, DocumentSet, _DocumentMetadata
from common.metadata import refresh_metadata_cache
from n8n_py.finder.cls import FinderResult, FolderFinder, IndexEntry
from rampy import js, json, test, typeis


@pytest.fixture
def workspace_root():
    with test.path(context=True) as tmp_root:
        yield tmp_root


@pytest.fixture
def finderpatch(monkeypatch, workspace_root):
    import common.metadata as metadata_mod
    import common.temp as tempmod
    import n8n_py.finder.cls as findermod

    monkeypatch.setattr(findermod, "root", lambda: workspace_root)

    metadata_dir = workspace_root / "service" / "tmp"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(tempmod, "TMP", metadata_dir)
    monkeypatch.setattr(metadata_mod, "_METADATA_PATH", metadata_dir / "metadata.json")
    refresh_metadata_cache()

    try:
        yield functools.partial(findermod.FolderFinder, testing=True)
    finally:
        refresh_metadata_cache()


@pytest.fixture()
def dbx_index(workspace_root):
    service_dir = workspace_root / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    return service_dir / "dbx_index.json"


class namespace(test.ns[list[str], list[str]]):
    finder: FolderFinder
    results: list[FinderResult]
    entries: js.array[json[str, str]]


ctx, cases = test.context.bind(namespace)


def base():
    ns = ctx.get()

    nargs, nitems = len(ns.args[0]), len(ns.entries)

    assert len(ns.finder.index) == nitems
    assert len(ns.finder.choices) == (nargs * nitems)
    assert len(ns.results) == nargs


cases["base"] = test.case(
    ["finder", "John Smith"],
    ["/Clio/Smith, John/00001-Smith", "/Clio/Jones, Mary/00002-Jones"],
    hooks=[base, lambda *_: ctx.print(include={"results"})],
)


def fuzzy_matching():
    ns = ctx.get()

    query = ns.args[0][1]
    result = ns.results[1]

    assert query == result["query"]

    for m in result["matches"]:
        search = m["pathDisplay"], m.get("matched_label")
        assert any("Smith" in s for s in search if s)


cases["fuzzy_matching"] = test.case(
    ["finder", "Jon Smth"],
    [
        "/Clio/Smith, John/00001-Smith",
        "/Clio/Smith-Jones, Anna/00002-SmithJones",
        "/Clio/ONeil, Patrick/00003-ONeil",
    ],
    hooks=[fuzzy_matching, lambda _: ctx.print(include={"query", "result"})],
)


def keep_highest_unique():
    ns = ctx.get()

    matches = ns.results[1]["matches"]

    assert typeis(matches, list)
    assert len(matches) == 1


cases["keep_highest_unique"] = test.case(
    ["finder", "John Smith"],
    ["/Clio/Smith, John/00001-Smith", "/Clio/Smith, John/00001-Smith"],
    hooks=[keep_highest_unique, lambda _: ctx.print(include={"matches"})],
)


@test.suite(cases)
def test_finder_paramaterized(input_text: list[str], index_items: list[str], finderpatch, dbx_index):
    entries = js.array(json(pathDisplay=path) for path in index_items)

    dbx_index.write_text(repr(entries))

    finder = finderpatch(input_text).setup()

    assert finder.dbx_path.as_posix() == dbx_index.as_posix()
    assert typeis(finder.index, list[IndexEntry])
    assert typeis(finder.choices, list[str])

    finder.run()
    results = finder.json.get("results")

    assert typeis(results, list[FinderResult])

    ctx(**locals())


@pytest.fixture
def doc_info():
    DocumentSet


# TODO
def test_finder_metadata_shortcut(finderpatch, dbx_index):
    doc = DocumentSet

    entries = js.array([json(pathDisplay=doc.path_display)])
    dbx_index.write_text(repr(entries))

    metadata_store = {}  # json[str, _DocumentMetadata]({doc.name: doc["metadata"]})
    metadata_path = dbx_index.parent / "tmp" / "metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(str(metadata_store))
    refresh_metadata_cache()

    finder = finderpatch(["finder", doc.desc])
    finder.setup().run()

    results = finder.json.get("results", [])
    assert len(results) == 2
    matches = results[1]["matches"]
    assert matches
    top = matches[0]
    assert top["pathDisplay"] == doc.path_display
    assert top["reason"] in {"exact", "metadata"}
    if top["reason"] == "metadata":
        assert top["matched_label"] == doc.desc


if __name__ == "__main__":
    pytest.main([__file__])

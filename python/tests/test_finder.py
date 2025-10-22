# ruff: noqa: F401, F811
from __future__ import annotations

import functools
import typing as ty

import pytest
from rampy import js, json, test, typed

from .shared import hook, path, spec, suite

if ty.TYPE_CHECKING:
    from .shared import TestExtensionFunc

SVC = path("service")
DBX = SVC / "dbx_index.json"


@pytest.fixture
def finderpatch(monkeypatch):
    import n8n_py.finder.cls as findermod

    monkeypatch.setattr(findermod, "root", lambda: SVC.parent)

    return functools.partial(findermod.FolderFinder, testing=True)


@test.suite(
    ["input_text", "index_items", "test_extension"],
    simple_matching=test.spec(
        arguments=(
            ["finder", "John Smith"],
            ["/Clio/Smith, John/00001-Smith", "/Clio/Jones, Mary/00002-Jones"],
        ),
        predicates=[
            "len(f.index) == nitems",
            "len(f.choices) == (nargs * nitems)",
            "typed(list)(results)",
            "len(results) == nargs",
        ],
        hooks=[
            test.hook(
                test.on.pre,
                providers=[lambda ctx: {"nargs": len(ctx["input_text"]), "nitems": len(ctx["entries"])}],
            ),
            test.hook(consumers=[lambda ctx, *_: print(ctx["results"])]),
        ],
    ),
    fuzzy_matching=test.spec(
        arguments=(
            ["finder", "Jon Smth"],
            [
                "/Clio/Smith, John/00001-Smith",
                "/Clio/Smith-Jones, Anna/00002-SmithJones",
                "/Clio/ONeil, Patrick/00003-ONeil",
            ],
        ),
        predicates=[
            "query == result['query']",
            "result['matches']",
            "any(any('Smith' in x for x in (m['pathDisplay'], m.get('matched_label')) if x) for m in result['matches'])",
        ],
        hooks=[
            test.hook(
                test.on.pre,
                providers=[lambda ctx: {"query": ctx["input_text"][1], "result": ctx["results"][1]}],
            ),
            test.hook(consumers=[lambda ctx, *_: print(f"{ctx['query']=}", ctx["result"], sep="\n")]),
        ],
    ),
    dedupe_keep_highest=test.spec(
        arguments=(
            ["finder", "John Smith"],
            ["/Clio/Smith, John/00001-Smith", "/Clio/Smith, John/00001-Smith"],
        ),
        predicates=["typed(list)(matches)", "len(matches) == 1"],
        hooks=[
            test.hook(
                test.on.pre,
                providers=[lambda ctx: {"matches": ctx["results"][1]["matches"]}],
            ),
            test.hook(consumers=[lambda ctx, *_: print(ctx["matches"])]),
        ],
    ),
)
def test_finder_paramaterized(
    input_text: list[str],
    index_items: list[str],
    test_extension: TestExtensionFunc,
    finderpatch,
):
    entries = js.array(index_items).map(lambda pd: json(pathDisplay=pd))

    SVC.mkdir()
    DBX.write_text(str(entries))

    f = finderpatch(input_text).setup()

    assert f.dbx_path.as_posix() == DBX.as_posix()

    try:
        assert typed(list)(f.index)
    except AssertionError:
        print(f"{f.index=!s}")
        raise

    try:
        assert typed(list[str])(f.choices)
    except AssertionError:
        print(f"{f.choices=!s}")
        raise

    f.run()

    results = f.json.get("results")
    assert results is not None

    test_extension(locals())

    DBX.unlink()
    SVC.rmdir()

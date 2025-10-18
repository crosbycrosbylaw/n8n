import n8n_py.finder.cls as findermod
from rampy import js, json, typed

from python.tests.shared import temp


def test_finder_loads_index_and_matches(monkeypatch):
    # create a minimal dbx_index.json
    entries = js.array.fromitems(
        json(pathDisplay="/Clio/Smith, John/00001-Smith"),
        json(pathDisplay="/Clio/Jones, Mary/00002-Jones"),
    )
    svc = temp("service")

    print(svc)

    svc.mkdir(exist_ok=True)
    dbx = svc / "dbx_index.json"
    dbx.write_text(str(entries))

    print(dbx.read_text())

    monkeypatch.setattr(findermod, "root", lambda: svc.parent)

    inputs = ["finder", "John Smith"]
    inst = findermod.FolderFinder(
        input=inputs,
        testing=True,
    )

    inst.setup()

    assert inst.dbx_path.as_posix() == dbx.as_posix()
    assert typed(list[dict])(inst.index)
    assert len(inst.index) == len(entries)
    assert all(x == y for x, y in zip(entries, inst.index, strict=True))

    assert typed(list)(inst.choices)
    assert len(inst.choices) == 4

    inst.run()

    assert "matches" in inst.json
    results = inst.json["matches"]
    assert typed(list[dict])(results)
    assert len(results) == 2

    for inp, res in zip(inputs, results):
        assert "query" in res
        assert res["query"] == inp
        assert "matches" in res
        matches = res["matches"]
        assert typed(list[dict])(matches)
        assert len(matches) > 0

    dbx.unlink()
    svc.rmdir()

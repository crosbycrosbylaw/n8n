import n8n_py.extractor.cls as exmod
from rampy import typed


def test_extractor_normalizes_and_parses():
    input_text = ["Smith v. Jones"]
    extractor = exmod.NameExtractor(input_text, testing=True).setup().run()

    assert "results" in extractor.json

    results = extractor.json["results"]
    assert typed(list)(results)

    first = results[0]

    try:
        assert typed(dict)(first)
        assert first["found_names"]
    except AssertionError:
        print(f"{first=!s}")
        raise

    parties = first["parties"]

    try:
        candidates = parties[0]["candidates"]
        party_type = parties[0]["type"]
        assert typed(list[dict])(candidates)
        assert any("smith" in c.get("normalized", "") for c in candidates) or party_type == "company"
        assert len(parties) == 2
    except AssertionError:
        print(f"{parties=!s}")
        raise


def test_extractor_handles_v_vs_and_company():
    cases = [
        "Smith v Jones",
        "Johnson vs. Brown",
        "ACME CORPORATION v. Doe",
    ]

    extractor = exmod.NameExtractor(cases, testing=True).setup().run()

    assert "results" in extractor.json

    results = extractor.json["results"]
    assert typed(list)(results)
    assert len(results) == 3

    # first two should be people parties
    for res in results[:2]:
        assert res["found_names"]

        left, right = res["parties"]
        assert left["type"] == "person"
        assert right["type"] == "person"

    # third should detect company on left
    third = results[2]
    assert third["found_names"]

    left, right = third["parties"]
    assert left["type"] == "company"
    assert right["type"] == "person"


# TODO !!
def test_extractor_normalization_accents_and_hyphens():
    inputs = ["José O'Neill v. Mary-Anne"]
    extractor = exmod.NameExtractor(inputs, testing=True).setup().run()

    assert "results" in extractor.json
    results = extractor.json["results"]
    assert typed(list)(results)
    assert len(results) >= 1

    first = results[0]
    assert first
    assert first["found_names"]

    for p, s in zip(first["parties"], ("o neill", "mary-anne")):
        if p["type"] == "company":
            continue
        candidates = p["candidates"]
        try:
            assert typed(list[dict])(candidates)
            assert any(s in c.get("normalized", "") for c in candidates)
        except AssertionError:
            print(f"{first['parties']=!s}")
            print(f"{candidates=!s}")
            raise

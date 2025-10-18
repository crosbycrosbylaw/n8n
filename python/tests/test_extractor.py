import n8n_py.extractor.cls as exmod


def test_extractor_normalizes_and_parses():
    input_text = ["Smith v. Jones"]
    inst = exmod.NameExtractor(input_text, testing=True)

    inst.setup()
    inst.run()

    assert "results" in inst.json
    results = inst.json["results"]
    assert isinstance(results, list)

    assert results[0]["found_names"]
    parties = results[0]["parties"]
    assert len(parties) == 2
    assert (
        any("smith" in c.get("normalized", "") for c in parties[0]["candidates"]) or parties[0]["type"] == "company"
    )

from rx_strategist.knowledge.drug_lookup import clear_lookup_cache, lookup_drug


def setup_function():
    clear_lookup_cache()


def test_rxnorm_hit_resolves_without_fda(monkeypatch):
    def fake_fetch(url, timeout=8):
        if "rxcui.json" in url:
            return {"idGroup": {"name": "ciplox", "rxnormId": ["20481"]}}
        if "related.json" in url:
            return {
                "relatedGroup": {
                    "conceptGroup": [
                        {"tty": "IN", "conceptProperties": [{"name": "Ciprofloxacin"}]}
                    ]
                }
            }
        if "label.json" in url:
            return {"results": []}
        return {}

    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json", fake_fetch
    )
    result = lookup_drug("Ciplox")
    assert result["resolved"] is True
    assert result["rxcui"] == "20481"
    assert "Ciprofloxacin" in result["ingredients"]
    assert result["source"] == "rxnorm"


def test_openfda_hit_resolves_without_rxcui(monkeypatch):
    def fake_fetch(url, timeout=8):
        if "rxcui.json" in url:
            return {"idGroup": {}}
        if "approximateTerm.json" in url:
            return {"approximateGroup": {"candidate": []}}
        if "label.json" in url:
            return {
                "results": [
                    {
                        "indications_and_usage": ["For relief of dry eye."],
                        "dosage_and_administration": ["Instill 1 or 2 drops."],
                        "openfda": {"substance_name": ["CARBOXYMETHYLCELLULOSE SODIUM"]},
                    }
                ]
            }
        return {}

    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json", fake_fetch
    )
    result = lookup_drug("Refresh Tear")
    assert result["resolved"] is True
    assert "openfda" in (result["source"] or "")
    assert "dry eye" in result["indications_text"].lower()
    assert "drops" in result["dosage_text"].lower()


def test_empty_apis_are_unresolved(monkeypatch):
    def fake_fetch(url, timeout=8):
        if "label.json" in url:
            return {"results": []}
        return {"idGroup": {}, "approximateGroup": {"candidate": []}}

    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json", fake_fetch
    )
    result = lookup_drug("not-a-real-drugazole")
    assert result["resolved"] is False
    assert result["error"]


def test_http_error_is_unresolved(monkeypatch):
    def fake_fetch(url, timeout=8):
        raise RuntimeError("HTTP 500 for rxnorm")

    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json", fake_fetch
    )
    result = lookup_drug("Ciplox")
    assert result["resolved"] is False
    assert "HTTP 500" in (result["error"] or "")


def test_empty_name_does_not_call_network(monkeypatch):
    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json",
        lambda url, timeout=8: (_ for _ in ()).throw(AssertionError("network")),
    )
    result = lookup_drug("  ")
    assert result["resolved"] is False
    assert result["error"] == "Empty drug name."


def test_lookup_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(url, timeout=8):
        calls["count"] += 1
        if "rxcui.json" in url:
            return {"idGroup": {"rxnormId": ["1"]}}
        if "related.json" in url:
            return {"relatedGroup": {"conceptGroup": []}}
        return {"results": []}

    monkeypatch.setattr(
        "rx_strategist.knowledge.drug_lookup._fetch_json", fake_fetch
    )
    first = lookup_drug("Ciplox")
    second = lookup_drug("ciplox")
    assert first["rxcui"] == second["rxcui"]
    assert calls["count"] > 0
    first_calls = calls["count"]
    lookup_drug("CIPLOX")
    assert calls["count"] == first_calls

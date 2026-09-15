from rx_strategist.verification.indication import check_indication


def test_matching_indication_is_appropriate():
    result = check_indication("losartan", ["Hypertension"])

    assert result == {
        "status": "APPROPRIATE",
        "matched_condition": "Hypertension",
        "reason": "losartan has a matching indication.",
    }


def test_missing_indication_requires_review():
    result = check_indication("losartan", ["asthma"])

    assert result["status"] == "REVIEW"
    assert result["reason"] == "No matching indication found."


def test_unknown_drug_is_appropriate_when_api_resolves():
    result = check_indication(
        "Ciplox",
        [],
        lookup_fn=lambda name: {
            "resolved": True,
            "source": "rxnorm",
            "ingredients": ["ciprofloxacin"],
            "indications_text": "bacterial infections",
        },
    )
    assert result["status"] == "APPROPRIATE"
    assert result["source"] == "rxnorm"
    assert "ciprofloxacin" in result["reason"].lower()


def test_unknown_drug_requires_review_when_api_unresolved():
    result = check_indication(
        "unknownzole",
        [],
        lookup_fn=lambda name: {"resolved": False, "error": "not found"},
    )
    assert result["status"] == "REVIEW"
    assert result["reason"] == "Drug not found in knowledge base."

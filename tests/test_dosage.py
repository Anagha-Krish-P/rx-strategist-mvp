from rx_strategist.verification.dosage import check_dosage


def test_matching_dosage_is_appropriate():
    result = check_dosage(
        "metformin", "type 2 diabetes", "500 mg", "twice daily"
    )

    assert result["status"] == "APPROPRIATE"
    assert result["recommended"] == {
        "dose": "500 mg",
        "frequency": "twice daily",
    }


def test_non_matching_dosage_requires_review():
    result = check_dosage(
        "metformin", "type 2 diabetes", "1000 mg", "twice daily"
    )

    assert result["status"] == "REVIEW"
    assert result["prescribed"]["dose"] == "1000 mg"


def test_unknown_drug_dosage_is_appropriate_when_api_resolves():
    result = check_dosage(
        "Refresh Tear",
        "",
        "1 drop",
        "three times daily",
        lookup_fn=lambda name: {
            "resolved": True,
            "source": "openfda",
            "dosage_text": "Instill 1 or 2 drops as needed.",
            "ingredients": ["carboxymethylcellulose"],
        },
    )
    assert result["status"] == "APPROPRIATE"
    assert result["recommended"]["guidance"].startswith("Instill")


def test_unknown_drug_dosage_requires_review_when_api_unresolved():
    result = check_dosage(
        "unknownzole",
        "",
        "10 mg",
        "once daily",
        lookup_fn=lambda name: {"resolved": False, "error": "not found"},
    )
    assert result["status"] == "REVIEW"
    assert result["reason"] == "Drug not found."
